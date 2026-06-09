#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional


ENTITY_VIEW_MAP = {
    "Corporation": "fiben_corporations",
    "Industry": "fiben_industries",
    "Country": "fiben_countries",
    "Security": "fiben_securities",
    "ListedSecurity": "fiben_listed_securities",
    "Person": "fiben_persons",
    "FinancialServiceAccount": "fiben_financial_service_accounts",
    "Holding": "fiben_holdings",
    "Transaction": "fiben_transactions",
    "BuyTransaction": "fiben_transactions",
    "SellTransaction": "fiben_transactions",
    "FinancialReport": "fiben_reports",
    "ReportElement": "fiben_report_elements",
    "StatementElement": "fiben_statement_elements",
    "Disclosure": "fiben_disclosures",
}

ENTITY_PK_MAP = {
    "Corporation": "CORPORATIONID",
    "Industry": "INDUSTRYSECTORCLASSIFIERID",
    "Country": "COUNTRYID",
    "Security": "SECURITYID",
    "ListedSecurity": "LISTEDSECURITYID",
    "Person": "PERSONID",
    "FinancialServiceAccount": "FINANCIALSERVICEACCOUNTID",
    "Holding": "HOLDINGID",
    "Transaction": "SECURITIESTRANSACTIONID",
    "BuyTransaction": "SECURITIESTRANSACTIONID",
    "SellTransaction": "SECURITIESTRANSACTIONID",
    "FinancialReport": "FINANCIALREPORTID",
    "ReportElement": "ELEMENTSOFFINANCIALREPORTID",
    "StatementElement": "ELEMENTOFFINANCIALSTATEMENTID",
    "Disclosure": "DISCLOSUREID",
}

RELATIONSHIPS = [
    {
        "id": "corporation_has_industry",
        "type": "direct",
        "source_entity": "Corporation",
        "target_entity": "Industry",
        "source_column": "ISCLASSIFIEDBY",
        "target_column": "INDUSTRYSECTORCLASSIFIERID",
        "dbsr_role": "join_edge",
    },
    {
        "id": "corporation_has_country",
        "type": "direct",
        "source_entity": "Corporation",
        "target_entity": "Country",
        "source_column": "ISDOMICILEDIN",
        "target_column": "COUNTRYID",
        "dbsr_role": "join_edge",
    },
    {
        "id": "corporation_has_security",
        "type": "reverse_direct",
        "source_entity": "Corporation",
        "target_entity": "Security",
        "source_column": "CORPORATIONID",
        "target_column": "ISPROVIDEDBY",
        "dbsr_role": "join_edge",
    },
    {
        "id": "security_has_listed_security",
        "type": "direct",
        "source_entity": "Security",
        "target_entity": "ListedSecurity",
        "source_column": "ISTRADEDON",
        "target_column": "LISTEDSECURITYID",
        "dbsr_role": "join_edge",
    },
    {
        "id": "person_owns_financial_service_account",
        "type": "reverse_direct",
        "source_entity": "Person",
        "target_entity": "FinancialServiceAccount",
        "source_column": "PERSONID",
        "target_column": "ISOWNEDBY",
        "dbsr_role": "join_edge",
    },
    {
        "id": "account_has_holding",
        "type": "reverse_direct",
        "source_entity": "FinancialServiceAccount",
        "target_entity": "Holding",
        "source_column": "FINANCIALSERVICEACCOUNTID",
        "target_column": "ISHELDBY",
        "dbsr_role": "join_edge",
    },
    {
        "id": "holding_refers_to_listed_security",
        "type": "direct",
        "source_entity": "Holding",
        "target_entity": "ListedSecurity",
        "source_column": "REFERSTO",
        "target_column": "LISTEDSECURITYID",
        "dbsr_role": "join_edge",
    },
    {
        "id": "account_records_transaction",
        "type": "reverse_direct",
        "source_entity": "FinancialServiceAccount",
        "target_entity": "Transaction",
        "source_column": "FINANCIALSERVICEACCOUNTID",
        "target_column": "ISFACILITATEDBY",
        "dbsr_role": "join_edge",
    },
    {
        "id": "transaction_refers_to_listed_security",
        "type": "direct",
        "source_entity": "Transaction",
        "target_entity": "ListedSecurity",
        "source_column": "REFERSTO",
        "target_column": "LISTEDSECURITYID",
        "dbsr_role": "join_edge",
    },
    {
        "id": "buy_transaction_is_transaction",
        "type": "subtype_alias",
        "source_entity": "BuyTransaction",
        "target_entity": "Transaction",
        "source_column": "SECURITIESTRANSACTIONID",
        "target_column": "SECURITIESTRANSACTIONID",
        "dbsr_role": "subtype_alias",
    },
    {
        "id": "sell_transaction_is_transaction",
        "type": "subtype_alias",
        "source_entity": "SellTransaction",
        "target_entity": "Transaction",
        "source_column": "SECURITIESTRANSACTIONID",
        "target_column": "SECURITIESTRANSACTIONID",
        "dbsr_role": "subtype_alias",
    },
    {
        "id": "corporation_has_financial_report",
        "type": "reverse_direct",
        "source_entity": "Corporation",
        "target_entity": "FinancialReport",
        "source_column": "CORPORATIONID",
        "target_column": "ISPROVIDEDBY",
        "dbsr_role": "join_edge",
    },
    {
        "id": "financial_report_contains_report_element",
        "type": "reverse_direct",
        "source_entity": "FinancialReport",
        "target_entity": "ReportElement",
        "source_column": "FINANCIALREPORTID",
        "target_column": "ISMEMBEROF",
        "dbsr_role": "join_edge",
    },
    {
        "id": "report_element_has_statement_element",
        "type": "direct",
        "source_entity": "ReportElement",
        "target_entity": "StatementElement",
        "source_column": "ELEMENTSOFFINANCIALREPORTID",
        "target_column": "ELEMENTOFFINANCIALSTATEMENTID",
        "dbsr_role": "join_edge",
    },
]


def parse_list(value: Any) -> List[str]:
    if value is None:
        return []
    s = str(value).strip()
    if not s or s == "[]":
        return []
    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    except Exception:
        pass
    return []


def load_benchmark_plan(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def unique_preserve_order(values: List[str]) -> List[str]:
    seen = set()
    out = []
    for v in values:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def infer_workload_from_plan(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for row in rows:
        qname = row.get("query_name", "")
        qtype = row.get("query_type", "")
        if not qname or qtype != "select":
            continue
        grouped[qname].append(row)

    workload = []

    for qname, qrows in sorted(grouped.items()):
        root = next((r.get("root_entity") for r in qrows if r.get("root_entity")), None)
        generic_class = next((r.get("generic_class") for r in qrows if r.get("generic_class")), "")
        query_family = next((r.get("query_family") for r in qrows if r.get("query_family")), "")

        touched = []
        if root:
            touched.append(root)

        for row in qrows:
            touched.extend(parse_list(row.get("embedded_entities")))
            touched.extend(parse_list(row.get("referenced_entities")))
            touched.extend(parse_list(row.get("materialized_entities")))

        touched = unique_preserve_order(touched)

        # This is a draft sequence. It must be reviewed manually before running DBSR.
        # We avoid using g_class, winners, p95, or SchemaLens selection scores.
        sequence = touched if touched else ([root] if root else [])

        workload.append(
            {
                "query_name": qname,
                "query_type": "read",
                "dbsr_sequence": sequence,
                "root_entity": root,
                "touched_entities": touched,
                "generic_class_from_existing_metadata": generic_class,
                "query_family_from_existing_metadata": query_family,
                "frequency": 1.0,
                "status": "draft_review_required",
                "source": "inferred_from_existing_fiben_benchmark_plan_metadata_without_using_g_class_or_results",
                "implementation_assumption": (
                    "The first adapter infers read JOIN sequences from existing FIBEN "
                    "benchmark metadata only to bootstrap DBSR inputs. These sequences "
                    "must be manually reviewed against the FIBEN query definitions before "
                    "DBSR schema generation."
                ),
            }
        )

    return workload


def build_input_model() -> Dict[str, Any]:
    entities = []
    for entity, view in ENTITY_VIEW_MAP.items():
        entities.append(
            {
                "name": entity,
                "source_view": view,
                "primary_key": ENTITY_PK_MAP[entity],
                "fields_policy": "all_fields_available_projection_refined_later",
            }
        )

    return {
        "baseline": "DBSR",
        "dataset": "FIBEN",
        "version": "0.1-draft-input-model",
        "entities": entities,
        "relationships": RELATIONSHIPS,
        "run_configuration": {
            "max_document_height": 3,
            "max_node_width": 2,
            "max_iterations": 4000,
            "query_plan_pruning_threshold": 30000,
            "fitness_function": "non_linear",
            "query_frequency_policy": "uniform_initially",
        },
        "implementation_assumptions": [
            {
                "id": "A01",
                "text": "FIBEN Q1-Q9 are treated as DBSR read workload sequences.",
            },
            {
                "id": "A02",
                "text": "Query frequencies are uniform unless explicit workload weights are later added.",
            },
            {
                "id": "A03",
                "text": "MongoDB physical loading is a materialization layer, not part of the DBSR core algorithm.",
            },
            {
                "id": "A04",
                "text": "DBSR generation must not use SchemaLens G0-G9 templates, winners, p95 values, or activation scores.",
            },
        ],
    }


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--benchmark-plan",
        default="analysis/fiben/benchmark_execution_plan.csv",
        help="Existing FIBEN benchmark plan used only to bootstrap query metadata.",
    )
    parser.add_argument(
        "--out-dir",
        default="DBSR_implementation/generated/fiben",
    )
    args = parser.parse_args()

    plan_path = Path(args.benchmark_plan)
    out_dir = Path(args.out_dir)

    rows = load_benchmark_plan(plan_path)
    input_model = build_input_model()
    workload = {
        "baseline": "DBSR",
        "dataset": "FIBEN",
        "version": "0.1-draft-workload",
        "scope": "read_queries_only",
        "queries": infer_workload_from_plan(rows),
        "manual_review_required": True,
        "notes": [
            "This file is a draft bootstrap artifact.",
            "Before DBSR generation, each dbsr_sequence must be reviewed against the real FIBEN query semantics.",
            "Q10 is excluded from this read-workload input and should be handled separately as an update/insert limitation or extension.",
        ],
    }

    write_json(out_dir / "dbsr_input_model.json", input_model)
    write_json(out_dir / "dbsr_workload.json", workload)

    print(f"Wrote {out_dir / 'dbsr_input_model.json'}")
    print(f"Wrote {out_dir / 'dbsr_workload.json'}")
    print(f"Read workload queries generated: {len(workload['queries'])}")


if __name__ == "__main__":
    main()
