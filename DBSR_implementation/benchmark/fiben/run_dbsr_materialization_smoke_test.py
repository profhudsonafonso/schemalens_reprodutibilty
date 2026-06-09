#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_COLLECTION_PLAN_FIELDS = [
    "rank",
    "target_collection",
    "document_signature",
    "root_entity",
    "root_source_view",
    "root_primary_key",
    "tree_entities",
    "source_collections",
    "embedding_steps",
    "missing_relationships",
    "materialization_strategy",
    "materialization_status",
]


REQUIRED_SOURCE_COLLECTION_FIELDS = [
    "entity",
    "source_view",
    "primary_key",
]


REQUIRED_EMBEDDING_STEP_FIELDS = [
    "parent_entity",
    "child_entity",
    "relationship_id",
    "relationship_direction",
    "relationship_type",
    "parent_join_column",
    "child_join_column",
    "materialization_operation",
]


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def validate_source_collection(item: Dict[str, Any], path_label: str) -> List[str]:
    errors: List[str] = []

    for field in REQUIRED_SOURCE_COLLECTION_FIELDS:
        if field not in item:
            errors.append(f"{path_label}: missing source collection field '{field}'")
        elif item[field] in (None, ""):
            errors.append(f"{path_label}: empty source collection field '{field}'")

    return errors


def validate_embedding_step(item: Dict[str, Any], path_label: str) -> List[str]:
    errors: List[str] = []

    for field in REQUIRED_EMBEDDING_STEP_FIELDS:
        if field not in item:
            errors.append(f"{path_label}: missing embedding step field '{field}'")
        elif item[field] in (None, "") and field != "relationship_type":
            errors.append(f"{path_label}: empty embedding step field '{field}'")

    if item.get("materialization_operation") != "lookup_children_and_embed":
        errors.append(
            f"{path_label}: unsupported materialization operation "
            f"'{item.get('materialization_operation')}'"
        )

    return errors


def expected_operation_count(collection_plan: Dict[str, Any]) -> int:
    # One root scan plus one lookup/embed operation per embedding edge.
    return 1 + len(collection_plan.get("embedding_steps", []))


def validate_collection_plan(collection_plan: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    label = str(collection_plan.get("target_collection", "<unknown_collection>"))

    for field in REQUIRED_COLLECTION_PLAN_FIELDS:
        if field not in collection_plan:
            errors.append(f"{label}: missing collection plan field '{field}'")

    for field in [
        "target_collection",
        "document_signature",
        "root_entity",
        "root_source_view",
        "root_primary_key",
        "materialization_strategy",
        "materialization_status",
    ]:
        if collection_plan.get(field) in (None, ""):
            errors.append(f"{label}: empty required field '{field}'")

    if collection_plan.get("missing_relationships"):
        errors.append(f"{label}: plan contains missing relationships")

    tree_entities = collection_plan.get("tree_entities", [])
    if not isinstance(tree_entities, list) or not tree_entities:
        errors.append(f"{label}: tree_entities must be a non-empty list")

    source_collections = collection_plan.get("source_collections", [])
    if not isinstance(source_collections, list) or not source_collections:
        errors.append(f"{label}: source_collections must be a non-empty list")
    else:
        for idx, source in enumerate(source_collections):
            errors.extend(validate_source_collection(source, f"{label}.source_collections[{idx}]"))

    embedding_steps = collection_plan.get("embedding_steps", [])
    if not isinstance(embedding_steps, list):
        errors.append(f"{label}: embedding_steps must be a list")
        embedding_steps = []

    for idx, step in enumerate(embedding_steps):
        errors.extend(validate_embedding_step(step, f"{label}.embedding_steps[{idx}]"))

    if len(tree_entities) != len(source_collections):
        warnings.append(
            f"{label}: tree_entities count differs from source_collections count"
        )

    if collection_plan.get("materialization_strategy") != "root_scan_then_nested_lookup_embedding":
        warnings.append(
            f"{label}: non-default materialization strategy "
            f"'{collection_plan.get('materialization_strategy')}'"
        )

    if not embedding_steps and collection_plan.get("materialization_status") != "planned_single_entity_collection":
        warnings.append(
            f"{label}: no embedding steps but status is "
            f"'{collection_plan.get('materialization_status')}'"
        )

    if embedding_steps and collection_plan.get("materialization_status") != "planned_nested_embedding":
        warnings.append(
            f"{label}: has embedding steps but status is "
            f"'{collection_plan.get('materialization_status')}'"
        )

    return {
        "rank": collection_plan.get("rank"),
        "target_collection": collection_plan.get("target_collection", ""),
        "document_signature": collection_plan.get("document_signature", ""),
        "root_entity": collection_plan.get("root_entity", ""),
        "source_views_count": len(source_collections),
        "embedding_steps_count": len(embedding_steps),
        "expected_operations": expected_operation_count(collection_plan),
        "errors_count": len(errors),
        "warnings_count": len(warnings),
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "warnings": warnings,
    }


def build_dry_run_operations(collection_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    operations: List[Dict[str, Any]] = []

    target_collection = collection_plan.get("target_collection", "")
    root_source_view = collection_plan.get("root_source_view", "")

    operations.append(
        {
            "operation_order": 1,
            "target_collection": target_collection,
            "operation_type": "root_scan",
            "source_view": root_source_view,
            "entity": collection_plan.get("root_entity", ""),
            "join_description": "",
        }
    )

    for idx, step in enumerate(collection_plan.get("embedding_steps", []), start=2):
        operations.append(
            {
                "operation_order": idx,
                "target_collection": target_collection,
                "operation_type": "lookup_children_and_embed",
                "source_view": "",
                "entity": step.get("child_entity", ""),
                "join_description": (
                    f"{step.get('parent_entity')}."
                    f"{step.get('parent_join_column')} -> "
                    f"{step.get('child_entity')}."
                    f"{step.get('child_join_column')}"
                ),
            }
        )

    return operations


def run_smoke_test(materialization_plan: Dict[str, Any]) -> Dict[str, Any]:
    collection_plans = materialization_plan.get("collection_plans", [])

    collection_results = [
        validate_collection_plan(plan)
        for plan in collection_plans
    ]

    dry_run_operations = [
        operation
        for plan in collection_plans
        for operation in build_dry_run_operations(plan)
    ]

    failed = [item for item in collection_results if item["status"] != "passed"]
    warnings = [
        warning
        for item in collection_results
        for warning in item["warnings"]
    ]

    summary = {
        "baseline": "DBSR",
        "dataset": "FIBEN",
        "smoke_test_type": "materialization_plan_dry_run",
        "status": "passed" if not failed else "failed",
        "target_collections": len(collection_plans),
        "passed_collections": len(collection_results) - len(failed),
        "failed_collections": len(failed),
        "warnings_count": len(warnings),
        "dry_run_operations": len(dry_run_operations),
        "plan_only": True,
        "mongo_access": False,
        "benchmark_execution": False,
    }

    return {
        "summary": summary,
        "collection_results": collection_results,
        "dry_run_operations": dry_run_operations,
        "implementation_assumptions": [
            "This smoke test validates the DBSR materialization plan without connecting to MongoDB.",
            "It checks required fields, source views, primary keys, embedding steps, and missing relationships.",
            "It does not load data and does not measure p95 latency.",
            "The official DBSR benchmark must later run on the same server used for SchemaLens p95 measurements.",
        ],
    }


def collection_results_to_rows(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for item in results:
        rows.append(
            {
                "rank": item["rank"],
                "target_collection": item["target_collection"],
                "document_signature": item["document_signature"],
                "root_entity": item["root_entity"],
                "source_views_count": item["source_views_count"],
                "embedding_steps_count": item["embedding_steps_count"],
                "expected_operations": item["expected_operations"],
                "errors_count": item["errors_count"],
                "warnings_count": item["warnings_count"],
                "status": item["status"],
                "errors": " | ".join(item["errors"]),
                "warnings": " | ".join(item["warnings"]),
            }
        )

    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--materialization-plan",
        default="DBSR_implementation/generated/fiben/dbsr_materialization_plan_structural.json",
    )
    parser.add_argument(
        "--out-dir",
        default="DBSR_implementation/generated/fiben",
    )
    args = parser.parse_args()

    materialization_plan = read_json(Path(args.materialization_plan))
    smoke_manifest = run_smoke_test(materialization_plan)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "dbsr_materialization_smoke_manifest.json"
    csv_path = out_dir / "dbsr_materialization_smoke_manifest.csv"
    operations_path = out_dir / "dbsr_materialization_smoke_operations.csv"

    write_json(json_path, smoke_manifest)

    write_csv(
        csv_path,
        collection_results_to_rows(smoke_manifest["collection_results"]),
        fieldnames=[
            "rank",
            "target_collection",
            "document_signature",
            "root_entity",
            "source_views_count",
            "embedding_steps_count",
            "expected_operations",
            "errors_count",
            "warnings_count",
            "status",
            "errors",
            "warnings",
        ],
    )

    write_csv(
        operations_path,
        smoke_manifest["dry_run_operations"],
        fieldnames=[
            "operation_order",
            "target_collection",
            "operation_type",
            "source_view",
            "entity",
            "join_description",
        ],
    )

    summary = smoke_manifest["summary"]

    print(f"Smoke status: {summary['status']}")
    print(f"Target collections: {summary['target_collections']}")
    print(f"Passed collections: {summary['passed_collections']}")
    print(f"Failed collections: {summary['failed_collections']}")
    print(f"Warnings: {summary['warnings_count']}")
    print(f"Dry-run operations: {summary['dry_run_operations']}")
    print(f"Mongo access: {summary['mongo_access']}")
    print(f"Benchmark execution: {summary['benchmark_execution']}")
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {operations_path}")

    if summary["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
