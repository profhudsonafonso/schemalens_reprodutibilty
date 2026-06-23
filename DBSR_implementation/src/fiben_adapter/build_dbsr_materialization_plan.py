#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from materialization.materialization_plan import (
    build_materialization_plan,
    materialization_plan_to_rows,
    read_json,
    write_csv,
    write_json,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-model",
        default="DBSR_implementation/generated/fiben/dbsr_input_model.json",
    )
    parser.add_argument(
        "--schema-manifest",
        default="DBSR_implementation/generated/fiben/dbsr_schema_manifest_structural.json",
    )
    parser.add_argument(
        "--out-dir",
        default="DBSR_implementation/generated/fiben",
    )
    args = parser.parse_args()

    input_model = read_json(Path(args.input_model))
    schema_manifest = read_json(Path(args.schema_manifest))

    plan = build_materialization_plan(
        input_model=input_model,
        schema_manifest=schema_manifest,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "dbsr_materialization_plan_structural.json"
    csv_path = out_dir / "dbsr_materialization_plan_structural.csv"
    summary_path = out_dir / "dbsr_materialization_plan_structural_summary.json"

    write_json(json_path, plan)

    rows = materialization_plan_to_rows(plan)
    write_csv(
        csv_path,
        rows,
        fieldnames=[
            "rank",
            "target_collection",
            "document_signature",
            "root_entity",
            "root_source_view",
            "root_primary_key",
            "tree_entities",
            "source_collections",
            "embedding_steps_count",
            "relationship_ids",
            "missing_relationships_count",
            "materialization_strategy",
            "materialization_status",
            "queries_covered",
            "sequences_covered",
            "total_utility",
        ],
    )

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(plan["summary"], f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Target collections: {plan['summary']['target_collections']}")
    print(f"Embedding steps total: {plan['summary']['embedding_steps_total']}")
    print(f"Missing relationships total: {plan['summary']['missing_relationships_total']}")
    print(f"Source views used: {plan['summary']['source_views_used']}")
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
