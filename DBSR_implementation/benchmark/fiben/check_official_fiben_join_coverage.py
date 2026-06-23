#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple


JOIN_TESTS = [
    {
        "name": "Transaction_REFERSTO_to_ListedSecurity_LISTEDSECURITYID",
        "parent_file": "SECURITIESTRANSACTION.csv",
        "parent_col": 3,
        "child_file": "LISTEDSECURITY.csv",
        "child_col": 0,
    },
    {
        "name": "Holding_REFERSTO_to_ListedSecurity_LISTEDSECURITYID",
        "parent_file": "HOLDING.csv",
        "parent_col": 2,
        "child_file": "LISTEDSECURITY.csv",
        "child_col": 0,
    },
    {
        "name": "FinancialServiceAccount_to_Holding",
        "parent_file": "FINANCIALSERVICEACCOUNT.csv",
        "parent_col": 0,
        "child_file": "HOLDING.csv",
        "child_col": 1,
    },
    {
        "name": "FinancialServiceAccount_to_Transaction",
        "parent_file": "FINANCIALSERVICEACCOUNT.csv",
        "parent_col": 0,
        "child_file": "SECURITIESTRANSACTION.csv",
        "child_col": 1,
    },
    {
        "name": "Corporation_to_Security",
        "parent_file": "CORPORATION.csv",
        "parent_col": 0,
        "child_file": "SECURITY.csv",
        "child_col": 2,
    },
    {
        "name": "FinancialReport_to_ReportElement",
        "parent_file": "FINANCIALREPORT.csv",
        "parent_col": 0,
        "child_file": "ELEMENTSOFFINANCIALREPORT.csv",
        "child_col": 1,
    },
    {
        "name": "ReportElement_to_StatementElement",
        "parent_file": "ELEMENTSOFFINANCIALREPORT.csv",
        "parent_col": 0,
        "child_file": "ELEMENTOFFINANCIALSTATEMENT.csv",
        "child_col": 0,
    },
]


def collect_values(path: Path, col_idx: int, max_rows: int) -> List[str]:
    values: List[str] = []

    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)

        for row_idx, row in enumerate(reader, start=1):
            if max_rows > 0 and row_idx > max_rows:
                break

            if col_idx < len(row):
                value = row[col_idx]
                if value != "":
                    values.append(value)

    return values


def collect_value_set(path: Path, col_idx: int) -> set:
    values = set()

    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)

        for row in reader:
            if col_idx < len(row):
                value = row[col_idx]
                if value != "":
                    values.add(value)

    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--sample-size", type=int, default=1000)
    parser.add_argument("--out", default="DBSR_implementation/generated/fiben/dbsr_official_fiben_csv_join_coverage.json")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    results = []

    for test in JOIN_TESTS:
        parent_path = data_dir / test["parent_file"]
        child_path = data_dir / test["child_file"]

        parent_values = collect_values(parent_path, test["parent_col"], args.sample_size)
        child_values = collect_value_set(child_path, test["child_col"])

        matched = sum(1 for value in parent_values if value in child_values)
        unmatched_examples = [value for value in parent_values if value not in child_values][:10]

        result = {
            "name": test["name"],
            "parent_file": test["parent_file"],
            "parent_col": test["parent_col"],
            "child_file": test["child_file"],
            "child_col": test["child_col"],
            "parent_sample_size": len(parent_values),
            "child_distinct_values": len(child_values),
            "matched": matched,
            "match_ratio": matched / len(parent_values) if parent_values else 0,
            "unmatched_examples": unmatched_examples,
        }

        results.append(result)

        print("=" * 80)
        print(result["name"])
        print(f"parent sample: {result['parent_sample_size']}")
        print(f"child distinct values: {result['child_distinct_values']}")
        print(f"matched: {result['matched']}")
        print(f"match_ratio: {result['match_ratio']:.4f}")
        print(f"unmatched examples: {result['unmatched_examples']}")

    output = {
        "dataset": "FIBEN",
        "source": "official_csv_files",
        "sample_size": args.sample_size,
        "results": results,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("=" * 80)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
