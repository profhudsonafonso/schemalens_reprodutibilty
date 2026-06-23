#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dbsr_core.generator import run_iterative_generator
from dbsr_core.model import DBSRModel
from dbsr_core.query_plan import (
    initial_plans_for_sequences,
    load_reviewed_sequences,
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
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
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

    initial_plans = initial_plans_for_sequences(sequences)
    result = run_iterative_generator(
        initial_plans=initial_plans,
        model=model,
        max_iterations=args.max_iterations,
    )

    out_dir = Path(args.out_dir)
    write_documents_csv(result.documents, out_dir / "dbsr_generated_documents.csv")
    write_query_plans_csv(result.query_plans, out_dir / "dbsr_generated_query_plans.csv")

    with (out_dir / "dbsr_generation_summary.json").open("w", encoding="utf-8") as f:
        json.dump(result.summary, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Generated documents: {result.summary['generated_documents']}")
    print(f"Generated query plans: {result.summary['generated_query_plans']}")
    print(f"Iterations executed: {result.summary['iterations_executed']}")
    print(f"Stopped because: {result.summary['stopped_because']}")
    print(f"Wrote {out_dir / 'dbsr_generated_documents.csv'}")
    print(f"Wrote {out_dir / 'dbsr_generated_query_plans.csv'}")
    print(f"Wrote {out_dir / 'dbsr_generation_summary.json'}")


if __name__ == "__main__":
    main()
