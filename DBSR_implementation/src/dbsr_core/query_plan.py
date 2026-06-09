#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from dbsr_core.document_tree import DocumentTree


@dataclass(frozen=True)
class QuerySequence:
    query_name: str
    sequence_id: str
    path: List[str]
    frequency: float = 1.0
    intent: str = ""

    def length(self) -> int:
        return len(self.path)


@dataclass
class QueryPlan:
    query_name: str
    sequence_id: str
    steps: List[DocumentTree]
    frequency: float = 1.0
    required_secondary_indexes: List[str] = field(default_factory=list)
    origin: str = "initial_single_level_documents"

    def step_count(self) -> int:
        return len(self.steps)

    def query_length(self) -> int:
        return self.step_count()

    def signature(self) -> str:
        return " -> ".join(step.signature() for step in self.steps)

    def documents_used(self) -> List[str]:
        return [step.signature() for step in self.steps]

    def to_row(self) -> Dict[str, Any]:
        return {
            "query_name": self.query_name,
            "sequence_id": self.sequence_id,
            "frequency": self.frequency,
            "step_count": self.step_count(),
            "plan_signature": self.signature(),
            "required_secondary_indexes": json.dumps(self.required_secondary_indexes),
            "origin": self.origin,
            "steps_json": json.dumps([step.to_dict() for step in self.steps], ensure_ascii=False),
        }


def load_reviewed_sequences(path: Path) -> List[QuerySequence]:
    with path.open("r", encoding="utf-8") as f:
        workload = json.load(f)

    sequences: List[QuerySequence] = []

    for query in workload.get("queries", []):
        qname = query["query_name"]
        frequency = float(query.get("frequency", 1.0))

        for seq in query.get("dbsr_sequences", []):
            sequences.append(
                QuerySequence(
                    query_name=qname,
                    sequence_id=seq["sequence_id"],
                    path=list(seq["path"]),
                    frequency=frequency,
                    intent=seq.get("intent", ""),
                )
            )

    return sequences


def initial_plan_for_sequence(sequence: QuerySequence) -> QueryPlan:
    return QueryPlan(
        query_name=sequence.query_name,
        sequence_id=sequence.sequence_id,
        steps=[DocumentTree.single(entity) for entity in sequence.path],
        frequency=sequence.frequency,
        required_secondary_indexes=[],
        origin="initial_single_level_documents",
    )


def initial_documents_for_sequences(sequences: Iterable[QuerySequence]) -> List[DocumentTree]:
    signatures: Dict[str, DocumentTree] = {}

    for sequence in sequences:
        for entity in sequence.path:
            doc = DocumentTree.single(entity)
            signatures.setdefault(doc.signature(), doc)

    return [signatures[sig] for sig in sorted(signatures)]


def initial_plans_for_sequences(sequences: Iterable[QuerySequence]) -> List[QueryPlan]:
    return [initial_plan_for_sequence(sequence) for sequence in sequences]


def write_documents_csv(documents: List[DocumentTree], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "document_id",
                "signature",
                "root_entity",
                "height_edges",
                "max_width",
                "entities_json",
                "tree_json",
            ],
        )
        writer.writeheader()

        for idx, document in enumerate(documents, start=1):
            writer.writerow(
                {
                    "document_id": f"D{idx}",
                    "signature": document.signature(),
                    "root_entity": document.root_entity(),
                    "height_edges": document.height_edges(),
                    "max_width": document.max_width(),
                    "entities_json": json.dumps(document.entities_preorder(), ensure_ascii=False),
                    "tree_json": json.dumps(document.to_dict(), ensure_ascii=False),
                }
            )


def write_query_plans_csv(plans: List[QueryPlan], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "query_name",
                "sequence_id",
                "frequency",
                "step_count",
                "plan_signature",
                "required_secondary_indexes",
                "origin",
                "steps_json",
            ],
        )
        writer.writeheader()

        for plan in plans:
            writer.writerow(plan.to_row())


def summarize_initial_artifacts(
    sequences: List[QuerySequence],
    documents: List[DocumentTree],
    plans: List[QueryPlan],
) -> Dict[str, Any]:
    return {
        "sequences": len(sequences),
        "initial_documents": len(documents),
        "initial_query_plans": len(plans),
        "max_initial_plan_steps": max((plan.step_count() for plan in plans), default=0),
        "queries": sorted({sequence.query_name for sequence in sequences}),
    }
