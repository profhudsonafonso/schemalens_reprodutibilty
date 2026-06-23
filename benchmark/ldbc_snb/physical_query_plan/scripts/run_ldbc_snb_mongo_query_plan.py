#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LDBC SNB MongoDB Query-Plan Runner for SchemaLens.

This script reuses the current LDBC SNB MongoDB benchmark runner for:
  - loading normalized LDBC SNB CSV files;
  - materializing MongoDB candidate configurations;
  - creating indexes;
  - selecting semantic query parameters.

Then it runs explain("executionStats")-style plan analysis and collStats
without running the full latency benchmark.

Expected location in the repository:
  benchmark/ldbc_snb/run_ldbc_snb_mongo_query_plan.py

Expected companion file in the same directory:
  benchmark/ldbc_snb/run_ldbc_snb_mongo_benchmark.py
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import pandas as pd
from pymongo import MongoClient
from pymongo.errors import AutoReconnect, NetworkTimeout, OperationFailure, ServerSelectionTimeoutError


# =========================================================
# Import the existing LDBC SNB benchmark runner
# =========================================================

try:
    ldbc_runner = importlib.import_module("run_ldbc_snb_mongo_benchmark")
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Could not import run_ldbc_snb_mongo_benchmark.py.\n"
        "Place this script in benchmark/ldbc_snb/ next to the current benchmark runner, "
        "or run it from a directory where that module is importable."
    ) from exc


# =========================================================
# Logging helpers
# =========================================================

GLOBAL_VERBOSE = False
GLOBAL_LOG_FILE_PATH: Optional[Path] = None


def utc_now_iso() -> str:
    return pd.Timestamp.now("UTC").isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_name(value: Any) -> str:
    return (
        str(value)
        .replace(".", "_")
        .replace("-", "_")
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .lower()
    )


def write_log(message: str, level: str = "INFO", force: bool = False) -> None:
    global GLOBAL_LOG_FILE_PATH

    line = f"[{utc_now_iso()}] [{level}] {message}"

    if force or GLOBAL_VERBOSE:
        print(line, flush=True)

    if GLOBAL_LOG_FILE_PATH is not None:
        with open(GLOBAL_LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def runner_log_compat(msg: str, verbose: Any = True, level: Optional[str] = None) -> None:
    """Compatible log function for the imported runner.

    The uploaded/current runner contains old calls such as log(msg, verbose)
    and newer calls such as log(msg, level="ERROR"). This wrapper accepts both.
    """
    if isinstance(verbose, str) and level is None:
        level = verbose
        should_print = True
    else:
        should_print = bool(verbose)
        level = level or "INFO"

    write_log(str(msg), level=str(level), force=should_print)


# Monkey-patch imported runner logging so data loading/materialization logs are persistent.
try:
    ldbc_runner.log = runner_log_compat
except Exception:
    pass


# =========================================================
# JSON / CSV helpers
# =========================================================


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def json_dumps(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return json.dumps(str(value), ensure_ascii=False)


def to_jsonable(value: Any) -> Any:
    """Convert BSON-ish / pandas-ish objects to JSON-serializable objects."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


# =========================================================
# Artifact loading and filtering
# =========================================================


def load_artifacts(artifacts_dir: Path, execution_plan: str) -> Tuple[pd.DataFrame, Dict[str, dict], dict]:
    plan_path = artifacts_dir / execution_plan
    specs_path = artifacts_dir / "mongodb_candidate_specs_by_candidate_id.json"
    manifest_path = artifacts_dir / "benchmark_manifest.json"

    if not plan_path.exists():
        raise FileNotFoundError(f"Execution plan not found: {plan_path}")
    if not specs_path.exists():
        raise FileNotFoundError(f"Candidate specs JSON not found: {specs_path}")

    plan_df = pd.read_csv(plan_path)
    specs_by_id = read_json(specs_path)
    manifest = read_json(manifest_path) if manifest_path.exists() else {}

    return plan_df, specs_by_id, manifest


def apply_filters(plan_df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    df = plan_df.copy()

    # Scale labels are usually per-bundle. Filter only if the plan contains matching rows.
    if args.scale_label and "scale_label" in df.columns:
        matching = df[df["scale_label"].astype(str) == str(args.scale_label)]
        if not matching.empty:
            df = matching

    if args.candidate_id:
        df = df[df["candidate_id"].astype(str).isin(args.candidate_id)]

    if args.query_name:
        df = df[df["query_name"].astype(str).isin(args.query_name)]

    if args.official_id:
        df = df[df["official_id"].astype(str).isin(args.official_id)]

    if args.benchmark_group:
        df = df[df["benchmark_group"].astype(str).isin(args.benchmark_group)]

    if args.g_class:
        df = df[df["g_class"].astype(str).isin(args.g_class)]

    if args.config_name:
        allowed = set(str(x) for x in args.config_name)
        mask = pd.Series(False, index=df.index)
        for col in ["candidate_id", "g_class", "mongodb_pattern", "document_strategy", "g_label"]:
            if col in df.columns:
                mask = mask | df[col].astype(str).isin(allowed)
        df = df[mask]

    if args.max_runs is not None:
        df = df.head(int(args.max_runs))

    return df.reset_index(drop=True)


# =========================================================
# MongoDB command helpers
# =========================================================


def connect_mongo(args: argparse.Namespace) -> MongoClient:
    kwargs: Dict[str, Any] = {}
    if args.mongo_username:
        kwargs["username"] = args.mongo_username
        kwargs["password"] = args.mongo_password
        kwargs["authSource"] = args.mongo_auth_source

    return MongoClient(
        host=args.mongo_host,
        port=int(args.mongo_port),
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=None,
        **kwargs,
    )


def build_db_name(prefix: str, candidate_id: str) -> str:
    return safe_name(f"{prefix}_{candidate_id}")


# =========================================================
# Plan extraction helpers
# =========================================================


def recursive_values_by_key(obj: Any, key: str) -> List[Any]:
    values: List[Any] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                values.append(v)
            values.extend(recursive_values_by_key(v, key))
    elif isinstance(obj, list):
        for item in obj:
            values.extend(recursive_values_by_key(item, key))
    return values


def first_value_by_key(obj: Any, key: str) -> Any:
    vals = recursive_values_by_key(obj, key)
    return vals[0] if vals else None


def sum_numeric_values_by_key(obj: Any, key: str) -> int:
    total = 0
    for value in recursive_values_by_key(obj, key):
        if isinstance(value, (int, float)):
            total += int(value)
    return total


def extract_stage_set_and_list(obj: Any) -> Tuple[Set[str], List[str]]:
    """Extract exact MongoDB stages.

    Important: this avoids substring checks, so OR is not detected inside SORT.
    """
    stage_list: List[str] = []

    def visit(x: Any) -> None:
        if isinstance(x, dict):
            # Query planner stages, e.g., IXSCAN, FETCH, COLLSCAN, OR, SORT.
            if isinstance(x.get("stage"), str):
                stage_list.append(x["stage"].upper())

            # Aggregation pipeline stages, e.g., $match, $group, $lookup.
            for k, v in x.items():
                if isinstance(k, str) and k.startswith("$"):
                    stage_list.append(k[1:].upper())
                visit(v)
        elif isinstance(x, list):
            for item in x:
                visit(item)

    visit(obj)
    return set(stage_list), stage_list


def extract_index_names(obj: Any) -> List[str]:
    names: List[str] = []
    for key in ["indexName", "indexNamePattern"]:
        for value in recursive_values_by_key(obj, key):
            if value is None:
                continue
            names.append(str(value))
    # Keep order but remove duplicates.
    seen: Set[str] = set()
    out: List[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def extract_rejected_plan_count(obj: Any) -> int:
    plans = first_value_by_key(obj, "rejectedPlans")
    if isinstance(plans, list):
        return len(plans)
    return 0


def extract_used_disk(obj: Any) -> Optional[bool]:
    vals = recursive_values_by_key(obj, "usedDisk")
    if not vals:
        return None
    return any(bool(v) for v in vals)


def extract_execution_metrics(explain_doc: dict) -> Dict[str, Any]:
    execution_stats = explain_doc.get("executionStats", {}) if isinstance(explain_doc, dict) else {}

    n_returned = execution_stats.get("nReturned")
    total_docs_examined = execution_stats.get("totalDocsExamined")
    total_keys_examined = execution_stats.get("totalKeysExamined")
    execution_time_ms = execution_stats.get("executionTimeMillis")

    if n_returned is None:
        vals = recursive_values_by_key(explain_doc, "nReturned")
        n_returned = vals[0] if vals else None

    if total_docs_examined is None:
        total_docs_examined = sum_numeric_values_by_key(explain_doc, "totalDocsExamined")

    if total_keys_examined is None:
        total_keys_examined = sum_numeric_values_by_key(explain_doc, "totalKeysExamined")

    if execution_time_ms is None:
        vals = recursive_values_by_key(explain_doc, "executionTimeMillis")
        execution_time_ms = vals[0] if vals else None

    stage_set, stage_list = extract_stage_set_and_list(explain_doc)
    index_names = extract_index_names(explain_doc)

    return {
        "executionTimeMillis": execution_time_ms,
        "nReturned": int(n_returned or 0),
        "totalDocsExamined": int(total_docs_examined or 0),
        "totalKeysExamined": int(total_keys_examined or 0),
        "docs_per_returned_total": safe_ratio(total_docs_examined or 0, n_returned or 0),
        "keys_per_returned_total": safe_ratio(total_keys_examined or 0, n_returned or 0),
        "stages": stage_list,
        "stage_set": stage_set,
        "index_names": index_names,
        "queryHash": first_value_by_key(explain_doc, "queryHash"),
        "planCacheKey": first_value_by_key(explain_doc, "planCacheKey"),
        "rejected_plans_count": extract_rejected_plan_count(explain_doc),
        "usedDisk": extract_used_disk(explain_doc),
    }


def safe_ratio(num: Any, den: Any) -> Optional[float]:
    try:
        n = float(num)
        d = float(den)
        if d == 0:
            return None
        return n / d
    except Exception:
        return None


STAGES_OF_INTEREST = [
    "IXSCAN", "COLLSCAN", "FETCH", "SORT", "AND_SORTED", "OR", "PROJECTION",
    "LOOKUP", "GROUP", "UNWIND", "LIMIT", "UPDATE", "MATCH", "PROJECT",
]


# =========================================================
# Physical collection stats
# =========================================================


def get_coll_stats(db, collection_name: str) -> Dict[str, Any]:
    try:
        stats = db.command("collStats", collection_name)
    except Exception as exc:
        return {
            "collection_name": collection_name,
            "collection_stats_status": "failed",
            "collection_stats_error": f"{type(exc).__name__}: {exc}",
        }

    index_sizes = stats.get("indexSizes") or {}
    count = stats.get("count")
    size = stats.get("size")
    avg_obj_size = stats.get("avgObjSize")
    storage_size = stats.get("storageSize")
    total_index_size = stats.get("totalIndexSize")
    total_size = None
    if isinstance(storage_size, (int, float)) and isinstance(total_index_size, (int, float)):
        total_size = int(storage_size + total_index_size)

    return {
        "collection_name": collection_name,
        "collection_stats_status": "completed",
        "collection_count": count,
        "collection_size_bytes": size,
        "collection_avg_obj_size_bytes": avg_obj_size,
        "collection_storage_size_bytes": storage_size,
        "collection_total_index_size_bytes": total_index_size,
        "collection_total_size_bytes": total_size,
        "collection_free_storage_size_bytes": stats.get("freeStorageSize"),
        "collection_nindexes": stats.get("nindexes"),
        "collection_index_sizes_json": json_dumps(index_sizes),
        "collection_stats_error": None,
    }


def add_derived_physical_metrics(row: Dict[str, Any]) -> Dict[str, Any]:
    docs_examined = row.get("totalDocsExamined") or 0
    returned = row.get("nReturned") or 0
    avg_obj_size = row.get("collection_avg_obj_size_bytes") or 0
    collection_count = row.get("collection_count") or 0
    collection_size = row.get("collection_size_bytes") or 0
    total_index_size = row.get("collection_total_index_size_bytes") or 0

    estimated_docs_examined_bytes = None
    estimated_returned_bytes = None

    if isinstance(avg_obj_size, (int, float)):
        estimated_docs_examined_bytes = float(docs_examined) * float(avg_obj_size)
        estimated_returned_bytes = float(returned) * float(avg_obj_size)

    row["estimated_docs_examined_bytes"] = estimated_docs_examined_bytes
    row["estimated_returned_bytes"] = estimated_returned_bytes
    row["estimated_examined_bytes_per_returned"] = safe_ratio(
        estimated_docs_examined_bytes or 0,
        returned,
    )
    row["docs_examined_collection_ratio"] = safe_ratio(docs_examined, collection_count)
    row["index_to_data_size_ratio"] = safe_ratio(total_index_size, collection_size)
    return row


# =========================================================
# Explain command builders
# =========================================================


def find_op(
    component_name: str,
    collection: str,
    filter_doc: Optional[dict] = None,
    projection: Optional[dict] = None,
    sort: Optional[dict] = None,
    limit: Optional[int] = None,
    note: Optional[str] = None,
    component_role: Optional[str] = None,
    candidate_physical_path: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "kind": "find",
        "component_name": component_name,
        "collection": collection,
        "filter": filter_doc or {},
        "projection": projection,
        "sort": sort,
        "limit": limit,
        "note": note,
        "component_role": component_role,
        "candidate_physical_path": candidate_physical_path,
    }


def aggregate_op(
    component_name: str,
    collection: str,
    pipeline: List[dict],
    note: Optional[str] = None,
    component_role: Optional[str] = None,
    candidate_physical_path: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "kind": "aggregate",
        "component_name": component_name,
        "collection": collection,
        "pipeline": pipeline,
        "note": note,
        "component_role": component_role,
        "candidate_physical_path": candidate_physical_path,
    }


def not_explainable_op(
    component_name: str,
    collection: str,
    reason: str,
    documents_written: int = 0,
) -> Dict[str, Any]:
    return {
        "kind": "not_explainable",
        "component_name": component_name,
        "collection": collection,
        "not_explainable_reason": reason,
        "documents_written": documents_written,
    }


def run_explain(db, op: Dict[str, Any], verbosity: str) -> dict:
    kind = op["kind"]
    collection = op["collection"]

    if kind == "find":
        inner: Dict[str, Any] = {
            "find": collection,
            "filter": op.get("filter") or {},
        }
        if op.get("projection") is not None:
            inner["projection"] = op["projection"]
        if op.get("sort") is not None:
            inner["sort"] = op["sort"]
        if op.get("limit") is not None:
            inner["limit"] = int(op["limit"])
        return db.command("explain", inner, verbosity=verbosity)

    if kind == "aggregate":
        inner = {
            "aggregate": collection,
            "pipeline": op.get("pipeline") or [],
            "cursor": {},
            "allowDiskUse": True,
        }
        return db.command("explain", inner, verbosity=verbosity)

    raise ValueError(f"Operation kind is not explainable: {kind}")


# =========================================================
# Parameter selection
# =========================================================


def normalize_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value)
    if s == "" or s.lower() == "nan":
        return None
    return s


def complete_params(db, official_id: str, params: dict, repetition: int) -> dict:
    out = dict(params or {})
    out.setdefault("person_id", ldbc_runner.first_value(db, "persons", "person_id"))
    out.setdefault("post_id", ldbc_runner.first_value(db, "posts", "post_id"))
    out.setdefault("comment_id", ldbc_runner.first_value(db, "comments", "comment_id"))
    out.setdefault("forum_id", ldbc_runner.first_value(db, "forums", "forum_id"))
    try:
        out.setdefault("tag_id", ldbc_runner.first_value(db, "tags", "tag_id"))
    except Exception:
        out.setdefault("tag_id", None)
    out.setdefault("place_id", ldbc_runner.first_value(db, "places", "place_id"))
    out.setdefault("new_id", f"qp_{official_id}_{int(time.time() * 1000)}_{repetition}")
    return out


def build_params_for_sample(db, official_id: str, repetition: int, sample_size: int) -> dict:
    # Clear only if not already available for this db; runner caches by db.name.
    pool = ldbc_runner.build_ldbc_query_parameter_pool(db, sample_size=sample_size)
    params = ldbc_runner.pick_ldbc_param_for_run(pool, official_id, repetition)
    return complete_params(db, official_id, params, repetition)


# =========================================================
# Small data lookups used only to build follow-up explain components
# =========================================================


def get_friends_for_components(db, person_id: Optional[str], max_depth: int = 1, limit: int = 200) -> List[str]:
    try:
        return ldbc_runner.get_friends(db, person_id, max_depth=max_depth, limit=limit) if person_id else []
    except Exception:
        return []


def ids_from_cursor(cursor, field: str, limit: int = 20) -> List[str]:
    out: List[str] = []
    try:
        for doc in cursor.limit(limit):
            val = normalize_id(doc.get(field))
            if val is not None and val not in out:
                out.append(val)
    except Exception:
        pass
    return out


def first_field(db, collection: str, filter_doc: dict, field: str) -> Optional[str]:
    try:
        doc = db[collection].find_one(filter_doc, {field: 1})
        if doc:
            return normalize_id(doc.get(field))
    except Exception:
        pass
    return None



# =========================================================
# Candidate-aware IC7 physical structures
# =========================================================

IC7_G3_SUMMARY_COLLECTION = "ic7_g3_person_recent_liker_summary"
IC7_G4_EDGE_COLLECTION = "ic7_g4_explicit_like_edges"
IC7_G6_REVERSE_COLLECTION = "ic7_g6_owner_liker_reverse_index"


def _safe_drop_collection(db, name: str) -> None:
    try:
        db[name].drop()
    except Exception:
        pass


def _insert_batches(collection, docs: List[dict], batch_size: int = 100000) -> int:
    n = 0
    batch: List[dict] = []
    for doc in docs:
        batch.append(doc)
        if len(batch) >= batch_size:
            collection.insert_many(batch, ordered=False)
            n += len(batch)
            batch = []
    if batch:
        collection.insert_many(batch, ordered=False)
        n += len(batch)
    return n


def _person_name_map(db, person_ids: List[str]) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    if not person_ids:
        return out
    for pdoc in db.persons.find({"person_id": {"$in": person_ids}}, {"person_id": 1, "first_name": 1, "last_name": 1}):
        pid = normalize_id(pdoc.get("person_id"))
        if pid:
            out[pid] = {
                "person_id": pid,
                "first_name": pdoc.get("first_name"),
                "last_name": pdoc.get("last_name"),
            }
    return out




def chunked_values(values, chunk_size: int = 5000):
    """Yield bounded chunks to avoid MongoDB's 16 MB BSON command limit."""
    values = list(values)
    for i in range(0, len(values), chunk_size):
        chunk = values[i:i + chunk_size]
        if chunk:
            yield chunk


def build_ic7_edge_docs(db, limit_owner_ids: Optional[List[str]] = None) -> List[dict]:
    """Create physical explicit-like-edge documents for IC7.

    This keeps the full materialization semantics. The only optimization is that
    large $in predicates are sent to MongoDB in bounded chunks, avoiding the
    16 MB BSON command limit at SF1/SF3.
    """
    docs: List[dict] = []
    owner_filter = {"creator_person_id": {"$in": limit_owner_ids}} if limit_owner_ids else {}

    post_owner: Dict[str, str] = {}
    for post in db.posts.find(owner_filter, {"post_id": 1, "creator_person_id": 1}).batch_size(50000):
        post_id = normalize_id(post.get("post_id"))
        owner = normalize_id(post.get("creator_person_id"))
        if post_id and owner:
            post_owner[post_id] = owner

    if post_owner:
        for post_id_chunk in chunked_values(post_owner.keys(), chunk_size=5000):
            cursor = db.person_likes_post.find(
                {"post_id": {"$in": post_id_chunk}},
                {"person_id": 1, "post_id": 1, "creation_date": 1},
            ).batch_size(50000)

            for like in cursor:
                post_id = normalize_id(like.get("post_id"))
                liker = normalize_id(like.get("person_id"))
                owner = post_owner.get(post_id)
                if owner and liker:
                    docs.append({
                        "owner_person_id": owner,
                        "liker_person_id": liker,
                        "message_id": post_id,
                        "message_type": "post",
                        "creation_date": like.get("creation_date"),
                    })

    comment_owner: Dict[str, str] = {}
    for comment in db.comments.find(owner_filter, {"comment_id": 1, "creator_person_id": 1}).batch_size(50000):
        comment_id = normalize_id(comment.get("comment_id"))
        owner = normalize_id(comment.get("creator_person_id"))
        if comment_id and owner:
            comment_owner[comment_id] = owner

    if comment_owner:
        for comment_id_chunk in chunked_values(comment_owner.keys(), chunk_size=5000):
            cursor = db.person_likes_comment.find(
                {"comment_id": {"$in": comment_id_chunk}},
                {"person_id": 1, "comment_id": 1, "creation_date": 1},
            ).batch_size(50000)

            for like in cursor:
                comment_id = normalize_id(like.get("comment_id"))
                liker = normalize_id(like.get("person_id"))
                owner = comment_owner.get(comment_id)
                if owner and liker:
                    docs.append({
                        "owner_person_id": owner,
                        "liker_person_id": liker,
                        "message_id": comment_id,
                        "message_type": "comment",
                        "creation_date": like.get("creation_date"),
                    })

    return docs


def materialize_ic7_auxiliary_collections(db, candidate_spec: dict, batch_size: int = 100000) -> Dict[str, int]:
    """Materialize real candidate-specific auxiliary collections for IC7.

    This is intentionally limited to query-plan analysis. It does not replace the
    benchmark p95 run. Its goal is to expose candidate-specific physical paths to
    MongoDB explain.
    """
    g_class = str((candidate_spec or {}).get("g_class", "")).upper()
    materialized: Dict[str, int] = {}

    if g_class not in {"G3", "G4", "G6"}:
        return materialized

    # Build the explicit edge structure once; G4 uses it directly and G3/G6 use
    # it to derive their summary/reverse-index structures.
    edge_docs = build_ic7_edge_docs(db)

    if g_class == "G4":
        _safe_drop_collection(db, IC7_G4_EDGE_COLLECTION)
        n = _insert_batches(db[IC7_G4_EDGE_COLLECTION], edge_docs, batch_size=batch_size) if edge_docs else 0
        db[IC7_G4_EDGE_COLLECTION].create_index("owner_person_id")
        db[IC7_G4_EDGE_COLLECTION].create_index("liker_person_id")
        db[IC7_G4_EDGE_COLLECTION].create_index([("owner_person_id", 1), ("creation_date", -1)])
        materialized[IC7_G4_EDGE_COLLECTION] = n
        return materialized

    # Group edges by owner for G3/G6.
    by_owner: Dict[str, List[dict]] = {}
    for e in edge_docs:
        by_owner.setdefault(e["owner_person_id"], []).append(e)

    if g_class == "G3":
        _safe_drop_collection(db, IC7_G3_SUMMARY_COLLECTION)
        summary_docs: List[dict] = []
        for owner, edges in by_owner.items():
            edges_sorted = sorted(edges, key=lambda x: str(x.get("creation_date") or ""), reverse=True)
            liker_ids = []
            for e in edges_sorted:
                liker = e.get("liker_person_id")
                if liker and liker not in liker_ids:
                    liker_ids.append(liker)
            person_map = _person_name_map(db, liker_ids[:100])
            summary_docs.append({
                "owner_person_id": owner,
                "recent_liker_ids": liker_ids[:100],
                "recent_likers": [person_map.get(x, {"person_id": x}) for x in liker_ids[:50]],
                "like_count": len(edges),
                "recent_messages": [
                    {
                        "message_id": e.get("message_id"),
                        "message_type": e.get("message_type"),
                        "liker_person_id": e.get("liker_person_id"),
                        "creation_date": e.get("creation_date"),
                    }
                    for e in edges_sorted[:100]
                ],
            })
        n = _insert_batches(db[IC7_G3_SUMMARY_COLLECTION], summary_docs, batch_size=batch_size) if summary_docs else 0
        db[IC7_G3_SUMMARY_COLLECTION].create_index("owner_person_id")
        materialized[IC7_G3_SUMMARY_COLLECTION] = n
        return materialized

    if g_class == "G6":
        _safe_drop_collection(db, IC7_G6_REVERSE_COLLECTION)
        rev_docs: List[dict] = []
        for owner, edges in by_owner.items():
            per_liker: Dict[str, dict] = {}
            for e in edges:
                liker = e.get("liker_person_id")
                if not liker:
                    continue
                item = per_liker.setdefault(liker, {
                    "owner_person_id": owner,
                    "liker_person_id": liker,
                    "like_count": 0,
                    "latest_creation_date": None,
                    "message_ids": [],
                })
                item["like_count"] += 1
                cd = e.get("creation_date")
                if cd is not None and (item["latest_creation_date"] is None or str(cd) > str(item["latest_creation_date"])):
                    item["latest_creation_date"] = cd
                if len(item["message_ids"]) < 20:
                    item["message_ids"].append(e.get("message_id"))
            rev_docs.extend(per_liker.values())
        n = _insert_batches(db[IC7_G6_REVERSE_COLLECTION], rev_docs, batch_size=batch_size) if rev_docs else 0
        db[IC7_G6_REVERSE_COLLECTION].create_index("owner_person_id")
        db[IC7_G6_REVERSE_COLLECTION].create_index("liker_person_id")
        db[IC7_G6_REVERSE_COLLECTION].create_index([("owner_person_id", 1), ("latest_creation_date", -1)])
        materialized[IC7_G6_REVERSE_COLLECTION] = n
        return materialized

    return materialized

# =========================================================
# Explainable operation plans per official LDBC SNB query
# =========================================================


def build_query_plan_ops(db, official_id: str, p: dict, candidate_spec: Optional[dict] = None, plan_row: Optional[pd.Series] = None) -> List[Dict[str, Any]]:
    """Build explainable MongoDB operations for each official-based query.

    These operations mirror the existing benchmark runner functions closely enough
    for query-plan diagnostics. Inserts are not forced into artificial explains;
    they are marked as not_explainable and only physical collection stats are kept.
    """
    official_id = str(official_id).upper()
    ops: List[Dict[str, Any]] = []

    pid = p.get("person_id")
    post_id = p.get("post_id")
    comment_id = p.get("comment_id")
    forum_id = p.get("forum_id")
    tag_id = p.get("tag_id")

    # -----------------------------
    # Short reads
    # -----------------------------
    if official_id == "IS1":
        place_id = first_field(db, "persons", {"person_id": pid}, "place_id") or p.get("place_id")
        return [
            find_op("is1_person_profile", "persons", {"person_id": pid}, limit=1),
            find_op("is1_person_place", "places", {"place_id": place_id}, limit=1),
        ]

    if official_id == "IS2":
        comment_ids = ids_from_cursor(db.comments.find({"creator_person_id": pid}, {"comment_id": 1}), "comment_id", limit=5)
        ops.extend([
            find_op("is2_recent_posts_by_person", "posts", {"creator_person_id": pid}, sort={"creation_date": -1}, limit=10),
            find_op("is2_recent_comments_by_person", "comments", {"creator_person_id": pid}, sort={"creation_date": -1}, limit=10),
        ])
        if comment_ids:
            ops.append(find_op("is2_parent_post_lookup", "posts", {"post_id": {"$exists": True}}, limit=1))
            ops.append(find_op("is2_parent_comment_lookup", "comments", {"comment_id": {"$in": comment_ids}}, limit=5))
        return ops

    if official_id == "IS3":
        return [
            find_op("is3_friends_outgoing", "person_knows_person", {"person1_id": pid}, limit=100),
            find_op("is3_friends_incoming", "person_knows_person", {"person2_id": pid}, limit=100),
        ]

    if official_id == "IS4":
        return [
            find_op("is4_post_content", "posts", {"post_id": post_id}, limit=1),
            find_op("is4_comment_content", "comments", {"comment_id": comment_id}, limit=1),
        ]

    if official_id == "IS5":
        post_creator = first_field(db, "posts", {"post_id": post_id}, "creator_person_id")
        comment_creator = first_field(db, "comments", {"comment_id": comment_id}, "creator_person_id")
        return [
            find_op("is5_post_lookup", "posts", {"post_id": post_id}, limit=1),
            find_op("is5_post_creator", "persons", {"person_id": post_creator}, limit=1),
            find_op("is5_comment_lookup", "comments", {"comment_id": comment_id}, limit=1),
            find_op("is5_comment_creator", "persons", {"person_id": comment_creator}, limit=1),
        ]

    if official_id == "IS6":
        f_id = first_field(db, "posts", {"post_id": post_id}, "forum_id") or forum_id
        moderator_id = first_field(db, "forums", {"forum_id": f_id}, "moderator_person_id")
        return [
            find_op("is6_post_lookup", "posts", {"post_id": post_id}, limit=1),
            find_op("is6_comment_lookup", "comments", {"comment_id": comment_id}, limit=1),
            find_op("is6_forum_lookup", "forums", {"forum_id": f_id}, limit=1),
            find_op("is6_forum_moderator", "persons", {"person_id": moderator_id}, limit=1),
        ]

    if official_id == "IS7":
        original_creator = first_field(db, "posts", {"post_id": post_id}, "creator_person_id")
        reply_creators = ids_from_cursor(
            db.comments.find({"reply_post_id": post_id}, {"creator_person_id": 1}),
            "creator_person_id",
            limit=20,
        )
        ops.extend([
            find_op("is7_original_post", "posts", {"post_id": post_id}, limit=1),
            find_op("is7_replies", "comments", {"reply_post_id": post_id}, limit=50),
        ])
        if reply_creators:
            ops.append(find_op("is7_reply_creators", "persons", {"person_id": {"$in": reply_creators}}, limit=50))
            if original_creator:
                ops.append(find_op(
                    "is7_friendship_with_original_creator",
                    "person_knows_person",
                    {"$or": [
                        {"person1_id": original_creator, "person2_id": {"$in": reply_creators}},
                        {"person2_id": original_creator, "person1_id": {"$in": reply_creators}},
                    ]},
                    limit=50,
                ))
        return ops

    # -----------------------------
    # Interactive complex reads
    # -----------------------------
    if official_id == "IC1":
        friends = get_friends_for_components(db, pid, max_depth=3, limit=200)
        return [
            find_op("ic1_knows_frontier", "person_knows_person", {"$or": [{"person1_id": pid}, {"person2_id": pid}]}, limit=200),
            find_op("ic1_friend_person_docs", "persons", {"person_id": {"$in": friends[:50]}}, limit=50),
            find_op("ic1_friend_study_org_edges", "person_study_at_organisation", {"person_id": {"$in": friends[:50]}}, limit=250),
            find_op("ic1_friend_work_org_edges", "person_work_at_organisation", {"person_id": {"$in": friends[:50]}}, limit=250),
        ]

    if official_id == "IC2":
        friends = get_friends_for_components(db, pid, max_depth=1, limit=200)
        return [
            find_op("ic2_friends", "person_knows_person", {"$or": [{"person1_id": pid}, {"person2_id": pid}]}, limit=200),
            find_op("ic2_posts_by_friends", "posts", {"creator_person_id": {"$in": friends[:50]}}, sort={"creation_date": -1}, limit=200),
            find_op("ic2_comments_by_friends", "comments", {"creator_person_id": {"$in": friends[:50]}}, sort={"creation_date": -1}, limit=200),
        ]

    if official_id == "IC3":
        friends = get_friends_for_components(db, pid, max_depth=2, limit=200)
        return [
            find_op("ic3_friends_foaf", "person_knows_person", {"$or": [{"person1_id": pid}, {"person2_id": pid}]}, limit=200),
            find_op("ic3_posts_by_friends", "posts", {"creator_person_id": {"$in": friends[:50]}}, limit=500),
            find_op("ic3_comments_by_friends", "comments", {"creator_person_id": {"$in": friends[:50]}}, limit=500),
            find_op("ic3_places_for_messages", "places", {"place_id": {"$exists": True}}, limit=50),
        ]

    if official_id == "IC4":
        friends = get_friends_for_components(db, pid, max_depth=1, limit=200)
        post_ids = ids_from_cursor(db.posts.find({"creator_person_id": {"$in": friends[:50]}}, {"post_id": 1}), "post_id", limit=100)
        return [
            find_op("ic4_friends", "person_knows_person", {"$or": [{"person1_id": pid}, {"person2_id": pid}]}, limit=200),
            find_op("ic4_posts_by_friends", "posts", {"creator_person_id": {"$in": friends[:50]}}, limit=500),
            find_op("ic4_post_tags", "post_has_tag", {"post_id": {"$in": post_ids}}, limit=500),
        ]

    if official_id == "IC5":
        friends = get_friends_for_components(db, pid, max_depth=2, limit=200)
        forums = ids_from_cursor(db.forum_has_member_person.find({"person_id": {"$in": friends[:50]}}, {"forum_id": 1}), "forum_id", limit=100)
        return [
            find_op("ic5_friends_foaf", "person_knows_person", {"$or": [{"person1_id": pid}, {"person2_id": pid}]}, limit=200),
            find_op("ic5_forum_memberships", "forum_has_member_person", {"person_id": {"$in": friends[:50]}}, limit=500),
            find_op("ic5_posts_in_forums", "posts", {"forum_id": {"$in": forums}}, limit=500),
        ]

    if official_id == "IC6":
        friends = get_friends_for_components(db, pid, max_depth=2, limit=200)
        post_ids = ids_from_cursor(db.posts.find({"creator_person_id": {"$in": friends[:50]}}, {"post_id": 1}), "post_id", limit=200)
        return [
            find_op("ic6_friends_foaf", "person_knows_person", {"$or": [{"person1_id": pid}, {"person2_id": pid}]}, limit=200),
            find_op("ic6_posts_by_friends", "posts", {"creator_person_id": {"$in": friends[:50]}}, limit=500),
            find_op("ic6_post_tags", "post_has_tag", {"post_id": {"$in": post_ids}}, limit=500),
            find_op("ic6_optional_tag_filter", "tags", {"tag_id": tag_id}, limit=1),
        ]

    if official_id == "IC7":
        g_class = str(((candidate_spec or {}).get("g_class") or (plan_row.get("g_class") if plan_row is not None else "") or "")).upper()
        mongodb_pattern = str(((candidate_spec or {}).get("materialization", {}) or {}).get("mongodb_pattern") or (plan_row.get("mongodb_pattern") if plan_row is not None else "") or "")

        own_posts = ids_from_cursor(db.posts.find({"creator_person_id": pid}, {"post_id": 1}), "post_id", limit=20)
        own_comments = ids_from_cursor(db.comments.find({"creator_person_id": pid}, {"comment_id": 1}), "comment_id", limit=20)
        likers_post = ids_from_cursor(db.person_likes_post.find({"post_id": {"$in": own_posts}}, {"person_id": 1}), "person_id", limit=100)
        likers_comment = ids_from_cursor(db.person_likes_comment.find({"comment_id": {"$in": own_comments}}, {"person_id": 1}), "person_id", limit=100)
        likers = list(dict.fromkeys(likers_post + likers_comment))

        # G3: query-plan path over a real owner-level summary collection.
        if g_class == "G3":
            summary_likers = ids_from_cursor(
                db[IC7_G3_SUMMARY_COLLECTION].find({"owner_person_id": pid}, {"recent_liker_ids": 1}),
                "recent_liker_ids",
                limit=1,
            )
            if not summary_likers:
                doc = db[IC7_G3_SUMMARY_COLLECTION].find_one({"owner_person_id": pid}, {"recent_liker_ids": 1}) or {}
                summary_likers = [normalize_id(x) for x in (doc.get("recent_liker_ids") or []) if normalize_id(x)]
            summary_likers = summary_likers or likers
            return [
                find_op(
                    "ic7_g3_owner_liker_summary",
                    IC7_G3_SUMMARY_COLLECTION,
                    {"owner_person_id": pid},
                    limit=1,
                    note="G3 uses a materialized owner-level recent-liker summary collection.",
                    component_role="summary_probe",
                    candidate_physical_path="g3_summary_collection",
                ),
                find_op(
                    "ic7_g3_knows_summary_likers",
                    "person_knows_person",
                    {"$or": [
                        {"person1_id": pid, "person2_id": {"$in": summary_likers[:100]}},
                        {"person2_id": pid, "person1_id": {"$in": summary_likers[:100]}},
                    ]},
                    limit=200,
                    note="Friendship check after reading summarized liker ids.",
                    component_role="friendship_check",
                    candidate_physical_path="g3_summary_collection",
                ),
            ]

        # G4: query-plan path over a real explicit-edge collection.
        if g_class == "G4":
            edge_likers = ids_from_cursor(
                db[IC7_G4_EDGE_COLLECTION].find({"owner_person_id": pid}, {"liker_person_id": 1}).sort("creation_date", -1),
                "liker_person_id",
                limit=100,
            ) or likers
            return [
                find_op(
                    "ic7_g4_explicit_like_edges_by_owner",
                    IC7_G4_EDGE_COLLECTION,
                    {"owner_person_id": pid},
                    sort={"creation_date": -1},
                    limit=200,
                    note="G4 uses a materialized explicit like-edge collection keyed by owner_person_id.",
                    component_role="explicit_edge_scan",
                    candidate_physical_path="g4_explicit_edge_collection",
                ),
                find_op(
                    "ic7_g4_liker_person_docs",
                    "persons",
                    {"person_id": {"$in": edge_likers[:100]}},
                    limit=100,
                    note="Fetch liker person documents after explicit edge scan.",
                    component_role="liker_document_fetch",
                    candidate_physical_path="g4_explicit_edge_collection",
                ),
                find_op(
                    "ic7_g4_knows_liker",
                    "person_knows_person",
                    {"$or": [
                        {"person1_id": pid, "person2_id": {"$in": edge_likers[:100]}},
                        {"person2_id": pid, "person1_id": {"$in": edge_likers[:100]}},
                    ]},
                    limit=200,
                    note="Friendship check after explicit edge scan.",
                    component_role="friendship_check",
                    candidate_physical_path="g4_explicit_edge_collection",
                ),
            ]

        # G6: query-plan path over a real owner->liker reverse-index collection.
        if g_class == "G6":
            reverse_likers = ids_from_cursor(
                db[IC7_G6_REVERSE_COLLECTION].find({"owner_person_id": pid}, {"liker_person_id": 1}).sort("latest_creation_date", -1),
                "liker_person_id",
                limit=100,
            ) or likers
            return [
                find_op(
                    "ic7_g6_owner_liker_reverse_index",
                    IC7_G6_REVERSE_COLLECTION,
                    {"owner_person_id": pid},
                    sort={"latest_creation_date": -1},
                    limit=200,
                    note="G6 uses a materialized reverse index from owner_person_id to liker_person_id.",
                    component_role="reverse_index_probe",
                    candidate_physical_path="g6_reverse_index_collection",
                ),
                find_op(
                    "ic7_g6_liker_person_docs",
                    "persons",
                    {"person_id": {"$in": reverse_likers[:100]}},
                    limit=100,
                    note="Fetch liker person documents after reverse-index probe.",
                    component_role="liker_document_fetch",
                    candidate_physical_path="g6_reverse_index_collection",
                ),
                find_op(
                    "ic7_g6_knows_liker",
                    "person_knows_person",
                    {"$or": [
                        {"person1_id": pid, "person2_id": {"$in": reverse_likers[:100]}},
                        {"person2_id": pid, "person1_id": {"$in": reverse_likers[:100]}},
                    ]},
                    limit=200,
                    note="Friendship check after reverse-index probe.",
                    component_role="friendship_check",
                    candidate_physical_path="g6_reverse_index_collection",
                ),
            ]

        # G0 and any fallback: canonical root/reference traversal.
        return [
            find_op("ic7_g0_posts_by_person", "posts", {"creator_person_id": pid}, limit=20, component_role="root_message_fetch", candidate_physical_path="g0_reference_traversal"),
            find_op("ic7_g0_comments_by_person", "comments", {"creator_person_id": pid}, limit=20, component_role="root_message_fetch", candidate_physical_path="g0_reference_traversal"),
            find_op("ic7_g0_likes_on_posts", "person_likes_post", {"post_id": {"$in": own_posts}}, sort={"creation_date": -1}, limit=200, component_role="relationship_lookup", candidate_physical_path="g0_reference_traversal"),
            find_op("ic7_g0_likes_on_comments", "person_likes_comment", {"comment_id": {"$in": own_comments}}, sort={"creation_date": -1}, limit=200, component_role="relationship_lookup", candidate_physical_path="g0_reference_traversal"),
            find_op("ic7_g0_liker_person_docs", "persons", {"person_id": {"$in": likers}}, limit=100, component_role="liker_document_fetch", candidate_physical_path="g0_reference_traversal"),
            find_op("ic7_g0_knows_liker", "person_knows_person", {"$or": [
                {"person1_id": pid, "person2_id": {"$in": likers}},
                {"person2_id": pid, "person1_id": {"$in": likers}},
            ]}, limit=200, component_role="friendship_check", candidate_physical_path="g0_reference_traversal"),
        ]

    # -----------------------------
    # Inserts: not artificially explained.
    # We keep affected collections + physical stats.
    # -----------------------------
    if official_id == "INS1":
        return [
            not_explainable_op("ins1_insert_person", "persons", "insert_not_explainable", 1),
            not_explainable_op("ins1_optional_person_place_ref", "person_is_located_in_place", "insert_not_explainable", 0),
            not_explainable_op("ins1_optional_interests", "person_has_interest_tag", "insert_not_explainable", 0),
            not_explainable_op("ins1_optional_study", "person_study_at_organisation", "insert_not_explainable", 0),
            not_explainable_op("ins1_optional_work", "person_work_at_organisation", "insert_not_explainable", 0),
        ]

    if official_id == "INS2":
        return [not_explainable_op("ins2_insert_like_to_post", "person_likes_post", "insert_not_explainable", 1)]

    if official_id == "INS3":
        return [not_explainable_op("ins3_insert_like_to_comment", "person_likes_comment", "insert_not_explainable", 1)]

    if official_id == "INS4":
        return [
            not_explainable_op("ins4_insert_forum", "forums", "insert_not_explainable", 1),
            not_explainable_op("ins4_optional_forum_tag", "forum_has_tag", "insert_not_explainable", 0),
        ]

    if official_id == "INS5":
        return [not_explainable_op("ins5_insert_forum_membership", "forum_has_member_person", "insert_not_explainable", 1)]

    if official_id == "INS6":
        return [
            not_explainable_op("ins6_insert_post", "posts", "insert_not_explainable", 1),
            not_explainable_op("ins6_insert_post_tag", "post_has_tag", "insert_not_explainable", 1 if tag_id else 0),
        ]

    if official_id == "INS7":
        return [
            not_explainable_op("ins7_insert_comment", "comments", "insert_not_explainable", 1),
            not_explainable_op("ins7_insert_comment_tag", "comment_has_tag", "insert_not_explainable", 1 if tag_id else 0),
        ]

    if official_id == "INS8":
        return [not_explainable_op("ins8_insert_friendship", "person_knows_person", "insert_not_explainable", 1)]

    return [not_explainable_op(f"{official_id.lower()}_no_query_plan_builder", "unknown", "no_query_plan_builder", 0)]


# =========================================================
# Row construction
# =========================================================


def plan_row_metadata(plan_row: pd.Series, spec: Optional[dict]) -> Dict[str, Any]:
    materialization = (spec or {}).get("materialization", {}) if isinstance(spec, dict) else {}
    metrics = (spec or {}).get("metrics", {}) if isinstance(spec, dict) else {}

    meta = {
        "candidate_id": plan_row.get("candidate_id"),
        "dataset": plan_row.get("dataset"),
        "scale_label": plan_row.get("scale_label"),
        "workload": plan_row.get("workload"),
        "query_name": plan_row.get("query_name"),
        "official_id": plan_row.get("official_id"),
        "official_title": plan_row.get("official_title"),
        "query_group": plan_row.get("query_group"),
        "operation_type": plan_row.get("operation_type"),
        "benchmark_group": plan_row.get("benchmark_group"),
        "activation_strength": plan_row.get("activation_strength"),
        "root_entity": plan_row.get("root_entity") or materialization.get("root_entity"),
        "root_collection": plan_row.get("root_collection") or materialization.get("root_collection"),
        "root_pk": plan_row.get("root_pk") or materialization.get("root_pk"),
        "g_class": plan_row.get("g_class") or (spec or {}).get("g_class"),
        "g_family": plan_row.get("g_family") or (spec or {}).get("g_family"),
        "g_role": plan_row.get("g_role") or (spec or {}).get("g_role"),
        "g_label": plan_row.get("g_label") or (spec or {}).get("g_label"),
        "mongodb_pattern": plan_row.get("mongodb_pattern") or materialization.get("mongodb_pattern"),
        "document_strategy": plan_row.get("document_strategy") or materialization.get("document_strategy"),
        "Rc_weighted": plan_row.get("Rc_weighted") or metrics.get("Rc_weighted"),
        "D": plan_row.get("D") or metrics.get("D"),
        "Re": plan_row.get("Re") or metrics.get("Re"),
        "DeltaRratio": plan_row.get("DeltaRratio") or metrics.get("DeltaRratio"),
        "dominant_semantic_type": plan_row.get("dominant_semantic_type") or metrics.get("dominant_semantic_type"),
        "update_volatility_max": plan_row.get("update_volatility_max") or metrics.get("update_volatility_max"),
        "observed_sharedness_max": plan_row.get("observed_sharedness_max") or metrics.get("observed_sharedness_max"),
        "accessed_entities_json": json_dumps(materialization.get("accessed_entities", [])),
        "relationships_used_json": json_dumps(materialization.get("relationships_used", [])),
        "edge_collections_json": json_dumps(materialization.get("edge_collections", [])),
        "reverse_indexes_json": json_dumps(materialization.get("reverse_indexes", [])),
    }
    return meta


def build_component_row(
    base_meta: Dict[str, Any],
    sample_index: int,
    db_name: str,
    op_index: int,
    op: Dict[str, Any],
    params: dict,
    explain_doc: Optional[dict],
    status: str,
    error_message: Optional[str],
    elapsed_wall_ms: Optional[float],
) -> Dict[str, Any]:
    collection_name = op.get("collection")
    metrics = extract_execution_metrics(explain_doc or {}) if explain_doc else {
        "executionTimeMillis": None,
        "nReturned": 0,
        "totalDocsExamined": 0,
        "totalKeysExamined": 0,
        "docs_per_returned_total": None,
        "keys_per_returned_total": None,
        "stages": [],
        "stage_set": set(),
        "index_names": [],
        "queryHash": None,
        "planCacheKey": None,
        "rejected_plans_count": 0,
        "usedDisk": None,
    }

    stage_set = metrics["stage_set"]

    row = dict(base_meta)
    row.update({
        "sample_index": sample_index,
        "db_name": db_name,
        "component_index": op_index,
        "component_name": op.get("component_name"),
        "component_role": op.get("component_role"),
        "candidate_physical_path": op.get("candidate_physical_path"),
        "operation_note": op.get("note"),
        "operation_kind": op.get("kind"),
        "collection_name": collection_name,
        "filter_json": json_dumps(op.get("filter")),
        "projection_json": json_dumps(op.get("projection")),
        "sort_json": json_dumps(op.get("sort")),
        "limit": op.get("limit"),
        "pipeline_json": json_dumps(op.get("pipeline")),
        "params_json": json_dumps(params),
        "execution_status": status,
        "error_message": error_message,
        "not_explainable_reason": op.get("not_explainable_reason"),
        "documents_written": int(op.get("documents_written") or 0),
        "explain_wall_ms": elapsed_wall_ms,
        "executionTimeMillis": metrics.get("executionTimeMillis"),
        "nReturned": metrics.get("nReturned"),
        "totalDocsExamined": metrics.get("totalDocsExamined"),
        "totalKeysExamined": metrics.get("totalKeysExamined"),
        "docs_per_returned_total": metrics.get("docs_per_returned_total"),
        "keys_per_returned_total": metrics.get("keys_per_returned_total"),
        "all_stages": ";".join(metrics.get("stages") or []),
        "all_index_names": ";".join(metrics.get("index_names") or []),
        "queryHash": metrics.get("queryHash"),
        "planCacheKey": metrics.get("planCacheKey"),
        "rejected_plans_count": metrics.get("rejected_plans_count"),
        "usedDisk": metrics.get("usedDisk"),
    })

    for stage in STAGES_OF_INTEREST:
        row[f"has_{stage}"] = stage in stage_set

    # Physical stats and derived metrics.
    if collection_name and collection_name != "unknown":
        row.update(get_coll_stats_from_cache(row.get("_db_obj"), collection_name))
    else:
        row.update({
            "collection_stats_status": "not_applicable",
            "collection_stats_error": None,
        })

    # Remove internal object if present.
    row.pop("_db_obj", None)
    return add_derived_physical_metrics(row)


_COLL_STATS_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}


def get_coll_stats_from_cache(db, collection_name: str) -> Dict[str, Any]:
    if db is None:
        return {"collection_stats_status": "missing_db", "collection_stats_error": None}
    key = (db.name, collection_name)
    if key not in _COLL_STATS_CACHE:
        _COLL_STATS_CACHE[key] = get_coll_stats(db, collection_name)
    return dict(_COLL_STATS_CACHE[key])


# =========================================================
# Aggregation outputs
# =========================================================


def any_true(series: pd.Series) -> bool:
    return bool(series.fillna(False).astype(bool).any())


def join_unique(series: pd.Series) -> str:
    values: List[str] = []
    seen: Set[str] = set()
    for value in series.dropna().astype(str):
        for part in value.split(";"):
            part = part.strip()
            if part and part not in seen:
                seen.add(part)
                values.append(part)
    return ";".join(values)


def summarize_components(component_df: pd.DataFrame) -> pd.DataFrame:
    if component_df.empty:
        return pd.DataFrame()

    group_cols = [
        "candidate_id", "dataset", "scale_label", "workload", "query_name", "official_id",
        "official_title", "query_group", "operation_type", "benchmark_group", "activation_strength",
        "root_entity", "root_collection", "root_pk", "g_class", "g_family", "g_role", "g_label",
        "mongodb_pattern", "document_strategy", "Rc_weighted", "D", "Re", "DeltaRratio",
        "dominant_semantic_type", "update_volatility_max", "observed_sharedness_max", "db_name",
    ]
    group_cols = [c for c in group_cols if c in component_df.columns]

    agg_dict: Dict[str, Any] = {
        "sample_index": "nunique",
        "component_name": "count",
        "execution_status": lambda s: "failed" if (s == "failed").any() else "completed",
        "error_message": join_unique,
        "executionTimeMillis": "sum",
        "nReturned": "sum",
        "totalDocsExamined": "sum",
        "totalKeysExamined": "sum",
        "estimated_docs_examined_bytes": "sum",
        "estimated_returned_bytes": "sum",
        "docs_examined_collection_ratio": "max",
        "index_to_data_size_ratio": "max",
        "collection_avg_obj_size_bytes": "max",
        "collection_size_bytes": "sum",
        "collection_total_index_size_bytes": "sum",
        "all_stages": join_unique,
        "all_index_names": join_unique,
        "queryHash": join_unique,
        "planCacheKey": join_unique,
        "rejected_plans_count": "sum",
        "documents_written": "sum",
    }

    for stage in STAGES_OF_INTEREST:
        col = f"has_{stage}"
        if col in component_df.columns:
            agg_dict[col] = any_true

    # Keep only existing columns in agg dict.
    agg_dict = {k: v for k, v in agg_dict.items() if k in component_df.columns}

    summary = component_df.groupby(group_cols, dropna=False).agg(agg_dict).reset_index()

    rename = {
        "sample_index": "sample_count",
        "component_name": "n_explain_components",
        "executionTimeMillis": "sum_executionTimeMillis",
        "nReturned": "sum_nReturned",
        "totalDocsExamined": "sum_totalDocsExamined",
        "totalKeysExamined": "sum_totalKeysExamined",
        "estimated_docs_examined_bytes": "sum_estimated_docs_examined_bytes",
        "estimated_returned_bytes": "sum_estimated_returned_bytes",
        "docs_examined_collection_ratio": "max_docs_examined_collection_ratio",
        "index_to_data_size_ratio": "max_index_to_data_size_ratio",
        "collection_avg_obj_size_bytes": "max_collection_avg_obj_size_bytes",
        "collection_size_bytes": "sum_collection_size_bytes",
        "collection_total_index_size_bytes": "sum_collection_total_index_size_bytes",
    }
    summary = summary.rename(columns=rename)

    summary["docs_per_returned_total"] = summary.apply(
        lambda r: safe_ratio(r.get("sum_totalDocsExamined"), r.get("sum_nReturned")),
        axis=1,
    )
    summary["keys_per_returned_total"] = summary.apply(
        lambda r: safe_ratio(r.get("sum_totalKeysExamined"), r.get("sum_nReturned")),
        axis=1,
    )
    summary["estimated_examined_bytes_per_returned"] = summary.apply(
        lambda r: safe_ratio(r.get("sum_estimated_docs_examined_bytes"), r.get("sum_nReturned")),
        axis=1,
    )

    # Friendly aliases requested in the planning notes.
    summary["all_stages"] = summary.get("all_stages", "")
    summary["all_index_names"] = summary.get("all_index_names", "")

    return summary


# =========================================================
# Raw explain saving
# =========================================================


def raw_explain_path(raw_dir: Path, candidate_id: str, official_id: str, sample_index: int, component_index: int, component_name: str) -> Path:
    filename = (
        f"{safe_name(official_id)}__{safe_name(candidate_id)}__"
        f"sample_{sample_index:03d}__component_{component_index:03d}__{safe_name(component_name)}.json"
    )
    return raw_dir / filename


# =========================================================
# Main query-plan execution
# =========================================================


def run_query_plan(args: argparse.Namespace) -> None:
    global GLOBAL_VERBOSE, GLOBAL_LOG_FILE_PATH, _COLL_STATS_CACHE
    GLOBAL_VERBOSE = bool(args.verbose)

    data_dir = Path(args.data_dir)
    artifacts_dir = Path(args.artifacts_dir)
    results_dir = Path(args.results_dir)
    ensure_dir(results_dir)

    GLOBAL_LOG_FILE_PATH = Path(args.log_file) if args.log_file else results_dir / "execution.log"
    if GLOBAL_LOG_FILE_PATH.exists() and not args.append_log:
        GLOBAL_LOG_FILE_PATH.unlink()

    write_log("LDBC SNB query-plan runner started", force=True)
    write_log(f"Command: {' '.join(sys.argv)}", force=True)

    if not args.query_plan_only:
        write_log("--query-plan-only was not provided; this script only supports query-plan mode.", level="WARNING", force=True)

    plan_df, specs_by_id, manifest = load_artifacts(artifacts_dir, args.execution_plan)
    selected_df = apply_filters(plan_df, args)

    if selected_df.empty:
        raise SystemExit("No selected rows after filters. Check --official-id, --query-name, --g-class, and --scale-label.")

    selected_summary_path = results_dir / "selected_experiments_summary.csv"
    selected_df.to_csv(selected_summary_path, index=False)
    write_log(f"Saved selected experiments: {selected_summary_path}", force=True)
    write_log(f"Selected plan rows: {len(selected_df)}", force=True)
    write_log(f"Selected candidates: {selected_df['candidate_id'].nunique()}", force=True)

    t_init = time.perf_counter()
    data = ldbc_runner.load_ldbc_snb_data(
        data_dir=data_dir,
        row_limit=args.row_limit,
        verbose=args.verbose,
    )
    init_seconds = time.perf_counter() - t_init

    init_rows = []
    for name, df in data.items():
        try:
            n_rows = int(len(df))
            n_cols = int(len(df.columns)) if hasattr(df, "columns") else None
        except Exception:
            n_rows = None
            n_cols = None
        init_rows.append({
            "scale_label": args.scale_label,
            "dataframe_name": name,
            "rows": n_rows,
            "columns": n_cols,
            "initialization_seconds_total": init_seconds,
            "status": "completed",
        })

    init_path = results_dir / "scale_db_initialization_summary.csv"
    pd.DataFrame(init_rows).to_csv(init_path, index=False)
    write_log(f"Saved initialization summary: {init_path}", force=True)

    client = connect_mongo(args)
    client.admin.command("ping")
    write_log("MongoDB connection OK", force=True)

    component_rows: List[Dict[str, Any]] = []
    load_rows: List[Dict[str, Any]] = []
    failed_rows: List[Dict[str, Any]] = []

    raw_dir = results_dir / "query_plan_raw_json"
    if args.save_raw_explain:
        ensure_dir(raw_dir)

    db_prefix = args.execution_db_prefix or f"ldbc_snb_qp_{safe_name(args.scale_label)}"

    try:
        for idx, plan_row in selected_df.iterrows():
            candidate_id = str(plan_row.get("candidate_id"))
            official_id = str(plan_row.get("official_id"))
            spec = specs_by_id.get(candidate_id)

            if not spec:
                err = f"Missing candidate spec for {candidate_id}"
                write_log(err, level="ERROR", force=True)
                failed_rows.append({
                    "candidate_id": candidate_id,
                    "official_id": official_id,
                    "execution_status": "failed",
                    "error_message": err,
                })
                continue

            db_name = build_db_name(db_prefix, candidate_id)
            write_log(
                f"[{idx + 1}/{len(selected_df)}] materializing candidate={candidate_id} official_id={official_id} db={db_name}",
                force=True,
            )

            t_load = time.perf_counter()
            try:
                load_info = ldbc_runner.materialize_candidate(
                    mongo_client=client,
                    db_name=db_name,
                    candidate_spec=spec,
                    data=data,
                    batch_size=args.batch_size,
                    force_rebuild=args.force_rebuild_db,
                    verbose=args.verbose,
                )
                if official_id.upper() == "IC7":
                    aux_info = materialize_ic7_auxiliary_collections(db=client[db_name], candidate_spec=spec, batch_size=args.batch_size)
                    if aux_info:
                        loaded = dict(load_info.get("loaded_collections", {}) or {})
                        loaded.update(aux_info)
                        load_info["loaded_collections"] = loaded
                        write_log(f"Materialized IC7 auxiliary collections for {candidate_id}: {aux_info}", force=True)
                load_status = "completed"
                load_error = None
            except Exception as exc:
                load_info = {"loaded_collections": {}, "load_completed": False, "load_seconds": None}
                load_status = "failed"
                load_error = f"{type(exc).__name__}: {exc}"
                write_log(traceback.format_exc(), level="ERROR", force=True)

            load_seconds = time.perf_counter() - t_load
            load_row = {
                "candidate_id": candidate_id,
                "official_id": official_id,
                "query_name": plan_row.get("query_name"),
                "benchmark_group": plan_row.get("benchmark_group"),
                "g_class": plan_row.get("g_class"),
                "db_name": db_name,
                "load_seconds": load_info.get("load_seconds", load_seconds),
                "load_status": load_status,
                "load_error": load_error,
                "loaded_collections_json": json_dumps(load_info.get("loaded_collections", {})),
            }
            load_rows.append(load_row)

            if load_status != "completed":
                failed_rows.append({**load_row, "execution_status": "failed", "error_message": load_error})
                continue

            db = client[db_name]
            _COLL_STATS_CACHE = {k: v for k, v in _COLL_STATS_CACHE.items() if k[0] != db_name}

            base_meta = plan_row_metadata(plan_row, spec)
            base_meta["_db_obj"] = db

            n_samples = 1 if args.explain_one_per_query else max(1, int(args.sample_size))

            for sample_index in range(1, n_samples + 1):
                try:
                    params = build_params_for_sample(db, official_id, sample_index, args.sample_size)
                    ops = build_query_plan_ops(db, official_id, params, candidate_spec=spec, plan_row=plan_row)
                except Exception as exc:
                    err = f"{type(exc).__name__}: {exc}"
                    write_log(f"Failed to build ops candidate={candidate_id} official_id={official_id}: {err}", level="ERROR", force=True)
                    failed_rows.append({
                        **{k: v for k, v in base_meta.items() if k != "_db_obj"},
                        "sample_index": sample_index,
                        "execution_status": "failed",
                        "error_message": err,
                    })
                    continue

                for op_index, op in enumerate(ops, start=1):
                    explain_doc = None
                    elapsed_wall_ms = None
                    status = "completed"
                    error_message = None

                    if op.get("kind") == "not_explainable":
                        status = "not_explainable"
                    else:
                        t0 = time.perf_counter()
                        try:
                            max_attempts = 3
                            for attempt in range(1, max_attempts + 1):
                                try:
                                    explain_doc = run_explain(db, op, args.explain_verbosity)
                                    break
                                except (AutoReconnect, ServerSelectionTimeoutError, NetworkTimeout):
                                    if attempt >= max_attempts:
                                        raise
                                    time.sleep(2 * attempt)
                            elapsed_wall_ms = (time.perf_counter() - t0) * 1000.0
                        except Exception as exc:
                            elapsed_wall_ms = (time.perf_counter() - t0) * 1000.0
                            status = "failed"
                            error_message = f"{type(exc).__name__}: {exc}"
                            write_log(
                                f"Explain failed candidate={candidate_id} official_id={official_id} component={op.get('component_name')}: {error_message}",
                                level="ERROR",
                                force=True,
                            )

                    row = build_component_row(
                        base_meta=base_meta,
                        sample_index=sample_index,
                        db_name=db_name,
                        op_index=op_index,
                        op=op,
                        params=params,
                        explain_doc=explain_doc,
                        status=status,
                        error_message=error_message,
                        elapsed_wall_ms=elapsed_wall_ms,
                    )
                    component_rows.append(row)

                    if args.save_raw_explain and explain_doc is not None:
                        out_path = raw_explain_path(
                            raw_dir=raw_dir,
                            candidate_id=candidate_id,
                            official_id=official_id,
                            sample_index=sample_index,
                            component_index=op_index,
                            component_name=op.get("component_name", "component"),
                        )
                        with open(out_path, "w", encoding="utf-8") as f:
                            json.dump(to_jsonable(explain_doc), f, indent=2, ensure_ascii=False)

                    if status == "failed":
                        failed_rows.append({k: v for k, v in row.items() if k != "_db_obj"})

    finally:
        try:
            client.close()
        except Exception:
            pass

    # -----------------------------------------------------
    # Save outputs
    # -----------------------------------------------------
    load_path = results_dir / "collection_swap_summary.csv"
    pd.DataFrame(load_rows).to_csv(load_path, index=False)
    write_log(f"Saved collection/materialization summary: {load_path}", force=True)

    component_df = pd.DataFrame(component_rows)
    component_path = results_dir / "query_plan_component_results.csv"
    component_df.to_csv(component_path, index=False)
    write_log(f"Saved query-plan component results: {component_path}", force=True)

    summary_df = summarize_components(component_df)
    summary_path = results_dir / "query_plan_summary_results.csv"
    summary_df.to_csv(summary_path, index=False)
    write_log(f"Saved query-plan summary results: {summary_path}", force=True)

    if not component_df.empty:
        status_summary = (
            component_df.groupby(["execution_status"], dropna=False)
            .size()
            .reset_index(name="rows")
            .sort_values("execution_status")
        )
    else:
        status_summary = pd.DataFrame([{"execution_status": "no_rows", "rows": 0}])

    status_path = results_dir / "query_plan_status_summary.csv"
    status_summary.to_csv(status_path, index=False)
    write_log(f"Saved query-plan status summary: {status_path}", force=True)

    if failed_rows:
        failed_path = results_dir / "query_plan_failed_rows.csv"
        pd.DataFrame(failed_rows).to_csv(failed_path, index=False)
        write_log(f"Saved failed rows: {failed_path}", level="WARNING", force=True)

    # Zero-returned rows for reads only. Inserts/not_explainable are excluded.
    zero_df = pd.DataFrame()
    if not summary_df.empty and "operation_type" in summary_df.columns and "sum_nReturned" in summary_df.columns:
        zero_df = summary_df[
            (summary_df["operation_type"].astype(str) == "read")
            & (summary_df["execution_status"].astype(str) == "completed")
            & (summary_df["sum_nReturned"].fillna(0).astype(float) <= 0)
        ].copy()

    if not zero_df.empty:
        zero_path = results_dir / "query_plan_zero_returned_rows.csv"
        zero_df.to_csv(zero_path, index=False)
        write_log(f"Saved zero-returned read rows: {zero_path}", level="WARNING", force=True)

    if not args.no_run_manifest:
        run_manifest = {
            "script": "run_ldbc_snb_mongo_query_plan.py",
            "query_plan_only": True,
            "data_dir": str(data_dir),
            "artifacts_dir": str(artifacts_dir),
            "results_dir": str(results_dir),
            "execution_plan": args.execution_plan,
            "scale_label": args.scale_label,
            "mongo_host": args.mongo_host,
            "mongo_port": args.mongo_port,
            "selected_plan_rows": int(len(selected_df)),
            "selected_candidates": int(selected_df["candidate_id"].nunique()),
            "selected_official_ids": sorted(selected_df["official_id"].dropna().astype(str).unique().tolist()),
            "selected_query_names": sorted(selected_df["query_name"].dropna().astype(str).unique().tolist()),
            "sample_size": int(args.sample_size),
            "explain_one_per_query": bool(args.explain_one_per_query),
            "explain_verbosity": args.explain_verbosity,
            "save_raw_explain": bool(args.save_raw_explain),
            "row_limit": args.row_limit,
            "batch_size": int(args.batch_size),
            "force_rebuild_db": bool(args.force_rebuild_db),
            "source_manifest": manifest,
            "output_files": {
                "execution_log": str(GLOBAL_LOG_FILE_PATH),
                "selected_experiments_summary": str(selected_summary_path),
                "scale_db_initialization_summary": str(init_path),
                "collection_swap_summary": str(load_path),
                "query_plan_component_results": str(component_path),
                "query_plan_summary_results": str(summary_path),
                "query_plan_status_summary": str(status_path),
                "query_plan_raw_json": str(raw_dir) if args.save_raw_explain else None,
            },
        }
        manifest_path = results_dir / "benchmark_run_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(to_jsonable(run_manifest), f, indent=2, ensure_ascii=False)
        write_log(f"Saved run manifest: {manifest_path}", force=True)

    write_log(f"Done. Results in: {results_dir}", force=True)


# =========================================================
# CLI
# =========================================================


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="MongoDB query-plan runner for LDBC SNB SchemaLens candidates"
    )

    p.add_argument("--data-dir", required=True, help="Path to the LDBC SNB scale-factor data directory")
    p.add_argument("--artifacts-dir", required=True, help="Path to the bundle mongo_configurations directory")
    p.add_argument("--results-dir", required=True, help="Output directory for query-plan analysis files")
    p.add_argument("--execution-plan", default="benchmark_execution_plan.csv", help="Execution plan CSV inside --artifacts-dir")
    p.add_argument("--scale-label", required=True, help="Scale label, e.g., sf0.1, sf1, sf3")

    p.add_argument("--mongo-host", default="127.0.0.1")
    p.add_argument("--mongo-port", type=int, default=27017)
    p.add_argument("--mongo-username", default=None)
    p.add_argument("--mongo-password", default=None)
    p.add_argument("--mongo-auth-source", default="admin")

    p.add_argument("--candidate-id", nargs="*", default=None)
    p.add_argument("--query-name", nargs="*", default=None)
    p.add_argument("--official-id", nargs="*", default=None)
    p.add_argument("--benchmark-group", nargs="*", choices=["primary", "secondary_affected", "control"], default=None)
    p.add_argument("--g-class", nargs="*", default=None)
    p.add_argument("--config-name", nargs="*", default=None, help="Optional alias filter over candidate_id/g_class/mongodb_pattern/document_strategy/g_label")
    p.add_argument("--run-phase", nargs="*", choices=["cold", "hot"], default=["hot"], help="Kept for compatibility; query-plan analysis uses materialized DB state")

    p.add_argument("--query-plan-only", action="store_true", help="Compatibility flag; this script always runs query-plan mode")
    p.add_argument("--explain-verbosity", default="executionStats", choices=["queryPlanner", "executionStats", "allPlansExecution"])
    p.add_argument("--save-raw-explain", action="store_true")
    p.add_argument("--explain-one-per-query", action="store_true", help="Use only one semantic parameter sample per candidate/query")
    p.add_argument("--minimal-base-load", action="store_true", help="Accepted for CLI compatibility; currently conservative full candidate materialization is used")

    p.add_argument("--sample-size", type=int, default=5, help="Number of semantic parameter samples when --explain-one-per-query is not used")
    p.add_argument("--row-limit", type=int, default=None, help="Optional row limit for loading LDBC CSVs, useful for smoke tests only")
    p.add_argument("--batch-size", type=int, default=50000)
    p.add_argument("--max-runs", type=int, default=None)
    p.add_argument("--execution-db-prefix", default=None)

    p.add_argument("--force-rebuild-db", "--force-rebuild-scale-db", dest="force_rebuild_db", action="store_true")
    p.add_argument("--log-file", default=None)
    p.add_argument("--append-log", action="store_true")
    p.add_argument("--no-run-manifest", action="store_true")
    p.add_argument("--verbose", action="store_true")

    return p


def main() -> None:
    args = build_arg_parser().parse_args()
    run_query_plan(args)


if __name__ == "__main__":
    main()
