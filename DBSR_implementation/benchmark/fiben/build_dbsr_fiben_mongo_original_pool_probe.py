#!/usr/bin/env python3
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pymongo import MongoClient


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def numeric_suffix(value: Any) -> str:
    if value is None:
        return ""
    m = re.search(r"([0-9]+)$", str(value))
    return m.group(1) if m else str(value)


def sort_key(value: Any) -> Tuple[int, Any]:
    s = str(value)
    return (0, int(s)) if s.isdigit() else (1, s)


def get_any(doc: Dict[str, Any], keys: List[str], default=None):
    for key in keys:
        if key in doc:
            return doc.get(key)
    return default


def get_collection(db, *names):
    for name in names:
        if name in db.list_collection_names():
            return db[name]
    return db[names[0]]


def find_ibm_or_fallback(db) -> Any:
    corporation = get_collection(db, "fiben_corporations", "Corporation", "corporations")
    security = get_collection(db, "fiben_securities", "Security", "securities")

    # Try IBM-like corporation first.
    for doc in corporation.find({}, {"CORPORATIONID": 1, "HASTICKERSYMBOL": 1, "HASLEGALNAME": 1}):
        ticker = str(doc.get("HASTICKERSYMBOL", "")).upper()
        legal = str(doc.get("HASLEGALNAME", "")).upper()
        if ticker == "IBM" or "IBM" in legal:
            return doc.get("CORPORATIONID")

    # Fallback: corporation with most securities.
    counts = defaultdict(int)
    for sec in security.find({}, {"ISPROVIDEDBY": 1}):
        cid = sec.get("ISPROVIDEDBY")
        if cid is not None:
            counts[cid] += 1

    if not counts:
        first = corporation.find_one({}, {"CORPORATIONID": 1})
        return None if not first else first.get("CORPORATIONID")

    return sorted(counts.items(), key=lambda kv: (-kv[1], sort_key(kv[0])))[0][0]


def build_q3_pool(db, sample_size: int) -> List[Any]:
    fsa = get_collection(db, "fiben_financial_service_accounts", "FinancialServiceAccount", "financial_service_accounts")
    ids = [
        doc.get("FINANCIALSERVICEACCOUNTID")
        for doc in fsa.find({}, {"FINANCIALSERVICEACCOUNTID": 1})
        if doc.get("FINANCIALSERVICEACCOUNTID") is not None
    ]
    return sorted(ids, key=sort_key)[:sample_size]


def build_q4_pool(db, sample_size: int) -> Tuple[List[Any], List[Dict[str, Any]]]:
    person = get_collection(db, "fiben_persons", "Person", "persons")
    fsa = get_collection(db, "fiben_financial_service_accounts", "FinancialServiceAccount", "financial_service_accounts")
    holding = get_collection(db, "fiben_holdings", "Holding", "holdings")
    security = get_collection(db, "fiben_securities", "Security", "securities")

    # Security suffix -> corporation ids.
    suffix_to_corporations = defaultdict(set)
    for sec in security.find({}, {"SECURITYID": 1, "ISPROVIDEDBY": 1}):
        suffix = numeric_suffix(sec.get("SECURITYID"))
        cid = sec.get("ISPROVIDEDBY")
        if suffix and cid is not None:
            suffix_to_corporations[suffix].add(str(cid))

    # FSA -> owner person.
    fsa_owner = {}
    for acc in fsa.find({}, {"FINANCIALSERVICEACCOUNTID": 1, "ISOWNEDBY": 1}):
        aid = acc.get("FINANCIALSERVICEACCOUNTID")
        owner = acc.get("ISOWNEDBY")
        if aid is not None and owner is not None:
            fsa_owner[str(aid)] = owner

    person_to_corps = defaultdict(set)
    person_to_holdings = defaultdict(set)

    # Holding -> FSA -> Person and Holding.REFERSTO -> Security suffix -> Corp.
    for h in holding.find({}, {"HOLDINGID": 1, "ISHELDBY": 1, "REFERSTO": 1}):
        aid = h.get("ISHELDBY")
        if aid is None:
            continue

        owner = fsa_owner.get(str(aid))
        if owner is None:
            continue

        suffix = numeric_suffix(h.get("REFERSTO"))
        if not suffix or suffix not in suffix_to_corporations:
            continue

        hid = h.get("HOLDINGID")
        if hid is not None:
            person_to_holdings[str(owner)].add(str(hid))

        for cid in suffix_to_corporations[suffix]:
            person_to_corps[str(owner)].add(cid)

    # Keep original person ids as stored.
    known_person_ids = {
        str(p.get("PERSONID")): p.get("PERSONID")
        for p in person.find({}, {"PERSONID": 1})
        if p.get("PERSONID") is not None
    }

    rows = []
    for person_key, corp_set in person_to_corps.items():
        if not corp_set:
            continue

        pid = known_person_ids.get(person_key, person_key)
        rows.append({
            "PERSONID": pid,
            "n_reachable_corporations": len(corp_set),
            "n_holdings": len(person_to_holdings.get(person_key, set())),
        })

    rows.sort(
        key=lambda r: (
            -int(r["n_reachable_corporations"]),
            -int(r["n_holdings"]),
            sort_key(r["PERSONID"]),
        )
    )

    return [r["PERSONID"] for r in rows[:sample_size]], rows[:sample_size]


def build_q9_pool(db, sample_size: int) -> List[Any]:
    transaction = get_collection(db, "fiben_transactions", "Transaction", "transactions")

    pipeline = [
        {"$match": {"REFERSTO": {"$ne": None}}},
        {"$group": {"_id": "$REFERSTO", "n": {"$sum": 1}}},
        {"$sort": {"n": -1, "_id": 1}},
        {"$limit": sample_size},
    ]

    return [row["_id"] for row in transaction.aggregate(pipeline, allowDiskUse=True)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-probe", required=True)
    parser.add_argument("--scale-label", required=True)
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--mongo-host", default="127.0.0.1")
    parser.add_argument("--mongo-port", type=int, default=27018)
    parser.add_argument("--mongo-username", default="mongo")
    parser.add_argument("--mongo-password", default="mongo")
    parser.add_argument("--mongo-auth-source", default="admin")
    parser.add_argument("--mongo-db", required=True)
    parser.add_argument("--out-probe", required=True)
    parser.add_argument("--out-diagnostics", required=True)
    args = parser.parse_args()

    client = MongoClient(
        host=args.mongo_host,
        port=args.mongo_port,
        username=args.mongo_username,
        password=args.mongo_password,
        authSource=args.mongo_auth_source,
    )
    db = client[args.mongo_db]

    probe = read_json(Path(args.base_probe))
    params = probe.setdefault("parameters", {})

    ibm_corporation_id = find_ibm_or_fallback(db)
    q3_pool = build_q3_pool(db, args.sample_size)
    q4_pool, q4_rows = build_q4_pool(db, args.sample_size)
    q9_pool = build_q9_pool(db, args.sample_size)

    for q in [
        "Q1_CompanyProfileIBM",
        "Q2_CompanyWithIndustryCountryAndListedSecurities",
        "Q5_ReportsAndMetricDataOfCompany",
        "Q7_PersonsWhoBoughtMoreIBMThanSold",
        "Q8_IBMTransactionsBelowAverageSellingPrice",
    ]:
        params.setdefault(q, {})
        params[q]["corporation_id"] = ibm_corporation_id
        params[q]["corporation_id_pool"] = [ibm_corporation_id]

    q3 = "Q3_SecuritiesHeldInEachFinancialServiceAccount"
    params.setdefault(q3, {})
    params[q3]["financial_service_account_id"] = q3_pool[0] if q3_pool else None
    params[q3]["financial_service_account_id_pool"] = q3_pool

    q4 = "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity"
    params.setdefault(q4, {})
    params[q4]["person_id"] = q4_pool[0] if q4_pool else None
    params[q4]["person_id_pool"] = q4_pool

    q6 = "Q6_TechUSListedSecuritiesWithHighLastTradedValue"
    params.setdefault(q6, {})
    params[q6].update({
        "industry_keyword": "tech",
        "country_name": "United States",
        "min_last_traded_value": 100,
    })

    q9 = "Q9_PersonsWhoBoughtAndSoldSameStock"
    params.setdefault(q9, {})
    params[q9]["listed_security_id"] = q9_pool[0] if q9_pool else None
    params[q9]["listed_security_id_pool"] = q9_pool

    q10 = "Q10_CreateAccountHoldingAndBuyTransaction"
    params.setdefault(q10, {})
    params[q10]["person_id_pool"] = q4_pool
    params[q10]["listed_security_id_pool"] = q9_pool

    probe["scale_label"] = args.scale_label
    probe["parameter_alignment"] = "mongo_original_pool_aligned"

    diagnostics = {
        "dataset": "FIBEN",
        "scale_label": args.scale_label,
        "mongo_database": args.mongo_db,
        "method": "mongo_original_pool_aligned",
        "ibm_corporation_id": ibm_corporation_id,
        "Q3_pool": q3_pool,
        "Q4_pool": q4_rows,
        "Q9_pool": q9_pool,
    }

    write_json(Path(args.out_probe), probe)
    write_json(Path(args.out_diagnostics), diagnostics)

    print(f"Wrote {args.out_probe}")
    print(f"Wrote {args.out_diagnostics}")
    print(f"IBM corporation: {ibm_corporation_id}")
    print(f"Q3 first 10: {q3_pool[:10]}")
    print(f"Q4 first 10: {q4_rows[:10]}")
    print(f"Q9 first 10: {q9_pool[:10]}")


if __name__ == "__main__":
    main()
