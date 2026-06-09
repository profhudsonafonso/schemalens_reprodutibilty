#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def connect_mongo(args: argparse.Namespace):
    try:
        from pymongo import MongoClient
    except ImportError as exc:
        raise SystemExit(
            "pymongo is required for execution mode. Install it with: pip install pymongo"
        ) from exc

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


def source_collection_for_entity(collection_plan: Dict[str, Any], entity: str) -> Dict[str, Any]:
    for item in collection_plan.get("source_collections", []):
        if item.get("entity") == entity:
            return item

    raise KeyError(f"Entity {entity} not found in source_collections for {collection_plan.get('target_collection')}")


def ensure_doc(
    docs_by_key: Dict[Tuple[str, str, str], Dict[str, Any]],
    source_view: str,
    entity: str,
    primary_key: str,
    target_collection: str,
) -> Dict[str, Any]:
    key = (source_view, entity, target_collection)

    if key not in docs_by_key:
        synthetic_id = f"{target_collection}__{entity}__1"
        docs_by_key[key] = {
            primary_key: synthetic_id,
            "_synthetic_entity": entity,
            "_synthetic_target_collection": target_collection,
            "_synthetic_source_view": source_view,
            "NAME": synthetic_id,
        }

    return docs_by_key[key]


def build_synthetic_docs(materialization_plan: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    docs_by_key: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    for collection_plan in materialization_plan.get("collection_plans", []):
        target_collection = collection_plan["target_collection"]

        for source in collection_plan.get("source_collections", []):
            ensure_doc(
                docs_by_key=docs_by_key,
                source_view=source["source_view"],
                entity=source["entity"],
                primary_key=source["primary_key"],
                target_collection=target_collection,
            )

        for step in collection_plan.get("embedding_steps", []):
            parent_source = source_collection_for_entity(collection_plan, step["parent_entity"])
            child_source = source_collection_for_entity(collection_plan, step["child_entity"])

            parent_doc = ensure_doc(
                docs_by_key=docs_by_key,
                source_view=parent_source["source_view"],
                entity=parent_source["entity"],
                primary_key=parent_source["primary_key"],
                target_collection=target_collection,
            )

            child_doc = ensure_doc(
                docs_by_key=docs_by_key,
                source_view=child_source["source_view"],
                entity=child_source["entity"],
                primary_key=child_source["primary_key"],
                target_collection=target_collection,
            )

            join_value = (
                f"{target_collection}__"
                f"{step['parent_entity']}__{step['child_entity']}__"
                f"{step['relationship_id']}__JOIN"
            )

            parent_doc[step["parent_join_column"]] = join_value
            child_doc[step["child_join_column"]] = join_value

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for (source_view, _, _), doc in docs_by_key.items():
        grouped[source_view].append(doc)

    return dict(grouped)


def load_synthetic_docs(db, docs_by_collection: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    loaded = {}

    for collection_name, docs in sorted(docs_by_collection.items()):
        db[collection_name].drop()

        if docs:
            db[collection_name].insert_many(docs)

        loaded[collection_name] = len(docs)

    return loaded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--materialization-plan",
        default="DBSR_implementation/generated/fiben/dbsr_materialization_plan_structural.json",
    )
    parser.add_argument("--scale-label", default="sf1")
    parser.add_argument("--mongo-host", default="127.0.0.1")
    parser.add_argument("--mongo-port", type=int, default=27018)
    parser.add_argument("--mongo-username", default=None)
    parser.add_argument("--mongo-password", default=None)
    parser.add_argument("--mongo-auth-source", default="admin")
    parser.add_argument("--mongo-db", default="dbsr_fiben_synthetic_smoke")
    parser.add_argument("--drop-db", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--out-dir",
        default="DBSR_implementation/generated/fiben",
    )
    args = parser.parse_args()

    materialization_plan = read_json(Path(args.materialization_plan))
    docs_by_collection = build_synthetic_docs(materialization_plan)

    loaded_counts: Dict[str, Any] = {}

    if args.execute:
        client = connect_mongo(args)

        if args.drop_db:
            client.drop_database(args.mongo_db)

        db = client[args.mongo_db]
        loaded_counts = load_synthetic_docs(db, docs_by_collection)
        status = "executed"
        mongo_access = True
    else:
        loaded_counts = {
            collection_name: len(docs)
            for collection_name, docs in docs_by_collection.items()
        }
        status = "dry_run"
        mongo_access = False

    manifest = {
        "baseline": "DBSR",
        "dataset": "FIBEN",
        "scale_label": args.scale_label,
        "source_type": "synthetic_minimal_fiben_source_db",
        "status": status,
        "mongo_access": mongo_access,
        "mongo_database": args.mongo_db if args.execute else "",
        "collections_prepared": len(docs_by_collection),
        "documents_prepared": sum(len(docs) for docs in docs_by_collection.values()),
        "loaded_counts": loaded_counts,
        "official_benchmark": False,
        "implementation_assumptions": [
            "This creates a synthetic minimal source database for executed loader smoke tests only.",
            "It is not a real FIBEN scale-factor database.",
            "It must not be used for p95 benchmark comparison.",
            "The official DBSR benchmark must later use the real FIBEN data on the same server used for SchemaLens.",
        ],
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"dbsr_synthetic_source_manifest_{args.scale_label}.json"

    write_json(output_path, manifest)

    print(f"Synthetic source status: {manifest['status']}")
    print(f"Mongo access: {manifest['mongo_access']}")
    print(f"Mongo database: {args.mongo_db if args.execute else '<not used>'}")
    print(f"Collections prepared: {manifest['collections_prepared']}")
    print(f"Documents prepared: {manifest['documents_prepared']}")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
