#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dbsr_core.schema_assembly import (
    assemble_schema_manifest,
    load_generated_documents,
    load_pruned_query_plans,
    load_ranked_documents,
    manifest_to_rows,
    write_csv,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ranked-schemas",
        default="DBSR_implementation/generated/fiben/dbsr_ranked_schemas.csv",
    )
    parser.add_argument(
        "--generated-documents",
        default="DBSR_implementation/generated/fiben/dbsr_generated_documents.csv",
    )
    parser.add_argument(
        "--pruned-query-plans",
        default="DBSR_implementation/generated/fiben/dbsr_pruned_query_plans.csv",
    )
    parser.add_argument(
        "--out-dir",
        default="DBSR_implementation/generated/fiben",
    )
    parser.add_argument(
        "--top-k-documents",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--no-executable-coverage-closure",
        action="store_true",
        help="Disable the coverage-closure step and keep only top-k ranked documents.",
    )
    args = parser.parse_args()

    ranked_documents = load_ranked_documents(Path(args.ranked_schemas))
    generated_docs = load_generated_documents(Path(args.generated_documents))
    pruned_query_plans = load_pruned_query_plans(Path(args.pruned_query_plans))

    manifest = assemble_schema_manifest(
        ranked_documents=ranked_documents,
        generated_documents_by_signature=generated_docs,
        top_k_documents=args.top_k_documents,
        pruned_query_plans=pruned_query_plans,
        ensure_executable_coverage=not args.no_executable_coverage_closure,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "dbsr_schema_manifest_structural.json"
    csv_path = out_dir / "dbsr_schema_manifest_structural.csv"
    summary_path = out_dir / "dbsr_schema_manifest_structural_summary.json"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    rows = manifest_to_rows(manifest)
    write_csv(
        csv_path,
        rows,
        fieldnames=[
            "rank",
            "source_rank",
            "collection_name",
            "document_signature",
            "root_entity",
            "embedded_or_included_entities",
            "height_edges",
            "max_width",
            "total_utility",
            "queries_covered",
            "sequences_covered",
            "plans_using_document",
            "query_names",
            "sequence_ids",
            "selection_reason",
            "added_for_query",
            "added_for_sequence",
            "added_from_plan",
            "materialization_status",
            "tree_found_in_generated_documents",
        ],
    )

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(manifest["summary"], f, indent=2, ensure_ascii=False)
        f.write("\n")

    summary = manifest["summary"]
    print(f"Selected documents: {summary['selected_documents']}")
    print(f"Initial top-k documents: {summary['initial_top_k_documents']}")
    print(f"Added documents for executable coverage: {summary['added_documents_for_executable_coverage']}")
    print(f"Partial covered queries: {summary['partial_covered_queries']}")
    print(f"Partial covered sequences: {summary['partial_covered_sequences']}")
    print(f"Executable queries: {summary['executable_queries']}")
    print(f"Executable sequences: {summary['executable_sequences']}/{summary['total_sequences']}")
    print(f"Total selected utility: {summary['total_selected_utility']}")
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
