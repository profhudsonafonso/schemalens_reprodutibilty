#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple


def group_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (row["query_name"], row["sequence_id"])


def prune_query_plans(
    scored_rows: List[Dict[str, Any]],
    near_best_cost_ratio: float = 1.20,
    max_plans_per_sequence: int = 5,
) -> List[Dict[str, Any]]:
    grouped = defaultdict(list)

    for row in scored_rows:
        grouped[group_key(row)].append(row)

    pruned: List[Dict[str, Any]] = []

    for _, rows in grouped.items():
        ordered = sorted(
            rows,
            key=lambda r: (
                float(r["structural_cost"]),
                int(r["step_count"]),
                r["plan_signature"],
            ),
        )

        if not ordered:
            continue

        best_cost = float(ordered[0]["structural_cost"])

        for rank, row in enumerate(ordered, start=1):
            cost = float(row["structural_cost"])
            keep = rank <= max_plans_per_sequence or cost <= (best_cost * near_best_cost_ratio)

            new_row = dict(row)
            new_row["structural_rank_within_sequence"] = rank
            new_row["best_structural_cost_for_sequence"] = round(best_cost, 6)
            new_row["cost_ratio_to_best_sequence_plan"] = round(cost / best_cost, 6) if best_cost else 1.0
            new_row["is_best_structural_plan"] = "yes" if rank == 1 else "no"
            new_row["is_pruned_candidate"] = "yes" if keep else "no"

            if keep:
                pruned.append(new_row)

    return sorted(
        pruned,
        key=lambda r: (
            r["query_name"],
            r["sequence_id"],
            int(r["structural_rank_within_sequence"]),
        ),
    )
