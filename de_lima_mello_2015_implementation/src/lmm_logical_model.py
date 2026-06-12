"""
Core data structures for the de Lima & Mello (2015) implementation.

This module does not contain FIBEN-specific logic.
It defines reusable objects for:

- conceptual EER entities;
- conceptual EER relationships;
- workload operations;
- volume/load information;
- GAF/MAF computation outputs;
- NoSQL document logical schema;
- conversion decisions and explanations.

The goal is to keep the implementation traceable: every generated document
structure should later record which rule was applied and why.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple
import json


# ---------------------------------------------------------------------------
# Conceptual/EER-level structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EntityType:
    """Entity type in the conceptual schema."""

    name: str
    attributes: Tuple[str, ...] = ()
    identifier: str = "id"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RelationshipEnd:
    """
    One end of an EER relationship.

    min_cardinality and max_cardinality describe participation/cardinality.
    max_cardinality can be "1", "N", or another textual marker.
    """

    entity: str
    role: str = ""
    min_cardinality: int = 0
    max_cardinality: str = "N"

    def is_mandatory_one(self) -> bool:
        """True when participation is equivalent to (1,1)."""
        return self.min_cardinality == 1 and self.max_cardinality == "1"

    def is_to_many(self) -> bool:
        return self.max_cardinality.upper() in {"N", "*", "M"}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RelationshipType:
    """
    Relationship type in the conceptual schema.

    kind can be:
    - association
    - associative
    - containment
    - descriptor
    - generalization
    - other

    The implementation will use kind only as metadata. The Lima & Mello
    conversion rules are mainly driven by cardinality, participation, GAF,
    MAF and referenced-block constraints.
    """

    name: str
    ends: Tuple[RelationshipEnd, ...]
    attributes: Tuple[str, ...] = ()
    kind: str = "association"
    description: str = ""

    def arity(self) -> int:
        return len(self.ends)

    def is_binary(self) -> bool:
        return self.arity() == 2

    def entities(self) -> Tuple[str, ...]:
        return tuple(end.entity for end in self.ends)

    def end_for(self, entity_name: str) -> RelationshipEnd:
        for end in self.ends:
            if end.entity == entity_name:
                return end
        raise KeyError(f"Entity {entity_name!r} is not part of relationship {self.name!r}")

    def cardinality_class(self) -> str:
        """
        Return a simple cardinality class for binary relationships.

        Possible values:
        - "1:1"
        - "1:N"
        - "N:N"
        - "n-ary"
        """
        if not self.is_binary():
            return "n-ary"

        many_count = sum(1 for end in self.ends if end.is_to_many())
        if many_count == 0:
            return "1:1"
        if many_count == 1:
            return "1:N"
        return "N:N"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["cardinality_class"] = self.cardinality_class()
        return data


@dataclass
class ConceptualSchema:
    """Container for conceptual entities and relationships."""

    name: str
    entities: Dict[str, EntityType] = field(default_factory=dict)
    relationships: Dict[str, RelationshipType] = field(default_factory=dict)

    def add_entity(self, entity: EntityType) -> None:
        if entity.name in self.entities:
            raise ValueError(f"Duplicated entity: {entity.name}")
        self.entities[entity.name] = entity

    def add_relationship(self, relationship: RelationshipType) -> None:
        if relationship.name in self.relationships:
            raise ValueError(f"Duplicated relationship: {relationship.name}")

        missing = [e for e in relationship.entities() if e not in self.entities]
        if missing:
            raise ValueError(
                f"Relationship {relationship.name} references unknown entities: {missing}"
            )

        self.relationships[relationship.name] = relationship

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "relationships": {k: v.to_dict() for k, v in self.relationships.items()},
        }


# ---------------------------------------------------------------------------
# Workload and volume/load structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OperationStep:
    """
    One accessed conceptual type inside one workload operation.

    conceptual_type can be either an entity name or a relationship name.
    """

    conceptual_type: str
    type_kind: str  # "entity" or "relationship"
    order: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkloadOperation:
    """
    One workload operation.

    frequency is the average frequency in a chosen period, for example per day.
    steps preserves the conceptual access sequence used by Lima & Mello.
    """

    name: str
    frequency: float
    steps: Tuple[OperationStep, ...]
    query_id: str = ""
    operation_kind: str = "read"  # read, insert, update, delete
    description: str = ""

    def first_step(self) -> OperationStep:
        if not self.steps:
            raise ValueError(f"Operation {self.name} has no steps")
        return sorted(self.steps, key=lambda s: s.order)[0]

    def ordered_steps(self) -> Tuple[OperationStep, ...]:
        return tuple(sorted(self.steps, key=lambda s: s.order))

    def touched_types(self) -> Tuple[str, ...]:
        return tuple(step.conceptual_type for step in self.ordered_steps())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VolumeProfile:
    """
    Volume/load information for one dataset scale.

    entity_counts stores N(t).
    relationship_counts stores N(r), when available.
    avg_cardinalities stores Avg(tuple, relationship).

    The avg_cardinalities key format is textual and explicit:
    "<from_entity>|<relationship>|<to_entity>"
    """

    scale: str
    entity_counts: Dict[str, float] = field(default_factory=dict)
    relationship_counts: Dict[str, float] = field(default_factory=dict)
    avg_cardinalities: Dict[str, float] = field(default_factory=dict)

    @staticmethod
    def avg_key(from_entity: str, relationship: str, to_entity: str) -> str:
        return f"{from_entity}|{relationship}|{to_entity}"

    def get_avg(self, from_entity: str, relationship: str, to_entity: str) -> Optional[float]:
        return self.avg_cardinalities.get(self.avg_key(from_entity, relationship, to_entity))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AccessVolume:
    """
    Access-volume contribution of one operation to one conceptual type.
    """

    operation_name: str
    conceptual_type: str
    type_kind: str
    access_volume: float
    order: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GAFRecord:
    """
    General Access Frequency result for one conceptual type.
    """

    conceptual_type: str
    type_kind: str
    gaf: float
    maf: float
    is_frequent: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# NoSQL document logical model structures
# ---------------------------------------------------------------------------

@dataclass
class LogicalAttribute:
    """
    Attribute in the NoSQL document logical model.

    attr_type can be:
    - normal
    - identifier
    - reference
    """

    name: str
    attr_type: str = "normal"
    source_type: Optional[str] = None
    references_collection: Optional[str] = None
    references_attribute: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LogicalBlock:
    """
    Block in the NoSQL document logical model.

    A root block belongs directly to a collection.
    Inner blocks represent hierarchical relationships.
    """

    name: str
    source_type: Optional[str] = None
    attributes: List[LogicalAttribute] = field(default_factory=list)
    inner_blocks: List["LogicalBlock"] = field(default_factory=list)
    min_occurs: int = 1
    max_occurs: str = "1"
    disjoint_group: Optional[str] = None

    def add_attribute(self, attribute: LogicalAttribute) -> None:
        if any(a.name == attribute.name for a in self.attributes):
            return
        self.attributes.append(attribute)

    def add_inner_block(self, block: "LogicalBlock") -> None:
        if any(b.name == block.name for b in self.inner_blocks):
            return
        self.inner_blocks.append(block)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source_type": self.source_type,
            "attributes": [a.to_dict() for a in self.attributes],
            "inner_blocks": [b.to_dict() for b in self.inner_blocks],
            "min_occurs": self.min_occurs,
            "max_occurs": self.max_occurs,
            "disjoint_group": self.disjoint_group,
        }


@dataclass
class LogicalCollection:
    """Collection in the NoSQL document logical schema."""

    name: str
    root_block: LogicalBlock
    source_types: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "root_block": self.root_block.to_dict(),
            "source_types": self.source_types,
        }


@dataclass
class ConversionDecision:
    """
    Explanation record for one conversion decision.

    This is essential for the later paper text because it records why a
    relationship or hierarchy was mapped as embedding/reference/etc.
    """

    target_name: str
    target_kind: str  # entity, relationship, hierarchy
    applied_rule: str
    reason: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LogicalSchema:
    """
    Complete NoSQL document logical schema produced by the method.
    """

    name: str
    scale: str
    collections: List[LogicalCollection] = field(default_factory=list)
    decisions: List[ConversionDecision] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_collection(self, collection: LogicalCollection) -> None:
        if any(c.name == collection.name for c in self.collections):
            return
        self.collections.append(collection)

    def add_decision(self, decision: ConversionDecision) -> None:
        self.decisions.append(decision)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "scale": self.scale,
            "collections": [c.to_dict() for c in self.collections],
            "decisions": [d.to_dict() for d in self.decisions],
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def write_json(path: str, payload: Any) -> None:
    """Write dictionaries/dataclasses/lists to JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_to_plain(payload), f, indent=2, sort_keys=True)


def _to_plain(value: Any) -> Any:
    """Convert dataclasses and nested values to plain JSON-compatible objects."""
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]
    return value
