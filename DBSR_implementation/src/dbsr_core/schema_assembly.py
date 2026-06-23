#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


@dataclass
class RankedDocument:
    rank: int
    document_signature: str
    total_utility: float
    queries_covered: int
    sequences_covered: int
    plans_using_document: int
    query_names: List[str]
    sequence_ids: List[str]


def read_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def safe_json_loads(value: Any, default: Any) -> Any:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def split_semicolon(value: Any) -> List[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [item for item in text.split(";") if item]


def split_plan_signature(plan_signature: str) -> List[str]:
    return [part.strip() for part in str(plan_signature).split(" -> ") if part.strip()]


def normalize_collection_name(signature: str, manifest_rank: int) -> str:
    base = re.sub(r"[^A-Za-z0-9]+", "_", signature).strip("_").lower()
    base = re.sub(r"_+", "_", base)
    if not base:
        base = "document"
    return f"dbsr_rank{manifest_rank:02d}_{base}"[:120]


def load_ranked_documents(path: Path) -> List[RankedDocument]:
    rows = read_csv(path)
    ranked: List[RankedDocument] = []

    for row in rows:
        ranked.append(
            RankedDocument(
                rank=int(row["rank"]),
                document_signature=row["document_signature"],
                total_utility=float(row["total_utility"]),
                queries_covered=int(row["queries_covered"]),
                sequences_covered=int(row["sequences_covered"]),
                plans_using_document=int(row["plans_using_document"]),
                query_names=split_semicolon(row.get("query_names")),
                sequence_ids=split_semicolon(row.get("sequence_ids")),
            )
        )

    ranked.sort(key=lambda item: item.rank)
    return ranked


def load_generated_documents(path: Path) -> Dict[str, Dict[str, Any]]:
    rows = read_csv(path)
    by_signature: Dict[str, Dict[str, Any]] = {}

    for row in rows:
        signature = row["signature"]
        by_signature[signature] = {
            "signature": signature,
            "root_entity": row.get("root_entity", ""),
            "height_edges": int(row.get("height_edges") or 0),
            "max_width": int(row.get("max_width") or 0),
            "entities": safe_json_loads(row.get("entities_json"), []),
            "tree": safe_json_loads(row.get("tree_json"), {}),
        }

    return by_signature


def load_pruned_query_plans(path: Path) -> List[Dict[str, Any]]:
    rows = read_csv(path)

    for row in rows:
        row["plan_documents"] = split_plan_signature(row["plan_signature"])
        row["structural_cost_float"] = float(row.get("structural_cost") or 0.0)
        row["step_count_int"] = int(row.get("step_count") or len(row["plan_documents"]))
        row["rank_int"] = int(row.get("structural_rank_within_sequence") or 999999)

    return rows


def sequence_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (row["query_name"], row["sequence_id"])


def group_plans_by_sequence(pruned_plans: List[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}

    for row in pruned_plans:
        grouped.setdefault(sequence_key(row), []).append(row)

    for key in grouped:
        grouped[key].sort(
            key=lambda row: (
                row["rank_int"],
                row["structural_cost_float"],
                row["step_count_int"],
                row["plan_signature"],
            )
        )

    return grouped


def executable_sequences(
    selected_signatures: Set[str],
    pruned_plans: List[Dict[str, Any]],
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    grouped = group_plans_by_sequence(pruned_plans)
    result: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for key, plans in grouped.items():
        executable_plan = None

        for plan in plans:
            if set(plan["plan_documents"]).issubset(selected_signatures):
                executable_plan = plan
                break

        result[key] = {
            "query_name": key[0],
            "sequence_id": key[1],
            "is_executable": executable_plan is not None,
            "executable_plan_signature": executable_plan["plan_signature"] if executable_plan else "",
            "best_available_plan_signature": plans[0]["plan_signature"] if plans else "",
            "missing_documents_for_best_plan": [
                doc for doc in (plans[0]["plan_documents"] if plans else [])
                if doc not in selected_signatures
            ],
        }

    return result


def close_selection_for_executable_coverage(
    initial_selected: List[RankedDocument],
    ranked_documents: List[RankedDocument],
    pruned_plans: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    ranked_by_signature = {item.document_signature: item for item in ranked_documents}

    selected_signatures: Set[str] = {item.document_signature for item in initial_selected}
    selection_rows: List[Dict[str, Any]] = [
        {
            "document_signature": item.document_signature,
            "source_rank": item.rank,
            "selection_reason": "top_k_ranked_document",
            "added_for_query": "",
            "added_for_sequence": "",
            "added_from_plan": "",
        }
        for item in initial_selected
    ]

    grouped = group_plans_by_sequence(pruned_plans)

    for key, plans in sorted(grouped.items(), key=lambda item: item[0]):
        current = executable_sequences(selected_signatures, pruned_plans)[key]

        if current["is_executable"]:
            continue

        best_plan = plans[0]

        for doc_signature in best_plan["plan_documents"]:
            if doc_signature in selected_signatures:
                continue

            selected_signatures.add(doc_signature)
            ranked_doc = ranked_by_signature.get(doc_signature)

            selection_rows.append(
                {
                    "document_signature": doc_signature,
                    "source_rank": ranked_doc.rank if ranked_doc else 999999,
                    "selection_reason": "added_for_executable_sequence_coverage",
                    "added_for_query": key[0],
                    "added_for_sequence": key[1],
                    "added_from_plan": best_plan["plan_signature"],
                }
            )

    final_coverage = executable_sequences(selected_signatures, pruned_plans)

    query_to_sequences: Dict[str, List[bool]] = {}
    for item in final_coverage.values():
        query_to_sequences.setdefault(item["query_name"], []).append(bool(item["is_executable"]))

    executable_queries = {
        query for query, values in query_to_sequences.items()
        if values and all(values)
    }

    initial_coverage = executable_sequences(
        {item.document_signature for item in initial_selected},
        pruned_plans,
    )

    coverage_summary = {
        "initial_selected_documents": len(initial_selected),
        "final_selected_documents": len(selection_rows),
        "added_documents_for_executable_coverage": len(selection_rows) - len(initial_selected),
        "total_sequences": len(final_coverage),
        "initial_executable_sequences": sum(1 for item in initial_coverage.values() if item["is_executable"]),
        "final_executable_sequences": sum(1 for item in final_coverage.values() if item["is_executable"]),
        "total_queries": len(query_to_sequences),
        "final_executable_queries": len(executable_queries),
        "non_executable_sequences": [
            item for item in final_coverage.values()
            if not item["is_executable"]
        ],
    }

    return selection_rows, coverage_summary


def ranked_document_or_default(
    signature: str,
    ranked_by_signature: Dict[str, RankedDocument],
) -> RankedDocument:
    item = ranked_by_signature.get(signature)

    if item:
        return item

    return RankedDocument(
        rank=999999,
        document_signature=signature,
        total_utility=0.0,
        queries_covered=0,
        sequences_covered=0,
        plans_using_document=0,
        query_names=[],
        sequence_ids=[],
    )


def assemble_schema_manifest(
    ranked_documents: List[RankedDocument],
    generated_documents_by_signature: Dict[str, Dict[str, Any]],
    top_k_documents: int,
    pruned_query_plans: List[Dict[str, Any]],
    ensure_executable_coverage: bool = True,
) -> Dict[str, Any]:
    ranked_by_signature = {item.document_signature: item for item in ranked_documents}
    initial_selected = ranked_documents[:top_k_documents]

    if ensure_executable_coverage:
        selection_rows, coverage_summary = close_selection_for_executable_coverage(
            initial_selected=initial_selected,
            ranked_documents=ranked_documents,
            pruned_plans=pruned_query_plans,
        )
    else:
        selection_rows = [
            {
                "document_signature": item.document_signature,
                "source_rank": item.rank,
                "selection_reason": "top_k_ranked_document",
                "added_for_query": "",
                "added_for_sequence": "",
                "added_from_plan": "",
            }
            for item in initial_selected
        ]
        coverage_summary = {}

    collections: List[Dict[str, Any]] = []
    partial_covered_queries: Set[str] = set()
    partial_covered_sequences: Set[str] = set()

    for manifest_rank, selected in enumerate(selection_rows, start=1):
        signature = selected["document_signature"]
        item = ranked_document_or_default(signature, ranked_by_signature)
        doc = generated_documents_by_signature.get(signature, {})
        entities = doc.get("entities", [])

        partial_covered_queries.update(item.query_names)
        partial_covered_sequences.update(item.sequence_ids)

        collections.append(
            {
                "rank": manifest_rank,
                "source_rank": selected["source_rank"],
                "collection_name": normalize_collection_name(signature, manifest_rank),
                "document_signature": signature,
                "root_entity": doc.get("root_entity", ""),
                "embedded_or_included_entities": entities,
                "height_edges": doc.get("height_edges", ""),
                "max_width": doc.get("max_width", ""),
                "total_utility": item.total_utility,
                "queries_covered": item.queries_covered,
                "sequences_covered": item.sequences_covered,
                "plans_using_document": item.plans_using_document,
                "query_names": item.query_names,
                "sequence_ids": item.sequence_ids,
                "tree": doc.get("tree", {}),
                "tree_found_in_generated_documents": bool(doc),
                "materialization_status": "not_materialized",
                "selection_reason": selected["selection_reason"],
                "added_for_query": selected["added_for_query"],
                "added_for_sequence": selected["added_for_sequence"],
                "added_from_plan": selected["added_from_plan"],
            }
        )

    total_utility = sum(float(coll["total_utility"]) for coll in collections)

    summary = {
        "selected_documents": len(collections),
        "initial_top_k_documents": top_k_documents,
        "added_documents_for_executable_coverage": coverage_summary.get("added_documents_for_executable_coverage", 0),
        "partial_covered_queries": len(partial_covered_queries),
        "partial_covered_sequences": len(partial_covered_sequences),
        "executable_queries": coverage_summary.get("final_executable_queries", None),
        "executable_sequences": coverage_summary.get("final_executable_sequences", None),
        "total_sequences": coverage_summary.get("total_sequences", None),
        "non_executable_sequences": coverage_summary.get("non_executable_sequences", []),
        "total_selected_utility": round(total_utility, 12),
        "query_names": sorted(partial_covered_queries),
        "sequence_ids": sorted(partial_covered_sequences),
    }

    return {
        "baseline": "DBSR",
        "dataset": "FIBEN",
        "manifest_type": "structural_schema_manifest_executable_coverage",
        "version": "0.2-structural-topk-plus-coverage-closure",
        "selection_policy": {
            "source": "dbsr_ranked_schemas.csv + dbsr_pruned_query_plans.csv",
            "top_k_documents": top_k_documents,
            "ranking_basis": "structural_proxy_utility",
            "coverage_policy": "add_documents_from_best_pruned_plan_until_each_sequence_is_executable",
            "physical_materialization": "not_performed_in_this_phase",
        },
        "summary": summary,
        "coverage_summary": coverage_summary,
        "collections": collections,
        "implementation_assumptions": [
            "This manifest starts from top-k ranked DBSR documents and then closes the selection for executable sequence coverage.",
            "A sequence is executable when at least one pruned query plan can be expressed using only selected documents.",
            "This avoids confusing partial document coverage with full query executability.",
            "It does not resolve physical duplication conflicts yet.",
            "It does not create MongoDB collections yet.",
            "Overlapping document structures are allowed in this structural manifest and must be resolved or explicitly materialized in a later phase.",
            "The manifest is independent from SchemaLens G0-G9 templates.",
        ],
    }


def manifest_to_rows(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for coll in manifest.get("collections", []):
        rows.append(
            {
                "rank": coll["rank"],
                "source_rank": coll["source_rank"],
                "collection_name": coll["collection_name"],
                "document_signature": coll["document_signature"],
                "root_entity": coll["root_entity"],
                "embedded_or_included_entities": json.dumps(coll["embedded_or_included_entities"], ensure_ascii=False),
                "height_edges": coll["height_edges"],
                "max_width": coll["max_width"],
                "total_utility": coll["total_utility"],
                "queries_covered": coll["queries_covered"],
                "sequences_covered": coll["sequences_covered"],
                "plans_using_document": coll["plans_using_document"],
                "query_names": ";".join(coll["query_names"]),
                "sequence_ids": ";".join(coll["sequence_ids"]),
                "selection_reason": coll["selection_reason"],
                "added_for_query": coll["added_for_query"],
                "added_for_sequence": coll["added_for_sequence"],
                "added_from_plan": coll["added_from_plan"],
                "materialization_status": coll["materialization_status"],
                "tree_found_in_generated_documents": "yes" if coll["tree_found_in_generated_documents"] else "no",
            }
        )

    return rows
