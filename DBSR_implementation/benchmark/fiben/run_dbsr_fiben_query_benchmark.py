#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def connect_mongo(args: argparse.Namespace):
    from pymongo import MongoClient

    kwargs: Dict[str, Any] = {
        "host": args.mongo_host,
        "port": args.mongo_port,
        "serverSelectionTimeoutMS": 5000,
    }

    if args.mongo_username:
        kwargs["username"] = args.mongo_username
    if args.mongo_password:
        kwargs["password"] = args.mongo_password
    if args.mongo_auth_source:
        kwargs["authSource"] = args.mongo_auth_source

    client = MongoClient(**kwargs)
    client.admin.command("ping")
    return client


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]

    k = (len(ordered) - 1) * (p / 100.0)
    lower = int(k)
    upper = min(lower + 1, len(ordered) - 1)
    weight = k - lower

    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def as_float(value: Any) -> float:
    if value is None:
        return 0.0

    try:
        return float(str(value).replace("+", ""))
    except Exception:
        return 0.0


def list_values(doc: Dict[str, Any], path: str) -> List[Any]:
    parts = path.split(".")

    def walk(value: Any, remaining: List[str]) -> List[Any]:
        if not remaining:
            return [value]

        if isinstance(value, list):
            out = []
            for item in value:
                out.extend(walk(item, remaining))
            return out

        if isinstance(value, dict):
            key = remaining[0]
            if key not in value:
                return []
            return walk(value[key], remaining[1:])

        return []

    return [v for v in walk(doc, parts) if v is not None]


def get_param(params: Dict[str, Any], query_name: str, key: str, default: Any = None) -> Any:
    return params["parameters"].get(query_name, {}).get(key, default)


def q1_company_profile(db, params: Dict[str, Any]) -> int:
    corp_id = get_param(params, "Q1_CompanyProfileIBM", "corporation_id")
    doc = db.dbsr_rank03_corporation.find_one({"CORPORATIONID": corp_id})
    return 1 if doc else 0


def q2_company_with_context(db, params: Dict[str, Any]) -> int:
    corp_id = get_param(params, "Q2_CompanyWithIndustryCountryAndListedSecurities", "corporation_id")

    docs = 0
    docs += len(list(db.dbsr_rank05_corporation_country.find({"CORPORATIONID": corp_id}).limit(10)))
    docs += len(list(db.dbsr_rank06_corporation_industry.find({"CORPORATIONID": corp_id}).limit(10)))
    docs += len(list(db.dbsr_rank08_corporation_security_listedsecurity.find({"CORPORATIONID": corp_id}).limit(10)))

    return docs


def q3_account_holdings(db, params: Dict[str, Any]) -> int:
    account_id = get_param(params, "Q3_SecuritiesHeldInEachFinancialServiceAccount", "financial_service_account_id")
    doc = db.dbsr_rank07_financialserviceaccount_holding_listedsecurity.find_one(
        {"FINANCIALSERVICEACCOUNTID": account_id}
    )
    if not doc:
        return 0
    return 1 + len(doc.get("holding", []))


def q4_person_to_companies(db, params: Dict[str, Any]) -> int:
    person_id = get_param(params, "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity", "person_id")

    person_doc = db.dbsr_rank11_person_financialserviceaccount_holding.find_one({"PERSONID": person_id})
    if not person_doc:
        return 0

    listed_security_ids = list_values(person_doc, "financialServiceAccount.holding.REFERSTO")
    company_docs = list(
        db.dbsr_rank12_listedsecurity_security_corporation.find(
            {"LISTEDSECURITYID": {"$in": listed_security_ids}}
        ).limit(100)
    )

    return 1 + len(listed_security_ids) + len(company_docs)


def q5_reports_and_metric_data(db, params: Dict[str, Any]) -> int:
    report_id = get_param(params, "Q5_ReportsAndMetricDataOfCompany", "financial_report_id")

    doc = db.dbsr_rank13_financialreport_reportelement_statementelement.find_one(
        {"FINANCIALREPORTID": report_id}
    )
    if not doc:
        return 0

    report_elements = doc.get("reportElement", [])
    statement_elements = 0

    for element in report_elements:
        statement_elements += len(element.get("statementElement", []))

    return 1 + len(report_elements) + statement_elements


def q6_listed_securities_by_industry_country(db, params: Dict[str, Any]) -> int:
    industry_ids = get_param(params, "Q6_TechUSListedSecuritiesWithHighLastTradedValue", "industry_ids", [])
    country_ids = get_param(params, "Q6_TechUSListedSecuritiesWithHighLastTradedValue", "country_ids", [])

    docs = 0

    if industry_ids:
        docs += len(list(
            db.dbsr_rank14_security_corporation_industry.find(
                {"corporation.industry.INDUSTRYSECTORCLASSIFIERID": {"$in": industry_ids}}
            ).limit(100)
        ))

    if country_ids:
        docs += len(list(
            db.dbsr_rank15_security_corporation_country.find(
                {"corporation.country.COUNTRYID": {"$in": country_ids}}
            ).limit(100)
        ))

    return docs


def q7_person_bought_more_than_sold(db, params: Dict[str, Any]) -> int:
    person_id = get_param(params, "Q7_PersonsWhoBoughtMoreIBMThanSold", "person_id")
    listed_ids = get_param(params, "Q7_PersonsWhoBoughtMoreIBMThanSold", "listed_security_ids", [])

    doc = db.dbsr_rank10_person_financialserviceaccount_transaction.find_one({"PERSONID": person_id})
    if not doc:
        return 0

    target_security = listed_ids[0] if listed_ids else None
    buy_amount = 0.0
    sell_amount = 0.0
    transaction_count = 0

    for account in doc.get("financialServiceAccount", []):
        for trx in account.get("transaction", []):
            if target_security and trx.get("REFERSTO") != target_security:
                continue

            transaction_count += 1
            amount = as_float(trx.get("AMOUNT"))

            if str(trx.get("TRANSACTIONKIND")) == "1":
                buy_amount += amount
            else:
                sell_amount += amount

    return 1 if buy_amount >= sell_amount and transaction_count > 0 else transaction_count


def q8_transactions_below_average(db, params: Dict[str, Any]) -> int:
    listed_id = get_param(params, "Q8_IBMTransactionsBelowAverageSellingPrice", "listed_security_id")

    pipeline = [
        {"$match": {"REFERSTO": listed_id}},
        {"$addFields": {"amount_numeric": {"$toDouble": "$AMOUNT"}}},
        {
            "$group": {
                "_id": "$REFERSTO",
                "avg_amount": {"$avg": "$amount_numeric"},
                "transactions": {"$push": {"id": "$SECURITIESTRANSACTIONID", "amount": "$amount_numeric"}},
            }
        },
        {
            "$project": {
                "below_avg": {
                    "$filter": {
                        "input": "$transactions",
                        "as": "t",
                        "cond": {"$lt": ["$$t.amount", "$avg_amount"]},
                    }
                }
            }
        },
        {"$limit": 1},
    ]

    rows = list(db.dbsr_rank02_transaction_listedsecurity.aggregate(pipeline, allowDiskUse=True))
    if not rows:
        return 0

    return len(rows[0].get("below_avg", []))


def q9_person_bought_and_sold_same_stock(db, params: Dict[str, Any]) -> int:
    person_id = get_param(params, "Q9_PersonsWhoBoughtAndSoldSameStock", "person_id")

    doc = db.dbsr_rank10_person_financialserviceaccount_transaction.find_one({"PERSONID": person_id})
    if not doc:
        return 0

    by_stock: Dict[str, set] = {}

    for account in doc.get("financialServiceAccount", []):
        for trx in account.get("transaction", []):
            stock = trx.get("REFERSTO")
            kind = str(trx.get("TRANSACTIONKIND"))
            if stock:
                by_stock.setdefault(stock, set()).add(kind)

    matched = [stock for stock, kinds in by_stock.items() if len(kinds) >= 2]
    return len(matched)


QUERY_FUNCTIONS: List[Tuple[str, Callable[[Any, Dict[str, Any]], int]]] = [
    ("Q1_CompanyProfileIBM", q1_company_profile),
    ("Q2_CompanyWithIndustryCountryAndListedSecurities", q2_company_with_context),
    ("Q3_SecuritiesHeldInEachFinancialServiceAccount", q3_account_holdings),
    ("Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity", q4_person_to_companies),
    ("Q5_ReportsAndMetricDataOfCompany", q5_reports_and_metric_data),
    ("Q6_TechUSListedSecuritiesWithHighLastTradedValue", q6_listed_securities_by_industry_country),
    ("Q7_PersonsWhoBoughtMoreIBMThanSold", q7_person_bought_more_than_sold),
    ("Q8_IBMTransactionsBelowAverageSellingPrice", q8_transactions_below_average),
    ("Q9_PersonsWhoBoughtAndSoldSameStock", q9_person_bought_and_sold_same_stock),
]


def write_raw_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "baseline",
        "dataset",
        "scale_label",
        "query_name",
        "phase",
        "repetition",
        "elapsed_ms",
        "returned_count",
        "status",
        "error",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_aggregate_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "baseline",
        "dataset",
        "scale_label",
        "query_name",
        "phase",
        "executions",
        "successful_executions",
        "failed_executions",
        "avg_ms",
        "p50_ms",
        "p95_ms",
        "min_ms",
        "max_ms",
        "avg_returned_count",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def aggregate_rows(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}

    for row in raw_rows:
        grouped.setdefault((row["query_name"], row["phase"]), []).append(row)

    output = []

    for (query_name, phase), rows in sorted(grouped.items()):
        successful = [r for r in rows if r["status"] == "completed"]
        elapsed = [float(r["elapsed_ms"]) for r in successful]
        returned = [int(r["returned_count"]) for r in successful]

        output.append({
            "baseline": "DBSR",
            "dataset": "FIBEN",
            "scale_label": rows[0]["scale_label"],
            "query_name": query_name,
            "phase": phase,
            "executions": len(rows),
            "successful_executions": len(successful),
            "failed_executions": len(rows) - len(successful),
            "avg_ms": round(statistics.mean(elapsed), 6) if elapsed else 0,
            "p50_ms": round(percentile(elapsed, 50), 6) if elapsed else 0,
            "p95_ms": round(percentile(elapsed, 95), 6) if elapsed else 0,
            "min_ms": round(min(elapsed), 6) if elapsed else 0,
            "max_ms": round(max(elapsed), 6) if elapsed else 0,
            "avg_returned_count": round(statistics.mean(returned), 6) if returned else 0,
        })

    return output


def run_once(db, params: Dict[str, Any], query_name: str, fn, phase: str, repetition: int, scale_label: str) -> Dict[str, Any]:
    start = time.perf_counter()
    status = "completed"
    error = ""
    returned_count = 0

    try:
        returned_count = fn(db, params)
    except Exception as exc:
        status = "failed"
        error = repr(exc)

    elapsed_ms = (time.perf_counter() - start) * 1000.0

    return {
        "baseline": "DBSR",
        "dataset": "FIBEN",
        "scale_label": scale_label,
        "query_name": query_name,
        "phase": phase,
        "repetition": repetition,
        "elapsed_ms": round(elapsed_ms, 6),
        "returned_count": returned_count,
        "status": status,
        "error": error,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parameter-probe", required=True)
    parser.add_argument("--scale-label", default="sf1")
    parser.add_argument("--mongo-host", default="127.0.0.1")
    parser.add_argument("--mongo-port", type=int, default=27018)
    parser.add_argument("--mongo-username", default=None)
    parser.add_argument("--mongo-password", default=None)
    parser.add_argument("--mongo-auth-source", default="admin")
    parser.add_argument("--mongo-db", required=True)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--hot-runs", type=int, default=1)
    parser.add_argument("--out-dir", default="DBSR_implementation/results/fiben")
    args = parser.parse_args()

    client = connect_mongo(args)
    db = client[args.mongo_db]
    params = read_json(Path(args.parameter_probe))

    raw_rows: List[Dict[str, Any]] = []

    for query_name, fn in QUERY_FUNCTIONS:
        for rep in range(1, args.warmup + 1):
            raw_rows.append(run_once(db, params, query_name, fn, "warmup", rep, args.scale_label))

        for rep in range(1, args.hot_runs + 1):
            raw_rows.append(run_once(db, params, query_name, fn, "hot", rep, args.scale_label))

    aggregate = aggregate_rows(raw_rows)

    out_dir = Path(args.out_dir)
    raw_path = out_dir / f"dbsr_fiben_query_benchmark_raw_{args.scale_label}.csv"
    aggregate_path = out_dir / f"dbsr_fiben_query_benchmark_aggregate_{args.scale_label}.csv"
    manifest_path = out_dir / f"dbsr_fiben_query_benchmark_manifest_{args.scale_label}.json"

    write_raw_csv(raw_path, raw_rows)
    write_aggregate_csv(aggregate_path, aggregate)

    manifest = {
        "baseline": "DBSR",
        "dataset": "FIBEN",
        "scale_label": args.scale_label,
        "mongo_database": args.mongo_db,
        "warmup": args.warmup,
        "hot_runs": args.hot_runs,
        "queries": [name for name, _ in QUERY_FUNCTIONS],
        "raw_results": str(raw_path),
        "aggregate_results": str(aggregate_path),
        "failed_executions": sum(1 for row in raw_rows if row["status"] != "completed"),
        "official_benchmark": args.hot_runs >= 10,
        "implementation_note": (
            "This DBSR executor runs over the physically materialized dbsr_rank* collections. "
            "Small hot_runs values are smoke tests; official comparison should use a stable "
            "hot-run count and the same server as SchemaLens."
        ),
    }

    write_json(manifest_path, manifest)

    print("DBSR FIBEN query benchmark completed.")
    print(f"Mongo database: {args.mongo_db}")
    print(f"Warmup runs: {args.warmup}")
    print(f"Hot runs: {args.hot_runs}")
    print(f"Failed executions: {manifest['failed_executions']}")
    print(f"Wrote {raw_path}")
    print(f"Wrote {aggregate_path}")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
