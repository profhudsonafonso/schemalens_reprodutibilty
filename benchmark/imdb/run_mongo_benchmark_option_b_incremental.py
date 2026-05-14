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


# ===================== LOGGING =====================
def log(msg: str, level: str = "INFO") -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


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


def initialize_scale_execution_db(client, db_name: str, con, row_limit=None, batch_size=1000000):
    log(f"=== INITIALIZING EXECUTION DB {db_name} ===")
    drop_database_if_exists(client, db_name)
    db = client[db_name]

    persons_inserted = load_persons_collection(db, con, row_limit=row_limit, batch_size=batch_size)
    roles_inserted = load_roles_collection(db, con, row_limit=row_limit, batch_size=batch_size)
    episodes_inserted = load_episodes_collection(db, con, row_limit=row_limit, batch_size=batch_size)

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


def run_experiment_on_execution_db(exp_row, template_df, pool, db, execution_db_name, args):
    log(f"=== BENCHMARK START experiment_id={exp_row['experiment_id']} execution_db={execution_db_name} ===")
    plan_df = template_df[template_df["experiment_id"] == exp_row["experiment_id"]].copy()
    if args.query_group:
        plan_df = plan_df[plan_df["query_group"].isin(set(args.query_group))]
    if args.run_phase:
        plan_df = plan_df[plan_df["run_phase"].isin(set(args.run_phase))]
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
    p = argparse.ArgumentParser(description="Fast incremental Option B benchmark runner for IMDb + MongoDB")
    p.add_argument("--catalog-csv", required=True)
    p.add_argument("--template-csv", required=True)
    p.add_argument("--results-dir", required=True)
    p.add_argument("--scale-label", nargs="*")
    p.add_argument("--experiments", nargs="*")
    p.add_argument("--config-name", nargs="*")
    p.add_argument("--query-group", nargs="*", choices=["primary", "secondary_affected", "control"])
    p.add_argument("--run-phase", nargs="*", choices=["cold", "hot"])
    p.add_argument("--max-runs", type=int, default=None)
    p.add_argument("--row-limit", type=int, default=None)
    p.add_argument("--batch-size", type=int, default=10000)
    p.add_argument("--batch-log-every", type=int, default=20)
    p.add_argument("--sample-size", type=int, default=20)
    p.add_argument("--execution-db-prefix", default="imdb_exec")
    p.add_argument("--force-rebuild-scale-db", action="store_true")
    p.add_argument("--verbose", action="store_true")
    return p


def main():
    global GLOBAL_VERBOSE, GLOBAL_BATCH_LOG_EVERY
    args = build_arg_parser().parse_args()
    GLOBAL_VERBOSE = bool(args.verbose)
    GLOBAL_BATCH_LOG_EVERY = max(1, int(args.batch_log_every))

    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    catalog_df = pd.read_csv(args.catalog_csv)
    template_df = pd.read_csv(args.template_csv)

    for col in ["embedded_entities","snapshot_entities","referenced_entities","changed_region_entities","derived_from_queries","primary_queries","secondary_affected_queries","control_queries"]:
        if col in catalog_df.columns:
            catalog_df[col] = catalog_df[col].apply(parse_listlike_cell)

    selected_catalog = select_experiments(catalog_df, args)
    if selected_catalog.empty:
        raise SystemExit("No experiments selected after filters.")

    log(f"Selected experiments: {len(selected_catalog)}")
    for _, r in selected_catalog.iterrows():
        log(f"  - {r['experiment_id']} | config={r['config_name']} | scale={r['scale_label']}")

    client = mongo_client()
    initialization_rows = []
    raw_frames = []
    agg_frames = []
    collection_swap_rows = []

    try:
        for scale_label, scale_df in selected_catalog.groupby("scale_label"):
            log(f"######## START SCALE {scale_label} ########")
            con = open_imdb_duckdb_for_scale(scale_label)
            pool = build_query_parameter_pool(scale_label, con, sample_size=args.sample_size)

            execution_db_name = sanitize_mongo_name(f"{args.execution_db_prefix}_{scale_label}")
            if args.force_rebuild_scale_db or execution_db_name not in client.list_database_names():
                init_summary = initialize_scale_execution_db(
                    client=client,
                    db_name=execution_db_name,
                    con=con,
                    row_limit=args.row_limit,
                    batch_size=args.batch_size,
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

    if raw_frames:
        raw_path = results_dir / "benchmark_raw_results.csv"
        pd.concat(raw_frames, ignore_index=True).to_csv(raw_path, index=False)
        log(f"Saved raw benchmark results: {raw_path}")

    if agg_frames:
        agg_path = results_dir / "benchmark_aggregate_results.csv"
        pd.concat(agg_frames, ignore_index=True).to_csv(agg_path, index=False)
        log(f"Saved aggregate benchmark results: {agg_path}")

    log(f"Done. Results in: {results_dir}")


if __name__ == "__main__":
    main()
