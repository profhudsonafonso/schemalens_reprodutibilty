#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Entity:
    name: str
    source_view: str
    primary_key: str
    fields_policy: str = "all_fields_available_projection_refined_later"


@dataclass(frozen=True)
class Relationship:
    id: str
    source_entity: str
    target_entity: str
    source_column: str
    target_column: str
    type: str = "direct"
    dbsr_role: str = "join_edge"

    def connects(self, left: str, right: str) -> bool:
        return (
            (self.source_entity == left and self.target_entity == right)
            or (self.source_entity == right and self.target_entity == left)
        )

    def direction_for(self, left: str, right: str) -> str:
        if self.source_entity == left and self.target_entity == right:
            return "forward"
        if self.source_entity == right and self.target_entity == left:
            return "reverse"
        return "not_connected"


@dataclass
class DBSRModel:
    dataset: str
    entities: Dict[str, Entity]
    relationships: List[Relationship]
    run_configuration: Dict[str, Any]
    implementation_assumptions: List[Dict[str, str]]

    @classmethod
    def from_json(cls, path: Path) -> "DBSRModel":
        with path.open("r", encoding="utf-8") as f:
            obj = json.load(f)

        entities = {
            e["name"]: Entity(
                name=e["name"],
                source_view=e.get("source_view", ""),
                primary_key=e.get("primary_key", ""),
                fields_policy=e.get("fields_policy", "all_fields_available_projection_refined_later"),
            )
            for e in obj.get("entities", [])
        }

        relationships = [
            Relationship(
                id=r["id"],
                source_entity=r["source_entity"],
                target_entity=r["target_entity"],
                source_column=r["source_column"],
                target_column=r["target_column"],
                type=r.get("type", "direct"),
                dbsr_role=r.get("dbsr_role", "join_edge"),
            )
            for r in obj.get("relationships", [])
        ]

        return cls(
            dataset=obj.get("dataset", ""),
            entities=entities,
            relationships=relationships,
            run_configuration=obj.get("run_configuration", {}),
            implementation_assumptions=obj.get("implementation_assumptions", []),
        )

    def get_entity(self, name: str) -> Entity:
        if name not in self.entities:
            raise KeyError(f"Unknown entity in DBSR model: {name}")
        return self.entities[name]

    def relationship_between(self, left: str, right: str) -> Optional[Relationship]:
        for rel in self.relationships:
            if rel.connects(left, right):
                return rel
        return None

    def validate_path(self, path: List[str]) -> List[str]:
        errors: List[str] = []

        if not path:
            errors.append("Empty path.")
            return errors

        for entity in path:
            if entity not in self.entities:
                errors.append(f"Unknown entity: {entity}")

        for left, right in zip(path, path[1:]):
            if self.relationship_between(left, right) is None:
                errors.append(f"No relationship found between {left} and {right}")

        return errors

    def max_document_height(self) -> int:
        return int(self.run_configuration.get("max_document_height", 3))

    def max_node_width(self) -> int:
        return int(self.run_configuration.get("max_node_width", 2))
