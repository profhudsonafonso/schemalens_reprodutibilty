#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


INDEX_PLAN = {
    "dbsr_rank01_listedsecurity": [
        [("LISTEDSECURITYID", 1)],
        [("TICKERSYMBOL", 1)],
    ],
    "dbsr_rank02_transaction_listedsecurity": [
        [("SECURITIESTRANSACTIONID", 1)],
        [("REFERSTO", 1)],
        [("TRANSACTIONKIND", 1)],
        [("REFERSTO", 1), ("TRANSACTIONKIND", 1)],
        [("listedSecurity.TICKERSYMBOL", 1)],
    ],
    "dbsr_rank03_corporation": [
        [("CORPORATIONID", 1)],
        [("TICKERSYMBOL", 1)],
    ],
    "dbsr_rank04_person": [
        [("PERSONID", 1)],
    ],
    "dbsr_rank05_corporation_country": [
        [("CORPORATIONID", 1)],
        [("country.COUNTRYID", 1)],
    ],
    "dbsr_rank06_corporation_industry": [
        [("CORPORATIONID", 1)],
        [("industry.INDUSTRYSECTORCLASSIFIERID", 1)],
    ],
    "dbsr_rank07_financialserviceaccount_holding_listedsecurity": [
        [("FINANCIALSERVICEACCOUNTID", 1)],
        [("holding.REFERSTO", 1)],
        [("holding.listedSecurity.LISTEDSECURITYID", 1)],
    ],
    "dbsr_rank08_corporation_security_listedsecurity": [
        [("CORPORATIONID", 1)],
        [("security.SECURITYID", 1)],
        [("security.listedSecurity.LISTEDSECURITYID", 1)],
    ],
    "dbsr_rank09_financialserviceaccount_transaction_listedsecurity": [
        [("FINANCIALSERVICEACCOUNTID", 1)],
        [("transaction.REFERSTO", 1)],
        [("transaction.TRANSACTIONKIND", 1)],
        [("transaction.REFERSTO", 1), ("transaction.TRANSACTIONKIND", 1)],
    ],
    "dbsr_rank10_person_financialserviceaccount_transaction": [
        [("PERSONID", 1)],
        [("financialServiceAccount.FINANCIALSERVICEACCOUNTID", 1)],
        [("financialServiceAccount.transaction.REFERSTO", 1)],
        [("financialServiceAccount.transaction.TRANSACTIONKIND", 1)],
    ],
    "dbsr_rank11_person_financialserviceaccount_holding": [
        [("PERSONID", 1)],
        [("financialServiceAccount.FINANCIALSERVICEACCOUNTID", 1)],
        [("financialServiceAccount.holding.REFERSTO", 1)],
    ],
    "dbsr_rank12_listedsecurity_security_corporation": [
        [("LISTEDSECURITYID", 1)],
        [("security.SECURITYID", 1)],
        [("security.corporation.CORPORATIONID", 1)],
    ],
    "dbsr_rank13_financialreport_reportelement_statementelement": [
        [("FINANCIALREPORTID", 1)],
        [("REPORTSOF", 1)],
        [("reportElement.ELEMENTSOFFINANCIALREPORTID", 1)],
        [("reportElement.statementElement.ELEMENTOFFINANCIALSTATEMENTID", 1)],
    ],
    "dbsr_rank14_security_corporation_industry": [
        [("SECURITYID", 1)],
        [("corporation.CORPORATIONID", 1)],
        [("corporation.industry.INDUSTRYSECTORCLASSIFIERID", 1)],
    ],
    "dbsr_rank15_security_corporation_country": [
        [("SECURITYID", 1)],
        [("corporation.CORPORATIONID", 1)],
        [("corporation.country.COUNTRYID", 1)],
    ],
}


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


def index_name(fields: List[tuple]) -> str:
    return "idx_" + "_".join(f"{name.replace('.', '_')}_{direction}" for name, direction in fields)


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

    created = []
    failed = []

    for collection, index_specs in INDEX_PLAN.items():
        for fields in index_specs:
            try:
                name = db[collection].create_index(fields, name=index_name(fields))
                created.append({
                    "collection": collection,
                    "fields": fields,
                    "index_name": name,
                    "status": "created_or_existing",
                })
            except Exception as exc:
                failed.append({
                    "collection": collection,
                    "fields": fields,
                    "status": "failed",
                    "error": repr(exc),
                })

    output = {
        "baseline": "DBSR",
        "dataset": "FIBEN",
        "scale_label": args.scale_label,
        "mongo_database": args.mongo_db,
        "index_plan_type": "dbsr_secondary_indexes",
        "collections": len(INDEX_PLAN),
        "indexes_requested": sum(len(v) for v in INDEX_PLAN.values()),
        "indexes_created_or_existing": len(created),
        "indexes_failed": len(failed),
        "created": created,
        "failed": failed,
        "implementation_note": (
            "These indexes are created on DBSR materialized collections before the official "
            "query benchmark. They do not change the DBSR document structures."
        ),
    }

    out = Path(args.out_dir) / f"dbsr_fiben_index_manifest_{args.scale_label}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("DBSR FIBEN indexes created.")
    print(f"Indexes requested: {output['indexes_requested']}")
    print(f"Indexes created/existing: {output['indexes_created_or_existing']}")
    print(f"Indexes failed: {output['indexes_failed']}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
