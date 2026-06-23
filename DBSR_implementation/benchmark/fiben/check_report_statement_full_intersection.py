#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def collect_statement_ids(path: Path) -> set[str]:
    ids = set()

    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)

        for row in reader:
            if row and row[0]:
                ids.add(row[0])

    return ids


def scan_report_elements(path: Path, statement_ids: set[str]) -> dict:
    total = 0
    matched = 0
    unmatched_examples = []
    matched_examples = []

    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)

        for row in reader:
            if not row or not row[0]:
                continue

            total += 1
            value = row[0]

            if value in statement_ids:
                matched += 1
                if len(matched_examples) < 10:
                    matched_examples.append(value)
            else:
                if len(unmatched_examples) < 10:
                    unmatched_examples.append(value)

    return {
        "report_elements_total": total,
        "statement_distinct_ids": len(statement_ids),
        "matched_report_elements": matched,
        "match_ratio": matched / total if total else 0,
        "matched_examples": matched_examples,
        "unmatched_examples": unmatched_examples,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument(
        "--out",
        default="DBSR_implementation/generated/fiben/dbsr_report_statement_full_intersection.json",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    statement_path = data_dir / "ELEMENTOFFINANCIALSTATEMENT.csv"
    report_element_path = data_dir / "ELEMENTSOFFINANCIALREPORT.csv"

    statement_ids = collect_statement_ids(statement_path)
    result = scan_report_elements(report_element_path, statement_ids)

    output = {
        "dataset": "FIBEN",
        "test": "ReportElement.ELEMENTSOFFINANCIALREPORTID -> StatementElement.ELEMENTOFFINANCIALSTATEMENTID",
        "result": result,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
