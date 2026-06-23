#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


ENTITY_FILE_MAP = {
    "Corporation": "CORPORATION.csv",
    "Industry": "INDUSTRYSECTORCLASSIFIER.csv",
    "Country": "COUNTRY.csv",
    "Security": "SECURITY.csv",
    "ListedSecurity": "LISTEDSECURITY.csv",
    "Person": "PERSON.csv",
    "FinancialServiceAccount": "FINANCIALSERVICEACCOUNT.csv",
    "Holding": "HOLDING.csv",
    "Transaction": "SECURITIESTRANSACTION.csv",
    "FinancialReport": "FINANCIALREPORT.csv",
    "ReportElement": "ELEMENTSOFFINANCIALREPORT.csv",
    "StatementElement": "ELEMENTOFFINANCIALSTATEMENT.csv",
}

# Headerless official FIBEN CSV files.
# These names are aligned with the DBSR input model and materialization plan.
ENTITY_COLUMNS = {
    "Corporation": [
        "CORPORATIONID",
        "ISCLASSIFIEDBY",
        "ISDOMICILEDIN",
        "TICKERSYMBOL",
        "NAME",
    ],
    "Industry": [
        "INDUSTRYSECTORCLASSIFIERID",
        "PARENTID",
        "CLASSIFICATIONCODE",
        "CLASSIFICATIONNAME",
        "SECTORCODE",
        "SECTORNAME",
    ],
    "Country": [
        "COUNTRYID",
        "NAME",
        "REGIONID",
    ],
    "Security": [
        "SECURITYID",
        "FINANCIALMARKETID",
        "ISPROVIDEDBY",
    ],
    "ListedSecurity": [
        "LISTEDSECURITYID",
        "FINANCIALMARKETID",
        "FIRSTTRADEDATE",
        "TICKERSYMBOL",
        "NAME",
    ],
    "Person": [
        "PERSONID",
        "COUNTRYID",
        "RESIDENCEID",
        "GENDER",
        "BIRTHDATE",
        "FULLNAME",
        "LASTNAME",
        "FIRSTNAME",
        "CITY",
    ],
    "FinancialServiceAccount": [
        "FINANCIALSERVICEACCOUNTID",
        "ISOWNEDBY",
        "BROKERID",
        "ACCOUNTNUMBER",
        "OPENDATE",
    ],
    "Holding": [
        "HOLDINGID",
        "ISHELDBY",
        "REFERSTO",
        "DESCRIPTION",
        "QUANTITY",
    ],
    "Transaction": [
        "SECURITIESTRANSACTIONID",
        "ISFACILITATEDBY",
        "TRANSACTIONTYPEID",
        "REFERSTO",
        "TRANSACTIONKIND",
        "TRANSACTIONDATE",
        "AMOUNT",
    ],
    "FinancialReport": [
        "FINANCIALREPORTID",
        "REPORTSOF",
        "ACCESSIONNUMBER",
    ],
    "ReportElement": [
        "ELEMENTSOFFINANCIALREPORTID",
        "ISMEMBEROF",
    ],
    "StatementElement": [
        "ELEMENTOFFINANCIALSTATEMENTID",
        "FISCALYEAR",
        "PERIODENDDATE",
        "FORMTYPE",
        "FISCALPERIOD",
        "CURRENCY",
        "PERIODTYPE",
        "CONCEPT",
        "INSTANTDATE",
        "ISSEGMENTED",
        "NUMERICVALUE",
        "FISCALYEAR_DUP",
        "NAMESPACE",
        "SOURCEFILE",
        "QUARTER",
    ],
}


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


def input_entities(input_model: Dict[str, Any]) -> List[Dict[str, Any]]:
    skip = {"BuyTransaction", "SellTransaction", "Disclosure"}
    return [
        entity for entity in input_model.get("entities", [])
        if entity["name"] not in skip
    ]


def source_views_by_entity(input_model: Dict[str, Any]) -> Dict[str, str]:
    return {
        entity["name"]: entity.get("source_view", "")
        for entity in input_entities(input_model)
    }


def primary_keys_by_entity(input_model: Dict[str, Any]) -> Dict[str, str]:
    return {
        entity["name"]: entity.get("primary_key", "")
        for entity in input_entities(input_model)
    }


def source_view_for_entity(input_model: Dict[str, Any], entity_name: str) -> str:
    return source_views_by_entity(input_model)[entity_name]


def parse_csv_rows(path: Path, columns: List[str], max_rows: int) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)

        for row_idx, row in enumerate(reader, start=1):
            if max_rows > 0 and row_idx > max_rows:
                break

            doc: Dict[str, Any] = {}

            for idx, value in enumerate(row):
                if idx < len(columns):
                    col = columns[idx]
                else:
                    col = f"COL_{idx + 1}"

                doc[col] = value if value != "" else None

            doc["_source_file_row_number"] = row_idx
            yield doc


def apply_compatibility_aliases(entity_name: str, doc: Dict[str, Any]) -> None:
    # The generated DBSR input model uses Security.ISTRADEDON as the join
    # toward ListedSecurity. The official CSV stores the matching identifier
    # in SECURITYID/LISTEDSECURITYID, so we expose a compatibility alias.
    if entity_name == "Security" and "SECURITYID" in doc:
        doc.setdefault("ISTRADEDON", doc["SECURITYID"])

    # Keep report-to-statement compatibility conservative. The official
    # benchmark validation will later confirm whether this edge needs a
    # stronger mapping.
    if entity_name == "StatementElement" and "ELEMENTOFFINANCIALSTATEMENTID" in doc:
        doc.setdefault("ELEMENTSOFFINANCIALREPORTID", doc["ELEMENTOFFINANCIALSTATEMENTID"])


def collect_index_fields(materialization_plan: Dict[str, Any]) -> Dict[str, set]:
    index_fields: Dict[str, set] = {}

    for collection_plan in materialization_plan.get("collection_plans", []):
        for source in collection_plan.get("source_collections", []):
            source_view = source["source_view"]
            index_fields.setdefault(source_view, set()).add(source["primary_key"])

        for step in collection_plan.get("embedding_steps", []):
            parent_entity = step["parent_entity"]
            child_entity = step["child_entity"]

            parent_source_view = ""
            child_source_view = ""

            for source in collection_plan.get("source_collections", []):
                if source["entity"] == parent_entity:
                    parent_source_view = source["source_view"]
                if source["entity"] == child_entity:
                    child_source_view = source["source_view"]

            if parent_source_view:
                index_fields.setdefault(parent_source_view, set()).add(step["parent_join_column"])
            if child_source_view:
                index_fields.setdefault(child_source_view, set()).add(step["child_join_column"])

    return index_fields


def load_entity(
    db,
    data_dir: Path,
    entity: Dict[str, Any],
    source_view: str,
    max_rows: int,
    batch_size: int,
    execute: bool,
) -> Dict[str, Any]:
    entity_name = entity["name"]
    file_name = ENTITY_FILE_MAP[entity_name]
    columns = ENTITY_COLUMNS[entity_name]
    path = data_dir / file_name

    if not path.exists():
        return {
            "entity": entity_name,
            "source_view": source_view,
            "file": file_name,
            "status": "missing_file",
            "rows_loaded": 0,
        }

    rows_loaded = 0
    batch: List[Dict[str, Any]] = []

    if execute:
        db[source_view].drop()

    for doc in parse_csv_rows(path=path, columns=columns, max_rows=max_rows):
        apply_compatibility_aliases(entity_name, doc)
        rows_loaded += 1

        if execute:
            batch.append(doc)

            if len(batch) >= batch_size:
                db[source_view].insert_many(batch)
                batch.clear()

    if execute and batch:
        db[source_view].insert_many(batch)

    return {
        "entity": entity_name,
        "source_view": source_view,
        "file": file_name,
        "status": "loaded" if execute else "dry_run_counted",
        "rows_loaded": rows_loaded,
        "columns_assigned": columns,
        "max_rows": max_rows,
    }


def create_indexes(db, index_fields: Dict[str, set], execute: bool) -> Dict[str, Any]:
    result: Dict[str, Any] = {}

    for collection_name, fields in sorted(index_fields.items()):
        result[collection_name] = []

        for field in sorted(fields):
            if not field:
                continue

            if execute:
                db[collection_name].create_index(field)

            result[collection_name].append(field)

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-model",
        default="DBSR_implementation/generated/fiben/dbsr_input_model.json",
    )
    parser.add_argument(
        "--materialization-plan",
        default="DBSR_implementation/generated/fiben/dbsr_materialization_plan_structural.json",
    )
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--scale-label", default="sf1")
    parser.add_argument("--mongo-host", default="127.0.0.1")
    parser.add_argument("--mongo-port", type=int, default=27018)
    parser.add_argument("--mongo-username", default=None)
    parser.add_argument("--mongo-password", default=None)
    parser.add_argument("--mongo-auth-source", default="admin")
    parser.add_argument("--mongo-db", default="dbsr_fiben_sf1_source_smoke")
    parser.add_argument("--batch-size", type=int, default=10000)
    parser.add_argument(
        "--max-rows",
        type=int,
        default=1000,
        help="0 means full file; positive values limit each source file.",
    )
    parser.add_argument("--drop-db", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--out-dir", default="DBSR_implementation/generated/fiben")
    args = parser.parse_args()

    input_model = read_json(Path(args.input_model))
    materialization_plan = read_json(Path(args.materialization_plan))
    data_dir = Path(args.data_dir)

    db = None
    mongo_access = False

    if args.execute:
        client = connect_mongo(args)
        if args.drop_db:
            client.drop_database(args.mongo_db)
        db = client[args.mongo_db]
        mongo_access = True

    source_views = source_views_by_entity(input_model)
    entities = input_entities(input_model)

    load_results = []

    for entity in entities:
        entity_name = entity["name"]
        if entity_name not in ENTITY_FILE_MAP:
            continue

        load_results.append(
            load_entity(
                db=db,
                data_dir=data_dir,
                entity=entity,
                source_view=source_views[entity_name],
                max_rows=args.max_rows,
                batch_size=args.batch_size,
                execute=args.execute,
            )
        )

    index_fields = collect_index_fields(materialization_plan)
    indexes = create_indexes(db, index_fields=index_fields, execute=args.execute)

    failed = [row for row in load_results if row["status"] == "missing_file"]

    manifest = {
        "baseline": "DBSR",
        "dataset": "FIBEN",
        "scale_label": args.scale_label,
        "source_type": "official_fiben_csv_source",
        "status": "executed" if args.execute and not failed else "dry_run" if not args.execute else "failed",
        "execute": args.execute,
        "mongo_access": mongo_access,
        "mongo_database": args.mongo_db if args.execute else "",
        "official_benchmark": False,
        "data_dir_recorded": False,
        "max_rows_per_file": args.max_rows,
        "entities_attempted": len(load_results),
        "entities_loaded": sum(1 for row in load_results if row["status"] in {"loaded", "dry_run_counted"}),
        "missing_files": failed,
        "total_rows_loaded": sum(row["rows_loaded"] for row in load_results),
        "load_results": load_results,
        "indexes": {
            collection: sorted(fields)
            for collection, fields in indexes.items()
        },
        "implementation_assumptions": [
            "The official FIBEN CSV files are headerless; column names are assigned by this loader.",
            "BuyTransaction and SellTransaction are treated as Transaction-level subtypes/filters.",
            "Disclosure is not required by the current DBSR Q1-Q9 manifest.",
            "This source load is not a p95 benchmark by itself.",
            "The official DBSR-vs-SchemaLens p95 comparison must use the same benchmark server and real scale settings.",
        ],
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mode = "executed" if args.execute else "dry_run"
    output_path = out_dir / f"dbsr_official_fiben_source_load_manifest_{args.scale_label}_{mode}.json"
    write_json(output_path, manifest)

    print(f"Official FIBEN source load status: {manifest['status']}")
    print(f"Mongo access: {manifest['mongo_access']}")
    print(f"Mongo database: {manifest['mongo_database'] or '<not used>'}")
    print(f"Entities attempted: {manifest['entities_attempted']}")
    print(f"Entities loaded: {manifest['entities_loaded']}")
    print(f"Missing files: {len(manifest['missing_files'])}")
    print(f"Total rows loaded/counted: {manifest['total_rows_loaded']}")
    print(f"Max rows per file: {manifest['max_rows_per_file']}")
    print(f"Wrote {output_path}")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
