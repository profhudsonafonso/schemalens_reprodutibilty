#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


@dataclass
class DocumentNode:
    entity: str
    children: List["DocumentNode"] = field(default_factory=list)

    def add_child(self, child: "DocumentNode") -> None:
        self.children.append(child)

    def clone(self) -> "DocumentNode":
        return DocumentNode(
            entity=self.entity,
            children=[child.clone() for child in self.children],
        )

    def entities_preorder(self) -> List[str]:
        values = [self.entity]
        for child in self.children:
            values.extend(child.entities_preorder())
        return values

    def entity_set(self) -> Set[str]:
        return set(self.entities_preorder())

    def height_nodes(self) -> int:
        if not self.children:
            return 1
        return 1 + max(child.height_nodes() for child in self.children)

    def max_width(self) -> int:
        child_width = len(self.children)
        if not self.children:
            return child_width
        return max(child_width, max(child.max_width() for child in self.children))

    def signature(self) -> str:
        if not self.children:
            return self.entity
        children_sig = ",".join(child.signature() for child in self.children)
        return f"{self.entity}|{{{children_sig}}}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity": self.entity,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class DocumentTree:
    root: DocumentNode

    @classmethod
    def single(cls, entity: str) -> "DocumentTree":
        return cls(root=DocumentNode(entity=entity))

    @classmethod
    def from_path(cls, path: List[str]) -> "DocumentTree":
        if not path:
            raise ValueError("Cannot create DocumentTree from empty path.")

        root = DocumentNode(entity=path[0])
        current = root

        for entity in path[1:]:
            child = DocumentNode(entity=entity)
            current.add_child(child)
            current = child

        return cls(root=root)

    def clone(self) -> "DocumentTree":
        return DocumentTree(root=self.root.clone())

    def root_entity(self) -> str:
        return self.root.entity

    def entities_preorder(self) -> List[str]:
        return self.root.entities_preorder()

    def entity_set(self) -> Set[str]:
        return self.root.entity_set()

    def contains_entity(self, entity: str) -> bool:
        return entity in self.entity_set()

    def height_nodes(self) -> int:
        return self.root.height_nodes()

    def height_edges(self) -> int:
        return max(0, self.height_nodes() - 1)

    def max_width(self) -> int:
        return self.root.max_width()

    def signature(self) -> str:
        return self.root.signature()

    def to_dict(self) -> Dict[str, Any]:
        return self.root.to_dict()

    def is_entity_set_subset_of(self, other: "DocumentTree") -> bool:
        return self.entity_set().issubset(other.entity_set())
