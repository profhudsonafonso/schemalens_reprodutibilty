#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def entity_lookup(input_model: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {entity["name"]: entity for entity in input_model.get("entities", [])}


def relationship_lookup(input_model: Dict[str, Any]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    lookup: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for rel in input_model.get("relationships", []):
        source = rel["source_entity"]
        target = rel["target_entity"]

        lookup[(source, target)] = {
            **rel,
            "tree_direction": "forward",
            "parent_join_column": rel["source_column"],
            "child_join_column": rel["target_column"],
        }

        lookup[(target, source)] = {
            **rel,
            "tree_direction": "reverse",
            "parent_join_column": rel["target_column"],
            "child_join_column": rel["source_column"],
        }

    return lookup


def walk_tree_edges(tree: Dict[str, Any]) -> List[Tuple[str, str]]:
    edges: List[Tuple[str, str]] = []
    parent = tree.get("entity")

    for child in tree.get("children", []):
        child_entity = child.get("entity")
        if parent and child_entity:
            edges.append((parent, child_entity))
        edges.extend(walk_tree_edges(child))

    return edges


def walk_tree_entities(tree: Dict[str, Any]) -> List[str]:
    entities = []
    entity = tree.get("entity")
    if entity:
        entities.append(entity)

    for child in tree.get("children", []):
        entities.extend(walk_tree_entities(child))

    return entities


def build_collection_materialization_plan(
    collection_manifest: Dict[str, Any],
    entities: Dict[str, Dict[str, Any]],
    relationships: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    tree = collection_manifest.get("tree", {})
    root_entity = collection_manifest.get("root_entity") or tree.get("entity")
    root_info = entities.get(root_entity, {})

    tree_entities = walk_tree_entities(tree)
    tree_edges = walk_tree_edges(tree)

    source_collections = []
    for entity_name in tree_entities:
        entity_info = entities.get(entity_name, {})
        source_collections.append(
            {
                "entity": entity_name,
                "source_view": entity_info.get("source_view", ""),
                "primary_key": entity_info.get("primary_key", ""),
            }
        )

    embedding_steps = []
    missing_relationships = []

    for parent_entity, child_entity in tree_edges:
        rel = relationships.get((parent_entity, child_entity))

        if rel is None:
            missing_relationships.append(
                {
                    "parent_entity": parent_entity,
                    "child_entity": child_entity,
                    "reason": "relationship_not_found_in_input_model",
                }
            )
            continue

        embedding_steps.append(
            {
                "parent_entity": parent_entity,
                "child_entity": child_entity,
                "relationship_id": rel.get("id", ""),
                "relationship_direction": rel.get("tree_direction", ""),
                "relationship_type": rel.get("type", ""),
                "dbsr_role": rel.get("dbsr_role", ""),
                "parent_join_column": rel.get("parent_join_column", ""),
                "child_join_column": rel.get("child_join_column", ""),
                "materialization_operation": "lookup_children_and_embed",
            }
        )

    if missing_relationships:
        status = "plan_has_missing_relationships"
    elif embedding_steps:
        status = "planned_nested_embedding"
    else:
        status = "planned_single_entity_collection"

    return {
        "rank": collection_manifest.get("rank"),
        "target_collection": collection_manifest.get("collection_name"),
        "document_signature": collection_manifest.get("document_signature"),
        "root_entity": root_entity,
        "root_source_view": root_info.get("source_view", ""),
        "root_primary_key": root_info.get("primary_key", ""),
        "tree_entities": tree_entities,
        "source_collections": source_collections,
        "embedding_steps": embedding_steps,
        "missing_relationships": missing_relationships,
        "materialization_strategy": "root_scan_then_nested_lookup_embedding",
        "materialization_status": status,
        "queries_covered": collection_manifest.get("queries_covered"),
        "sequences_covered": collection_manifest.get("sequences_covered"),
        "total_utility": collection_manifest.get("total_utility"),
        "notes": [
            "This is a materialization plan only; it does not load MongoDB.",
            "The physical loader must use this plan to create the target collection later.",
            "Statistics must be captured before any temporary benchmark database is dropped.",
        ],
    }


def build_materialization_plan(
    input_model: Dict[str, Any],
    schema_manifest: Dict[str, Any],
) -> Dict[str, Any]:
    entities = entity_lookup(input_model)
    relationships = relationship_lookup(input_model)

    collection_plans = [
        build_collection_materialization_plan(
            collection_manifest=collection,
            entities=entities,
            relationships=relationships,
        )
        for collection in schema_manifest.get("collections", [])
    ]

    embedding_steps_total = sum(len(plan["embedding_steps"]) for plan in collection_plans)
    missing_relationships_total = sum(len(plan["missing_relationships"]) for plan in collection_plans)
    source_views = sorted(
        {
            item["source_view"]
            for plan in collection_plans
            for item in plan["source_collections"]
            if item.get("source_view")
        }
    )

    return {
        "baseline": "DBSR",
        "dataset": "FIBEN",
        "plan_type": "structural_materialization_plan",
        "version": "0.1-plan-only",
        "source_schema_manifest": schema_manifest.get("manifest_type", ""),
        "summary": {
            "target_collections": len(collection_plans),
            "embedding_steps_total": embedding_steps_total,
            "missing_relationships_total": missing_relationships_total,
            "source_views_used": len(source_views),
            "source_view_names": source_views,
            "plan_only": True,
        },
        "collection_plans": collection_plans,
        "implementation_assumptions": [
            "This phase creates a materialization plan but does not create MongoDB collections.",
            "Each selected DBSR document signature becomes one target collection in this first plan.",
            "Overlapping target collections are allowed because conflict resolution is deferred.",
            "A later physical loader must implement root scans, child lookups, embedding, index creation, and statistics capture.",
            "The plan is independent from SchemaLens G0-G9 templates.",
        ],
    }


def materialization_plan_to_rows(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for item in plan.get("collection_plans", []):
        relationship_ids = [
            step.get("relationship_id", "")
            for step in item.get("embedding_steps", [])
        ]

        rows.append(
            {
                "rank": item.get("rank"),
                "target_collection": item.get("target_collection"),
                "document_signature": item.get("document_signature"),
                "root_entity": item.get("root_entity"),
                "root_source_view": item.get("root_source_view"),
                "root_primary_key": item.get("root_primary_key"),
                "tree_entities": json.dumps(item.get("tree_entities", []), ensure_ascii=False),
                "source_collections": json.dumps(item.get("source_collections", []), ensure_ascii=False),
                "embedding_steps_count": len(item.get("embedding_steps", [])),
                "relationship_ids": ";".join(relationship_ids),
                "missing_relationships_count": len(item.get("missing_relationships", [])),
                "materialization_strategy": item.get("materialization_strategy"),
                "materialization_status": item.get("materialization_status"),
                "queries_covered": item.get("queries_covered"),
                "sequences_covered": item.get("sequences_covered"),
                "total_utility": item.get("total_utility"),
            }
        )

    return rows
