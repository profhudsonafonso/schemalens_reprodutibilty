#!/usr/bin/env python3
from pathlib import Path
import csv


def repo_root_from_script() -> Path:
    # This script is expected at: analysis/scripts/merge_qg9_query_plan_results.py
    return Path(__file__).resolve().parents[2]


REPO_ROOT = repo_root_from_script()

BASE_DIR = (
    REPO_ROOT
    / "analysis"
    / "generated"
    / "query_plan"
    / "imdb"
    / "qg9_validation"
)

SUMMARY_INPUTS = [
    BASE_DIR / "query_plan_summary_results_qg9_sf025_sf050.csv",
    BASE_DIR / "query_plan_summary_results_qg9_sf1.csv",
]

COMPONENT_INPUTS = [
    BASE_DIR / "query_plan_component_results_qg9_sf025_sf050.csv",
    BASE_DIR / "query_plan_component_results_qg9_sf1.csv",
]

STATUS_INPUTS = [
    BASE_DIR / "query_plan_status_summary_qg9_sf025_sf050.csv",
    BASE_DIR / "query_plan_status_summary_qg9_sf1.csv",
]

SUMMARY_OUTPUT = BASE_DIR / "query_plan_summary_qg9_all_sfs.csv"
COMPONENT_OUTPUT = BASE_DIR / "query_plan_components_qg9_all_sfs.csv"
STATUS_OUTPUT = BASE_DIR / "query_plan_status_summary_qg9_all_sfs.csv"


def read_csv_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    return fieldnames, rows


def write_union_csv(paths, output_path: Path, deduplicate=False, key_cols=None):
    all_rows = []
    all_fields = []

    for path in paths:
        if not path.exists():
            print(f"[WARN] Missing file: {path}")
            continue

        fields, rows = read_csv_rows(path)
        print(f"[INFO] Read {len(rows)} rows from {path.name}")

        for field in fields:
            if field not in all_fields:
                all_fields.append(field)

        all_rows.extend(rows)

    if not all_rows:
        print(f"[WARN] No rows found. Skipping output: {output_path.name}")
        return

    if deduplicate:
        if not key_cols:
            raise ValueError("key_cols must be provided when deduplicate=True")

        dedup = {}
        for row in all_rows:
            key = tuple(row.get(col, "") for col in key_cols)
            dedup[key] = row
        all_rows = list(dedup.values())

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"[OK] Saved {len(all_rows)} rows to {output_path}")


def main():
    print(f"[INFO] Repository root: {REPO_ROOT}")
    print(f"[INFO] Base directory: {BASE_DIR}")

    if not BASE_DIR.exists():
        raise SystemExit(f"[ERROR] Folder not found: {BASE_DIR}")

    write_union_csv(
        paths=SUMMARY_INPUTS,
        output_path=SUMMARY_OUTPUT,
        deduplicate=True,
        key_cols=[
            "experiment_id",
            "scale_label",
            "config_name",
            "query_name",
            "run_phase",
            "repetition",
        ],
    )

    write_union_csv(
        paths=COMPONENT_INPUTS,
        output_path=COMPONENT_OUTPUT,
        deduplicate=False,
    )

    write_union_csv(
        paths=STATUS_INPUTS,
        output_path=STATUS_OUTPUT,
        deduplicate=False,
    )


if __name__ == "__main__":
    main()