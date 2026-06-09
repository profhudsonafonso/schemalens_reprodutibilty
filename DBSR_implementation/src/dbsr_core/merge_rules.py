#!/usr/bin/env python3
from __future__ import annotations

from typing import List, Optional

from dbsr_core.document_tree import DocumentNode, DocumentTree
from dbsr_core.model import DBSRModel
from dbsr_core.query_plan import QueryPlan


def _has_attachable_parent(node: DocumentNode, child_root_entity: str, model: DBSRModel) -> bool:
    if model.relationship_between(node.entity, child_root_entity) is not None:
        return True
    return any(_has_attachable_parent(child, child_root_entity, model) for child in node.children)


def _attach_to_first_relationship_node(
    node: DocumentNode,
    child: DocumentNode,
    model: DBSRModel,
) -> bool:
    if model.relationship_between(node.entity, child.entity) is not None:
        node.add_child(child)
        return True

    for existing_child in node.children:
        if _attach_to_first_relationship_node(existing_child, child, model):
            return True

    return False


def can_merge_as_adjacent_path(
    left: DocumentTree,
    right: DocumentTree,
    model: DBSRModel,
    max_height_edges: Optional[int] = None,
    max_width: Optional[int] = None,
) -> bool:
    if right.root_entity() in left.entity_set():
        return True

    if not _has_attachable_parent(left.root, right.root_entity(), model):
        return False

    candidate = merge_as_adjacent_path(left, right, model)

    if max_height_edges is not None and candidate.height_edges() > max_height_edges:
        return False

    if max_width is not None and candidate.max_width() > max_width:
        return False

    return True


def merge_as_adjacent_path(
    left: DocumentTree,
    right: DocumentTree,
    model: DBSRModel,
) -> DocumentTree:
    merged = left.clone()

    if right.root_entity() in merged.entity_set():
        return merged

    attached = _attach_to_first_relationship_node(
        node=merged.root,
        child=right.root.clone(),
        model=model,
    )

    if not attached:
        raise ValueError(
            f"Cannot merge {left.signature()} with {right.signature()}: no attachable relationship."
        )

    return merged


def compact_plan(plan: QueryPlan) -> QueryPlan:
    compacted_steps: List[DocumentTree] = []

    for step in plan.steps:
        if any(step.is_entity_set_subset_of(existing) for existing in compacted_steps):
            continue
        compacted_steps.append(step)

    return QueryPlan(
        query_name=plan.query_name,
        sequence_id=plan.sequence_id,
        steps=compacted_steps,
        frequency=plan.frequency,
        filters=dict(plan.filters),
        required_secondary_indexes=list(plan.required_secondary_indexes),
        origin=f"{plan.origin}+inner_compaction_simplified",
    )


def merge_adjacent_step(
    plan: QueryPlan,
    step_index: int,
    model: DBSRModel,
    max_height_edges: Optional[int] = None,
    max_width: Optional[int] = None,
) -> Optional[QueryPlan]:
    if step_index < 0 or step_index >= len(plan.steps) - 1:
        return None

    left = plan.steps[step_index]
    right = plan.steps[step_index + 1]

    if not can_merge_as_adjacent_path(
        left=left,
        right=right,
        model=model,
        max_height_edges=max_height_edges,
        max_width=max_width,
    ):
        return None

    merged_doc = merge_as_adjacent_path(left, right, model)
    new_steps = plan.steps[:step_index] + [merged_doc] + plan.steps[step_index + 2:]

    return compact_plan(
        QueryPlan(
            query_name=plan.query_name,
            sequence_id=plan.sequence_id,
            steps=new_steps,
            frequency=plan.frequency,
            filters=dict(plan.filters),
            required_secondary_indexes=list(plan.required_secondary_indexes),
            origin=f"{plan.origin}+merge_step_{step_index}",
        )
    )


def generate_one_step_merges(plan: QueryPlan, model: DBSRModel) -> List[QueryPlan]:
    # DBSR's MaxDim height is interpreted as document-tree height in nodes.
    # DocumentTree.height_edges() is therefore compared with max_height_nodes - 1.
    max_height_edges = max(0, model.max_document_height() - 1)
    max_width = model.max_node_width()

    generated: List[QueryPlan] = []

    for idx in range(max(0, len(plan.steps) - 1)):
        candidate = merge_adjacent_step(
            plan=plan,
            step_index=idx,
            model=model,
            max_height_edges=max_height_edges,
            max_width=max_width,
        )
        if candidate is not None:
            generated.append(candidate)

    return generated
