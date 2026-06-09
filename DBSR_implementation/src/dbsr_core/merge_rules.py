#!/usr/bin/env python3
from __future__ import annotations

from typing import List, Optional

from dbsr_core.document_tree import DocumentNode, DocumentTree
from dbsr_core.model import DBSRModel
from dbsr_core.query_plan import QueryPlan


def _attach_child_to_first_matching_leaf(
    node: DocumentNode,
    parent_entity: str,
    child: DocumentNode,
) -> bool:
    if node.entity == parent_entity:
        node.add_child(child)
        return True

    for existing_child in node.children:
        if _attach_child_to_first_matching_leaf(existing_child, parent_entity, child):
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

    if model.relationship_between(left.root_entity(), right.root_entity()) is None:
        return False

    candidate = merge_as_adjacent_path(left, right)

    if max_height_edges is not None and candidate.height_edges() > max_height_edges:
        return False

    if max_width is not None and candidate.max_width() > max_width:
        return False

    return True


def merge_as_adjacent_path(left: DocumentTree, right: DocumentTree) -> DocumentTree:
    merged = left.clone()

    if right.root_entity() in merged.entity_set():
        return merged

    # Minimal DBSR-faithful first implementation:
    # merge the next document as an embedded child under the current root.
    # Later phases will extend this to largest-overlap and leaf-to-root merge.
    merged.root.add_child(right.root.clone())
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

    merged_doc = merge_as_adjacent_path(left, right)
    new_steps = plan.steps[:step_index] + [merged_doc] + plan.steps[step_index + 2:]

    return compact_plan(
        QueryPlan(
            query_name=plan.query_name,
            sequence_id=plan.sequence_id,
            steps=new_steps,
            frequency=plan.frequency,
            required_secondary_indexes=list(plan.required_secondary_indexes),
            origin=f"{plan.origin}+merge_step_{step_index}",
        )
    )


def generate_one_step_merges(plan: QueryPlan, model: DBSRModel) -> List[QueryPlan]:
    max_height_edges = model.max_document_height()
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
