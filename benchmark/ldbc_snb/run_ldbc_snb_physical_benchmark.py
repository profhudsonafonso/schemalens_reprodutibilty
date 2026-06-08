#!/usr/bin/env python3
import argparse
import csv
import json
import logging
import math
import os
import statistics
import subprocess
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pymongo import MongoClient


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def setup_logger(results_dir: Path):
    results_dir.mkdir(parents=True, exist_ok=True)
    log_path = results_dir / "execution.log"

    logger = logging.getLogger("ldbc_physical")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

    fh = logging.FileHandler(log_path)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger


def run_shell(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
        return out.strip()
    except Exception as e:
        return f"ERROR: {e}"


class ResourceMonitor:
    def __init__(self, out_csv, container_name=None, mongo_data_dir=None, interval_sec=5, logger=None):
        self.out_csv = Path(out_csv)
        self.container_name = container_name
        self.mongo_data_dir = mongo_data_dir
        self.interval_sec = interval_sec
        self.logger = logger
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.out_csv.parent.mkdir(parents=True, exist_ok=True)
        with self.out_csv.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "container",
                "running",
                "status",
                "exit_code",
                "oom_killed",
                "mem_free_mb",
                "mem_used_mb",
                "mem_total_mb",
                "mem_percent",
                "disk_free_gb",
                "disk_used_gb",
                "docker_cpu",
                "docker_mem",
                "docker_mem_percent",
                "docker_block_io",
                "docker_pids",
            ])

        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        if self.logger:
            self.logger.info(f"Resource monitor started: {self.out_csv}")

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=self.interval_sec + 2)
        if self.logger:
            self.logger.info("Resource monitor stopped")

    def _loop(self):
        while not self.stop_event.is_set():
            try:
                row = self.sample()
                with self.out_csv.open("a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(row)
            except Exception:
                if self.logger:
                    self.logger.warning("Resource monitor sample failed:\n" + traceback.format_exc())
            self.stop_event.wait(self.interval_sec)

    def sample(self):
        ts = datetime.now().astimezone().isoformat(timespec="seconds")

        # system memory
        mem_free = mem_used = mem_total = mem_percent = ""
        free_out = run_shell("free -m | awk '/Mem:/ {print $4\",\"$3\",\"$2}'")
        try:
            mem_free, mem_used, mem_total = [float(x) for x in free_out.split(",")]
            mem_percent = round((mem_used / mem_total) * 100, 2) if mem_total else ""
        except Exception:
            pass

        # disk
        disk_free = disk_used = ""
        if self.mongo_data_dir:
            df_out = run_shell(f"df -BG {self.mongo_data_dir} | awk 'NR==2 {{gsub(\"G\", \"\", $3); gsub(\"G\", \"\", $4); print $4\",\"$3}}'")
            try:
                disk_free, disk_used = [float(x) for x in df_out.split(",")]
            except Exception:
                pass

        running = status = exit_code = oom_killed = ""
        docker_cpu = docker_mem = docker_mem_percent = docker_block_io = docker_pids = ""

        if self.container_name:
            inspect = run_shell(
                f"docker inspect -f '{{{{.State.Running}}}},{{{{.State.Status}}}},{{{{.State.ExitCode}}}},{{{{.State.OOMKilled}}}}' {self.container_name}"
            )
            try:
                running, status, exit_code, oom_killed = inspect.split(",")
            except Exception:
                pass

            stats = run_shell(
                f"docker stats --no-stream --format '{{{{.CPUPerc}}}},{{{{.MemUsage}}}},{{{{.MemPerc}}}},{{{{.BlockIO}}}},{{{{.PIDs}}}}' {self.container_name}"
            )
            try:
                docker_cpu, docker_mem, docker_mem_percent, docker_block_io, docker_pids = stats.split(",", 4)
            except Exception:
                pass

        return [
            ts,
            self.container_name or "",
            running,
            status,
            exit_code,
            oom_killed,
            mem_free,
            mem_used,
            mem_total,
            mem_percent,
            disk_free,
            disk_used,
            docker_cpu,
            docker_mem,
            docker_mem_percent,
            docker_block_io,
            docker_pids,
        ]


def percentile(values, p):
    if not values:
        return None
    vals = sorted(values)
    if len(vals) == 1:
        return vals[0]
    k = (len(vals) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return vals[int(k)]
    return vals[f] * (c - k) + vals[c] * (k - f)


def get_candidate_manifest(args, logger):
    if args.materialize_first:
        if not args.build_script:
            raise ValueError("--build-script is required with --materialize-first")
        if not args.data_dir:
            raise ValueError("--data-dir is required with --materialize-first")
        if not args.artifacts_dir:
            raise ValueError("--artifacts-dir is required with --materialize-first")

        materialization_dir = Path(args.results_dir) / "materialization"
        materialization_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "python", args.build_script,
            "--mongo-host", args.mongo_host,
            "--mongo-port", str(args.mongo_port),
            "--mongo-username", args.mongo_username,
            "--mongo-password", args.mongo_password,
            "--mongo-auth-source", args.mongo_auth_source,
            "--data-dir", args.data_dir,
            "--artifacts-dir", args.artifacts_dir,
            "--results-dir", str(materialization_dir),
            "--execution-plan", args.execution_plan,
            "--scale-label", args.scale_label,
            "--official-id", args.official_id,
            "--batch-size", str(args.batch_size),
            "--force-rebuild-db",
            "--verbose",
        ]

        logger.info("Materialization command:")
        logger.info(" ".join(cmd))
        subprocess.run(cmd, check=True)

        manifest_path = materialization_dir / "materialization" / "physical_materialization_manifest.csv"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Materialization manifest not found: {manifest_path}")
        return manifest_path

    if not args.manifest:
        raise ValueError("--manifest is required unless --materialize-first is used")
    return Path(args.manifest)


def connect_mongo(args):
    return MongoClient(
        host=args.mongo_host,
        port=args.mongo_port,
        username=args.mongo_username,
        password=args.mongo_password,
        authSource=args.mongo_auth_source,
        serverSelectionTimeoutMS=10000,
        socketTimeoutMS=600000,
        connectTimeoutMS=10000,
    )


def normalize_id(v):
    """Preserve LDBC SNB IDs as strings because CSV-loaded MongoDB fields are string typed."""
    if v is None:
        return None
    return str(v)


def get_doc_value(doc, names, default=None):
    if not doc:
        return default
    for n in names:
        if n in doc:
            return doc[n]
    return default



def build_parameter_pools(client, manifest, sample_size, logger):
    """
    Build query-specific parameter pools for the initial physical benchmark.
    LDBC SNB IDs are stored as strings in MongoDB, so we preserve string values.
    """
    pools = {}

    for official_id, qdf in manifest.groupby("official_id"):
        official_id = str(official_id)
        db = client[qdf.iloc[0]["db_name"]]
        existing = set(db.list_collection_names())
        vals = []

        if official_id in {"IS1", "IS2", "IS3"}:
            if "persons" in existing:
                vals = [
                    normalize_id(d.get("person_id"))
                    for d in db.persons.find({}, {"person_id": 1}).limit(sample_size * 5)
                    if d.get("person_id") is not None
                ]

        elif official_id in {"IS4", "IS5", "IS6"}:
            # Use real message ids. Prefer posts, then comments.
            if "posts" in existing:
                vals += [
                    normalize_id(d.get("post_id"))
                    for d in db.posts.find({}, {"post_id": 1}).limit(sample_size * 3)
                    if d.get("post_id") is not None
                ]
            if "comments" in existing:
                vals += [
                    normalize_id(d.get("comment_id"))
                    for d in db.comments.find({}, {"comment_id": 1}).limit(sample_size * 3)
                    if d.get("comment_id") is not None
                ]

        elif official_id == "IS7":
            # Need a message id with actual replies.
            if "comment_reply_of_post" in existing:
                vals += [
                    normalize_id(d.get("post_id"))
                    for d in db.comment_reply_of_post.find({}, {"post_id": 1}).limit(sample_size * 5)
                    if d.get("post_id") is not None
                ]

            if "comments" in existing:
                vals += [
                    normalize_id(d.get("reply_post_id"))
                    for d in db.comments.find(
                        {"reply_post_id": {"$nin": [None, "", float("nan")]}},
                        {"reply_post_id": 1}
                    ).limit(sample_size * 5)
                    if d.get("reply_post_id") is not None
                ]
                vals += [
                    normalize_id(d.get("reply_comment_id"))
                    for d in db.comments.find(
                        {"reply_comment_id": {"$nin": [None, "", float("nan")]}},
                        {"reply_comment_id": 1}
                    ).limit(sample_size * 5)
                    if d.get("reply_comment_id") is not None
                ]

            if "comment_reply_of_comment" in existing:
                for field in ["parent_comment_id", "comment_id"]:
                    vals += [
                        normalize_id(d.get(field))
                        for d in db.comment_reply_of_comment.find({}, {field: 1}).limit(sample_size * 5)
                        if d.get(field) is not None
                    ]

        elif official_id == "IC7":
            vals = get_owner_pool(client, qdf, sample_size, logger)

        # Deduplicate preserving order.
        clean = []
        for x in vals:
            if x is None:
                continue
            sx = normalize_id(x)
            if sx.lower() == "nan":
                continue
            if sx not in clean:
                clean.append(sx)

        pools[official_id] = clean[:sample_size]
        logger.info(f"Parameter pool {official_id}: {pools[official_id]}")

    return pools


def choose_parameter_for_run(parameter_pools, official_id, run_idx):
    pool = parameter_pools.get(str(official_id), [])
    if not pool:
        return None
    return pool[run_idx % len(pool)]



def get_owner_pool(client, manifest, sample_size, logger):
    # Prefer IC7 derived collections, because they guarantee useful owner ids.
    owner_ids = []

    for _, row in manifest.iterrows():
        db = client[row["db_name"]]
        g = row["g_class"]

        if g == "G3" and "ic7_g3_person_recent_liker_summary" in db.list_collection_names():
            owner_ids += [
                d.get("owner_person_id")
                for d in db.ic7_g3_person_recent_liker_summary.find({}, {"owner_person_id": 1}).limit(sample_size * 3)
            ]

        if g == "G4" and "ic7_g4_explicit_like_edges" in db.list_collection_names():
            owner_ids += db.ic7_g4_explicit_like_edges.distinct("owner_person_id")[: sample_size * 3]

        if g == "G6" and "ic7_g6_owner_liker_reverse_index" in db.list_collection_names():
            owner_ids += db.ic7_g6_owner_liker_reverse_index.distinct("owner_person_id")[: sample_size * 3]

    owner_ids = [normalize_id(x) for x in owner_ids if x is not None]
    seen = []
    for x in owner_ids:
        if x not in seen:
            seen.append(x)

    if len(seen) >= sample_size:
        pool = seen[:sample_size]
        logger.info(f"IC7 parameter pool from derived collections: {pool}")
        return pool

    # Fallback: owners with posts/comments.
    row = manifest.iloc[0]
    db = client[row["db_name"]]
    fallback = []
    if "posts" in db.list_collection_names():
        fallback += db.posts.distinct("creator_person_id")[: sample_size * 3]
    if "comments" in db.list_collection_names():
        fallback += db.comments.distinct("creator_person_id")[: sample_size * 3]

    fallback = [normalize_id(x) for x in fallback if x is not None]
    pool = []
    for x in fallback:
        if x not in pool:
            pool.append(x)
    pool = pool[:sample_size]
    logger.info(f"IC7 parameter pool from fallback base collections: {pool}")
    return pool


def fetch_persons(db, liker_ids):
    if not liker_ids:
        return {}
    docs = list(db.persons.find({"person_id": {"$in": liker_ids}}, {"_id": 0}).limit(len(liker_ids) + 5))
    return {d.get("person_id"): d for d in docs}


def fetch_knows(db, owner_id, liker_ids):
    if not liker_ids:
        return set()
    rows = list(db.person_knows_person.find({
        "$or": [
            {"person1_id": owner_id, "person2_id": {"$in": liker_ids}},
            {"person2_id": owner_id, "person1_id": {"$in": liker_ids}},
        ]
    }, {"_id": 0, "person1_id": 1, "person2_id": 1}))
    known = set()
    for r in rows:
        p1 = r.get("person1_id")
        p2 = r.get("person2_id")
        if p1 == owner_id:
            known.add(p2)
        elif p2 == owner_id:
            known.add(p1)
    return known



def first_collection(db, names):
    existing = set(db.list_collection_names())
    for n in names:
        if n in existing:
            return n
    return None


def find_one_by_any_id(db, collection, id_fields, value):
    filters = [{f: value} for f in id_fields]
    if not filters:
        return None
    return db[collection].find_one({"$or": filters}, {"_id": 0})


def find_many_by_any_id(db, collection, id_fields, value, limit=20):
    filters = [{f: value} for f in id_fields]
    if not filters:
        return []
    return list(db[collection].find({"$or": filters}, {"_id": 0}).limit(limit))


def run_is_generic(db, official_id, param_id, limit=20):
    """
    Conservative physical read path for LDBC short-read style queries.
    This is intentionally generic for the first multi-query validation phase.
    It uses the collections physically present in the candidate database.

    The goal here is to validate the multi-query runner infrastructure before
    adding highly specialized physical paths for each IS query.
    """
    oid = normalize_id(param_id)

    if official_id == "IS1":
        # Person profile by id
        doc = find_one_by_any_id(db, "persons", ["person_id", "id"], oid)
        return [doc] if doc else []

    if official_id == "IS2":
        # Recent messages of a person: posts/comments by creator.
        results = []
        if "posts" in db.list_collection_names():
            results += list(db.posts.find(
                {"creator_person_id": oid},
                {"_id": 0}
            ).sort("creation_date", -1).limit(limit))
        if "comments" in db.list_collection_names():
            results += list(db.comments.find(
                {"creator_person_id": oid},
                {"_id": 0}
            ).sort("creation_date", -1).limit(limit))
        return sorted(results, key=lambda x: str(x.get("creation_date", "")), reverse=True)[:limit]

    if official_id == "IS3":
        # Friends/knows of a person.
        if "person_knows_person" not in db.list_collection_names():
            return []
        rows = list(db.person_knows_person.find({
            "$or": [
                {"person1_id": oid},
                {"person2_id": oid},
            ]
        }, {"_id": 0}).limit(limit))
        return rows

    if official_id == "IS4":
        # Message by id, post or comment.
        results = []
        if "posts" in db.list_collection_names():
            doc = find_one_by_any_id(db, "posts", ["post_id", "message_id", "id"], oid)
            if doc:
                results.append(doc)
        if "comments" in db.list_collection_names():
            doc = find_one_by_any_id(db, "comments", ["comment_id", "message_id", "id"], oid)
            if doc:
                results.append(doc)
        return results[:limit]

    if official_id == "IS5":
        # Creator of a message. Find message then creator person.
        msg = None
        if "posts" in db.list_collection_names():
            msg = find_one_by_any_id(db, "posts", ["post_id", "message_id", "id"], oid)
        if msg is None and "comments" in db.list_collection_names():
            msg = find_one_by_any_id(db, "comments", ["comment_id", "message_id", "id"], oid)
        if not msg:
            return []
        creator_id = normalize_id(msg.get("creator_person_id"))
        if creator_id is None:
            return [msg]
        person = find_one_by_any_id(db, "persons", ["person_id", "id"], creator_id)
        return [{"message": msg, "creator": person}]

    if official_id == "IS6":
        # Forum or tags of a message. Conservative: return message plus available post/comment tags.
        results = []
        if "posts" in db.list_collection_names():
            msg = find_one_by_any_id(db, "posts", ["post_id", "message_id", "id"], oid)
            if msg:
                results.append({"message": msg})
                if "post_has_tag" in db.list_collection_names():
                    tags = list(db.post_has_tag.find({"post_id": oid}, {"_id": 0}).limit(limit))
                    results.append({"post_has_tag": tags})
        if "comments" in db.list_collection_names():
            msg = find_one_by_any_id(db, "comments", ["comment_id", "message_id", "id"], oid)
            if msg:
                results.append({"message": msg})
                if "comment_has_tag" in db.list_collection_names():
                    tags = list(db.comment_has_tag.find({"comment_id": oid}, {"_id": 0}).limit(limit))
                    results.append({"comment_has_tag": tags})
        return results[:limit]

    if official_id == "IS7":
        # Replies of a message.
        results = []
        if "comment_reply_of_post" in db.list_collection_names():
            results += list(db.comment_reply_of_post.find({"post_id": oid}, {"_id": 0}).limit(limit))
        if "comment_reply_of_comment" in db.list_collection_names():
            # Real materialized fields: parent_comment_id -> child comment_id.
            results += list(db.comment_reply_of_comment.find({"parent_comment_id": oid}, {"_id": 0}).limit(limit))
            results += list(db.comment_reply_of_comment.find({"comment_id": oid}, {"_id": 0}).limit(limit))
        # Fallback: direct fields in comments
        if not results and "comments" in db.list_collection_names():
            results += list(db.comments.find({
                "$or": [
                    {"reply_post_id": oid},
                    {"reply_comment_id": oid},
                ]
            }, {"_id": 0}).limit(limit))
        return results[:limit]

    raise ValueError(f"Generic IS runner not implemented for {official_id}")


def explain_is_generic(db, official_id, param_id, limit=20):
    oid = normalize_id(param_id)
    comps = []

    def add(name, collection, filter_doc, projection=None, sort=None, limit_value=None):
        if collection not in db.list_collection_names():
            return
        exp = make_explain_find(db, collection, filter_doc, projection, sort, limit_value)
        stats = explain_stats(exp)
        comps.append({
            "component_name": name,
            "operation_kind": "find",
            "collection_name": collection,
            "filter_json": json.dumps(filter_doc, default=str),
            **stats,
            "raw_explain": exp,
        })

    if official_id == "IS1":
        add("is1_person_by_id", "persons", {"person_id": oid}, None, None, 1)

    elif official_id == "IS2":
        add("is2_posts_by_creator", "posts", {"creator_person_id": oid}, None, [("creation_date", -1)], limit)
        add("is2_comments_by_creator", "comments", {"creator_person_id": oid}, None, [("creation_date", -1)], limit)

    elif official_id == "IS3":
        add("is3_knows_person1", "person_knows_person", {"person1_id": oid}, None, None, limit)
        add("is3_knows_person2", "person_knows_person", {"person2_id": oid}, None, None, limit)

    elif official_id == "IS4":
        add("is4_post_by_id", "posts", {"post_id": oid}, None, None, 1)
        add("is4_comment_by_id", "comments", {"comment_id": oid}, None, None, 1)

    elif official_id == "IS5":
        add("is5_post_by_id", "posts", {"post_id": oid}, None, None, 1)
        add("is5_comment_by_id", "comments", {"comment_id": oid}, None, None, 1)

    elif official_id == "IS6":
        add("is6_post_by_id", "posts", {"post_id": oid}, None, None, 1)
        add("is6_comment_by_id", "comments", {"comment_id": oid}, None, None, 1)
        add("is6_post_tags", "post_has_tag", {"post_id": oid}, None, None, limit)
        add("is6_comment_tags", "comment_has_tag", {"comment_id": oid}, None, None, limit)

    elif official_id == "IS7":
        add("is7_replies_of_post", "comment_reply_of_post", {"post_id": oid}, None, None, limit)
        add("is7_replies_of_comment_parent", "comment_reply_of_comment", {"parent_comment_id": oid}, None, None, limit)
        add("is7_replies_of_comment_child", "comment_reply_of_comment", {"comment_id": oid}, None, None, limit)
        add("is7_comments_reply_fields", "comments", {"$or": [{"reply_post_id": oid}, {"reply_comment_id": oid}]}, None, None, limit)

    else:
        raise ValueError(f"Explain IS runner not implemented for {official_id}")

    return comps



def run_ic7_g0(db, owner_id, limit=20):
    posts = list(db.posts.find(
        {"creator_person_id": owner_id},
        {"_id": 0, "post_id": 1, "creation_date": 1}
    ).sort("creation_date", -1).limit(limit))

    comments = list(db.comments.find(
        {"creator_person_id": owner_id},
        {"_id": 0, "comment_id": 1, "creation_date": 1}
    ).sort("creation_date", -1).limit(limit))

    post_ids = [p.get("post_id") for p in posts if p.get("post_id") is not None]
    comment_ids = [c.get("comment_id") for c in comments if c.get("comment_id") is not None]

    post_likes = []
    comment_likes = []

    if post_ids:
        post_likes = list(db.person_likes_post.find(
            {"post_id": {"$in": post_ids}},
            {"_id": 0}
        ).sort("creation_date", -1).limit(limit))

    if comment_ids:
        comment_likes = list(db.person_likes_comment.find(
            {"comment_id": {"$in": comment_ids}},
            {"_id": 0}
        ).sort("creation_date", -1).limit(limit))

    events = []
    for r in post_likes:
        events.append({
            "liker_person_id": r.get("person_id"),
            "message_id": r.get("post_id"),
            "message_type": "post",
            "creation_date": r.get("creation_date"),
        })
    for r in comment_likes:
        events.append({
            "liker_person_id": r.get("person_id"),
            "message_id": r.get("comment_id"),
            "message_type": "comment",
            "creation_date": r.get("creation_date"),
        })

    events = [e for e in events if e.get("liker_person_id") is not None]
    events = sorted(events, key=lambda x: str(x.get("creation_date", "")), reverse=True)[:limit]

    liker_ids = list(dict.fromkeys([normalize_id(e["liker_person_id"]) for e in events]))
    persons = fetch_persons(db, liker_ids)
    known = fetch_knows(db, owner_id, liker_ids)

    return [
        {
            **e,
            "liker_person": persons.get(normalize_id(e["liker_person_id"]), {}),
            "is_known": normalize_id(e["liker_person_id"]) in known,
        }
        for e in events
    ]


def run_ic7_g3(db, owner_id, limit=20):
    col = db.ic7_g3_person_recent_liker_summary
    doc = col.find_one({"owner_person_id": owner_id}, {"_id": 0})

    if not doc:
        return []

    # G3 physically materializes an owner-level summary. It already embeds
    # recent_likers with person attributes and recent_messages with message-level
    # like evidence. Therefore, the physical G3 access path should not fetch the
    # liker document from persons again.
    recent_likers = doc.get("recent_likers") or []
    recent_messages = doc.get("recent_messages") or []

    liker_person_by_id = {}
    for pdoc in recent_likers:
        if isinstance(pdoc, dict):
            pid = normalize_id(get_doc_value(pdoc, ["person_id", "liker_person_id", "liker_id"]))
            if pid is not None:
                liker_person_by_id[pid] = pdoc

    events = []

    if recent_messages:
        for r in recent_messages:
            if not isinstance(r, dict):
                continue
            liker_id = normalize_id(get_doc_value(r, ["liker_person_id", "person_id", "liker_id"]))
            events.append({
                "liker_person_id": liker_id,
                "message_id": get_doc_value(r, ["message_id", "latest_message_id", "post_id", "comment_id"]),
                "message_type": get_doc_value(r, ["message_type", "latest_message_type"]),
                "creation_date": get_doc_value(r, ["creation_date", "latest_creation_date", "latest_like_date"]),
                "liker_person": liker_person_by_id.get(liker_id, {}),
            })
    else:
        # Fallback if a generic G3 summary only stores recent_likers.
        for r in recent_likers:
            if isinstance(r, dict):
                liker_id = normalize_id(get_doc_value(r, ["person_id", "liker_person_id", "liker_id"]))
                events.append({
                    "liker_person_id": liker_id,
                    "liker_person": r,
                })
            else:
                events.append({
                    "liker_person_id": normalize_id(r),
                    "liker_person": {},
                })

    events = [e for e in events if e.get("liker_person_id") is not None][:limit]
    liker_ids = list(dict.fromkeys([normalize_id(e["liker_person_id"]) for e in events]))
    known = fetch_knows(db, owner_id, liker_ids)

    return [
        {
            **e,
            "is_known": normalize_id(e["liker_person_id"]) in known,
        }
        for e in events
    ]


def run_ic7_g4(db, owner_id, limit=20):
    rows = list(db.ic7_g4_explicit_like_edges.find(
        {"owner_person_id": owner_id},
        {"_id": 0}
    ).sort("creation_date", -1).limit(limit))

    events = []
    for r in rows:
        events.append({
            "liker_person_id": get_doc_value(r, ["liker_person_id", "person_id", "liker_id"]),
            "message_id": get_doc_value(r, ["message_id", "post_id", "comment_id"]),
            "message_type": get_doc_value(r, ["message_type"]),
            "creation_date": get_doc_value(r, ["creation_date", "like_creation_date"]),
        })

    events = [e for e in events if e.get("liker_person_id") is not None]
    liker_ids = list(dict.fromkeys([normalize_id(e["liker_person_id"]) for e in events]))
    persons = fetch_persons(db, liker_ids)
    known = fetch_knows(db, owner_id, liker_ids)

    return [
        {
            **e,
            "liker_person": persons.get(normalize_id(e["liker_person_id"]), {}),
            "is_known": normalize_id(e["liker_person_id"]) in known,
        }
        for e in events
    ]


def run_ic7_g6(db, owner_id, limit=20):
    rows = list(db.ic7_g6_owner_liker_reverse_index.find(
        {"owner_person_id": owner_id},
        {"_id": 0}
    ).sort("latest_creation_date", -1).limit(limit))

    events = []
    for r in rows:
        events.append({
            "liker_person_id": get_doc_value(r, ["liker_person_id", "person_id", "liker_id"]),
            "message_id": get_doc_value(r, ["latest_message_id", "message_id", "post_id", "comment_id"]),
            "message_type": get_doc_value(r, ["latest_message_type", "message_type"]),
            "creation_date": get_doc_value(r, ["latest_creation_date", "creation_date"]),
            "like_count": get_doc_value(r, ["like_count"]),
        })

    events = [e for e in events if e.get("liker_person_id") is not None][:limit]
    liker_ids = list(dict.fromkeys([normalize_id(e["liker_person_id"]) for e in events]))
    persons = fetch_persons(db, liker_ids)
    known = fetch_knows(db, owner_id, liker_ids)

    return [
        {
            **e,
            "liker_person": persons.get(normalize_id(e["liker_person_id"]), {}),
            "is_known": normalize_id(e["liker_person_id"]) in known,
        }
        for e in events
    ]


def run_physical_candidate(db, official_id, g_class, param_id, limit=20):
    if official_id == "IC7":
        if g_class == "G0":
            return run_ic7_g0(db, param_id, limit)
        if g_class == "G3":
            return run_ic7_g3(db, param_id, limit)
        if g_class == "G4":
            return run_ic7_g4(db, param_id, limit)
        if g_class == "G6":
            return run_ic7_g6(db, param_id, limit)
        raise ValueError(f"IC7 physical runner not implemented for g_class={g_class}")

    if official_id.startswith("IS"):
        return run_is_generic(db, official_id, param_id, limit)

    raise ValueError(f"Physical runner not implemented for official_id={official_id} g_class={g_class}")


def choose_explain_param(client, manifest, official_id, param_pool, limit, logger):
    """Choose one IC7 owner that returns non-empty results for all IC7 candidates when possible."""
    for owner_id in param_pool:
        ok_all = True
        counts = {}
        for _, row in manifest.iterrows():
            db = client[row["db_name"]]
            g_class = row["g_class"]
            try:
                n = len(run_physical_candidate(db, official_id, g_class, owner_id, limit))
            except Exception:
                n = 0
            counts[g_class] = n
            if n == 0:
                ok_all = False
        if ok_all:
            logger.info(f"Query-plan owner selected for all candidates: {owner_id} counts={counts}")
            return owner_id

    # Fallback: choose the owner with the largest total returned count.
    best_owner = param_pool[0]
    best_score = -1
    best_counts = {}
    for owner_id in param_pool:
        score = 0
        counts = {}
        for _, row in manifest.iterrows():
            db = client[row["db_name"]]
            g_class = row["g_class"]
            try:
                n = len(run_physical_candidate(db, official_id, g_class, owner_id, limit))
            except Exception:
                n = 0
            counts[g_class] = n
            score += n
        if score > best_score:
            best_owner = owner_id
            best_score = score
            best_counts = counts

    logger.info(f"Query-plan owner fallback selected: {best_owner} counts={best_counts}")
    return best_owner


def make_explain_find(db, collection, filter_doc, projection=None, sort=None, limit=None):
    command = {
        "find": collection,
        "filter": filter_doc,
    }
    if projection:
        command["projection"] = projection
    if sort:
        command["sort"] = dict(sort)
    if limit:
        command["limit"] = int(limit)

    return db.command("explain", command, verbosity="executionStats")


def flatten_stages(obj, stages=None, indexes=None):
    if stages is None:
        stages = []
    if indexes is None:
        indexes = []

    if isinstance(obj, dict):
        stage = obj.get("stage")
        if stage:
            stages.append(stage)
        index_name = obj.get("indexName")
        if index_name:
            indexes.append(index_name)
        for v in obj.values():
            flatten_stages(v, stages, indexes)
    elif isinstance(obj, list):
        for v in obj:
            flatten_stages(v, stages, indexes)

    return stages, indexes


def explain_stats(explain):
    stages, indexes = flatten_stages(explain)
    execution_stats = explain.get("executionStats", {}) if isinstance(explain, dict) else {}

    return {
        "executionTimeMillis": execution_stats.get("executionTimeMillis", 0),
        "nReturned": execution_stats.get("nReturned", 0),
        "totalDocsExamined": execution_stats.get("totalDocsExamined", 0),
        "totalKeysExamined": execution_stats.get("totalKeysExamined", 0),
        "all_stages": ";".join(sorted(set(stages))),
        "all_index_names": ";".join(sorted(set(indexes))),
        "has_IXSCAN": "IXSCAN" in stages or "EXPRESS_IXSCAN" in stages,
        "has_COLLSCAN": "COLLSCAN" in stages,
        "has_FETCH": "FETCH" in stages,
        "has_SORT": "SORT" in stages,
        "has_OR": "OR" in stages,
        "has_LIMIT": "LIMIT" in stages,
    }


def run_ic7_explain_components(db, g_class, owner_id, limit):
    components = []

    def add(name, collection, filter_doc, projection=None, sort=None, limit_value=None):
        exp = make_explain_find(db, collection, filter_doc, projection, sort, limit_value)
        stats = explain_stats(exp)
        components.append({
            "component_name": name,
            "operation_kind": "find",
            "collection_name": collection,
            "filter_json": json.dumps(filter_doc, default=str),
            **stats,
            "raw_explain": exp,
        })

    if g_class == "G0":
        posts = list(db.posts.find(
            {"creator_person_id": owner_id},
            {"post_id": 1, "creation_date": 1}
        ).sort("creation_date", -1).limit(limit))

        comments = list(db.comments.find(
            {"creator_person_id": owner_id},
            {"comment_id": 1, "creation_date": 1}
        ).sort("creation_date", -1).limit(limit))
        post_ids = [p.get("post_id") for p in posts if p.get("post_id") is not None]
        comment_ids = [c.get("comment_id") for c in comments if c.get("comment_id") is not None]

        add("ic7_g0_posts_by_person", "posts", {"creator_person_id": owner_id}, {"post_id": 1, "creation_date": 1}, [("creation_date", -1)], limit)
        add("ic7_g0_comments_by_person", "comments", {"creator_person_id": owner_id}, {"comment_id": 1, "creation_date": 1}, [("creation_date", -1)], limit)

        if post_ids:
            add("ic7_g0_likes_on_posts", "person_likes_post", {"post_id": {"$in": post_ids}}, None, [("creation_date", -1)], limit)
        if comment_ids:
            add("ic7_g0_likes_on_comments", "person_likes_comment", {"comment_id": {"$in": comment_ids}}, None, [("creation_date", -1)], limit)

    elif g_class == "G3":
        add("ic7_g3_owner_liker_summary", "ic7_g3_person_recent_liker_summary", {"owner_person_id": owner_id}, None, None, 1)

    elif g_class == "G4":
        add("ic7_g4_explicit_like_edges_by_owner", "ic7_g4_explicit_like_edges", {"owner_person_id": owner_id}, None, [("creation_date", -1)], limit)

    elif g_class == "G6":
        add("ic7_g6_owner_liker_reverse_index", "ic7_g6_owner_liker_reverse_index", {"owner_person_id": owner_id}, None, [("latest_creation_date", -1)], limit)

    # Common follow-up components after retrieving likers.
    result = run_physical_candidate(db, official_id, g_class, owner_id, limit)
    liker_ids = list(dict.fromkeys([normalize_id(x.get("liker_person_id")) for x in result if x.get("liker_person_id") is not None]))

    if liker_ids:
        # G3 embeds recent_likers in the summary collection, so it does not need
        # an additional persons lookup. G0/G4/G6 still fetch person documents.
        if g_class != "G3":
            add("ic7_liker_person_docs", "persons", {"person_id": {"$in": liker_ids}}, {"person_id": 1}, None, limit)

        add("ic7_knows_liker", "person_knows_person", {
            "$or": [
                {"person1_id": owner_id, "person2_id": {"$in": liker_ids}},
                {"person2_id": owner_id, "person1_id": {"$in": liker_ids}},
            ]
        }, None, None, limit)

    return components


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)


def aggregate_raw(raw_rows):
    df = pd.DataFrame(raw_rows)
    if df.empty:
        return pd.DataFrame()

    rows = []
    keys = [
        "candidate_id", "official_id", "query_name", "benchmark_group",
        "g_class", "mongodb_pattern", "document_strategy", "db_name", "run_phase"
    ]

    for group_vals, gdf in df.groupby(keys, dropna=False):
        item = dict(zip(keys, group_vals))
        ok = gdf[gdf["execution_status"] == "completed"]
        lat = ok["latency_ms"].astype(float).tolist()

        item.update({
            "successful_runs": len(ok),
            "failed_runs": int((gdf["execution_status"] != "completed").sum()),
            "avg_latency_ms": statistics.mean(lat) if lat else None,
            "median_latency_ms": statistics.median(lat) if lat else None,
            "p95_latency_ms": percentile(lat, 95) if lat else None,
            "p99_latency_ms": percentile(lat, 99) if lat else None,
            "stddev_latency_ms": statistics.stdev(lat) if len(lat) > 1 else 0 if lat else None,
            "min_latency_ms": min(lat) if lat else None,
            "max_latency_ms": max(lat) if lat else None,
            "avg_documents_returned": ok["documents_returned"].astype(float).mean() if len(ok) else None,
            "documents_written": 0,
        })
        rows.append(item)

    return pd.DataFrame(rows)


def summarize_query_plan(component_rows):
    df = pd.DataFrame(component_rows)
    if df.empty:
        return pd.DataFrame()

    keys = [
        "candidate_id", "official_id", "query_name", "benchmark_group",
        "g_class", "mongodb_pattern", "document_strategy", "db_name"
    ]

    rows = []
    for group_vals, gdf in df.groupby(keys, dropna=False):
        item = dict(zip(keys, group_vals))
        item.update({
            "n_explain_components": len(gdf),
            "execution_status": "completed",
            "sum_executionTimeMillis": gdf["executionTimeMillis"].astype(float).sum(),
            "sum_nReturned": gdf["nReturned"].astype(float).sum(),
            "sum_totalDocsExamined": gdf["totalDocsExamined"].astype(float).sum(),
            "sum_totalKeysExamined": gdf["totalKeysExamined"].astype(float).sum(),
            "all_stages": ";".join(sorted(set(";".join(gdf["all_stages"].fillna("").astype(str)).split(";")) - {""})),
            "all_index_names": ";".join(sorted(set(";".join(gdf["all_index_names"].fillna("").astype(str)).split(";")) - {""})),
            "has_IXSCAN": bool(gdf["has_IXSCAN"].any()),
            "has_COLLSCAN": bool(gdf["has_COLLSCAN"].any()),
            "has_FETCH": bool(gdf["has_FETCH"].any()),
            "has_SORT": bool(gdf["has_SORT"].any()),
            "has_OR": bool(gdf["has_OR"].any()),
            "has_LIMIT": bool(gdf["has_LIMIT"].any()),
        })
        rows.append(item)

    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest")
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--official-id", default="IC7", help="Official query id, comma list, or IS for IS1-IS7")
    ap.add_argument("--scale-label", default="sf0.1")
    ap.add_argument("--run-phase", default="hot")
    ap.add_argument("--sample-size", type=int, default=5)
    ap.add_argument("--warmup-runs", type=int, default=3)
    ap.add_argument("--benchmark-runs", type=int, default=20)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--owner-ids", nargs="*", default=None, help="Optional fixed IC7 owner_person_id values. Keep as strings.")

    ap.add_argument("--mongo-host", default="127.0.0.1")
    ap.add_argument("--mongo-port", type=int, default=27018)
    ap.add_argument("--mongo-username", default="mongo")
    ap.add_argument("--mongo-password", default="mongo")
    ap.add_argument("--mongo-auth-source", default="admin")

    ap.add_argument("--materialize-first", action="store_true")
    ap.add_argument("--build-script")
    ap.add_argument("--data-dir")
    ap.add_argument("--artifacts-dir")
    ap.add_argument("--execution-plan", default="benchmark_execution_plan.csv")
    ap.add_argument("--batch-size", type=int, default=50000)

    ap.add_argument("--resource-monitor", action="store_true")
    ap.add_argument("--resource-monitor-interval-sec", type=int, default=5)
    ap.add_argument("--docker-container-name", default="ldbc_mongodb_physical")
    ap.add_argument("--mongo-data-dir", default="/home/hudson/mongo_data/ldbc_physical")

    ap.add_argument("--save-raw-explain", action="store_true")

    args = ap.parse_args()

    results_dir = Path(args.results_dir)
    logger = setup_logger(results_dir)

    logger.info("LDBC SNB physical benchmark runner started")
    logger.info("Command arguments: " + json.dumps(vars(args), indent=2))

    monitor = None
    if args.resource_monitor:
        monitor = ResourceMonitor(
            out_csv=results_dir / "resource_monitor.csv",
            container_name=args.docker_container_name,
            mongo_data_dir=args.mongo_data_dir,
            interval_sec=args.resource_monitor_interval_sec,
            logger=logger,
        )
        monitor.start()

    try:
        manifest_path = get_candidate_manifest(args, logger)
        logger.info(f"Using manifest: {manifest_path}")

        manifest = pd.read_csv(manifest_path)

        if args.official_id == "IS":
            selected_ids = {f"IS{i}" for i in range(1, 8)}
        elif "," in args.official_id:
            selected_ids = {x.strip() for x in args.official_id.split(",") if x.strip()}
        elif args.official_id == "ALL":
            selected_ids = set(manifest["official_id"].astype(str).unique())
        else:
            selected_ids = {args.official_id}

        manifest = manifest[
            (manifest["official_id"].astype(str).isin(selected_ids))
            & (manifest["ready_for_benchmark"] == True)
        ].copy()

        if manifest.empty:
            raise RuntimeError(f"No ready candidates found for {args.official_id}")

        logger.info(f"Selected official IDs: {sorted(selected_ids)}")

        logger.info(f"Ready candidates selected: {len(manifest)}")
        logger.info(manifest[["candidate_id", "official_id", "g_class", "benchmark_group", "db_name"]].to_string(index=False))

        client = connect_mongo(args)
        client.admin.command("ping")
        logger.info("MongoDB connection OK")

        if args.owner_ids:
            # Manual override: use the same explicit pool for all selected queries.
            parameter_pools = {
                oid: [normalize_id(x) for x in args.owner_ids]
                for oid in sorted(set(manifest["official_id"].astype(str)))
            }
            logger.info(f"Parameter pools from --owner-ids: {parameter_pools}")
        else:
            parameter_pools = build_parameter_pools(client, manifest, args.sample_size, logger)

        empty_pools = {k: v for k, v in parameter_pools.items() if not v}
        if empty_pools:
            raise RuntimeError(f"Empty parameter pools for: {sorted(empty_pools)}")

        pool_rows = []
        for oid, pool in parameter_pools.items():
            for pos, value in enumerate(pool):
                pool_rows.append({"official_id": oid, "position": pos, "parameter_id": value})
        pd.DataFrame(pool_rows).to_csv(results_dir / "parameter_pools_by_query.csv", index=False)
        logger.info(f"Saved parameter pools: {results_dir / 'parameter_pools_by_query.csv'}")

        raw_rows = []
        query_plan_components = []
        raw_explain_dir = results_dir / "query_plan_raw_json"
        raw_explain_dir.mkdir(parents=True, exist_ok=True)

        for _, row in manifest.iterrows():
            candidate = row.to_dict()
            db = client[candidate["db_name"]]
            g_class = candidate["g_class"]
            candidate_id = candidate["candidate_id"]

            logger.info(f"Benchmark candidate={candidate_id} g_class={g_class} db={candidate['db_name']}")

            query_id = str(candidate.get("official_id"))
            q_param_pool = parameter_pools.get(query_id, [])

            if not q_param_pool:
                raise RuntimeError(f"Empty parameter pool for official_id={query_id}")

            # Warmup, not recorded.
            for i in range(args.warmup_runs):
                owner_id = q_param_pool[i % len(q_param_pool)]
                try:
                    _ = run_physical_candidate(db, candidate.get("official_id"), g_class, owner_id, args.limit)
                except Exception as e:
                    logger.warning(f"Warmup failed candidate={candidate_id}: {e}")

            # Timed benchmark, no explain here.
            for i in range(args.benchmark_runs):
                owner_id = q_param_pool[i % len(q_param_pool)]
                start = time.perf_counter()
                status = "completed"
                error = ""
                docs_returned = 0
                try:
                    result = run_physical_candidate(db, candidate.get("official_id"), g_class, owner_id, args.limit)
                    docs_returned = len(result)
                except Exception as e:
                    status = "failed"
                    error = repr(e)
                    logger.error(f"Benchmark failed candidate={candidate_id} run={i}: {e}")
                end = time.perf_counter()

                raw_rows.append({
                    "timestamp": utc_now(),
                    "dataset": "ldbc_snb",
                    "scale_label": args.scale_label,
                    "candidate_id": candidate_id,
                    "official_id": candidate.get("official_id"),
                    "query_name": candidate.get("query_name"),
                    "benchmark_group": candidate.get("benchmark_group"),
                    "g_class": g_class,
                    "mongodb_pattern": candidate.get("mongodb_pattern"),
                    "document_strategy": candidate.get("document_strategy"),
                    "db_name": candidate.get("db_name"),
                    "run_phase": args.run_phase,
                    "run_idx": i,
                    "parameter_id": owner_id,
                    "latency_ms": (end - start) * 1000.0,
                    "documents_returned": docs_returned,
                    "documents_written": 0,
                    "execution_status": status,
                    "error_message": error,
                })

            # Query plan after benchmark, not included in p95.
            logger.info(f"Query plan candidate={candidate_id}")
            explain_owner = choose_explain_param(client, manifest, candidate.get("official_id"), q_param_pool, args.limit, logger)
            try:
                if candidate.get("official_id") == "IC7":
                    comps = run_ic7_explain_components(db, g_class, explain_owner, args.limit)
                elif str(candidate.get("official_id", "")).startswith("IS"):
                    comps = explain_is_generic(db, candidate.get("official_id"), explain_owner, args.limit)
                else:
                    raise ValueError(f"Query-plan runner not implemented for official_id={candidate.get('official_id')}")

                for j, comp in enumerate(comps):
                    raw_explain = comp.pop("raw_explain", None)

                    comp.update({
                        "candidate_id": candidate_id,
                        "official_id": candidate.get("official_id"),
                        "query_name": candidate.get("query_name"),
                        "benchmark_group": candidate.get("benchmark_group"),
                        "g_class": g_class,
                        "mongodb_pattern": candidate.get("mongodb_pattern"),
                        "document_strategy": candidate.get("document_strategy"),
                        "db_name": candidate.get("db_name"),
                        "parameter_id": explain_owner,
                    })

                    if args.save_raw_explain and raw_explain is not None:
                        raw_path = raw_explain_dir / f"{candidate_id}_{j}_{comp['component_name']}.json"
                        raw_path.write_text(json.dumps(raw_explain, default=str, indent=2), encoding="utf-8")
                        comp["raw_explain_path"] = str(raw_path)

                    query_plan_components.append(comp)

            except Exception as e:
                logger.error(f"Query plan failed candidate={candidate_id}: {e}\n{traceback.format_exc()}")
                query_plan_components.append({
                    "candidate_id": candidate_id,
                    "official_id": candidate.get("official_id"),
                    "query_name": candidate.get("query_name"),
                    "benchmark_group": candidate.get("benchmark_group"),
                    "g_class": g_class,
                    "mongodb_pattern": candidate.get("mongodb_pattern"),
                    "document_strategy": candidate.get("document_strategy"),
                    "db_name": candidate.get("db_name"),
                    "execution_status": "failed",
                    "error_message": repr(e),
                })

        write_csv(results_dir / "benchmark_raw_results.csv", raw_rows)
        aggregate = aggregate_raw(raw_rows)
        if not aggregate.empty:
            aggregate["semantic_warning"] = ""
            read_mask = aggregate["official_id"].astype(str).str.startswith(("IC", "IS"))
            zero_mask = read_mask & (pd.to_numeric(aggregate["avg_documents_returned"], errors="coerce").fillna(0) <= 0)
            aggregate.loc[zero_mask, "semantic_warning"] = "zero_documents_returned_for_read_query"
        aggregate.to_csv(results_dir / "benchmark_aggregate_results.csv", index=False)

        component_df = pd.DataFrame(query_plan_components)
        component_df.to_csv(results_dir / "query_plan_component_results.csv", index=False)

        summary_df = summarize_query_plan(query_plan_components)
        summary_df.to_csv(results_dir / "query_plan_summary_results.csv", index=False)

        status_rows = []
        if not component_df.empty and "execution_status" in component_df.columns:
            status_rows = component_df["execution_status"].fillna("completed").value_counts().reset_index().to_dict("records")
        pd.DataFrame(status_rows).to_csv(results_dir / "query_plan_status_summary.csv", index=False)

        run_manifest = {
            "timestamp": utc_now(),
            "script": "run_ldbc_snb_physical_benchmark.py",
            "manifest": str(manifest_path),
            "results_dir": str(results_dir),
            "official_id": args.official_id,
            "scale_label": args.scale_label,
            "sample_size": args.sample_size,
            "warmup_runs": args.warmup_runs,
            "benchmark_runs": args.benchmark_runs,
            "resource_monitor": bool(args.resource_monitor),
            "notes": "Benchmark p95 was measured before query-plan explain. Explain results are not included in performance timings.",
        }
        (results_dir / "benchmark_run_manifest.json").write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")

        logger.info("Saved benchmark_raw_results.csv")
        logger.info("Saved benchmark_aggregate_results.csv")
        logger.info("Saved query_plan_component_results.csv")
        logger.info("Saved query_plan_summary_results.csv")
        logger.info("Saved query_plan_status_summary.csv")
        logger.info("Saved benchmark_run_manifest.json")
        logger.info(f"Done. Results in: {results_dir}")

    except Exception:
        logger.error("Fatal error in physical benchmark runner:\n" + traceback.format_exc())
        raise
    finally:
        if monitor:
            monitor.stop()


if __name__ == "__main__":
    main()
