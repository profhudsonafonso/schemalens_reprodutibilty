#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List


def plan_documents(plan_signature: str) -> List[str]:
    return [part.strip() for part in plan_signature.split(" -> ") if part.strip()]


def build_document_utility_matrix(pruned_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    matrix: List[Dict[str, Any]] = []

    for row in pruned_rows:
        documents = plan_documents(row["plan_signature"])
        if not documents:
            continue

        plan_utility = float(row["plan_utility"])
        contribution = plan_utility / len(documents)

        for doc in documents:
            matrix.append(
                {
                    "query_name": row["query_name"],
                    "sequence_id": row["sequence_id"],
                    "document_signature": doc,
                    "plan_signature": row["plan_signature"],
                    "plan_structural_cost": row["structural_cost"],
                    "plan_utility": row["plan_utility"],
                    "document_utility_contribution": round(contribution, 12),
                }
            )

    return matrix


def rank_documents(matrix_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    totals: Dict[str, float] = defaultdict(float)
    query_sets: Dict[str, set] = defaultdict(set)
    sequence_sets: Dict[str, set] = defaultdict(set)
    plan_sets: Dict[str, set] = defaultdict(set)

    for row in matrix_rows:
        doc = row["document_signature"]
        totals[doc] += float(row["document_utility_contribution"])
        query_sets[doc].add(row["query_name"])
        sequence_sets[doc].add(row["sequence_id"])
        plan_sets[doc].add(row["plan_signature"])

    ranked = []

    for doc, total in totals.items():
        ranked.append(
            {
                "document_signature": doc,
                "total_utility": round(total, 12),
                "queries_covered": len(query_sets[doc]),
                "sequences_covered": len(sequence_sets[doc]),
                "plans_using_document": len(plan_sets[doc]),
                "query_names": ";".join(sorted(query_sets[doc])),
                "sequence_ids": ";".join(sorted(sequence_sets[doc])),
            }
        )

    ranked.sort(
        key=lambda r: (
            -float(r["total_utility"]),
            -int(r["queries_covered"]),
            -int(r["sequences_covered"]),
            r["document_signature"],
        )
    )

    for idx, row in enumerate(ranked, start=1):
        row["rank"] = idx

    return ranked
