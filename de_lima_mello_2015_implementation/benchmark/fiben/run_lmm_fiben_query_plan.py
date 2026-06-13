"""
Run MongoDB explain("executionStats") for the Lima & Mello 2015 FIBEN materialization.

This script targets the already materialized database, e.g.:
  lmm_fiben_sf1_source_full

It produces:
- per-query explain summary CSV;
- raw explain JSON files;
- a status summary;
- a manifest.

Q10 is intentionally skipped because it is an insert/update workload, not a
read-query executionStats workload.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
from pymongo import MongoClient


QUERY_IDS = [
    "Q1_CompanyProfile",
    "Q2_CompanyWithIndustryCountryAndListedSecurities",
    "Q3_SecuritiesHeldInEachFinancialServiceAccount",
    "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity",
    "Q5_ReportsAndMetricDataOfCompany",
    "Q6_TechUSListedSecuritiesWithHighLastTradedValue",
    "Q7_PersonsWhoBoughtMoreIBMThanSold",
    "Q8_IBMTransactionsBelowAverageSellingPrice",
    "Q9_PersonsWhoBoughtAndSoldSameStock",
]


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return str(value)


def safe_int(value: Any) -> int:
    try:
        if value is None:
            return 0
        return int(value)
    except Exception:
        return 0


def walk_dicts(obj: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk_dicts(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk_dicts(item)


def collect_explain_metrics(explain: Dict[str, Any]) -> Dict[str, Any]:
    docs_examined = 0
    keys_examined = 0
    n_returned = 0
    execution_time_ms = 0

    stages = set()
    collections = set()

    for node in walk_dicts(explain):
        if "stage" in node:
            stages.add(str(node["stage"]))

        if "queryPlanner" in node and isinstance(node.get("queryPlanner"), dict):
            planner = node["queryPlanner"]
            if "namespace" in planner:
                collections.add(str(planner["namespace"]))

        if "nReturned" in node:
            n_returned += safe_int(node.get("nReturned"))

        if "totalDocsExamined" in node:
            docs_examined += safe_int(node.get("totalDocsExamined"))

        if "totalKeysExamined" in node:
            keys_examined += safe_int(node.get("totalKeysExamined"))

        if "executionTimeMillis" in node:
            execution_time_ms = max(execution_time_ms, safe_int(node.get("executionTimeMillis")))

        if "executionTimeMillisEstimate" in node:
            execution_time_ms = max(execution_time_ms, safe_int(node.get("executionTimeMillisEstimate")))

    return {
        "n_returned_accumulated": n_returned,
        "total_docs_examined_accumulated": docs_examined,
        "total_keys_examined_accumulated": keys_examined,
        "execution_time_ms_max": execution_time_ms,
        "stages": sorted(stages),
        "namespaces": sorted(collections),
        "has_ixscan": "IXSCAN" in stages,
        "has_collscan": "COLLSCAN" in stages,
        "has_fetch": "FETCH" in stages,
        "has_sort": "SORT" in stages,
        "has_lookup": "$lookup" in json.dumps(explain, default=json_default),
        "has_group": "$group" in json.dumps(explain, default=json_default),
        "has_unwind": "$unwind" in json.dumps(explain, default=json_default),
    }


def first_doc(db, collection: str, filter_doc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    doc = db[collection].find_one(filter_doc or {})
    return doc or {}


def first_non_header_doc(db, collection: str, id_field: str, extra_filter: Dict[str, Any] | None = None) -> Dict[str, Any]:
    filt: Dict[str, Any] = {
        id_field: {
            "$exists": True,
            "$nin": [None, "", id_field],
        }
    }
    if extra_filter:
        filt.update(extra_filter)

    doc = first_doc(db, collection, filt)
    if doc:
        return doc

    doc = first_doc(db, collection)
    if doc:
        return doc

    raise RuntimeError(f"Could not find any document in {collection}")


def pick_transaction_type_value(db, semantic_value: int) -> Any:
    """
    FIBEN scaled CSVs may load TRANSACTIONTYPE either as strings or numeric values.
    Pick the representation that exists in the materialized database.
    """
    as_str = str(semantic_value)

    if db["lmm_transaction"].count_documents({"TRANSACTIONTYPE": as_str}, limit=1):
        return as_str

    if db["lmm_transaction"].count_documents({"TRANSACTIONTYPE": semantic_value}, limit=1):
        return semantic_value

    # Fallback keeps previous behavior.
    return semantic_value


def pick_valid_transaction_refersto_for_buy_sell(db) -> str:
    """
    Pick a REFERSTO value with both buy and sell transactions.
    This avoids CSV header rows such as LISTEDSECURITYID and avoids zero-result Q8.
    """
    pipeline = [
        {
            "$match": {
                "listed_security.0": {"$exists": True},
                "REFERSTO": {
                    "$exists": True,
                    "$nin": [None, "", "REFERSTO", "LISTEDSECURITYID"],
                },
                "TRANSACTIONTYPE": {"$in": [1, 2, "1", "2"]},
            }
        },
        {
            "$group": {
                "_id": "$REFERSTO",
                "n_total": {"$sum": 1},
                "n_buy": {
                    "$sum": {
                        "$cond": [
                            {"$in": ["$TRANSACTIONTYPE", [1, "1"]]},
                            1,
                            0,
                        ]
                    }
                },
                "n_sell": {
                    "$sum": {
                        "$cond": [
                            {"$in": ["$TRANSACTIONTYPE", [2, "2"]]},
                            1,
                            0,
                        ]
                    }
                },
            }
        },
        {"$match": {"n_buy": {"$gt": 0}, "n_sell": {"$gt": 0}}},
        {"$sort": {"n_total": -1, "_id": 1}},
        {"$limit": 1},
    ]

    rows = list(db["lmm_transaction"].aggregate(pipeline, allowDiskUse=True))
    if rows:
        return rows[0]["_id"]

    fallback = db["lmm_transaction"].find_one(
        {
            "listed_security.0": {"$exists": True},
            "REFERSTO": {
                "$exists": True,
                "$nin": [None, "", "REFERSTO", "LISTEDSECURITYID"],
            },
        },
        {"REFERSTO": 1},
    )
    if fallback and fallback.get("REFERSTO"):
        return fallback["REFERSTO"]

    raise RuntimeError("Could not find a valid transaction REFERSTO for Q8/Q9 parameters.")



def pick_person_for_buy_sell_stock(db, refersto: str) -> str:
    """
    Pick a person directly from the embedded lmm_person structure used by Q7/Q9.
    The selected person must have both buy and sell transactions for the chosen
    stock, and must satisfy buy_total > sell_total for Q7.
    """
    pipeline = [
        {
            "$match": {
                "PERSONID": {"$exists": True, "$nin": [None, "", "PERSONID"]}
            }
        },
        {"$unwind": "$financial_service_account"},
        {"$unwind": "$financial_service_account.transaction"},
        {
            "$match": {
                "financial_service_account.transaction.REFERSTO": refersto,
                "financial_service_account.transaction.TRANSACTIONTYPE": {
                    "$in": [1, "1", 2, "2"]
                },
            }
        },
        {
            "$group": {
                "_id": "$PERSONID",
                "n_buy": {
                    "$sum": {
                        "$cond": [
                            {
                                "$in": [
                                    "$financial_service_account.transaction.TRANSACTIONTYPE",
                                    [1, "1"],
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "n_sell": {
                    "$sum": {
                        "$cond": [
                            {
                                "$in": [
                                    "$financial_service_account.transaction.TRANSACTIONTYPE",
                                    [2, "2"],
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "buy_total": {
                    "$sum": {
                        "$cond": [
                            {
                                "$in": [
                                    "$financial_service_account.transaction.TRANSACTIONTYPE",
                                    [1, "1"],
                                ]
                            },
                            "$financial_service_account.transaction.VALUE",
                            0,
                        ]
                    }
                },
                "sell_total": {
                    "$sum": {
                        "$cond": [
                            {
                                "$in": [
                                    "$financial_service_account.transaction.TRANSACTIONTYPE",
                                    [2, "2"],
                                ]
                            },
                            "$financial_service_account.transaction.VALUE",
                            0,
                        ]
                    }
                },
                "n_transactions": {"$sum": 1},
            }
        },
        {
            "$match": {
                "n_buy": {"$gt": 0},
                "n_sell": {"$gt": 0},
                "$expr": {"$gt": ["$buy_total", "$sell_total"]},
            }
        },
        {"$sort": {"n_transactions": -1, "_id": 1}},
        {"$limit": 1},
    ]

    rows = list(db["lmm_person"].aggregate(pipeline, allowDiskUse=True, maxTimeMS=600000))
    if rows:
        return rows[0]["_id"]

    raise RuntimeError(
        f"Could not find a Q7/Q9-compatible person for REFERSTO={refersto}"
    )


def pick_security_ids_for_corporation(db, corporation_id: str) -> list[str]:
    """
    SchemaLens Q7/Q8 are parameterized by corporation.
    It first finds Security documents provided by that corporation and then
    searches transactions whose REFERSTO matches those securities.

    In the LMM SF10 materialization, the same raw security may appear as
    SF10_SEC_R01_<id>, ..., SF10_SEC_R10_<id>. To avoid multiplying the
    workload cardinality by all scale replicas, we select one deterministic
    transaction-backed variant per raw security id, matching the SchemaLens
    benchmark cardinality.
    """
    corp_raw = str(corporation_id)
    corp_suffix = corp_raw.split("_")[-1]

    def norm_id(value):
        if value is None:
            return None
        s = str(value)
        if not s or s.upper() in {"ISPROVIDEDBY", "CORPORATIONID", "SECURITYID"}:
            return None
        return s.split("_")[-1]

    raw_security_ids = set()

    for s in db["lmm_security"].find(
        {
            "ISPROVIDEDBY": {"$exists": True, "$nin": [None, "", "ISPROVIDEDBY"]},
        },
        {"SECURITYID": 1, "_id": 1, "ISPROVIDEDBY": 1},
    ):
        if norm_id(s.get("ISPROVIDEDBY")) == corp_suffix:
            sid = s.get("SECURITYID") or s.get("_id")
            if sid and str(sid) != "SECURITYID":
                raw_security_ids.add(str(sid).split("_")[-1])

    selected_ids = []

    for raw_sid in sorted(raw_security_ids):
        # Prefer transaction-backed SF variants, deterministically sorted.
        variants = db["lmm_transaction"].distinct(
            "REFERSTO",
            {
                "REFERSTO": {
                    "$exists": True,
                    "$nin": [None, "", "REFERSTO", "LISTEDSECURITYID"],
                    "$regex": f"(^|_){re.escape(raw_sid)}$",
                }
            },
        )

        variants = sorted(
            str(v)
            for v in variants
            if v and str(v).split("_")[-1] == raw_sid
        )

        # Prefer SF-prefixed transaction-backed variants. The raw id may exist in
        # Security, but transactions in SF10 usually reference SF10_SEC_Rxx_<id>.
        sf_variants = [
            v for v in variants
            if v.startswith("SF10_SEC_R")
        ]

        if sf_variants:
            selected_ids.append(sf_variants[0])
        elif variants:
            selected_ids.append(variants[0])
        else:
            # Fallback to raw id if no transaction-backed id exists.
            selected_ids.append(raw_sid)

    if selected_ids:
        return selected_ids

    sample = list(db["lmm_security"].find(
        {},
        {"SECURITYID": 1, "_id": 1, "ISPROVIDEDBY": 1},
    ).limit(10))

    raise RuntimeError(
        f"Could not find securities for corporation_id={corporation_id}. "
        f"Sample lmm_security docs: {sample}"
    )


def pick_q9_refersto_raw_pool(db) -> str:
    """
    SchemaLens Q9 parameter pool:
    SELECT REFERSTO
    FROM transactions
    WHERE REFERSTO IS NOT NULL
    GROUP BY REFERSTO
    ORDER BY COUNT(*) DESC, REFERSTO
    LIMIT sample_size
    """
    rows = list(db["lmm_transaction"].aggregate(
        [
            {
                "$match": {
                    "REFERSTO": {
                        "$exists": True,
                        "$nin": [None, "", "REFERSTO", "LISTEDSECURITYID"],
                    }
                }
            },
            {"$group": {"_id": "$REFERSTO", "n": {"$sum": 1}}},
            {"$sort": {"n": -1, "_id": 1}},
            {"$limit": 1},
        ],
        allowDiskUse=True,
        maxTimeMS=600000,
    ))

    if rows:
        return rows[0]["_id"]

    raise RuntimeError("Could not find a raw REFERSTO parameter for Q9.")


def pick_q4_person_with_reachable_company(db) -> str:
    """
    SchemaLens Q4 parameter rule:
    choose a Person with a complete path
    Person -> FinancialServiceAccount -> Holding -> Security -> Corporation.

    In the LMM materialization, the path is embedded from lmm_person through
    financial_service_account and holding. We require at least one holding that
    can be linked to a security/corporation.
    """
    pipeline = [
        {
            "$match": {
                "PERSONID": {"$exists": True, "$nin": [None, "", "PERSONID"]}
            }
        },
        {"$unwind": "$financial_service_account"},
        {"$unwind": "$financial_service_account.holding"},
        {
            "$match": {
                "financial_service_account.holding.REFERSTO": {
                    "$exists": True,
                    "$nin": [None, "", "REFERSTO", "SECURITYID", "LISTEDSECURITYID"],
                }
            }
        },
        {
            "$group": {
                "_id": "$PERSONID",
                "n_holdings": {"$sum": 1},
                "sample_refersto": {"$first": "$financial_service_account.holding.REFERSTO"},
            }
        },
        {"$sort": {"n_holdings": -1, "_id": 1}},
        {"$limit": 1},
    ]

    rows = list(db["lmm_person"].aggregate(pipeline, allowDiskUse=True, maxTimeMS=600000))
    if rows and rows[0].get("_id"):
        return rows[0]["_id"]

    raise RuntimeError("Could not find a Q4-compatible person in lmm_person.")

def build_params(db) -> Dict[str, Any]:
    company = first_doc(db, "lmm_corporation", {"TICKER": "IBM"})
    if not company:
        company = first_doc(db, "lmm_corporation", {"TICKER": {"$regex": "^IBM"}})
    if not company:
        company = first_non_header_doc(db, "lmm_corporation", "CORPORATIONID")

    corporation_id = str(company.get("CORPORATIONID"))
    corporation_security_ids = pick_security_ids_for_corporation(db, corporation_id)

    account = first_non_header_doc(
        db,
        "lmm_financial_service_account",
        "FINANCIALSERVICEACCOUNTID",
    )

    # Q4 follows the SchemaLens parameter rule: choose a person with a complete
    # Person -> Account -> Holding -> Security -> Corporation path.
    q4_person_id = pick_q4_person_with_reachable_company(db)

    # Q9 follows the original SchemaLens raw REFERSTO pool.
    q9_refersto = pick_q9_refersto_raw_pool(db)

    buy_type = pick_transaction_type_value(db, 1)
    sell_type = pick_transaction_type_value(db, 2)

    return {
        "corporation_id": corporation_id,
        "corporation_ticker": company.get("TICKER"),
        "person_id": q4_person_id,
        "account_id": account.get("FINANCIALSERVICEACCOUNTID"),
        "listed_security_id": q9_refersto,
        "transaction_refersto": q9_refersto,
        "corporation_security_ids": corporation_security_ids,
        "high_value_threshold": 4500,
        "buy_type": buy_type,
        "sell_type": sell_type,
        "buy_type_values": [1, "1"],
        "sell_type_values": [2, "2"],
    }


def maybe_limit(pipeline: List[Dict[str, Any]], result_limit: Optional[int]) -> List[Dict[str, Any]]:
    if result_limit is None:
        return pipeline
    return pipeline + [{"$limit": result_limit}]


def build_queries(params: Dict[str, Any], result_limit: Optional[int]) -> List[Dict[str, Any]]:
    corp_id = params["corporation_id"]
    person_id = params["person_id"]
    account_id = params["account_id"]
    security_id = params["listed_security_id"]
    corporation_security_ids = params.get("corporation_security_ids", [])
    high_value = params["high_value_threshold"]
    buy_type = params["buy_type"]
    sell_type = params["sell_type"]
    buy_type_values = params.get("buy_type_values", [1, "1"])
    sell_type_values = params.get("sell_type_values", [2, "2"])

    queries: List[Dict[str, Any]] = []

    queries.append({
        "query_id": "Q1",
        "query_name": "Q1_CompanyProfile",
        "root_collection": "lmm_corporation",
        "pipeline": maybe_limit([
            {"$match": {"CORPORATIONID": corp_id}},
            {"$project": {
                "CORPORATIONID": 1,
                "TICKER": 1,
                "NAME": 1,
                "country": 1,
                "industry": 1,
            }},
        ], result_limit),
    })

    queries.append({
        "query_id": "Q2",
        "query_name": "Q2_CompanyWithIndustryCountryAndListedSecurities",
        "root_collection": "lmm_corporation",
        "pipeline": maybe_limit([
            {"$match": {"CORPORATIONID": corp_id}},
            {"$lookup": {
                "from": "lmm_listed_security",
                "localField": "CORPORATIONID",
                "foreignField": "ISPROVIDEDBY",
                "as": "listed_securities",
            }},
            {"$project": {
                "CORPORATIONID": 1,
                "TICKER": 1,
                "NAME": 1,
                "country": 1,
                "industry": 1,
                "listed_securities": 1,
            }},
        ], result_limit),
    })

    queries.append({
        "query_id": "Q3",
        "query_name": "Q3_SecuritiesHeldInEachFinancialServiceAccount",
        "root_collection": "lmm_financial_service_account",
        "pipeline": maybe_limit([
            {"$match": {"FINANCIALSERVICEACCOUNTID": account_id}},
            {"$project": {
                "FINANCIALSERVICEACCOUNTID": 1,
                "ISOWNEDBY": 1,
                "holding": 1,
            }},
        ], result_limit),
    })

    queries.append({
        "query_id": "Q4",
        "query_name": "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity",
        "root_collection": "lmm_person",
        "pipeline": maybe_limit([
            {"$match": {"PERSONID": person_id}},
            {"$unwind": "$financial_service_account"},
            {"$unwind": "$financial_service_account.holding"},
            {"$lookup": {
                "from": "lmm_listed_security",
                "localField": "financial_service_account.holding.REFERSTO",
                "foreignField": "LISTEDSECURITYID",
                "as": "listed_security",
            }},
            {"$unwind": "$listed_security"},
            {"$lookup": {
                "from": "lmm_corporation",
                "localField": "listed_security.ISPROVIDEDBY",
                "foreignField": "CORPORATIONID",
                "as": "corporation",
            }},
            {"$project": {
                "PERSONID": 1,
                "financial_service_account.FINANCIALSERVICEACCOUNTID": 1,
                "listed_security.LISTEDSECURITYID": 1,
                "corporation.CORPORATIONID": 1,
                "corporation.NAME": 1,
            }},
        ], result_limit),
    })

    queries.append({
        "query_id": "Q5",
        "query_name": "Q5_ReportsAndMetricDataOfCompany",
        "root_collection": "lmm_corporation",
        "pipeline": maybe_limit([
            {"$match": {"CORPORATIONID": corp_id}},
            {"$unwind": "$financial_report"},
            {"$project": {
                "CORPORATIONID": 1,
                "TICKER": 1,
                "financial_report.FINANCIALREPORTID": 1,
                "financial_report.report_element": 1,
                "financial_report.disclosure_ref": 1,
            }},
        ], result_limit),
    })

    queries.append({
        "query_id": "Q6",
        "query_name": "Q6_TechUSListedSecuritiesWithHighLastTradedValue",
        "root_collection": "lmm_transaction",
        "pipeline": maybe_limit([
            {"$match": {"VALUE": {"$gte": high_value}}},
            {"$lookup": {
                "from": "lmm_listed_security",
                "localField": "REFERSTO",
                "foreignField": "LISTEDSECURITYID",
                "as": "listed_security",
            }},
            {"$unwind": "$listed_security"},
            {"$lookup": {
                "from": "lmm_corporation",
                "localField": "listed_security.ISPROVIDEDBY",
                "foreignField": "CORPORATIONID",
                "as": "corporation",
            }},
            {"$project": {
                "SECURITIESTRANSACTIONID": 1,
                "REFERSTO": 1,
                "VALUE": 1,
                "listed_security": 1,
                "corporation.CORPORATIONID": 1,
                "corporation.NAME": 1,
            }},
        ], result_limit),
    })

    queries.append({
        "query_id": "Q7",
        "query_name": "Q7_PersonsWhoBoughtMoreIBMThanSold",
        "root_collection": "lmm_transaction",
        "pipeline": maybe_limit([
            {"$match": {
                "REFERSTO": {"$in": corporation_security_ids},
                "TRANSACTIONTYPE": {"$in": buy_type_values + sell_type_values},
            }},
            {"$group": {
                "_id": "$ISFACILITATEDBY",
                "buy_total": {
                    "$sum": {
                        "$cond": [
                            {"$in": ["$TRANSACTIONTYPE", buy_type_values]},
                            {"$ifNull": ["$HASCOUNT", {"$ifNull": ["$COUNT", "$VALUE"]}]},
                            0,
                        ]
                    }
                },
                "sell_total": {
                    "$sum": {
                        "$cond": [
                            {"$in": ["$TRANSACTIONTYPE", sell_type_values]},
                            {"$ifNull": ["$HASCOUNT", {"$ifNull": ["$COUNT", "$VALUE"]}]},
                            0,
                        ]
                    }
                },
                "n_transactions": {"$sum": 1},
            }},
            {"$match": {"$expr": {"$gt": ["$buy_total", "$sell_total"]}}},
        ], result_limit),
    })

    queries.append({
        "query_id": "Q8",
        "query_name": "Q8_IBMTransactionsBelowAverageSellingPrice",
        "root_collection": "lmm_transaction",
        "pipeline": maybe_limit([
            {"$match": {
                "REFERSTO": {"$in": corporation_security_ids},
            }},
            {"$set": {
                "_price_value": {
                    "$ifNull": ["$HASPRICE", {"$ifNull": ["$PRICE", "$VALUE"]}]
                }
            }},
            {"$group": {
                "_id": None,
                "avg_sell_price": {
                    "$avg": {
                        "$cond": [
                            {"$in": ["$TRANSACTIONTYPE", sell_type_values]},
                            "$_price_value",
                            None,
                        ]
                    }
                },
                "transactions": {
                    "$push": {
                        "SECURITIESTRANSACTIONID": "$SECURITIESTRANSACTIONID",
                        "REFERSTO": "$REFERSTO",
                        "TRANSACTIONTYPE": "$TRANSACTIONTYPE",
                        "price": "$_price_value",
                    }
                },
            }},
            {"$unwind": "$transactions"},
            {"$match": {"$expr": {"$lt": ["$transactions.price", "$avg_sell_price"]}}},
        ], result_limit),
    })

    queries.append({
        "query_id": "Q9",
        "query_name": "Q9_PersonsWhoBoughtAndSoldSameStock",
        "root_collection": "lmm_transaction",
        "pipeline": maybe_limit([
            {"$match": {
                "REFERSTO": security_id,
                "TRANSACTIONTYPE": {"$in": buy_type_values + sell_type_values},
            }},
            {"$group": {
                "_id": "$ISFACILITATEDBY",
                "types": {"$addToSet": "$TRANSACTIONTYPE"},
                "n_transactions": {"$sum": 1},
            }},
            {"$match": {"$expr": {"$and": [
                {"$gt": [{"$size": {"$setIntersection": ["$types", buy_type_values]}}, 0]},
                {"$gt": [{"$size": {"$setIntersection": ["$types", sell_type_values]}}, 0]},
            ]}}},
        ], result_limit),
    })

    return queries


def explain_aggregate(db, collection: str, pipeline: List[Dict[str, Any]], max_time_ms: int) -> Dict[str, Any]:
    return db.command(
        {
            "explain": {
                "aggregate": collection,
                "pipeline": pipeline,
                "cursor": {},
                "maxTimeMS": max_time_ms,
            },
            "verbosity": "executionStats",
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo-uri", default="mongodb://mongo:mongo@127.0.0.1:27018/admin")
    parser.add_argument("--db-name", default="lmm_fiben_sf1_source_full")
    parser.add_argument("--scale", default="sf1")
    parser.add_argument("--output-dir", default="de_lima_mello_2015_implementation/results/fiben/query_plan")
    parser.add_argument("--max-time-ms", type=int, default=120000)
    parser.add_argument("--result-limit", type=int, default=1000)
    parser.add_argument("--queries", default=None, help="Comma-separated query ids, e.g. Q1,Q2,Q5")
    args = parser.parse_args()

    client = MongoClient(args.mongo_uri)
    db = client[args.db_name]

    output_dir = Path(args.output_dir) / args.scale / args.db_name
    raw_dir = output_dir / "raw_explain_json"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    params = build_params(db)
    query_specs = build_queries(params, result_limit=args.result_limit)

    if args.queries:
        selected = {q.strip().upper() for q in args.queries.split(",")}
        query_specs = [q for q in query_specs if q["query_id"].upper() in selected]

    rows: List[Dict[str, Any]] = []

    print(f"[{now()}] Running Lima & Mello FIBEN query plans on {args.db_name}")
    print(f"[{now()}] Params: {json.dumps(params, default=json_default)}")

    for spec in query_specs:
        qid = spec["query_id"]
        qname = spec["query_name"]
        collection = spec["root_collection"]
        pipeline = spec["pipeline"]

        print(f"[{now()}] Explain {qid}: {qname} on {collection}", flush=True)

        started = time.time()

        try:
            explain = explain_aggregate(
                db=db,
                collection=collection,
                pipeline=pipeline,
                max_time_ms=args.max_time_ms,
            )
            metrics = collect_explain_metrics(explain)

            raw_path = raw_dir / f"{qid}_{qname}.json"
            raw_path.write_text(
                json.dumps(explain, indent=2, sort_keys=True, default=json_default),
                encoding="utf-8",
            )

            rows.append({
                "method": "lima_mello_2015",
                "dataset": "FIBEN",
                "scale": args.scale,
                "database": args.db_name,
                "query_id": qid,
                "query_name": qname,
                "root_collection": collection,
                "status": "completed",
                "elapsed_wall_seconds": time.time() - started,
                "max_time_ms": args.max_time_ms,
                "result_limit": args.result_limit,
                "n_returned_accumulated": metrics["n_returned_accumulated"],
                "total_docs_examined_accumulated": metrics["total_docs_examined_accumulated"],
                "total_keys_examined_accumulated": metrics["total_keys_examined_accumulated"],
                "execution_time_ms_max": metrics["execution_time_ms_max"],
                "has_ixscan": metrics["has_ixscan"],
                "has_collscan": metrics["has_collscan"],
                "has_fetch": metrics["has_fetch"],
                "has_sort": metrics["has_sort"],
                "has_lookup": metrics["has_lookup"],
                "has_group": metrics["has_group"],
                "has_unwind": metrics["has_unwind"],
                "stages": metrics["stages"],
                "namespaces": metrics["namespaces"],
                "raw_explain_json": str(raw_path),
                "pipeline_json": json.dumps(pipeline, default=json_default),
            })

        except Exception as exc:
            rows.append({
                "method": "lima_mello_2015",
                "dataset": "FIBEN",
                "scale": args.scale,
                "database": args.db_name,
                "query_id": qid,
                "query_name": qname,
                "root_collection": collection,
                "status": f"failed: {exc}",
                "elapsed_wall_seconds": time.time() - started,
                "max_time_ms": args.max_time_ms,
                "result_limit": args.result_limit,
                "n_returned_accumulated": None,
                "total_docs_examined_accumulated": None,
                "total_keys_examined_accumulated": None,
                "execution_time_ms_max": None,
                "has_ixscan": None,
                "has_collscan": None,
                "has_fetch": None,
                "has_sort": None,
                "has_lookup": None,
                "has_group": None,
                "has_unwind": None,
                "stages": [],
                "namespaces": [],
                "raw_explain_json": None,
                "pipeline_json": json.dumps(pipeline, default=json_default),
            })

    summary_df = pd.DataFrame(rows)

    summary_csv = output_dir / "lmm_fiben_query_plan_summary_results.csv"
    status_csv = output_dir / "lmm_fiben_query_plan_status_summary.csv"
    params_json = output_dir / "lmm_fiben_query_plan_params.json"
    manifest_json = output_dir / "lmm_fiben_query_plan_manifest.json"

    summary_df.to_csv(summary_csv, index=False)

    status_df = (
        summary_df.groupby("status", as_index=False)
        .agg(n_queries=("query_id", "count"))
        .sort_values("status")
    )
    status_df.to_csv(status_csv, index=False)

    params_json.write_text(
        json.dumps(params, indent=2, sort_keys=True, default=json_default),
        encoding="utf-8",
    )

    manifest = {
        "status": "completed",
        "method": "lima_mello_2015",
        "dataset": "FIBEN",
        "scale": args.scale,
        "database": args.db_name,
        "query_count": int(len(summary_df)),
        "status_counts": summary_df["status"].value_counts().to_dict(),
        "output_files": {
            "summary_csv": str(summary_csv),
            "status_csv": str(status_csv),
            "params_json": str(params_json),
            "manifest_json": str(manifest_json),
            "raw_explain_json_dir": str(raw_dir),
        },
        "important_note": "Q10 is skipped because it is an insert/update workload.",
    }

    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=json_default),
        encoding="utf-8",
    )

    print(f"[{now()}] Done.")
    print(json.dumps(manifest, indent=2, sort_keys=True, default=json_default))


if __name__ == "__main__":
    main()
