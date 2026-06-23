#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workload",
        default="DBSR_implementation/generated/fiben/dbsr_workload.json",
        help="Auto-generated draft DBSR workload."
    )
    parser.add_argument(
        "--overrides",
        default="DBSR_implementation/input/fiben/query_sequence_overrides.json",
        help="Manual reviewed query sequence overrides."
    )
    parser.add_argument(
        "--output",
        default="DBSR_implementation/generated/fiben/dbsr_workload_reviewed.json",
        help="Reviewed DBSR workload output."
    )
    args = parser.parse_args()

    workload = read_json(Path(args.workload))
    overrides = read_json(Path(args.overrides))

    query_overrides = overrides.get("query_overrides", {})
    applied = 0
    missing = []

    for query in workload.get("queries", []):
        qname = query.get("query_name")
        override = query_overrides.get(qname)

        if not override:
            missing.append(qname)
            continue

        query["dbsr_sequence_inferred"] = query.get("dbsr_sequence", [])
        query["dbsr_sequences"] = override.get("dbsr_sequences", [])
        query["frequency"] = override.get("frequency", query.get("frequency", 1.0))
        query["status"] = "manual_sequence_reviewed_draft"
        query["review_status"] = override.get("review_status", "reviewed_draft")
        query["manual_override_source"] = str(Path(args.overrides))
        query["manual_sequence_intents"] = [
            {
                "sequence_id": seq.get("sequence_id"),
                "intent": seq.get("intent")
            }
            for seq in query["dbsr_sequences"]
        ]

        if "implementation_assumption" in override:
            query["implementation_assumption"] = override["implementation_assumption"]

        applied += 1

    workload["version"] = "0.2-reviewed-workload-draft"
    workload["manual_review_required"] = True
    workload["manual_review_status"] = "reviewed_draft_not_final"
    workload["override_file"] = str(Path(args.overrides))
    workload["notes"].append(
        "Manual query-sequence overrides were applied. The result is still a reviewed draft and must be checked against exact FIBEN query implementations before final DBSR generation."
    )

    write_json(Path(args.output), workload)

    print(f"Wrote {args.output}")
    print(f"Overrides applied: {applied}")
    print(f"Queries without override: {len(missing)}")

    if missing:
        print("Missing overrides:")
        for q in missing:
            print(f"  - {q}")


if __name__ == "__main__":
    main()
