"""
Generate a MongoDB physical materialization plan for the Lima & Mello FIBEN schema.

This script does not load data into MongoDB.

It reads the logical conversion decisions and produces:
- planned MongoDB collections;
- planned embedded edges;
- planned reference edges;
- entity role summary;
- suggested indexes;
- warnings about entities that are both roots and embedded elsewhere.

This physical plan is the bridge between:
1. the Lima & Mello logical decision layer;
2. the later MongoDB materialization script.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set

import pandas as pd


FIBEN_EDGE_COLUMN_OVERRIDES = {
    # The conceptual relationship is ReportElement -> StatementElement.
    # Physically, ELEMENTSOFFINANCIALREPORT.csv stores:
    #   column 1: ELEMENTOFFINANCIALSTATEMENTID
    #   column 2: ISMEMBEROF, pointing to FINANCIALREPORTID.
    # Therefore, the Rule-6 reference to StatementElement must use
    # ELEMENTOFFINANCIALSTATEMENTID, not a synthetic report-element id.
    ("report_element_has_statement_element", "selected_source_column"): "ELEMENTOFFINANCIALSTATEMENTID",
}


def json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if pd.isna(value):
        return None
    return str(value)


def snake_case(value: str) -> str:
    value = str(value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value)
    value = value.strip("_").lower()
    return value


def collection_name(entity: str) -> str:
    return f"lmm_{snake_case(entity)}"


def role_for_rule(applied_rule: str, logical_representation: str) -> str:
    if applied_rule == "RULE_5_HIERARCHY":
        return "embed"
    if applied_rule == "RULE_4_ONE_BLOCK":
        return "merge"
    if applied_rule in {
        "RULE_1_SUPERCLASS_FOCUSED",
        "RULE_2_SUBCLASS_FOCUSED",
        "RULE_3_HIERARCHY_FOCUSED",
    }:
        return "specialize_or_fold"
    if applied_rule == "RULE_6_REFERENCES":
        return "reference"
    return "unknown"


def build_edge_rows(decisions_df: pd.DataFrame, cardinalities_df: pd.DataFrame) -> pd.DataFrame:
    cardinality_lookup = {
        str(row["relationship_name"]): row.to_dict()
        for _, row in cardinalities_df.iterrows()
    }

    edge_column_overrides = {}

    rows: List[Dict[str, Any]] = []

    for _, decision in decisions_df.iterrows():
        rel_name = str(decision["relationship_name"])
        top_entity = str(decision["top_entity"])
        secondary_entity = str(decision["nested_or_secondary_entity"])
        applied_rule = str(decision["applied_rule"])
        logical_representation = str(decision["logical_representation"])
        physical_role = role_for_rule(applied_rule, logical_representation)

        card = cardinality_lookup.get(rel_name, {})

        selected_source_column = edge_column_overrides.get(
            (rel_name, "selected_source_column"),
            card.get("selected_source_column"),
        )
        selected_target_column = edge_column_overrides.get(
            (rel_name, "selected_target_column"),
            card.get("selected_target_column"),
        )
        bridge_source_column = edge_column_overrides.get(
            (rel_name, "bridge_source_column"),
            card.get("bridge_source_column"),
        )
        bridge_target_column = edge_column_overrides.get(
            (rel_name, "bridge_target_column"),
            card.get("bridge_target_column"),
        )

        rows.append(
            {
                "relationship_name": rel_name,
                "source_entity": decision["source_entity"],
                "target_entity": decision["target_entity"],
                "relationship_kind": decision["relationship_kind"],
                "applied_rule": applied_rule,
                "logical_representation": logical_representation,
                "physical_role": physical_role,
                "owning_root_entity": top_entity,
                "owning_collection": collection_name(top_entity),
                "secondary_entity": secondary_entity,
                "secondary_collection": collection_name(secondary_entity),
                "embedded_field_name": snake_case(secondary_entity),
                "reference_field_name": f"{snake_case(secondary_entity)}_ref",
                "top_entity_selection_reason": decision["top_entity_selection_reason"],
                "observed_cardinality": decision.get("observed_cardinality"),
                "confidence_status": decision.get("confidence_status"),
                "hint_confidence": decision.get("hint_confidence"),
                "avg_source_to_target": decision.get("avg_source_to_target"),
                "avg_target_to_source": decision.get("avg_target_to_source"),
                "source_view": card.get("source_view"),
                "target_view": card.get("target_view"),
                "bridge_view": card.get("bridge_view"),
                "selected_source_column": selected_source_column,
                "selected_target_column": selected_target_column,
                "bridge_source_column": bridge_source_column,
                "bridge_target_column": bridge_target_column,
                "materialization_note": materialization_note_for_role(
                    physical_role=physical_role,
                    applied_rule=applied_rule,
                    rel_name=rel_name,
                ),
            }
        )

    return pd.DataFrame(rows)


def materialization_note_for_role(physical_role: str, applied_rule: str, rel_name: str) -> str:
    if physical_role == "embed":
        return (
            "Materialize secondary entity as an embedded block/array inside the owning collection. "
            "If the same secondary entity is also a root elsewhere, duplication is expected and must be documented."
        )

    if physical_role == "reference":
        return (
            "Materialize as a reference because cardinality evidence was missing or Rule 6 was selected. "
            "Do not invent embedding for the main comparison mode."
        )

    if physical_role == "specialize_or_fold":
        return (
            "Apply hierarchy conversion: fold subclass, preserve specialization, or keep discriminator according to the applied rule."
        )

    if physical_role == "merge":
        return "Materialize the two concepts in a single logical block."

    return f"No specific materialization note for {rel_name} with {applied_rule}."


def build_collection_rows(edges_df: pd.DataFrame, gaf_df: pd.DataFrame) -> pd.DataFrame:
    root_entities: Set[str] = set(edges_df["owning_root_entity"].dropna().astype(str))

    # Reference targets must also be available as collections.
    reference_targets = set(
        edges_df.loc[
            edges_df["physical_role"] == "reference",
            "secondary_entity",
        ].dropna().astype(str)
    )

    # MAF-relevant entities should be independently materializable.
    relevant_entities = set(
        gaf_df.loc[
            (gaf_df["type_kind"] == "entity") & (gaf_df["is_relevant_by_maf"] == True),
            "conceptual_type",
        ].dropna().astype(str)
    )

    all_collection_entities = sorted(root_entities | reference_targets | relevant_entities)

    rows: List[Dict[str, Any]] = []

    for entity in all_collection_entities:
        entity_gaf_row = gaf_df[gaf_df["conceptual_type"] == entity]
        gaf = float(entity_gaf_row["gaf"].iloc[0]) if len(entity_gaf_row) else 0.0
        relevant = bool(entity_gaf_row["is_relevant_by_maf"].iloc[0]) if len(entity_gaf_row) else False

        embedded_edges = edges_df[
            (edges_df["owning_root_entity"] == entity)
            & (edges_df["physical_role"] == "embed")
        ]

        reference_edges = edges_df[
            (edges_df["owning_root_entity"] == entity)
            & (edges_df["physical_role"] == "reference")
        ]

        hierarchy_edges = edges_df[
            (edges_df["owning_root_entity"] == entity)
            & (edges_df["physical_role"].isin(["specialize_or_fold", "merge"]))
        ]

        rows.append(
            {
                "root_entity": entity,
                "collection_name": collection_name(entity),
                "root_gaf": gaf,
                "root_relevant_by_maf": relevant,
                "is_top_entity_in_decisions": entity in root_entities,
                "is_reference_target": entity in reference_targets,
                "is_maf_relevant_entity": entity in relevant_entities,
                "embedded_entities": sorted(set(embedded_edges["secondary_entity"].astype(str))),
                "referenced_entities": sorted(set(reference_edges["secondary_entity"].astype(str))),
                "hierarchy_or_merged_entities": sorted(set(hierarchy_edges["secondary_entity"].astype(str))),
                "n_embedded_edges": int(len(embedded_edges)),
                "n_reference_edges": int(len(reference_edges)),
                "n_hierarchy_edges": int(len(hierarchy_edges)),
                "suggested_indexes": suggested_indexes_for_collection(entity, edges_df),
            }
        )

    return pd.DataFrame(rows)


def suggested_indexes_for_collection(entity: str, edges_df: pd.DataFrame) -> List[str]:
    indexes = ["_id"]

    collection = collection_name(entity)

    incoming_or_owned = edges_df[
        (edges_df["owning_collection"] == collection)
        | (edges_df["secondary_collection"] == collection)
    ]

    for _, row in incoming_or_owned.iterrows():
        for col in [
            "selected_source_column",
            "selected_target_column",
            "bridge_source_column",
            "bridge_target_column",
        ]:
            value = row.get(col)
            if pd.notna(value):
                idx = snake_case(str(value))
                if idx and idx not in indexes:
                    indexes.append(idx)

    return indexes


def build_entity_role_summary(collections_df: pd.DataFrame, edges_df: pd.DataFrame) -> pd.DataFrame:
    entities: Set[str] = set(collections_df["root_entity"].astype(str))
    entities |= set(edges_df["secondary_entity"].dropna().astype(str))
    entities |= set(edges_df["source_entity"].dropna().astype(str))
    entities |= set(edges_df["target_entity"].dropna().astype(str))

    rows: List[Dict[str, Any]] = []

    for entity in sorted(entities):
        as_root = entity in set(collections_df["root_entity"].astype(str))

        embedded_in = sorted(
            set(
                edges_df.loc[
                    (edges_df["secondary_entity"] == entity)
                    & (edges_df["physical_role"] == "embed"),
                    "owning_collection",
                ].astype(str)
            )
        )

        referenced_by = sorted(
            set(
                edges_df.loc[
                    (edges_df["secondary_entity"] == entity)
                    & (edges_df["physical_role"] == "reference"),
                    "owning_collection",
                ].astype(str)
            )
        )

        specialized_in = sorted(
            set(
                edges_df.loc[
                    (edges_df["secondary_entity"] == entity)
                    & (edges_df["physical_role"].isin(["specialize_or_fold", "merge"])),
                    "owning_collection",
                ].astype(str)
            )
        )

        rows.append(
            {
                "entity": entity,
                "collection_name": collection_name(entity),
                "is_root_collection": as_root,
                "embedded_in_collections": embedded_in,
                "referenced_by_collections": referenced_by,
                "specialized_or_folded_in_collections": specialized_in,
                "n_embedded_in": len(embedded_in),
                "n_referenced_by": len(referenced_by),
                "n_specialized_or_folded_in": len(specialized_in),
                "has_duplicate_materialization_risk": as_root and len(embedded_in) > 0,
                "role_note": role_note(
                    as_root=as_root,
                    embedded_in=embedded_in,
                    referenced_by=referenced_by,
                    specialized_in=specialized_in,
                ),
            }
        )

    return pd.DataFrame(rows)


def role_note(
    as_root: bool,
    embedded_in: List[str],
    referenced_by: List[str],
    specialized_in: List[str],
) -> str:
    notes: List[str] = []

    if as_root:
        notes.append("root_collection")

    if embedded_in:
        notes.append("embedded_elsewhere")

    if referenced_by:
        notes.append("reference_target")

    if specialized_in:
        notes.append("hierarchy_or_specialization")

    if not notes:
        return "only_conceptual_participant"

    if as_root and embedded_in:
        notes.append("duplication_expected_document_design")

    return ";".join(notes)


def dataframe_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    return json.loads(df.to_json(orient="records"))


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
        "--target-database",
        default="lmm_fiben_sf1_source_full",
        help="Default MongoDB database name for the first physical materialization.",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    decisions_path = input_dir / "lmm_fiben_conversion_decisions.csv"
    cardinalities_path = input_dir / "lmm_fiben_relationship_cardinalities.csv"
    gaf_path = input_dir / "lmm_fiben_gaf_by_concept.csv"

    for p in [decisions_path, cardinalities_path, gaf_path]:
        if not p.exists():
            raise FileNotFoundError(f"Required input file not found: {p}")

    decisions_df = pd.read_csv(decisions_path)
    cardinalities_df = pd.read_csv(cardinalities_path)
    gaf_df = pd.read_csv(gaf_path)

    edges_df = build_edge_rows(decisions_df, cardinalities_df)
    collections_df = build_collection_rows(edges_df, gaf_df)
    entity_roles_df = build_entity_role_summary(collections_df, edges_df)

    duplicate_risk_df = entity_roles_df[
        entity_roles_df["has_duplicate_materialization_risk"] == True
    ].copy()

    collections_csv = output_dir / "lmm_fiben_physical_collections.csv"
    edges_csv = output_dir / "lmm_fiben_physical_edges.csv"
    entity_roles_csv = output_dir / "lmm_fiben_entity_role_summary.csv"
    duplicate_risk_csv = output_dir / "lmm_fiben_duplicate_materialization_risk.csv"
    plan_json = output_dir / "lmm_fiben_physical_plan.json"
    report_json = output_dir / "lmm_fiben_physical_plan_report.json"

    collections_df.to_csv(collections_csv, index=False)
    edges_df.to_csv(edges_csv, index=False)
    entity_roles_df.to_csv(entity_roles_csv, index=False)
    duplicate_risk_df.to_csv(duplicate_risk_csv, index=False)

    plan = {
        "plan_name": "Lima_Mello_2015_FIBEN_MongoDB_physical_plan",
        "target_engine": "MongoDB",
        "target_database": args.target_database,
        "status": "physical_plan_only_not_loaded",
        "methodological_mode": "lima_mello_from_schemalens_consistent_inputs",
        "collections": dataframe_records(collections_df),
        "edges": dataframe_records(edges_df),
        "entity_roles": dataframe_records(entity_roles_df),
        "notes": [
            "This plan does not load data.",
            "Rule 5 edges become embedded blocks/arrays.",
            "Rule 6 edges become references.",
            "Entities that are both root collections and embedded elsewhere are expected in denormalized document design and are flagged.",
            "The first physical materialization target is SF1; SF10 and SF30 should use lmm_fiben_sf10_source_full and lmm_fiben_sf30_source_full.",
        ],
    }

    plan_json.write_text(
        json.dumps(plan, indent=2, sort_keys=True, default=json_default),
        encoding="utf-8",
    )

    report = {
        "status": "completed",
        "target_database": args.target_database,
        "n_collections": int(len(collections_df)),
        "n_physical_edges": int(len(edges_df)),
        "physical_role_counts": edges_df["physical_role"].value_counts().to_dict(),
        "n_entities_with_duplicate_materialization_risk": int(len(duplicate_risk_df)),
        "entities_with_duplicate_materialization_risk": duplicate_risk_df["entity"].tolist(),
        "collections": collections_df["collection_name"].tolist(),
        "output_files": {
            "physical_collections_csv": str(collections_csv),
            "physical_edges_csv": str(edges_csv),
            "entity_role_summary_csv": str(entity_roles_csv),
            "duplicate_materialization_risk_csv": str(duplicate_risk_csv),
            "physical_plan_json": str(plan_json),
            "report_json": str(report_json),
        },
        "important_note": (
            "Inspect duplicate materialization risks before loading MongoDB. "
            "They may be valid denormalization choices, but must be documented."
        ),
    }

    report_json.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=json_default),
        encoding="utf-8",
    )

    print("Generated Lima & Mello FIBEN physical materialization plan.")
    print(f"Collections: {len(collections_df)}")
    print(f"Physical edges: {len(edges_df)}")

    print("\nPhysical role counts:")
    print(edges_df["physical_role"].value_counts().to_string())

    print("\nDuplicate materialization risk entities:")
    if len(duplicate_risk_df):
        print(duplicate_risk_df[["entity", "embedded_in_collections", "role_note"]].to_string(index=False))
    else:
        print("None")

    print("\nCollections:")
    print(collections_df[["root_entity", "collection_name", "n_embedded_edges", "n_reference_edges", "n_hierarchy_edges"]].to_string(index=False))

    print("\nOutput files:")
    for path in report["output_files"].values():
        print(f"  {path}")


if __name__ == "__main__":
    main()
