#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


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


def safe_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: safe_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [safe_value(v) for v in value]
    if value.__class__.__name__ == "ObjectId":
        return str(value)
    return value


def values_at_path(obj: Any, path: str) -> List[Any]:
    parts = path.split(".")

    def walk(value: Any, remaining: List[str]) -> List[Any]:
        if not remaining:
            return [value]

        if isinstance(value, list):
            out: List[Any] = []
            for item in value:
                out.extend(walk(item, remaining))
            return out

        if isinstance(value, dict):
            key = remaining[0]
            if key not in value:
                return []
            return walk(value[key], remaining[1:])

        return []

    values = walk(obj, parts)
    return [safe_value(v) for v in values if v is not None]


def first_value(obj: Optional[Dict[str, Any]], path: str) -> Any:
    if not obj:
        return None
    values = values_at_path(obj, path)
    return values[0] if values else None


def first_values(obj: Optional[Dict[str, Any]], path: str, limit: int = 10) -> List[Any]:
    if not obj:
        return []
    return values_at_path(obj, path)[:limit]


def find_one(db, collection: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    doc = db[collection].find_one(query)
    return safe_value(doc) if doc else None


def collection_counts(db) -> Dict[str, int]:
    counts: Dict[str, int] = {}

    for name in sorted(db.list_collection_names()):
        if name.startswith("dbsr_rank"):
            counts[name] = db[name].count_documents({})

    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo-host", default="127.0.0.1")
    parser.add_argument("--mongo-port", type=int, default=27018)
    parser.add_argument("--mongo-username", default=None)
    parser.add_argument("--mongo-password", default=None)
    parser.add_argument("--mongo-auth-source", default="admin")
    parser.add_argument("--mongo-db", required=True)
    parser.add_argument("--scale-label", default="sf1")
    parser.add_argument("--out-dir", default="DBSR_implementation/generated/fiben")
    args = parser.parse_args()

    client = connect_mongo(args)
    db = client[args.mongo_db]

    counts = collection_counts(db)

    # Q1: company profile. Prefer IBM if present, otherwise use any corporation.
    q1_doc = find_one(db, "dbsr_rank03_corporation", {"TICKERSYMBOL": "IBM"})
    if not q1_doc:
        q1_doc = find_one(db, "dbsr_rank03_corporation", {})

    # Q2: company with industry/country/listed securities.
    q2_doc = find_one(db, "dbsr_rank08_corporation_security_listedsecurity", {"security.0": {"$exists": True}})
    if not q2_doc:
        q2_doc = find_one(db, "dbsr_rank08_corporation_security_listedsecurity", {})

    # Q3: securities held in a financial service account.
    q3_doc = find_one(db, "dbsr_rank07_financialserviceaccount_holding_listedsecurity", {"holding.0": {"$exists": True}})
    if not q3_doc:
        q3_doc = find_one(db, "dbsr_rank07_financialserviceaccount_holding_listedsecurity", {})

    # Q4: person -> account -> holding path.
    q4_doc = find_one(db, "dbsr_rank11_person_financialserviceaccount_holding", {"financialServiceAccount.0": {"$exists": True}})
    if not q4_doc:
        q4_doc = find_one(db, "dbsr_rank11_person_financialserviceaccount_holding", {})

    # Q5: financial report with report elements and statement elements.
    q5_doc = find_one(
        db,
        "dbsr_rank13_financialreport_reportelement_statementelement",
        {"reportElement.statementElement.0": {"$exists": True}},
    )
    if not q5_doc:
        q5_doc = find_one(
            db,
            "dbsr_rank13_financialreport_reportelement_statementelement",
            {"reportElement.0": {"$exists": True}},
        )

    # Q6: listed/security/company/industry/country paths.
    q6_industry_doc = find_one(db, "dbsr_rank14_security_corporation_industry", {"corporation.0": {"$exists": True}})
    q6_country_doc = find_one(db, "dbsr_rank15_security_corporation_country", {"corporation.0": {"$exists": True}})

    # Q7: person/account/transaction path.
    q7_q9_doc = find_one(
        db,
        "dbsr_rank10_person_financialserviceaccount_transaction",
        {"financialServiceAccount.transaction.0": {"$exists": True}},
    )
    if not q7_q9_doc:
        q7_q9_doc = find_one(db, "dbsr_rank10_person_financialserviceaccount_transaction", {})

    # Q9: choose a person who bought and sold the same stock.
    q9_match_rows = list(db.dbsr_rank10_person_financialserviceaccount_transaction.aggregate([
        {"$unwind": "$financialServiceAccount"},
        {"$unwind": "$financialServiceAccount.transaction"},
        {"$group": {
            "_id": {
                "person": "$PERSONID",
                "stock": "$financialServiceAccount.transaction.REFERSTO",
            },
            "kinds": {"$addToSet": "$financialServiceAccount.transaction.TRANSACTIONKIND"},
            "txCount": {"$sum": 1},
        }},
        {"$match": {"kinds.1": {"$exists": True}}},
        {"$sort": {"txCount": -1}},
        {"$limit": 1},
    ], allowDiskUse=True))

    q9_match = q9_match_rows[0] if q9_match_rows else None
    q9_person_id = q9_match["_id"]["person"] if q9_match else first_value(q7_q9_doc, "PERSONID")
    q9_stock_id = q9_match["_id"]["stock"] if q9_match else None
    q9_doc = find_one(db, "dbsr_rank10_person_financialserviceaccount_transaction", {"PERSONID": q9_person_id}) if q9_person_id else q7_q9_doc

    # Q8: transaction with listed security.
    q8_doc = find_one(db, "dbsr_rank02_transaction_listedsecurity", {"listedSecurity.0": {"$exists": True}})
    if not q8_doc:
        q8_doc = find_one(db, "dbsr_rank02_transaction_listedsecurity", {})

    parameters = {
        "Q1_CompanyProfileIBM": {
            "collection": "dbsr_rank03_corporation",
            "corporation_id": first_value(q1_doc, "CORPORATIONID"),
            "ticker_symbol": first_value(q1_doc, "TICKERSYMBOL"),
            "name": first_value(q1_doc, "NAME"),
            "returned_sample": q1_doc is not None,
        },
        "Q2_CompanyWithIndustryCountryAndListedSecurities": {
            "main_collection": "dbsr_rank08_corporation_security_listedsecurity",
            "corporation_id": first_value(q2_doc, "CORPORATIONID"),
            "ticker_symbol": first_value(q2_doc, "TICKERSYMBOL"),
            "security_ids": first_values(q2_doc, "security.SECURITYID"),
            "listed_security_ids": first_values(q2_doc, "security.listedSecurity.LISTEDSECURITYID"),
            "returned_sample": q2_doc is not None,
        },
        "Q3_SecuritiesHeldInEachFinancialServiceAccount": {
            "collection": "dbsr_rank07_financialserviceaccount_holding_listedsecurity",
            "financial_service_account_id": first_value(q3_doc, "FINANCIALSERVICEACCOUNTID"),
            "holding_ids": first_values(q3_doc, "holding.HOLDINGID"),
            "listed_security_ids": first_values(q3_doc, "holding.listedSecurity.LISTEDSECURITYID"),
            "returned_sample": q3_doc is not None,
        },
        "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity": {
            "collection": "dbsr_rank11_person_financialserviceaccount_holding",
            "person_id": first_value(q4_doc, "PERSONID"),
            "financial_service_account_ids": first_values(q4_doc, "financialServiceAccount.FINANCIALSERVICEACCOUNTID"),
            "holding_ids": first_values(q4_doc, "financialServiceAccount.holding.HOLDINGID"),
            "listed_security_ids": first_values(q4_doc, "financialServiceAccount.holding.REFERSTO"),
            "returned_sample": q4_doc is not None,
        },
        "Q5_ReportsAndMetricDataOfCompany": {
            "collection": "dbsr_rank13_financialreport_reportelement_statementelement",
            "financial_report_id": first_value(q5_doc, "FINANCIALREPORTID"),
            "corporation_id": first_value(q5_doc, "REPORTSOF"),
            "report_element_ids": first_values(q5_doc, "reportElement.ELEMENTSOFFINANCIALREPORTID"),
            "statement_element_ids": first_values(q5_doc, "reportElement.statementElement.ELEMENTOFFINANCIALSTATEMENTID"),
            "returned_sample": q5_doc is not None,
        },
        "Q6_TechUSListedSecuritiesWithHighLastTradedValue": {
            "industry_collection": "dbsr_rank14_security_corporation_industry",
            "country_collection": "dbsr_rank15_security_corporation_country",
            "industry_security_id": first_value(q6_industry_doc, "SECURITYID"),
            "country_security_id": first_value(q6_country_doc, "SECURITYID"),
            "industry_ids": first_values(q6_industry_doc, "corporation.industry.INDUSTRYSECTORCLASSIFIERID"),
            "country_ids": first_values(q6_country_doc, "corporation.country.COUNTRYID"),
            "returned_sample": q6_industry_doc is not None and q6_country_doc is not None,
        },
        "Q7_PersonsWhoBoughtMoreIBMThanSold": {
            "collection": "dbsr_rank10_person_financialserviceaccount_transaction",
            "person_id": first_value(q7_q9_doc, "PERSONID"),
            "account_ids": first_values(q7_q9_doc, "financialServiceAccount.FINANCIALSERVICEACCOUNTID"),
            "transaction_ids": first_values(q7_q9_doc, "financialServiceAccount.transaction.SECURITIESTRANSACTIONID"),
            "transaction_kinds": first_values(q7_q9_doc, "financialServiceAccount.transaction.TRANSACTIONKIND"),
            "listed_security_ids": first_values(q7_q9_doc, "financialServiceAccount.transaction.REFERSTO"),
            "returned_sample": q7_q9_doc is not None,
        },
        "Q8_IBMTransactionsBelowAverageSellingPrice": {
            "collection": "dbsr_rank02_transaction_listedsecurity",
            "transaction_id": first_value(q8_doc, "SECURITIESTRANSACTIONID"),
            "listed_security_id": first_value(q8_doc, "REFERSTO"),
            "transaction_kind": first_value(q8_doc, "TRANSACTIONKIND"),
            "amount": first_value(q8_doc, "AMOUNT"),
            "ticker_symbol": first_value(q8_doc, "listedSecurity.TICKERSYMBOL"),
            "returned_sample": q8_doc is not None,
        },
        "Q9_PersonsWhoBoughtAndSoldSameStock": {
            "collection": "dbsr_rank10_person_financialserviceaccount_transaction",
            "person_id": first_value(q9_doc, "PERSONID"),
            "matched_stock_id": q9_stock_id,
            "matched_tx_count": q9_match.get("txCount") if q9_match else None,
            "account_ids": first_values(q9_doc, "financialServiceAccount.FINANCIALSERVICEACCOUNTID"),
            "transaction_ids": first_values(q9_doc, "financialServiceAccount.transaction.SECURITIESTRANSACTIONID"),
            "listed_security_ids": first_values(q9_doc, "financialServiceAccount.transaction.REFERSTO"),
            "transaction_kinds": first_values(q9_doc, "financialServiceAccount.transaction.TRANSACTIONKIND"),
            "returned_sample": q9_doc is not None and q9_match is not None,
        },
    }

    missing = [
        name for name, row in parameters.items()
        if not row.get("returned_sample")
    ]

    output = {
        "baseline": "DBSR",
        "dataset": "FIBEN",
        "scale_label": args.scale_label,
        "probe_type": "dbsr_fiben_query_parameter_probe",
        "mongo_database": args.mongo_db,
        "mongo_access": True,
        "official_benchmark": False,
        "collection_counts": counts,
        "parameters": parameters,
        "missing_parameter_samples": missing,
        "implementation_note": (
            "This probe only selects real parameter samples from the materialized DBSR "
            "collections. It does not measure latency and does not affect schema selection."
        ),
    }

    out_dir = Path(args.out_dir)
    output_path = out_dir / f"dbsr_fiben_query_parameter_probe_{args.scale_label}.json"

    write_json(output_path, output)

    print("DBSR FIBEN query parameter probe completed.")
    print(f"Mongo database: {args.mongo_db}")
    print(f"Collections counted: {len(counts)}")
    print(f"Missing parameter samples: {len(missing)}")
    print(f"Wrote {output_path}")

    for query_name, row in parameters.items():
        print(f"{query_name}: returned_sample={row.get('returned_sample')}")


if __name__ == "__main__":
    main()
