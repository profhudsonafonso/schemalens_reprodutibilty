"""
FIBEN conceptual schema for the de Lima & Mello (2015) implementation.

This module reuses the same FIBEN conceptual layer used in the SchemaLens
methodology, but represents it in the data structures required by the
Lima & Mello workload-driven logical design method.

Methodological decision:
- The conceptual entities and relationships are shared with SchemaLens.
- Lima & Mello-specific information is added here: relationship ends,
  cardinality class, participation constraints, and relationship attributes
  when needed.
"""

from __future__ import annotations

from typing import Dict, List

try:
    from .lmm_logical_model import (
        ConceptualSchema,
        EntityType,
        RelationshipEnd,
        RelationshipType,
    )
except ImportError:
    from lmm_logical_model import (
        ConceptualSchema,
        EntityType,
        RelationshipEnd,
        RelationshipType,
    )


FIBEN_ENTITY_NAMES: List[str] = [
    "Corporation",
    "Industry",
    "Country",
    "Security",
    "ListedSecurity",
    "Person",
    "FinancialServiceAccount",
    "Holding",
    "Transaction",
    "BuyTransaction",
    "SellTransaction",
    "FinancialReport",
    "ReportElement",
    "StatementElement",
    "Disclosure",
]


def build_fiben_conceptual_schema() -> ConceptualSchema:
    """
    Build the FIBEN conceptual schema used by the Lima & Mello baseline.

    Cardinalities are encoded at a logical/conceptual level and may be refined
    later after inspecting the official FIBEN CSV columns and observed counts.

    The goal of this first version is to preserve the same conceptual graph used
    by SchemaLens while adding enough relationship metadata for the Lima & Mello
    conversion rules.
    """
    schema = ConceptualSchema(name="FIBEN_Lima_Mello_Conceptual_Schema")

    # ---------------------------------------------------------------------
    # Entities
    # ---------------------------------------------------------------------
    for entity_name in FIBEN_ENTITY_NAMES:
        schema.add_entity(
            EntityType(
                name=entity_name,
                identifier="id",
                attributes=(),
                description=f"FIBEN conceptual entity: {entity_name}",
            )
        )

    # ---------------------------------------------------------------------
    # Corporation profile descriptors
    # ---------------------------------------------------------------------
    schema.add_relationship(
        RelationshipType(
            name="corporation_has_industry",
            kind="descriptor",
            ends=(
                RelationshipEnd(
                    entity="Corporation",
                    role="corporation",
                    min_cardinality=0,
                    max_cardinality="N",
                ),
                RelationshipEnd(
                    entity="Industry",
                    role="industry",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
            ),
            description="A corporation is associated with an industry descriptor.",
        )
    )

    schema.add_relationship(
        RelationshipType(
            name="corporation_has_country",
            kind="descriptor",
            ends=(
                RelationshipEnd(
                    entity="Corporation",
                    role="corporation",
                    min_cardinality=0,
                    max_cardinality="N",
                ),
                RelationshipEnd(
                    entity="Country",
                    role="country",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
            ),
            description="A corporation is associated with a country descriptor.",
        )
    )

    # ---------------------------------------------------------------------
    # Securities and listing structure
    # ---------------------------------------------------------------------
    schema.add_relationship(
        RelationshipType(
            name="corporation_has_listed_security",
            kind="association",
            ends=(
                RelationshipEnd(
                    entity="Corporation",
                    role="issuer",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
                RelationshipEnd(
                    entity="ListedSecurity",
                    role="listed_security",
                    min_cardinality=0,
                    max_cardinality="N",
                ),
            ),
            description="A corporation may have multiple listed securities.",
        )
    )

    schema.add_relationship(
        RelationshipType(
            name="listed_security_represents_security",
            kind="association",
            ends=(
                RelationshipEnd(
                    entity="ListedSecurity",
                    role="listed_security",
                    min_cardinality=0,
                    max_cardinality="N",
                ),
                RelationshipEnd(
                    entity="Security",
                    role="security",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
            ),
            description="A listed security refers to an underlying security.",
        )
    )

    # ---------------------------------------------------------------------
    # Person/account/holding investment structure
    # ---------------------------------------------------------------------
    schema.add_relationship(
        RelationshipType(
            name="person_owns_financial_service_account",
            kind="ownership",
            ends=(
                RelationshipEnd(
                    entity="Person",
                    role="owner",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
                RelationshipEnd(
                    entity="FinancialServiceAccount",
                    role="account",
                    min_cardinality=0,
                    max_cardinality="N",
                ),
            ),
            description="A person may own financial service accounts.",
        )
    )

    schema.add_relationship(
        RelationshipType(
            name="account_has_holding",
            kind="containment",
            ends=(
                RelationshipEnd(
                    entity="FinancialServiceAccount",
                    role="account",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
                RelationshipEnd(
                    entity="Holding",
                    role="holding",
                    min_cardinality=0,
                    max_cardinality="N",
                ),
            ),
            description="An account contains holdings.",
        )
    )

    schema.add_relationship(
        RelationshipType(
            name="holding_refers_to_listed_security",
            kind="association",
            ends=(
                RelationshipEnd(
                    entity="Holding",
                    role="holding",
                    min_cardinality=0,
                    max_cardinality="N",
                ),
                RelationshipEnd(
                    entity="ListedSecurity",
                    role="listed_security",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
            ),
            description="A holding refers to a listed security.",
        )
    )

    # ---------------------------------------------------------------------
    # Transactions
    # ---------------------------------------------------------------------
    schema.add_relationship(
        RelationshipType(
            name="account_records_transaction",
            kind="containment",
            ends=(
                RelationshipEnd(
                    entity="FinancialServiceAccount",
                    role="account",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
                RelationshipEnd(
                    entity="Transaction",
                    role="transaction",
                    min_cardinality=0,
                    max_cardinality="N",
                ),
            ),
            description="An account records transactions.",
        )
    )

    schema.add_relationship(
        RelationshipType(
            name="transaction_refers_to_listed_security",
            kind="association",
            ends=(
                RelationshipEnd(
                    entity="Transaction",
                    role="transaction",
                    min_cardinality=0,
                    max_cardinality="N",
                ),
                RelationshipEnd(
                    entity="ListedSecurity",
                    role="listed_security",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
            ),
            description="A transaction refers to the listed security traded.",
        )
    )

    # Generalization-like structure for transaction subtypes.
    schema.add_relationship(
        RelationshipType(
            name="buy_transaction_is_transaction",
            kind="generalization",
            ends=(
                RelationshipEnd(
                    entity="Transaction",
                    role="superclass",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
                RelationshipEnd(
                    entity="BuyTransaction",
                    role="subclass",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
            ),
            description="BuyTransaction is modeled as a subtype of Transaction.",
        )
    )

    schema.add_relationship(
        RelationshipType(
            name="sell_transaction_is_transaction",
            kind="generalization",
            ends=(
                RelationshipEnd(
                    entity="Transaction",
                    role="superclass",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
                RelationshipEnd(
                    entity="SellTransaction",
                    role="subclass",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
            ),
            description="SellTransaction is modeled as a subtype of Transaction.",
        )
    )

    # ---------------------------------------------------------------------
    # Financial reporting structure
    # ---------------------------------------------------------------------
    schema.add_relationship(
        RelationshipType(
            name="corporation_has_financial_report",
            kind="containment",
            ends=(
                RelationshipEnd(
                    entity="Corporation",
                    role="corporation",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
                RelationshipEnd(
                    entity="FinancialReport",
                    role="financial_report",
                    min_cardinality=0,
                    max_cardinality="N",
                ),
            ),
            description="A corporation has financial reports.",
        )
    )

    schema.add_relationship(
        RelationshipType(
            name="financial_report_contains_report_element",
            kind="containment",
            ends=(
                RelationshipEnd(
                    entity="FinancialReport",
                    role="financial_report",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
                RelationshipEnd(
                    entity="ReportElement",
                    role="report_element",
                    min_cardinality=0,
                    max_cardinality="N",
                ),
            ),
            description="A financial report contains report elements.",
        )
    )

    schema.add_relationship(
        RelationshipType(
            name="report_element_has_statement_element",
            kind="containment",
            ends=(
                RelationshipEnd(
                    entity="ReportElement",
                    role="report_element",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
                RelationshipEnd(
                    entity="StatementElement",
                    role="statement_element",
                    min_cardinality=0,
                    max_cardinality="N",
                ),
            ),
            description="A report element has statement elements.",
        )
    )

    schema.add_relationship(
        RelationshipType(
            name="financial_report_contains_disclosure",
            kind="containment",
            ends=(
                RelationshipEnd(
                    entity="FinancialReport",
                    role="financial_report",
                    min_cardinality=0,
                    max_cardinality="1",
                ),
                RelationshipEnd(
                    entity="Disclosure",
                    role="disclosure",
                    min_cardinality=0,
                    max_cardinality="N",
                ),
            ),
            description="A financial report contains disclosures.",
        )
    )

    return schema


def conceptual_schema_summary() -> Dict[str, object]:
    """Return a compact summary useful for tests and README reporting."""
    schema = build_fiben_conceptual_schema()
    return {
        "schema_name": schema.name,
        "n_entities": len(schema.entities),
        "n_relationships": len(schema.relationships),
        "entities": sorted(schema.entities.keys()),
        "relationships": {
            name: {
                "kind": rel.kind,
                "entities": rel.entities(),
                "cardinality_class": rel.cardinality_class(),
            }
            for name, rel in sorted(schema.relationships.items())
        },
    }


if __name__ == "__main__":
    import json

    print(json.dumps(conceptual_schema_summary(), indent=2, sort_keys=True))
