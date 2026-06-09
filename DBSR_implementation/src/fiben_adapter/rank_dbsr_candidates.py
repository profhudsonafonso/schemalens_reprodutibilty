#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from dbsr_core.cost_model import score_query_plan_row
from dbsr_core.pruning import prune_query_plans
from dbsr_core.utility import build_document_utility_matrix, rank_documents


def read_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--generated-query-plans",
        default="DBSR_implementation/generated/fiben/dbsr_generated_query_plans.csv",
    )
    parser.add_argument(
        "--out-dir",
        default="DBSR_implementation/generated/fiben",
    )
    parser.add_argument(
        "--near-best-cost-ratio",
        type=float,
        default=1.20,
    )
    parser.add_argument(
        "--max-plans-per-sequence",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--top-k-documents",
        type=int,
        default=10,
    )
    args = parser.parse_args()

    plans = read_csv(Path(args.generated_query_plans))

    scored_rows: List[Dict[str, Any]] = []
    for row in plans:
        score = score_query_plan_row(row)
        scored = dict(row)
        scored.update(score)
        scored_rows.append(scored)

    pruned_rows = prune_query_plans(
        scored_rows=scored_rows,
        near_best_cost_ratio=args.near_best_cost_ratio,
        max_plans_per_sequence=args.max_plans_per_sequence,
    )

    matrix_rows = build_document_utility_matrix(pruned_rows)
    ranked_documents = rank_documents(matrix_rows)
    recommended_documents = ranked_documents[: args.top_k_documents]

    out_dir = Path(args.out_dir)

    scored_fields = [
        "query_name",
        "sequence_id",
        "frequency",
        "step_count",
        "join_steps",
        "document_count",
        "plan_signature",
        "filters_json",
        "structural_cost",
        "plan_utility",
        "total_document_structural_cost",
        "filter_count",
        "required_secondary_indexes",
        "origin",
        "steps_json",
    ]

    pruned_fields = scored_fields + [
        "structural_rank_within_sequence",
        "best_structural_cost_for_sequence",
        "cost_ratio_to_best_sequence_plan",
        "is_best_structural_plan",
        "is_pruned_candidate",
    ]

    matrix_fields = [
        "query_name",
        "sequence_id",
        "document_signature",
        "plan_signature",
        "plan_structural_cost",
        "plan_utility",
        "document_utility_contribution",
    ]

    ranked_fields = [
        "rank",
        "document_signature",
        "total_utility",
        "queries_covered",
        "sequences_covered",
        "plans_using_document",
        "query_names",
        "sequence_ids",
    ]

    write_csv(out_dir / "dbsr_scored_query_plans.csv", scored_rows, scored_fields)
    write_csv(out_dir / "dbsr_pruned_query_plans.csv", pruned_rows, pruned_fields)
    write_csv(out_dir / "dbsr_document_utility_matrix.csv", matrix_rows, matrix_fields)
    write_csv(out_dir / "dbsr_ranked_schemas.csv", ranked_documents, ranked_fields)
    write_csv(out_dir / "dbsr_recommended_documents.csv", recommended_documents, ranked_fields)

    summary = {
        "implementation_status": "phase_2c_structural_cost_pruning_and_first_utility_ranking",
        "input_query_plans": len(plans),
        "scored_query_plans": len(scored_rows),
        "pruned_query_plans": len(pruned_rows),
        "utility_matrix_rows": len(matrix_rows),
        "ranked_documents": len(ranked_documents),
        "recommended_documents": len(recommended_documents),
        "near_best_cost_ratio": args.near_best_cost_ratio,
        "max_plans_per_sequence": args.max_plans_per_sequence,
        "top_k_documents": args.top_k_documents,
        "generated_files": [
            "dbsr_scored_query_plans.csv",
            "dbsr_pruned_query_plans.csv",
            "dbsr_document_utility_matrix.csv",
            "dbsr_ranked_schemas.csv",
            "dbsr_recommended_documents.csv",
            "dbsr_ranking_summary.json",
        ],
        "implementation_assumptions": [
            "This phase uses a structural proxy cost, not the final DBSR cost model.",
            "The cost rewards shorter query plans and penalizes larger/deeper/wider document trees.",
            "Cardinality, selectivity, physical object size, and MongoDB execution statistics are not used yet.",
            "Document utility is aggregated from pruned query plans and uniformly distributed over documents used by each plan.",
            "Full schema assembly from ranked documents is deferred to a later phase.",
        ],
    }

    with (out_dir / "dbsr_ranking_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Input query plans: {summary['input_query_plans']}")
    print(f"Scored query plans: {summary['scored_query_plans']}")
    print(f"Pruned query plans: {summary['pruned_query_plans']}")
    print(f"Utility matrix rows: {summary['utility_matrix_rows']}")
    print(f"Ranked documents: {summary['ranked_documents']}")
    print(f"Recommended documents: {summary['recommended_documents']}")
    print(f"Wrote {out_dir / 'dbsr_scored_query_plans.csv'}")
    print(f"Wrote {out_dir / 'dbsr_pruned_query_plans.csv'}")
    print(f"Wrote {out_dir / 'dbsr_document_utility_matrix.csv'}")
    print(f"Wrote {out_dir / 'dbsr_ranked_schemas.csv'}")
    print(f"Wrote {out_dir / 'dbsr_recommended_documents.csv'}")
    print(f"Wrote {out_dir / 'dbsr_ranking_summary.json'}")


if __name__ == "__main__":
    main()
