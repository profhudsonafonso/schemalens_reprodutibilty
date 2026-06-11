#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


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


def find_join_value(document: Dict[str, Any], column: str) -> Any:
    if column in document:
        return document[column]

    column_lower = column.lower()
    for key, value in document.items():
        if key.lower() == column_lower:
            return value

    return None


def source_view_for_entity(collection_plan: Dict[str, Any], entity: str) -> str:
    for item in collection_plan.get("source_collections", []):
        if item.get("entity") == entity:
            return item.get("source_view", "")
    return ""


def batched_cursor(cursor: Iterable[Dict[str, Any]], batch_size: int):
    batch: List[Dict[str, Any]] = []
    for doc in cursor:
        batch.append(doc)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def estimate_root_count(db, source_view: str, root_limit: Optional[int]) -> Optional[int]:
    try:
        count = int(db[source_view].estimated_document_count())
        if root_limit is not None and root_limit > 0:
            return min(count, root_limit)
        return count
    except Exception:
        return root_limit if root_limit and root_limit > 0 else None


def lookup_children(
    db,
    source_view: str,
    child_join_column: str,
    parent_join_value: Any,
    limit: Optional[int],
) -> List[Dict[str, Any]]:
    if parent_join_value is None:
        return []

    cursor = db[source_view].find({child_join_column: parent_join_value})

    if limit is not None and limit > 0:
        cursor = cursor.limit(limit)

    return list(cursor)


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


def format_eta(seconds: Optional[float]) -> str:
    if seconds is None or math.isinf(seconds) or seconds < 0:
        return "unknown"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def materialize_collection_streaming(
    db,
    collection_plan: Dict[str, Any],
    root_limit: Optional[int],
    child_limit: Optional[int],
    drop_target: bool,
    batch_size: int,
    progress_interval: int,
    skip_existing: bool,
) -> Dict[str, Any]:
    target = collection_plan["target_collection"]
    root_source_view = collection_plan["root_source_view"]
    embedding_steps = collection_plan.get("embedding_steps", [])

    expected_roots = estimate_root_count(db, root_source_view, root_limit)

    if skip_existing and collection_exists(db, target):
        existing_count = int(db[target].estimated_document_count())
        if expected_roots is not None and existing_count >= expected_roots:
            return {
                "target_collection": target,
                "root_source_view": root_source_view,
                "root_documents_loaded": 0,
                "embedding_steps": len(embedding_steps),
                "inserted_documents": existing_count,
                "elapsed_seconds": 0.0,
                "status": "skipped_existing_complete",
            }

    if drop_target and collection_exists(db, target):
        print(f"[{target}] dropping existing target collection", flush=True)
        db[target].drop()
    elif collection_exists(db, target) and db[target].estimated_document_count() > 0:
        raise RuntimeError(
            f"Target collection {target} already exists and is non-empty. "
            f"Use --drop-target or --skip-existing."
        )

    started = time.time()
    inserted = 0
    last_report = 0

    print(
        f"[{target}] start root={root_source_view} "
        f"expected={expected_roots} batch_size={batch_size} "
        f"embedding_steps={len(embedding_steps)}",
        flush=True,
    )

    cursor = db[root_source_view].find({}, no_cursor_timeout=True).batch_size(batch_size)

    if root_limit is not None and root_limit > 0:
        cursor = cursor.limit(root_limit)

    try:
        for batch in batched_cursor(cursor, batch_size=batch_size):
            embed_children_recursive(
                db=db,
                parent_docs=batch,
                collection_plan=collection_plan,
                step_index=0,
                child_limit=child_limit,
            )

            if batch:
                db[target].insert_many(batch, ordered=False)
                inserted += len(batch)

            should_report = (
                inserted - last_report >= progress_interval
                or (expected_roots is not None and inserted >= expected_roots)
            )

            if should_report:
                elapsed = time.time() - started
                rate = inserted / elapsed if elapsed > 0 else 0
                if expected_roots and rate > 0:
                    remaining = max(expected_roots - inserted, 0)
                    eta = remaining / rate
                    pct = inserted / expected_roots * 100
                else:
                    eta = None
                    pct = 0.0

                print(
                    f"[{target}] inserted={inserted:,}"
                    f"/{expected_roots if expected_roots is not None else '?'} "
                    f"pct={pct:.2f}% rate={rate:.1f} docs/s "
                    f"elapsed={format_eta(elapsed)} eta={format_eta(eta)}",
                    flush=True,
                )
                last_report = inserted

    finally:
        try:
            cursor.close()
        except Exception:
            pass

    elapsed = time.time() - started

    print(
        f"[{target}] completed inserted={inserted:,} "
        f"elapsed={format_eta(elapsed)}",
        flush=True,
    )

    return {
        "target_collection": target,
        "root_source_view": root_source_view,
        "root_documents_loaded": inserted,
        "embedding_steps": len(embedding_steps),
        "inserted_documents": inserted,
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


def parse_target_collections(value: Optional[str]) -> Optional[set[str]]:
    if not value:
        return None
    return {item.strip() for item in value.split(",") if item.strip()}


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
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--progress-interval", type=int, default=100000)
    parser.add_argument("--target-collection", default=None)
    parser.add_argument("--drop-target", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--out-dir", default="DBSR_implementation/generated/fiben")
    args = parser.parse_args()

    plan = read_json(Path(args.materialization_plan))
    collection_plans = plan.get("collection_plans", [])

    selected_targets = parse_target_collections(args.target_collection)
    if selected_targets is not None:
        collection_plans = [
            item for item in collection_plans
            if item.get("target_collection") in selected_targets
        ]

        missing_targets = selected_targets - {
            item.get("target_collection") for item in collection_plans
        }
        if missing_targets:
            raise SystemExit(f"Unknown target collections: {sorted(missing_targets)}")

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
            try:
                execution_rows.append(
                    materialize_collection_streaming(
                        db=db,
                        collection_plan=collection_plan,
                        root_limit=args.root_limit,
                        child_limit=args.child_limit,
                        drop_target=args.drop_target,
                        batch_size=args.batch_size,
                        progress_interval=args.progress_interval,
                        skip_existing=args.skip_existing,
                    )
                )
            except Exception as exc:
                target = collection_plan.get("target_collection")
                print(f"[{target}] failed: {exc}", file=sys.stderr, flush=True)
                execution_rows.append(
                    {
                        "target_collection": target,
                        "root_source_view": collection_plan.get("root_source_view"),
                        "root_documents_loaded": 0,
                        "embedding_steps": len(collection_plan.get("embedding_steps", [])),
                        "inserted_documents": 0,
                        "elapsed_seconds": 0.0,
                        "status": "failed",
                        "error": str(exc),
                    }
                )

        target_collections = [item["target_collection"] for item in collection_plans]
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
        "loader_type": "dbsr_materialization_loader_streaming",
        "status": status,
        "execute": args.execute,
        "mongo_access": mongo_access,
        "benchmark_execution": False,
        "root_limit": args.root_limit,
        "child_limit": args.child_limit,
        "batch_size": args.batch_size,
        "progress_interval": args.progress_interval,
        "target_collection_filter": args.target_collection,
        "drop_target": args.drop_target,
        "skip_existing": args.skip_existing,
        "target_collections": len(collection_plans),
        "completed_collections": sum(
            1 for row in execution_rows
            if row["status"] in {
                "completed",
                "dry_run_not_executed",
                "skipped_existing_complete",
            }
        ),
        "failed_collections": sum(
            1 for row in execution_rows
            if row["status"] not in {
                "completed",
                "dry_run_not_executed",
                "skipped_existing_complete",
            }
        ),
        "execution_results": execution_rows,
        "collection_statistics": stats_rows,
        "implementation_assumptions": [
            "This loader materializes DBSR target collections in streaming batches.",
            "Large roots are not loaded fully into Python memory before insertion.",
            "Progress logs report inserted root documents, approximate rate, and ETA.",
            "Use --target-collection to materialize one or more collections independently.",
            "Use --skip-existing to resume already completed target collections.",
            "Official DBSR p95 benchmark must run later on the same server used for SchemaLens.",
            "Statistics are captured after materialization and before any target database is dropped.",
        ],
    }

    suffix = args.scale_label
    mode = "executed" if args.execute else "dry_run"
    output_path = out_dir / f"dbsr_loader_execution_manifest_{suffix}_{mode}.json"

    write_json(output_path, manifest)

    print(f"Loader status: {manifest['status']}", flush=True)
    print(f"Mongo access: {manifest['mongo_access']}", flush=True)
    print(f"Benchmark execution: {manifest['benchmark_execution']}", flush=True)
    print(f"Target collections: {manifest['target_collections']}", flush=True)
    print(f"Completed collections: {manifest['completed_collections']}", flush=True)
    print(f"Failed collections: {manifest['failed_collections']}", flush=True)
    print(f"Wrote {output_path}", flush=True)

    if manifest["failed_collections"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
