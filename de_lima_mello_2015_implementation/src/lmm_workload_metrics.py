"""
Compute Lima & Mello workload metrics for FIBEN.

This script computes:
- access volume v(o_i, t_j);
- GAF(t), General Access Frequency;
- MAF, Minimal Access Frequency;
- concept relevance according to GAF >= MAF.

Inputs:
- lmm_fiben_workload_access_paths.csv
- lmm_fiben_relationship_cardinalities.csv

Methodological mode:
- Main comparison keeps SchemaLens artifact-consistent cardinalities.
- Missing/no-observed cardinalities are not corrected.
- They receive fallback multiplier 1.0 and are explicitly flagged.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


SUBTYPE_TO_SUPERTYPE = {
    "BuyTransaction": "Transaction",
    "SellTransaction": "Transaction",
}


def resolve_supertype(entity_name: Optional[str]) -> Optional[str]:
    if entity_name is None:
        return None
    return SUBTYPE_TO_SUPERTYPE.get(entity_name, entity_name)


def as_float(value: Any) -> Optional[float]:
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if pd.isna(value):
        return None
    return str(value)


def build_relationship_lookup(cardinality_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}

    for _, row in cardinality_df.iterrows():
        relationship_name = str(row["relationship_name"])
        lookup[relationship_name] = row.to_dict()

    return lookup


def find_directional_avg(
    relationship_lookup: Dict[str, Dict[str, Any]],
    relationship_name: str,
    from_entity: str,
    to_entity: str,
    fallback_multiplier: float,
) -> Tuple[float, str, Optional[str], Optional[str]]:
    """
    Return the directional Avg multiplier for from_entity --relationship--> to_entity.

    If a relationship is defined on a superclass, a subtype such as
    BuyTransaction or SellTransaction is resolved to Transaction. This preserves
    EER inheritance semantics without changing the workload access path.
    """
    rel = relationship_lookup.get(relationship_name)

    if rel is None:
        return (
            fallback_multiplier,
            "relationship_not_found_fallback",
            None,
            None,
        )

    source = str(rel.get("source_entity"))
    target = str(rel.get("target_entity"))
    confidence_status = rel.get("lmm_confidence_status")
    observed_cardinality = rel.get("observed_cardinality")

    # Direct match.
    if from_entity == source and to_entity == target:
        avg = as_float(rel.get("avg_source_to_target"))
        if avg is None:
            return (
                fallback_multiplier,
                "missing_source_to_target_avg_fallback_1_0",
                confidence_status,
                observed_cardinality,
            )
        return (
            avg,
            "observed_source_to_target_avg",
            confidence_status,
            observed_cardinality,
        )

    if from_entity == target and to_entity == source:
        avg = as_float(rel.get("avg_target_to_source"))
        if avg is None:
            return (
                fallback_multiplier,
                "missing_target_to_source_avg_fallback_1_0",
                confidence_status,
                observed_cardinality,
            )
        return (
            avg,
            "observed_target_to_source_avg",
            confidence_status,
            observed_cardinality,
        )

    # Inheritance-aware match.
    resolved_from = resolve_supertype(from_entity)
    resolved_to = resolve_supertype(to_entity)

    if resolved_from == source and resolved_to == target:
        avg = as_float(rel.get("avg_source_to_target"))
        if avg is None:
            return (
                fallback_multiplier,
                "missing_source_to_target_avg_via_supertype_fallback_1_0",
                confidence_status,
                observed_cardinality,
            )
        return (
            avg,
            "observed_source_to_target_avg_via_supertype",
            confidence_status,
            observed_cardinality,
        )

    if resolved_from == target and resolved_to == source:
        avg = as_float(rel.get("avg_target_to_source"))
        if avg is None:
            return (
                fallback_multiplier,
                "missing_target_to_source_avg_via_supertype_fallback_1_0",
                confidence_status,
                observed_cardinality,
            )
        return (
            avg,
            "observed_target_to_source_avg_via_supertype",
            confidence_status,
            observed_cardinality,
        )

    return (
        fallback_multiplier,
        "relationship_endpoint_mismatch_fallback",
        confidence_status,
        observed_cardinality,
    )

def compute_access_volumes(
    access_paths_df: pd.DataFrame,
    relationship_lookup: Dict[str, Dict[str, Any]],
    fallback_multiplier: float = 1.0,
) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []

    required_columns = {
        "operation_name",
        "query_id",
        "operation_kind",
        "frequency",
        "step_order",
        "conceptual_type",
        "type_kind",
    }

    missing = required_columns - set(access_paths_df.columns)
    if missing:
        raise ValueError(f"Missing required columns in access paths file: {sorted(missing)}")

    grouped = access_paths_df.sort_values(
        ["operation_name", "step_order"]
    ).groupby("operation_name", sort=False)

    for operation_name, op_df in grouped:
        op_df = op_df.sort_values("step_order").reset_index(drop=True)

        previous_volume: Optional[float] = None

        for idx, step in op_df.iterrows():
            frequency = as_float(step["frequency"])
            if frequency is None:
                raise ValueError(f"Invalid frequency for operation {operation_name}")

            conceptual_type = str(step["conceptual_type"])
            type_kind = str(step["type_kind"])
            query_id = str(step["query_id"])
            operation_kind = str(step["operation_kind"])

            multiplier = 1.0
            multiplier_status = "first_step_frequency"
            relationship_confidence_status = None
            observed_cardinality = None
            from_entity = None
            to_entity = None
            relationship_name = None

            if idx == 0:
                access_volume = frequency
            else:
                previous_step = op_df.iloc[idx - 1]

                if previous_volume is None:
                    previous_volume = frequency

                if type_kind == "relationship":
                    relationship_name = conceptual_type

                    if str(previous_step["type_kind"]) == "entity":
                        from_entity = str(previous_step["conceptual_type"])

                    if idx + 1 < len(op_df) and str(op_df.iloc[idx + 1]["type_kind"]) == "entity":
                        to_entity = str(op_df.iloc[idx + 1]["conceptual_type"])

                    if from_entity is not None and to_entity is not None:
                        (
                            multiplier,
                            multiplier_status,
                            relationship_confidence_status,
                            observed_cardinality,
                        ) = find_directional_avg(
                            relationship_lookup=relationship_lookup,
                            relationship_name=relationship_name,
                            from_entity=from_entity,
                            to_entity=to_entity,
                            fallback_multiplier=fallback_multiplier,
                        )
                    else:
                        multiplier = fallback_multiplier
                        multiplier_status = "relationship_without_adjacent_entities_fallback"

                    access_volume = previous_volume * multiplier

                elif type_kind == "entity" and str(previous_step["type_kind"]) == "relationship":
                    multiplier = 1.0
                    multiplier_status = "entity_inherits_previous_relationship_volume"
                    relationship_name = str(previous_step["conceptual_type"])
                    access_volume = previous_volume

                    rel = relationship_lookup.get(relationship_name)
                    if rel is not None:
                        relationship_confidence_status = rel.get("lmm_confidence_status")
                        observed_cardinality = rel.get("observed_cardinality")

                else:
                    multiplier = 1.0
                    multiplier_status = "generic_inherited_volume"
                    access_volume = previous_volume

            previous_volume = access_volume

            rows.append(
                {
                    "operation_name": operation_name,
                    "query_id": query_id,
                    "operation_kind": operation_kind,
                    "frequency": frequency,
                    "step_order": int(step["step_order"]),
                    "conceptual_type": conceptual_type,
                    "type_kind": type_kind,
                    "access_volume": float(access_volume),
                    "multiplier_from_previous": float(multiplier),
                    "multiplier_status": multiplier_status,
                    "relationship_name_for_multiplier": relationship_name,
                    "from_entity_for_multiplier": from_entity,
                    "to_entity_for_multiplier": to_entity,
                    "relationship_confidence_status": relationship_confidence_status,
                    "observed_cardinality": observed_cardinality,
                }
            )

    return pd.DataFrame(rows)


def compute_gaf(access_volume_df: pd.DataFrame, maf_value: float) -> pd.DataFrame:
    gaf_df = (
        access_volume_df
        .groupby(["conceptual_type", "type_kind"], as_index=False)
        .agg(
            gaf=("access_volume", "sum"),
            n_access_steps=("access_volume", "count"),
            n_operations=("operation_name", lambda s: len(set(s))),
            n_query_ids=("query_id", lambda s: len(set(s))),
            query_ids=("query_id", lambda s: sorted(set(s))),
            operation_names=("operation_name", lambda s: sorted(set(s))),
        )
    )

    gaf_df["maf"] = maf_value
    gaf_df["gaf_over_maf"] = gaf_df["gaf"] / maf_value if maf_value != 0 else None
    gaf_df["is_relevant_by_maf"] = gaf_df["gaf"] >= maf_value

    gaf_df = gaf_df.sort_values(
        ["gaf", "conceptual_type"],
        ascending=[False, True],
    ).reset_index(drop=True)

    return gaf_df


def compute_gaf_by_query(access_volume_df: pd.DataFrame) -> pd.DataFrame:
    return (
        access_volume_df
        .groupby(["query_id", "conceptual_type", "type_kind"], as_index=False)
        .agg(
            query_gaf=("access_volume", "sum"),
            n_access_steps=("access_volume", "count"),
            operation_names=("operation_name", lambda s: sorted(set(s))),
        )
        .sort_values(["query_id", "query_gaf"], ascending=[True, False])
        .reset_index(drop=True)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        default="de_lima_mello_2015_implementation/generated/fiben",
    )
    parser.add_argument(
        "--output-dir",
        default="de_lima_mello_2015_implementation/generated/fiben",
    )
    parser.add_argument(
        "--maf-percentage",
        type=float,
        default=0.0115,
        help="MAF percentage. Default follows the Lima & Mello case study: 1.15%.",
    )
    parser.add_argument(
        "--load-coverage",
        type=float,
        default=0.80,
        help="Observed workload coverage. Default follows the paper example: 80%.",
    )
    parser.add_argument(
        "--fallback-multiplier",
        type=float,
        default=1.0,
        help="Multiplier used when observed Avg is missing. It is flagged, not treated as observed evidence.",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    access_paths_path = input_dir / "lmm_fiben_workload_access_paths.csv"
    cardinalities_path = input_dir / "lmm_fiben_relationship_cardinalities.csv"

    if not access_paths_path.exists():
        raise FileNotFoundError(f"Missing workload access paths file: {access_paths_path}")

    if not cardinalities_path.exists():
        raise FileNotFoundError(f"Missing relationship cardinalities file: {cardinalities_path}")

    access_paths_df = pd.read_csv(access_paths_path)
    cardinality_df = pd.read_csv(cardinalities_path)

    relationship_lookup = build_relationship_lookup(cardinality_df)

    access_volume_df = compute_access_volumes(
        access_paths_df=access_paths_df,
        relationship_lookup=relationship_lookup,
        fallback_multiplier=args.fallback_multiplier,
    )

    observed_total_access_volume = float(access_volume_df["access_volume"].sum())

    if args.load_coverage <= 0:
        raise ValueError("--load-coverage must be greater than zero")

    estimated_total_access_volume = observed_total_access_volume / args.load_coverage
    maf_value = args.maf_percentage * estimated_total_access_volume

    gaf_df = compute_gaf(access_volume_df, maf_value=maf_value)
    gaf_by_query_df = compute_gaf_by_query(access_volume_df)

    access_volume_csv = output_dir / "lmm_fiben_access_volume_trace.csv"
    gaf_csv = output_dir / "lmm_fiben_gaf_by_concept.csv"
    gaf_by_query_csv = output_dir / "lmm_fiben_gaf_by_query_concept.csv"
    top_gaf_csv = output_dir / "lmm_fiben_top_gaf_concepts.csv"
    maf_json = output_dir / "lmm_fiben_maf_summary.json"
    report_json = output_dir / "lmm_fiben_workload_metrics_report.json"

    access_volume_df.to_csv(access_volume_csv, index=False)
    gaf_df.to_csv(gaf_csv, index=False)
    gaf_by_query_df.to_csv(gaf_by_query_csv, index=False)
    gaf_df.head(20).to_csv(top_gaf_csv, index=False)

    multiplier_status_counts = (
        access_volume_df["multiplier_status"]
        .value_counts(dropna=False)
        .to_dict()
    )

    confidence_status_counts = (
        access_volume_df["relationship_confidence_status"]
        .fillna("not_applicable")
        .value_counts(dropna=False)
        .to_dict()
    )

    maf_payload = {
        "maf_percentage": args.maf_percentage,
        "load_coverage": args.load_coverage,
        "observed_total_access_volume": observed_total_access_volume,
        "estimated_total_access_volume": estimated_total_access_volume,
        "maf": maf_value,
        "interpretation": "Concepts with GAF >= MAF are considered relevant by the Lima & Mello threshold.",
    }

    maf_json.write_text(
        json.dumps(maf_payload, indent=2, sort_keys=True, default=json_default),
        encoding="utf-8",
    )

    report = {
        "status": "completed",
        "methodological_mode": "lima_mello_gaf_maf_from_schemalens_artifact_consistent_inputs",
        "input_files": {
            "access_paths": str(access_paths_path),
            "relationship_cardinalities": str(cardinalities_path),
        },
        "parameters": {
            "maf_percentage": args.maf_percentage,
            "load_coverage": args.load_coverage,
            "fallback_multiplier": args.fallback_multiplier,
        },
        "metrics": maf_payload,
        "n_access_volume_rows": int(len(access_volume_df)),
        "n_gaf_concepts": int(len(gaf_df)),
        "n_relevant_concepts_by_maf": int(gaf_df["is_relevant_by_maf"].sum()),
        "multiplier_status_counts": multiplier_status_counts,
        "relationship_confidence_status_counts": confidence_status_counts,
        "top_10_gaf_concepts": gaf_df.head(10)[
            ["conceptual_type", "type_kind", "gaf", "maf", "gaf_over_maf", "is_relevant_by_maf"]
        ].to_dict(orient="records"),
        "output_files": {
            "access_volume_trace_csv": str(access_volume_csv),
            "gaf_by_concept_csv": str(gaf_csv),
            "gaf_by_query_concept_csv": str(gaf_by_query_csv),
            "top_gaf_concepts_csv": str(top_gaf_csv),
            "maf_summary_json": str(maf_json),
            "report_json": str(report_json),
        },
        "important_note": (
            "Missing/no-observed relationship cardinalities are not corrected. "
            "They use fallback multiplier 1.0 and remain explicitly flagged in the access-volume trace."
        ),
    }

    report_json.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=json_default),
        encoding="utf-8",
    )

    print("Computed Lima & Mello workload metrics for FIBEN.")
    print(f"Access-volume rows: {len(access_volume_df)}")
    print(f"GAF concepts: {len(gaf_df)}")
    print(f"Observed total access volume: {observed_total_access_volume:.6f}")
    print(f"Estimated total access volume: {estimated_total_access_volume:.6f}")
    print(f"MAF: {maf_value:.6f}")
    print(f"Relevant concepts by MAF: {int(gaf_df['is_relevant_by_maf'].sum())}")

    print("\nMultiplier status counts:")
    print(access_volume_df["multiplier_status"].value_counts(dropna=False).to_string())

    print("\nTop 15 GAF concepts:")
    print(
        gaf_df.head(15)[
            ["conceptual_type", "type_kind", "gaf", "maf", "gaf_over_maf", "is_relevant_by_maf"]
        ].to_string(index=False)
    )

    print("\nOutput files:")
    for path in report["output_files"].values():
        print(f"  {path}")


if __name__ == "__main__":
    main()
