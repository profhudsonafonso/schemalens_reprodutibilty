"""
Import SchemaLens FIBEN artifacts into the de Lima & Mello baseline format.

This script does not recalculate cardinalities. It imports the relationship
join hints and observed cardinalities already produced by the SchemaLens FIBEN
methodology notebook.

Methodological choice:
- Main comparison mode keeps the same cardinality evidence used by SchemaLens.
- Low-confidence and no-match relationships are preserved with explicit flags.
- Corrections can be tested later as a sensitivity analysis, but not used in the
  main SchemaLens vs. Lima & Mello comparison.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd


REQUIRED_FILES = {
    "relationship_cardinality": "relationship_cardinality.csv",
    "join_hints": "fiben_relationship_join_hints.csv",
}

OPTIONAL_FILES = {
    "observed_cardinality_by_relationship": "observed_cardinality_by_relationship.csv",
    "cardinality_observed": "cardinality_observed.csv",
    "observed_cardinality_summary": "observed_cardinality_summary.csv",
    "low_confidence_relationships": "low_confidence_cardinality_relationships.csv",
    "no_match_relationships": "no_match_cardinality_relationships.csv",
    "relationship_semantics": "relationship_semantics.csv",
    "semantic_relationships": "semantic_relationships.csv",
    "relationship_semantic_profile": "relationship_semantic_profile.csv",
    "relationship_sharedness": "relationship_sharedness.csv",
    "sharedness_observed": "sharedness_observed.csv",
    "observed_sharedness_by_relationship": "observed_sharedness_by_relationship.csv",
    "query_sharedness_profile": "query_sharedness_profile.csv",
    "final_document_variable_matrix": "final_document_variable_matrix.csv",
    "activation_input_matrix": "activation_input_matrix.csv",
    "document_variable_matrix_for_activation": "document_variable_matrix_for_activation.csv",
}


def find_file(input_dir: Path, filename: str) -> Optional[Path]:
    matches = sorted(input_dir.rglob(filename))
    if not matches:
        return None
    return matches[0]


def read_csv_if_exists(path: Optional[Path]) -> Optional[pd.DataFrame]:
    if path is None or not path.exists():
        return None
    return pd.read_csv(path)


def as_float(value: Any) -> Optional[float]:
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_divide(num: Any, den: Any) -> Optional[float]:
    num_f = as_float(num)
    den_f = as_float(den)
    if num_f is None or den_f is None or den_f == 0:
        return None
    return num_f / den_f


def derive_lmm_average_cardinalities(row: pd.Series) -> Dict[str, Optional[float]]:
    """
    Derive directional Avg values for the Lima & Mello format.

    For direct FK-style hints:
    - source_to_target is estimated as joined_rows / source_non_null_rows.
      This is usually close to 1 when the source has a FK to the target.
    - target_to_source is estimated as joined_rows / joined_distinct_target_keys.

    For bridge hints:
    - both directions are estimated from joined rows and distinct source/target keys.

    For subtype aliases:
    - both directions are treated as 1.0 when a 1:1 match was observed.

    If the SchemaLens artifact reports no observed match, the Avg values remain null.
    This preserves the original evidence instead of inventing new cardinalities.
    """
    observed_cardinality = str(row.get("observed_cardinality", ""))
    hint_type = str(row.get("hint_type", ""))
    joined_rows = as_float(row.get("joined_rows"))

    if joined_rows is None or joined_rows <= 0 or observed_cardinality == "no_observed_matches":
        return {
            "avg_source_to_target": None,
            "avg_target_to_source": None,
            "avg_derivation_method": "not_derived_no_observed_match",
        }

    if hint_type == "subtype_alias" or observed_cardinality == "observed_1_to_1":
        return {
            "avg_source_to_target": 1.0,
            "avg_target_to_source": 1.0,
            "avg_derivation_method": "subtype_or_observed_1_to_1",
        }

    if hint_type == "direct":
        return {
            "avg_source_to_target": safe_divide(
                row.get("joined_rows"),
                row.get("source_non_null_rows"),
            ),
            "avg_target_to_source": safe_divide(
                row.get("joined_rows"),
                row.get("joined_distinct_target_keys"),
            ),
            "avg_derivation_method": "direct_fk_observed_join",
        }

    if hint_type == "bridge":
        return {
            "avg_source_to_target": safe_divide(
                row.get("joined_rows"),
                row.get("joined_distinct_source_keys"),
            ),
            "avg_target_to_source": safe_divide(
                row.get("joined_rows"),
                row.get("joined_distinct_target_keys"),
            ),
            "avg_derivation_method": "bridge_observed_join",
        }

    return {
        "avg_source_to_target": safe_divide(
            row.get("joined_rows"),
            row.get("joined_distinct_source_keys"),
        ),
        "avg_target_to_source": safe_divide(
            row.get("joined_rows"),
            row.get("joined_distinct_target_keys"),
        ),
        "avg_derivation_method": "generic_observed_join",
    }


def classify_lmm_confidence(row: pd.Series) -> str:
    hint_confidence = str(row.get("hint_confidence", "")).lower()
    observed_cardinality = str(row.get("observed_cardinality", ""))
    computation_status = str(row.get("computation_status", ""))

    if computation_status != "computed":
        return "needs_review_not_computed"

    if observed_cardinality == "no_observed_matches":
        return "needs_review_no_observed_match"

    if hint_confidence in {"low", "medium"}:
        return f"needs_review_{hint_confidence}_hint_confidence"

    return "high_confidence_observed"


def build_avg_cardinality_json(imported_df: pd.DataFrame) -> Dict[str, Any]:
    avg_cardinalities: Dict[str, float] = {}
    confidence: Dict[str, Dict[str, Any]] = {}

    for _, row in imported_df.iterrows():
        relationship = row["relationship_name"]
        source = row["source_entity"]
        target = row["target_entity"]

        source_to_target_key = f"{source}|{relationship}|{target}"
        target_to_source_key = f"{target}|{relationship}|{source}"

        avg_st = as_float(row.get("avg_source_to_target"))
        avg_ts = as_float(row.get("avg_target_to_source"))

        if avg_st is not None:
            avg_cardinalities[source_to_target_key] = avg_st

        if avg_ts is not None:
            avg_cardinalities[target_to_source_key] = avg_ts

        confidence[relationship] = {
            "source_entity": source,
            "target_entity": target,
            "observed_cardinality": row.get("observed_cardinality"),
            "hint_confidence": row.get("hint_confidence"),
            "lmm_confidence_status": row.get("lmm_confidence_status"),
            "avg_derivation_method": row.get("avg_derivation_method"),
        }

    return {
        "methodological_mode": "schemalens_artifact_consistent",
        "description": (
            "Avg values derived from SchemaLens FIBEN observed cardinality artifacts. "
            "No low-confidence relationship was corrected in the main comparison mode."
        ),
        "avg_cardinalities": avg_cardinalities,
        "relationship_confidence": confidence,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        default="de_lima_mello_2015_implementation/generated/fiben/schemalens_artifacts",
        help="Directory containing extracted SchemaLens FIBEN CSV artifacts.",
    )
    parser.add_argument(
        "--output-dir",
        default="de_lima_mello_2015_implementation/generated/fiben",
        help="Directory where Lima & Mello normalized artifacts will be written.",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    discovered: Dict[str, Optional[str]] = {}

    required_paths: Dict[str, Path] = {}
    for key, filename in REQUIRED_FILES.items():
        path = find_file(input_dir, filename)
        discovered[key] = str(path) if path else None
        if path is None:
            raise FileNotFoundError(
                f"Required artifact not found: {filename} under {input_dir}"
            )
        required_paths[key] = path

    optional_paths: Dict[str, Optional[Path]] = {}
    for key, filename in OPTIONAL_FILES.items():
        path = find_file(input_dir, filename)
        optional_paths[key] = path
        discovered[key] = str(path) if path else None

    relationship_cardinality_df = pd.read_csv(required_paths["relationship_cardinality"])
    join_hints_df = pd.read_csv(required_paths["join_hints"])

    avg_rows = []
    for _, row in relationship_cardinality_df.iterrows():
        avg_rows.append(derive_lmm_average_cardinalities(row))

    avg_df = pd.DataFrame(avg_rows)

    imported_df = pd.concat(
        [
            relationship_cardinality_df.reset_index(drop=True),
            avg_df.reset_index(drop=True),
        ],
        axis=1,
    )

    imported_df["lmm_confidence_status"] = imported_df.apply(
        classify_lmm_confidence,
        axis=1,
    )

    imported_df["use_in_main_comparison"] = True
    imported_df["comparison_mode"] = "schemalens_artifact_consistent"

    preferred_columns = [
        "relationship_name",
        "edge_id",
        "semantic_type",
        "source_entity",
        "target_entity",
        "hint_type",
        "hint_confidence",
        "observed_cardinality",
        "computation_status",
        "lmm_confidence_status",
        "avg_source_to_target",
        "avg_target_to_source",
        "avg_derivation_method",
        "source_view",
        "target_view",
        "bridge_view",
        "selected_source_column",
        "selected_target_column",
        "bridge_source_column",
        "bridge_target_column",
        "source_non_null_rows",
        "target_non_null_rows",
        "source_distinct_keys",
        "target_distinct_keys",
        "joined_rows",
        "joined_distinct_source_keys",
        "joined_distinct_target_keys",
        "notes",
        "use_in_main_comparison",
        "comparison_mode",
    ]

    existing_preferred = [c for c in preferred_columns if c in imported_df.columns]
    remaining = [c for c in imported_df.columns if c not in existing_preferred]
    imported_df = imported_df[existing_preferred + remaining]

    low_confidence_df = imported_df[
        imported_df["lmm_confidence_status"] != "high_confidence_observed"
    ].copy()

    imported_csv = output_dir / "lmm_fiben_relationship_cardinalities.csv"
    low_conf_csv = output_dir / "lmm_fiben_low_confidence_relationships.csv"
    join_hints_csv = output_dir / "lmm_fiben_relationship_join_hints_imported.csv"
    avg_json_path = output_dir / "lmm_fiben_avg_cardinalities.json"
    report_json_path = output_dir / "lmm_fiben_artifact_import_report.json"

    imported_df.to_csv(imported_csv, index=False)
    low_confidence_df.to_csv(low_conf_csv, index=False)
    join_hints_df.to_csv(join_hints_csv, index=False)

    avg_payload = build_avg_cardinality_json(imported_df)
    avg_json_path.write_text(
        json.dumps(avg_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    optional_summary: Dict[str, Dict[str, Any]] = {}
    for key, path in optional_paths.items():
        df = read_csv_if_exists(path)
        optional_summary[key] = {
            "path": str(path) if path else None,
            "exists": path is not None,
            "rows": int(len(df)) if df is not None else None,
            "columns": list(df.columns) if df is not None else None,
        }

    report = {
        "status": "completed",
        "methodological_mode": "schemalens_artifact_consistent",
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "discovered_artifacts": discovered,
        "n_relationships_imported": int(len(imported_df)),
        "n_low_confidence_or_no_match_relationships": int(len(low_confidence_df)),
        "confidence_status_counts": imported_df["lmm_confidence_status"]
        .value_counts(dropna=False)
        .to_dict(),
        "observed_cardinality_counts": imported_df["observed_cardinality"]
        .value_counts(dropna=False)
        .to_dict(),
        "output_files": {
            "relationship_cardinalities_csv": str(imported_csv),
            "low_confidence_relationships_csv": str(low_conf_csv),
            "join_hints_imported_csv": str(join_hints_csv),
            "avg_cardinalities_json": str(avg_json_path),
            "report_json": str(report_json_path),
        },
        "optional_artifacts": optional_summary,
        "main_comparison_rule": (
            "Do not correct low-confidence/no-match cardinalities in the main "
            "SchemaLens vs. Lima & Mello comparison. Preserve them as imported "
            "evidence and flag them for interpretation."
        ),
    }

    report_json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("Imported SchemaLens FIBEN artifacts for Lima & Mello.")
    print(f"Relationships imported: {len(imported_df)}")
    print(f"Needs-review relationships: {len(low_confidence_df)}")
    print("\nConfidence status counts:")
    print(imported_df["lmm_confidence_status"].value_counts(dropna=False).to_string())
    print("\nOutput files:")
    for path in report["output_files"].values():
        print(f"  {path}")


if __name__ == "__main__":
    main()
