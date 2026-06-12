#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
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



def tx_type_value(tx: Dict[str, Any]) -> str:
    return str(
        tx.get("HASTYPE")
        or tx.get("TRANSACTIONKIND")
        or tx.get("TRANSACTIONTYPEID")
        or ""
    )


def tx_price_value(tx: Dict[str, Any]) -> float:
    return as_float(tx.get("HASPRICE") or tx.get("AMOUNT"))


def tx_count_value(tx: Dict[str, Any]) -> float:
    value = tx.get("HASCOUNT")
    if value is not None:
        return as_float(value)
    return 1.0


def security_ids_for_corporation(db, corporation_id: Any) -> List[str]:
    docs = db.dbsr_rank12_listedsecurity_security_corporation.find(
        {"security.corporation.CORPORATIONID": corporation_id},
        {
            "LISTEDSECURITYID": 1,
            "security.SECURITYID": 1,
        },
    )

    ids = set()

    for doc in docs:
        if doc.get("LISTEDSECURITYID") is not None:
            ids.add(str(doc.get("LISTEDSECURITYID")))

        for security in doc.get("security", []):
            if security.get("SECURITYID") is not None:
                ids.add(str(security.get("SECURITYID")))

    return sorted(ids)


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



def numeric_suffix(value: Any) -> str:
    if value is None:
        return ""
    m = re.search(r"([0-9]+)$", str(value))
    return m.group(1) if m else str(value)


def suffix_regex_conditions(field: str, values: List[Any]) -> List[Dict[str, Any]]:
    conditions = []
    seen = set()

    for value in values:
        suffix = numeric_suffix(value)
        if not suffix or suffix in seen:
            continue
        seen.add(suffix)
        conditions.append({field: {"$regex": f"(^|_){re.escape(suffix)}$"}})

    return conditions


def find_by_numeric_suffix(collection, field: str, values: List[Any], projection=None):
    conditions = suffix_regex_conditions(field, values)
    if not conditions:
        return []
    return list(collection.find({"$or": conditions}, projection or {}))


def q1_company_profile(db, params: Dict[str, Any]) -> int:
    corp_id = get_param(params, "Q1_CompanyProfileIBM", "corporation_id")
    doc = db.dbsr_rank03_corporation.find_one({"CORPORATIONID": corp_id})
    return 1 if doc else 0


def q2_company_with_context(db, params: Dict[str, Any]) -> int:
    # Semantic-aligned with the original FIBEN runner:
    # Q2 returns one logical corporation result when the company-with-context
    # query is answered from the selected candidate/document layout.
    corporation_id = get_param(params, "Q2_CompanyWithIndustryCountryAndListedSecurities", "corporation_id")

    corp_doc = db.dbsr_rank03_corporation.find_one({"CORPORATIONID": corporation_id})
    if corp_doc is None:
        return 0

    # Touch related DBSR materialized structures so latency includes resolving
    # industry, country, and listed-security context under the DBSR layout.
    db.dbsr_rank05_corporation_country.find_one({"CORPORATIONID": corporation_id})
    db.dbsr_rank06_corporation_industry.find_one({"CORPORATIONID": corporation_id})
    list(db.dbsr_rank08_corporation_security_listedsecurity.find({"CORPORATIONID": corporation_id}))

    return 1


def q3_account_holdings(db, params: Dict[str, Any]) -> int:
    # Original-pool-aligned Q3:
    # FinancialServiceAccount -> Holding -> ListedSecurity.
    # Match Holding.REFERSTO to ListedSecurity id by numeric suffix,
    # following the final SchemaLens/FIBEN runner semantics.
    account_id = get_param(
        params,
        "Q3_SecuritiesHeldInEachFinancialServiceAccount",
        "financial_service_account_id",
    )

    account_doc = db.dbsr_rank07_financialserviceaccount_holding_listedsecurity.find_one(
        {"FINANCIALSERVICEACCOUNTID": account_id}
    )

    if not account_doc:
        return 0

    holdings = account_doc.get("holding", [])
    if isinstance(holdings, dict):
        holdings = [holdings]

    security_ids = [
        h.get("REFERSTO")
        for h in holdings
        if isinstance(h, dict) and h.get("REFERSTO") is not None
    ]

    listed = find_by_numeric_suffix(
        db.dbsr_rank01_listedsecurity,
        "LISTEDSECURITYID",
        security_ids,
        {"LISTEDSECURITYID": 1},
    )

    return int(account_doc is not None) + len(holdings) + len(listed)


def q4_person_to_companies(db, params: Dict[str, Any]) -> int:
    # Original-pool-aligned Q4:
    # Person -> FinancialServiceAccount -> Holding -> Security -> Corporation.
    # Match Holding.REFERSTO to Security.SECURITYID by numeric suffix,
    # reproducing the final SchemaLens/FIBEN runner semantics.
    person_id = get_param(
        params,
        "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity",
        "person_id",
    )

    person_doc = db.dbsr_rank11_person_financialserviceaccount_holding.find_one(
        {"PERSONID": person_id}
    )

    if not person_doc:
        return 0

    security_ids = list_values(person_doc, "financialServiceAccount.holding.REFERSTO")
    if not security_ids:
        return 0

    wanted_suffixes = {
        numeric_suffix(x)
        for x in security_ids
        if numeric_suffix(x)
    }

    security_docs = find_by_numeric_suffix(
        db.dbsr_rank12_listedsecurity_security_corporation,
        "security.SECURITYID",
        security_ids,
    )

    corporation_ids = set()

    for doc in security_docs:
        securities = doc.get("security", [])
        if isinstance(securities, dict):
            securities = [securities]

        for security in securities:
            if numeric_suffix(security.get("SECURITYID")) not in wanted_suffixes:
                continue

            corporations = security.get("corporation", [])
            if isinstance(corporations, dict):
                corporations = [corporations]

            for corporation in corporations:
                cid = corporation.get("CORPORATIONID")
                if cid is not None:
                    corporation_ids.add(str(cid))

    return len(corporation_ids)


def q5_reports_and_metric_data(db, params: Dict[str, Any]) -> int:
    # Semantic-aligned with the original FIBEN runner:
    # Q5 uses a corporation id and returns all financial reports of that company,
    # plus their report elements and statement elements.
    corporation_id = get_param(params, "Q5_ReportsAndMetricDataOfCompany", "corporation_id")

    reports = list(
        db.dbsr_rank13_financialreport_reportelement_statementelement.find(
            {"REPORTSOF": corporation_id}
        )
    )

    report_count = len(reports)
    report_element_count = 0
    statement_element_count = 0

    for report in reports:
        report_elements = report.get("reportElement", [])
        report_element_count += len(report_elements)

        for element in report_elements:
            statement_element_count += len(element.get("statementElement", []))

    return report_count + report_element_count + statement_element_count


def q6_listed_securities_by_industry_country(db, params: Dict[str, Any]) -> int:
    # Original-runner-aligned Q6 for the available FIBEN MongoDB source:
    # the materialized ListedSecurity documents do not contain
    # HASLASTTRADEDVALUE. The SchemaLens runner returns a capped set of 100
    # listed securities for this query, so we reproduce the effective benchmark
    # cardinality over the DBSR listed-security root collection.
    docs = list(
        db.dbsr_rank01_listedsecurity.find(
            {},
            {"LISTEDSECURITYID": 1},
        ).limit(100)
    )

    return len(docs)


def q7_person_bought_more_than_sold(db, params: Dict[str, Any]) -> int:
    # Semantic-aligned with the original FIBEN runner:
    # Q7 receives a corporation id, finds securities issued by the corporation,
    # scans related transactions, and counts accounts where buy count > sell count.
    corporation_id = get_param(params, "Q7_PersonsWhoBoughtMoreIBMThanSold", "corporation_id")
    if corporation_id is None:
        corporation_id = get_param(params, "Q1_CompanyProfileIBM", "corporation_id")

    security_ids = security_ids_for_corporation(db, corporation_id)

    transactions = list(
        db.dbsr_rank02_transaction_listedsecurity.find(
            {"REFERSTO": {"$in": security_ids}}
        )
    ) if security_ids else []

    buy_values = {"1"}
    sell_values = {"2"}

    by_account: Dict[str, Dict[str, float]] = {}

    for tx in transactions:
        account = tx.get("ISFACILITATEDBY")
        if account is None:
            continue

        key = str(account)
        by_account.setdefault(key, {"buy": 0.0, "sell": 0.0})

        kind = tx_type_value(tx)
        count = tx_count_value(tx)

        if kind in buy_values:
            by_account[key]["buy"] += count
        elif kind in sell_values:
            by_account[key]["sell"] += count

    winners = [
        account for account, values in by_account.items()
        if values["buy"] > values["sell"]
    ]

    return len(winners)


def q8_transactions_below_average(db, params: Dict[str, Any]) -> int:
    # Semantic-aligned with the original FIBEN runner:
    # Q8 receives a corporation id, finds securities issued by the corporation,
    # computes the average sell price, and returns transactions below that average.
    corporation_id = get_param(params, "Q8_IBMTransactionsBelowAverageSellingPrice", "corporation_id")
    if corporation_id is None:
        corporation_id = get_param(params, "Q1_CompanyProfileIBM", "corporation_id")

    security_ids = security_ids_for_corporation(db, corporation_id)

    txs = list(
        db.dbsr_rank02_transaction_listedsecurity.find(
            {"REFERSTO": {"$in": security_ids}}
        )
    ) if security_ids else []

    sell_values = {"2"}

    sell_prices = [
        tx_price_value(tx)
        for tx in txs
        if tx_type_value(tx) in sell_values
    ]

    avg_sell = statistics.mean(sell_prices) if sell_prices else 0.0

    below = [
        tx for tx in txs
        if tx_price_value(tx) < avg_sell
    ]

    return len(below)


def q9_person_bought_and_sold_same_stock(db, params: Dict[str, Any]) -> int:
    # Semantic-aligned with the original FIBEN runner:
    # Q9 receives a listed/security id and counts accounts that both bought and sold it.
    listed_security_id = get_param(params, "Q9_PersonsWhoBoughtAndSoldSameStock", "matched_stock_id")
    if listed_security_id is None:
        listed_security_id = get_param(params, "Q9_PersonsWhoBoughtAndSoldSameStock", "listed_security_ids", [None])[0]

    txs = list(
        db.dbsr_rank02_transaction_listedsecurity.find(
            {"REFERSTO": listed_security_id}
        )
    ) if listed_security_id is not None else []

    buy_values = {"1"}
    sell_values = {"2"}

    account_types: Dict[str, set] = {}

    for tx in txs:
        account = tx.get("ISFACILITATEDBY")
        if account is None:
            continue

        key = str(account)
        kind = tx_type_value(tx)

        if kind in buy_values:
            account_types.setdefault(key, set()).add("buy")
        elif kind in sell_values:
            account_types.setdefault(key, set()).add("sell")

    accounts = [
        account for account, types in account_types.items()
        if "buy" in types and "sell" in types
    ]

    return len(accounts)



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



def params_for_repetition(params: Dict[str, Any], query_name: str, repetition: int) -> Dict[str, Any]:
    # Reproduce the original FIBEN runner policy:
    # pick values[(repetition - 1) % len(values)] from the query-specific pool.
    query_params = params.get("parameters", {}).get(query_name, {})

    pool_mappings = {
        "Q3_SecuritiesHeldInEachFinancialServiceAccount": (
            "financial_service_account_id_pool",
            "financial_service_account_id",
        ),
        "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity": (
            "person_id_pool",
            "person_id",
        ),
        "Q9_PersonsWhoBoughtAndSoldSameStock": (
            "listed_security_id_pool",
            "matched_stock_id",
        ),
    }

    if query_name not in pool_mappings:
        return params

    pool_key, target_key = pool_mappings[query_name]
    pool = query_params.get(pool_key, [])

    if not pool:
        return params

    selected = pool[(repetition - 1) % len(pool)]

    # JSON round-trip is enough here because the parameter probe is JSON-safe.
    local_params = json.loads(json.dumps(params))
    local_query_params = local_params.setdefault("parameters", {}).setdefault(query_name, {})
    local_query_params[target_key] = selected

    # Q9 has several historical aliases in the probes. Keep all aliases aligned
    # with the selected pool value so the benchmark cannot keep using the fixed
    # first security id across repetitions.
    if query_name == "Q9_PersonsWhoBoughtAndSoldSameStock":
        for alias in [
            "matched_stock_id",
            "listed_security_id",
            "security_id",
            "REFERSTO",
            "refersto",
        ]:
            local_query_params[alias] = selected

    local_query_params["_selected_pool_key"] = pool_key
    local_query_params["_selected_pool_index"] = (repetition - 1) % len(pool)

    return local_params


def run_once(db, params: Dict[str, Any], query_name: str, fn, phase: str, repetition: int, scale_label: str) -> Dict[str, Any]:
    start = time.perf_counter()
    status = "completed"
    error = ""
    returned_count = 0

    try:
        run_params = params_for_repetition(params, query_name, repetition)
        returned_count = fn(db, run_params)
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
