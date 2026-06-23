#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Set


CANDIDATE_FILES = [
    "ELEMENTOFFINANCIALSTATEMENT.csv",
    "MONETARYAMOUNT.csv",
    "FINANCIALREPORT.csv",
    "ELEMENTSOFFINANCIALREPORT.csv",
]


def sample_values(path: Path, col_idx: int, sample_size: int) -> List[str]:
    values = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)
        for row_idx, row in enumerate(reader, start=1):
            if sample_size > 0 and row_idx > sample_size:
                break
            if col_idx < len(row) and row[col_idx] != "":
                values.append(row[col_idx])
    return values


def all_values(path: Path, col_idx: int) -> Set[str]:
    values = set()
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if col_idx < len(row) and row[col_idx] != "":
                values.add(row[col_idx])
    return values


def max_cols(path: Path, sample_rows: int = 100) -> int:
    max_len = 0
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader, start=1):
            if idx > sample_rows:
                break
            max_len = max(max_len, len(row))
    return max_len


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--sample-size", type=int, default=1000)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    report_file = data_dir / "ELEMENTSOFFINANCIALREPORT.csv"
    report_col0 = sample_values(report_file, 0, args.sample_size)
    report_col1 = sample_values(report_file, 1, args.sample_size)

    print("ReportElement file:", report_file)
    print("ReportElement col0 sample:", report_col0[:10])
    print("ReportElement col1 sample:", report_col1[:10])
    print()

    for source_name, source_values in [
        ("ELEMENTSOFFINANCIALREPORT.col0", report_col0),
        ("ELEMENTSOFFINANCIALREPORT.col1", report_col1),
    ]:
        print("=" * 100)
        print("Source:", source_name)
        print("Source sample size:", len(source_values))

        for file_name in CANDIDATE_FILES:
            path = data_dir / file_name
            if not path.exists():
                print("Missing:", file_name)
                continue

            ncols = max_cols(path)

            for col_idx in range(ncols):
                target_values = all_values(path, col_idx)
                matched = sum(1 for value in source_values if value in target_values)
                ratio = matched / len(source_values) if source_values else 0

                if matched > 0:
                    print(
                        f"{source_name} -> {file_name}.col{col_idx}: "
                        f"matched={matched}, ratio={ratio:.4f}, "
                        f"target_distinct={len(target_values)}"
                    )


if __name__ == "__main__":
    main()
