"""
Create manual column schemas for FIBEN headerless CSV files.

The FIBEN source files used here do not expose a reliable header row.
This script defines stable column names for the semantic views used by the
Lima & Mello physical plan and validates that all columns required by
the physical edges are present.

It does not load MongoDB.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


MANUAL_COLUMNS_BY_FILE_STEM: Dict[str, List[str]] = {
    "CORPORATION": [
        "CORPORATIONID",
        "ISCLASSIFIEDBY",
        "ISDOMICILEDIN",
        "TICKER",
        "NAME",
    ],
    "COUNTRY": [
        "COUNTRYID",
        "NAME",
        "REGIONID",
    ],
    "INDUSTRYSECTORCLASSIFICATIONSCHEME": [
        "INDUSTRYSECTORCLASSIFIERID",
        "NAME",
        "SCHEME",
    ],
    "LISTEDSECURITY": [
        "LISTEDSECURITYID",
        "ISPROVIDEDBY",
        "ISSUEDATE",
        "TICKER",
        "NAME",
    ],
    "SECURITY": [
        "LISTEDSECURITYID",
        "ISTRADEDON",
        "ISPROVIDEDBY",
    ],
    "PERSON": [
        "PERSONID",
        "COUNTRYID",
        "CITYID",
        "GENDER",
        "BIRTHDATE",
        "FULLNAME",
        "LASTNAME",
        "FIRSTNAME",
        "CITYNAME",
    ],
    "FINANCIALSERVICEACCOUNT": [
        "FINANCIALSERVICEACCOUNTID",
        "ISOWNEDBY",
        "ISFACILITATEDBY",
        "ACCOUNTNUMBER",
        "OPENEDON",
    ],
    "HOLDING": [
        "HOLDINGID",
        "ISHELDBY",
        "REFERSTO",
        "NAME",
        "QUANTITY",
    ],
    "SECURITIESTRANSACTION": [
        "SECURITIESTRANSACTIONID",
        "ISFACILITATEDBY",
        "EXECUTES",
        "REFERSTO",
        "TRANSACTIONTYPE",
        "TRANSACTIONDATETIME",
        "VALUE",
    ],
    "FINANCIALREPORT": [
        "FINANCIALREPORTID",
        "ISPROVIDEDBY",
        "HASUNIQUEIDENTIFIER",
    ],
    "ELEMENTSOFFINANCIALREPORT": [
        "ELEMENTSOFFINANCIALREPORTID",
        "ISMEMBEROF",
    ],
    "ELEMENTOFFINANCIALSTATEMENT": [
        "ELEMENTOFFINANCIALSTATEMENTID",
        "NAME",
        "STATEMENTTYPE",
    ],
    "DISCLOSURE": [
        "DISCLOSUREID",
        "YEAR",
        "PERIODENDDATE",
        "DOCUMENTTYPE",
        "FISCALPERIOD",
        "CURRENCY",
        "CONTEXTTYPE",
        "CONCEPT",
        "INSTANT_OR_DURATION",
        "ISNEGATED",
        "VALUE",
        "FISCALYEAR",
        "NAMESPACE",
        "HASUNIQUEIDENTIFIER",
        "PERIOD",
    ],
}


def json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if pd.isna(value):
        return None
    return str(value)


def file_stem_without_suffix(path: Path) -> str:
    name = path.name

    for suffix in [".csv.gz", ".tsv.gz", ".txt.gz", ".csv", ".tsv", ".txt"]:
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]

    return path.stem


def infer_delimiter(path: Path) -> str:
    candidates = [",", "|", ";", "\t"]
    best_sep = ","
    best_n_cols = 0

    for sep in candidates:
        try:
            df = pd.read_csv(
                path,
                header=None,
                nrows=5,
                sep=sep,
                compression="infer",
            )
            if len(df.columns) > best_n_cols:
                best_n_cols = len(df.columns)
                best_sep = sep
        except Exception:
            continue

    return best_sep


def detect_n_columns(path: Path, delimiter: str) -> int:
    df = pd.read_csv(
        path,
        header=None,
        nrows=5,
        sep=delimiter,
        compression="infer",
    )
    return int(len(df.columns))


def build_columns_for_file(path: Path, n_columns: int) -> List[str]:
    stem = file_stem_without_suffix(path).upper()
    manual = MANUAL_COLUMNS_BY_FILE_STEM.get(stem)

    if manual is None:
        return [f"COL_{i+1}" for i in range(n_columns)]

    columns = list(manual)

    if n_columns > len(columns):
        for i in range(len(columns), n_columns):
            columns.append(f"EXTRA_COL_{i+1}")

    return columns[:n_columns]


def build_column_schema_rows(mapping_df: pd.DataFrame) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    matched = mapping_df[mapping_df["status"] == "matched"].copy()

    for _, row in matched.iterrows():
        semantic_view = str(row["semantic_view"])
        file_path = Path(str(row["file_path"]))

        delimiter = infer_delimiter(file_path)
        n_columns = detect_n_columns(file_path, delimiter)
        columns = build_columns_for_file(file_path, n_columns)

        stem = file_stem_without_suffix(file_path).upper()
        manual_defined = stem in MANUAL_COLUMNS_BY_FILE_STEM

        for position, column_name in enumerate(columns):
            rows.append(
                {
                    "semantic_view": semantic_view,
                    "file_path": str(file_path),
                    "relative_file_path": row["relative_file_path"],
                    "file_name": file_path.name,
                    "file_stem": stem,
                    "has_header": False,
                    "delimiter": delimiter,
                    "n_detected_columns": n_columns,
                    "manual_schema_defined": manual_defined,
                    "column_position_zero_based": position,
                    "column_position_one_based": position + 1,
                    "column_name": column_name,
                }
            )

    return rows


def add_required(
    rows: List[Dict[str, Any]],
    semantic_view: Optional[str],
    required_column: Optional[str],
    relationship_name: str,
    role: str,
) -> None:
    if semantic_view is None or required_column is None:
        return

    if pd.isna(semantic_view) or pd.isna(required_column):
        return

    semantic_view = str(semantic_view)
    required_column = str(required_column)

    if not semantic_view or semantic_view.lower() == "nan":
        return

    if not required_column or required_column.lower() == "nan":
        return

    rows.append(
        {
            "semantic_view": semantic_view,
            "required_column": required_column,
            "relationship_name": relationship_name,
            "column_role": role,
        }
    )


def build_required_columns(edges_df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []

    for _, edge in edges_df.iterrows():
        rel = str(edge["relationship_name"])

        add_required(
            rows,
            edge.get("source_view"),
            edge.get("selected_source_column"),
            rel,
            "source_selected_column",
        )
        add_required(
            rows,
            edge.get("target_view"),
            edge.get("selected_target_column"),
            rel,
            "target_selected_column",
        )
        add_required(
            rows,
            edge.get("bridge_view"),
            edge.get("bridge_source_column"),
            rel,
            "bridge_source_column",
        )
        add_required(
            rows,
            edge.get("bridge_view"),
            edge.get("bridge_target_column"),
            rel,
            "bridge_target_column",
        )

    return pd.DataFrame(rows).drop_duplicates().reset_index(drop=True)


def validate_required_columns(
    required_df: pd.DataFrame,
    column_schema_df: pd.DataFrame,
) -> pd.DataFrame:
    available = set(
        zip(
            column_schema_df["semantic_view"].astype(str),
            column_schema_df["column_name"].astype(str),
        )
    )

    rows: List[Dict[str, Any]] = []

    for _, req in required_df.iterrows():
        semantic_view = str(req["semantic_view"])
        required_column = str(req["required_column"])
        status = (
            "present"
            if (semantic_view, required_column) in available
            else "missing"
        )

        rows.append(
            {
                "semantic_view": semantic_view,
                "required_column": required_column,
                "relationship_name": req["relationship_name"],
                "column_role": req["column_role"],
                "status": status,
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scale",
        default="sf1",
    )
    parser.add_argument(
        "--source-profile-dir",
        default="de_lima_mello_2015_implementation/generated/fiben/source_profile",
    )
    parser.add_argument(
        "--physical-plan-dir",
        default="de_lima_mello_2015_implementation/generated/fiben",
    )
    parser.add_argument(
        "--output-dir",
        default="de_lima_mello_2015_implementation/generated/fiben/source_profile",
    )
    args = parser.parse_args()

    source_profile_dir = Path(args.source_profile_dir) / args.scale
    physical_plan_dir = Path(args.physical_plan_dir)
    output_dir = Path(args.output_dir) / args.scale
    output_dir.mkdir(parents=True, exist_ok=True)

    mapping_path = source_profile_dir / f"lmm_fiben_source_file_mapping_{args.scale}.csv"
    edges_path = physical_plan_dir / "lmm_fiben_physical_edges.csv"

    if not mapping_path.exists():
        raise FileNotFoundError(f"Missing source mapping file: {mapping_path}")

    if not edges_path.exists():
        raise FileNotFoundError(f"Missing physical edges file: {edges_path}")

    mapping_df = pd.read_csv(mapping_path)
    edges_df = pd.read_csv(edges_path)

    if (mapping_df["status"] != "matched").any():
        unmatched = mapping_df.loc[mapping_df["status"] != "matched", "semantic_view"].tolist()
        raise RuntimeError(f"Unmatched semantic views remain: {unmatched}")

    column_schema_df = pd.DataFrame(build_column_schema_rows(mapping_df))
    required_df = build_required_columns(edges_df)
    validation_df = validate_required_columns(required_df, column_schema_df)

    missing_df = validation_df[validation_df["status"] != "present"].copy()

    column_schema_csv = output_dir / f"lmm_fiben_column_schema_{args.scale}.csv"
    required_columns_csv = output_dir / f"lmm_fiben_required_columns_{args.scale}.csv"
    validation_csv = output_dir / f"lmm_fiben_required_column_validation_{args.scale}.csv"
    report_json = output_dir / f"lmm_fiben_column_schema_report_{args.scale}.json"

    column_schema_df.to_csv(column_schema_csv, index=False)
    required_df.to_csv(required_columns_csv, index=False)
    validation_df.to_csv(validation_csv, index=False)

    report = {
        "status": "completed" if len(missing_df) == 0 else "completed_with_missing_required_columns",
        "scale": args.scale,
        "n_semantic_views": int(mapping_df["semantic_view"].nunique()),
        "n_column_schema_rows": int(len(column_schema_df)),
        "n_required_columns": int(len(required_df)),
        "n_missing_required_columns": int(len(missing_df)),
        "missing_required_columns": missing_df.to_dict(orient="records"),
        "manual_column_files": sorted(MANUAL_COLUMNS_BY_FILE_STEM.keys()),
        "output_files": {
            "column_schema_csv": str(column_schema_csv),
            "required_columns_csv": str(required_columns_csv),
            "required_column_validation_csv": str(validation_csv),
            "report_json": str(report_json),
        },
        "important_note": (
            "FIBEN source files are treated as headerless CSVs. "
            "Manual schemas are used to assign stable column names before materialization."
        ),
    }

    report_json.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=json_default),
        encoding="utf-8",
    )

    print("Generated FIBEN manual column schema.")
    print(f"Scale: {args.scale}")
    print(f"Semantic views: {mapping_df['semantic_view'].nunique()}")
    print(f"Column schema rows: {len(column_schema_df)}")
    print(f"Required columns: {len(required_df)}")
    print(f"Missing required columns: {len(missing_df)}")

    if len(missing_df):
        print("\nMissing required columns:")
        print(missing_df.to_string(index=False))

    print("\nValidation summary:")
    print(validation_df["status"].value_counts().to_string())

    print("\nOutput files:")
    for path in report["output_files"].values():
        print(f"  {path}")


if __name__ == "__main__":
    main()
