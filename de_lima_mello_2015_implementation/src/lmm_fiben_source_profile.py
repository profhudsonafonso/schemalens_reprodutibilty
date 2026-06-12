"""
Profile FIBEN source CSV files for the Lima & Mello MongoDB materialization.

This script does not load MongoDB.

It maps the semantic/source views used by the Lima & Mello physical plan
(e.g., fiben_corporations, fiben_reports, fiben_transactions) to actual CSV
files in a FIBEN data directory.

The output is used by the later MongoDB materialization script.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd


DEFAULT_VIEW_CANDIDATES: Dict[str, List[str]] = {
    "fiben_corporations": [
        "corporations",
        "corporation",
        "companies",
        "company",
        "corp",
    ],
    "fiben_industries": [
        "industries",
        "industry",
        "industry_classifications",
        "industry_classification",
    ],
    "fiben_countries": [
        "countries",
        "country",
    ],
    "fiben_securities": [
        "securities",
        "security",
    ],
    "fiben_listed_securities": [
        "listed_securities",
        "listed_security",
        "listedsecurity",
        "listedsecurities",
    ],
    "fiben_persons": [
        "persons",
        "person",
    ],
    "fiben_financial_service_accounts": [
        "financial_service_accounts",
        "financialserviceaccounts",
        "financial_service_account",
        "accounts",
        "account",
    ],
    "fiben_holdings": [
        "holdings",
        "holding",
    ],
    "fiben_transactions": [
        "transactions",
        "transaction",
        "securities_transactions",
        "securities_transaction",
        "security_transactions",
        "security_transaction",
    ],
    "fiben_buy_transactions": [
        "buy_transactions",
        "buy_transaction",
        "buytransactions",
        "buytransaction",
    ],
    "fiben_sell_transactions": [
        "sell_transactions",
        "sell_transaction",
        "selltransactions",
        "selltransaction",
    ],
    "fiben_reports": [
        "reports",
        "report",
        "financial_reports",
        "financial_report",
        "filings",
        "filing",
    ],
    "fiben_report_elements": [
        "report_elements",
        "report_element",
        "reportelements",
        "reportelement",
    ],
    "fiben_statement_elements": [
        "statement_elements",
        "statement_element",
        "statementelements",
        "statementelement",
    ],
    "fiben_disclosures": [
        "disclosures",
        "disclosure",
    ],
}


FIBEN_EXACT_VIEW_FILE_OVERRIDES: Dict[str, str] = {
    # Conceptual subtypes over the same physical transaction CSV.
    "fiben_buy_transactions": "SECURITIESTRANSACTION",
    "fiben_sell_transactions": "SECURITIESTRANSACTION",

    # Conceptual financial-report element aliases.
    "fiben_report_elements": "ELEMENTSOFFINANCIALREPORT",
    "fiben_statement_elements": "ELEMENTOFFINANCIALSTATEMENT",
}


def json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if pd.isna(value):
        return None
    return str(value)


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "", str(value).lower())


def discover_data_files(data_dir: Path) -> List[Path]:
    allowed_suffixes = {
        ".csv",
        ".tsv",
        ".txt",
        ".gz",
    }

    files: List[Path] = []

    for path in data_dir.rglob("*"):
        if not path.is_file():
            continue

        name = path.name.lower()

        if name.endswith(".csv") or name.endswith(".tsv") or name.endswith(".txt"):
            files.append(path)
        elif name.endswith(".csv.gz") or name.endswith(".tsv.gz") or name.endswith(".txt.gz"):
            files.append(path)
        elif path.suffix.lower() in allowed_suffixes:
            files.append(path)

    return sorted(files)


def stem_without_compression(path: Path) -> str:
    name = path.name

    for suffix in [".csv.gz", ".tsv.gz", ".txt.gz", ".csv", ".tsv", ".txt"]:
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]

    return path.stem


def read_csv_header(path: Path) -> Tuple[List[str], str]:
    """
    Read only the header and infer a delimiter.

    The function tries common delimiters and returns the version with the
    largest number of columns.
    """
    delimiters = [",", "|", ";", "\t"]
    best_columns: List[str] = []
    best_delimiter = ","

    for sep in delimiters:
        try:
            df = pd.read_csv(path, nrows=0, sep=sep, compression="infer")
            cols = [str(c) for c in df.columns]
            if len(cols) > len(best_columns):
                best_columns = cols
                best_delimiter = sep
        except Exception:
            continue

    return best_columns, best_delimiter


def count_rows_fast(path: Path) -> Optional[int]:
    """
    Count data rows by line count.

    This can be expensive for large SF10/SF30 files, so use only when requested.
    """
    try:
        if path.name.lower().endswith(".gz"):
            import gzip

            with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
                n_lines = sum(1 for _ in f)
        else:
            with path.open("rt", encoding="utf-8", errors="ignore") as f:
                n_lines = sum(1 for _ in f)

        return max(n_lines - 1, 0)
    except Exception:
        return None


def build_available_file_index(files: Iterable[Path]) -> Dict[str, Path]:
    index: Dict[str, Path] = {}

    for path in files:
        normalized = normalize_name(stem_without_compression(path))
        if normalized not in index:
            index[normalized] = path

    return index


def resolve_view_to_file(
    view_name: str,
    available_index: Dict[str, Path],
) -> Tuple[Optional[Path], str, List[str]]:
    candidates = DEFAULT_VIEW_CANDIDATES.get(view_name, [])

    # Exact semantic-view-to-file override.
    # This handles FIBEN conceptual aliases whose physical CSV name is not
    # similar to the semantic view name.
    override = FIBEN_EXACT_VIEW_FILE_OVERRIDES.get(view_name)
    if override is not None:
        normalized_override = normalize_name(override)
        if normalized_override in available_index:
            return (
                available_index[normalized_override],
                "exact_fiben_override_match",
                candidates + [override],
            )

    normalized_candidates = [normalize_name(c) for c in candidates]
    normalized_view_without_prefix = normalize_name(
        view_name.replace("fiben_", "")
    )

    all_candidates = normalized_candidates + [normalized_view_without_prefix]

    # Exact match first.
    for candidate in all_candidates:
        if candidate in available_index:
            return available_index[candidate], "exact_candidate_match", candidates

    # Conservative fallback: view candidate must fully appear in the file stem,
    # but avoid mapping listed_securities to securities by checking longer names first.
    sorted_candidates = sorted(set(all_candidates), key=len, reverse=True)

    for candidate in sorted_candidates:
        for normalized_stem, path in available_index.items():
            if candidate and candidate in normalized_stem:
                return path, "substring_candidate_match", candidates

    return None, "unmatched", candidates

def collect_required_views(input_dir: Path) -> List[str]:
    """
    Collect source/target/bridge views from the physical edge plan.
    """
    edges_path = input_dir / "lmm_fiben_physical_edges.csv"

    if not edges_path.exists():
        raise FileNotFoundError(f"Missing physical edges file: {edges_path}")

    edges_df = pd.read_csv(edges_path)

    view_columns = ["source_view", "target_view", "bridge_view"]

    views = set()

    for col in view_columns:
        if col in edges_df.columns:
            for value in edges_df[col].dropna().astype(str):
                if value and value.lower() != "nan":
                    views.add(value)

    # Add all known candidates to support root-only collections too.
    views.update(DEFAULT_VIEW_CANDIDATES.keys())

    return sorted(views)


def build_mapping_rows(
    required_views: List[str],
    available_index: Dict[str, Path],
    data_dir: Path,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for view_name in required_views:
        path, status, candidates = resolve_view_to_file(view_name, available_index)

        rows.append(
            {
                "semantic_view": view_name,
                "status": "matched" if path else "unmatched",
                "match_strategy": status,
                "file_path": str(path) if path else None,
                "relative_file_path": str(path.relative_to(data_dir)) if path else None,
                "candidate_aliases": candidates,
            }
        )

    return rows


def build_profile_rows(
    mapping_df: pd.DataFrame,
    count_rows: bool,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    matched_df = mapping_df[mapping_df["status"] == "matched"].copy()

    for _, row in matched_df.iterrows():
        path = Path(str(row["file_path"]))

        columns, delimiter = read_csv_header(path)

        rows.append(
            {
                "semantic_view": row["semantic_view"],
                "file_path": str(path),
                "file_name": path.name,
                "file_size_bytes": path.stat().st_size if path.exists() else None,
                "delimiter": delimiter,
                "n_columns": len(columns),
                "columns": columns,
                "n_rows": count_rows_fast(path) if count_rows else None,
                "row_count_policy": "counted" if count_rows else "not_counted",
            }
        )

    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        required=True,
        help="FIBEN source data directory, e.g. /home/hudson/Documents/framework_test/fiben/data full",
    )
    parser.add_argument(
        "--input-dir",
        default="de_lima_mello_2015_implementation/generated/fiben",
    )
    parser.add_argument(
        "--output-dir",
        default="de_lima_mello_2015_implementation/generated/fiben/source_profile",
    )
    parser.add_argument(
        "--scale",
        default="sf1",
        help="Scale label used in output filenames.",
    )
    parser.add_argument(
        "--count-rows",
        action="store_true",
        help="Count rows by scanning files. Useful for SF1, but may be slow for large scales.",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    input_dir = Path(args.input_dir)
    output_base = Path(args.output_dir)
    output_dir = output_base / args.scale
    output_dir.mkdir(parents=True, exist_ok=True)

    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    files = discover_data_files(data_dir)
    available_index = build_available_file_index(files)
    required_views = collect_required_views(input_dir)

    mapping_rows = build_mapping_rows(
        required_views=required_views,
        available_index=available_index,
        data_dir=data_dir,
    )

    mapping_df = pd.DataFrame(mapping_rows)

    profile_rows = build_profile_rows(
        mapping_df=mapping_df,
        count_rows=args.count_rows,
    )

    profile_df = pd.DataFrame(profile_rows)

    discovered_files_df = pd.DataFrame(
        [
            {
                "file_path": str(path),
                "relative_file_path": str(path.relative_to(data_dir)),
                "file_name": path.name,
                "normalized_stem": normalize_name(stem_without_compression(path)),
                "file_size_bytes": path.stat().st_size,
            }
            for path in files
        ]
    )

    mapping_csv = output_dir / f"lmm_fiben_source_file_mapping_{args.scale}.csv"
    profile_csv = output_dir / f"lmm_fiben_source_table_profile_{args.scale}.csv"
    discovered_csv = output_dir / f"lmm_fiben_discovered_source_files_{args.scale}.csv"
    report_json = output_dir / f"lmm_fiben_source_profile_report_{args.scale}.json"

    mapping_df.to_csv(mapping_csv, index=False)
    profile_df.to_csv(profile_csv, index=False)
    discovered_files_df.to_csv(discovered_csv, index=False)

    unmatched = mapping_df[mapping_df["status"] != "matched"].copy()

    report = {
        "status": "completed",
        "scale": args.scale,
        "data_dir": str(data_dir),
        "n_discovered_files": int(len(discovered_files_df)),
        "n_required_views": int(len(mapping_df)),
        "n_matched_views": int((mapping_df["status"] == "matched").sum()),
        "n_unmatched_views": int(len(unmatched)),
        "unmatched_views": unmatched["semantic_view"].tolist(),
        "count_rows": bool(args.count_rows),
        "output_files": {
            "source_file_mapping_csv": str(mapping_csv),
            "source_table_profile_csv": str(profile_csv),
            "discovered_source_files_csv": str(discovered_csv),
            "report_json": str(report_json),
        },
        "next_step": (
            "If all required views are matched, run the MongoDB materialization script. "
            "If some views are unmatched, add aliases to DEFAULT_VIEW_CANDIDATES."
        ),
    }

    report_json.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=json_default),
        encoding="utf-8",
    )

    print("Generated FIBEN source profile for Lima & Mello materialization.")
    print(f"Scale: {args.scale}")
    print(f"Discovered files: {len(discovered_files_df)}")
    print(f"Required views: {len(mapping_df)}")
    print(f"Matched views: {(mapping_df['status'] == 'matched').sum()}")
    print(f"Unmatched views: {len(unmatched)}")

    if len(unmatched):
        print("\nUnmatched views:")
        print(unmatched[["semantic_view", "candidate_aliases"]].to_string(index=False))

    print("\nMatched mapping:")
    print(mapping_df[["semantic_view", "status", "match_strategy", "relative_file_path"]].to_string(index=False))

    print("\nOutput files:")
    for path in report["output_files"].values():
        print(f"  {path}")


if __name__ == "__main__":
    main()
