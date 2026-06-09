#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dbsr_core.model import DBSRModel
from dbsr_core.query_plan import (
    initial_documents_for_sequences,
    initial_plans_for_sequences,
    load_reviewed_sequences,
    summarize_initial_artifacts,
    write_documents_csv,
    write_query_plans_csv,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-model",
        default="DBSR_implementation/generated/fiben/dbsr_input_model.json",
    )
    parser.add_argument(
        "--workload",
        default="DBSR_implementation/generated/fiben/dbsr_workload_reviewed.json",
    )
    parser.add_argument(
        "--out-dir",
        default="DBSR_implementation/generated/fiben",
    )
    args = parser.parse_args()

    model = DBSRModel.from_json(Path(args.input_model))
    sequences = load_reviewed_sequences(Path(args.workload))

    errors = []
    for sequence in sequences:
        path_errors = model.validate_path(sequence.path)
        for error in path_errors:
            errors.append(
                {
                    "query_name": sequence.query_name,
                    "sequence_id": sequence.sequence_id,
                    "path": sequence.path,
                    "error": error,
                }
            )

    if errors:
        print("Path validation errors found:")
        for error in errors:
            print(json.dumps(error, ensure_ascii=False))
        raise SystemExit(1)

    documents = initial_documents_for_sequences(sequences)
    plans = initial_plans_for_sequences(sequences)
    summary = summarize_initial_artifacts(sequences, documents, plans)

    out_dir = Path(args.out_dir)
    write_documents_csv(documents, out_dir / "dbsr_initial_documents.csv")
    write_query_plans_csv(plans, out_dir / "dbsr_initial_query_plans.csv")

    with (out_dir / "dbsr_initial_plan_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Sequences loaded: {summary['sequences']}")
    print(f"Initial documents: {summary['initial_documents']}")
    print(f"Initial query plans: {summary['initial_query_plans']}")
    print(f"Max initial plan steps: {summary['max_initial_plan_steps']}")
    print(f"Wrote {out_dir / 'dbsr_initial_documents.csv'}")
    print(f"Wrote {out_dir / 'dbsr_initial_query_plans.csv'}")
    print(f"Wrote {out_dir / 'dbsr_initial_plan_summary.json'}")


if __name__ == "__main__":
    main()
