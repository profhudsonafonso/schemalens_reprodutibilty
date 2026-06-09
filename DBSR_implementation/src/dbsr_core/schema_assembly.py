#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set


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


def normalize_collection_name(signature: str, rank: int) -> str:
    base = re.sub(r"[^A-Za-z0-9]+", "_", signature).strip("_").lower()
    base = re.sub(r"_+", "_", base)
    if not base:
        base = "document"
    return f"dbsr_rank{rank:02d}_{base}"[:120]


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


def assemble_schema_manifest(
    ranked_documents: List[RankedDocument],
    generated_documents_by_signature: Dict[str, Dict[str, Any]],
    top_k_documents: int,
) -> Dict[str, Any]:
    selected = ranked_documents[:top_k_documents]

    collections: List[Dict[str, Any]] = []
    covered_queries: Set[str] = set()
    covered_sequences: Set[str] = set()

    for item in selected:
        doc = generated_documents_by_signature.get(item.document_signature, {})
        entities = doc.get("entities", [])

        covered_queries.update(item.query_names)
        covered_sequences.update(item.sequence_ids)

        collections.append(
            {
                "rank": item.rank,
                "collection_name": normalize_collection_name(item.document_signature, item.rank),
                "document_signature": item.document_signature,
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
            }
        )

    total_utility = sum(item.total_utility for item in selected)

    return {
        "baseline": "DBSR",
        "dataset": "FIBEN",
        "manifest_type": "structural_schema_manifest",
        "version": "0.1-structural-topk",
        "selection_policy": {
            "source": "dbsr_ranked_schemas.csv",
            "top_k_documents": top_k_documents,
            "ranking_basis": "structural_proxy_utility",
            "physical_materialization": "not_performed_in_this_phase",
        },
        "summary": {
            "selected_documents": len(collections),
            "covered_queries": len(covered_queries),
            "covered_sequences": len(covered_sequences),
            "total_selected_utility": round(total_utility, 12),
            "query_names": sorted(covered_queries),
            "sequence_ids": sorted(covered_sequences),
        },
        "collections": collections,
        "implementation_assumptions": [
            "This manifest assembles a first DBSR structural recommendation from ranked document utilities.",
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
                "materialization_status": coll["materialization_status"],
                "tree_found_in_generated_documents": "yes" if coll["tree_found_in_generated_documents"] else "no",
            }
        )

    return rows
