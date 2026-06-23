#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import Any, Dict, List


def safe_json_loads(value: Any, default: Any) -> Any:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def count_entities(tree: Dict[str, Any]) -> int:
    return 1 + sum(count_entities(child) for child in tree.get("children", []))


def height_nodes(tree: Dict[str, Any]) -> int:
    children = tree.get("children", [])
    if not children:
        return 1
    return 1 + max(height_nodes(child) for child in children)


def height_edges(tree: Dict[str, Any]) -> int:
    return max(0, height_nodes(tree) - 1)


def max_width(tree: Dict[str, Any]) -> int:
    children = tree.get("children", [])
    if not children:
        return 0
    return max(len(children), max(max_width(child) for child in children))


def document_structural_cost(tree: Dict[str, Any]) -> float:
    entity_count = count_entities(tree)
    h_edges = height_edges(tree)
    width = max_width(tree)

    # Structural proxy:
    # - each entity adds payload;
    # - deeper trees add nested traversal/maintenance cost;
    # - wider nodes add fan-out/array complexity.
    return 1.0 + (0.75 * max(0, entity_count - 1)) + (0.50 * h_edges) + (0.25 * width)


def score_query_plan_row(row: Dict[str, Any]) -> Dict[str, Any]:
    steps = safe_json_loads(row.get("steps_json"), [])
    filters = safe_json_loads(row.get("filters_json"), {})

    step_count = int(row.get("step_count") or len(steps))
    join_steps = max(0, step_count - 1)

    document_costs = [document_structural_cost(step) for step in steps]

    # First structural cost approximation.
    # Lower step_count is rewarded, but larger embedded documents are penalized.
    structural_cost = (
        (10.0 * step_count)
        + (5.0 * join_steps)
        + sum(document_costs)
        + (0.25 * len(filters))
    )

    frequency = float(row.get("frequency") or 1.0)
    utility = frequency / (1.0 + structural_cost)

    return {
        "structural_cost": round(structural_cost, 6),
        "plan_utility": round(utility, 12),
        "join_steps": join_steps,
        "document_count": len(steps),
        "total_document_structural_cost": round(sum(document_costs), 6),
        "filter_count": len(filters),
    }
