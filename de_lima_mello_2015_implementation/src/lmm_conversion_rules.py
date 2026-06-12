"""
Apply de Lima & Mello (2015) conversion rules to the FIBEN workload.

This script creates an artifact-level logical document schema from:
- the FIBEN conceptual schema;
- SchemaLens-consistent observed cardinalities;
- GAF/MAF workload metrics.

The output is not yet a MongoDB physical materialization script.
It is the logical schema decision layer that will guide materialization later.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

try:
    from .fiben_conceptual_schema import build_fiben_conceptual_schema
except ImportError:
    from fiben_conceptual_schema import build_fiben_conceptual_schema


def json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if pd.isna(value):
        return None
    return str(value)


def as_float(value: Any, default: float = 0.0) -> float:
    if pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_gaf_lookup(gaf_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}

    for _, row in gaf_df.iterrows():
        lookup[str(row["conceptual_type"])] = row.to_dict()

    return lookup


def get_gaf(gaf_lookup: Dict[str, Dict[str, Any]], concept: str) -> float:
    row = gaf_lookup.get(concept)
    if row is None:
        return 0.0
    return as_float(row.get("gaf"), default=0.0)


def is_relevant(gaf_lookup: Dict[str, Dict[str, Any]], concept: str) -> bool:
    row = gaf_lookup.get(concept)
    if row is None:
        return False
    return bool(row.get("is_relevant_by_maf"))


def relationship_row_lookup(cardinality_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    return {
        str(row["relationship_name"]): row.to_dict()
        for _, row in cardinality_df.iterrows()
    }


def pick_top_entity_by_gaf(
    source: str,
    target: str,
    gaf_lookup: Dict[str, Dict[str, Any]],
) -> Tuple[str, str, str]:
    source_gaf = get_gaf(gaf_lookup, source)
    target_gaf = get_gaf(gaf_lookup, target)

    if source_gaf >= target_gaf:
        return source, target, "source_has_equal_or_higher_gaf"

    return target, source, "target_has_higher_gaf"


def pick_top_entity_for_rule5(
    source: str,
    target: str,
    relationship_kind: str,
    gaf_lookup: Dict[str, Dict[str, Any]],
) -> Tuple[str, str, str]:
    """
    Pick the top entity for Rule 5.

    In the main comparison, cardinality evidence remains exactly the one
    imported from SchemaLens. This function only improves the logical
    interpretation of binary 1:N relationships.

    For relationships with strong conceptual direction, the source entity is
    kept as the owner/root:
    - containment;
    - ownership;
    - descriptor.

    For ordinary associations, the top entity is selected by higher GAF.
    """
    if relationship_kind in {"containment", "ownership", "descriptor"}:
        return source, target, f"source_entity_preserved_for_{relationship_kind}"

    return pick_top_entity_by_gaf(source, target, gaf_lookup)


def relationship_has_observed_avg(row: Optional[Dict[str, Any]]) -> bool:
    if row is None:
        return False

    avg_st = row.get("avg_source_to_target")
    avg_ts = row.get("avg_target_to_source")

    if pd.isna(avg_st) and pd.isna(avg_ts):
        return False

    observed_cardinality = str(row.get("observed_cardinality", ""))
    if observed_cardinality == "no_observed_matches":
        return False

    return True


def classify_relationship_decision(
    relationship_name: str,
    source: str,
    target: str,
    relationship_kind: str,
    cardinality_class: str,
    rel_row: Optional[Dict[str, Any]],
    gaf_lookup: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    source_gaf = get_gaf(gaf_lookup, source)
    target_gaf = get_gaf(gaf_lookup, target)
    relationship_gaf = get_gaf(gaf_lookup, relationship_name)

    source_relevant = is_relevant(gaf_lookup, source)
    target_relevant = is_relevant(gaf_lookup, target)
    relationship_relevant = is_relevant(gaf_lookup, relationship_name)

    observed_cardinality = rel_row.get("observed_cardinality") if rel_row else None
    confidence_status = rel_row.get("lmm_confidence_status") if rel_row else None
    hint_confidence = rel_row.get("hint_confidence") if rel_row else None
    avg_source_to_target = rel_row.get("avg_source_to_target") if rel_row else None
    avg_target_to_source = rel_row.get("avg_target_to_source") if rel_row else None

    has_observed_avg = relationship_has_observed_avg(rel_row)

    # Generalization/subtype relationships are handled separately.
    if relationship_kind in {"generalization", "subtype"}:
        supertype = "Transaction" if "Transaction" in {source, target} else source
        subtype = target if source == supertype else source

        supertype_relevant = is_relevant(gaf_lookup, supertype)
        subtype_relevant = is_relevant(gaf_lookup, subtype)

        if supertype_relevant and subtype_relevant:
            rule = "RULE_3_HIERARCHY_FOCUSED"
            representation = "preserve_subtype_as_logical_specialization"
            reason = "Both superclass and subclass are relevant by MAF."
        elif subtype_relevant and not supertype_relevant:
            rule = "RULE_2_SUBCLASS_FOCUSED"
            representation = "preserve_subclass_logical_block"
            reason = "Subclass is relevant by MAF and superclass is not."
        else:
            rule = "RULE_1_SUPERCLASS_FOCUSED"
            representation = "fold_subclass_into_superclass_or_discriminator"
            reason = "Subclass is not relevant by MAF, so the superclass-centered representation is preferred."

        return {
            "relationship_name": relationship_name,
            "source_entity": source,
            "target_entity": target,
            "relationship_kind": relationship_kind,
            "cardinality_class": cardinality_class,
            "applied_rule": rule,
            "logical_representation": representation,
            "top_entity": supertype,
            "nested_or_secondary_entity": subtype,
            "top_entity_selection_reason": "hierarchy_supertype",
            "source_gaf": source_gaf,
            "target_gaf": target_gaf,
            "relationship_gaf": relationship_gaf,
            "source_relevant_by_maf": source_relevant,
            "target_relevant_by_maf": target_relevant,
            "relationship_relevant_by_maf": relationship_relevant,
            "observed_cardinality": observed_cardinality,
            "confidence_status": confidence_status,
            "hint_confidence": hint_confidence,
            "avg_source_to_target": avg_source_to_target,
            "avg_target_to_source": avg_target_to_source,
            "decision_reason": reason,
        }

    # If there is no observed cardinality evidence, use Rule 6.
    # This preserves SchemaLens-consistent evidence instead of inventing a corrected relationship.
    if not has_observed_avg:
        top, secondary, top_reason = pick_top_entity_by_gaf(source, target, gaf_lookup)
        return {
            "relationship_name": relationship_name,
            "source_entity": source,
            "target_entity": target,
            "relationship_kind": relationship_kind,
            "cardinality_class": cardinality_class,
            "applied_rule": "RULE_6_REFERENCES",
            "logical_representation": "reference_due_to_missing_or_no_observed_cardinality",
            "top_entity": top,
            "nested_or_secondary_entity": secondary,
            "top_entity_selection_reason": top_reason,
            "source_gaf": source_gaf,
            "target_gaf": target_gaf,
            "relationship_gaf": relationship_gaf,
            "source_relevant_by_maf": source_relevant,
            "target_relevant_by_maf": target_relevant,
            "relationship_relevant_by_maf": relationship_relevant,
            "observed_cardinality": observed_cardinality,
            "confidence_status": confidence_status,
            "hint_confidence": hint_confidence,
            "avg_source_to_target": avg_source_to_target,
            "avg_target_to_source": avg_target_to_source,
            "decision_reason": (
                "No observed cardinality evidence was available. "
                "The main comparison preserves SchemaLens artifact-consistent evidence and uses references."
            ),
        }

    # Rule 4: 1:1 relationship modeled as one logical block.
    if cardinality_class == "1:1" or str(observed_cardinality) == "observed_1_to_1":
        top, secondary, top_reason = pick_top_entity_by_gaf(source, target, gaf_lookup)
        return {
            "relationship_name": relationship_name,
            "source_entity": source,
            "target_entity": target,
            "relationship_kind": relationship_kind,
            "cardinality_class": cardinality_class,
            "applied_rule": "RULE_4_ONE_BLOCK",
            "logical_representation": "single_logical_block",
            "top_entity": top,
            "nested_or_secondary_entity": secondary,
            "top_entity_selection_reason": top_reason,
            "source_gaf": source_gaf,
            "target_gaf": target_gaf,
            "relationship_gaf": relationship_gaf,
            "source_relevant_by_maf": source_relevant,
            "target_relevant_by_maf": target_relevant,
            "relationship_relevant_by_maf": relationship_relevant,
            "observed_cardinality": observed_cardinality,
            "confidence_status": confidence_status,
            "hint_confidence": hint_confidence,
            "avg_source_to_target": avg_source_to_target,
            "avg_target_to_source": avg_target_to_source,
            "decision_reason": "The relationship is one-to-one or observed as one-to-one.",
        }

    # Rule 5: binary 1:N relationship modeled as hierarchy.
    if cardinality_class in {"1:N", "N:1"}:
        top, secondary, top_reason = pick_top_entity_for_rule5(
            source=source,
            target=target,
            relationship_kind=relationship_kind,
            gaf_lookup=gaf_lookup,
        )
        return {
            "relationship_name": relationship_name,
            "source_entity": source,
            "target_entity": target,
            "relationship_kind": relationship_kind,
            "cardinality_class": cardinality_class,
            "applied_rule": "RULE_5_HIERARCHY",
            "logical_representation": "hierarchical_embedding_or_inner_block",
            "top_entity": top,
            "nested_or_secondary_entity": secondary,
            "top_entity_selection_reason": top_reason,
            "source_gaf": source_gaf,
            "target_gaf": target_gaf,
            "relationship_gaf": relationship_gaf,
            "source_relevant_by_maf": source_relevant,
            "target_relevant_by_maf": target_relevant,
            "relationship_relevant_by_maf": relationship_relevant,
            "observed_cardinality": observed_cardinality,
            "confidence_status": confidence_status,
            "hint_confidence": hint_confidence,
            "avg_source_to_target": avg_source_to_target,
            "avg_target_to_source": avg_target_to_source,
            "decision_reason": (
                "The relationship is binary 1:N in the conceptual model. "
                "For containment, ownership, and descriptor relationships, the conceptual source entity is preserved as the top/root. "
                "For ordinary associations, the top entity is chosen by higher GAF."
            ),
        }

    # Rule 6: fallback for N:N, n-ary, or cases where hierarchy cannot be safely applied.
    top, secondary, top_reason = pick_top_entity_by_gaf(source, target, gaf_lookup)
    return {
        "relationship_name": relationship_name,
        "source_entity": source,
        "target_entity": target,
        "relationship_kind": relationship_kind,
        "cardinality_class": cardinality_class,
        "applied_rule": "RULE_6_REFERENCES",
        "logical_representation": "reference_or_relationship_block",
        "top_entity": top,
        "nested_or_secondary_entity": secondary,
        "top_entity_selection_reason": top_reason,
        "source_gaf": source_gaf,
        "target_gaf": target_gaf,
        "relationship_gaf": relationship_gaf,
        "source_relevant_by_maf": source_relevant,
        "target_relevant_by_maf": target_relevant,
        "relationship_relevant_by_maf": relationship_relevant,
        "observed_cardinality": observed_cardinality,
        "confidence_status": confidence_status,
        "hint_confidence": hint_confidence,
        "avg_source_to_target": avg_source_to_target,
        "avg_target_to_source": avg_target_to_source,
        "decision_reason": "Fallback case for relationships not safely handled by Rule 4 or Rule 5.",
    }


def build_logical_schema_summary(decisions_df: pd.DataFrame, gaf_df: pd.DataFrame) -> Dict[str, Any]:
    collections: Dict[str, Dict[str, Any]] = {}

    def ensure_collection(entity: str) -> Dict[str, Any]:
        if entity not in collections:
            row = gaf_df[gaf_df["conceptual_type"] == entity]
            gaf = float(row["gaf"].iloc[0]) if len(row) else 0.0
            relevant = bool(row["is_relevant_by_maf"].iloc[0]) if len(row) else False

            collections[entity] = {
                "root_entity": entity,
                "root_gaf": gaf,
                "root_relevant_by_maf": relevant,
                "embedded_entities": [],
                "referenced_entities": [],
                "merged_or_specialized_entities": [],
                "source_decisions": [],
            }

        return collections[entity]

    for _, row in decisions_df.iterrows():
        top = str(row["top_entity"])
        secondary = str(row["nested_or_secondary_entity"])
        rule = str(row["applied_rule"])
        rel = str(row["relationship_name"])

        collection = ensure_collection(top)
        collection["source_decisions"].append(rel)

        if rule == "RULE_5_HIERARCHY":
            collection["embedded_entities"].append(
                {
                    "entity": secondary,
                    "relationship": rel,
                    "reason": row["decision_reason"],
                }
            )
        elif rule == "RULE_4_ONE_BLOCK":
            collection["merged_or_specialized_entities"].append(
                {
                    "entity": secondary,
                    "relationship": rel,
                    "reason": row["decision_reason"],
                }
            )
        elif rule in {
            "RULE_1_SUPERCLASS_FOCUSED",
            "RULE_2_SUBCLASS_FOCUSED",
            "RULE_3_HIERARCHY_FOCUSED",
        }:
            collection["merged_or_specialized_entities"].append(
                {
                    "entity": secondary,
                    "relationship": rel,
                    "representation": row["logical_representation"],
                    "reason": row["decision_reason"],
                }
            )
        else:
            collection["referenced_entities"].append(
                {
                    "entity": secondary,
                    "relationship": rel,
                    "reason": row["decision_reason"],
                }
            )
            ensure_collection(secondary)

    # Ensure all MAF-relevant entities have a collection, even if no relationship selected them as top.
    for _, row in gaf_df.iterrows():
        if str(row["type_kind"]) == "entity" and bool(row["is_relevant_by_maf"]):
            ensure_collection(str(row["conceptual_type"]))

    return {
        "logical_schema_name": "Lima_Mello_2015_FIBEN_logical_schema",
        "schema_status": "logical_decision_layer_not_physical_materialization",
        "collections": collections,
        "notes": [
            "This schema is generated from GAF/MAF, conceptual cardinalities, and SchemaLens-consistent observed evidence.",
            "Relationships with no observed cardinality evidence are represented as references in the main comparison mode.",
            "Physical MongoDB materialization will be implemented in a later phase.",
        ],
    }


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
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    gaf_path = input_dir / "lmm_fiben_gaf_by_concept.csv"
    cardinalities_path = input_dir / "lmm_fiben_relationship_cardinalities.csv"

    if not gaf_path.exists():
        raise FileNotFoundError(f"Missing GAF file: {gaf_path}")

    if not cardinalities_path.exists():
        raise FileNotFoundError(f"Missing cardinalities file: {cardinalities_path}")

    gaf_df = pd.read_csv(gaf_path)
    cardinality_df = pd.read_csv(cardinalities_path)

    gaf_lookup = load_gaf_lookup(gaf_df)
    rel_lookup = relationship_row_lookup(cardinality_df)

    schema = build_fiben_conceptual_schema()

    decision_rows: List[Dict[str, Any]] = []

    for relationship_name, relationship in schema.relationships.items():
        source = relationship.ends[0].entity
        target = relationship.ends[1].entity
        relationship_kind = relationship.kind
        cardinality_class = relationship.cardinality_class()
        rel_row = rel_lookup.get(relationship_name)

        decision_rows.append(
            classify_relationship_decision(
                relationship_name=relationship_name,
                source=source,
                target=target,
                relationship_kind=relationship_kind,
                cardinality_class=cardinality_class,
                rel_row=rel_row,
                gaf_lookup=gaf_lookup,
            )
        )

    decisions_df = pd.DataFrame(decision_rows)

    decisions_df = decisions_df.sort_values(
        ["applied_rule", "relationship_gaf", "relationship_name"],
        ascending=[True, False, True],
    ).reset_index(drop=True)

    logical_schema = build_logical_schema_summary(decisions_df, gaf_df)

    decisions_csv = output_dir / "lmm_fiben_conversion_decisions.csv"
    rule_summary_csv = output_dir / "lmm_fiben_conversion_rule_summary.csv"
    logical_schema_json = output_dir / "lmm_fiben_logical_schema.json"
    logical_schema_collections_json = output_dir / "lmm_fiben_logical_collections.json"
    report_json = output_dir / "lmm_fiben_conversion_report.json"

    decisions_df.to_csv(decisions_csv, index=False)

    rule_summary_df = (
        decisions_df
        .groupby(["applied_rule", "logical_representation"], as_index=False)
        .agg(
            n_relationships=("relationship_name", "count"),
            relationships=("relationship_name", lambda s: sorted(set(s))),
            top_entities=("top_entity", lambda s: sorted(set(s))),
            secondary_entities=("nested_or_secondary_entity", lambda s: sorted(set(s))),
        )
        .sort_values(["applied_rule", "logical_representation"])
        .reset_index(drop=True)
    )

    rule_summary_df.to_csv(rule_summary_csv, index=False)

    logical_schema_json.write_text(
        json.dumps(logical_schema, indent=2, sort_keys=True, default=json_default),
        encoding="utf-8",
    )

    logical_schema_collections_json.write_text(
        json.dumps(logical_schema["collections"], indent=2, sort_keys=True, default=json_default),
        encoding="utf-8",
    )

    report = {
        "status": "completed",
        "methodological_mode": "lima_mello_conversion_rules_from_schemalens_consistent_inputs",
        "n_relationship_decisions": int(len(decisions_df)),
        "rule_counts": decisions_df["applied_rule"].value_counts().to_dict(),
        "logical_representation_counts": decisions_df["logical_representation"].value_counts().to_dict(),
        "n_logical_collections": int(len(logical_schema["collections"])),
        "logical_collections": sorted(logical_schema["collections"].keys()),
        "output_files": {
            "conversion_decisions_csv": str(decisions_csv),
            "rule_summary_csv": str(rule_summary_csv),
            "logical_schema_json": str(logical_schema_json),
            "logical_collections_json": str(logical_schema_collections_json),
            "report_json": str(report_json),
        },
        "important_note": (
            "This is the logical decision layer. It should be inspected before "
            "implementing MongoDB physical materialization."
        ),
    }

    report_json.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=json_default),
        encoding="utf-8",
    )

    print("Applied Lima & Mello conversion rules to FIBEN.")
    print(f"Relationship decisions: {len(decisions_df)}")
    print(f"Logical collections: {len(logical_schema['collections'])}")

    print("\nRule counts:")
    print(decisions_df["applied_rule"].value_counts().to_string())

    print("\nLogical representation counts:")
    print(decisions_df["logical_representation"].value_counts().to_string())

    print("\nRule summary:")
    print(rule_summary_df.to_string(index=False))

    print("\nOutput files:")
    for path in report["output_files"].values():
        print(f"  {path}")


if __name__ == "__main__":
    main()
