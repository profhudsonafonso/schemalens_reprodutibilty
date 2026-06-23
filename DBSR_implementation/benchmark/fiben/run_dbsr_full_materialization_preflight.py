#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


MONGO_DOC_LIMIT_BYTES = 16 * 1024 * 1024


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def connect_mongo(args: argparse.Namespace):
    from pymongo import MongoClient

    kwargs: Dict[str, Any] = {
        "host": args.mongo_host,
        "port": args.mongo_port,
        "serverSelectionTimeoutMS": 5000,
    }

    if args.mongo_username:
        kwargs["username"] = args.mongo_username
    if args.mongo_password:
        kwargs["password"] = args.mongo_password
    if args.mongo_auth_source:
        kwargs["authSource"] = args.mongo_auth_source

    client = MongoClient(**kwargs)
    client.admin.command("ping")
    return client


def collection_stats(db, collection_name: str) -> Dict[str, Any]:
    try:
        stats = db.command("collStats", collection_name)
        return {
            "count": int(stats.get("count", 0)),
            "avg_obj_size": float(stats.get("avgObjSize", 0.0) or 0.0),
            "storage_size": int(stats.get("storageSize", 0) or 0),
            "total_index_size": int(stats.get("totalIndexSize", 0) or 0),
        }
    except Exception as exc:
        return {
            "count": db[collection_name].count_documents({}),
            "avg_obj_size": 0.0,
            "storage_size": 0,
            "total_index_size": 0,
            "error": str(exc),
        }


def top_child_counts(db, child_collection: str, child_join_column: str, top_n: int) -> Dict[str, Any]:
    match_stage = {
        "$match": {
            child_join_column: {
                "$exists": True,
                "$ne": None,
            }
        }
    }

    group_stage = {
        "$group": {
            "_id": f"${child_join_column}",
            "child_count": {"$sum": 1},
        }
    }

    summary_pipeline = [
        match_stage,
        group_stage,
        {
            "$group": {
                "_id": None,
                "parent_keys_with_children": {"$sum": 1},
                "total_children": {"$sum": "$child_count"},
                "max_children": {"$max": "$child_count"},
                "avg_children_when_present": {"$avg": "$child_count"},
            }
        },
    ]

    top_pipeline = [
        match_stage,
        group_stage,
        {"$sort": {"child_count": -1}},
        {"$limit": top_n},
    ]

    summary = list(db[child_collection].aggregate(summary_pipeline, allowDiskUse=True))
    top_values = list(db[child_collection].aggregate(top_pipeline, allowDiskUse=True))

    if summary:
        row = summary[0]
        parent_keys_with_children = int(row.get("parent_keys_with_children", 0) or 0)
        total_children = int(row.get("total_children", 0) or 0)
        max_children = int(row.get("max_children", 0) or 0)
        avg_children = float(row.get("avg_children_when_present", 0.0) or 0.0)
    else:
        parent_keys_with_children = 0
        total_children = 0
        max_children = 0
        avg_children = 0.0

    return {
        "child_collection": child_collection,
        "child_join_column": child_join_column,
        "parent_keys_with_children": parent_keys_with_children,
        "total_children": total_children,
        "max_children": max_children,
        "avg_children_when_present": avg_children,
        "top_parent_values": [
            {
                "join_value": str(row["_id"]),
                "child_count": int(row["child_count"]),
            }
            for row in top_values
        ],
    }


def source_collection_map(collection_plan: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        source["entity"]: source
        for source in collection_plan.get("source_collections", [])
    }


def estimate_document_size(
    entity: str,
    children_by_parent: Dict[str, List[Dict[str, Any]]],
    source_by_entity: Dict[str, Dict[str, Any]],
    source_stats: Dict[str, Dict[str, Any]],
    relation_stats: Dict[Tuple[str, str, str], Dict[str, Any]],
) -> float:
    source_view = source_by_entity[entity]["source_view"]
    base_size = source_stats.get(source_view, {}).get("avg_obj_size", 0.0)

    total = base_size

    for step in children_by_parent.get(entity, []):
        child_entity = step["child_entity"]
        child_source = source_by_entity[child_entity]["source_view"]
        key = (
            child_source,
            step["child_join_column"],
            step["relationship_id"],
        )

        rel = relation_stats.get(key, {})
        max_children = float(rel.get("max_children", 0.0) or 0.0)
        child_size = estimate_document_size(
            entity=child_entity,
            children_by_parent=children_by_parent,
            source_by_entity=source_by_entity,
            source_stats=source_stats,
            relation_stats=relation_stats,
        )

        total += max_children * child_size

    return total


def risk_label(estimated_bytes: float, threshold_bytes: int) -> str:
    if estimated_bytes >= threshold_bytes:
        return "high_risk_over_threshold"
    if estimated_bytes >= threshold_bytes * 0.5:
        return "medium_risk_near_threshold"
    return "low_risk"


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "target_collection",
        "document_signature",
        "root_entity",
        "root_source_view",
        "root_count",
        "embedding_steps",
        "estimated_worst_case_bson_bytes",
        "estimated_worst_case_bson_mb",
        "risk_label",
        "max_child_summary",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow({
                "target_collection": row["target_collection"],
                "document_signature": row["document_signature"],
                "root_entity": row["root_entity"],
                "root_source_view": row["root_source_view"],
                "root_count": row["root_count"],
                "embedding_steps": row["embedding_steps"],
                "estimated_worst_case_bson_bytes": row["estimated_worst_case_bson_bytes"],
                "estimated_worst_case_bson_mb": row["estimated_worst_case_bson_mb"],
                "risk_label": row["risk_label"],
                "max_child_summary": json.dumps(row["max_child_summary"], ensure_ascii=False),
            })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--materialization-plan",
        default="DBSR_implementation/generated/fiben/dbsr_materialization_plan_structural.json",
    )
    parser.add_argument("--scale-label", default="sf1_full_source")
    parser.add_argument("--mongo-host", default="127.0.0.1")
    parser.add_argument("--mongo-port", type=int, default=27018)
    parser.add_argument("--mongo-username", default=None)
    parser.add_argument("--mongo-password", default=None)
    parser.add_argument("--mongo-auth-source", default="admin")
    parser.add_argument("--mongo-db", required=True)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--threshold-mb", type=float, default=16.0)
    parser.add_argument("--out-dir", default="DBSR_implementation/generated/fiben")
    args = parser.parse_args()

    materialization_plan = read_json(Path(args.materialization_plan))

    client = connect_mongo(args)
    db = client[args.mongo_db]

    threshold_bytes = int(args.threshold_mb * 1024 * 1024)

    all_source_views = sorted({
        source["source_view"]
        for collection_plan in materialization_plan.get("collection_plans", [])
        for source in collection_plan.get("source_collections", [])
    })

    source_stats = {
        source_view: collection_stats(db, source_view)
        for source_view in all_source_views
    }

    relation_stats: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    for collection_plan in materialization_plan.get("collection_plans", []):
        source_by_entity = source_collection_map(collection_plan)

        for step in collection_plan.get("embedding_steps", []):
            child_entity = step["child_entity"]
            child_source = source_by_entity[child_entity]["source_view"]
            child_join_column = step["child_join_column"]
            relationship_id = step["relationship_id"]

            key = (child_source, child_join_column, relationship_id)

            if key not in relation_stats:
                relation_stats[key] = top_child_counts(
                    db=db,
                    child_collection=child_source,
                    child_join_column=child_join_column,
                    top_n=args.top_n,
                )
                relation_stats[key]["relationship_id"] = relationship_id
                relation_stats[key]["child_entity"] = child_entity

    collection_results = []

    for collection_plan in materialization_plan.get("collection_plans", []):
        source_by_entity = source_collection_map(collection_plan)
        root_entity = collection_plan["root_entity"]
        root_source_view = collection_plan["root_source_view"]

        children_by_parent: Dict[str, List[Dict[str, Any]]] = {}

        for step in collection_plan.get("embedding_steps", []):
            children_by_parent.setdefault(step["parent_entity"], []).append(step)

        estimated_bytes = estimate_document_size(
            entity=root_entity,
            children_by_parent=children_by_parent,
            source_by_entity=source_by_entity,
            source_stats=source_stats,
            relation_stats=relation_stats,
        )

        max_child_summary = []

        for step in collection_plan.get("embedding_steps", []):
            child_entity = step["child_entity"]
            child_source = source_by_entity[child_entity]["source_view"]
            key = (
                child_source,
                step["child_join_column"],
                step["relationship_id"],
            )
            rel = relation_stats[key]

            max_child_summary.append({
                "relationship_id": step["relationship_id"],
                "parent_entity": step["parent_entity"],
                "child_entity": step["child_entity"],
                "child_source_view": child_source,
                "child_join_column": step["child_join_column"],
                "max_children": rel["max_children"],
                "avg_children_when_present": rel["avg_children_when_present"],
                "top_parent_values": rel["top_parent_values"],
            })

        row = {
            "target_collection": collection_plan["target_collection"],
            "document_signature": collection_plan["document_signature"],
            "root_entity": root_entity,
            "root_source_view": root_source_view,
            "root_count": source_stats[root_source_view]["count"],
            "embedding_steps": len(collection_plan.get("embedding_steps", [])),
            "estimated_worst_case_bson_bytes": int(estimated_bytes),
            "estimated_worst_case_bson_mb": round(estimated_bytes / (1024 * 1024), 6),
            "risk_label": risk_label(estimated_bytes, threshold_bytes),
            "max_child_summary": max_child_summary,
        }

        collection_results.append(row)

    risk_counts: Dict[str, int] = {}
    for row in collection_results:
        risk_counts[row["risk_label"]] = risk_counts.get(row["risk_label"], 0) + 1

    output = {
        "baseline": "DBSR",
        "dataset": "FIBEN",
        "scale_label": args.scale_label,
        "check_type": "full_materialization_preflight",
        "mongo_database": args.mongo_db,
        "mongo_access": True,
        "official_benchmark": False,
        "threshold_mb": args.threshold_mb,
        "source_stats": source_stats,
        "relation_stats": [
            {
                "source_view": key[0],
                "join_column": key[1],
                "relationship_id": key[2],
                **value,
            }
            for key, value in relation_stats.items()
        ],
        "collection_results": collection_results,
        "risk_counts": risk_counts,
        "high_risk_collections": [
            row for row in collection_results
            if row["risk_label"] == "high_risk_over_threshold"
        ],
        "implementation_note": (
            "This preflight does not materialize DBSR collections and does not "
            "affect schema selection or p95 results. It estimates physical "
            "document-size risk before full MongoDB materialization."
        ),
    }

    out_dir = Path(args.out_dir)
    json_path = out_dir / f"dbsr_full_materialization_preflight_{args.scale_label}.json"
    csv_path = out_dir / f"dbsr_full_materialization_preflight_{args.scale_label}.csv"

    write_json(json_path, output)
    write_csv(csv_path, collection_results)

    print("DBSR full materialization preflight completed.")
    print(f"Mongo database: {args.mongo_db}")
    print(f"Target collections checked: {len(collection_results)}")
    print(f"Risk counts: {risk_counts}")
    print(f"High-risk collections: {len(output['high_risk_collections'])}")
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
