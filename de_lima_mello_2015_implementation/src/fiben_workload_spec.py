"""
FIBEN workload specification for the de Lima & Mello (2015) implementation.

This module maps the FIBEN Q1-Q10 workload to the operation format required by
the Lima & Mello method.

Methodological decisions:
- The same conceptual workload used in SchemaLens is reused here.
- Query frequencies are uniform by default: frequency = 1.0.
- Queries with conceptual branches are represented as multiple elementary
  operations with the same query_id.
- This avoids artificial paths such as Corporation -> Industry -> Country.
- Q10 is included in the logical-design workload because Lima & Mello accepts
  retrieval and update operations as workload operations.
- Q10 will later be skipped only for read-query query-plan comparison.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

try:
    from .lmm_logical_model import OperationStep, WorkloadOperation
except ImportError:
    from lmm_logical_model import OperationStep, WorkloadOperation


DEFAULT_FREQUENCY = 1.0


def entity(name: str, order: int) -> OperationStep:
    return OperationStep(conceptual_type=name, type_kind="entity", order=order)


def relationship(name: str, order: int) -> OperationStep:
    return OperationStep(conceptual_type=name, type_kind="relationship", order=order)


def op(
    name: str,
    query_id: str,
    operation_kind: str,
    description: str,
    steps: Iterable[OperationStep],
    frequency: float = DEFAULT_FREQUENCY,
) -> WorkloadOperation:
    return WorkloadOperation(
        name=name,
        query_id=query_id,
        operation_kind=operation_kind,
        frequency=frequency,
        description=description,
        steps=tuple(steps),
    )


def build_fiben_workload_operations(
    frequency: float = DEFAULT_FREQUENCY,
) -> List[WorkloadOperation]:
    """
    Build FIBEN workload operations in Lima & Mello access-sequence format.

    Branching benchmark queries are decomposed into elementary access paths.
    This keeps the method faithful to the paper's operation-sequence model.
    """
    operations: List[WorkloadOperation] = []

    # Q1: local lookup.
    operations.append(
        op(
            name="Q1_CompanyProfileIBM",
            query_id="Q1",
            operation_kind="read",
            frequency=frequency,
            description="Show the profile of company IBM.",
            steps=[entity("Corporation", 1)],
        )
    )

    # Q2: Corporation has three direct branches.
    operations.extend(
        [
            op(
                name="Q2a_CompanyIndustry",
                query_id="Q2",
                operation_kind="read",
                frequency=frequency,
                description="Show IBM with its industry.",
                steps=[
                    entity("Corporation", 1),
                    relationship("corporation_has_industry", 2),
                    entity("Industry", 3),
                ],
            ),
            op(
                name="Q2b_CompanyCountry",
                query_id="Q2",
                operation_kind="read",
                frequency=frequency,
                description="Show IBM with its country.",
                steps=[
                    entity("Corporation", 1),
                    relationship("corporation_has_country", 2),
                    entity("Country", 3),
                ],
            ),
            op(
                name="Q2c_CompanyListedSecurities",
                query_id="Q2",
                operation_kind="read",
                frequency=frequency,
                description="Show IBM with its listed securities.",
                steps=[
                    entity("Corporation", 1),
                    relationship("corporation_has_listed_security", 2),
                    entity("ListedSecurity", 3),
                ],
            ),
        ]
    )

    # Q3: account -> holding -> listed security -> security.
    operations.append(
        op(
            name="Q3_SecuritiesHeldInEachFinancialServiceAccount",
            query_id="Q3",
            operation_kind="read",
            frequency=frequency,
            description="Show the securities held in each financial service account.",
            steps=[
                entity("FinancialServiceAccount", 1),
                relationship("account_has_holding", 2),
                entity("Holding", 3),
                relationship("holding_refers_to_listed_security", 4),
                entity("ListedSecurity", 5),
                relationship("listed_security_represents_security", 6),
                entity("Security", 7),
            ],
        )
    )

    # Q4: deep traversal from person to corporation.
    operations.append(
        op(
            name="Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity",
            query_id="Q4",
            operation_kind="read",
            frequency=frequency,
            description=(
                "Show the companies reached from a person through account, "
                "holding, and listed security."
            ),
            steps=[
                entity("Person", 1),
                relationship("person_owns_financial_service_account", 2),
                entity("FinancialServiceAccount", 3),
                relationship("account_has_holding", 4),
                entity("Holding", 5),
                relationship("holding_refers_to_listed_security", 6),
                entity("ListedSecurity", 7),
                relationship("corporation_has_listed_security", 8),
                entity("Corporation", 9),
            ],
        )
    )

    # Q5: two branches from FinancialReport.
    operations.extend(
        [
            op(
                name="Q5a_ReportsAndStatementMetricDataOfCompany",
                query_id="Q5",
                operation_kind="read",
                frequency=frequency,
                description=(
                    "Show the financial reports of a company and the statement "
                    "metric data contained in each report."
                ),
                steps=[
                    entity("Corporation", 1),
                    relationship("corporation_has_financial_report", 2),
                    entity("FinancialReport", 3),
                    relationship("financial_report_contains_report_element", 4),
                    entity("ReportElement", 5),
                    relationship("report_element_has_statement_element", 6),
                    entity("StatementElement", 7),
                ],
            ),
            op(
                name="Q5b_ReportsAndDisclosuresOfCompany",
                query_id="Q5",
                operation_kind="read",
                frequency=frequency,
                description=(
                    "Show the financial reports of a company and the disclosure "
                    "data contained in each report."
                ),
                steps=[
                    entity("Corporation", 1),
                    relationship("corporation_has_financial_report", 2),
                    entity("FinancialReport", 3),
                    relationship("financial_report_contains_disclosure", 4),
                    entity("Disclosure", 5),
                ],
            ),
        ]
    )

    # Q6: same three direct branches as Q2, but with filters.
    operations.extend(
        [
            op(
                name="Q6a_TechIndustryFilter",
                query_id="Q6",
                operation_kind="read",
                frequency=frequency,
                description="Filter companies by technology industry.",
                steps=[
                    entity("Corporation", 1),
                    relationship("corporation_has_industry", 2),
                    entity("Industry", 3),
                ],
            ),
            op(
                name="Q6b_USCountryFilter",
                query_id="Q6",
                operation_kind="read",
                frequency=frequency,
                description="Filter companies by US country.",
                steps=[
                    entity("Corporation", 1),
                    relationship("corporation_has_country", 2),
                    entity("Country", 3),
                ],
            ),
            op(
                name="Q6c_ListedSecurityHighValueFilter",
                query_id="Q6",
                operation_kind="read",
                frequency=frequency,
                description="Return listed securities with high last traded value.",
                steps=[
                    entity("Corporation", 1),
                    relationship("corporation_has_listed_security", 2),
                    entity("ListedSecurity", 3),
                ],
            ),
        ]
    )

    # Q7: buy and sell branches are separated.
    operations.extend(
        [
            op(
                name="Q7a_PersonBoughtIBM",
                query_id="Q7",
                operation_kind="read",
                frequency=frequency,
                description="Find persons with IBM buy transactions.",
                steps=[
                    entity("Person", 1),
                    relationship("person_owns_financial_service_account", 2),
                    entity("FinancialServiceAccount", 3),
                    relationship("account_records_transaction", 4),
                    entity("Transaction", 5),
                    relationship("buy_transaction_is_transaction", 6),
                    entity("BuyTransaction", 7),
                    relationship("transaction_refers_to_listed_security", 8),
                    entity("ListedSecurity", 9),
                    relationship("corporation_has_listed_security", 10),
                    entity("Corporation", 11),
                ],
            ),
            op(
                name="Q7b_PersonSoldIBM",
                query_id="Q7",
                operation_kind="read",
                frequency=frequency,
                description="Find persons with IBM sell transactions.",
                steps=[
                    entity("Person", 1),
                    relationship("person_owns_financial_service_account", 2),
                    entity("FinancialServiceAccount", 3),
                    relationship("account_records_transaction", 4),
                    entity("Transaction", 5),
                    relationship("sell_transaction_is_transaction", 6),
                    entity("SellTransaction", 7),
                    relationship("transaction_refers_to_listed_security", 8),
                    entity("ListedSecurity", 9),
                    relationship("corporation_has_listed_security", 10),
                    entity("Corporation", 11),
                ],
            ),
        ]
    )

    # Q8: IBM listed security -> transaction -> sell transaction.
    operations.append(
        op(
            name="Q8_IBMTransactionsBelowAverageSellingPrice",
            query_id="Q8",
            operation_kind="read",
            frequency=frequency,
            description=(
                "Show each transaction for IBM whose price is less than the "
                "average selling price."
            ),
            steps=[
                entity("Corporation", 1),
                relationship("corporation_has_listed_security", 2),
                entity("ListedSecurity", 3),
                relationship("transaction_refers_to_listed_security", 4),
                entity("Transaction", 5),
                relationship("sell_transaction_is_transaction", 6),
                entity("SellTransaction", 7),
            ],
        )
    )

    # Q9: buy and sell paths separated.
    operations.extend(
        [
            op(
                name="Q9a_PersonBoughtStock",
                query_id="Q9",
                operation_kind="read",
                frequency=frequency,
                description="Find persons who bought a stock.",
                steps=[
                    entity("Person", 1),
                    relationship("person_owns_financial_service_account", 2),
                    entity("FinancialServiceAccount", 3),
                    relationship("account_records_transaction", 4),
                    entity("Transaction", 5),
                    relationship("buy_transaction_is_transaction", 6),
                    entity("BuyTransaction", 7),
                    relationship("transaction_refers_to_listed_security", 8),
                    entity("ListedSecurity", 9),
                ],
            ),
            op(
                name="Q9b_PersonSoldStock",
                query_id="Q9",
                operation_kind="read",
                frequency=frequency,
                description="Find persons who sold a stock.",
                steps=[
                    entity("Person", 1),
                    relationship("person_owns_financial_service_account", 2),
                    entity("FinancialServiceAccount", 3),
                    relationship("account_records_transaction", 4),
                    entity("Transaction", 5),
                    relationship("sell_transaction_is_transaction", 6),
                    entity("SellTransaction", 7),
                    relationship("transaction_refers_to_listed_security", 8),
                    entity("ListedSecurity", 9),
                ],
            ),
        ]
    )

    # Q10: insertion has account/holding and account/transaction branches.
    operations.extend(
        [
            op(
                name="Q10a_CreateAccountAndHolding",
                query_id="Q10",
                operation_kind="insert",
                frequency=frequency,
                description=(
                    "Create an account for a person and add a holding for a "
                    "listed security."
                ),
                steps=[
                    entity("Person", 1),
                    relationship("person_owns_financial_service_account", 2),
                    entity("FinancialServiceAccount", 3),
                    relationship("account_has_holding", 4),
                    entity("Holding", 5),
                    relationship("holding_refers_to_listed_security", 6),
                    entity("ListedSecurity", 7),
                ],
            ),
            op(
                name="Q10b_CreateAccountAndBuyTransaction",
                query_id="Q10",
                operation_kind="insert",
                frequency=frequency,
                description=(
                    "Create an account for a person and register a buy "
                    "transaction."
                ),
                steps=[
                    entity("Person", 1),
                    relationship("person_owns_financial_service_account", 2),
                    entity("FinancialServiceAccount", 3),
                    relationship("account_records_transaction", 4),
                    entity("Transaction", 5),
                    relationship("buy_transaction_is_transaction", 6),
                    entity("BuyTransaction", 7),
                ],
            ),
        ]
    )

    return operations


def operations_to_access_path_rows(
    operations: List[WorkloadOperation],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []

    for operation in operations:
        for step in operation.ordered_steps():
            rows.append(
                {
                    "operation_name": operation.name,
                    "query_id": operation.query_id,
                    "operation_kind": operation.operation_kind,
                    "frequency": operation.frequency,
                    "description": operation.description,
                    "step_order": step.order,
                    "conceptual_type": step.conceptual_type,
                    "type_kind": step.type_kind,
                }
            )

    return rows


def operations_to_summary_rows(
    operations: List[WorkloadOperation],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []

    for operation in operations:
        ordered_steps = operation.ordered_steps()
        rows.append(
            {
                "operation_name": operation.name,
                "query_id": operation.query_id,
                "operation_kind": operation.operation_kind,
                "frequency": operation.frequency,
                "n_steps": len(ordered_steps),
                "entities": [
                    step.conceptual_type
                    for step in ordered_steps
                    if step.type_kind == "entity"
                ],
                "relationships": [
                    step.conceptual_type
                    for step in ordered_steps
                    if step.type_kind == "relationship"
                ],
                "access_sequence": " -> ".join(
                    step.conceptual_type for step in ordered_steps
                ),
                "description": operation.description,
            }
        )

    return rows


def write_workload_outputs(
    output_dir: Path,
    operations: List[WorkloadOperation],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    access_path_df = pd.DataFrame(operations_to_access_path_rows(operations))
    summary_df = pd.DataFrame(operations_to_summary_rows(operations))

    access_path_csv = output_dir / "lmm_fiben_workload_access_paths.csv"
    summary_csv = output_dir / "lmm_fiben_workload_summary.csv"
    operations_json = output_dir / "lmm_fiben_workload_operations.json"
    report_json = output_dir / "lmm_fiben_workload_spec_report.json"

    access_path_df.to_csv(access_path_csv, index=False)
    summary_df.to_csv(summary_csv, index=False)

    operations_payload = {
        "methodological_mode": "lima_mello_elementary_workload_operations",
        "frequency_policy": "uniform_frequency_1_0",
        "notes": [
            "Branching benchmark queries are decomposed into elementary access paths.",
            "This avoids artificial conceptual transitions when computing GAF.",
            "Q10 is included for logical-design workload but will be skipped in read-query query-plan comparison.",
        ],
        "operations": [operation.to_dict() for operation in operations],
    }

    operations_json.write_text(
        json.dumps(operations_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    report = {
        "status": "completed",
        "n_operations": len(operations),
        "n_benchmark_query_ids": len(set(op.query_id for op in operations)),
        "query_ids": sorted(set(op.query_id for op in operations)),
        "operation_kind_counts": summary_df["operation_kind"].value_counts().to_dict(),
        "frequency_policy": "uniform_frequency_1_0",
        "branching_policy": "decompose_branching_queries_into_elementary_access_paths",
        "output_files": {
            "access_paths_csv": str(access_path_csv),
            "summary_csv": str(summary_csv),
            "operations_json": str(operations_json),
            "report_json": str(report_json),
        },
    }

    report_json.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("FIBEN workload specification written.")
    print(f"Operations: {len(operations)}")
    print(f"Benchmark query ids: {report['n_benchmark_query_ids']}")
    print("\nOperation kind counts:")
    print(summary_df["operation_kind"].value_counts().to_string())
    print("\nOutput files:")
    for path in report["output_files"].values():
        print(f"  {path}")


def main() -> None:
    operations = build_fiben_workload_operations()
    output_dir = Path("de_lima_mello_2015_implementation/generated/fiben")
    write_workload_outputs(output_dir=output_dir, operations=operations)


if __name__ == "__main__":
    main()
