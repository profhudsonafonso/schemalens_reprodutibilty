#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from dbsr_core.document_tree import DocumentTree
from dbsr_core.merge_rules import generate_one_step_merges
from dbsr_core.model import DBSRModel
from dbsr_core.query_plan import QueryPlan


@dataclass
class DBSRGenerationResult:
    documents: List[DocumentTree]
    query_plans: List[QueryPlan]
    summary: Dict[str, Any]


def _plan_key(plan: QueryPlan) -> Tuple[str, str, str]:
    return (plan.query_name, plan.sequence_id, plan.signature())


def _collect_documents_from_plan(plan: QueryPlan, documents_by_signature: Dict[str, DocumentTree]) -> None:
    for document in plan.steps:
        documents_by_signature.setdefault(document.signature(), document)


def run_iterative_generator(
    initial_plans: List[QueryPlan],
    model: DBSRModel,
    max_iterations: int | None = None,
) -> DBSRGenerationResult:
    if max_iterations is None:
        max_iterations = int(model.run_configuration.get("max_iterations", 4000))

    stack: List[QueryPlan] = list(initial_plans)
    seen_plan_keys = set()
    query_plans_by_key: Dict[Tuple[str, str, str], QueryPlan] = {}
    documents_by_signature: Dict[str, DocumentTree] = {}

    iterations = 0
    generated_candidate_count = 0
    skipped_duplicate_plans = 0

    while stack and iterations < max_iterations:
        plan = stack.pop(0)
        key = _plan_key(plan)

        if key in seen_plan_keys:
            skipped_duplicate_plans += 1
            continue

        seen_plan_keys.add(key)
        query_plans_by_key[key] = plan
        _collect_documents_from_plan(plan, documents_by_signature)

        new_plans = generate_one_step_merges(plan, model)
        generated_candidate_count += len(new_plans)

        for candidate in new_plans:
            candidate_key = _plan_key(candidate)
            if candidate_key not in seen_plan_keys:
                stack.append(candidate)

        iterations += 1

    documents = [documents_by_signature[sig] for sig in sorted(documents_by_signature)]
    query_plans = sorted(
        query_plans_by_key.values(),
        key=lambda p: (p.query_name, p.sequence_id, p.step_count(), p.signature()),
    )

    summary = {
        "iterations_executed": iterations,
        "max_iterations": max_iterations,
        "stopped_because": "stack_empty" if not stack else "max_iterations_reached",
        "remaining_stack_size": len(stack),
        "generated_candidate_count": generated_candidate_count,
        "skipped_duplicate_plans": skipped_duplicate_plans,
        "generated_documents": len(documents),
        "generated_query_plans": len(query_plans),
        "min_plan_steps": min((p.step_count() for p in query_plans), default=0),
        "max_plan_steps": max((p.step_count() for p in query_plans), default=0),
        "implementation_status": "phase_2b_simplified_iterative_generator",
        "implementation_assumptions": [
            "This phase implements an iterative per-plan merge loop.",
            "It does not yet implement full DBSR global notification of all relevant query plans when a novel document is generated.",
            "It does not yet implement cost-based pruning or utility ranking.",
            "It interprets DBSR MaxDim height as document-tree height in nodes.",
        ],
    }

    return DBSRGenerationResult(
        documents=documents,
        query_plans=query_plans,
        summary=summary,
    )
