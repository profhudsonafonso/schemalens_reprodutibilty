#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LDBC SNB MongoDB Benchmark Runner — methodology-oriented executor.

This runner reads:

- mongodb_candidate_specs_by_candidate_id.json
- benchmark_execution_plan.csv or benchmark_execution_plan_smoke.csv
- LDBC SNB SF0.1 CSV files

It materializes each candidate in MongoDB and executes the query linked
to each candidate.

Important:
- This is not the official LDBC driver.
- This is the runner for the methodology benchmark artifacts.
- It supports the official-based workload subset used in the notebook.
"""

import argparse
import csv
import json
import math
import os
import random
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from pymongo import MongoClient, ASCENDING
from pymongo.errors import OperationFailure, AutoReconnect, ServerSelectionTimeoutError, NetworkTimeout


# =========================================================
# Basic helpers
# =========================================================

def log(msg: str, verbose: bool = True) -> None:
    if verbose:
        print(msg, flush=True)


def safe_name(value: str) -> str:
    return (
        str(value)
        .replace(".", "_")
        .replace("-", "_")
        .replace(" ", "_")
        .replace("/", "_")
        .lower()
    )


def now_ms() -> int:
    return int(time.time() * 1000)


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def insert_many_batched(collection, docs: List[dict], batch_size: int) -> int:
    n = 0
    batch = []

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


def df_to_docs(df: pd.DataFrame) -> List[dict]:
    df = df.where(pd.notna(df), None)
    return df.to_dict(orient="records")


def load_pipe_csv(path: Path, row_limit: Optional[int] = None) -> pd.DataFrame:
    return pd.read_csv(
        path,
        sep="|",
        dtype=str,
        engine="python",
        nrows=row_limit,
    )


def find_one_file(folder: Path, prefix: str) -> Path:
    matches = sorted([
        p for p in folder.glob(f"{prefix}*.csv")
        if not p.name.startswith(".")
    ])
    if not matches:
        raise FileNotFoundError(f"No CSV file found with prefix {prefix} in {folder}")
    return matches[0]


def normalize_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    s = str(value)
    if s == "" or s.lower() == "nan":
        return None
    return s


def unique_by(df: pd.DataFrame, key: str) -> pd.DataFrame:
    if key not in df.columns:
        return df
    return df.drop_duplicates(subset=[key], keep="first").reset_index(drop=True)


# =========================================================
# Locate LDBC SNB folders
# =========================================================

def locate_snb_dirs(data_dir: Path) -> Dict[str, Path]:
    snapshot_candidates = sorted([
        p for p in data_dir.glob("social_network-*-CsvMergeForeign-StringDateFormatter")
        if p.is_dir()
    ])

    if not snapshot_candidates:
        raise FileNotFoundError(
            f"Could not find CsvMergeForeign snapshot directory under {data_dir}"
        )

    snapshot_dir = snapshot_candidates[0]
    dynamic_dir = snapshot_dir / "dynamic"
    static_dir = snapshot_dir / "static"

    update_candidates = sorted([
        p for p in data_dir.glob("social_network-*-numpart-*")
        if p.is_dir()
    ])

    update_dir = update_candidates[0] if update_candidates else snapshot_dir

    substitution_candidates = sorted([
        p for p in data_dir.glob("substitution_parameters-*")
        if p.is_dir()
    ])

    substitution_dir = substitution_candidates[0] if substitution_candidates else data_dir

    return {
        "snapshot_dir": snapshot_dir,
        "dynamic_dir": dynamic_dir,
        "static_dir": static_dir,
        "update_dir": update_dir,
        "substitution_dir": substitution_dir,
    }


# =========================================================
# Load normalized LDBC SNB data
# =========================================================

def load_ldbc_snb_data(data_dir: Path, row_limit: Optional[int], verbose: bool) -> Dict[str, pd.DataFrame]:
    dirs = locate_snb_dirs(data_dir)
    dynamic_dir = dirs["dynamic_dir"]
    static_dir = dirs["static_dir"]

    log(f"[load] dynamic_dir={dynamic_dir}", verbose)
    log(f"[load] static_dir={static_dir}", verbose)

    # -------------------------------
    # Entities
    # -------------------------------

    persons_raw = load_pipe_csv(find_one_file(dynamic_dir, "person_"), row_limit)
    forums_raw = load_pipe_csv(find_one_file(dynamic_dir, "forum_"), row_limit)
    posts_raw = load_pipe_csv(find_one_file(dynamic_dir, "post_"), row_limit)
    comments_raw = load_pipe_csv(find_one_file(dynamic_dir, "comment_"), row_limit)

    places_raw = load_pipe_csv(find_one_file(static_dir, "place_"), row_limit)
    organisations_raw = load_pipe_csv(find_one_file(static_dir, "organisation_"), row_limit)
    tags_raw = load_pipe_csv(find_one_file(static_dir, "tag_"), row_limit)
    tagclasses_raw = load_pipe_csv(find_one_file(static_dir, "tagclass_"), row_limit)

    persons = persons_raw.rename(columns={
        "id": "person_id",
        "firstName": "first_name",
        "lastName": "last_name",
        "creationDate": "creation_date",
        "locationIP": "location_ip",
        "browserUsed": "browser_used",
        "place": "place_id",
    })
    persons = persons[
        [c for c in [
            "person_id", "first_name", "last_name", "gender", "birthday",
            "creation_date", "location_ip", "browser_used", "place_id"
        ] if c in persons.columns]
    ]
    persons = unique_by(persons, "person_id")

    forums = forums_raw.rename(columns={
        "id": "forum_id",
        "creationDate": "creation_date",
        "moderator": "moderator_person_id",
    })
    forums = forums[
        [c for c in ["forum_id", "title", "creation_date", "moderator_person_id"] if c in forums.columns]
    ]
    forums = unique_by(forums, "forum_id")

    posts = posts_raw.rename(columns={
        "id": "post_id",
        "imageFile": "image_file",
        "creationDate": "creation_date",
        "locationIP": "location_ip",
        "browserUsed": "browser_used",
        "creator": "creator_person_id",
        "Forum.id": "forum_id",
        "place": "place_id",
    })
    posts = posts[
        [c for c in [
            "post_id", "image_file", "creation_date", "location_ip", "browser_used",
            "language", "content", "length", "creator_person_id", "forum_id", "place_id"
        ] if c in posts.columns]
    ]
    posts = unique_by(posts, "post_id")

    comments = comments_raw.rename(columns={
        "id": "comment_id",
        "creationDate": "creation_date",
        "locationIP": "location_ip",
        "browserUsed": "browser_used",
        "creator": "creator_person_id",
        "place": "place_id",
        "replyOfPost": "reply_post_id",
        "replyOfComment": "reply_comment_id",
    })
    comments = comments[
        [c for c in [
            "comment_id", "creation_date", "location_ip", "browser_used",
            "content", "length", "creator_person_id", "place_id",
            "reply_post_id", "reply_comment_id"
        ] if c in comments.columns]
    ]
    comments = unique_by(comments, "comment_id")

    places = places_raw.rename(columns={
        "id": "place_id",
        "isPartOf": "parent_place_id",
    })
    places = places[
        [c for c in ["place_id", "name", "url", "type", "parent_place_id"] if c in places.columns]
    ]
    places = unique_by(places, "place_id")

    organisations = organisations_raw.rename(columns={
        "id": "organisation_id",
        "place": "place_id",
    })
    organisations = organisations[
        [c for c in ["organisation_id", "type", "name", "url", "place_id"] if c in organisations.columns]
    ]
    organisations = unique_by(organisations, "organisation_id")

    tags = tags_raw.rename(columns={
        "id": "tag_id",
        "hasType": "tagclass_id",
    })
    tags = tags[
        [c for c in ["tag_id", "name", "url", "tagclass_id"] if c in tags.columns]
    ]
    tags = unique_by(tags, "tag_id")

    tagclasses = tagclasses_raw.rename(columns={
        "id": "tagclass_id",
        "isSubclassOf": "parent_tagclass_id",
    })
    tagclasses = tagclasses[
        [c for c in ["tagclass_id", "name", "url", "parent_tagclass_id"] if c in tagclasses.columns]
    ]
    tagclasses = unique_by(tagclasses, "tagclass_id")

    data = {
        "persons": persons,
        "forums": forums,
        "posts": posts,
        "comments": comments,
        "places": places,
        "organisations": organisations,
        "tags": tags,
        "tagclasses": tagclasses,
    }

    # -------------------------------
    # Explicit relationships
    # -------------------------------

    def rel_file(prefix: str) -> Optional[Path]:
        try:
            return find_one_file(dynamic_dir, prefix)
        except FileNotFoundError:
            return None

    relationship_loaders = {
        "person_knows_person": ("person_knows_person_", {
            "Person.id": "person1_id",
            "Person.id_1": "person2_id",
            "creationDate": "creation_date",
        }),
        "forum_has_member_person": ("forum_hasMember_person_", {
            "Forum.id": "forum_id",
            "Person.id": "person_id",
            "joinDate": "join_date",
        }),
        "person_likes_post": ("person_likes_post_", {
            "Person.id": "person_id",
            "Post.id": "post_id",
            "creationDate": "creation_date",
        }),
        "person_likes_comment": ("person_likes_comment_", {
            "Person.id": "person_id",
            "Comment.id": "comment_id",
            "creationDate": "creation_date",
        }),
        "post_has_tag": ("post_hasTag_tag_", {
            "Post.id": "post_id",
            "Tag.id": "tag_id",
        }),
        "comment_has_tag": ("comment_hasTag_tag_", {
            "Comment.id": "comment_id",
            "Tag.id": "tag_id",
        }),
        "forum_has_tag": ("forum_hasTag_tag_", {
            "Forum.id": "forum_id",
            "Tag.id": "tag_id",
        }),
        "person_has_interest_tag": ("person_hasInterest_tag_", {
            "Person.id": "person_id",
            "Tag.id": "tag_id",
        }),
        "person_study_at_organisation": ("person_studyAt_organisation_", {
            "Person.id": "person_id",
            "Organisation.id": "organisation_id",
            "classYear": "class_year",
        }),
        "person_work_at_organisation": ("person_workAt_organisation_", {
            "Person.id": "person_id",
            "Organisation.id": "organisation_id",
            "workFrom": "work_from",
        }),
    }

    for rel_name, (prefix, rename_map) in relationship_loaders.items():
        path = rel_file(prefix)
        if path is None:
            data[rel_name] = pd.DataFrame()
            continue

        df = load_pipe_csv(path, row_limit)

        # Fix duplicated LDBC relationship column names generated by pandas.
        # Example:
        # person_knows_person has two logical Person.id columns.
        # pandas loads them as Person.id and Person.id.1.
        df = df.rename(columns=rename_map)

        if rel_name == "person_knows_person":
            if "person1_id" not in df.columns and "Person.id" in df.columns:
                df["person1_id"] = df["Person.id"]

            if "person2_id" not in df.columns:
                for candidate_col in ["Person.id_1", "Person.id.1", "Person.id.2"]:
                    if candidate_col in df.columns:
                        df["person2_id"] = df[candidate_col]
                        break

            keep_cols = [
                c for c in ["person1_id", "person2_id", "creation_date"]
                if c in df.columns
            ]
            df = df[keep_cols]

        data[rel_name] = df

    # -------------------------------
    # FK-derived relationships
    # -------------------------------

    data["person_is_located_in_place"] = persons[
        ["person_id", "place_id"]
    ].dropna().drop_duplicates()

    data["forum_has_moderator_person"] = forums[
        ["forum_id", "moderator_person_id"]
    ].dropna().rename(columns={"moderator_person_id": "person_id"}).drop_duplicates()

    data["forum_container_of_post"] = posts[
        ["forum_id", "post_id"]
    ].dropna().drop_duplicates()

    data["post_has_creator_person"] = posts[
        ["post_id", "creator_person_id"]
    ].dropna().rename(columns={"creator_person_id": "person_id"}).drop_duplicates()

    data["post_is_located_in_place"] = posts[
        ["post_id", "place_id"]
    ].dropna().drop_duplicates()

    data["comment_has_creator_person"] = comments[
        ["comment_id", "creator_person_id"]
    ].dropna().rename(columns={"creator_person_id": "person_id"}).drop_duplicates()

    data["comment_is_located_in_place"] = comments[
        ["comment_id", "place_id"]
    ].dropna().drop_duplicates()

    if "reply_post_id" in comments.columns:
        data["comment_reply_of_post"] = comments[
            ["reply_post_id", "comment_id"]
        ].dropna().rename(columns={"reply_post_id": "post_id"}).drop_duplicates()
    else:
        data["comment_reply_of_post"] = pd.DataFrame(columns=["post_id", "comment_id"])

    if "reply_comment_id" in comments.columns:
        data["comment_reply_of_comment"] = comments[
            ["reply_comment_id", "comment_id"]
        ].dropna().rename(columns={"reply_comment_id": "parent_comment_id"}).drop_duplicates()
    else:
        data["comment_reply_of_comment"] = pd.DataFrame(columns=["parent_comment_id", "comment_id"])

    data["organisation_is_located_in_place"] = organisations[
        ["organisation_id", "place_id"]
    ].dropna().drop_duplicates()

    data["tag_has_type_tagclass"] = tags[
        ["tag_id", "tagclass_id"]
    ].dropna().drop_duplicates()

    data["tagclass_is_subclass_of_tagclass"] = tagclasses[
        ["tagclass_id", "parent_tagclass_id"]
    ].dropna().drop_duplicates()

    data["place_is_part_of_place"] = places[
        ["parent_place_id", "place_id"]
    ].dropna().drop_duplicates()

    log("[load] loaded dataframes:", verbose)
    for k, df in data.items():
        log(f"  - {k}: {len(df)} rows", verbose)

    return data


# =========================================================
# Entity and relationship collection maps
# =========================================================

ENTITY_COLLECTIONS = {
    "Person": "persons",
    "Forum": "forums",
    "Post": "posts",
    "Comment": "comments",
    "Place": "places",
    "Organisation": "organisations",
    "Tag": "tags",
    "TagClass": "tagclasses",
}

ENTITY_PK = {
    "Person": "person_id",
    "Forum": "forum_id",
    "Post": "post_id",
    "Comment": "comment_id",
    "Place": "place_id",
    "Organisation": "organisation_id",
    "Tag": "tag_id",
    "TagClass": "tagclass_id",
}

RELATIONSHIP_COLLECTIONS = {
    "person_knows_person": "person_knows_person",
    "person_is_located_in_place": "person_is_located_in_place",
    "person_has_interest_tag": "person_has_interest_tag",
    "person_likes_post": "person_likes_post",
    "person_likes_comment": "person_likes_comment",
    "person_study_at_organisation": "person_study_at_organisation",
    "person_work_at_organisation": "person_work_at_organisation",
    "forum_has_moderator_person": "forum_has_moderator_person",
    "forum_has_member_person": "forum_has_member_person",
    "forum_has_tag": "forum_has_tag",
    "forum_container_of_post": "forum_container_of_post",
    "post_has_creator_person": "post_has_creator_person",
    "post_is_located_in_place": "post_is_located_in_place",
    "post_has_tag": "post_has_tag",
    "comment_has_creator_person": "comment_has_creator_person",
    "comment_is_located_in_place": "comment_is_located_in_place",
    "comment_has_tag": "comment_has_tag",
    "comment_reply_of_post": "comment_reply_of_post",
    "comment_reply_of_comment": "comment_reply_of_comment",
    "organisation_is_located_in_place": "organisation_is_located_in_place",
    "tag_has_type_tagclass": "tag_has_type_tagclass",
    "tagclass_is_subclass_of_tagclass": "tagclass_is_subclass_of_tagclass",
    "place_is_part_of_place": "place_is_part_of_place",
}


# =========================================================
# MongoDB materialization
# =========================================================

def create_indexes(db) -> None:
    index_specs = {
        "persons": ["person_id", "place_id", "first_name"],
        "forums": ["forum_id", "moderator_person_id"],
        "posts": ["post_id", "creator_person_id", "forum_id", "place_id", "creation_date"],
        "comments": [
            "comment_id", "creator_person_id", "place_id",
            "reply_post_id", "reply_comment_id", "creation_date"
        ],
        "places": ["place_id", "parent_place_id", "name", "type"],
        "organisations": ["organisation_id", "place_id"],
        "tags": ["tag_id", "tagclass_id", "name"],
        "tagclasses": ["tagclass_id", "parent_tagclass_id"],
        "person_knows_person": ["person1_id", "person2_id"],
        "forum_has_member_person": ["forum_id", "person_id"],
        "forum_has_moderator_person": ["forum_id", "person_id"],
        "forum_container_of_post": ["forum_id", "post_id"],
        "person_likes_post": ["person_id", "post_id"],
        "person_likes_comment": ["person_id", "comment_id"],
        "post_has_tag": ["post_id", "tag_id"],
        "comment_has_tag": ["comment_id", "tag_id"],
        "forum_has_tag": ["forum_id", "tag_id"],
        "person_has_interest_tag": ["person_id", "tag_id"],
        "person_study_at_organisation": ["person_id", "organisation_id"],
        "person_work_at_organisation": ["person_id", "organisation_id"],
        "comment_reply_of_post": ["post_id", "comment_id"],
        "comment_reply_of_comment": ["parent_comment_id", "comment_id"],
    }

    for collection_name, fields in index_specs.items():
        col = db[collection_name]
        for field in fields:
            try:
                col.create_index([(field, ASCENDING)])
            except Exception:
                pass


def materialize_candidate(
    mongo_client: MongoClient,
    db_name: str,
    candidate_spec: dict,
    data: Dict[str, pd.DataFrame],
    batch_size: int,
    force_rebuild: bool,
    verbose: bool,
) -> Dict[str, Any]:
    start = time.perf_counter()

    if force_rebuild:
        mongo_client.drop_database(db_name)

    db = mongo_client[db_name]

    materialization = candidate_spec["materialization"]
    accessed_entities = materialization.get("accessed_entities", [])
    relationships_used = materialization.get("relationships_used", [])

    loaded_collections = {}

    # Load accessed entity collections
    for entity in accessed_entities:
        collection_name = ENTITY_COLLECTIONS.get(entity)
        if not collection_name:
            continue

        df = data.get(collection_name)
        if df is None:
            continue

        docs = df_to_docs(df)
        n = insert_many_batched(db[collection_name], docs, batch_size) if docs else 0
        loaded_collections[collection_name] = n

    # Load relationship collections used by candidate
    for rel in relationships_used:
        collection_name = RELATIONSHIP_COLLECTIONS.get(rel, rel)
        df = data.get(rel)

        if df is None or len(df) == 0:
            loaded_collections[collection_name] = 0
            continue

        docs = df_to_docs(df)
        n = insert_many_batched(db[collection_name], docs, batch_size) if docs else 0
        loaded_collections[collection_name] = n

    # Always load minimal collections useful for query resolution
    # This avoids failures in mixed Message/Post/Comment queries.
    for collection_name in ["persons", "posts", "comments", "forums", "places"]:
        if collection_name in loaded_collections:
            continue
        df = data.get(collection_name)
        if df is not None and len(df) > 0:
            docs = df_to_docs(df)
            n = insert_many_batched(db[collection_name], docs, batch_size)
            loaded_collections[collection_name] = n

    create_indexes(db)

    elapsed = time.perf_counter() - start

    return {
        "db_name": db_name,
        "load_seconds": elapsed,
        "loaded_collections": loaded_collections,
        "load_completed": True,
    }


# =========================================================
# Parameter helpers
# =========================================================

def first_value(db, collection: str, field: str) -> Optional[str]:
    doc = db[collection].find_one({field: {"$exists": True, "$ne": None}}, {field: 1})
    if not doc:
        return None
    return normalize_id(doc.get(field))


def first_doc(db, collection: str, projection: Optional[dict] = None) -> Optional[dict]:
    return db[collection].find_one({}, projection)



# =========================================================
# Query parameter pool helpers
# =========================================================

_LDBC_PARAM_POOL_CACHE = {}


def cyclic_pick(values, repetition: int):
    if not values:
        return None
    return values[(int(repetition) - 1) % len(values)]


def distinct_non_null(values):
    out = []
    seen = set()

    for v in values:
        v = normalize_id(v)
        if v is None:
            continue
        if v not in seen:
            seen.add(v)
            out.append(v)

    return out


def persons_with_friends(db, limit: int = 100):
    """
    Select persons that actually appear in person_knows_person.
    This fixes IC1/IC2/IC3/IC4/IC5 returning zero because the first person
    in the persons collection may have no knows edges.
    """
    pipeline = [
        {
            "$project": {
                "person_id": "$person1_id"
            }
        },
        {
            "$unionWith": {
                "coll": "person_knows_person",
                "pipeline": [
                    {
                        "$project": {
                            "person_id": "$person2_id"
                        }
                    }
                ],
            }
        },
        {
            "$group": {
                "_id": "$person_id",
                "degree": {"$sum": 1}
            }
        },
        {
            "$sort": {
                "degree": -1
            }
        },
        {
            "$limit": limit
        },
    ]

    try:
        return [
            normalize_id(x["_id"])
            for x in db.person_knows_person.aggregate(pipeline, allowDiskUse=True)
            if normalize_id(x.get("_id")) is not None
        ]
    except Exception:
        # Fallback without unionWith.
        vals = []
        for e in db.person_knows_person.find({}, {"person1_id": 1, "person2_id": 1}).limit(limit * 10):
            vals.append(e.get("person1_id"))
            vals.append(e.get("person2_id"))
        return distinct_non_null(vals)[:limit]


def persons_with_friends_and_messages(db, limit: int = 100):
    """
    Select persons whose friends have posts or comments.
    Useful for IC2, IC3, IC4, IC6.
    """
    base_persons = persons_with_friends(db, limit=limit * 3)
    selected = []

    for pid in base_persons:
        friends = get_friends(db, pid, max_depth=1, limit=200)

        if not friends:
            continue

        has_message = (
            db.posts.count_documents({"creator_person_id": {"$in": friends}}, limit=1) > 0
            or db.comments.count_documents({"creator_person_id": {"$in": friends}}, limit=1) > 0
        )

        if has_message:
            selected.append(pid)

        if len(selected) >= limit:
            break

    return selected or base_persons[:limit]


def persons_with_friends_posts_and_tags(db, limit: int = 100):
    """
    Select persons whose friends have tagged posts.
    Useful for IC4 and IC6.
    """
    base_persons = persons_with_friends_and_messages(db, limit=limit * 3)
    selected = []

    for pid in base_persons:
        friends = get_friends(db, pid, max_depth=2, limit=300)

        if not friends:
            continue

        post = db.posts.find_one(
            {"creator_person_id": {"$in": friends}},
            {"post_id": 1}
        )

        if not post:
            continue

        has_tag = db.post_has_tag.count_documents(
            {"post_id": post.get("post_id")},
            limit=1
        ) > 0

        if has_tag:
            selected.append(pid)

        if len(selected) >= limit:
            break

    return selected or base_persons[:limit]


def persons_with_friends_and_forums(db, limit: int = 100):
    """
    Select persons whose friends or friends-of-friends are forum members.
    Useful for IC5.
    """
    base_persons = persons_with_friends(db, limit=limit * 3)
    selected = []

    for pid in base_persons:
        friends = get_friends(db, pid, max_depth=2, limit=300)

        if not friends:
            continue

        has_membership = db.forum_has_member_person.count_documents(
            {"person_id": {"$in": friends}},
            limit=1
        ) > 0

        if has_membership:
            selected.append(pid)

        if len(selected) >= limit:
            break

    return selected or base_persons[:limit]


def persons_with_own_messages_and_likes(db, limit: int = 100):
    """
    Select persons whose posts/comments have likes.
    Useful for IC7.
    """
    selected = []

    # Persons with liked posts
    liked_posts = list(db.person_likes_post.find({}, {"post_id": 1}).limit(limit * 20))
    post_ids = distinct_non_null([x.get("post_id") for x in liked_posts])

    for post in db.posts.find({"post_id": {"$in": post_ids}}, {"creator_person_id": 1}).limit(limit * 5):
        pid = normalize_id(post.get("creator_person_id"))
        if pid and pid not in selected:
            selected.append(pid)
        if len(selected) >= limit:
            return selected

    # Persons with liked comments
    liked_comments = list(db.person_likes_comment.find({}, {"comment_id": 1}).limit(limit * 20))
    comment_ids = distinct_non_null([x.get("comment_id") for x in liked_comments])

    for comment in db.comments.find({"comment_id": {"$in": comment_ids}}, {"creator_person_id": 1}).limit(limit * 5):
        pid = normalize_id(comment.get("creator_person_id"))
        if pid and pid not in selected:
            selected.append(pid)
        if len(selected) >= limit:
            return selected

    return selected or persons_with_friends(db, limit=limit)


def posts_with_replies(db, limit: int = 100):
    rows = list(
        db.comment_reply_of_post.aggregate([
            {"$group": {"_id": "$post_id", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}},
            {"$limit": limit},
        ])
    )

    vals = [normalize_id(x["_id"]) for x in rows if normalize_id(x.get("_id")) is not None]

    if vals:
        return vals

    return distinct_non_null([
        x.get("post_id")
        for x in db.posts.find({}, {"post_id": 1}).limit(limit)
    ])


def comments_with_replies(db, limit: int = 100):
    rows = list(
        db.comment_reply_of_comment.aggregate([
            {"$group": {"_id": "$parent_comment_id", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}},
            {"$limit": limit},
        ])
    )

    vals = [normalize_id(x["_id"]) for x in rows if normalize_id(x.get("_id")) is not None]

    if vals:
        return vals

    return distinct_non_null([
        x.get("comment_id")
        for x in db.comments.find({}, {"comment_id": 1}).limit(limit)
    ])


def forums_with_members(db, limit: int = 100):
    rows = list(
        db.forum_has_member_person.aggregate([
            {"$group": {"_id": "$forum_id", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}},
            {"$limit": limit},
        ])
    )

    vals = [normalize_id(x["_id"]) for x in rows if normalize_id(x.get("_id")) is not None]

    if vals:
        return vals

    return distinct_non_null([
        x.get("forum_id")
        for x in db.forums.find({}, {"forum_id": 1}).limit(limit)
    ])


def tags_used_in_posts(db, limit: int = 100):
    rows = list(
        db.post_has_tag.aggregate([
            {"$group": {"_id": "$tag_id", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}},
            {"$limit": limit},
        ])
    )

    vals = [normalize_id(x["_id"]) for x in rows if normalize_id(x.get("_id")) is not None]

    if vals:
        return vals

    return distinct_non_null([
        x.get("tag_id")
        for x in db.tags.find({}, {"tag_id": 1}).limit(limit)
    ])


def build_ldbc_query_parameter_pool(db, sample_size: int = 20) -> dict:
    """
    Build semantic query parameters for LDBC SNB.

    This follows the same idea as the FIBEN runner:
    do not pick arbitrary first IDs.
    Pick IDs that actually have the paths required by each query.
    """
    db_name = db.name

    if db_name in _LDBC_PARAM_POOL_CACHE:
        return _LDBC_PARAM_POOL_CACHE[db_name]

    pool = {}

    connected_persons = persons_with_friends(db, limit=sample_size)
    message_persons = persons_with_friends_and_messages(db, limit=sample_size)
    tag_persons = persons_with_friends_posts_and_tags(db, limit=sample_size)
    forum_persons = persons_with_friends_and_forums(db, limit=sample_size)
    liked_message_persons = persons_with_own_messages_and_likes(db, limit=sample_size)

    post_ids = distinct_non_null([
        x.get("post_id")
        for x in db.posts.find({}, {"post_id": 1}).limit(sample_size)
    ])

    comment_ids = distinct_non_null([
        x.get("comment_id")
        for x in db.comments.find({}, {"comment_id": 1}).limit(sample_size)
    ])

    reply_post_ids = posts_with_replies(db, limit=sample_size)
    reply_comment_ids = comments_with_replies(db, limit=sample_size)
    forum_ids = forums_with_members(db, limit=sample_size)
    tag_ids = tags_used_in_posts(db, limit=sample_size)

    place_ids = distinct_non_null([
        x.get("place_id")
        for x in db.places.find({}, {"place_id": 1}).limit(sample_size)
    ])

    # Official interactive complex reads
    pool["IC1"] = [{"person_id": pid} for pid in connected_persons]
    pool["IC2"] = [{"person_id": pid} for pid in message_persons]
    pool["IC3"] = [{"person_id": pid} for pid in message_persons]
    pool["IC4"] = [{"person_id": pid} for pid in tag_persons]
    pool["IC5"] = [{"person_id": pid} for pid in forum_persons]
    pool["IC6"] = [
        {
            "person_id": pid,
            "tag_id": cyclic_pick(tag_ids, i + 1),
        }
        for i, pid in enumerate(tag_persons)
    ]
    pool["IC7"] = [{"person_id": pid} for pid in liked_message_persons]

    # Short reads
    pool["IS1"] = [{"person_id": pid} for pid in connected_persons]
    pool["IS2"] = [{"person_id": pid} for pid in message_persons]
    pool["IS3"] = [{"person_id": pid} for pid in connected_persons]
    pool["IS4"] = [
        {
            "post_id": cyclic_pick(post_ids, i + 1),
            "comment_id": cyclic_pick(comment_ids, i + 1),
        }
        for i in range(max(len(post_ids), len(comment_ids), 1))
    ]
    pool["IS5"] = pool["IS4"]
    pool["IS6"] = [
        {
            "post_id": cyclic_pick(reply_post_ids or post_ids, i + 1),
            "comment_id": cyclic_pick(reply_comment_ids or comment_ids, i + 1),
        }
        for i in range(max(len(reply_post_ids), len(reply_comment_ids), 1))
    ]
    pool["IS7"] = [
        {
            "post_id": cyclic_pick(reply_post_ids or post_ids, i + 1),
            "comment_id": cyclic_pick(reply_comment_ids or comment_ids, i + 1),
        }
        for i in range(max(len(reply_post_ids), len(reply_comment_ids), 1))
    ]

    # Inserts
    pool["INS1"] = [
        {
            "person_id": cyclic_pick(connected_persons, i + 1),
            "place_id": cyclic_pick(place_ids, i + 1),
        }
        for i in range(max(len(connected_persons), 1))
    ]
    pool["INS2"] = [
        {
            "person_id": cyclic_pick(connected_persons, i + 1),
            "post_id": cyclic_pick(post_ids, i + 1),
        }
        for i in range(max(len(connected_persons), len(post_ids), 1))
    ]
    pool["INS3"] = [
        {
            "person_id": cyclic_pick(connected_persons, i + 1),
            "comment_id": cyclic_pick(comment_ids, i + 1),
        }
        for i in range(max(len(connected_persons), len(comment_ids), 1))
    ]
    pool["INS4"] = [
        {
            "person_id": cyclic_pick(connected_persons, i + 1),
            "tag_id": cyclic_pick(tag_ids, i + 1),
        }
        for i in range(max(len(connected_persons), 1))
    ]
    pool["INS5"] = [
        {
            "person_id": cyclic_pick(connected_persons, i + 1),
            "forum_id": cyclic_pick(forum_ids, i + 1),
        }
        for i in range(max(len(connected_persons), len(forum_ids), 1))
    ]
    pool["INS6"] = [
        {
            "person_id": cyclic_pick(connected_persons, i + 1),
            "forum_id": cyclic_pick(forum_ids, i + 1),
            "place_id": cyclic_pick(place_ids, i + 1),
            "tag_id": cyclic_pick(tag_ids, i + 1),
        }
        for i in range(max(len(connected_persons), len(forum_ids), 1))
    ]
    pool["INS7"] = [
        {
            "person_id": cyclic_pick(connected_persons, i + 1),
            "post_id": cyclic_pick(post_ids, i + 1),
            "comment_id": cyclic_pick(comment_ids, i + 1),
            "place_id": cyclic_pick(place_ids, i + 1),
            "tag_id": cyclic_pick(tag_ids, i + 1),
        }
        for i in range(max(len(connected_persons), len(post_ids), 1))
    ]
    pool["INS8"] = [{"person_id": pid} for pid in connected_persons]

    # Fallback for any empty pool
    fallback_person = first_value(db, "persons", "person_id")
    fallback_post = first_value(db, "posts", "post_id")
    fallback_comment = first_value(db, "comments", "comment_id")
    fallback_forum = first_value(db, "forums", "forum_id")
    fallback_tag = first_value(db, "tags", "tag_id") if "tags" in db.list_collection_names() else None
    fallback_place = first_value(db, "places", "place_id")

    for key, values in list(pool.items()):
        if not values:
            pool[key] = [{
                "person_id": fallback_person,
                "post_id": fallback_post,
                "comment_id": fallback_comment,
                "forum_id": fallback_forum,
                "tag_id": fallback_tag,
                "place_id": fallback_place,
            }]

    log(
        "[param-pool] "
        + " ".join(f"{k}={len(v)}" for k, v in sorted(pool.items()))
    )

    _LDBC_PARAM_POOL_CACHE[db_name] = pool
    return pool


def pick_ldbc_param_for_run(pool: dict, official_id: str, repetition: int) -> dict:
    values = pool.get(official_id, [])
    if not values:
        return {}
    return values[(int(repetition) - 1) % len(values)]


def build_params(db, official_id: str, repetition: int) -> dict:
    """
    Build query parameters using semantic parameter pools.

    This replaces the previous first_value-based strategy, which caused
    IC1-IC5 to return 0 documents when the first person had no useful path.
    """
    pool = build_ldbc_query_parameter_pool(db, sample_size=20)

    params = pick_ldbc_param_for_run(pool, official_id, repetition)

    # Complete common defaults
    params = dict(params or {})

    params.setdefault("person_id", first_value(db, "persons", "person_id"))
    params.setdefault("post_id", first_value(db, "posts", "post_id"))
    params.setdefault("comment_id", first_value(db, "comments", "comment_id"))
    params.setdefault("forum_id", first_value(db, "forums", "forum_id"))
    params.setdefault("tag_id", first_value(db, "tags", "tag_id") if "tags" in db.list_collection_names() else None)
    params.setdefault("place_id", first_value(db, "places", "place_id"))
    params.setdefault("new_id", f"bench_{official_id}_{int(time.time() * 1000)}_{repetition}")

    return params


# =========================================================
# Query execution functions
# =========================================================

def exec_is1(db, p):
    person = db.persons.find_one({"person_id": p["person_id"]})
    if not person:
        return 0
    place = None
    if person.get("place_id"):
        place = db.places.find_one({"place_id": person.get("place_id")})
    return 1 + (1 if place else 0)


def exec_is2(db, p):
    pid = p["person_id"]
    posts = list(db.posts.find({"creator_person_id": pid}).sort("creation_date", -1).limit(10))
    comments = list(db.comments.find({"creator_person_id": pid}).sort("creation_date", -1).limit(10))
    n = len(posts) + len(comments)

    for c in comments[:5]:
        if c.get("reply_post_id"):
            db.posts.find_one({"post_id": c.get("reply_post_id")})
            n += 1
        elif c.get("reply_comment_id"):
            parent = db.comments.find_one({"comment_id": c.get("reply_comment_id")})
            n += 1 if parent else 0

    return n


def exec_is3(db, p):
    pid = p["person_id"]
    a = list(db.person_knows_person.find({"person1_id": pid}).limit(100))
    b = list(db.person_knows_person.find({"person2_id": pid}).limit(100))
    return len(a) + len(b)


def exec_is4(db, p):
    post = db.posts.find_one({"post_id": p["post_id"]})
    if post:
        return 1
    comment = db.comments.find_one({"comment_id": p["comment_id"]})
    return 1 if comment else 0


def exec_is5(db, p):
    post = db.posts.find_one({"post_id": p["post_id"]})
    if post and post.get("creator_person_id"):
        person = db.persons.find_one({"person_id": post.get("creator_person_id")})
        return 1 + (1 if person else 0)

    comment = db.comments.find_one({"comment_id": p["comment_id"]})
    if comment and comment.get("creator_person_id"):
        person = db.persons.find_one({"person_id": comment.get("creator_person_id")})
        return 1 + (1 if person else 0)

    return 0


def exec_is6(db, p):
    post = db.posts.find_one({"post_id": p["post_id"]})
    if not post:
        comment = db.comments.find_one({"comment_id": p["comment_id"]})
        if comment and comment.get("reply_post_id"):
            post = db.posts.find_one({"post_id": comment.get("reply_post_id")})

    if not post:
        return 0

    n = 1
    forum = None
    if post.get("forum_id"):
        forum = db.forums.find_one({"forum_id": post.get("forum_id")})
        n += 1 if forum else 0

    if forum and forum.get("moderator_person_id"):
        moderator = db.persons.find_one({"person_id": forum.get("moderator_person_id")})
        n += 1 if moderator else 0

    return n


def exec_is7(db, p):
    post_id = p["post_id"]
    post = db.posts.find_one({"post_id": post_id})
    if not post:
        return 0

    replies = list(db.comments.find({"reply_post_id": post_id}).limit(50))
    n = len(replies)

    original_creator = post.get("creator_person_id")

    for r in replies:
        creator = r.get("creator_person_id")
        if creator:
            db.persons.find_one({"person_id": creator})
            n += 1

            if original_creator:
                friendship = db.person_knows_person.find_one({
                    "$or": [
                        {"person1_id": original_creator, "person2_id": creator},
                        {"person1_id": creator, "person2_id": original_creator},
                    ]
                })
                n += 1 if friendship else 0

    return n


def get_friends(db, person_id: str, max_depth: int = 1, limit: int = 500) -> List[str]:
    if not person_id:
        return []

    seen = {person_id}
    frontier = [person_id]

    for _ in range(max_depth):
        next_frontier = []

        for pid in frontier:
            edges = list(db.person_knows_person.find({
                "$or": [
                    {"person1_id": pid},
                    {"person2_id": pid},
                ]
            }).limit(limit))

            for e in edges:
                a = e.get("person1_id")
                b = e.get("person2_id")
                other = b if a == pid else a

                if other and other not in seen:
                    seen.add(other)
                    next_frontier.append(other)

        frontier = next_frontier[:limit]

        if not frontier:
            break

    seen.discard(person_id)
    return list(seen)[:limit]


def exec_ic1(db, p):
    friends = get_friends(db, p["person_id"], max_depth=3, limit=200)
    n = len(friends)

    for pid in friends[:50]:
        person = db.persons.find_one({"person_id": pid})
        if person:
            n += 1
        list(db.person_study_at_organisation.find({"person_id": pid}).limit(5))
        list(db.person_work_at_organisation.find({"person_id": pid}).limit(5))

    return n


def exec_ic2(db, p):
    friends = get_friends(db, p["person_id"], max_depth=1, limit=200)
    n = len(friends)

    for pid in friends[:50]:
        n += db.posts.count_documents({"creator_person_id": pid}, limit=20)
        n += db.comments.count_documents({"creator_person_id": pid}, limit=20)

    return n


def exec_ic3(db, p):
    friends = get_friends(db, p["person_id"], max_depth=2, limit=200)
    n = len(friends)

    for pid in friends[:50]:
        posts = list(db.posts.find({"creator_person_id": pid}).limit(10))
        comments = list(db.comments.find({"creator_person_id": pid}).limit(10))
        n += len(posts) + len(comments)

        for m in posts[:5] + comments[:5]:
            if m.get("place_id"):
                place = db.places.find_one({"place_id": m.get("place_id")})
                n += 1 if place else 0

    return n


def exec_ic4(db, p):
    friends = get_friends(db, p["person_id"], max_depth=1, limit=200)
    n = len(friends)

    for pid in friends[:50]:
        posts = list(db.posts.find({"creator_person_id": pid}).limit(10))
        n += len(posts)

        for post in posts[:5]:
            tags = list(db.post_has_tag.find({"post_id": post.get("post_id")}).limit(10))
            n += len(tags)

    return n


def exec_ic5(db, p):
    friends = get_friends(db, p["person_id"], max_depth=2, limit=200)
    n = len(friends)

    for pid in friends[:50]:
        memberships = list(db.forum_has_member_person.find({"person_id": pid}).limit(10))
        n += len(memberships)

        for m in memberships[:5]:
            forum_id = m.get("forum_id")
            if forum_id:
                n += db.posts.count_documents({"forum_id": forum_id}, limit=50)

    return n


def exec_ic6(db, p):
    friends = get_friends(db, p["person_id"], max_depth=2, limit=200)
    tag_counter = 0

    for pid in friends[:50]:
        posts = list(db.posts.find({"creator_person_id": pid}).limit(10))
        for post in posts:
            tag_counter += db.post_has_tag.count_documents({"post_id": post.get("post_id")}, limit=20)

    return tag_counter


def exec_ic7(db, p):
    pid = p["person_id"]
    posts = list(db.posts.find({"creator_person_id": pid}).limit(20))
    comments = list(db.comments.find({"creator_person_id": pid}).limit(20))

    n = len(posts) + len(comments)

    for post in posts:
        likes = list(db.person_likes_post.find({"post_id": post.get("post_id")}).limit(20))
        n += len(likes)

    for comment in comments:
        likes = list(db.person_likes_comment.find({"comment_id": comment.get("comment_id")}).limit(20))
        n += len(likes)

    return n


def exec_ins1(db, p):
    new_id = p["new_id"]
    db.persons.insert_one({
        "person_id": new_id,
        "first_name": "Benchmark",
        "last_name": "Person",
        "gender": "unknown",
        "creation_date": str(now_ms()),
        "place_id": p.get("place_id"),
    })
    return 1


def exec_ins2(db, p):
    db.person_likes_post.insert_one({
        "person_id": p["person_id"],
        "post_id": p["post_id"],
        "creation_date": str(now_ms()),
    })
    return 1


def exec_ins3(db, p):
    db.person_likes_comment.insert_one({
        "person_id": p["person_id"],
        "comment_id": p["comment_id"],
        "creation_date": str(now_ms()),
    })
    return 1


def exec_ins4(db, p):
    fid = p["new_id"]
    db.forums.insert_one({
        "forum_id": fid,
        "title": "Benchmark Forum",
        "creation_date": str(now_ms()),
        "moderator_person_id": p["person_id"],
    })
    return 1


def exec_ins5(db, p):
    db.forum_has_member_person.insert_one({
        "forum_id": p["forum_id"],
        "person_id": p["person_id"],
        "join_date": str(now_ms()),
    })
    return 1


def exec_ins6(db, p):
    post_id = p["new_id"]
    db.posts.insert_one({
        "post_id": post_id,
        "creation_date": str(now_ms()),
        "creator_person_id": p["person_id"],
        "forum_id": p["forum_id"],
        "place_id": p["place_id"],
        "content": "benchmark post",
        "length": "14",
    })
    if p.get("tag_id"):
        db.post_has_tag.insert_one({"post_id": post_id, "tag_id": p["tag_id"]})
    return 1


def exec_ins7(db, p):
    comment_id = p["new_id"]
    db.comments.insert_one({
        "comment_id": comment_id,
        "creation_date": str(now_ms()),
        "creator_person_id": p["person_id"],
        "reply_post_id": p["post_id"],
        "place_id": p["place_id"],
        "content": "benchmark comment",
        "length": "17",
    })
    if p.get("tag_id"):
        db.comment_has_tag.insert_one({"comment_id": comment_id, "tag_id": p["tag_id"]})
    return 1


def exec_ins8(db, p):
    db.person_knows_person.insert_one({
        "person1_id": p["person_id"],
        "person2_id": p["new_id"],
        "creation_date": str(now_ms()),
    })
    return 1


QUERY_EXECUTORS = {
    "IS1": exec_is1,
    "IS2": exec_is2,
    "IS3": exec_is3,
    "IS4": exec_is4,
    "IS5": exec_is5,
    "IS6": exec_is6,
    "IS7": exec_is7,
    "IC1": exec_ic1,
    "IC2": exec_ic2,
    "IC3": exec_ic3,
    "IC4": exec_ic4,
    "IC5": exec_ic5,
    "IC6": exec_ic6,
    "IC7": exec_ic7,
    "INS1": exec_ins1,
    "INS2": exec_ins2,
    "INS3": exec_ins3,
    "INS4": exec_ins4,
    "INS5": exec_ins5,
    "INS6": exec_ins6,
    "INS7": exec_ins7,
    "INS8": exec_ins8,
}


def execute_candidate_query(db, official_id: str, repetition: int) -> Tuple[int, str]:
    executor = QUERY_EXECUTORS.get(official_id)
    if executor is None:
        return 0, f"NO_EXECUTOR_FOR_{official_id}"

    params = build_params(db, official_id, repetition)

    try:
        result_count = executor(db, params)
        return int(result_count), "OK"
    except Exception as e:
        return 0, f"ERROR: {type(e).__name__}: {e}"


# =========================================================
# Runner
# =========================================================

def connect_mongo(args) -> MongoClient:
    kwargs = {}

    if args.mongo_username:
        kwargs["username"] = args.mongo_username
        kwargs["password"] = args.mongo_password
        kwargs["authSource"] = args.mongo_auth_source

    return MongoClient(
        host=args.mongo_host,
        port=args.mongo_port,
        serverSelectionTimeoutMS=10000,
        **kwargs,
    )


def build_db_name(prefix: str, candidate_id: str) -> str:
    return safe_name(f"{prefix}_{candidate_id}")


def apply_filters(plan_df: pd.DataFrame, args) -> pd.DataFrame:
    df = plan_df.copy()

    if args.query_name:
        df = df[df["query_name"].isin(args.query_name)]

    if args.official_id:
        df = df[df["official_id"].isin(args.official_id)]

    if args.benchmark_group:
        df = df[df["benchmark_group"].isin(args.benchmark_group)]

    if args.g_class:
        df = df[df["g_class"].isin(args.g_class)]

    if args.max_runs is not None:
        df = df.head(args.max_runs)

    return df.reset_index(drop=True)


def run(args) -> None:
    data_dir = Path(args.data_dir)
    artifacts_dir = Path(args.artifacts_dir)
    results_dir = Path(args.results_dir)
    ensure_dir(results_dir)

    plan_path = artifacts_dir / args.execution_plan
    specs_path = artifacts_dir / "mongodb_candidate_specs_by_candidate_id.json"

    if not plan_path.exists():
        raise FileNotFoundError(f"Execution plan not found: {plan_path}")

    if not specs_path.exists():
        raise FileNotFoundError(f"Candidate specs JSON not found: {specs_path}")

    plan_df = pd.read_csv(plan_path)
    plan_df = apply_filters(plan_df, args)

    candidate_specs = read_json(specs_path)

    log(f"[runner] plan_path={plan_path}", args.verbose)
    log(f"[runner] specs_path={specs_path}", args.verbose)
    log(f"[runner] selected plan rows={len(plan_df)}", args.verbose)

    data = load_ldbc_snb_data(
        data_dir=data_dir,
        row_limit=args.row_limit,
        verbose=args.verbose,
    )

    client = connect_mongo(args)
    client.admin.command("ping")
    log("[mongo] connection OK", args.verbose)

    raw_rows = []
    load_rows = []

    db_prefix = args.execution_db_prefix or f"ldbc_snb_{safe_name(args.scale_label)}"

    for idx, plan_row in plan_df.iterrows():
        candidate_id = plan_row["candidate_id"]
        official_id = plan_row["official_id"]

        spec = candidate_specs.get(candidate_id)
        if not spec:
            raw_rows.append({
                "candidate_id": candidate_id,
                "official_id": official_id,
                "status": "ERROR_MISSING_SPEC",
            })
            continue

        db_name = build_db_name(db_prefix, candidate_id)

        log(
            f"\n[{idx + 1}/{len(plan_df)}] candidate={candidate_id} "
            f"query={official_id} group={plan_row['benchmark_group']} db={db_name}",
            args.verbose,
        )

        load_info = materialize_candidate(
            mongo_client=client,
            db_name=db_name,
            candidate_spec=spec,
            data=data,
            batch_size=args.batch_size,
            force_rebuild=args.force_rebuild_db,
            verbose=args.verbose,
        )

        load_rows.append({
            "candidate_id": candidate_id,
            "official_id": official_id,
            "query_name": plan_row.get("query_name"),
            "benchmark_group": plan_row.get("benchmark_group"),
            "g_class": plan_row.get("g_class"),
            "db_name": db_name,
            "load_seconds": load_info["load_seconds"],
            "load_completed": load_info["load_completed"],
            "loaded_collections_json": json.dumps(load_info["loaded_collections"], ensure_ascii=False),
        })

        db = client[db_name]

        for rep in range(args.repetitions):
            start = time.perf_counter()
            result_count, status = execute_candidate_query(db, official_id, rep)
            elapsed = time.perf_counter() - start

            raw_rows.append({
                "candidate_id": candidate_id,
                "official_id": official_id,
                "query_name": plan_row.get("query_name"),
                "query_group": plan_row.get("query_group"),
                "benchmark_group": plan_row.get("benchmark_group"),
                "g_class": plan_row.get("g_class"),
                "mongodb_pattern": plan_row.get("mongodb_pattern"),
                "document_strategy": plan_row.get("document_strategy"),
                "repetition": rep + 1,
                "elapsed_ms": elapsed * 1000.0,
                "result_count": result_count,
                "status": status,
                "db_name": db_name,
            })

            log(
                f"  rep={rep + 1} elapsed_ms={elapsed * 1000.0:.3f} "
                f"result_count={result_count} status={status}",
                args.verbose,
            )

    raw_df = pd.DataFrame(raw_rows)
    load_df = pd.DataFrame(load_rows)

    raw_path = results_dir / "benchmark_raw_results.csv"
    load_path = results_dir / "candidate_load_summary.csv"

    raw_df.to_csv(raw_path, index=False)
    load_df.to_csv(load_path, index=False)

    if len(raw_df) > 0 and "elapsed_ms" in raw_df.columns:
        agg_df = (
            raw_df
            .groupby([
                "candidate_id", "official_id", "query_name",
                "query_group", "benchmark_group", "g_class",
                "mongodb_pattern", "document_strategy",
            ], dropna=False)
            .agg(
                repetitions=("repetition", "count"),
                mean_elapsed_ms=("elapsed_ms", "mean"),
                median_elapsed_ms=("elapsed_ms", "median"),
                min_elapsed_ms=("elapsed_ms", "min"),
                max_elapsed_ms=("elapsed_ms", "max"),
                mean_result_count=("result_count", "mean"),
                n_failures=("status", lambda x: int((x != "OK").sum())),
            )
            .reset_index()
        )
    else:
        agg_df = pd.DataFrame()

    agg_path = results_dir / "benchmark_aggregate_results.csv"
    agg_df.to_csv(agg_path, index=False)

    run_manifest = {
        "data_dir": str(data_dir),
        "artifacts_dir": str(artifacts_dir),
        "execution_plan": args.execution_plan,
        "results_dir": str(results_dir),
        "scale_label": args.scale_label,
        "n_plan_rows": int(len(plan_df)),
        "repetitions": int(args.repetitions),
        "row_limit": args.row_limit,
        "batch_size": args.batch_size,
        "raw_results": raw_path.name,
        "aggregate_results": agg_path.name,
        "load_summary": load_path.name,
    }

    with open(results_dir / "run_manifest.json", "w", encoding="utf-8") as f:
        json.dump(run_manifest, f, indent=2, ensure_ascii=False)

    log("\n[done] Results saved:", True)
    log(f"  - {raw_path}", True)
    log(f"  - {agg_path}", True)
    log(f"  - {load_path}", True)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--artifacts-dir", required=True)
    parser.add_argument("--results-dir", required=True)

    parser.add_argument("--execution-plan", default="benchmark_execution_plan_smoke.csv")
    parser.add_argument("--scale-label", default="sf0.1")
    parser.add_argument("--execution-db-prefix", default=None)

    parser.add_argument("--mongo-host", default="127.0.0.1")
    parser.add_argument("--mongo-port", type=int, default=27017)
    parser.add_argument("--mongo-username", default=None)
    parser.add_argument("--mongo-password", default=None)
    parser.add_argument("--mongo-auth-source", default="admin")

    parser.add_argument("--batch-size", type=int, default=10000)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--max-runs", type=int, default=None)
    parser.add_argument("--row-limit", type=int, default=None)

    parser.add_argument("--query-name", nargs="*", default=None)
    parser.add_argument("--official-id", nargs="*", default=None)
    parser.add_argument("--benchmark-group", nargs="*", default=None)
    parser.add_argument("--g-class", nargs="*", default=None)

    parser.add_argument("--force-rebuild-db", action="store_true")
    parser.add_argument("--verbose", action="store_true")

    return parser.parse_args()



# =========================================================
# FIBEN-STANDARD OUTPUT PATCH FOR LDBC SNB RUNNER
# =========================================================
#
# This section overrides the previous LDBC runner orchestration
# so that output files and output fields match the FIBEN benchmark runner.
# =========================================================

import sys
import traceback
from datetime import datetime
import numpy as np

GLOBAL_VERBOSE = False
GLOBAL_BATCH_LOG_EVERY = 20
GLOBAL_LOG_INTERVAL_SECONDS = 30.0
GLOBAL_LOG_FILE_PATH = None


def log(msg: str, level: str = "INFO") -> None:
    """
    FIBEN-style logger:
    - prints to terminal
    - writes to execution.log
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = "" if msg is None else str(msg)
    message_lines = message.splitlines() if message.splitlines() else [""]

    for message_line in message_lines:
        line = f"[{ts}] [{level}] {message_line}"
        print(line, flush=True)

        if GLOBAL_LOG_FILE_PATH is not None:
            try:
                log_path = Path(GLOBAL_LOG_FILE_PATH)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:
                pass


def vlog(msg: str, level: str = "INFO") -> None:
    if GLOBAL_VERBOSE:
        log(msg, level=level)


def initialize_execution_log(log_file_path: Path, args) -> None:
    """
    Create/reset execution.log in the same style as the FIBEN runner.
    """
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_file_path, "w", encoding="utf-8") as f:
        f.write("# LDBC SNB MongoDB benchmark execution log\n")
        f.write(f"# Created at: {datetime.now().isoformat()}\n")
        f.write(f"# Command: {' '.join(sys.argv)}\n")
        f.write("#\n")
        f.write(f"# data_dir: {args.data_dir}\n")
        f.write(f"# artifacts_dir: {args.artifacts_dir}\n")
        f.write(f"# results_dir: {args.results_dir}\n")
        f.write(f"# scale_label: {args.scale_label}\n")
        f.write(f"# repetitions: {args.repetitions}\n")
        f.write(f"# row_limit: {args.row_limit}\n")
        f.write(f"# batch_size: {args.batch_size}\n")
        f.write("\n")


def sanitize_mongo_name_fiben(name: str) -> str:
    if name is None:
        return None
    invalid_chars = ["/", "\\", ".", "\"", "$", " ", "\x00", ":"]
    out = str(name)
    for ch in invalid_chars:
        out = out.replace(ch, "_")
    return out


def parse_listlike_cell_fiben(value):
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value is None:
        return []
    if isinstance(value, float) and pd.isna(value):
        return []
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            obj = json.loads(s)
            if isinstance(obj, list):
                return obj
        except Exception:
            pass
        if s.startswith("[") and s.endswith("]"):
            try:
                import ast
                obj = ast.literal_eval(s)
                if isinstance(obj, list):
                    return obj
            except Exception:
                pass
        return [part.strip() for part in s.split(",") if part.strip()]
    return [value]


def normalize_plan_to_fiben_fields(plan_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert LDBC plan columns to the same naming style used by FIBEN.

    LDBC generated:
    - benchmark_group
    - mongodb_pattern
    - root_collection

    FIBEN expects:
    - final_benchmark_group
    - design_pattern
    - collection_name
    """
    df = plan_df.copy()

    if "final_benchmark_group" not in df.columns:
        if "benchmark_group" in df.columns:
            df["final_benchmark_group"] = df["benchmark_group"]
        else:
            df["final_benchmark_group"] = "unknown"

    if "design_pattern" not in df.columns:
        if "mongodb_pattern" in df.columns:
            df["design_pattern"] = df["mongodb_pattern"]
        else:
            df["design_pattern"] = df.get("document_strategy", "unknown")

    if "collection_name" not in df.columns:
        if "root_collection" in df.columns:
            df["collection_name"] = df["root_collection"]
        else:
            df["collection_name"] = df["candidate_id"].apply(lambda x: sanitize_mongo_name_fiben(str(x)))

    if "materialized_entities" not in df.columns:
        df["materialized_entities"] = [[] for _ in range(len(df))]

    if "active_g_classes" not in df.columns:
        df["active_g_classes"] = df["g_class"].apply(lambda x: [x])

    # Keep old column too for compatibility.
    if "benchmark_group" not in df.columns:
        df["benchmark_group"] = df["final_benchmark_group"]

    for col in [
        "embedded_entities",
        "referenced_entities",
        "summarized_entities",
        "edge_collections",
        "reverse_indexes",
        "materialized_entities",
        "active_g_classes",
        "candidate_ids",
    ]:
        if col in df.columns:
            df[col] = df[col].apply(parse_listlike_cell_fiben)

    return df


def load_benchmark_artifacts_fiben_standard(artifacts_dir: Path, execution_plan: str):
    """
    Load benchmark artifacts in the same style as FIBEN, but allowing
    smoke/full execution plan selection.
    """
    execution_plan_path = artifacts_dir / execution_plan
    specs_path = artifacts_dir / "mongodb_candidate_specs_by_candidate_id.json"
    manifest_path = artifacts_dir / "benchmark_manifest.json"

    if not execution_plan_path.exists():
        raise FileNotFoundError(f"Missing benchmark execution plan: {execution_plan_path}")

    if not specs_path.exists():
        raise FileNotFoundError(f"Missing candidate specs: {specs_path}")

    plan_df = pd.read_csv(execution_plan_path)
    plan_df = normalize_plan_to_fiben_fields(plan_df)

    with open(specs_path, "r", encoding="utf-8") as f:
        specs_by_id = json.load(f)

    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = {}

    return plan_df, specs_by_id, manifest


def build_run_template(plan_df: pd.DataFrame, repetitions: int, phases: list) -> pd.DataFrame:
    """
    FIBEN-style run template:
    one row per candidate/query/phase/repetition.
    """
    rows = []

    for _, plan_row in plan_df.iterrows():
        for phase in phases:
            for repetition in range(1, repetitions + 1):
                row = plan_row.to_dict()
                row["run_phase"] = phase
                row["repetition"] = repetition
                rows.append(row)

    return pd.DataFrame(rows)


def select_plan_rows_fiben_standard(plan_df: pd.DataFrame, args) -> pd.DataFrame:
    df = plan_df.copy()

    if args.candidate_id:
        df = df[df["candidate_id"].isin(set(args.candidate_id))]

    if args.query_name:
        df = df[df["query_name"].isin(set(args.query_name))]

    if args.official_id:
        df = df[df["official_id"].isin(set(args.official_id))]

    if args.benchmark_group:
        df = df[df["final_benchmark_group"].isin(set(args.benchmark_group))]

    if args.g_class:
        df = df[df["g_class"].isin(set(args.g_class))]

    if args.max_runs is not None:
        df = df.head(args.max_runs).copy()

    return df.sort_values(
        ["query_name", "final_benchmark_group", "candidate_id"]
    ).reset_index(drop=True)


def estimate_documents_written(official_id: str, result_count: int, success: bool) -> int:
    """
    Convert LDBC query result into FIBEN-style documents_written.
    """
    if not success:
        return 0

    if not str(official_id).startswith("INS"):
        return 0

    # Current LDBC executor returns a count-like value for inserts.
    if result_count is not None and int(result_count) > 0:
        return int(result_count)

    return 1


def estimate_documents_returned(official_id: str, result_count: int, success: bool) -> int:
    """
    Convert LDBC query result into FIBEN-style documents_returned.
    """
    if not success:
        return 0

    if str(official_id).startswith("INS"):
        return 0

    return int(result_count or 0)


def aggregate_benchmark_results(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Same aggregate output schema as the FIBEN runner.
    """
    if results_df.empty:
        return pd.DataFrame()

    def p95(values):
        return float(np.percentile(values, 95)) if values else None

    def p99(values):
        return float(np.percentile(values, 99)) if values else None

    rows = []

    group_cols = [
        "candidate_id",
        "query_name",
        "final_benchmark_group",
        "design_pattern",
        "g_class",
        "scale_label",
        "run_phase",
    ]

    for keys, grp in results_df.groupby(group_cols, dropna=False):
        kd = dict(zip(group_cols, keys))

        lat = [float(x) for x in grp["latency_ms"].dropna().tolist()]
        ret = grp["documents_returned"].dropna().tolist()
        wr = grp["documents_written"].dropna().tolist()

        rows.append({
            **kd,
            "n_runs": int(len(grp)),
            "n_success_runs": int((grp["success"] == True).sum()),
            "avg_latency_ms": float(np.mean(lat)) if lat else None,
            "median_latency_ms": float(np.median(lat)) if lat else None,
            "p95_latency_ms": p95(lat),
            "p99_latency_ms": p99(lat),
            "min_latency_ms": float(np.min(lat)) if lat else None,
            "max_latency_ms": float(np.max(lat)) if lat else None,
            "std_latency_ms": float(np.std(lat)) if lat else None,
            "avg_documents_returned": float(np.mean(ret)) if len(ret) else None,
            "avg_documents_written": float(np.mean(wr)) if len(wr) else None,
        })

    return (
        pd.DataFrame(rows)
        .sort_values(["scale_label", "query_name", "final_benchmark_group", "candidate_id", "run_phase"])
        .reset_index(drop=True)
    )


def run_candidate_benchmark_fiben_standard(
    db,
    cfg: dict,
    template_df: pd.DataFrame,
    args,
) -> pd.DataFrame:
    """
    Run one candidate using FIBEN-style raw output fields.
    """
    candidate_id = cfg["candidate_id"]
    candidate_rows = template_df[template_df["candidate_id"] == candidate_id].copy()

    if args.run_phase:
        candidate_rows = candidate_rows[candidate_rows["run_phase"].isin(set(args.run_phase))]

    log(f"=== BENCHMARK START candidate={candidate_id} rows={len(candidate_rows)} ===")

    rows = []

    for i, (_, run_row) in enumerate(candidate_rows.iterrows(), start=1):
        official_id = run_row["official_id"]
        repetition = int(run_row["repetition"])

        if i == 1 or i % GLOBAL_BATCH_LOG_EVERY == 0:
            log(
                f"[benchmark-progress] candidate={candidate_id} "
                f"row={i}/{len(candidate_rows)} query={run_row['query_name']} "
                f"official_id={official_id} "
                f"group={run_row['final_benchmark_group']} "
                f"phase={run_row['run_phase']} rep={repetition}"
            )

        start_ts = pd.Timestamp.now("UTC")
        t0 = time.perf_counter()

        try:
            max_attempts = 3
            last_status = None
            last_exception = None
            result_count = 0

            for attempt in range(1, max_attempts + 1):
                try:
                    result_count, status = execute_candidate_query(db, official_id, repetition)
                    last_status = status

                    if status == "OK":
                        break

                    # Non-OK logical status: do not retry unless it looks transient.
                    if "AutoReconnect" not in str(status) and "ServerSelectionTimeout" not in str(status):
                        break

                except (AutoReconnect, ServerSelectionTimeoutError, NetworkTimeout) as e:
                    last_exception = e
                    last_status = f"{type(e).__name__}: {e}"

                    if attempt < max_attempts:
                        time.sleep(2 * attempt)
                        continue

                except Exception as e:
                    last_exception = e
                    last_status = f"{type(e).__name__}: {e}"
                    break

            latency_ms = (time.perf_counter() - t0) * 1000.0

            status = last_status or "UNKNOWN"
            success = status == "OK"
            execution_status = "completed" if success else "failed"
            error_message = None if success else status

            documents_returned = estimate_documents_returned(
                official_id=official_id,
                result_count=result_count,
                success=success,
            )
            documents_written = estimate_documents_written(
                official_id=official_id,
                result_count=result_count,
                success=success,
            )

        except Exception as e:
            latency_ms = None
            success = False
            documents_returned = None
            documents_written = None
            execution_status = "failed"
            error_message = f"{type(e).__name__}: {e}"

            if args.verbose:
                log(traceback.format_exc(), level="ERROR")

        end_ts = pd.Timestamp.now("UTC")

        out = run_row.to_dict()
        out.update({
            "start_ts": start_ts,
            "end_ts": end_ts,
            "latency_ms": latency_ms,
            "success": success,
            "documents_returned": documents_returned,
            "documents_written": documents_written,
            "execution_status": execution_status,
            "error_message": error_message,
        })

        rows.append(out)

    log(f"=== BENCHMARK COMPLETED candidate={candidate_id} rows={len(rows)} ===")
    return pd.DataFrame(rows)


def build_arg_parser():
    """
    FIBEN-style CLI, adapted to LDBC SNB.
    """
    p = argparse.ArgumentParser(
        description="Server-side MongoDB benchmark runner for LDBC SNB methodology candidates"
    )

    p.add_argument("--data-dir", required=True, help="Path to the LDBC SNB SF data directory")
    p.add_argument("--artifacts-dir", required=True, help="Path to ldbc_snb_mongo_configurations")
    p.add_argument("--results-dir", required=True, help="Directory where benchmark results will be written")
    p.add_argument("--log-file", default=None, help="Optional execution log file path. Default: <results-dir>/execution.log")

    p.add_argument("--execution-plan", default="benchmark_execution_plan.csv")
    p.add_argument("--scale-label", default="sf0.1")
    p.add_argument("--execution-db-prefix", default="ldbc_snb_exec")

    p.add_argument("--mongo-host", default="127.0.0.1")
    p.add_argument("--mongo-port", type=int, default=27017)
    p.add_argument("--mongo-username", default=None)
    p.add_argument("--mongo-password", default=None)
    p.add_argument("--mongo-auth-source", default="admin")

    p.add_argument("--candidate-id", nargs="*")
    p.add_argument("--query-name", nargs="*")
    p.add_argument("--official-id", nargs="*")
    p.add_argument("--benchmark-group", nargs="*", choices=["primary", "secondary_affected", "control"])
    p.add_argument("--g-class", nargs="*")
    p.add_argument("--run-phase", nargs="*", choices=["cold", "hot"])

    p.add_argument("--repetitions", type=int, default=5)
    p.add_argument("--max-runs", type=int, default=None)
    p.add_argument("--row-limit", type=int, default=None)
    p.add_argument("--batch-size", type=int, default=10000)
    p.add_argument("--batch-log-every", type=int, default=20)
    p.add_argument("--log-interval-seconds", type=float, default=30.0)
    p.add_argument("--sample-size", type=int, default=20)

    p.add_argument("--force-rebuild-db", action="store_true")
    p.add_argument("--skip-candidate-load", action="store_true")
    p.add_argument("--verbose", action="store_true")

    return p


def main():
    """
    FIBEN-style orchestration adapted to LDBC SNB.
    """
    global GLOBAL_VERBOSE, GLOBAL_BATCH_LOG_EVERY, GLOBAL_LOG_INTERVAL_SECONDS, GLOBAL_LOG_FILE_PATH

    args = build_arg_parser().parse_args()

    GLOBAL_VERBOSE = bool(args.verbose)
    GLOBAL_BATCH_LOG_EVERY = max(1, int(args.batch_log_every))
    GLOBAL_LOG_INTERVAL_SECONDS = float(args.log_interval_seconds)

    data_dir = Path(args.data_dir)
    artifacts_dir = Path(args.artifacts_dir)
    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    GLOBAL_LOG_FILE_PATH = (
        Path(args.log_file)
        if args.log_file is not None
        else results_dir / "execution.log"
    )

    initialize_execution_log(Path(GLOBAL_LOG_FILE_PATH), args)

    log(f"Execution log file: {GLOBAL_LOG_FILE_PATH}")
    log(f"Command: {' '.join(sys.argv)}")

    plan_df, specs_by_id, manifest = load_benchmark_artifacts_fiben_standard(
        artifacts_dir=artifacts_dir,
        execution_plan=args.execution_plan,
    )

    selected_plan_df = select_plan_rows_fiben_standard(plan_df, args)

    if selected_plan_df.empty:
        raise SystemExit("No benchmark configurations selected after filters.")

    log(f"Selected plan rows: {len(selected_plan_df)}")
    log(f"Selected candidates: {selected_plan_df['candidate_id'].nunique()}")

    # -----------------------------------------------------
    # Load LDBC data into memory once.
    # This replaces the FIBEN DuckDB initialization stage.
    # We still write scale_db_initialization_summary.csv
    # to keep the result files standardized.
    # -----------------------------------------------------

    initialization_rows = []
    t_init = time.perf_counter()

    data = load_ldbc_snb_data(
        data_dir=data_dir,
        row_limit=args.row_limit,
        verbose=args.verbose,
    )

    init_elapsed = time.perf_counter() - t_init

    init_summary = {
        "scale_label": args.scale_label,
        "data_dir": str(data_dir),
        "row_limit": args.row_limit,
        "elapsed_seconds": init_elapsed,
        "initialization_status": "completed",
        "error_message": None,
    }

    for name, df in data.items():
        try:
            init_summary[f"{name}_rows"] = int(len(df))
        except Exception:
            pass

    initialization_rows.append(init_summary)

    # -----------------------------------------------------
    # Mongo connection
    # -----------------------------------------------------

    client = connect_mongo(args)
    client.admin.command("ping")
    log("MongoDB connection OK")

    execution_db_name = sanitize_mongo_name_fiben(
        f"{args.execution_db_prefix}_{args.scale_label}"
    )

    unique_candidates_df = (
        selected_plan_df
        .drop_duplicates(subset=["candidate_id"])
        .reset_index(drop=True)
    )

    candidate_load_rows = []
    raw_frames = []
    agg_frames = []

    phases = args.run_phase if args.run_phase else ["cold", "hot"]

    template_df = build_run_template(
        selected_plan_df,
        repetitions=args.repetitions,
        phases=phases,
    )

    try:
        for i, (_, candidate_row) in enumerate(unique_candidates_df.iterrows(), start=1):
            candidate_id = candidate_row["candidate_id"]
            spec = specs_by_id.get(candidate_id)

            if spec is None:
                log(f"Missing candidate spec for {candidate_id}", level="ERROR")
                continue

            db_name = build_db_name(args.execution_db_prefix, candidate_id)
            db = client[db_name]

            log(
                f"=== CANDIDATE {i}/{len(unique_candidates_df)} "
                f"candidate={candidate_id} db={db_name} ==="
            )

            if not args.skip_candidate_load:
                t0 = time.perf_counter()

                try:
                    load_info = materialize_candidate(
                        mongo_client=client,
                        db_name=db_name,
                        candidate_spec=spec,
                        data=data,
                        batch_size=args.batch_size,
                        force_rebuild=args.force_rebuild_db,
                        verbose=args.verbose,
                    )

                    loaded_collections = load_info.get("loaded_collections", {})
                    documents_inserted = sum(int(v or 0) for v in loaded_collections.values())

                    summary = {
                        "candidate_id": candidate_id,
                        "query_name": candidate_row.get("query_name"),
                        "official_id": candidate_row.get("official_id"),
                        "final_benchmark_group": candidate_row.get("final_benchmark_group"),
                        "g_class": candidate_row.get("g_class"),
                        "design_pattern": candidate_row.get("design_pattern"),
                        "collection_name": candidate_row.get("collection_name"),
                        "root_entity": candidate_row.get("root_entity"),
                        "db_name": db_name,
                        "documents_inserted": documents_inserted,
                        "loaded_collections_json": json.dumps(loaded_collections, ensure_ascii=False),
                        "elapsed_seconds": time.perf_counter() - t0,
                        "load_status": "completed",
                        "error_message": None,
                    }

                except Exception as e:
                    summary = {
                        "candidate_id": candidate_id,
                        "query_name": candidate_row.get("query_name"),
                        "official_id": candidate_row.get("official_id"),
                        "final_benchmark_group": candidate_row.get("final_benchmark_group"),
                        "g_class": candidate_row.get("g_class"),
                        "design_pattern": candidate_row.get("design_pattern"),
                        "collection_name": candidate_row.get("collection_name"),
                        "root_entity": candidate_row.get("root_entity"),
                        "db_name": db_name,
                        "documents_inserted": None,
                        "loaded_collections_json": None,
                        "elapsed_seconds": time.perf_counter() - t0,
                        "load_status": "failed",
                        "error_message": f"{type(e).__name__}: {e}",
                    }

                    if args.verbose:
                        log(traceback.format_exc(), level="ERROR")

                candidate_load_rows.append(summary)

            else:
                log("Skipping candidate load because --skip-candidate-load was set.")

            cfg = {
                "candidate_id": candidate_id,
                "query_name": candidate_row.get("query_name"),
                "official_id": candidate_row.get("official_id"),
                "collection_name": candidate_row.get("collection_name"),
                "root_entity": candidate_row.get("root_entity"),
                "g_class": candidate_row.get("g_class"),
                "design_pattern": candidate_row.get("design_pattern"),
                "final_benchmark_group": candidate_row.get("final_benchmark_group"),
            }

            raw_df = run_candidate_benchmark_fiben_standard(
                db=db,
                cfg=cfg,
                template_df=template_df,
                args=args,
            )

            if not raw_df.empty:
                raw_df["scale_label"] = args.scale_label
                raw_df["execution_db_name"] = db_name
                raw_frames.append(raw_df)

                agg_df = aggregate_benchmark_results(raw_df)
                agg_frames.append(agg_df)

    finally:
        client.close()

    # -----------------------------------------------------
    # Save output files with FIBEN-compatible names.
    # -----------------------------------------------------

    if initialization_rows:
        init_path = results_dir / "scale_db_initialization_summary.csv"
        pd.DataFrame(initialization_rows).to_csv(init_path, index=False)
        log(f"Saved initialization summary: {init_path}")

    if candidate_load_rows:
        load_path = results_dir / "candidate_load_summary.csv"
        pd.DataFrame(candidate_load_rows).to_csv(load_path, index=False)
        log(f"Saved candidate load summary: {load_path}")

    if raw_frames:
        raw_path = results_dir / "benchmark_raw_results.csv"
        pd.concat(raw_frames, ignore_index=True).to_csv(raw_path, index=False)
        log(f"Saved raw benchmark results: {raw_path}")

    if agg_frames:
        agg_path = results_dir / "benchmark_aggregate_results.csv"
        pd.concat(agg_frames, ignore_index=True).to_csv(agg_path, index=False)
        log(f"Saved aggregate benchmark results: {agg_path}")

    run_manifest = {
        "script": "run_ldbc_snb_mongo_benchmark.py",
        "data_dir": str(data_dir),
        "artifacts_dir": str(artifacts_dir),
        "results_dir": str(results_dir),
        "scale_label": args.scale_label,
        "execution_db_name": execution_db_name,
        "execution_log_file": str(GLOBAL_LOG_FILE_PATH),
        "execution_plan": args.execution_plan,
        "n_selected_candidates": int(selected_plan_df["candidate_id"].nunique()),
        "n_selected_plan_rows": int(len(selected_plan_df)),
        "repetitions": int(args.repetitions),
        "phases": phases,
        "row_limit": args.row_limit,
        "batch_size": args.batch_size,
    }

    run_manifest_path = results_dir / "benchmark_run_manifest.json"

    with open(run_manifest_path, "w", encoding="utf-8") as f:
        json.dump(run_manifest, f, indent=2, ensure_ascii=False)

    log(f"Saved run manifest: {run_manifest_path}")
    log(f"Done. Results in: {results_dir}")


if __name__ == "__main__":
    main()
