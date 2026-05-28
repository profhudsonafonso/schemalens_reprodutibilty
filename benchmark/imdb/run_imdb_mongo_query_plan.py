#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import time
import uuid
import traceback
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import duckdb
import numpy as np
import pandas as pd
from pymongo import MongoClient
from pymongo.errors import BulkWriteError

# ===================== CONFIG =====================
MONGO_HOST = "127.0.0.1"
MONGO_PORT = 27018
MONGO_USERNAME = "mongo"
MONGO_PASSWORD = "mongo"
MONGO_AUTH_SOURCE = "admin"

IMDB_SF_PATHS = {
    "sf0.25": "/home/hudson/Documents/framework_test/imdb/data/sf_025",
    "sf0.5": "/home/hudson/Documents/framework_test/imdb/data/sf_050",
    "sf1": "/home/hudson/Documents/framework_test/imdb/data/sf_1",
}

TSV_SCHEMAS = {
    "name_basics": {"filename": "name.basics.tsv", "max_line_size": 4 * 1024 * 1024, "columns": {
        "nconst": "VARCHAR","primaryName": "VARCHAR","birthYear": "VARCHAR","deathYear": "VARCHAR",
        "primaryProfession": "VARCHAR","knownForTitles": "VARCHAR"}},
    "title_akas": {"filename": "title.akas.tsv", "max_line_size": 4 * 1024 * 1024, "columns": {
        "titleId": "VARCHAR","ordering": "VARCHAR","title": "VARCHAR","region": "VARCHAR",
        "language": "VARCHAR","types": "VARCHAR","attributes": "VARCHAR","isOriginalTitle": "VARCHAR"}},
    "title_basics": {"filename": "title.basics.tsv", "max_line_size": 8 * 1024 * 1024, "columns": {
        "tconst": "VARCHAR","titleType": "VARCHAR","primaryTitle": "VARCHAR","originalTitle": "VARCHAR",
        "isAdult": "VARCHAR","startYear": "VARCHAR","endYear": "VARCHAR","runtimeMinutes": "VARCHAR","genres": "VARCHAR"}},
    "title_crew": {"filename": "title.crew.tsv", "max_line_size": 4 * 1024 * 1024, "columns": {
        "tconst": "VARCHAR","directors": "VARCHAR","writers": "VARCHAR"}},
    "title_episode": {"filename": "title.episode.tsv", "max_line_size": 4 * 1024 * 1024, "columns": {
        "tconst": "VARCHAR","parentTconst": "VARCHAR","seasonNumber": "VARCHAR","episodeNumber": "VARCHAR"}},
    "title_principals": {"filename": "title.principals.tsv", "max_line_size": 16 * 1024 * 1024, "columns": {
        "tconst": "VARCHAR","ordering": "VARCHAR","nconst": "VARCHAR","category": "VARCHAR","job": "VARCHAR","characters": "VARCHAR"}},
    "title_ratings": {"filename": "title.ratings.tsv", "max_line_size": 2 * 1024 * 1024, "columns": {
        "tconst": "VARCHAR","averageRating": "DOUBLE","numVotes": "BIGINT"}},
}

GLOBAL_VERBOSE = False
GLOBAL_BATCH_LOG_EVERY = 20
GLOBAL_LOG_FILE: Optional[Path] = None


# ===================== LOGGING =====================
def log(msg: str, level: str = "INFO") -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    if GLOBAL_LOG_FILE is not None:
        try:
            GLOBAL_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with GLOBAL_LOG_FILE.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            # Do not fail the experiment because logging-to-file failed.
            pass


def vlog(msg: str, level: str = "INFO") -> None:
    if GLOBAL_VERBOSE:
        log(msg, level=level)


# ===================== HELPERS =====================
def sanitize_mongo_name(name: str) -> str:
    if name is None:
        return None
    invalid_chars = ['/', '\\', '.', '"', '$', ' ', '\x00']
    out = str(name)
    for ch in invalid_chars:
        out = out.replace(ch, '_')
    return out


def parse_listlike_cell(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    if isinstance(value, float) and math.isnan(value):
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
        return [part.strip() for part in s.split(",") if part.strip()]
    return []


def sql_quote(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def sql_in_list(values: Iterable[str]) -> str:
    values = list(values)
    if not values:
        return "('')"
    return "(" + ", ".join(sql_quote(v) for v in values) + ")"


def mongo_client() -> MongoClient:
    return MongoClient(
        host=MONGO_HOST,
        port=MONGO_PORT,
        username=MONGO_USERNAME,
        password=MONGO_PASSWORD,
        authSource=MONGO_AUTH_SOURCE,
    )


def drop_database_if_exists(client: MongoClient, db_name: str) -> None:
    if db_name in client.list_database_names():
        log(f"Removing Mongo database: {db_name}")
        client.drop_database(db_name)


def safe_insert_many(collection, docs: List[dict]) -> int:
    if not docs:
        return 0
    try:
        collection.insert_many(docs, ordered=False)
        return len(docs)
    except BulkWriteError as e:
        return len(docs) - len(e.details.get("writeErrors", []))


def duckdb_columns_map_sql(columns: Dict[str, str]) -> str:
    return "{" + ", ".join(f"'{k}': '{v}'" for k, v in columns.items()) + "}"


def create_tsv_view(con, view_name: str, file_path: Path, columns: Dict[str, str], max_line_size: int) -> None:
    file_sql = str(file_path).replace("\\", "/").replace("'", "''")
    columns_sql = duckdb_columns_map_sql(columns)
    sql = f"""
    CREATE OR REPLACE VIEW {view_name} AS
    SELECT *
    FROM read_csv(
        '{file_sql}',
        delim='\t',
        header=true,
        columns={columns_sql},
        nullstr='\\N',
        auto_detect=false,
        parallel=false,
        quote='',
        escape='',
        max_line_size={max_line_size}
    );
    """
    con.execute(sql)


def create_semantic_views(con) -> None:
    con.execute("""
    CREATE OR REPLACE VIEW imdb_watchitems AS
    SELECT
        b.tconst AS watchitem_id,
        b.titleType AS title_type,
        b.primaryTitle AS title,
        b.originalTitle AS original_title,
        b.isAdult AS is_adult,
        b.startYear AS release_year,
        b.endYear AS end_year,
        b.runtimeMinutes AS runtime_minutes,
        CASE WHEN b.genres IS NULL THEN NULL ELSE split_part(b.genres, ',', 1) END AS primary_genre,
        r.averageRating AS avg_rating,
        r.numVotes AS num_votes
    FROM imdb_title_basics b
    LEFT JOIN imdb_title_ratings r ON b.tconst = r.tconst
    """)

    con.execute("""
    CREATE OR REPLACE VIEW imdb_persons AS
    SELECT
        nconst AS person_id,
        primaryName AS person_name,
        birthYear AS birth_year,
        deathYear AS death_year,
        primaryProfession AS primary_profession,
        knownForTitles AS known_for_titles
    FROM imdb_name_basics
    """)

    con.execute("""
    CREATE OR REPLACE VIEW imdb_roles AS
    SELECT
        tconst || '#' || ordering AS role_id,
        tconst AS watchitem_id,
        nconst AS person_id,
        ordering AS principal_order,
        category AS role_category,
        job,
        characters
    FROM imdb_title_principals
    """)

    con.execute("""
    CREATE OR REPLACE VIEW imdb_series AS
    SELECT
        watchitem_id AS series_watchitem_id,
        title,
        original_title,
        release_year,
        end_year,
        runtime_minutes,
        primary_genre,
        avg_rating,
        num_votes
    FROM imdb_watchitems
    WHERE title_type = 'tvSeries'
    """)

    con.execute("""
    CREATE OR REPLACE VIEW imdb_episodes AS
    SELECT
        e.tconst AS episode_watchitem_id,
        e.parentTconst AS series_watchitem_id,
        e.seasonNumber AS season_number,
        e.episodeNumber AS episode_number
    FROM imdb_title_episode e
    """)


def open_imdb_duckdb_for_scale(scale_label: str):
    sf_dir = Path(IMDB_SF_PATHS[scale_label])
    if not sf_dir.exists():
        raise FileNotFoundError(f"Scale-factor folder not found: {sf_dir}")

    log(f"Opening DuckDB for {scale_label} from {sf_dir}")
    con = duckdb.connect(database=":memory:")
    try:
        con.execute("PRAGMA disable_progress_bar")
    except Exception:
        pass

    for alias, spec in TSV_SCHEMAS.items():
        file_path = sf_dir / spec["filename"]
        if not file_path.exists():
            raise FileNotFoundError(f"Missing TSV file: {file_path}")
        vlog(f"Creating DuckDB view imdb_{alias}")
        create_tsv_view(con, f"imdb_{alias}", file_path, spec["columns"], spec["max_line_size"])

    create_semantic_views(con)
    return con


def iter_query_batches(con, base_sql: str, order_col: str, batch_size: int, row_limit: Optional[int] = None):
    offset = 0
    batch_no = 0
    while True:
        current_limit = batch_size
        if row_limit is not None:
            remaining = row_limit - offset
            if remaining <= 0:
                break
            current_limit = min(current_limit, remaining)
        sql = f"""
        {base_sql}
        ORDER BY {order_col}
        LIMIT {current_limit}
        OFFSET {offset}
        """
        df = con.execute(sql).df()
        if df.empty:
            break
        batch_no += 1
        yield batch_no, df
        offset += len(df)


# ===================== DATA FETCHERS =====================
def fetch_roles_for_watchitems(con, watchitem_ids):
    if not watchitem_ids:
        return pd.DataFrame(columns=["role_id","watchitem_id","person_id","principal_order","role_category","job","characters"])
    sql = f"""
    SELECT role_id, watchitem_id, person_id, principal_order, role_category, job, characters
    FROM imdb_roles
    WHERE watchitem_id IN {sql_in_list(watchitem_ids)}
    ORDER BY watchitem_id, principal_order
    """
    return con.execute(sql).df()


def fetch_persons_by_ids(con, person_ids):
    if not person_ids:
        return {}
    sql = f"""
    SELECT person_id, person_name, birth_year, death_year, primary_profession, known_for_titles
    FROM imdb_persons
    WHERE person_id IN {sql_in_list(person_ids)}
    """
    df = con.execute(sql).df()
    return {row["person_id"]: row.to_dict() for _, row in df.iterrows()}


def fetch_episodes_for_series(con, series_ids):
    if not series_ids:
        return pd.DataFrame(columns=["episode_watchitem_id","series_watchitem_id","season_number","episode_number","title","primary_genre","avg_rating","release_year"])
    sql = f"""
    SELECT
        e.episode_watchitem_id,
        e.series_watchitem_id,
        e.season_number,
        e.episode_number,
        w.title,
        w.primary_genre,
        w.avg_rating,
        w.release_year
    FROM imdb_episodes e
    LEFT JOIN imdb_watchitems w ON e.episode_watchitem_id = w.watchitem_id
    WHERE e.series_watchitem_id IN {sql_in_list(series_ids)}
    ORDER BY e.series_watchitem_id, e.season_number, e.episode_number
    """
    return con.execute(sql).df()


# ===================== BUILDERS =====================
def base_watchitem_doc(row):
    title_type = row["title_type"]
    return {
        "watchitem_id": row["watchitem_id"],
        "title_type": title_type,
        "title": row["title"],
        "original_title": row["original_title"],
        "is_adult": row["is_adult"],
        "release_year": row["release_year"],
        "end_year": row["end_year"],
        "runtime_minutes": row["runtime_minutes"],
        "primary_genre": row["primary_genre"],
        "avg_rating": row["avg_rating"],
        "num_votes": row["num_votes"],
        "is_movie": title_type == "movie",
        "is_series": title_type == "tvSeries",
        "is_episode": title_type == "tvEpisode",
    }


def build_watchitem_docs(batch_df, config_name, con):
    watchitem_ids = batch_df["watchitem_id"].tolist()
    roles_by_watchitem = defaultdict(list)
    person_map = {}

    if config_name in ["watchitem_g4", "watchitem_g5", "watchitem_g6"]:
        roles_df = fetch_roles_for_watchitems(con, watchitem_ids)
        if not roles_df.empty:
            for _, r in roles_df.iterrows():
                roles_by_watchitem[r["watchitem_id"]].append(r.to_dict())
            if config_name in ["watchitem_g5", "watchitem_g6"]:
                person_map = fetch_persons_by_ids(con, sorted(roles_df["person_id"].dropna().unique().tolist()))

    docs = []
    for _, row in batch_df.iterrows():
        doc = base_watchitem_doc(row)
        wid = row["watchitem_id"]

        if config_name == "watchitem_g2":
            doc["genre_doc"] = {"name": row["primary_genre"]} if pd.notna(row["primary_genre"]) else None

        if config_name == "watchitem_g3":
            doc["subtype_component"] = {
                "subtype": row["title_type"],
                "is_movie": row["title_type"] == "movie",
                "is_series": row["title_type"] == "tvSeries",
                "is_episode": row["title_type"] == "tvEpisode",
            }

        if config_name in ["watchitem_g4", "watchitem_g5", "watchitem_g6"]:
            embedded_roles = []
            for role in roles_by_watchitem.get(wid, []):
                role_doc = {
                    "role_id": role["role_id"],
                    "person_id": role["person_id"],
                    "principal_order": role["principal_order"],
                    "role_category": role["role_category"],
                    "job": role["job"],
                    "characters": role["characters"],
                }
                if config_name == "watchitem_g5":
                    p = person_map.get(role["person_id"])
                    if p is not None:
                        role_doc["person_snapshot"] = {
                            "person_id": p["person_id"],
                            "person_name": p["person_name"],
                            "primary_profession": p["primary_profession"],
                        }
                if config_name == "watchitem_g6":
                    p = person_map.get(role["person_id"])
                    if p is not None:
                        role_doc["person_embedded"] = p
                embedded_roles.append(role_doc)
            doc["roles_embedded"] = embedded_roles

        docs.append(doc)

    return docs


def build_series_docs(batch_df, config_name, con):
    series_ids = batch_df["series_watchitem_id"].tolist()
    episodes_df = fetch_episodes_for_series(con, series_ids)
    episodes_by_series = defaultdict(list)

    if not episodes_df.empty:
        for _, e in episodes_df.iterrows():
            episodes_by_series[e["series_watchitem_id"]].append(e.to_dict())

    docs = []
    for _, row in batch_df.iterrows():
        doc = {
            "series_watchitem_id": row["series_watchitem_id"],
            "title": row["title"],
            "original_title": row["original_title"],
            "release_year": row["release_year"],
            "end_year": row["end_year"],
            "runtime_minutes": row["runtime_minutes"],
            "primary_genre": row["primary_genre"],
            "avg_rating": row["avg_rating"],
            "num_votes": row["num_votes"],
        }
        sid = row["series_watchitem_id"]

        if config_name == "series_g8":
            doc["episodes_embedded"] = [
                {
                    "episode_watchitem_id": e["episode_watchitem_id"],
                    "season_number": e["season_number"],
                    "episode_number": e["episode_number"],
                }
                for e in episodes_by_series.get(sid, [])
            ]

        if config_name == "series_g9":
            doc["episodes_embedded"] = [
                {
                    "episode_watchitem_id": e["episode_watchitem_id"],
                    "season_number": e["season_number"],
                    "episode_number": e["episode_number"],
                    "title": e["title"],
                    "primary_genre": e["primary_genre"],
                    "avg_rating": e["avg_rating"],
                    "release_year": e["release_year"],
                }
                for e in episodes_by_series.get(sid, [])
            ]

        docs.append(doc)

    return docs


# ===================== MATERIALIZATION =====================
def _log_collection_progress(collection_name: str, batch_no: int, batch_count: int, total_count: int) -> None:
    if batch_no == 1 or batch_no % GLOBAL_BATCH_LOG_EVERY == 0:
        log(f"[materialize:{collection_name}] batch={batch_no} batch_docs={batch_count} total_inserted={total_count}")


def load_persons_collection(db, con, row_limit=None, batch_size=1000000):
    coll = db["persons"]
    coll.drop()
    total = 0
    log("[materialize:persons] start")
    sql = "SELECT person_id, person_name, birth_year, death_year, primary_profession, known_for_titles FROM imdb_persons"
    for batch_no, batch in iter_query_batches(con, sql, "person_id", batch_size, row_limit):
        inserted = safe_insert_many(coll, batch.to_dict(orient="records"))
        total += inserted
        _log_collection_progress("persons", batch_no, len(batch), total)
    coll.create_index("person_id", unique=True)
    coll.create_index("person_name")
    log(f"[materialize:persons] completed total_inserted={total}")
    return total


def load_roles_collection(db, con, row_limit=None, batch_size=1000000):
    coll = db["roles"]
    coll.drop()
    total = 0
    log("[materialize:roles] start")
    sql = "SELECT role_id, watchitem_id, person_id, principal_order, role_category, job, characters FROM imdb_roles"
    for batch_no, batch in iter_query_batches(con, sql, "role_id", batch_size, row_limit):
        inserted = safe_insert_many(coll, batch.to_dict(orient="records"))
        total += inserted
        _log_collection_progress("roles", batch_no, len(batch), total)
    coll.create_index("role_id", unique=True)
    coll.create_index("watchitem_id")
    coll.create_index("person_id")
    coll.create_index("role_category")
    log(f"[materialize:roles] completed total_inserted={total}")
    return total


def load_episodes_collection(db, con, row_limit=None, batch_size=1000000):
    coll = db["episodes"]
    coll.drop()
    total = 0
    log("[materialize:episodes] start")
    sql = """
    SELECT
        e.episode_watchitem_id,
        e.series_watchitem_id,
        e.season_number,
        e.episode_number,
        w.title,
        w.primary_genre,
        w.avg_rating,
        w.release_year
    FROM imdb_episodes e
    LEFT JOIN imdb_watchitems w ON e.episode_watchitem_id = w.watchitem_id
    """
    for batch_no, batch in iter_query_batches(con, sql, "episode_watchitem_id", batch_size, row_limit):
        inserted = safe_insert_many(coll, batch.to_dict(orient="records"))
        total += inserted
        _log_collection_progress("episodes", batch_no, len(batch), total)
    coll.create_index("episode_watchitem_id", unique=True)
    coll.create_index("series_watchitem_id")
    log(f"[materialize:episodes] completed total_inserted={total}")
    return total


def replace_watchitems_collection(db, con, config_name, row_limit=None, batch_size=1000000):
    coll = db["watchitems"]
    coll.drop()
    total = 0
    log(f"[replace:watchitems] start config={config_name}")
    sql = """
    SELECT
        watchitem_id, title_type, title, original_title, is_adult,
        release_year, end_year, runtime_minutes, primary_genre, avg_rating, num_votes
    FROM imdb_watchitems
    """
    for batch_no, batch in iter_query_batches(con, sql, "watchitem_id", batch_size, row_limit):
        docs = build_watchitem_docs(batch, config_name, con)
        inserted = safe_insert_many(coll, docs)
        total += inserted
        _log_collection_progress("watchitems", batch_no, len(batch), total)
    coll.create_index("watchitem_id", unique=True)
    coll.create_index("title")
    coll.create_index("primary_genre")
    coll.create_index("title_type")
    coll.create_index("avg_rating")
    coll.create_index("release_year")
    coll.create_index("num_votes")
    coll.create_index([("title", "text")])
    log(f"[replace:watchitems] completed config={config_name} total_inserted={total}")
    return total


def replace_series_collection(db, con, config_name, row_limit=None, batch_size=1000000):
    coll = db["series"]
    coll.drop()
    total = 0
    log(f"[replace:series] start config={config_name}")
    sql = """
    SELECT
        series_watchitem_id, title, original_title, release_year, end_year,
        runtime_minutes, primary_genre, avg_rating, num_votes
    FROM imdb_series
    """
    for batch_no, batch in iter_query_batches(con, sql, "series_watchitem_id", batch_size, row_limit):
        docs = build_series_docs(batch, config_name, con)
        inserted = safe_insert_many(coll, docs)
        total += inserted
        _log_collection_progress("series", batch_no, len(batch), total)
    coll.create_index("series_watchitem_id", unique=True)
    coll.create_index("primary_genre")
    coll.create_index("avg_rating")
    log(f"[replace:series] completed config={config_name} total_inserted={total}")
    return total


def initialize_scale_execution_db(
    client,
    db_name: str,
    con,
    row_limit=None,
    batch_size=1000000,
    load_persons: bool = True,
    load_roles: bool = True,
    load_episodes: bool = True,
):
    log(f"=== INITIALIZING EXECUTION DB {db_name} ===")
    drop_database_if_exists(client, db_name)
    db = client[db_name]

    persons_inserted = 0
    roles_inserted = 0
    episodes_inserted = 0

    if load_persons:
        persons_inserted = load_persons_collection(db, con, row_limit=row_limit, batch_size=batch_size)
    else:
        log("[materialize:persons] skipped by minimal/skip-load option")

    if load_roles:
        roles_inserted = load_roles_collection(db, con, row_limit=row_limit, batch_size=batch_size)
    else:
        log("[materialize:roles] skipped by minimal/skip-load option")

    if load_episodes:
        episodes_inserted = load_episodes_collection(db, con, row_limit=row_limit, batch_size=batch_size)
    else:
        log("[materialize:episodes] skipped by minimal/skip-load option")

    watchitems_inserted = replace_watchitems_collection(db, con, "watchitem_g0", row_limit=row_limit, batch_size=batch_size)
    series_inserted = replace_series_collection(db, con, "series_g7", row_limit=row_limit, batch_size=batch_size)

    log(f"=== EXECUTION DB READY {db_name} persons={persons_inserted} roles={roles_inserted} episodes={episodes_inserted} watchitems={watchitems_inserted} series={series_inserted} ===")
    return {
        "db_name": db_name,
        "persons_inserted": persons_inserted,
        "roles_inserted": roles_inserted,
        "episodes_inserted": episodes_inserted,
        "watchitems_inserted": watchitems_inserted,
        "series_inserted": series_inserted,
        "load_persons": bool(load_persons),
        "load_roles": bool(load_roles),
        "load_episodes": bool(load_episodes),
    }


# ===================== QUERY PARAM POOLS =====================
_query_param_pool_cache = {}


def first_keyword(text):
    if not isinstance(text, str):
        return None
    parts = [p.strip() for p in text.split() if len(p.strip()) >= 3]
    return parts[0] if parts else None


def build_query_parameter_pool(scale_label, con, sample_size=20):
    cache_key = (scale_label, sample_size)
    if cache_key in _query_param_pool_cache:
        return _query_param_pool_cache[cache_key]

    log(f"Building query parameter pool for {scale_label}")
    pool = {}
    pool["QG1_WatchItemById"] = con.execute(f"""
        SELECT watchitem_id
        FROM imdb_watchitems
        WHERE watchitem_id IS NOT NULL
        ORDER BY num_votes DESC NULLS LAST, watchitem_id
        LIMIT {sample_size}
    """).df()["watchitem_id"].tolist()

    pool["QG2_WatchItemByTitle"] = con.execute(f"""
        SELECT title
        FROM imdb_watchitems
        WHERE title IS NOT NULL
        ORDER BY num_votes DESC NULLS LAST, watchitem_id
        LIMIT {sample_size}
    """).df()["title"].tolist()

    pool["QG3_RecommendationByGenreAndSubtype"] = con.execute(f"""
        SELECT primary_genre, title_type
        FROM imdb_watchitems
        WHERE primary_genre IS NOT NULL
          AND title_type IN ('movie', 'tvSeries', 'tvEpisode')
        GROUP BY 1,2
        ORDER BY COUNT(*) DESC, primary_genre, title_type
        LIMIT {sample_size}
    """).df().to_dict(orient="records")

    pool["QG4_AllPersonsOfTypeForWatchItem"] = con.execute(f"""
        SELECT watchitem_id, role_category
        FROM imdb_roles
        WHERE role_category IS NOT NULL
        GROUP BY 1,2
        ORDER BY COUNT(*) DESC, watchitem_id, role_category
        LIMIT {sample_size}
    """).df().to_dict(orient="records")

    pool["QG5_AllPersonsForEpisodesOfSeries"] = con.execute(f"""
        SELECT series_watchitem_id
        FROM imdb_episodes
        WHERE series_watchitem_id IS NOT NULL
        GROUP BY 1
        ORDER BY COUNT(*) DESC, series_watchitem_id
        LIMIT {sample_size}
    """).df()["series_watchitem_id"].tolist()

    pool["QG6_EpisodesOfSeries"] = pool["QG5_AllPersonsForEpisodesOfSeries"]
    pool["QG7_UpdateWatchItemMetadata"] = pool["QG1_WatchItemById"]

    pool["QG8_AddPersonRoleToWatchItem"] = con.execute(f"""
        SELECT watchitem_id
        FROM imdb_watchitems
        WHERE watchitem_id IS NOT NULL
        ORDER BY num_votes DESC NULLS LAST, watchitem_id
        LIMIT {sample_size}
    """).df()["watchitem_id"].tolist()

    pool["QG9_TopRatedSeriesByGenre"] = con.execute(f"""
        SELECT primary_genre
        FROM imdb_series
        WHERE primary_genre IS NOT NULL
        GROUP BY 1
        ORDER BY COUNT(*) DESC, primary_genre
        LIMIT {sample_size}
    """).df()["primary_genre"].tolist()

    adv_df = con.execute(f"""
        SELECT title, primary_genre, release_year, avg_rating, title_type
        FROM imdb_watchitems
        WHERE title IS NOT NULL
          AND primary_genre IS NOT NULL
          AND title_type IN ('movie', 'tvSeries', 'tvEpisode')
        ORDER BY num_votes DESC NULLS LAST, watchitem_id
        LIMIT {sample_size}
    """).df()

    pool["QG10_AdvancedSearchWatchItems"] = [
        {
            "keyword": first_keyword(row["title"]),
            "genre": row["primary_genre"],
            "year_min": row["release_year"],
            "rating_min": row["avg_rating"],
            "subtype": row["title_type"],
        }
        for _, row in adv_df.iterrows()
    ]

    _query_param_pool_cache[cache_key] = pool
    log(f"Parameter pool ready for {scale_label}")
    return pool


def pick_param_for_run(pool, query_name, repetition):
    values = pool.get(query_name, [])
    if not values:
        return None
    return values[(repetition - 1) % len(values)]


# ===================== QUERY EXECUTION =====================
def execute_qg1(db, cfg, param):
    t0 = time.perf_counter()
    doc = db["watchitems"].find_one({"watchitem_id": param})
    latency_ms = (time.perf_counter() - t0) * 1000
    return {"latency_ms": latency_ms, "success": True, "documents_returned": 1 if doc else 0, "documents_written": 0}


def execute_qg2(db, cfg, param):
    t0 = time.perf_counter()
    docs = list(db["watchitems"].find({"title": param}).limit(20))
    latency_ms = (time.perf_counter() - t0) * 1000
    return {"latency_ms": latency_ms, "success": True, "documents_returned": len(docs), "documents_written": 0}


def execute_qg3(db, cfg, param):
    query = {"title_type": param["title_type"]}
    query["genre_doc.name" if cfg["config_name"] == "watchitem_g2" else "primary_genre"] = param["primary_genre"]
    t0 = time.perf_counter()
    docs = list(db["watchitems"].find(query).sort("avg_rating", -1).limit(20))
    latency_ms = (time.perf_counter() - t0) * 1000
    return {"latency_ms": latency_ms, "success": True, "documents_returned": len(docs), "documents_written": 0}


def execute_qg4(db, cfg, param):
    watchitem_id = param["watchitem_id"]
    role_category = param["role_category"]
    t0 = time.perf_counter()

    if cfg["config_name"] == "watchitem_g6":
        doc = db["watchitems"].find_one({"watchitem_id": watchitem_id}, {"roles_embedded": 1})
        roles = doc.get("roles_embedded", []) if doc else []
        persons = [r.get("person_embedded") for r in roles if r.get("role_category") == role_category and r.get("person_embedded")]
        n = len(persons)
    elif cfg["config_name"] == "watchitem_g5":
        doc = db["watchitems"].find_one({"watchitem_id": watchitem_id}, {"roles_embedded": 1})
        roles = doc.get("roles_embedded", []) if doc else []
        persons = [r.get("person_snapshot") for r in roles if r.get("role_category") == role_category and r.get("person_snapshot")]
        n = len(persons)
    elif cfg["config_name"] == "watchitem_g4":
        doc = db["watchitems"].find_one({"watchitem_id": watchitem_id}, {"roles_embedded": 1})
        roles = doc.get("roles_embedded", []) if doc else []
        person_ids = [r.get("person_id") for r in roles if r.get("role_category") == role_category]
        persons = list(db["persons"].find({"person_id": {"$in": person_ids}})) if person_ids else []
        n = len(persons)
    else:
        roles = list(db["roles"].find({"watchitem_id": watchitem_id, "role_category": role_category}))
        person_ids = [r["person_id"] for r in roles]
        persons = list(db["persons"].find({"person_id": {"$in": person_ids}})) if person_ids else []
        n = len(persons)

    latency_ms = (time.perf_counter() - t0) * 1000
    return {"latency_ms": latency_ms, "success": True, "documents_returned": n, "documents_written": 0}


def _persons_for_episode_watchitems(db, cfg, episode_watchitem_ids):
    if not episode_watchitem_ids:
        return 0

    if cfg["config_name"] == "watchitem_g6":
        docs = list(db["watchitems"].find({"watchitem_id": {"$in": episode_watchitem_ids}}, {"roles_embedded": 1}))
        n = 0
        for d in docs:
            for r in d.get("roles_embedded", []):
                if r.get("person_embedded"):
                    n += 1
        return n

    if cfg["config_name"] == "watchitem_g5":
        docs = list(db["watchitems"].find({"watchitem_id": {"$in": episode_watchitem_ids}}, {"roles_embedded": 1}))
        n = 0
        for d in docs:
            for r in d.get("roles_embedded", []):
                if r.get("person_snapshot"):
                    n += 1
        return n

    if cfg["config_name"] == "watchitem_g4":
        docs = list(db["watchitems"].find({"watchitem_id": {"$in": episode_watchitem_ids}}, {"roles_embedded": 1}))
        person_ids = []
        for d in docs:
            for r in d.get("roles_embedded", []):
                if r.get("person_id"):
                    person_ids.append(r["person_id"])
        return db["persons"].count_documents({"person_id": {"$in": person_ids}}) if person_ids else 0

    roles = list(db["roles"].find({"watchitem_id": {"$in": episode_watchitem_ids}}, {"person_id": 1}))
    person_ids = [r["person_id"] for r in roles if "person_id" in r]
    return db["persons"].count_documents({"person_id": {"$in": person_ids}}) if person_ids else 0


def execute_qg5(db, cfg, param):
    series_watchitem_id = param
    t0 = time.perf_counter()

    if cfg["selected_root"] == "Series" and cfg["config_name"] in ["series_g8", "series_g9"]:
        sdoc = db["series"].find_one({"series_watchitem_id": series_watchitem_id}, {"episodes_embedded": 1})
        episode_ids = [e["episode_watchitem_id"] for e in sdoc.get("episodes_embedded", [])] if sdoc else []
    else:
        episode_ids = [e["episode_watchitem_id"] for e in db["episodes"].find({"series_watchitem_id": series_watchitem_id}, {"episode_watchitem_id": 1})]

    n = _persons_for_episode_watchitems(db, cfg, episode_ids)
    latency_ms = (time.perf_counter() - t0) * 1000
    return {"latency_ms": latency_ms, "success": True, "documents_returned": n, "documents_written": 0}


def execute_qg6(db, cfg, param):
    series_watchitem_id = param
    t0 = time.perf_counter()

    if cfg["selected_root"] == "Series" and cfg["config_name"] in ["series_g8", "series_g9"]:
        sdoc = db["series"].find_one({"series_watchitem_id": series_watchitem_id}, {"episodes_embedded": 1})
        episodes = sdoc.get("episodes_embedded", []) if sdoc else []
        n = len(episodes)
    else:
        n = db["episodes"].count_documents({"series_watchitem_id": series_watchitem_id})

    latency_ms = (time.perf_counter() - t0) * 1000
    return {"latency_ms": latency_ms, "success": True, "documents_returned": n, "documents_written": 0}


def execute_qg7(db, cfg, param, repetition):
    t0 = time.perf_counter()
    result = db["watchitems"].update_one(
        {"watchitem_id": param},
        {"$set": {"benchmark_runtime_minutes": f"bench_{repetition}", "benchmark_marker": f"run_{repetition}"}}
    )
    latency_ms = (time.perf_counter() - t0) * 1000
    return {"latency_ms": latency_ms, "success": True, "documents_returned": 0, "documents_written": int(result.modified_count)}


def execute_qg8(db, cfg, param, repetition):
    watchitem_id = param
    new_person_id = f"bench_person_{uuid.uuid4().hex[:12]}"
    new_role_id = f"{watchitem_id}#bench_{uuid.uuid4().hex[:8]}"

    person_doc = {
        "person_id": new_person_id,
        "person_name": f"Benchmark Person {repetition}",
        "birth_year": None,
        "death_year": None,
        "primary_profession": "benchmark_person",
        "known_for_titles": None,
    }
    role_doc = {
        "role_id": new_role_id,
        "watchitem_id": watchitem_id,
        "person_id": new_person_id,
        "principal_order": "999999",
        "role_category": "benchmark_role",
        "job": "benchmark_job",
        "characters": None,
    }
    embedded_role_doc = {
        "role_id": new_role_id,
        "person_id": new_person_id,
        "principal_order": "999999",
        "role_category": "benchmark_role",
        "job": "benchmark_job",
        "characters": None,
    }

    if cfg["config_name"] == "watchitem_g5":
        embedded_role_doc["person_snapshot"] = {
            "person_id": new_person_id,
            "person_name": person_doc["person_name"],
            "primary_profession": person_doc["primary_profession"],
        }

    if cfg["config_name"] == "watchitem_g6":
        embedded_role_doc["person_embedded"] = person_doc.copy()

    t0 = time.perf_counter()
    db["persons"].insert_one(person_doc)
    db["roles"].insert_one(role_doc)
    if cfg["config_name"] in ["watchitem_g4", "watchitem_g5", "watchitem_g6"]:
        db["watchitems"].update_one({"watchitem_id": watchitem_id}, {"$push": {"roles_embedded": embedded_role_doc}})
    latency_ms = (time.perf_counter() - t0) * 1000

    db["roles"].delete_one({"role_id": new_role_id})
    db["persons"].delete_one({"person_id": new_person_id})
    if cfg["config_name"] in ["watchitem_g4", "watchitem_g5", "watchitem_g6"]:
        db["watchitems"].update_one({"watchitem_id": watchitem_id}, {"$pull": {"roles_embedded": {"role_id": new_role_id}}})

    return {"latency_ms": latency_ms, "success": True, "documents_returned": 0, "documents_written": 2}


def execute_qg9(db, cfg, param):
    genre = param
    t0 = time.perf_counter()

    if cfg["selected_root"] == "Series":
        docs = list(db["series"].find({"primary_genre": genre}).sort("avg_rating", -1).limit(20))
    else:
        docs = list(db["watchitems"].find({"title_type": "tvSeries", "primary_genre": genre}).sort("avg_rating", -1).limit(20))

    latency_ms = (time.perf_counter() - t0) * 1000
    return {"latency_ms": latency_ms, "success": True, "documents_returned": len(docs), "documents_written": 0}


def execute_qg10(db, cfg, param):
    query = {}
    keyword = param.get("keyword")
    genre = param.get("genre")
    year_min = param.get("year_min")
    rating_min = param.get("rating_min")
    subtype = param.get("subtype")

    if keyword:
        query["title"] = {"$regex": keyword, "$options": "i"}
    if genre:
        query["genre_doc.name" if cfg["config_name"] == "watchitem_g2" else "primary_genre"] = genre
    if subtype:
        query["subtype_component.subtype" if cfg["config_name"] == "watchitem_g3" else "title_type"] = subtype
    if year_min not in [None, "", "None"]:
        query["release_year"] = {"$gte": year_min}
    if rating_min not in [None, "", "None"]:
        query["avg_rating"] = {"$gte": rating_min}

    t0 = time.perf_counter()
    docs = list(db["watchitems"].find(query).sort("avg_rating", -1).limit(20))
    latency_ms = (time.perf_counter() - t0) * 1000
    return {"latency_ms": latency_ms, "success": True, "documents_returned": len(docs), "documents_written": 0}


def execute_query_by_name(db, cfg, query_name, param, repetition):
    if query_name == "QG1_WatchItemById": return execute_qg1(db, cfg, param)
    if query_name == "QG2_WatchItemByTitle": return execute_qg2(db, cfg, param)
    if query_name == "QG3_RecommendationByGenreAndSubtype": return execute_qg3(db, cfg, param)
    if query_name == "QG4_AllPersonsOfTypeForWatchItem": return execute_qg4(db, cfg, param)
    if query_name == "QG5_AllPersonsForEpisodesOfSeries": return execute_qg5(db, cfg, param)
    if query_name == "QG6_EpisodesOfSeries": return execute_qg6(db, cfg, param)
    if query_name == "QG7_UpdateWatchItemMetadata": return execute_qg7(db, cfg, param, repetition)
    if query_name == "QG8_AddPersonRoleToWatchItem": return execute_qg8(db, cfg, param, repetition)
    if query_name == "QG9_TopRatedSeriesByGenre": return execute_qg9(db, cfg, param)
    if query_name == "QG10_AdvancedSearchWatchItems": return execute_qg10(db, cfg, param)
    raise KeyError(f"Unsupported query: {query_name}")


# ===================== QUERY PLAN / EXPLAIN-ONLY MODE =====================
def _json_default(obj):
    """Serialize MongoDB/BSON/Pandas objects safely for raw explain JSON files."""
    try:
        return obj.isoformat()
    except Exception:
        return str(obj)


def _walk_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk_dicts(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_dicts(item)


def _safe_number(value):
    try:
        if value is None:
            return None
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    except Exception:
        return None


def get_collection_stats(db, collection_name: str) -> dict:
    """
    Return compact collection-level physical statistics.

    These metrics complement explain() because two configurations may have the
    same plan shape/docsExamined but different physical costs due to document
    size, embedded arrays, or index footprint. This is especially useful for
    comparing, for example, G7 vs. G8 when both use the same collection and
    index plan but one configuration embeds more data.
    """
    if not collection_name:
        return {
            "collection_stats_ok": False,
            "collection_stats_error": "missing collection name",
        }
    try:
        stats = db.command("collStats", collection_name)
        index_sizes = stats.get("indexSizes", {}) or {}
        return {
            "collection_stats_ok": True,
            "collection_stats_error": None,
            "collection_count": _safe_number(stats.get("count")),
            "collection_size_bytes": _safe_number(stats.get("size")),
            "collection_avg_obj_size_bytes": _safe_number(stats.get("avgObjSize")),
            "collection_storage_size_bytes": _safe_number(stats.get("storageSize")),
            "collection_total_index_size_bytes": _safe_number(stats.get("totalIndexSize")),
            "collection_total_size_bytes": _safe_number(stats.get("totalSize")),
            "collection_free_storage_size_bytes": _safe_number(stats.get("freeStorageSize")),
            "collection_nindexes": _safe_number(stats.get("nindexes")),
            "collection_scale_factor": _safe_number(stats.get("scaleFactor")),
            "collection_index_sizes_json": json.dumps(index_sizes, default=_json_default, sort_keys=True),
        }
    except Exception as e:
        return {
            "collection_stats_ok": False,
            "collection_stats_error": f"{type(e).__name__}: {e}",
            "collection_count": None,
            "collection_size_bytes": None,
            "collection_avg_obj_size_bytes": None,
            "collection_storage_size_bytes": None,
            "collection_total_index_size_bytes": None,
            "collection_total_size_bytes": None,
            "collection_free_storage_size_bytes": None,
            "collection_nindexes": None,
            "collection_scale_factor": None,
            "collection_index_sizes_json": "{}",
        }


def summarize_explain(explain_doc: dict) -> dict:
    """
    Extract compact executionStats/queryPlanner metrics from a MongoDB explain document.

    Works for both find/cursor explains and command explains. It intentionally uses
    recursive collection because MongoDB nesting differs for find, count, update,
    classic engine, and slot-based execution.
    """
    if not isinstance(explain_doc, dict):
        return {
            "execution_time_ms": None,
            "n_returned": None,
            "total_docs_examined": None,
            "total_keys_examined": None,
            "docs_per_returned": None,
            "keys_per_returned": None,
            "winning_plan_stage": None,
            "namespace": None,
            "query_hash": None,
            "plan_cache_key": None,
            "rejected_plans_count": None,
            "stages": "",
            "index_names": "",
            "has_ixscan": False,
            "has_collscan": False,
            "has_fetch": False,
            "has_sort": False,
            "has_limit": False,
            "has_update": False,
            "has_and_sorted": False,
            "has_or_stage": False,
            "has_projection": False,
            "has_lookup": False,
            "has_group": False,
            "used_disk": False,
        }

    exec_stats = explain_doc.get("executionStats", {}) or {}
    qp = explain_doc.get("queryPlanner", {}) or {}

    stages = []
    index_names = []
    used_disk = False
    for d in _walk_dicts(explain_doc):
        stage = d.get("stage") or d.get("nodeType")
        if stage:
            stages.append(str(stage))
        idx = d.get("indexName")
        if idx:
            index_names.append(str(idx))
        if d.get("usedDisk") is True:
            used_disk = True

    # Prefer top-level executionStats metrics, but fall back to recursive maxima/sums.
    execution_time_ms = exec_stats.get("executionTimeMillis")
    n_returned = exec_stats.get("nReturned")
    total_docs_examined = exec_stats.get("totalDocsExamined")
    total_keys_examined = exec_stats.get("totalKeysExamined")

    # Update/command explains may expose nMatched/nWouldModify rather than nReturned.
    if n_returned is None:
        for d in _walk_dicts(exec_stats):
            if "nReturned" in d:
                n_returned = d.get("nReturned")
                break
            if "nMatched" in d:
                n_returned = d.get("nMatched")
                break

    if total_docs_examined is None:
        vals = [d.get("docsExamined") for d in _walk_dicts(exec_stats) if isinstance(d.get("docsExamined"), (int, float))]
        total_docs_examined = max(vals) if vals else None

    if total_keys_examined is None:
        vals = [d.get("keysExamined") for d in _walk_dicts(exec_stats) if isinstance(d.get("keysExamined"), (int, float))]
        total_keys_examined = max(vals) if vals else None

    stages_unique = []
    for s in stages:
        if s not in stages_unique:
            stages_unique.append(s)
    indexes_unique = []
    for idx in index_names:
        if idx not in indexes_unique:
            indexes_unique.append(idx)

    stage_text = "|".join(stages_unique)
    stage_set = set(stages_unique)
    rejected_plans = qp.get("rejectedPlans") or []
    return {
        "execution_time_ms": execution_time_ms,
        "n_returned": n_returned,
        "total_docs_examined": total_docs_examined,
        "total_keys_examined": total_keys_examined,
        "docs_per_returned": (float(total_docs_examined) / float(n_returned)) if total_docs_examined is not None and n_returned not in [None, 0] else None,
        "keys_per_returned": (float(total_keys_examined) / float(n_returned)) if total_keys_examined is not None and n_returned not in [None, 0] else None,
        "winning_plan_stage": qp.get("winningPlan", {}).get("stage"),
        "namespace": qp.get("namespace") or explain_doc.get("namespace"),
        "query_hash": qp.get("queryHash"),
        "plan_cache_key": qp.get("planCacheKey"),
        "rejected_plans_count": len(rejected_plans) if isinstance(rejected_plans, list) else None,
        "stages": stage_text,
        "index_names": "|".join(indexes_unique),
        # Exact stage membership. Do not use substring matching because, for example,
        # SORT contains the letters OR and would incorrectly trigger has_or_stage.
        "has_ixscan": "IXSCAN" in stage_set,
        "has_collscan": "COLLSCAN" in stage_set,
        "has_fetch": "FETCH" in stage_set,
        "has_sort": bool(stage_set.intersection({"SORT", "SORT_KEY_GENERATOR"})),
        "has_limit": "LIMIT" in stage_set,
        "has_update": ("UPDATE" in stage_set) or ("UPDATE" in str(explain_doc.get("command", {})).upper()),
        "has_and_sorted": bool(stage_set.intersection({"AND_SORTED", "AND_HASH"})),
        "has_or_stage": "OR" in stage_set,
        "has_projection": bool(stage_set.intersection({"PROJECTION", "PROJECTION_SIMPLE", "PROJECTION_DEFAULT", "PROJECTION_COVERED"})),
        "has_lookup": bool(stage_set.intersection({"LOOKUP", "$lookup"})),
        "has_group": bool(stage_set.intersection({"GROUP", "$group"})),
        "used_disk": used_disk,
    }


def _safe_explain_cursor(cursor, verbosity: str) -> dict:
    # PyMongo Cursor.explain() may not accept verbosity in older versions.
    try:
        return cursor.explain(verbosity=verbosity)
    except TypeError:
        return cursor.explain()


def explain_find_component(collection, component_name: str, query: dict, projection: Optional[dict] = None,
                           sort: Optional[list] = None, limit: Optional[int] = None,
                           verbosity: str = "executionStats") -> dict:
    cursor = collection.find(query, projection or {})
    if sort:
        cursor = cursor.sort(sort)
    if limit:
        cursor = cursor.limit(int(limit))
    explain_doc = _safe_explain_cursor(cursor, verbosity)
    return {
        "component_name": component_name,
        "operation_type": "find",
        "collection_name": collection.name,
        "query_shape": json.dumps(query, default=_json_default, sort_keys=True),
        "projection_shape": json.dumps(projection or {}, default=_json_default, sort_keys=True),
        "sort_shape": json.dumps(sort or [], default=_json_default),
        "limit": limit,
        "explain_doc": explain_doc,
    }


def explain_count_component(db, collection_name: str, component_name: str, query: dict,
                            verbosity: str = "executionStats") -> dict:
    cmd = {"count": collection_name, "query": query}
    explain_doc = db.command("explain", cmd, verbosity=verbosity)
    return {
        "component_name": component_name,
        "operation_type": "count",
        "collection_name": collection_name,
        "query_shape": json.dumps(query, default=_json_default, sort_keys=True),
        "projection_shape": "{}",
        "sort_shape": "[]",
        "limit": None,
        "explain_doc": explain_doc,
    }


def explain_update_component(db, collection_name: str, component_name: str, query: dict, update_doc: dict,
                             verbosity: str = "executionStats") -> dict:
    cmd = {
        "update": collection_name,
        "updates": [{"q": query, "u": update_doc, "multi": False, "upsert": False}],
    }
    explain_doc = db.command("explain", cmd, verbosity=verbosity)
    return {
        "component_name": component_name,
        "operation_type": "update",
        "collection_name": collection_name,
        "query_shape": json.dumps(query, default=_json_default, sort_keys=True),
        "projection_shape": "{}",
        "sort_shape": "[]",
        "limit": 1,
        "explain_doc": explain_doc,
    }


def _fetch_role_person_ids_for_watchitem(db, watchitem_id: str, role_category: str) -> List[str]:
    roles = list(db["roles"].find({"watchitem_id": watchitem_id, "role_category": role_category}, {"person_id": 1, "_id": 0}))
    return [r["person_id"] for r in roles if r.get("person_id")]


def _fetch_episode_ids_for_series(db, series_watchitem_id: str) -> List[str]:
    episodes = list(db["episodes"].find({"series_watchitem_id": series_watchitem_id}, {"episode_watchitem_id": 1, "_id": 0}))
    return [e["episode_watchitem_id"] for e in episodes if e.get("episode_watchitem_id")]


def _fetch_embedded_episode_ids(db, series_watchitem_id: str) -> List[str]:
    sdoc = db["series"].find_one({"series_watchitem_id": series_watchitem_id}, {"episodes_embedded.episode_watchitem_id": 1})
    return [e.get("episode_watchitem_id") for e in (sdoc or {}).get("episodes_embedded", []) if e.get("episode_watchitem_id")]


def _fetch_person_ids_from_embedded_roles(db, watchitem_ids: List[str], cfg: dict, role_category: Optional[str] = None) -> List[str]:
    if not watchitem_ids:
        return []
    docs = list(db["watchitems"].find({"watchitem_id": {"$in": watchitem_ids}}, {"roles_embedded": 1, "_id": 0}))
    person_ids = []
    for d in docs:
        for r in d.get("roles_embedded", []):
            if role_category and r.get("role_category") != role_category:
                continue
            if r.get("person_id"):
                person_ids.append(r["person_id"])
            elif r.get("person_snapshot", {}).get("person_id"):
                person_ids.append(r["person_snapshot"]["person_id"])
            elif r.get("person_embedded", {}).get("person_id"):
                person_ids.append(r["person_embedded"]["person_id"])
    # limit very large $in lists to keep explains readable and safe
    return list(dict.fromkeys(person_ids))[:500]


def explain_query_by_name(db, cfg, query_name, param, repetition, verbosity="executionStats") -> dict:
    """
    Return component-level MongoDB explains for one logical IMDb benchmark query.

    For read queries composed of multiple MongoDB operations, this function records
    one component per operation. For QG7 updates, it uses MongoDB explain on the
    update command. For QG8 insert-heavy operations, MongoDB does not provide a
    meaningful insert explain, so the script records insert components as
    not_explainable and explains the update component when the configuration embeds
    roles into watchitems.
    """
    components = []
    notes = []

    if query_name == "QG1_WatchItemById":
        components.append(explain_find_component(db["watchitems"], "watchitem_by_id", {"watchitem_id": param}, limit=1, verbosity=verbosity))

    elif query_name == "QG2_WatchItemByTitle":
        components.append(explain_find_component(db["watchitems"], "watchitem_by_title", {"title": param}, limit=20, verbosity=verbosity))

    elif query_name == "QG3_RecommendationByGenreAndSubtype":
        query = {"title_type": param["title_type"]}
        query["genre_doc.name" if cfg["config_name"] == "watchitem_g2" else "primary_genre"] = param["primary_genre"]
        components.append(explain_find_component(db["watchitems"], "recommendation_by_genre_subtype", query, sort=[("avg_rating", -1)], limit=20, verbosity=verbosity))

    elif query_name == "QG4_AllPersonsOfTypeForWatchItem":
        watchitem_id = param["watchitem_id"]
        role_category = param["role_category"]
        if cfg["config_name"] in ["watchitem_g4", "watchitem_g5", "watchitem_g6"]:
            components.append(explain_find_component(db["watchitems"], "watchitem_roles_embedded_lookup", {"watchitem_id": watchitem_id}, projection={"roles_embedded": 1}, limit=1, verbosity=verbosity))
            if cfg["config_name"] == "watchitem_g4":
                person_ids = _fetch_person_ids_from_embedded_roles(db, [watchitem_id], cfg, role_category=role_category)
                if person_ids:
                    components.append(explain_find_component(db["persons"], "persons_by_embedded_role_ids", {"person_id": {"$in": person_ids}}, verbosity=verbosity))
        else:
            role_query = {"watchitem_id": watchitem_id, "role_category": role_category}
            components.append(explain_find_component(db["roles"], "roles_by_watchitem_and_category", role_query, verbosity=verbosity))
            person_ids = _fetch_role_person_ids_for_watchitem(db, watchitem_id, role_category)
            if person_ids:
                components.append(explain_find_component(db["persons"], "persons_by_role_ids", {"person_id": {"$in": person_ids}}, verbosity=verbosity))

    elif query_name == "QG5_AllPersonsForEpisodesOfSeries":
        series_watchitem_id = param
        if cfg["selected_root"] == "Series" and cfg["config_name"] in ["series_g8", "series_g9"]:
            components.append(explain_find_component(db["series"], "series_embedded_episodes_lookup", {"series_watchitem_id": series_watchitem_id}, projection={"episodes_embedded": 1}, limit=1, verbosity=verbosity))
            episode_ids = _fetch_embedded_episode_ids(db, series_watchitem_id)
        else:
            components.append(explain_find_component(db["episodes"], "episodes_by_series", {"series_watchitem_id": series_watchitem_id}, projection={"episode_watchitem_id": 1}, verbosity=verbosity))
            episode_ids = _fetch_episode_ids_for_series(db, series_watchitem_id)

        if episode_ids:
            if cfg["config_name"] in ["watchitem_g4", "watchitem_g5", "watchitem_g6"]:
                components.append(explain_find_component(db["watchitems"], "episode_watchitems_with_roles", {"watchitem_id": {"$in": episode_ids[:500]}}, projection={"roles_embedded": 1}, verbosity=verbosity))
                if cfg["config_name"] == "watchitem_g4":
                    person_ids = _fetch_person_ids_from_embedded_roles(db, episode_ids[:500], cfg)
                    if person_ids:
                        components.append(explain_find_component(db["persons"], "persons_from_embedded_episode_roles", {"person_id": {"$in": person_ids}}, verbosity=verbosity))
            else:
                role_query = {"watchitem_id": {"$in": episode_ids[:500]}}
                components.append(explain_find_component(db["roles"], "roles_for_episode_watchitems", role_query, projection={"person_id": 1}, verbosity=verbosity))
                roles = list(db["roles"].find(role_query, {"person_id": 1, "_id": 0}).limit(500))
                person_ids = [r.get("person_id") for r in roles if r.get("person_id")]
                if person_ids:
                    components.append(explain_find_component(db["persons"], "persons_for_episode_roles", {"person_id": {"$in": list(dict.fromkeys(person_ids))[:500]}}, verbosity=verbosity))

    elif query_name == "QG6_EpisodesOfSeries":
        series_watchitem_id = param
        if cfg["selected_root"] == "Series" and cfg["config_name"] in ["series_g8", "series_g9"]:
            components.append(explain_find_component(db["series"], "series_embedded_episodes_lookup", {"series_watchitem_id": series_watchitem_id}, projection={"episodes_embedded": 1}, limit=1, verbosity=verbosity))
        else:
            components.append(explain_count_component(db, "episodes", "count_episodes_by_series", {"series_watchitem_id": series_watchitem_id}, verbosity=verbosity))

    elif query_name == "QG7_UpdateWatchItemMetadata":
        update_doc = {"$set": {"benchmark_runtime_minutes": "explain_only", "benchmark_marker": "explain_only"}}
        components.append(explain_update_component(db, "watchitems", "update_watchitem_metadata", {"watchitem_id": param}, update_doc, verbosity=verbosity))

    elif query_name == "QG8_AddPersonRoleToWatchItem":
        watchitem_id = param
        notes.append("MongoDB does not expose a useful query plan for pure insert_one operations; insert components are recorded as not_explainable.")
        components.append({
            "component_name": "insert_person_doc",
            "operation_type": "insert_not_explainable",
            "collection_name": "persons",
            "query_shape": "{}",
            "projection_shape": "{}",
            "sort_shape": "[]",
            "limit": None,
            "explain_doc": {},
        })
        components.append({
            "component_name": "insert_role_doc",
            "operation_type": "insert_not_explainable",
            "collection_name": "roles",
            "query_shape": "{}",
            "projection_shape": "{}",
            "sort_shape": "[]",
            "limit": None,
            "explain_doc": {},
        })
        if cfg["config_name"] in ["watchitem_g4", "watchitem_g5", "watchitem_g6"]:
            update_doc = {"$push": {"roles_embedded": {"role_id": "explain_only", "person_id": "explain_only"}}}
            components.append(explain_update_component(db, "watchitems", "push_embedded_role", {"watchitem_id": watchitem_id}, update_doc, verbosity=verbosity))

    elif query_name == "QG9_TopRatedSeriesByGenre":
        genre = param
        if cfg["selected_root"] == "Series":
            components.append(explain_find_component(db["series"], "top_rated_series_by_genre", {"primary_genre": genre}, sort=[("avg_rating", -1)], limit=20, verbosity=verbosity))
        else:
            components.append(explain_find_component(db["watchitems"], "top_rated_watchitems_by_genre", {"title_type": "tvSeries", "primary_genre": genre}, sort=[("avg_rating", -1)], limit=20, verbosity=verbosity))

    elif query_name == "QG10_AdvancedSearchWatchItems":
        query = {}
        keyword = param.get("keyword")
        genre = param.get("genre")
        year_min = param.get("year_min")
        rating_min = param.get("rating_min")
        subtype = param.get("subtype")

        if keyword:
            query["title"] = {"$regex": keyword, "$options": "i"}
        if genre:
            query["genre_doc.name" if cfg["config_name"] == "watchitem_g2" else "primary_genre"] = genre
        if subtype:
            query["subtype_component.subtype" if cfg["config_name"] == "watchitem_g3" else "title_type"] = subtype
        if year_min not in [None, "", "None"]:
            query["release_year"] = {"$gte": year_min}
        if rating_min not in [None, "", "None"]:
            query["avg_rating"] = {"$gte": rating_min}
        components.append(explain_find_component(db["watchitems"], "advanced_search_watchitems", query, sort=[("avg_rating", -1)], limit=20, verbosity=verbosity))

    else:
        raise KeyError(f"Unsupported query for explain: {query_name}")

    return {"components": components, "notes": " | ".join(notes)}


def _component_to_row(base: dict, component: dict, component_index: int, raw_explain_path: Optional[str] = None,
                      collection_stats: Optional[dict] = None) -> dict:
    explain_doc = component.get("explain_doc") or {}
    summary = summarize_explain(explain_doc)
    collection_stats = collection_stats or {}

    avg_obj_size = _safe_number(collection_stats.get("collection_avg_obj_size_bytes"))
    docs_examined = _safe_number(summary.get("total_docs_examined"))
    n_returned = _safe_number(summary.get("n_returned"))
    collection_count = _safe_number(collection_stats.get("collection_count"))
    collection_size = _safe_number(collection_stats.get("collection_size_bytes"))
    total_index_size = _safe_number(collection_stats.get("collection_total_index_size_bytes"))

    estimated_docs_examined_bytes = (docs_examined * avg_obj_size) if docs_examined is not None and avg_obj_size is not None else None
    estimated_returned_bytes = (n_returned * avg_obj_size) if n_returned is not None and avg_obj_size is not None else None
    docs_examined_collection_ratio = (docs_examined / collection_count) if docs_examined is not None and collection_count not in [None, 0] else None
    index_to_data_size_ratio = (total_index_size / collection_size) if total_index_size is not None and collection_size not in [None, 0] else None

    return {
        **base,
        "component_index": component_index,
        "component_name": component.get("component_name"),
        "operation_type": component.get("operation_type"),
        "collection_name": component.get("collection_name"),
        "query_shape": component.get("query_shape"),
        "projection_shape": component.get("projection_shape"),
        "sort_shape": component.get("sort_shape"),
        "limit": component.get("limit"),
        "raw_explain_path": raw_explain_path,
        **summary,
        **collection_stats,
        # Derived physical-cost indicators. These are estimates, not measured I/O.
        # They are useful to explain cases where two candidates have similar plans
        # but different document sizes due to embedding/summaries.
        "estimated_docs_examined_bytes": estimated_docs_examined_bytes,
        "estimated_returned_bytes": estimated_returned_bytes,
        "docs_examined_collection_ratio": docs_examined_collection_ratio,
        "index_to_data_size_ratio": index_to_data_size_ratio,
    }


def _aggregate_component_rows(component_rows: List[dict]) -> dict:
    def sum_nonnull(key):
        vals = [r.get(key) for r in component_rows if r.get(key) is not None and not pd.isna(r.get(key))]
        return float(sum(float(v) for v in vals)) if vals else None

    def any_bool(key):
        return bool(any(bool(r.get(key)) for r in component_rows))

    stage_set = []
    index_set = []
    for r in component_rows:
        for s in str(r.get("stages") or "").split("|"):
            if s and s not in stage_set:
                stage_set.append(s)
        for idx in str(r.get("index_names") or "").split("|"):
            if idx and idx not in index_set:
                index_set.append(idx)

    n_returned = sum_nonnull("n_returned")
    docs_examined = sum_nonnull("total_docs_examined")
    keys_examined = sum_nonnull("total_keys_examined")

    # Aggregate physical collection stats without double-counting the same
    # collection multiple times in a multi-component logical query.
    unique_collection_stats = {}
    for r in component_rows:
        cname = r.get("collection_name")
        if not cname or cname in unique_collection_stats:
            continue
        unique_collection_stats[cname] = r

    def sum_unique_collection(key):
        vals = []
        for r in unique_collection_stats.values():
            v = r.get(key)
            if v is not None and not pd.isna(v):
                vals.append(float(v))
        return float(sum(vals)) if vals else None

    def max_unique_collection(key):
        vals = []
        for r in unique_collection_stats.values():
            v = r.get(key)
            if v is not None and not pd.isna(v):
                vals.append(float(v))
        return float(max(vals)) if vals else None

    collection_names = sorted(unique_collection_stats.keys())

    return {
        "n_components": len(component_rows),
        "sum_execution_time_ms": sum_nonnull("execution_time_ms"),
        "sum_n_returned": n_returned,
        "sum_total_docs_examined": docs_examined,
        "sum_total_keys_examined": keys_examined,
        "docs_per_returned_total": (docs_examined / n_returned) if docs_examined is not None and n_returned not in [None, 0] else None,
        "keys_per_returned_total": (keys_examined / n_returned) if keys_examined is not None and n_returned not in [None, 0] else None,
        "has_ixscan_any": any_bool("has_ixscan"),
        "has_collscan_any": any_bool("has_collscan"),
        "has_fetch_any": any_bool("has_fetch"),
        "has_sort_any": any_bool("has_sort"),
        "has_update_any": any_bool("has_update"),
        "has_and_sorted_any": any_bool("has_and_sorted"),
        "has_or_stage_any": any_bool("has_or_stage"),
        "has_projection_any": any_bool("has_projection"),
        "has_lookup_any": any_bool("has_lookup"),
        "has_group_any": any_bool("has_group"),
        "used_disk_any": any_bool("used_disk"),
        "all_stages": "|".join(stage_set),
        "all_index_names": "|".join(index_set),
        "component_collections": "|".join(collection_names),
        "unique_component_collection_count": len(collection_names),
        "sum_collection_count_unique": sum_unique_collection("collection_count"),
        "sum_collection_size_bytes_unique": sum_unique_collection("collection_size_bytes"),
        "sum_collection_storage_size_bytes_unique": sum_unique_collection("collection_storage_size_bytes"),
        "sum_collection_total_index_size_bytes_unique": sum_unique_collection("collection_total_index_size_bytes"),
        "sum_collection_total_size_bytes_unique": sum_unique_collection("collection_total_size_bytes"),
        "max_collection_avg_obj_size_bytes": max_unique_collection("collection_avg_obj_size_bytes"),
        "sum_estimated_docs_examined_bytes": sum_nonnull("estimated_docs_examined_bytes"),
        "sum_estimated_returned_bytes": sum_nonnull("estimated_returned_bytes"),
        "estimated_examined_bytes_per_returned": (sum_nonnull("estimated_docs_examined_bytes") / n_returned) if sum_nonnull("estimated_docs_examined_bytes") is not None and n_returned not in [None, 0] else None,
        "max_docs_examined_collection_ratio": max([r.get("docs_examined_collection_ratio") for r in component_rows if r.get("docs_examined_collection_ratio") is not None and not pd.isna(r.get("docs_examined_collection_ratio"))], default=None),
        "max_index_to_data_size_ratio": max([r.get("index_to_data_size_ratio") for r in component_rows if r.get("index_to_data_size_ratio") is not None and not pd.isna(r.get("index_to_data_size_ratio"))], default=None),
    }


def _make_explain_plan_df(exp_row, template_df, args):
    plan_df = template_df[template_df["experiment_id"] == exp_row["experiment_id"]].copy()
    if args.query_group:
        plan_df = plan_df[plan_df["query_group"].isin(set(args.query_group))]
    if args.run_phase:
        plan_df = plan_df[plan_df["run_phase"].isin(set(args.run_phase))]
    if args.query_name:
        plan_df = plan_df[plan_df["query_name"].isin(set(args.query_name))]
    plan_df = plan_df.sort_values(["query_group", "query_name", "run_phase", "repetition"]).reset_index(drop=True)

    # In explain-only mode, we normally need one representative parameter per query/group.
    if args.explain_one_per_query:
        plan_df = plan_df.drop_duplicates(subset=["query_group", "query_name"], keep="first").reset_index(drop=True)

    if args.max_runs is not None:
        plan_df = plan_df.head(args.max_runs).copy()
    return plan_df


def run_query_plan_on_execution_db(exp_row, template_df, pool, db, execution_db_name, args):
    log(f"=== QUERY PLAN START experiment_id={exp_row['experiment_id']} execution_db={execution_db_name} ===")
    plan_df = _make_explain_plan_df(exp_row, template_df, args)
    log(f"Explain plan rows for {exp_row['experiment_id']}: {len(plan_df)}")

    cfg = {
        "experiment_id": exp_row["experiment_id"],
        "config_name": exp_row["config_name"],
        "selected_root": exp_row["selected_root"],
        "primary_collection": exp_row["primary_collection"],
        "scale_label": exp_row["scale_label"],
        "execution_db_name": execution_db_name,
    }

    component_rows = []
    summary_rows = []
    raw_dir = Path(args.results_dir) / "query_plan_raw_json"
    if args.save_raw_explain:
        raw_dir.mkdir(parents=True, exist_ok=True)

    for i, (_, run_row) in enumerate(plan_df.iterrows(), start=1):
        query_name = run_row["query_name"]
        repetition = int(run_row["repetition"])
        param = pick_param_for_run(pool, query_name, repetition)

        if i == 1 or i % GLOBAL_BATCH_LOG_EVERY == 0:
            log(f"[explain-progress] experiment={exp_row['experiment_id']} row={i}/{len(plan_df)} query={query_name} group={run_row['query_group']} rep={repetition}")

        start_ts = pd.Timestamp.now("UTC")
        status = "completed"
        error_message = None
        notes = None
        rows_for_summary = []
        try:
            explain_result = explain_query_by_name(db, cfg, query_name, param, repetition, verbosity=args.explain_verbosity)
            notes = explain_result.get("notes")
            for component_index, component in enumerate(explain_result.get("components", []), start=1):
                raw_path_str = None
                if args.save_raw_explain:
                    raw_name = sanitize_mongo_name(f"{exp_row['experiment_id']}__{query_name}__c{component_index}_{component.get('component_name')}.json")
                    raw_path = raw_dir / raw_name
                    raw_path.write_text(json.dumps(component.get("explain_doc") or {}, indent=2, default=_json_default), encoding="utf-8")
                    raw_path_str = str(raw_path)

                base = run_row.to_dict()
                base.update({
                    "execution_db_name": execution_db_name,
                    "explain_verbosity": args.explain_verbosity,
                    "param_json": json.dumps(param, default=_json_default, sort_keys=True),
                    "start_ts": start_ts,
                    "execution_status": status,
                    "error_message": error_message,
                    "notes": notes,
                })
                collection_stats = get_collection_stats(db, component.get("collection_name")) if args.collect_collection_stats else {}
                row = _component_to_row(base, component, component_index, raw_explain_path=raw_path_str, collection_stats=collection_stats)
                component_rows.append(row)
                rows_for_summary.append(row)
        except Exception as e:
            status = "failed"
            error_message = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            log(f"[explain-error] experiment={exp_row['experiment_id']} query={query_name}: {error_message}", level="ERROR")

        end_ts = pd.Timestamp.now("UTC")
        summary_base = run_row.to_dict()
        summary_base.update({
            "execution_db_name": execution_db_name,
            "explain_verbosity": args.explain_verbosity,
            "param_json": json.dumps(param, default=_json_default, sort_keys=True),
            "start_ts": start_ts,
            "end_ts": end_ts,
            "execution_status": status,
            "error_message": error_message,
            "notes": notes,
        })
        summary_base.update(_aggregate_component_rows(rows_for_summary))
        summary_rows.append(summary_base)

    log(f"=== QUERY PLAN COMPLETED experiment_id={exp_row['experiment_id']} rows={len(summary_rows)} components={len(component_rows)} ===")
    return pd.DataFrame(summary_rows), pd.DataFrame(component_rows)


def aggregate_benchmark_results(results_df):
    if results_df.empty:
        return pd.DataFrame()

    def p95(values): return float(np.percentile(values, 95)) if values else None
    def p99(values): return float(np.percentile(values, 99)) if values else None

    rows = []
    group_cols = ["experiment_id", "config_name", "activated_class", "benchmark_family", "scale_label", "query_name", "query_group", "run_phase"]
    for keys, grp in results_df.groupby(group_cols):
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
            "avg_documents_returned": float(np.mean(ret)) if ret else None,
            "avg_documents_written": float(np.mean(wr)) if wr else None,
        })

    return pd.DataFrame(rows).sort_values(["scale_label","config_name","query_group","query_name","run_phase"]).reset_index(drop=True)


# ===================== ORCHESTRATION =====================
def select_experiments(catalog_df, args):
    df = catalog_df.copy()
    if args.experiments:
        df = df[df["experiment_id"].isin(set(args.experiments))]
    if args.scale_label:
        df = df[df["scale_label"].isin(set(args.scale_label))]
    if args.config_name:
        df = df[df["config_name"].isin(set(args.config_name))]
    return df.sort_values(["scale_factor", "config_name"]).reset_index(drop=True)


def determine_base_collection_loads_for_scale(scale_df, template_df, args):
    """Decide which stable base collections must be materialized.

    Conservative default: load all base collections, matching the original runner.
    With --minimal-base-load, only load base collections needed by selected queries.
    This is useful for QG9-only diagnostics because QG9 does not need persons,
    roles, or the Mongo episodes collection.
    """
    load_persons = not bool(getattr(args, "skip_persons", False))
    load_roles = not bool(getattr(args, "skip_roles", False))
    load_episodes = not bool(getattr(args, "skip_episodes", False))

    if not getattr(args, "minimal_base_load", False):
        return load_persons, load_roles, load_episodes

    exp_ids = set(scale_df["experiment_id"].tolist())
    plan = template_df[template_df["experiment_id"].isin(exp_ids)].copy()
    if getattr(args, "query_group", None):
        plan = plan[plan["query_group"].isin(set(args.query_group))]
    if getattr(args, "run_phase", None):
        plan = plan[plan["run_phase"].isin(set(args.run_phase))]
    if getattr(args, "query_name", None):
        plan = plan[plan["query_name"].isin(set(args.query_name))]

    qnames = set(plan["query_name"].dropna().astype(str).tolist())

    needs_roles = bool(qnames.intersection({
        "QG4_AllPersonsOfTypeForWatchItem",
        "QG5_AllPersonsForEpisodesOfSeries",
        "QG8_AddPersonRoleToWatchItem",
    }))
    needs_persons = bool(qnames.intersection({
        "QG4_AllPersonsOfTypeForWatchItem",
        "QG5_AllPersonsForEpisodesOfSeries",
        "QG8_AddPersonRoleToWatchItem",
    }))
    needs_episodes = bool(qnames.intersection({
        "QG5_AllPersonsForEpisodesOfSeries",
        "QG6_EpisodesOfSeries",
    }))

    load_persons = load_persons and needs_persons
    load_roles = load_roles and needs_roles
    load_episodes = load_episodes and needs_episodes

    log(
        "Minimal base-load decision: "
        f"queries={sorted(qnames)} load_persons={load_persons} "
        f"load_roles={load_roles} load_episodes={load_episodes}"
    )
    return load_persons, load_roles, load_episodes


def run_experiment_on_execution_db(exp_row, template_df, pool, db, execution_db_name, args):
    log(f"=== BENCHMARK START experiment_id={exp_row['experiment_id']} execution_db={execution_db_name} ===")
    plan_df = template_df[template_df["experiment_id"] == exp_row["experiment_id"]].copy()
    if args.query_group:
        plan_df = plan_df[plan_df["query_group"].isin(set(args.query_group))]
    if args.run_phase:
        plan_df = plan_df[plan_df["run_phase"].isin(set(args.run_phase))]
    if args.query_name:
        plan_df = plan_df[plan_df["query_name"].isin(set(args.query_name))]
    plan_df = plan_df.sort_values(["query_group","query_name","run_phase","repetition"]).reset_index(drop=True)
    if args.max_runs is not None:
        plan_df = plan_df.head(args.max_runs).copy()

    log(f"Benchmark plan rows for {exp_row['experiment_id']}: {len(plan_df)}")

    cfg = {
        "experiment_id": exp_row["experiment_id"],
        "config_name": exp_row["config_name"],
        "selected_root": exp_row["selected_root"],
        "primary_collection": exp_row["primary_collection"],
        "scale_label": exp_row["scale_label"],
        "execution_db_name": execution_db_name,
    }

    rows = []
    for i, (_, run_row) in enumerate(plan_df.iterrows(), start=1):
        query_name = run_row["query_name"]
        repetition = int(run_row["repetition"])
        param = pick_param_for_run(pool, query_name, repetition)

        if i == 1 or i % GLOBAL_BATCH_LOG_EVERY == 0:
            log(f"[benchmark-progress] experiment={exp_row['experiment_id']} row={i}/{len(plan_df)} query={query_name} group={run_row['query_group']} phase={run_row['run_phase']} rep={repetition}")

        start_ts = pd.Timestamp.now("UTC")
        try:
            metrics = execute_query_by_name(db, cfg, query_name, param, repetition)
            execution_status = "completed"
            error_message = None
        except Exception as e:
            metrics = {"latency_ms": None, "success": False, "documents_returned": None, "documents_written": None}
            execution_status = "failed"
            error_message = f"{type(e).__name__}: {e}"

        end_ts = pd.Timestamp.now("UTC")

        out = run_row.to_dict()
        out.update({
            "execution_db_name": execution_db_name,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "latency_ms": metrics["latency_ms"],
            "success": metrics["success"],
            "documents_returned": metrics["documents_returned"],
            "documents_written": metrics["documents_written"],
            "execution_status": execution_status,
            "error_message": error_message,
        })
        rows.append(out)

        if args.verbose:
            log(f"[benchmark] {exp_row['experiment_id']} | {query_name} | {run_row['query_group']} | {run_row['run_phase']} | r{repetition:02d} | status={execution_status} | latency_ms={metrics['latency_ms']}")

    log(f"=== BENCHMARK COMPLETED experiment_id={exp_row['experiment_id']} rows={len(rows)} ===")
    return pd.DataFrame(rows)


def build_arg_parser():
    p = argparse.ArgumentParser(description="IMDb MongoDB runner with benchmark and query-plan-only modes")
    p.add_argument("--catalog-csv", required=True)
    p.add_argument("--template-csv", required=True)
    p.add_argument("--results-dir", required=True)
    p.add_argument("--scale-label", nargs="*")
    p.add_argument("--experiments", nargs="*")
    p.add_argument("--config-name", nargs="*")
    p.add_argument("--query-group", nargs="*", choices=["primary", "secondary_affected", "control"])
    p.add_argument("--run-phase", nargs="*", choices=["cold", "hot"])
    p.add_argument("--query-name", nargs="*", help="Optional filter for query names, e.g., QG9_TopRatedSeriesByGenre")
    p.add_argument("--max-runs", type=int, default=None)
    p.add_argument("--row-limit", type=int, default=None)
    p.add_argument("--batch-size", type=int, default=10000)
    p.add_argument("--batch-log-every", type=int, default=20)
    p.add_argument("--sample-size", type=int, default=20)
    p.add_argument("--execution-db-prefix", default="imdb_exec")
    p.add_argument("--force-rebuild-scale-db", action="store_true")
    p.add_argument(
        "--minimal-base-load",
        action="store_true",
        help=(
            "Load only stable base collections required by the selected query set. "
            "Useful for query-plan-only diagnostics such as QG9, where roles/persons "
            "are not needed. Do not use for full benchmark-compatible loads unless "
            "you understand which queries are selected."
        ),
    )
    p.add_argument("--skip-persons", action="store_true", help="Force skipping Mongo persons materialization.")
    p.add_argument("--skip-roles", action="store_true", help="Force skipping Mongo roles materialization.")
    p.add_argument("--skip-episodes", action="store_true", help="Force skipping Mongo episodes materialization.")
    p.add_argument("--query-plan-only", action="store_true", help="Load/swap candidate collections and collect MongoDB explain() plans instead of benchmark timings.")
    p.add_argument("--explain-verbosity", choices=["queryPlanner", "executionStats", "allPlansExecution"], default="executionStats")
    p.add_argument("--explain-one-per-query", action="store_true", default=True, help="In query-plan-only mode, keep one representative parameter per query/group instead of every repetition.")
    p.add_argument("--no-explain-one-per-query", dest="explain_one_per_query", action="store_false", help="Collect explain plans for all rows in the benchmark template.")
    p.add_argument("--save-raw-explain", action="store_true", help="Save raw explain JSON files under results-dir/query_plan_raw_json.")
    p.add_argument("--no-collection-stats", dest="collect_collection_stats", action="store_false", help="Disable collStats collection metrics in query-plan-only outputs.")
    p.set_defaults(collect_collection_stats=True)
    p.add_argument("--log-file", default=None, help="Optional path for persistent execution log. Default: <results-dir>/execution.log")
    p.add_argument("--append-log", action="store_true", help="Append to an existing log instead of overwriting it.")
    p.add_argument("--write-run-manifest", action="store_true", default=True, help="Write benchmark_run_manifest.json with arguments and high-level status.")
    p.add_argument("--no-run-manifest", dest="write_run_manifest", action="store_false")
    p.add_argument("--verbose", action="store_true")
    return p


def main():
    global GLOBAL_VERBOSE, GLOBAL_BATCH_LOG_EVERY, GLOBAL_LOG_FILE
    args = build_arg_parser().parse_args()
    GLOBAL_VERBOSE = bool(args.verbose)
    GLOBAL_BATCH_LOG_EVERY = max(1, int(args.batch_log_every))

    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    # Persistent log file.
    GLOBAL_LOG_FILE = Path(args.log_file) if args.log_file else (results_dir / "execution.log")
    if GLOBAL_LOG_FILE.exists() and not args.append_log:
        GLOBAL_LOG_FILE.unlink()
    log("=== IMDb MongoDB query-plan runner started ===")
    log(f"results_dir={results_dir}")
    log(f"query_plan_only={args.query_plan_only} explain_verbosity={args.explain_verbosity}")
    log(f"force_rebuild_scale_db={args.force_rebuild_scale_db} row_limit={args.row_limit} batch_size={args.batch_size}")
    log(f"scale_label_filter={args.scale_label} config_name_filter={args.config_name} query_name_filter={args.query_name}")

    run_started_at = pd.Timestamp.now("UTC")

    catalog_df = pd.read_csv(args.catalog_csv)
    template_df = pd.read_csv(args.template_csv)

    for col in ["embedded_entities","snapshot_entities","referenced_entities","changed_region_entities","derived_from_queries","primary_queries","secondary_affected_queries","control_queries"]:
        if col in catalog_df.columns:
            catalog_df[col] = catalog_df[col].apply(parse_listlike_cell)

    selected_catalog = select_experiments(catalog_df, args)
    if selected_catalog.empty:
        raise SystemExit("No experiments selected after filters.")

    log(f"Selected experiments: {len(selected_catalog)}")
    try:
        selected_counts = selected_catalog.groupby(["scale_label", "selected_root", "config_name"]).size().reset_index(name="n_experiments")
        selected_counts_path = results_dir / "selected_experiments_summary.csv"
        selected_counts.to_csv(selected_counts_path, index=False)
        log(f"Saved selected experiments summary: {selected_counts_path}")
    except Exception as e:
        log(f"Could not save selected experiments summary: {type(e).__name__}: {e}", level="WARN")
    for _, r in selected_catalog.iterrows():
        log(f"  - {r['experiment_id']} | config={r['config_name']} | scale={r['scale_label']}")

    client = mongo_client()
    initialization_rows = []
    raw_frames = []
    agg_frames = []
    query_plan_summary_frames = []
    query_plan_component_frames = []
    collection_swap_rows = []

    try:
        for scale_label, scale_df in selected_catalog.groupby("scale_label"):
            log(f"######## START SCALE {scale_label} ########")
            con = open_imdb_duckdb_for_scale(scale_label)
            pool = build_query_parameter_pool(scale_label, con, sample_size=args.sample_size)

            execution_db_name = sanitize_mongo_name(f"{args.execution_db_prefix}_{scale_label}")
            if args.force_rebuild_scale_db or execution_db_name not in client.list_database_names():
                load_persons, load_roles, load_episodes = determine_base_collection_loads_for_scale(
                    scale_df=scale_df,
                    template_df=template_df,
                    args=args,
                )
                init_summary = initialize_scale_execution_db(
                    client=client,
                    db_name=execution_db_name,
                    con=con,
                    row_limit=args.row_limit,
                    batch_size=args.batch_size,
                    load_persons=load_persons,
                    load_roles=load_roles,
                    load_episodes=load_episodes,
                )
                init_summary["scale_label"] = scale_label
                initialization_rows.append(init_summary)
            else:
                log(f"Reusing existing execution db: {execution_db_name}")

            db = client[execution_db_name]
            current_watchitems_config = "watchitem_g0"
            current_series_config = "series_g7"

            watchitem_df = scale_df[scale_df["selected_root"] == "WatchItem"].sort_values("config_name")
            series_df = scale_df[scale_df["selected_root"] == "Series"].sort_values("config_name")

            for _, exp_row in watchitem_df.iterrows():
                target_config = exp_row["config_name"]
                if target_config != current_watchitems_config:
                    t0 = time.perf_counter()
                    n_inserted = replace_watchitems_collection(
                        db=db,
                        con=con,
                        config_name=target_config,
                        row_limit=args.row_limit,
                        batch_size=args.batch_size,
                    )
                    elapsed_s = time.perf_counter() - t0
                    collection_swap_rows.append({
                        "scale_label": scale_label,
                        "collection_name": "watchitems",
                        "config_name": target_config,
                        "documents_inserted": n_inserted,
                        "elapsed_seconds": elapsed_s,
                    })
                    current_watchitems_config = target_config

                if args.query_plan_only:
                    summary_df, component_df = run_query_plan_on_execution_db(
                        exp_row=exp_row,
                        template_df=template_df,
                        pool=pool,
                        db=db,
                        execution_db_name=execution_db_name,
                        args=args,
                    )
                    if not summary_df.empty:
                        query_plan_summary_frames.append(summary_df)
                    if not component_df.empty:
                        query_plan_component_frames.append(component_df)
                else:
                    raw_df = run_experiment_on_execution_db(
                        exp_row=exp_row,
                        template_df=template_df,
                        pool=pool,
                        db=db,
                        execution_db_name=execution_db_name,
                        args=args,
                    )
                    if not raw_df.empty:
                        raw_frames.append(raw_df)
                        agg = aggregate_benchmark_results(raw_df)
                        agg_frames.append(agg)
                        log(f"Aggregate rows for {exp_row['experiment_id']}: {len(agg)}")

            if current_watchitems_config != "watchitem_g0" and not series_df.empty:
                t0 = time.perf_counter()
                n_inserted = replace_watchitems_collection(
                    db=db,
                    con=con,
                    config_name="watchitem_g0",
                    row_limit=args.row_limit,
                    batch_size=args.batch_size,
                )
                elapsed_s = time.perf_counter() - t0
                collection_swap_rows.append({
                    "scale_label": scale_label,
                    "collection_name": "watchitems",
                    "config_name": "watchitem_g0",
                    "documents_inserted": n_inserted,
                    "elapsed_seconds": elapsed_s,
                })
                current_watchitems_config = "watchitem_g0"

            for _, exp_row in series_df.iterrows():
                target_config = exp_row["config_name"]
                if target_config != current_series_config:
                    t0 = time.perf_counter()
                    n_inserted = replace_series_collection(
                        db=db,
                        con=con,
                        config_name=target_config,
                        row_limit=args.row_limit,
                        batch_size=args.batch_size,
                    )
                    elapsed_s = time.perf_counter() - t0
                    collection_swap_rows.append({
                        "scale_label": scale_label,
                        "collection_name": "series",
                        "config_name": target_config,
                        "documents_inserted": n_inserted,
                        "elapsed_seconds": elapsed_s,
                    })
                    current_series_config = target_config

                if args.query_plan_only:
                    summary_df, component_df = run_query_plan_on_execution_db(
                        exp_row=exp_row,
                        template_df=template_df,
                        pool=pool,
                        db=db,
                        execution_db_name=execution_db_name,
                        args=args,
                    )
                    if not summary_df.empty:
                        query_plan_summary_frames.append(summary_df)
                    if not component_df.empty:
                        query_plan_component_frames.append(component_df)
                else:
                    raw_df = run_experiment_on_execution_db(
                        exp_row=exp_row,
                        template_df=template_df,
                        pool=pool,
                        db=db,
                        execution_db_name=execution_db_name,
                        args=args,
                    )
                    if not raw_df.empty:
                        raw_frames.append(raw_df)
                        agg = aggregate_benchmark_results(raw_df)
                        agg_frames.append(agg)
                        log(f"Aggregate rows for {exp_row['experiment_id']}: {len(agg)}")

            con.close()
            log(f"######## COMPLETED SCALE {scale_label} ########")

    finally:
        client.close()

    if initialization_rows:
        init_path = results_dir / "scale_db_initialization_summary.csv"
        pd.DataFrame(initialization_rows).to_csv(init_path, index=False)
        log(f"Saved initialization summary: {init_path}")

    if collection_swap_rows:
        swaps_path = results_dir / "collection_swap_summary.csv"
        pd.DataFrame(collection_swap_rows).to_csv(swaps_path, index=False)
        log(f"Saved collection swap summary: {swaps_path}")

    qp_all = pd.DataFrame()
    if query_plan_summary_frames:
        qp_summary_path = results_dir / "query_plan_summary_results.csv"
        qp_all = pd.concat(query_plan_summary_frames, ignore_index=True)
        qp_all.to_csv(qp_summary_path, index=False)
        log(f"Saved query plan summary results: {qp_summary_path}")

        try:
            status_cols = [c for c in ["scale_label", "query_name", "query_group", "run_phase", "execution_status"] if c in qp_all.columns]
            if status_cols:
                status_summary = qp_all.groupby(status_cols).size().reset_index(name="n_rows")
                status_path = results_dir / "query_plan_status_summary.csv"
                status_summary.to_csv(status_path, index=False)
                log(f"Saved query plan status summary: {status_path}")

            failed = qp_all[qp_all.get("execution_status", "").astype(str).str.lower().ne("completed")] if "execution_status" in qp_all.columns else pd.DataFrame()
            if not failed.empty:
                failed_path = results_dir / "query_plan_failed_rows.csv"
                failed.to_csv(failed_path, index=False)
                log(f"Saved failed query-plan rows: {failed_path}", level="WARN")
            else:
                log("No failed query-plan rows detected.")

            if "sum_n_returned" in qp_all.columns and "query_name" in qp_all.columns:
                zero_returned = qp_all[
                    (pd.to_numeric(qp_all["sum_n_returned"], errors="coerce").fillna(0) == 0)
                    & (~qp_all["query_name"].astype(str).str.contains("Update|Add", case=False, na=False))
                ].copy()
                if not zero_returned.empty:
                    zero_path = results_dir / "query_plan_zero_returned_rows.csv"
                    zero_returned.to_csv(zero_path, index=False)
                    log(f"Saved zero-returned read query-plan rows for inspection: {zero_path}", level="WARN")
        except Exception as e:
            log(f"Could not write query-plan validation summaries: {type(e).__name__}: {e}", level="WARN")

    if query_plan_component_frames:
        qp_components_path = results_dir / "query_plan_component_results.csv"
        pd.concat(query_plan_component_frames, ignore_index=True).to_csv(qp_components_path, index=False)
        log(f"Saved query plan component results: {qp_components_path}")

    if raw_frames:
        raw_path = results_dir / "benchmark_raw_results.csv"
        pd.concat(raw_frames, ignore_index=True).to_csv(raw_path, index=False)
        log(f"Saved raw benchmark results: {raw_path}")

    if agg_frames:
        agg_path = results_dir / "benchmark_aggregate_results.csv"
        pd.concat(agg_frames, ignore_index=True).to_csv(agg_path, index=False)
        log(f"Saved aggregate benchmark results: {agg_path}")

    run_finished_at = pd.Timestamp.now("UTC")
    if args.write_run_manifest:
        try:
            manifest = {
                "runner": "run_imdb_mongo_benchmark_query_plan_v4_minimal.py",
                "started_at_utc": str(run_started_at),
                "finished_at_utc": str(run_finished_at),
                "duration_seconds": float((run_finished_at - run_started_at).total_seconds()),
                "results_dir": str(results_dir),
                "catalog_csv": str(args.catalog_csv),
                "template_csv": str(args.template_csv),
                "query_plan_only": bool(args.query_plan_only),
                "explain_verbosity": args.explain_verbosity,
                "scale_label_filter": args.scale_label,
                "experiments_filter": args.experiments,
                "config_name_filter": args.config_name,
                "query_group_filter": args.query_group,
                "run_phase_filter": args.run_phase,
                "query_name_filter": args.query_name,
                "max_runs": args.max_runs,
                "row_limit": args.row_limit,
                "batch_size": args.batch_size,
                "sample_size": args.sample_size,
                "execution_db_prefix": args.execution_db_prefix,
                "force_rebuild_scale_db": bool(args.force_rebuild_scale_db),
                "minimal_base_load": bool(args.minimal_base_load),
                "skip_persons": bool(args.skip_persons),
                "skip_roles": bool(args.skip_roles),
                "skip_episodes": bool(args.skip_episodes),
                "save_raw_explain": bool(args.save_raw_explain),
                "collect_collection_stats": bool(args.collect_collection_stats),
                "n_selected_experiments": int(len(selected_catalog)) if "selected_catalog" in locals() else None,
                "n_initialization_rows": int(len(initialization_rows)),
                "n_collection_swap_rows": int(len(collection_swap_rows)),
                "n_query_plan_summary_rows": int(len(qp_all)) if "qp_all" in locals() and not qp_all.empty else 0,
                "log_file": str(GLOBAL_LOG_FILE) if GLOBAL_LOG_FILE is not None else None,
            }
            manifest_path = results_dir / "benchmark_run_manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
            log(f"Saved run manifest: {manifest_path}")
        except Exception as e:
            log(f"Could not write run manifest: {type(e).__name__}: {e}", level="WARN")

    log(f"Done. Results in: {results_dir}")


if __name__ == "__main__":
    main()
