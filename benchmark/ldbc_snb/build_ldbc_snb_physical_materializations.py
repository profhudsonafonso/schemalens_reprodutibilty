#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build physical MongoDB materializations for LDBC SNB SchemaLens candidates.

Purpose
-------
This is STEP 1 of the journal/extended evaluation pipeline.
It does NOT run latency benchmarks and does NOT run query plans.
It reads the SchemaLens-generated MongoDB candidate artifacts, creates one
MongoDB database per candidate, compiles the candidate template into concrete
physical collections/indexes when possible, validates what was created, and
writes a manifest that the later benchmark/query-plan runner must consume.

The key methodological rule is:
    A candidate should not enter the physical benchmark unless this script marks
    it as ready/ready_generic in physical_materialization_manifest.csv.

Expected companion file
-----------------------
Place this script in the same directory as the existing LDBC benchmark runner:
    run_ldbc_snb_mongo_benchmark.py

The script imports that runner to reuse the already validated LDBC CSV loader and
canonical candidate loader, then adds explicit physical structures for templates
that require them.

Outputs
-------
<results-dir>/materialization/
    selected_experiments_summary.csv
    scale_db_initialization_summary.csv
    physical_materialization_manifest.csv
    physical_materialization_manifest.json
    physical_support_matrix.csv
    physical_impossibility_report.csv
    materialization_validation_summary.csv
    README_materialization.md
    benchmark_run_manifest.json
    execution.log

Notes
-----
- G0/G1/G2/G7 can be valid physical materializations as reference/root/containment
  baseline structures. They do not necessarily need derived collections.
- G3/G4/G6/G8/G9 often require derived summaries, explicit edge collections,
  reverse indexes, or embedded containment collections. This script attempts to
  build those structures using both artifact metadata and LDBC naming patterns.
- Exact query-specific physical compilers can be added incrementally. IC7 is
  implemented explicitly because it is the representative mixed graph case.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import sys
import time
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import OperationFailure

try:
    ldbc_runner = importlib.import_module("run_ldbc_snb_mongo_benchmark")
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Could not import run_ldbc_snb_mongo_benchmark.py.\n"
        "Place this script next to the current LDBC benchmark runner or run it "
        "from a directory where that module is importable."
    ) from exc


# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
GLOBAL_VERBOSE = False
GLOBAL_LOG_FILE_PATH: Optional[Path] = None


def utc_now_iso() -> str:
    return pd.Timestamp.now("UTC").isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_name(value: Any, max_len: int = 80) -> str:
    raw = str(value)
    out = re.sub(r"[^A-Za-z0-9_]+", "_", raw).strip("_").lower()
    if not out:
        out = "x"
    return out[:max_len]


def short_hash(value: Any, n: int = 8) -> str:
    return hashlib.sha1(str(value).encode("utf-8")).hexdigest()[:n]


def write_log(message: str, level: str = "INFO", force: bool = False) -> None:
    line = f"[{utc_now_iso()}] [{level}] {message}"
    if force or GLOBAL_VERBOSE:
        print(line, flush=True)
    if GLOBAL_LOG_FILE_PATH is not None:
        with open(GLOBAL_LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def runner_log_compat(msg: str, verbose: Any = True, level: Optional[str] = None) -> None:
    if isinstance(verbose, str) and level is None:
        level = verbose
        should_print = True
    else:
        should_print = bool(verbose)
        level = level or "INFO"
    write_log(str(msg), level=str(level), force=should_print)


try:
    ldbc_runner.log = runner_log_compat
except Exception:
    pass


# -----------------------------------------------------------------------------
# Static LDBC naming helpers
# -----------------------------------------------------------------------------
ENTITY_COLLECTIONS = {
    "Person": "persons",
    "Forum": "forums",
    "Post": "posts",
    "Comment": "comments",
    "Place": "places",
    "Organisation": "organisations",
    "Organization": "organisations",
    "Tag": "tags",
    "TagClass": "tagclasses",
}

COLLECTION_PKS = {
    "persons": "person_id",
    "forums": "forum_id",
    "posts": "post_id",
    "comments": "comment_id",
    "places": "place_id",
    "organisations": "organisation_id",
    "tags": "tag_id",
    "tagclasses": "tagclass_id",
}

# Priority for inferring pair-like relationship endpoints.
RELATIONSHIP_ENDPOINT_PRIORITIES = {
    "person_knows_person": ["person1_id", "person2_id"],
    "person_likes_post": ["person_id", "post_id"],
    "person_likes_comment": ["person_id", "comment_id"],
    "forum_has_member_person": ["forum_id", "person_id"],
    "forum_has_moderator_person": ["forum_id", "person_id"],
    "forum_container_of_post": ["forum_id", "post_id"],
    "post_has_creator_person": ["post_id", "person_id", "creator_person_id"],
    "comment_has_creator_person": ["comment_id", "person_id", "creator_person_id"],
    "comment_reply_of_post": ["comment_id", "post_id"],
    "comment_reply_of_comment": ["comment1_id", "comment2_id", "comment_id", "parent_comment_id"],
    "post_has_tag": ["post_id", "tag_id"],
    "comment_has_tag": ["comment_id", "tag_id"],
    "forum_has_tag": ["forum_id", "tag_id"],
    "person_has_interest_tag": ["person_id", "tag_id"],
    "person_is_located_in_place": ["person_id", "place_id"],
    "post_is_located_in_place": ["post_id", "place_id"],
    "comment_is_located_in_place": ["comment_id", "place_id"],
    "person_study_at_organisation": ["person_id", "organisation_id"],
    "person_work_at_organisation": ["person_id", "organisation_id"],
    "organisation_is_located_in_place": ["organisation_id", "place_id"],
    "tag_has_type_tagclass": ["tag_id", "tagclass_id"],
    "tagclass_is_subclass_of_tagclass": ["tagclass_id", "parent_tagclass_id"],
    "place_is_part_of_place": ["place_id", "parent_place_id"],
}

CONTAINMENT_HINTS = [
    "container_of",
    "reply_of",
    "is_part_of",
]


# -----------------------------------------------------------------------------
# JSON/CSV helpers
# -----------------------------------------------------------------------------

def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def json_dumps(value: Any) -> str:
    try:
        return json.dumps(to_jsonable(value), ensure_ascii=False, sort_keys=True)
    except Exception:
        return json.dumps(str(value), ensure_ascii=False)


def to_jsonable(value: Any) -> Any:
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
    artifact_manifest = read_json(manifest_path) if manifest_path.exists() else {}
    return plan_df, specs_by_id, artifact_manifest


def apply_filters(plan_df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    df = plan_df.copy()
    if args.scale_label and "scale_label" in df.columns:
        matching = df[df["scale_label"].astype(str) == str(args.scale_label)]
        if not matching.empty:
            df = matching
    if args.candidate_id:
        df = df[df["candidate_id"].astype(str).isin(args.candidate_id)]
    if args.official_id:
        df = df[df["official_id"].astype(str).isin(args.official_id)]
    if args.query_name:
        df = df[df["query_name"].astype(str).isin(args.query_name)]
    if args.g_class:
        df = df[df["g_class"].astype(str).isin(args.g_class)]
    if args.benchmark_group:
        df = df[df["benchmark_group"].astype(str).isin(args.benchmark_group)]
    if args.max_candidates is not None:
        df = df.head(int(args.max_candidates))
    return df.reset_index(drop=True)


# -----------------------------------------------------------------------------
# Mongo helpers
# -----------------------------------------------------------------------------

def connect_mongo(args: argparse.Namespace) -> MongoClient:
    kwargs = {
        "host": args.mongo_host,
        "port": int(args.mongo_port),
        "serverSelectionTimeoutMS": int(args.server_selection_timeout_ms),
        "connectTimeoutMS": int(args.connect_timeout_ms),
        "socketTimeoutMS": int(args.socket_timeout_ms),
    }
    if args.mongo_username:
        kwargs["username"] = args.mongo_username
        kwargs["password"] = args.mongo_password
        kwargs["authSource"] = args.mongo_auth_source
    return MongoClient(**kwargs)


def build_db_name(prefix: str, scale_label: str, candidate_id: str) -> str:
    return f"{safe_name(prefix)}_{safe_name(scale_label)}_{safe_name(candidate_id, max_len=90)}"


def collection_exists(db, name: str) -> bool:
    try:
        return name in db.list_collection_names()
    except Exception:
        return False


def safe_drop_collection(db, name: str) -> None:
    try:
        db[name].drop()
    except Exception:
        pass


def insert_batches(collection, docs: Iterable[dict], batch_size: int) -> int:
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


def create_index_safe(collection, keys: Any, **kwargs) -> Optional[str]:
    try:
        return collection.create_index(keys, **kwargs)
    except Exception as exc:
        write_log(f"Could not create index on {collection.full_name}: {keys}: {exc}", level="WARNING")
        return None


def coll_stats(db, name: str) -> Dict[str, Any]:
    try:
        stats = db.command("collStats", name)
        return {
            "collection": name,
            "count": int(stats.get("count", 0)),
            "size": int(stats.get("size", 0)),
            "storageSize": int(stats.get("storageSize", 0)),
            "totalIndexSize": int(stats.get("totalIndexSize", 0)),
            "avgObjSize": stats.get("avgObjSize"),
            "nindexes": int(stats.get("nindexes", 0)),
        }
    except Exception as exc:
        return {"collection": name, "error": f"{type(exc).__name__}: {exc}"}


def get_collection_fields(db, collection_name: str, sample_limit: int = 10) -> List[str]:
    fields = set()
    try:
        for doc in db[collection_name].find({}, limit=sample_limit):
            fields.update(doc.keys())
    except Exception:
        pass
    fields.discard("_id")
    return sorted(fields)


def normalize_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value)
    if s == "" or s.lower() == "nan":
        return None
    return s


def infer_id_fields(db, collection_name: str) -> List[str]:
    fields = get_collection_fields(db, collection_name)
    id_fields = [f for f in fields if f.endswith("_id") or f in {"id"}]
    priorities = RELATIONSHIP_ENDPOINT_PRIORITIES.get(collection_name, [])
    ordered = []
    for p in priorities:
        if p in id_fields and p not in ordered:
            ordered.append(p)
    for f in id_fields:
        if f not in ordered:
            ordered.append(f)
    return ordered


def infer_pair_fields(db, collection_name: str, root_pk: Optional[str] = None) -> Optional[Tuple[str, str, str]]:
    """Return (source_field, target_field, method)."""
    id_fields = infer_id_fields(db, collection_name)
    if len(id_fields) < 2:
        return None
    if root_pk and root_pk in id_fields:
        others = [f for f in id_fields if f != root_pk]
        if others:
            return root_pk, others[0], "root_pk_priority"
    if collection_name in RELATIONSHIP_ENDPOINT_PRIORITIES:
        pr = [f for f in RELATIONSHIP_ENDPOINT_PRIORITIES[collection_name] if f in id_fields]
        if len(pr) >= 2:
            return pr[0], pr[1], "relationship_priority"
    return id_fields[0], id_fields[1], "generic_first_two_id_fields"


def spec_list(spec: dict, *keys: str) -> List[str]:
    for k in keys:
        v = spec.get(k)
        if isinstance(v, list):
            return [str(x) for x in v if str(x) and str(x).lower() != "nan"]
        if isinstance(v, str) and v:
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed]
            except Exception:
                return [x.strip() for x in v.split(",") if x.strip()]
    return []


def get_root_collection_and_pk(spec: dict, plan_row: pd.Series, db=None) -> Tuple[Optional[str], Optional[str], str]:
    root_entity = spec.get("root_entity") or plan_row.get("root_entity") if plan_row is not None else None
    root_pk = spec.get("root_pk") or plan_row.get("root_pk") if plan_row is not None else None
    root_collection = spec.get("root_collection") or plan_row.get("root_collection") if plan_row is not None else None

    if root_entity and not root_collection:
        root_collection = ENTITY_COLLECTIONS.get(str(root_entity), safe_name(str(root_entity)) + "s")
    if root_collection and not root_pk:
        root_pk = COLLECTION_PKS.get(str(root_collection))
    if not root_collection and db is not None:
        # As a last fallback, pick persons if it exists because many LDBC queries are person-rooted.
        if collection_exists(db, "persons"):
            root_collection = "persons"
            root_pk = "person_id"
    method = "artifact" if (root_collection and root_pk) else "fallback_incomplete"
    return str(root_collection) if root_collection else None, str(root_pk) if root_pk else None, method


def relationship_collections_from_spec(spec: dict, db) -> List[str]:
    candidates = []
    for key in ["relationships_used", "relationship_collections", "edge_collections", "touched_relationships"]:
        candidates.extend(spec_list(spec, key))
    # Keep only collections that actually exist.
    seen = []
    for c in candidates:
        cc = str(c)
        if collection_exists(db, cc) and cc not in seen:
            seen.append(cc)
    # If artifacts do not explicitly expose relationship collections, infer from current db.
    if not seen:
        for c in db.list_collection_names():
            if any(tok in c for tok in ["_has_", "_likes_", "_knows_", "_container_of_", "_reply_of_", "_is_located_", "_study_at_", "_work_at_", "_part_of_"]):
                seen.append(c)
    return seen


# -----------------------------------------------------------------------------
# Exact IC7 compiler
# -----------------------------------------------------------------------------
IC7_G3_SUMMARY_COLLECTION = "ic7_g3_person_recent_liker_summary"
IC7_G4_EDGE_COLLECTION = "ic7_g4_explicit_like_edges"
IC7_G6_REVERSE_COLLECTION = "ic7_g6_owner_liker_reverse_index"


def build_ic7_edge_docs(db) -> List[dict]:
    docs: List[dict] = []
    post_owner: Dict[str, str] = {}
    if collection_exists(db, "posts"):
        for post in db.posts.find({}, {"post_id": 1, "creator_person_id": 1}):
            post_id = normalize_id(post.get("post_id"))
            owner = normalize_id(post.get("creator_person_id"))
            if post_id and owner:
                post_owner[post_id] = owner
    if post_owner and collection_exists(db, "person_likes_post"):
        post_ids = list(post_owner.keys())
        # Chunk to avoid huge $in documents.
        for i in range(0, len(post_ids), 50000):
            chunk = post_ids[i : i + 50000]
            for like in db.person_likes_post.find({"post_id": {"$in": chunk}}, {"person_id": 1, "post_id": 1, "creation_date": 1}):
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
    if collection_exists(db, "comments"):
        for comment in db.comments.find({}, {"comment_id": 1, "creator_person_id": 1}):
            comment_id = normalize_id(comment.get("comment_id"))
            owner = normalize_id(comment.get("creator_person_id"))
            if comment_id and owner:
                comment_owner[comment_id] = owner
    if comment_owner and collection_exists(db, "person_likes_comment"):
        comment_ids = list(comment_owner.keys())
        for i in range(0, len(comment_ids), 50000):
            chunk = comment_ids[i : i + 50000]
            for like in db.person_likes_comment.find({"comment_id": {"$in": chunk}}, {"person_id": 1, "comment_id": 1, "creation_date": 1}):
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


def person_name_map(db, person_ids: Sequence[str]) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    if not person_ids or not collection_exists(db, "persons"):
        return out
    for i in range(0, len(person_ids), 50000):
        chunk = list(person_ids[i : i + 50000])
        for pdoc in db.persons.find({"person_id": {"$in": chunk}}, {"person_id": 1, "first_name": 1, "last_name": 1}):
            pid = normalize_id(pdoc.get("person_id"))
            if pid:
                out[pid] = {"person_id": pid, "first_name": pdoc.get("first_name"), "last_name": pdoc.get("last_name")}
    return out


def compile_ic7_physical(db, g_class: str, batch_size: int) -> Tuple[List[dict], List[dict], List[str]]:
    created: List[dict] = []
    indexes: List[dict] = []
    warnings: List[str] = []
    edge_docs = build_ic7_edge_docs(db)
    if g_class == "G4":
        safe_drop_collection(db, IC7_G4_EDGE_COLLECTION)
        n = insert_batches(db[IC7_G4_EDGE_COLLECTION], edge_docs, batch_size=batch_size) if edge_docs else 0
        idxs = [
            create_index_safe(db[IC7_G4_EDGE_COLLECTION], [("owner_person_id", ASCENDING)]),
            create_index_safe(db[IC7_G4_EDGE_COLLECTION], [("liker_person_id", ASCENDING)]),
            create_index_safe(db[IC7_G4_EDGE_COLLECTION], [("owner_person_id", ASCENDING), ("creation_date", DESCENDING)]),
        ]
        created.append({"collection": IC7_G4_EDGE_COLLECTION, "role": "explicit_like_edge_collection", "documents": n})
        indexes.extend({"collection": IC7_G4_EDGE_COLLECTION, "index": x} for x in idxs if x)
        return created, indexes, warnings

    by_owner: Dict[str, List[dict]] = defaultdict(list)
    for e in edge_docs:
        by_owner[e["owner_person_id"]].append(e)

    if g_class == "G3":
        safe_drop_collection(db, IC7_G3_SUMMARY_COLLECTION)
        summary_docs: List[dict] = []
        for owner, edges in by_owner.items():
            edges_sorted = sorted(edges, key=lambda x: str(x.get("creation_date") or ""), reverse=True)
            liker_ids: List[str] = []
            for e in edges_sorted:
                liker = e.get("liker_person_id")
                if liker and liker not in liker_ids:
                    liker_ids.append(liker)
            pmap = person_name_map(db, liker_ids[:100])
            summary_docs.append({
                "owner_person_id": owner,
                "recent_liker_ids": liker_ids[:100],
                "recent_likers": [pmap.get(x, {"person_id": x}) for x in liker_ids[:50]],
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
        n = insert_batches(db[IC7_G3_SUMMARY_COLLECTION], summary_docs, batch_size=batch_size) if summary_docs else 0
        idx = create_index_safe(db[IC7_G3_SUMMARY_COLLECTION], [("owner_person_id", ASCENDING)])
        created.append({"collection": IC7_G3_SUMMARY_COLLECTION, "role": "owner_recent_liker_summary", "documents": n})
        if idx:
            indexes.append({"collection": IC7_G3_SUMMARY_COLLECTION, "index": idx})
        return created, indexes, warnings

    if g_class == "G6":
        safe_drop_collection(db, IC7_G6_REVERSE_COLLECTION)
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
                if len(item["message_ids"]) < 50:
                    item["message_ids"].append(e.get("message_id"))
            rev_docs.extend(per_liker.values())
        n = insert_batches(db[IC7_G6_REVERSE_COLLECTION], rev_docs, batch_size=batch_size) if rev_docs else 0
        idxs = [
            create_index_safe(db[IC7_G6_REVERSE_COLLECTION], [("owner_person_id", ASCENDING)]),
            create_index_safe(db[IC7_G6_REVERSE_COLLECTION], [("liker_person_id", ASCENDING)]),
            create_index_safe(db[IC7_G6_REVERSE_COLLECTION], [("owner_person_id", ASCENDING), ("latest_creation_date", DESCENDING)]),
        ]
        created.append({"collection": IC7_G6_REVERSE_COLLECTION, "role": "owner_liker_reverse_index", "documents": n})
        indexes.extend({"collection": IC7_G6_REVERSE_COLLECTION, "index": x} for x in idxs if x)
        return created, indexes, warnings

    return created, indexes, warnings


# -----------------------------------------------------------------------------
# Generic template compilers
# -----------------------------------------------------------------------------

def compile_explicit_edge_collections(db, candidate_id: str, spec: dict, plan_row: pd.Series, batch_size: int) -> Tuple[List[dict], List[dict], List[str]]:
    """Compile generic G4-style explicit edge collections from relationship collections."""
    root_collection, root_pk, _ = get_root_collection_and_pk(spec, plan_row, db)
    rels = relationship_collections_from_spec(spec, db)
    created: List[dict] = []
    indexes: List[dict] = []
    warnings: List[str] = []
    if not rels:
        return created, indexes, ["No relationship collections available for explicit edge materialization."]

    for rel in rels:
        pair = infer_pair_fields(db, rel, root_pk=root_pk)
        if not pair:
            warnings.append(f"Could not infer endpoint fields for relationship collection {rel}.")
            continue
        src_field, tgt_field, method = pair
        out_name = f"phys_{safe_name(candidate_id, 32)}_edge_{safe_name(rel, 40)}"
        safe_drop_collection(db, out_name)

        def gen_docs() -> Iterable[dict]:
            for doc in db[rel].find({}, projection={src_field: 1, tgt_field: 1, "creation_date": 1}):
                src = normalize_id(doc.get(src_field))
                tgt = normalize_id(doc.get(tgt_field))
                if src is None or tgt is None:
                    continue
                yield {
                    "relationship_name": rel,
                    "source_id": src,
                    "target_id": tgt,
                    "source_field": src_field,
                    "target_field": tgt_field,
                    "creation_date": doc.get("creation_date"),
                    "original_id": str(doc.get("_id")),
                }

        n = insert_batches(db[out_name], gen_docs(), batch_size=batch_size)
        idxs = [
            create_index_safe(db[out_name], [("source_id", ASCENDING)]),
            create_index_safe(db[out_name], [("target_id", ASCENDING)]),
            create_index_safe(db[out_name], [("source_id", ASCENDING), ("creation_date", DESCENDING)]),
        ]
        created.append({"collection": out_name, "role": "generic_explicit_edge_collection", "relationship": rel, "documents": n, "endpoint_inference": method})
        indexes.extend({"collection": out_name, "index": x} for x in idxs if x)
    return created, indexes, warnings


def compile_reverse_indexes(db, candidate_id: str, spec: dict, plan_row: pd.Series, batch_size: int) -> Tuple[List[dict], List[dict], List[str]]:
    """Compile generic G6-style reverse indexes from relationship collections."""
    root_collection, root_pk, _ = get_root_collection_and_pk(spec, plan_row, db)
    rels = relationship_collections_from_spec(spec, db)
    created: List[dict] = []
    indexes: List[dict] = []
    warnings: List[str] = []
    if not rels:
        return created, indexes, ["No relationship collections available for reverse-index materialization."]

    for rel in rels:
        pair = infer_pair_fields(db, rel, root_pk=root_pk)
        if not pair:
            warnings.append(f"Could not infer endpoint fields for reverse index from {rel}.")
            continue
        src_field, tgt_field, method = pair
        out_name = f"phys_{safe_name(candidate_id, 32)}_rev_{safe_name(rel, 42)}"
        safe_drop_collection(db, out_name)

        def gen_docs() -> Iterable[dict]:
            for doc in db[rel].find({}, projection={src_field: 1, tgt_field: 1, "creation_date": 1}):
                src = normalize_id(doc.get(src_field))
                tgt = normalize_id(doc.get(tgt_field))
                if src is None or tgt is None:
                    continue
                yield {
                    "relationship_name": rel,
                    "lookup_id": tgt,
                    "referenced_id": src,
                    "lookup_field": tgt_field,
                    "referenced_field": src_field,
                    "creation_date": doc.get("creation_date"),
                    "original_id": str(doc.get("_id")),
                }

        n = insert_batches(db[out_name], gen_docs(), batch_size=batch_size)
        idxs = [
            create_index_safe(db[out_name], [("lookup_id", ASCENDING)]),
            create_index_safe(db[out_name], [("referenced_id", ASCENDING)]),
            create_index_safe(db[out_name], [("lookup_id", ASCENDING), ("creation_date", DESCENDING)]),
        ]
        created.append({"collection": out_name, "role": "generic_reverse_index", "relationship": rel, "documents": n, "endpoint_inference": method})
        indexes.extend({"collection": out_name, "index": x} for x in idxs if x)
    return created, indexes, warnings


def compile_root_summaries(db, candidate_id: str, spec: dict, plan_row: pd.Series, batch_size: int, max_items_per_relationship: int) -> Tuple[List[dict], List[dict], List[str]]:
    """Compile generic G3-style root summaries from relationship collections."""
    root_collection, root_pk, root_method = get_root_collection_and_pk(spec, plan_row, db)
    rels = relationship_collections_from_spec(spec, db)
    created: List[dict] = []
    indexes: List[dict] = []
    warnings: List[str] = []
    if not root_collection or not root_pk or not collection_exists(db, root_collection):
        return created, indexes, [f"Cannot compile root summary: root collection/pk unavailable ({root_collection}/{root_pk})."]
    if not rels:
        return created, indexes, ["No relationship collections available for root-summary materialization."]

    out_name = f"phys_{safe_name(candidate_id, 32)}_root_summary"
    safe_drop_collection(db, out_name)

    # Build per-root relationship arrays using each relationship collection.
    per_root: Dict[str, dict] = {}
    for root_doc in db[root_collection].find({}, {root_pk: 1}):
        rid = normalize_id(root_doc.get(root_pk))
        if rid is not None:
            per_root[rid] = {"root_id": rid, "root_collection": root_collection, "root_pk": root_pk, "relationship_summaries": {}}

    for rel in rels:
        fields = infer_id_fields(db, rel)
        if not fields:
            warnings.append(f"No ID fields found in {rel}; skipped for root summary.")
            continue
        # Possible root fields: exact root_pk, or common LDBC creator/owner variants.
        root_side_candidates = [root_pk]
        if root_pk == "person_id":
            root_side_candidates.extend(["creator_person_id", "person1_id", "person2_id"])
        root_side = next((f for f in root_side_candidates if f in fields), None)
        if root_side is None:
            warnings.append(f"Relationship {rel} does not expose root field {root_pk}; skipped for root summary.")
            continue
        other_fields = [f for f in fields if f != root_side]
        projection = {root_side: 1, **{f: 1 for f in other_fields[:4]}, "creation_date": 1}
        for doc in db[rel].find({}, projection=projection):
            rid = normalize_id(doc.get(root_side))
            if rid not in per_root:
                continue
            bucket = per_root[rid]["relationship_summaries"].setdefault(rel, [])
            if len(bucket) >= max_items_per_relationship:
                continue
            item = {"root_field": root_side, "creation_date": doc.get("creation_date")}
            for f in other_fields[:4]:
                item[f] = normalize_id(doc.get(f))
            bucket.append(item)

    docs = (v for v in per_root.values() if v.get("relationship_summaries"))
    n = insert_batches(db[out_name], docs, batch_size=batch_size)
    idx = create_index_safe(db[out_name], [("root_id", ASCENDING)])
    created.append({"collection": out_name, "role": "generic_root_summary", "documents": n, "root_collection": root_collection, "root_pk": root_pk, "root_inference": root_method})
    if idx:
        indexes.append({"collection": out_name, "index": idx})
    if n == 0:
        warnings.append("Root summary collection was created with zero documents.")
    return created, indexes, warnings


def compile_containment_embedding(db, candidate_id: str, spec: dict, plan_row: pd.Series, batch_size: int, reduced: bool) -> Tuple[List[dict], List[dict], List[str]]:
    """Compile generic G8/G9 containment-like embedded root collection.

    This is intentionally generic: it searches relationship collections whose names
    suggest containment and embeds directly related children under the inferred root.
    """
    root_collection, root_pk, root_method = get_root_collection_and_pk(spec, plan_row, db)
    rels = relationship_collections_from_spec(spec, db)
    containment_rels = [r for r in rels if any(h in r for h in CONTAINMENT_HINTS)]
    created: List[dict] = []
    indexes: List[dict] = []
    warnings: List[str] = []
    if not root_collection or not root_pk or not collection_exists(db, root_collection):
        return created, indexes, [f"Cannot compile containment embedding: root collection/pk unavailable ({root_collection}/{root_pk})."]
    if not containment_rels:
        return created, indexes, ["No containment-like relationship collections detected for embedding."]

    out_name = f"phys_{safe_name(candidate_id, 32)}_{'reduced' if reduced else 'rich'}_containment"
    safe_drop_collection(db, out_name)

    # Start with root documents.
    root_docs: Dict[str, dict] = {}
    for doc in db[root_collection].find({}):
        rid = normalize_id(doc.get(root_pk))
        if rid is None:
            continue
        base = dict(doc)
        base.pop("_id", None)
        base["_physical_materialization"] = "reduced_containment" if reduced else "rich_containment"
        base["embedded_relationships"] = {}
        root_docs[rid] = base

    for rel in containment_rels:
        pair = infer_pair_fields(db, rel, root_pk=root_pk)
        if not pair:
            warnings.append(f"Could not infer containment endpoints for {rel}.")
            continue
        src_field, tgt_field, method = pair
        # Prefer src as root side when root_pk matches; otherwise heuristic keeps pair order.
        root_field = src_field if src_field == root_pk else src_field
        child_field = tgt_field
        if root_field != root_pk and tgt_field == root_pk:
            root_field, child_field = tgt_field, src_field
        for edge in db[rel].find({}, {root_field: 1, child_field: 1, "creation_date": 1}):
            rid = normalize_id(edge.get(root_field))
            cid = normalize_id(edge.get(child_field))
            if rid not in root_docs or cid is None:
                continue
            arr = root_docs[rid]["embedded_relationships"].setdefault(rel, [])
            item = {"id": cid, "source_relationship": rel}
            if not reduced:
                item["creation_date"] = edge.get("creation_date")
                # Try to include child payload from a matching known collection.
                child_coll = None
                for coll, pk in COLLECTION_PKS.items():
                    if pk == child_field and collection_exists(db, coll):
                        child_coll = coll
                        break
                if child_coll:
                    child_doc = db[child_coll].find_one({child_field: cid})
                    if child_doc:
                        child_doc.pop("_id", None)
                        item["doc"] = child_doc
            arr.append(item)

    docs = (v for v in root_docs.values() if v.get("embedded_relationships"))
    n = insert_batches(db[out_name], docs, batch_size=batch_size)
    idx = create_index_safe(db[out_name], [(root_pk, ASCENDING)])
    created.append({"collection": out_name, "role": "generic_containment_embedding", "documents": n, "root_collection": root_collection, "root_pk": root_pk, "reduced": reduced, "root_inference": root_method})
    if idx:
        indexes.append({"collection": out_name, "index": idx})
    if n == 0:
        warnings.append("Containment embedding collection was created with zero documents.")
    return created, indexes, warnings


def validate_direct_template(db, candidate_id: str, spec: dict, plan_row: pd.Series, g_class: str) -> Tuple[List[dict], List[dict], List[str]]:
    """Validate templates whose physical shape is the canonical loaded structure."""
    rels = relationship_collections_from_spec(spec, db)
    root_collection, root_pk, _ = get_root_collection_and_pk(spec, plan_row, db)
    warnings = []
    if root_collection and not collection_exists(db, root_collection):
        warnings.append(f"Root collection {root_collection} not present.")
    physical_role = {
        "G0": "normalized_reference_baseline",
        "G1": "root_centered_reference_lookup",
        "G2": "descriptor_reference_layout",
        "G5": "root_bridge_reference_layout",
        "G7": "containment_reference_baseline",
    }.get(g_class, "canonical_loaded_layout")
    created = [{
        "collection": root_collection or "<unknown>",
        "role": physical_role,
        "relationships_available": rels,
        "documents": coll_stats(db, root_collection).get("count") if root_collection and collection_exists(db, root_collection) else None,
    }]
    indexes: List[dict] = []
    return created, indexes, warnings


def compile_physical_structures(db, candidate_id: str, official_id: str, spec: dict, plan_row: pd.Series, args: argparse.Namespace) -> Dict[str, Any]:
    g_class = str(spec.get("g_class") or plan_row.get("g_class") or "").upper()
    pattern = str(spec.get("mongodb_pattern") or plan_row.get("mongodb_pattern") or "")
    strategy = str(spec.get("document_strategy") or plan_row.get("document_strategy") or "")

    created: List[dict] = []
    indexes: List[dict] = []
    warnings: List[str] = []
    exact = False

    # Query-specific exact physical compilers have priority.
    if str(official_id).upper() == "IC7" and g_class in {"G3", "G4", "G6"}:
        c, i, w = compile_ic7_physical(db, g_class, args.batch_size)
        created.extend(c); indexes.extend(i); warnings.extend(w); exact = True

    elif g_class in {"G0", "G1", "G2", "G5", "G7"}:
        c, i, w = validate_direct_template(db, candidate_id, spec, plan_row, g_class)
        created.extend(c); indexes.extend(i); warnings.extend(w); exact = True

    elif g_class == "G3" or "summary" in pattern or "summary" in strategy:
        c, i, w = compile_root_summaries(db, candidate_id, spec, plan_row, args.batch_size, args.max_summary_items)
        created.extend(c); indexes.extend(i); warnings.extend(w); exact = False

    elif g_class == "G4" or "explicit_edge" in pattern or "edge_document" in strategy:
        c, i, w = compile_explicit_edge_collections(db, candidate_id, spec, plan_row, args.batch_size)
        created.extend(c); indexes.extend(i); warnings.extend(w); exact = False

    elif g_class == "G6" or "reverse" in pattern or "reverse" in strategy:
        c, i, w = compile_reverse_indexes(db, candidate_id, spec, plan_row, args.batch_size)
        created.extend(c); indexes.extend(i); warnings.extend(w); exact = False

    elif g_class in {"G8", "G9"} or "containment" in pattern:
        c, i, w = compile_containment_embedding(db, candidate_id, spec, plan_row, args.batch_size, reduced=(g_class == "G8"))
        created.extend(c); indexes.extend(i); warnings.extend(w); exact = False

    else:
        warnings.append(f"No physical compiler registered for g_class={g_class}, pattern={pattern}, strategy={strategy}.")

    if created and not any((x.get("documents") == 0) for x in created if isinstance(x.get("documents"), int)):
        status = "ready" if exact else "ready_generic"
        reason = ""
    elif created:
        status = "ready_with_warnings" if exact else "ready_generic_with_warnings"
        reason = "; ".join(warnings) if warnings else "One or more created structures contain zero documents."
    else:
        status = "unsupported"
        reason = "; ".join(warnings) if warnings else "No physical structures created."

    return {
        "materialization_status": status,
        "materialization_exactness": "query_specific" if exact else "generic_template",
        "physical_collections_created": created,
        "physical_indexes_created": indexes,
        "warnings": warnings,
        "unsupported_reason": reason if status == "unsupported" else "",
    }


# -----------------------------------------------------------------------------
# Main build pipeline
# -----------------------------------------------------------------------------

def materialize_all(args: argparse.Namespace) -> None:
    global GLOBAL_VERBOSE, GLOBAL_LOG_FILE_PATH
    GLOBAL_VERBOSE = bool(args.verbose)

    data_dir = Path(args.data_dir).expanduser().resolve()
    artifacts_dir = Path(args.artifacts_dir).expanduser().resolve()
    results_dir = Path(args.results_dir).expanduser().resolve()
    materialization_dir = results_dir / "materialization"
    ensure_dir(materialization_dir)

    GLOBAL_LOG_FILE_PATH = materialization_dir / "execution.log"
    if GLOBAL_LOG_FILE_PATH.exists() and not args.append_log:
        GLOBAL_LOG_FILE_PATH.unlink()

    write_log("LDBC SNB physical materialization builder started", force=True)
    write_log(f"Command: {' '.join(sys.argv)}", force=True)
    write_log("This script builds materializations only; it does not run p95 benchmark or query-plan analysis.", force=True)

    plan_df, specs_by_id, artifact_manifest = load_artifacts(artifacts_dir, args.execution_plan)
    selected_df = apply_filters(plan_df, args)
    if selected_df.empty:
        raise SystemExit("No selected rows after filters. Check --official-id, --g-class, --candidate-id, and --scale-label.")

    selected_path = materialization_dir / "selected_experiments_summary.csv"
    selected_df.to_csv(selected_path, index=False)
    write_log(f"Saved selected experiments: {selected_path}", force=True)
    write_log(f"Selected plan rows: {len(selected_df)}", force=True)
    write_log(f"Selected candidate IDs: {selected_df['candidate_id'].nunique() if 'candidate_id' in selected_df.columns else len(selected_df)}", force=True)

    t0 = time.perf_counter()
    data = ldbc_runner.load_ldbc_snb_data(data_dir=data_dir, row_limit=args.row_limit, verbose=args.verbose)
    load_data_seconds = time.perf_counter() - t0
    init_rows = []
    for name, df in data.items():
        init_rows.append({
            "scale_label": args.scale_label,
            "dataframe_name": name,
            "rows": int(len(df)) if hasattr(df, "__len__") else None,
            "columns": int(len(df.columns)) if hasattr(df, "columns") else None,
            "initialization_seconds_total": load_data_seconds,
            "status": "completed",
        })
    pd.DataFrame(init_rows).to_csv(materialization_dir / "scale_db_initialization_summary.csv", index=False)

    client = connect_mongo(args)
    client.admin.command("ping")
    write_log("MongoDB connection OK", force=True)

    manifest_rows: List[dict] = []
    validation_rows: List[dict] = []
    support_rows: List[dict] = []
    impossibility_rows: List[dict] = []
    manifest_json: List[dict] = []

    db_prefix = args.db_prefix or "ldbc_snb_phys"

    try:
        for idx, plan_row in selected_df.iterrows():
            candidate_id = str(plan_row.get("candidate_id"))
            official_id = str(plan_row.get("official_id"))
            query_name = str(plan_row.get("query_name"))
            spec = specs_by_id.get(candidate_id)
            if not spec:
                reason = f"Missing candidate spec for candidate_id={candidate_id}"
                write_log(reason, level="ERROR", force=True)
                impossibility_rows.append({
                    "candidate_id": candidate_id,
                    "official_id": official_id,
                    "query_name": query_name,
                    "materialization_status": "unsupported",
                    "unsupported_reason": reason,
                })
                continue

            g_class = str(spec.get("g_class") or plan_row.get("g_class") or "")
            pattern = str(spec.get("mongodb_pattern") or plan_row.get("mongodb_pattern") or "")
            strategy = str(spec.get("document_strategy") or plan_row.get("document_strategy") or "")
            benchmark_group = str(plan_row.get("benchmark_group") or spec.get("benchmark_group") or "")
            db_name = build_db_name(db_prefix, args.scale_label, candidate_id)

            write_log(f"[{idx + 1}/{len(selected_df)}] Materializing candidate={candidate_id} official_id={official_id} g={g_class} db={db_name}", force=True)
            t_candidate = time.perf_counter()
            base_status = "not_started"
            base_error = ""
            base_info: Dict[str, Any] = {}
            physical_info: Dict[str, Any] = {}

            try:
                base_info = ldbc_runner.materialize_candidate(
                    mongo_client=client,
                    db_name=db_name,
                    candidate_spec=spec,
                    data=data,
                    batch_size=args.batch_size,
                    force_rebuild=args.force_rebuild_db,
                    verbose=args.verbose,
                )
                base_status = "completed"

                physical_info = compile_physical_structures(client[db_name], candidate_id, official_id, spec, plan_row, args)
                status = physical_info["materialization_status"]
                unsupported_reason = physical_info.get("unsupported_reason", "")

            except Exception as exc:
                status = "failed"
                unsupported_reason = f"{type(exc).__name__}: {exc}"
                base_error = unsupported_reason
                write_log(traceback.format_exc(), level="ERROR", force=True)
                physical_info = {
                    "materialization_status": status,
                    "materialization_exactness": "failed",
                    "physical_collections_created": [],
                    "physical_indexes_created": [],
                    "warnings": [unsupported_reason],
                    "unsupported_reason": unsupported_reason,
                }

            elapsed = time.perf_counter() - t_candidate
            created = physical_info.get("physical_collections_created", [])
            indexes = physical_info.get("physical_indexes_created", [])
            warnings = physical_info.get("warnings", [])
            loaded_collections = base_info.get("loaded_collections", {}) if isinstance(base_info, dict) else {}

            row = {
                "scale_label": args.scale_label,
                "candidate_id": candidate_id,
                "official_id": official_id,
                "query_name": query_name,
                "benchmark_group": benchmark_group,
                "g_class": g_class,
                "mongodb_pattern": pattern,
                "document_strategy": strategy,
                "db_name": db_name,
                "base_materialization_status": base_status,
                "base_materialization_error": base_error,
                "materialization_status": status,
                "materialization_exactness": physical_info.get("materialization_exactness", ""),
                "physical_collections_created_json": json_dumps(created),
                "physical_indexes_created_json": json_dumps(indexes),
                "loaded_collections_json": json_dumps(loaded_collections),
                "warnings_json": json_dumps(warnings),
                "unsupported_reason": unsupported_reason,
                "materialization_seconds": elapsed,
                "ready_for_benchmark": status in {"ready", "ready_generic", "ready_with_warnings", "ready_generic_with_warnings"},
                "builder_script": Path(__file__).name,
            }
            manifest_rows.append(row)
            manifest_json.append({**row, "candidate_spec_excerpt": {k: spec.get(k) for k in ["root_entity", "root_collection", "root_pk", "accessed_entities", "relationships_used", "edge_collections", "reverse_indexes"]}})

            support_rows.append({
                "candidate_id": candidate_id,
                "official_id": official_id,
                "query_name": query_name,
                "g_class": g_class,
                "mongodb_pattern": pattern,
                "document_strategy": strategy,
                "materialization_status": status,
                "materialization_exactness": physical_info.get("materialization_exactness", ""),
                "n_physical_collections_created": len(created),
                "n_physical_indexes_created": len(indexes),
                "ready_for_benchmark": row["ready_for_benchmark"],
                "unsupported_reason": unsupported_reason,
            })

            if status in {"unsupported", "failed"}:
                impossibility_rows.append({
                    "candidate_id": candidate_id,
                    "official_id": official_id,
                    "query_name": query_name,
                    "g_class": g_class,
                    "mongodb_pattern": pattern,
                    "document_strategy": strategy,
                    "materialization_status": status,
                    "unsupported_reason": unsupported_reason,
                })

            # Validate base and physical collections.
            for cname in list(loaded_collections.keys()) + [c.get("collection") for c in created if c.get("collection")]:
                if cname and collection_exists(client[db_name], cname):
                    st = coll_stats(client[db_name], cname)
                    validation_rows.append({
                        "candidate_id": candidate_id,
                        "official_id": official_id,
                        "query_name": query_name,
                        "g_class": g_class,
                        "db_name": db_name,
                        **st,
                    })

            write_log(f"Candidate {candidate_id} materialization_status={status} elapsed={elapsed:.2f}s", force=True)

    finally:
        try:
            client.close()
        except Exception:
            pass

    manifest_df = pd.DataFrame(manifest_rows)
    support_df = pd.DataFrame(support_rows)
    imposs_df = pd.DataFrame(impossibility_rows)
    validation_df = pd.DataFrame(validation_rows)

    manifest_csv = materialization_dir / "physical_materialization_manifest.csv"
    manifest_json_path = materialization_dir / "physical_materialization_manifest.json"
    support_csv = materialization_dir / "physical_support_matrix.csv"
    imposs_csv = materialization_dir / "physical_impossibility_report.csv"
    validation_csv = materialization_dir / "materialization_validation_summary.csv"

    manifest_df.to_csv(manifest_csv, index=False)
    support_df.to_csv(support_csv, index=False)
    imposs_df.to_csv(imposs_csv, index=False)
    validation_df.to_csv(validation_csv, index=False)
    with open(manifest_json_path, "w", encoding="utf-8") as f:
        json.dump(to_jsonable(manifest_json), f, ensure_ascii=False, indent=2)

    run_manifest = {
        "created_at": utc_now_iso(),
        "script": Path(__file__).name,
        "command": " ".join(sys.argv),
        "data_dir": str(data_dir),
        "artifacts_dir": str(artifacts_dir),
        "results_dir": str(results_dir),
        "scale_label": args.scale_label,
        "execution_plan": args.execution_plan,
        "n_selected_rows": int(len(selected_df)),
        "n_manifest_rows": int(len(manifest_df)),
        "n_ready": int(manifest_df["ready_for_benchmark"].sum()) if not manifest_df.empty else 0,
        "n_unsupported": int(len(imposs_df)),
        "artifact_manifest": artifact_manifest,
    }
    with open(materialization_dir / "benchmark_run_manifest.json", "w", encoding="utf-8") as f:
        json.dump(to_jsonable(run_manifest), f, ensure_ascii=False, indent=2)

    write_readme(materialization_dir, args, manifest_df, support_df, imposs_df)

    write_log(f"Saved physical materialization manifest: {manifest_csv}", force=True)
    write_log(f"Saved physical support matrix: {support_csv}", force=True)
    write_log(f"Saved physical impossibility report: {imposs_csv}", force=True)
    write_log(f"Saved materialization validation summary: {validation_csv}", force=True)
    write_log("Done.", force=True)


def write_readme(materialization_dir: Path, args: argparse.Namespace, manifest_df: pd.DataFrame, support_df: pd.DataFrame, imposs_df: pd.DataFrame) -> None:
    ready = int(manifest_df["ready_for_benchmark"].sum()) if not manifest_df.empty and "ready_for_benchmark" in manifest_df.columns else 0
    total = int(len(manifest_df))
    unsupported = int(len(imposs_df))
    counts = {}
    if not manifest_df.empty and "materialization_status" in manifest_df.columns:
        counts = manifest_df["materialization_status"].value_counts(dropna=False).to_dict()
    text = f"""# LDBC SNB physical materialization build

This folder contains the physical materialization manifest generated before running the physical-materialization-aware benchmark.

## Scope

- Scale label: `{args.scale_label}`
- Data directory: `{args.data_dir}`
- Artifacts directory: `{args.artifacts_dir}`
- Execution plan: `{args.execution_plan}`
- Selected candidates: {total}
- Ready for benchmark: {ready}
- Unsupported/failed: {unsupported}

## Methodological rule

A candidate should enter the physical benchmark only if it appears in `physical_materialization_manifest.csv` with `ready_for_benchmark = True`.
Unsupported candidates are listed in `physical_impossibility_report.csv` with the reason.

## Output files

- `physical_materialization_manifest.csv`: candidate-level manifest used by the benchmark runner.
- `physical_materialization_manifest.json`: JSON version with candidate-spec excerpts.
- `physical_support_matrix.csv`: compact matrix of physical support by candidate.
- `physical_impossibility_report.csv`: candidates that could not be materialized and why.
- `materialization_validation_summary.csv`: collection-level stats after materialization.
- `scale_db_initialization_summary.csv`: loaded LDBC dataframes.
- `selected_experiments_summary.csv`: artifact plan rows selected for this build.
- `execution.log`: full execution log.

## Status counts

```text
{json.dumps(counts, indent=2, ensure_ascii=False)}
```

## Next step

Run the physical benchmark/query-plan script from this manifest, not directly from the original execution plan. The benchmark script must not run candidates absent from this manifest or marked unsupported.
"""
    with open(materialization_dir / "README_materialization.md", "w", encoding="utf-8") as f:
        f.write(text)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build physical MongoDB materializations for LDBC SNB SchemaLens candidates.")

    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--artifacts-dir", required=True)
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--execution-plan", default="benchmark_execution_plan.csv")
    parser.add_argument("--scale-label", required=True)

    parser.add_argument("--mongo-host", default="127.0.0.1")
    parser.add_argument("--mongo-port", type=int, default=27017)
    parser.add_argument("--mongo-username", default=None)
    parser.add_argument("--mongo-password", default=None)
    parser.add_argument("--mongo-auth-source", default="admin")
    parser.add_argument("--server-selection-timeout-ms", type=int, default=10000)
    parser.add_argument("--connect-timeout-ms", type=int, default=10000)
    parser.add_argument("--socket-timeout-ms", type=int, default=600000)

    parser.add_argument("--candidate-id", nargs="*", default=None)
    parser.add_argument("--official-id", nargs="*", default=None)
    parser.add_argument("--query-name", nargs="*", default=None)
    parser.add_argument("--g-class", nargs="*", default=None)
    parser.add_argument("--benchmark-group", nargs="*", default=None)
    parser.add_argument("--max-candidates", type=int, default=None)

    parser.add_argument("--db-prefix", default="ldbc_snb_phys")
    parser.add_argument("--batch-size", type=int, default=100000)
    parser.add_argument("--row-limit", type=int, default=None)
    parser.add_argument("--force-rebuild-db", action="store_true")
    parser.add_argument("--max-summary-items", type=int, default=100, help="Max relationship items stored per root/relation for generic G3 summaries.")

    parser.add_argument("--append-log", action="store_true")
    parser.add_argument("--verbose", action="store_true")

    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    materialize_all(args)


if __name__ == "__main__":
    main()
