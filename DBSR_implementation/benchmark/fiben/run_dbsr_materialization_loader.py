#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


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


def collection_exists(db, name: str) -> bool:
    return name in db.list_collection_names()


def fetch_documents(
    db,
    source_view: str,
    limit: Optional[int],
) -> List[Dict[str, Any]]:
    cursor = db[source_view].find({})

    if limit is not None and limit > 0:
        cursor = cursor.limit(limit)

    return list(cursor)


def find_join_value(document: Dict[str, Any], column: str) -> Any:
    if column in document:
        return document[column]

    # Try case-insensitive fallback.
    column_lower = column.lower()
    for key, value in document.items():
        if key.lower() == column_lower:
            return value

    return None


def lookup_children(
    db,
    source_view: str,
    child_join_column: str,
    parent_join_value: Any,
    limit: Optional[int],
) -> List[Dict[str, Any]]:
    if parent_join_value is None:
        return []

    query = {child_join_column: parent_join_value}
    cursor = db[source_view].find(query)

    if limit is not None and limit > 0:
        cursor = cursor.limit(limit)

    return list(cursor)


def source_view_for_entity(collection_plan: Dict[str, Any], entity: str) -> str:
    for item in collection_plan.get("source_collections", []):
        if item.get("entity") == entity:
            return item.get("source_view", "")

    return ""


def embed_children_recursive(
    db,
    parent_docs: List[Dict[str, Any]],
    collection_plan: Dict[str, Any],
    step_index: int,
    child_limit: Optional[int],
) -> None:
    embedding_steps = collection_plan.get("embedding_steps", [])

    if step_index >= len(embedding_steps):
        return

    step = embedding_steps[step_index]

    child_entity = step["child_entity"]
    parent_join_column = step["parent_join_column"]
    child_join_column = step["child_join_column"]
    child_source_view = source_view_for_entity(collection_plan, child_entity)

    embedded_field = child_entity[0].lower() + child_entity[1:]

    for parent_doc in parent_docs:
        parent_join_value = find_join_value(parent_doc, parent_join_column)
        children = lookup_children(
            db=db,
            source_view=child_source_view,
            child_join_column=child_join_column,
            parent_join_value=parent_join_value,
            limit=child_limit,
        )

        parent_doc[embedded_field] = children

        if children:
            embed_children_recursive(
                db=db,
                parent_docs=children,
                collection_plan=collection_plan,
                step_index=step_index + 1,
                child_limit=child_limit,
            )


def materialize_collection(
    db,
    collection_plan: Dict[str, Any],
    root_limit: Optional[int],
    child_limit: Optional[int],
    drop_target: bool,
) -> Dict[str, Any]:
    target = collection_plan["target_collection"]
    root_source_view = collection_plan["root_source_view"]

    started = time.time()

    root_docs = fetch_documents(
        db=db,
        source_view=root_source_view,
        limit=root_limit,
    )

    embed_children_recursive(
        db=db,
        parent_docs=root_docs,
        collection_plan=collection_plan,
        step_index=0,
        child_limit=child_limit,
    )

    if drop_target and collection_exists(db, target):
        db[target].drop()

    if root_docs:
        db[target].insert_many(root_docs)

    elapsed = time.time() - started

    return {
        "target_collection": target,
        "root_source_view": root_source_view,
        "root_documents_loaded": len(root_docs),
        "embedding_steps": len(collection_plan.get("embedding_steps", [])),
        "inserted_documents": len(root_docs),
        "elapsed_seconds": round(elapsed, 6),
        "status": "completed",
    }


def capture_collection_stats(db, target_collections: List[str]) -> List[Dict[str, Any]]:
    stats_rows: List[Dict[str, Any]] = []

    for name in target_collections:
        row: Dict[str, Any] = {
            "collection": name,
            "exists": collection_exists(db, name),
            "count": 0,
            "avg_object_size_bytes": None,
            "size_bytes": None,
            "storage_size_bytes": None,
            "total_index_size_bytes": None,
        }

        if not row["exists"]:
            stats_rows.append(row)
            continue

        try:
            stats = db.command("collStats", name)
            row["count"] = int(stats.get("count", 0))
            row["avg_object_size_bytes"] = stats.get("avgObjSize")
            row["size_bytes"] = stats.get("size")
            row["storage_size_bytes"] = stats.get("storageSize")
            row["total_index_size_bytes"] = stats.get("totalIndexSize")
        except Exception as exc:
            row["stats_error"] = str(exc)
            row["count"] = int(db[name].estimated_document_count())

        stats_rows.append(row)

    return stats_rows


def dry_run_collection(collection_plan: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "target_collection": collection_plan["target_collection"],
        "root_source_view": collection_plan["root_source_view"],
        "root_documents_loaded": 0,
        "embedding_steps": len(collection_plan.get("embedding_steps", [])),
        "inserted_documents": 0,
        "elapsed_seconds": 0.0,
        "status": "dry_run_not_executed",
    }


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
    parser.add_argument("--mongo-db", default=None)
    parser.add_argument("--root-limit", type=int, default=10)
    parser.add_argument("--child-limit", type=int, default=20)
    parser.add_argument("--drop-target", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--out-dir",
        default="DBSR_implementation/generated/fiben",
    )
    args = parser.parse_args()

    plan = read_json(Path(args.materialization_plan))
    collection_plans = plan.get("collection_plans", [])

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    execution_rows: List[Dict[str, Any]] = []
    stats_rows: List[Dict[str, Any]] = []

    if args.execute:
        if not args.mongo_db:
            raise SystemExit("--mongo-db is required when --execute is used")

        client = connect_mongo(args)
        db = client[args.mongo_db]

        for collection_plan in collection_plans:
            execution_rows.append(
                materialize_collection(
                    db=db,
                    collection_plan=collection_plan,
                    root_limit=args.root_limit,
                    child_limit=args.child_limit,
                    drop_target=args.drop_target,
                )
            )

        target_collections = [
            item["target_collection"]
            for item in collection_plans
        ]
        stats_rows = capture_collection_stats(db, target_collections)

        status = "executed"
        mongo_access = True
    else:
        execution_rows = [
            dry_run_collection(collection_plan)
            for collection_plan in collection_plans
        ]
        status = "dry_run"
        mongo_access = False

    manifest = {
        "baseline": "DBSR",
        "dataset": "FIBEN",
        "scale_label": args.scale_label,
        "loader_type": "dbsr_materialization_loader",
        "status": status,
        "execute": args.execute,
        "mongo_access": mongo_access,
        "benchmark_execution": False,
        "root_limit": args.root_limit,
        "child_limit": args.child_limit,
        "drop_target": args.drop_target,
        "target_collections": len(collection_plans),
        "completed_collections": sum(
            1 for row in execution_rows
            if row["status"] in {"completed", "dry_run_not_executed"}
        ),
        "failed_collections": sum(
            1 for row in execution_rows
            if row["status"] not in {"completed", "dry_run_not_executed"}
        ),
        "execution_results": execution_rows,
        "collection_statistics": stats_rows,
        "implementation_assumptions": [
            "The default mode is dry-run and does not connect to MongoDB.",
            "Real materialization requires --execute and --mongo-db.",
            "This loader is intended first for smoke-scale validation.",
            "Official DBSR p95 benchmark must run later on the same server used for SchemaLens.",
            "Statistics are captured after materialization and before any target database is dropped.",
        ],
    }

    suffix = args.scale_label
    mode = "executed" if args.execute else "dry_run"
    output_path = out_dir / f"dbsr_loader_execution_manifest_{suffix}_{mode}.json"

    write_json(output_path, manifest)

    print(f"Loader status: {manifest['status']}")
    print(f"Mongo access: {manifest['mongo_access']}")
    print(f"Benchmark execution: {manifest['benchmark_execution']}")
    print(f"Target collections: {manifest['target_collections']}")
    print(f"Completed collections: {manifest['completed_collections']}")
    print(f"Failed collections: {manifest['failed_collections']}")
    print(f"Wrote {output_path}")

    if manifest["failed_collections"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
