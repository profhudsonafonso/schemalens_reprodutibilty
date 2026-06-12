"""
Materialize the Lima & Mello 2015 FIBEN logical schema in MongoDB.

This script loads the physical plan generated from:
- Lima & Mello conversion decisions;
- FIBEN source file mapping;
- manual FIBEN column schema.

It supports a smoke mode with --max-rows-per-view before full SF1 loading.

Protected databases are never dropped.
"""

from __future__ import annotations

import argparse
import ast
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
from pymongo import MongoClient, ASCENDING
from pymongo.errors import BulkWriteError


PROTECTED_DATABASES = {
    "fiben_exec_sf1",
    "fiben_exec_sf10",
    "fiben_exec_sf30",
    "dbsr_fiben_sf1_source_full",
    "dbsr_fiben_sf10_source_full",
    "dbsr_fiben_sf30_source_full",
}

ENTITY_TO_VIEW = {
    "Corporation": "fiben_corporations",
    "Industry": "fiben_industries",
    "Country": "fiben_countries",
    "Security": "fiben_securities",
    "ListedSecurity": "fiben_listed_securities",
    "Person": "fiben_persons",
    "FinancialServiceAccount": "fiben_financial_service_accounts",
    "Holding": "fiben_holdings",
    "Transaction": "fiben_transactions",
    "BuyTransaction": "fiben_buy_transactions",
    "SellTransaction": "fiben_sell_transactions",
    "FinancialReport": "fiben_reports",
    "ReportElement": "fiben_report_elements",
    "StatementElement": "fiben_statement_elements",
    "Disclosure": "fiben_disclosures",
}

EMBED_EDGE_ORDER = [
    "transaction_refers_to_listed_security",
    "financial_report_contains_report_element",
    "account_has_holding",
    "account_records_transaction",
    "person_owns_financial_service_account",
    "corporation_has_country",
    "corporation_has_industry",
    "corporation_has_financial_report",
    "holding_refers_to_listed_security",
]


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def safe_json(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return str(value)


def parse_list(value: Any) -> List[str]:
    if value is None or pd.isna(value):
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = ast.literal_eval(str(value))
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    except Exception:
        pass
    return []


def source_collection_name(view: str) -> str:
    return f"_src_{view}"


def read_columns_for_view(column_schema_df: pd.DataFrame, semantic_view: str) -> List[str]:
    view_df = column_schema_df[column_schema_df["semantic_view"] == semantic_view].copy()
    view_df = view_df.sort_values("column_position_zero_based")
    cols = view_df["column_name"].astype(str).tolist()
    if not cols:
        raise RuntimeError(f"No columns found for semantic view {semantic_view}")
    return cols


def file_for_view(mapping_df: pd.DataFrame, semantic_view: str) -> Path:
    row = mapping_df[mapping_df["semantic_view"] == semantic_view]
    if len(row) != 1:
        raise RuntimeError(f"Expected one mapping row for {semantic_view}, found {len(row)}")
    status = str(row["status"].iloc[0])
    if status != "matched":
        raise RuntimeError(f"Semantic view {semantic_view} is not matched")
    return Path(str(row["file_path"].iloc[0]))


def delimiter_for_view(column_schema_df: pd.DataFrame, semantic_view: str) -> str:
    row = column_schema_df[column_schema_df["semantic_view"] == semantic_view]
    if len(row) == 0:
        return ","
    return str(row["delimiter"].iloc[0])


def primary_key_for_view(column_schema_df: pd.DataFrame, semantic_view: str) -> str:
    cols = read_columns_for_view(column_schema_df, semantic_view)
    return cols[0]


def dataframe_to_records(df: pd.DataFrame, pk_col: Optional[str], metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    records = json.loads(df.to_json(orient="records"))

    for doc in records:
        for k, v in metadata.items():
            doc[k] = v

        if pk_col and pk_col in doc:
            doc["_id"] = doc[pk_col]

    return records


def load_view_to_collection(
    db,
    mapping_df: pd.DataFrame,
    column_schema_df: pd.DataFrame,
    semantic_view: str,
    collection_name: str,
    batch_size: int,
    max_rows_per_view: Optional[int],
    extra_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    path = file_for_view(mapping_df, semantic_view)
    cols = read_columns_for_view(column_schema_df, semantic_view)
    sep = delimiter_for_view(column_schema_df, semantic_view)
    pk_col = primary_key_for_view(column_schema_df, semantic_view)

    coll = db[collection_name]
    coll.drop()

    inserted = 0
    duplicate_errors = 0
    started = time.time()

    reader = pd.read_csv(
        path,
        header=None,
        names=cols,
        sep=sep,
        chunksize=batch_size,
        compression="infer",
        low_memory=False,
    )

    for chunk in reader:
        if max_rows_per_view is not None:
            remaining = max_rows_per_view - inserted
            if remaining <= 0:
                break
            chunk = chunk.head(remaining)

        records = dataframe_to_records(
            chunk,
            pk_col=pk_col,
            metadata={
                "_lmm_source_view": semantic_view,
                "_lmm_loaded_as": collection_name,
                **extra_metadata,
            },
        )

        if records:
            try:
                coll.insert_many(records, ordered=False)
                inserted += len(records)
            except BulkWriteError as exc:
                details = exc.details or {}
                errors = details.get("writeErrors", [])
                duplicate_errors += len(errors)
                inserted += details.get("nInserted", 0)

        if max_rows_per_view is not None and inserted >= max_rows_per_view:
            break

    elapsed = time.time() - started

    try:
        coll.create_index([("_lmm_source_view", ASCENDING)])
        coll.create_index([(pk_col, ASCENDING)])
    except Exception:
        pass

    return {
        "semantic_view": semantic_view,
        "collection_name": collection_name,
        "file_path": str(path),
        "primary_key": pk_col,
        "inserted_documents": int(inserted),
        "duplicate_errors": int(duplicate_errors),
        "elapsed_seconds": elapsed,
    }


def create_indexes(db, physical_collections_df: pd.DataFrame, edges_df: pd.DataFrame) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    existing_collections = set(db.list_collection_names())

    def try_create_index(collection: str, field: Any, reason: str) -> None:
        if field is None or pd.isna(field):
            return

        field = str(field)

        if not collection or collection == "nan":
            return

        if collection not in existing_collections:
            rows.append({
                "collection": collection,
                "index": field,
                "reason": reason,
                "status": "skipped_missing_collection",
            })
            return

        try:
            db[collection].create_index([(field, ASCENDING)])
            rows.append({
                "collection": collection,
                "index": field,
                "reason": reason,
                "status": "created",
            })
        except Exception as exc:
            rows.append({
                "collection": collection,
                "index": field,
                "reason": reason,
                "status": f"failed: {exc}",
            })

    for _, row in physical_collections_df.iterrows():
        collection = str(row["collection_name"])

        if collection not in existing_collections:
            rows.append({
                "collection": collection,
                "index": None,
                "reason": "planned_collection_index",
                "status": "skipped_missing_collection",
            })
            continue

        indexes = parse_list(row.get("suggested_indexes"))

        for idx in indexes:
            if idx == "_id":
                continue
            try_create_index(collection, idx, "planned_collection_index")

    existing_collections = set(db.list_collection_names())
    root_collections = set(physical_collections_df["collection_name"].astype(str))

    for _, edge in edges_df.iterrows():
        physical_role = str(edge.get("physical_role"))
        owning_collection = str(edge.get("owning_collection"))
        secondary_collection = str(edge.get("secondary_collection"))

        # Parent-side lookup index.
        for field in [
            edge.get("selected_source_column"),
            edge.get("selected_target_column"),
            edge.get("bridge_source_column"),
            edge.get("bridge_target_column"),
        ]:
            try_create_index(owning_collection, field, "edge_parent_or_reference_index")

        # Secondary root collection index, if it exists.
        for field in [
            edge.get("selected_source_column"),
            edge.get("selected_target_column"),
            edge.get("bridge_source_column"),
            edge.get("bridge_target_column"),
        ]:
            try_create_index(secondary_collection, field, "edge_secondary_collection_index")

        # Auxiliary source collection index for embedded entities that are not root collections.
        if physical_role == "embed" and secondary_collection not in root_collections:
            secondary_entity = str(edge.get("secondary_entity"))
            semantic_view = ENTITY_TO_VIEW.get(secondary_entity)

            if semantic_view:
                aux_collection = source_collection_name(semantic_view)

                try:
                    _local_field, foreign_field = parent_and_child_fields(edge)
                    try_create_index(aux_collection, foreign_field, "auxiliary_embedding_foreign_index")
                except Exception as exc:
                    rows.append({
                        "collection": aux_collection,
                        "index": None,
                        "reason": "auxiliary_embedding_foreign_index",
                        "status": f"failed_infer_field: {exc}",
                    })

    return rows


def edge_sort_key(row: pd.Series) -> Tuple[int, str]:
    rel = str(row["relationship_name"])
    if rel in EMBED_EDGE_ORDER:
        return (EMBED_EDGE_ORDER.index(rel), rel)
    return (999, rel)


def parent_and_child_fields(edge: pd.Series) -> Tuple[str, str]:
    owning_root = str(edge["owning_root_entity"])
    source_entity = str(edge["source_entity"])
    target_entity = str(edge["target_entity"])

    if owning_root == source_entity:
        return str(edge["selected_source_column"]), str(edge["selected_target_column"])

    if owning_root == target_entity:
        return str(edge["selected_target_column"]), str(edge["selected_source_column"])

    raise RuntimeError(
        f"Cannot infer parent/child join fields for {edge['relationship_name']}: "
        f"owning={owning_root}, source={source_entity}, target={target_entity}"
    )


def lookup_collection_for_secondary(
    secondary_entity: str,
    root_collections: Set[str],
) -> str:
    candidate_root_collection = f"lmm_{camel_to_snake(secondary_entity)}"
    if candidate_root_collection in root_collections:
        return candidate_root_collection

    view = ENTITY_TO_VIEW.get(secondary_entity)
    if not view:
        raise RuntimeError(f"No semantic view mapping for secondary entity {secondary_entity}")

    return source_collection_name(view)


def camel_to_snake(value: str) -> str:
    import re
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return value.lower()


def run_embedding_edges(db, edges_df: pd.DataFrame, physical_collections_df: pd.DataFrame) -> List[Dict[str, Any]]:
    embed_df = edges_df[edges_df["physical_role"] == "embed"].copy()
    embed_df = embed_df.sort_values(by="relationship_name")
    embed_df["_sort_key"] = embed_df.apply(edge_sort_key, axis=1)
    embed_df = embed_df.sort_values("_sort_key")

    root_collections = set(physical_collections_df["collection_name"].astype(str))

    rows: List[Dict[str, Any]] = []

    for _, edge in embed_df.iterrows():
        rel = str(edge["relationship_name"])
        parent_collection = str(edge["owning_collection"])
        secondary_entity = str(edge["secondary_entity"])
        embedded_field = str(edge["embedded_field_name"])

        try:
            local_field, foreign_field = parent_and_child_fields(edge)
            lookup_from = lookup_collection_for_secondary(secondary_entity, root_collections)

            started = time.time()

            print(
                f"[{now()}] Embedding {rel}: "
                f"{parent_collection}.{local_field} -> {lookup_from}.{foreign_field} as {embedded_field}",
                flush=True,
            )

            db[parent_collection].aggregate(
                [
                    {
                        "$lookup": {
                            "from": lookup_from,
                            "localField": local_field,
                            "foreignField": foreign_field,
                            "as": embedded_field,
                        }
                    },
                    {
                        "$merge": {
                            "into": parent_collection,
                            "whenMatched": "replace",
                            "whenNotMatched": "discard",
                        }
                    },
                ],
                allowDiskUse=True,
                maxTimeMS=600000,
            )

            rows.append(
                {
                    "relationship_name": rel,
                    "parent_collection": parent_collection,
                    "lookup_from": lookup_from,
                    "local_field": local_field,
                    "foreign_field": foreign_field,
                    "embedded_field": embedded_field,
                    "status": "completed",
                    "elapsed_seconds": time.time() - started,
                }
            )

        except Exception as exc:
            rows.append(
                {
                    "relationship_name": rel,
                    "parent_collection": parent_collection,
                    "lookup_from": None,
                    "local_field": None,
                    "foreign_field": None,
                    "embedded_field": embedded_field,
                    "status": f"failed: {exc}",
                    "elapsed_seconds": None,
                }
            )

    return rows


def add_simple_reference_fields(db, edges_df: pd.DataFrame) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    ref_df = edges_df[edges_df["physical_role"] == "reference"].copy()

    for _, edge in ref_df.iterrows():
        rel = str(edge["relationship_name"])
        parent_collection = str(edge["owning_collection"])
        reference_field = str(edge["reference_field_name"])

        bridge_view = edge.get("bridge_view")
        if bridge_view is not None and not pd.isna(bridge_view):
            rows.append(
                {
                    "relationship_name": rel,
                    "parent_collection": parent_collection,
                    "reference_field": reference_field,
                    "status": "skipped_bridge_reference",
                    "note": "Bridge references are preserved through existing FK columns and handled by query runner if needed.",
                }
            )
            continue

        try:
            local_field, _foreign_field = parent_and_child_fields(edge)
            started = time.time()

            db[parent_collection].update_many(
                {},
                [{"$set": {reference_field: f"${local_field}"}}],
            )

            rows.append(
                {
                    "relationship_name": rel,
                    "parent_collection": parent_collection,
                    "reference_field": reference_field,
                    "source_field": local_field,
                    "status": "completed",
                    "elapsed_seconds": time.time() - started,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "relationship_name": rel,
                    "parent_collection": parent_collection,
                    "reference_field": reference_field,
                    "status": f"failed: {exc}",
                    "note": None,
                }
            )

    return rows


def load_materialized_collections(
    db,
    mapping_df: pd.DataFrame,
    column_schema_df: pd.DataFrame,
    physical_collections_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    batch_size: int,
    max_rows_per_view: Optional[int],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for _, coll_row in physical_collections_df.iterrows():
        root_entity = str(coll_row["root_entity"])
        collection = str(coll_row["collection_name"])
        semantic_view = ENTITY_TO_VIEW.get(root_entity)

        if semantic_view is None:
            rows.append(
                {
                    "root_entity": root_entity,
                    "collection_name": collection,
                    "status": "skipped_no_semantic_view",
                }
            )
            continue

        result = load_view_to_collection(
            db=db,
            mapping_df=mapping_df,
            column_schema_df=column_schema_df,
            semantic_view=semantic_view,
            collection_name=collection,
            batch_size=batch_size,
            max_rows_per_view=max_rows_per_view,
            extra_metadata={
                "_lmm_root_entity": root_entity,
                "_lmm_materialization_role": "root_collection",
            },
        )
        result["root_entity"] = root_entity
        result["status"] = "completed"
        rows.append(result)

    # Load auxiliary source collections needed for embedded entities that are not root collections.
    root_entities = set(physical_collections_df["root_entity"].astype(str))
    aux_entities = set(
        edges_df.loc[
            (edges_df["physical_role"] == "embed")
            & (~edges_df["secondary_entity"].astype(str).isin(root_entities)),
            "secondary_entity",
        ].astype(str)
    )

    for entity in sorted(aux_entities):
        semantic_view = ENTITY_TO_VIEW.get(entity)
        if not semantic_view:
            rows.append(
                {
                    "root_entity": entity,
                    "collection_name": None,
                    "status": "skipped_aux_no_semantic_view",
                }
            )
            continue

        collection = source_collection_name(semantic_view)
        result = load_view_to_collection(
            db=db,
            mapping_df=mapping_df,
            column_schema_df=column_schema_df,
            semantic_view=semantic_view,
            collection_name=collection,
            batch_size=batch_size,
            max_rows_per_view=max_rows_per_view,
            extra_metadata={
                "_lmm_root_entity": entity,
                "_lmm_materialization_role": "auxiliary_source_for_embedding",
            },
        )
        result["root_entity"] = entity
        result["status"] = "completed_auxiliary"
        rows.append(result)

    return rows


def count_collections(db) -> List[Dict[str, Any]]:
    rows = []
    for name in sorted(db.list_collection_names()):
        rows.append({"collection_name": name, "count": db[name].count_documents({})})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo-uri", default="mongodb://mongo:mongo@127.0.0.1:27018/admin")
    parser.add_argument("--target-db", default="lmm_fiben_sf1_source_full")
    parser.add_argument("--scale", default="sf1")
    parser.add_argument("--generated-dir", default="de_lima_mello_2015_implementation/generated/fiben")
    parser.add_argument("--batch-size", type=int, default=10000)
    parser.add_argument("--max-rows-per-view", type=int, default=None)
    parser.add_argument("--drop-target", action="store_true")
    parser.add_argument("--skip-embeddings", action="store_true")
    args = parser.parse_args()

    if args.drop_target and args.target_db in PROTECTED_DATABASES:
        raise RuntimeError(f"Refusing to drop protected database: {args.target_db}")

    generated_dir = Path(args.generated_dir)
    profile_dir = generated_dir / "source_profile" / args.scale

    mapping_df = pd.read_csv(profile_dir / f"lmm_fiben_source_file_mapping_{args.scale}.csv")
    column_schema_df = pd.read_csv(profile_dir / f"lmm_fiben_column_schema_{args.scale}.csv")
    physical_collections_df = pd.read_csv(generated_dir / "lmm_fiben_physical_collections.csv")
    edges_df = pd.read_csv(generated_dir / "lmm_fiben_physical_edges.csv")

    client = MongoClient(args.mongo_uri)
    db = client[args.target_db]

    if args.drop_target:
        print(f"[{now()}] Dropping target database: {args.target_db}")
        client.drop_database(args.target_db)

    print(f"[{now()}] Loading Lima & Mello FIBEN materialization into {args.target_db}")

    load_rows = load_materialized_collections(
        db=db,
        mapping_df=mapping_df,
        column_schema_df=column_schema_df,
        physical_collections_df=physical_collections_df,
        edges_df=edges_df,
        batch_size=args.batch_size,
        max_rows_per_view=args.max_rows_per_view,
    )

    print(f"[{now()}] Creating indexes")
    index_rows = create_indexes(db, physical_collections_df, edges_df)

    if args.skip_embeddings:
        embed_rows = []
        reference_rows = []
        print(f"[{now()}] Skipping embeddings and reference fields")
    else:
        print(f"[{now()}] Running Rule-5 embedding edges")
        embed_rows = run_embedding_edges(db, edges_df, physical_collections_df)

        print(f"[{now()}] Adding simple Rule-6 reference fields")
        reference_rows = add_simple_reference_fields(db, edges_df)

    count_rows = count_collections(db)

    output_dir = Path("de_lima_mello_2015_implementation/results/fiben/materialization") / args.scale / args.target_db
    output_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(load_rows).to_csv(output_dir / "lmm_materialization_load_summary.csv", index=False)
    pd.DataFrame(index_rows).to_csv(output_dir / "lmm_materialization_index_summary.csv", index=False)
    pd.DataFrame(embed_rows).to_csv(output_dir / "lmm_materialization_embedding_summary.csv", index=False)
    pd.DataFrame(reference_rows).to_csv(output_dir / "lmm_materialization_reference_summary.csv", index=False)
    pd.DataFrame(count_rows).to_csv(output_dir / "lmm_materialization_collection_counts.csv", index=False)

    report = {
        "status": "completed",
        "target_database": args.target_db,
        "scale": args.scale,
        "max_rows_per_view": args.max_rows_per_view,
        "skip_embeddings": args.skip_embeddings,
        "n_collections": len(count_rows),
        "collections": count_rows,
        "embedding_status_counts": pd.Series([r.get("status") for r in embed_rows]).value_counts().to_dict() if embed_rows else {},
        "reference_status_counts": pd.Series([r.get("status") for r in reference_rows]).value_counts().to_dict() if reference_rows else {},
        "output_dir": str(output_dir),
    }

    (output_dir / "lmm_materialization_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=safe_json),
        encoding="utf-8",
    )

    print(f"[{now()}] Done.")
    print(json.dumps(report, indent=2, sort_keys=True, default=safe_json))


if __name__ == "__main__":
    main()
