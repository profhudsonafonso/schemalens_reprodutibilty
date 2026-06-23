#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def sample_values(path: Path, col_idx: int, sample_size: int) -> list[str]:
    values = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)
        for row_idx, row in enumerate(reader, start=1):
            if sample_size > 0 and row_idx > sample_size:
                break
            if col_idx < len(row) and row[col_idx]:
                values.append(row[col_idx])
    return values


def scan_file(path: Path, source_values: set[str], max_rows: int = 0) -> list[dict]:
    matches = []
    max_cols = 0
    col_matches = {}

    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)

        for row_idx, row in enumerate(reader, start=1):
            if max_rows > 0 and row_idx > max_rows:
                break

            max_cols = max(max_cols, len(row))

            for idx, value in enumerate(row):
                if value in source_values:
                    col_matches[idx] = col_matches.get(idx, 0) + 1

    for col_idx, count in sorted(col_matches.items()):
        matches.append({
            "file": str(path),
            "column": col_idx,
            "matches": count,
        })

    return matches


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--sample-size", type=int, default=1000)
    parser.add_argument("--scan-max-rows", type=int, default=0)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    source_file = data_dir / "ELEMENTSOFFINANCIALREPORT.csv"

    source_values = set(sample_values(source_file, 0, args.sample_size))

    print(f"Source file: {source_file}")
    print(f"Source values sampled: {len(source_values)}")
    print("First values:", list(source_values)[:10])
    print("=" * 100)

    all_matches = []

    for path in sorted(data_dir.glob("*.csv")):
        matches = scan_file(path, source_values, max_rows=args.scan_max_rows)

        for match in matches:
            all_matches.append(match)
            print(
                f"{Path(match['file']).name}.col{match['column']} "
                f"matches={match['matches']}"
            )

    print("=" * 100)
    print(f"Total matching file/column pairs: {len(all_matches)}")


if __name__ == "__main__":
    main()
