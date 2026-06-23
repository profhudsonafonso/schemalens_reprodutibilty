#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import run_dbsr_fiben_query_benchmark as bench


QUERY_NAMES = [
    "Q1_CompanyProfileIBM",
    "Q2_CompanyWithIndustryCountryAndListedSecurities",
    "Q3_SecuritiesHeldInEachFinancialServiceAccount",
    "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity",
    "Q5_ReportsAndMetricDataOfCompany",
    "Q6_TechUSListedSecuritiesWithHighLastTradedValue",
    "Q7_PersonsWhoBoughtMoreIBMThanSold",
    "Q8_IBMTransactionsBelowAverageSellingPrice",
    "Q9_PersonsWhoBoughtAndSoldSameStock",
    "Q10_CreateAccountHoldingAndBuyTransaction",
]


ROOT_ENTITY = {
    "Q1_CompanyProfileIBM": "Corporation",
    "Q2_CompanyWithIndustryCountryAndListedSecurities": "Corporation",
    "Q3_SecuritiesHeldInEachFinancialServiceAccount": "FinancialServiceAccount",
    "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity": "Person",
    "Q5_ReportsAndMetricDataOfCompany": "Corporation",
    "Q6_TechUSListedSecuritiesWithHighLastTradedValue": "ListedSecurity",
    "Q7_PersonsWhoBoughtMoreIBMThanSold": "Corporation",
    "Q8_IBMTransactionsBelowAverageSellingPrice": "Corporation",
    "Q9_PersonsWhoBoughtAndSoldSameStock": "ListedSecurity",
    "Q10_CreateAccountHoldingAndBuyTransaction": "Person",
}


SUMMARY_COLUMNS = [
    "candidate_id",
    "query_name",
    "final_benchmark_group",
    "design_pattern",
    "g_class",
    "root_entity",
    "scale_label",
    "run_phase",
    "repetition",
    "execution_db_name",
    "execution_status",
    "n_components",
    "n_completed_components",
    "n_failed_components",
    "sum_execution_time_millis",
    "sum_n_returned",
    "sum_total_docs_examined",
    "sum_total_keys_examined",
    "docs_per_returned_total",
    "keys_per_returned_total",
    "has_IXSCAN",
    "has_COLLSCAN",
    "has_FETCH",
    "has_SORT",
    "has_AND_SORTED",
    "has_OR",
    "has_PROJECTION",
    "has_LOOKUP",
    "has_GROUP",
    "used_disk",
    "all_stages",
    "all_index_names",
    "query_hashes",
    "plan_cache_keys",
    "n_rejected_plans",
    "sum_estimated_docs_examined_bytes",
    "sum_estimated_returned_bytes",
    "estimated_examined_bytes_per_returned",
    "max_docs_examined_collection_ratio",
    "max_index_to_data_size_ratio",
    "max_collection_avg_obj_size_bytes",
    "collections_touched",
    "source_results_dir",
]


COMPONENT_COLUMNS = [
    "candidate_id",
    "query_name",
    "final_benchmark_group",
    "selection_role",
    "benchmark_priority",
    "g_class",
    "design_pattern",
    "variant",
    "root_entity",
    "collection_name",
    "scale_label",
    "run_phase",
    "repetition",
    "component_no",
    "component_name",
    "component_role",
    "operation_type",
    "filter_json",
    "pipeline_json",
    "projection_json",
    "limit",
    "sort_json",
    "start_ts",
    "end_ts",
    "execution_status",
    "error_message",
    "raw_explain_path",
    "execution_time_millis",
    "n_returned",
    "total_docs_examined",
    "total_keys_examined",
    "docs_per_returned_total",
    "keys_per_returned_total",
    "all_stages_json",
    "all_index_names_json",
    "all_stages",
    "all_index_names",
    "has_IXSCAN",
    "has_COLLSCAN",
    "has_FETCH",
    "has_SORT",
    "has_AND_SORTED",
    "has_OR",
    "has_PROJECTION",
    "has_LOOKUP",
    "has_GROUP",
    "used_disk",
    "query_hash",
    "plan_cache_key",
    "n_rejected_plans",
    "collection_count",
    "collection_size_bytes",
    "collection_avg_obj_size_bytes",
    "collection_storage_size_bytes",
    "collection_total_index_size_bytes",
    "collection_total_size_bytes",
    "collection_free_storage_size_bytes",
    "collection_nindexes",
    "collection_index_sizes_json",
    "estimated_docs_examined_bytes",
    "estimated_returned_bytes",
    "estimated_examined_bytes_per_returned",
    "docs_examined_collection_ratio",
    "index_to_data_size_ratio",
    "parameter_json",
    "execution_db_name",
    "source_results_dir",
]


def safe_json_dumps(value: Any, max_len: int = 4000) -> str:
    try:
        s = json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)
    except Exception:
        s = str(value)
    if max_len and len(s) > max_len:
        return s[:max_len] + "...<truncated>"
    return s


def recursive_plan_walk(obj: Any, stages: List[str], indexes: List[str], used_disk_flags: List[bool]) -> None:
    if isinstance(obj, dict):
        stage = obj.get("stage")
        if isinstance(stage, str):
            stages.append(stage)

        index_name = obj.get("indexName")
        if isinstance(index_name, str):
            indexes.append(index_name)

        if "usedDisk" in obj:
            used_disk_flags.append(bool(obj.get("usedDisk")))

        for key, value in obj.items():
            if isinstance(key, str):
                key_upper = key.upper().lstrip("$")
                if key_upper in {"LOOKUP", "GROUP", "SORT", "PROJECT", "MATCH", "UNWIND"}:
                    stages.append("PROJECTION" if key_upper == "PROJECT" else key_upper)
            recursive_plan_walk(value, stages, indexes, used_disk_flags)

    elif isinstance(obj, list):
        for item in obj:
            recursive_plan_walk(item, stages, indexes, used_disk_flags)


def first_non_null_recursive(obj: Any, keys: Iterable[str]) -> Any:
    keys = set(keys)
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in keys and value is not None:
                return value
        for value in obj.values():
            found = first_non_null_recursive(value, keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = first_non_null_recursive(item, keys)
            if found is not None:
                return found
    return None


def count_rejected_plans(explain_doc: Dict[str, Any]) -> int:
    qp = explain_doc.get("queryPlanner", {}) if isinstance(explain_doc, dict) else {}
    rejected = qp.get("rejectedPlans", []) if isinstance(qp, dict) else []
    return len(rejected) if isinstance(rejected, list) else 0


def summarize_explain_doc(explain_doc: Dict[str, Any]) -> Dict[str, Any]:
    stages: List[str] = []
    indexes: List[str] = []
    used_disk_flags: List[bool] = []

    recursive_plan_walk(explain_doc, stages, indexes, used_disk_flags)

    stage_set = set(stages)
    index_set = set(indexes)

    execution_stats = explain_doc.get("executionStats", {}) if isinstance(explain_doc, dict) else {}
    if not isinstance(execution_stats, dict):
        execution_stats = {}

    n_returned = execution_stats.get("nReturned")
    total_docs_examined = execution_stats.get("totalDocsExamined")
    total_keys_examined = execution_stats.get("totalKeysExamined")
    execution_time_millis = execution_stats.get("executionTimeMillis")

    if n_returned is None:
        n_returned = first_non_null_recursive(explain_doc, ["nReturned"])
    if total_docs_examined is None:
        total_docs_examined = first_non_null_recursive(explain_doc, ["totalDocsExamined", "docsExamined"])
    if total_keys_examined is None:
        total_keys_examined = first_non_null_recursive(explain_doc, ["totalKeysExamined", "keysExamined"])
    if execution_time_millis is None:
        execution_time_millis = first_non_null_recursive(explain_doc, ["executionTimeMillis"])

    n_returned = int(n_returned or 0)
    total_docs_examined = int(total_docs_examined or 0)
    total_keys_examined = int(total_keys_examined or 0)
    execution_time_millis = float(execution_time_millis or 0.0)

    return {
        "execution_time_millis": execution_time_millis,
        "n_returned": n_returned,
        "total_docs_examined": total_docs_examined,
        "total_keys_examined": total_keys_examined,
        "docs_per_returned_total": (
            float(total_docs_examined) / float(n_returned) if n_returned > 0 else None
        ),
        "keys_per_returned_total": (
            float(total_keys_examined) / float(n_returned) if n_returned > 0 else None
        ),
        "all_stages": sorted(stage_set),
        "all_index_names": sorted(index_set),
        "has_IXSCAN": ("IXSCAN" in stage_set) or ("EXPRESS_IXSCAN" in stage_set),
        "has_COLLSCAN": "COLLSCAN" in stage_set,
        "has_FETCH": "FETCH" in stage_set,
        "has_SORT": "SORT" in stage_set,
        "has_AND_SORTED": "AND_SORTED" in stage_set,
        "has_OR": "OR" in stage_set,
        "has_PROJECTION": "PROJECTION" in stage_set,
        "has_LOOKUP": "LOOKUP" in stage_set,
        "has_GROUP": "GROUP" in stage_set,
        "used_disk": any(used_disk_flags),
        "query_hash": first_non_null_recursive(explain_doc, ["queryHash"]),
        "plan_cache_key": first_non_null_recursive(explain_doc, ["planCacheKey"]),
        "n_rejected_plans": count_rejected_plans(explain_doc),
    }


def get_collection_stats(db, collection_name: str) -> Dict[str, Any]:
    try:
        stats = db.command("collStats", collection_name)
    except Exception:
        return {
            "collection_count": None,
            "collection_size_bytes": None,
            "collection_avg_obj_size_bytes": None,
            "collection_storage_size_bytes": None,
            "collection_total_index_size_bytes": None,
            "collection_total_size_bytes": None,
            "collection_free_storage_size_bytes": None,
            "collection_nindexes": None,
            "collection_index_sizes_json": None,
        }

    return {
        "collection_count": stats.get("count"),
        "collection_size_bytes": stats.get("size"),
        "collection_avg_obj_size_bytes": stats.get("avgObjSize"),
        "collection_storage_size_bytes": stats.get("storageSize"),
        "collection_total_index_size_bytes": stats.get("totalIndexSize"),
        "collection_total_size_bytes": stats.get("totalSize"),
        "collection_free_storage_size_bytes": stats.get("freeStorageSize"),
        "collection_nindexes": stats.get("nindexes"),
        "collection_index_sizes_json": safe_json_dumps(stats.get("indexSizes", {})),
    }


def explain_find(
    db,
    collection_name: str,
    filter_doc: Dict[str, Any],
    projection_doc: Optional[Dict[str, Any]],
    limit: Optional[int],
    sort_doc: Optional[Dict[str, Any]],
    verbosity: str,
) -> Dict[str, Any]:
    cmd: Dict[str, Any] = {
        "find": collection_name,
        "filter": filter_doc or {},
    }

    if projection_doc is not None:
        cmd["projection"] = projection_doc
    if limit is not None:
        cmd["limit"] = int(limit)
    if sort_doc is not None:
        cmd["sort"] = sort_doc

    return db.command("explain", cmd, verbosity=verbosity)


def base_metadata(query_name: str, args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "candidate_id": f"dbsr_{query_name.lower()}__materialized_baseline",
        "query_name": query_name,
        "final_benchmark_group": "baseline",
        "selection_role": "baseline_comparison",
        "benchmark_priority": "dbsr",
        "g_class": "DBSR",
        "design_pattern": "dbsr_materialized_document_tree",
        "variant": "dbsr_materialized",
        "root_entity": ROOT_ENTITY.get(query_name),
        "scale_label": args.scale_label,
        "run_phase": args.run_phase,
        "execution_db_name": args.mongo_db,
        "source_results_dir": str(Path(args.out_dir)),
    }


def build_component_row(
    db,
    args: argparse.Namespace,
    query_name: str,
    repetition: int,
    component_no: int,
    component_name: str,
    collection_name: str,
    filter_doc: Dict[str, Any],
    projection_doc: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
    sort_doc: Optional[Dict[str, Any]] = None,
    component_role: str = "read",
    operation_type: str = "find",
    parameter: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    start_ts = datetime.now(timezone.utc).isoformat()
    end_ts = start_ts
    status = "completed"
    error_message = ""
    raw_explain_path = None
    explain_doc: Dict[str, Any] = {}
    summary: Dict[str, Any] = {}

    try:
        explain_doc = explain_find(
            db=db,
            collection_name=collection_name,
            filter_doc=filter_doc,
            projection_doc=projection_doc,
            limit=limit,
            sort_doc=sort_doc,
            verbosity=args.explain_verbosity,
        )
        summary = summarize_explain_doc(explain_doc)
        end_ts = datetime.now(timezone.utc).isoformat()

        if args.save_raw_explain:
            raw_dir = Path(args.out_dir) / "raw_explain" / args.scale_label
            raw_dir.mkdir(parents=True, exist_ok=True)
            raw_path = raw_dir / f"{query_name}__rep{repetition:02d}__c{component_no:02d}_{component_name}.json"
            raw_path.write_text(json.dumps(explain_doc, indent=2, default=str) + "\n", encoding="utf-8")
            raw_explain_path = str(raw_path)

    except Exception as exc:
        status = "failed"
        error_message = repr(exc)
        end_ts = datetime.now(timezone.utc).isoformat()
        summary = {
            "execution_time_millis": None,
            "n_returned": 0,
            "total_docs_examined": 0,
            "total_keys_examined": 0,
            "docs_per_returned_total": None,
            "keys_per_returned_total": None,
            "all_stages": [],
            "all_index_names": [],
            "has_IXSCAN": False,
            "has_COLLSCAN": False,
            "has_FETCH": False,
            "has_SORT": False,
            "has_AND_SORTED": False,
            "has_OR": False,
            "has_PROJECTION": False,
            "has_LOOKUP": False,
            "has_GROUP": False,
            "used_disk": False,
            "query_hash": None,
            "plan_cache_key": None,
            "n_rejected_plans": 0,
        }

    stats = get_collection_stats(db, collection_name)
    avg_obj_size = stats.get("collection_avg_obj_size_bytes") or 0
    docs_examined = summary.get("total_docs_examined") or 0
    n_returned = summary.get("n_returned") or 0
    collection_count = stats.get("collection_count") or 0
    collection_size = stats.get("collection_size_bytes") or 0
    index_size = stats.get("collection_total_index_size_bytes") or 0

    estimated_docs_examined_bytes = float(docs_examined) * float(avg_obj_size) if avg_obj_size else None
    estimated_returned_bytes = float(n_returned) * float(avg_obj_size) if avg_obj_size else None

    row = {}
    row.update(base_metadata(query_name, args))
    row.update({
        "collection_name": collection_name,
        "repetition": repetition,
        "component_no": component_no,
        "component_name": component_name,
        "component_role": component_role,
        "operation_type": operation_type,
        "filter_json": safe_json_dumps(filter_doc),
        "pipeline_json": None,
        "projection_json": safe_json_dumps(projection_doc or {}),
        "limit": limit,
        "sort_json": safe_json_dumps(sort_doc or {}),
        "start_ts": start_ts,
        "end_ts": end_ts,
        "execution_status": status,
        "error_message": error_message,
        "raw_explain_path": raw_explain_path,
        "execution_time_millis": summary.get("execution_time_millis"),
        "n_returned": n_returned,
        "total_docs_examined": docs_examined,
        "total_keys_examined": summary.get("total_keys_examined") or 0,
        "docs_per_returned_total": summary.get("docs_per_returned_total"),
        "keys_per_returned_total": summary.get("keys_per_returned_total"),
        "all_stages_json": safe_json_dumps(summary.get("all_stages", [])),
        "all_index_names_json": safe_json_dumps(summary.get("all_index_names", [])),
        "all_stages": ";".join(summary.get("all_stages", [])),
        "all_index_names": ";".join(summary.get("all_index_names", [])),
        "has_IXSCAN": summary.get("has_IXSCAN"),
        "has_COLLSCAN": summary.get("has_COLLSCAN"),
        "has_FETCH": summary.get("has_FETCH"),
        "has_SORT": summary.get("has_SORT"),
        "has_AND_SORTED": summary.get("has_AND_SORTED"),
        "has_OR": summary.get("has_OR"),
        "has_PROJECTION": summary.get("has_PROJECTION"),
        "has_LOOKUP": summary.get("has_LOOKUP"),
        "has_GROUP": summary.get("has_GROUP"),
        "used_disk": summary.get("used_disk"),
        "query_hash": summary.get("query_hash"),
        "plan_cache_key": summary.get("plan_cache_key"),
        "n_rejected_plans": summary.get("n_rejected_plans"),
        **stats,
        "estimated_docs_examined_bytes": estimated_docs_examined_bytes,
        "estimated_returned_bytes": estimated_returned_bytes,
        "estimated_examined_bytes_per_returned": (
            estimated_docs_examined_bytes / float(n_returned)
            if estimated_docs_examined_bytes is not None and n_returned > 0 else None
        ),
        "docs_examined_collection_ratio": (
            float(docs_examined) / float(collection_count)
            if collection_count else None
        ),
        "index_to_data_size_ratio": (
            float(index_size) / float(collection_size)
            if collection_size else None
        ),
        "parameter_json": safe_json_dumps(parameter or {}, max_len=2000),
    })

    return row


def skipped_q10_row(args: argparse.Namespace, repetition: int) -> Dict[str, Any]:
    row = {}
    query_name = "Q10_CreateAccountHoldingAndBuyTransaction"
    row.update(base_metadata(query_name, args))
    row.update({
        "collection_name": "not_explainable",
        "repetition": repetition,
        "component_no": 1,
        "component_name": "not_explainable",
        "component_role": "not_explainable",
        "operation_type": "not_explainable",
        "filter_json": None,
        "pipeline_json": None,
        "projection_json": None,
        "limit": None,
        "sort_json": None,
        "start_ts": datetime.now(timezone.utc).isoformat(),
        "end_ts": datetime.now(timezone.utc).isoformat(),
        "execution_status": "skipped",
        "error_message": "insert/update workload is not explainable through MongoDB executionStats in this runner",
        "raw_explain_path": None,
        "execution_time_millis": 0,
        "n_returned": 0,
        "total_docs_examined": 0,
        "total_keys_examined": 0,
        "docs_per_returned_total": None,
        "keys_per_returned_total": None,
        "all_stages_json": "[]",
        "all_index_names_json": "[]",
        "all_stages": None,
        "all_index_names": None,
        "has_IXSCAN": False,
        "has_COLLSCAN": False,
        "has_FETCH": False,
        "has_SORT": False,
        "has_AND_SORTED": False,
        "has_OR": False,
        "has_PROJECTION": False,
        "has_LOOKUP": False,
        "has_GROUP": False,
        "used_disk": False,
        "query_hash": None,
        "plan_cache_key": None,
        "n_rejected_plans": 0,
        "parameter_json": "{}",
    })
    return row


def q1_components(db, args, params, repetition):
    corp_id = bench.get_param(params, "Q1_CompanyProfileIBM", "corporation_id")
    return [build_component_row(db, args, "Q1_CompanyProfileIBM", repetition, 1, "corporation_root", "dbsr_rank03_corporation", {"CORPORATIONID": corp_id}, None, 1, None, parameter={"corporation_id": corp_id})]


def q2_components(db, args, params, repetition):
    q = "Q2_CompanyWithIndustryCountryAndListedSecurities"
    corp_id = bench.get_param(params, q, "corporation_id")
    return [
        build_component_row(db, args, q, repetition, 1, "corporation_root", "dbsr_rank03_corporation", {"CORPORATIONID": corp_id}, None, 1, None, parameter={"corporation_id": corp_id}),
        build_component_row(db, args, q, repetition, 2, "corporation_country", "dbsr_rank05_corporation_country", {"CORPORATIONID": corp_id}, None, 1, None, parameter={"corporation_id": corp_id}),
        build_component_row(db, args, q, repetition, 3, "corporation_industry", "dbsr_rank06_corporation_industry", {"CORPORATIONID": corp_id}, None, 1, None, parameter={"corporation_id": corp_id}),
        build_component_row(db, args, q, repetition, 4, "corporation_security_listedsecurity", "dbsr_rank08_corporation_security_listedsecurity", {"CORPORATIONID": corp_id}, None, None, None, parameter={"corporation_id": corp_id}),
    ]


def q3_components(db, args, params, repetition):
    q = "Q3_SecuritiesHeldInEachFinancialServiceAccount"
    account_id = bench.get_param(params, q, "financial_service_account_id")

    rows = [
        build_component_row(db, args, q, repetition, 1, "account_holding_listedsecurity", "dbsr_rank07_financialserviceaccount_holding_listedsecurity", {"FINANCIALSERVICEACCOUNTID": account_id}, None, 1, None, parameter={"financial_service_account_id": account_id})
    ]

    account_doc = db.dbsr_rank07_financialserviceaccount_holding_listedsecurity.find_one({"FINANCIALSERVICEACCOUNTID": account_id})
    security_ids = []
    if account_doc:
        holdings = account_doc.get("holding", [])
        if isinstance(holdings, dict):
            holdings = [holdings]
        security_ids = [
            h.get("REFERSTO") for h in holdings
            if isinstance(h, dict) and h.get("REFERSTO") is not None
        ]

    conditions = bench.suffix_regex_conditions("LISTEDSECURITYID", security_ids)
    rows.append(
        build_component_row(db, args, q, repetition, 2, "listedsecurity_suffix_lookup", "dbsr_rank01_listedsecurity", {"$or": conditions} if conditions else {"_id": "__no_match__"}, {"LISTEDSECURITYID": 1}, None, None, parameter={"financial_service_account_id": account_id, "security_ids_count": len(security_ids)})
    )
    return rows


def q4_components(db, args, params, repetition):
    q = "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity"
    person_id = bench.get_param(params, q, "person_id")

    rows = [
        build_component_row(db, args, q, repetition, 1, "person_account_holding", "dbsr_rank11_person_financialserviceaccount_holding", {"PERSONID": person_id}, None, 1, None, parameter={"person_id": person_id})
    ]

    person_doc = db.dbsr_rank11_person_financialserviceaccount_holding.find_one({"PERSONID": person_id})
    security_ids = bench.list_values(person_doc, "financialServiceAccount.holding.REFERSTO") if person_doc else []
    conditions = bench.suffix_regex_conditions("security.SECURITYID", security_ids)

    rows.append(
        build_component_row(db, args, q, repetition, 2, "security_corporation_suffix_lookup", "dbsr_rank12_listedsecurity_security_corporation", {"$or": conditions} if conditions else {"_id": "__no_match__"}, None, None, None, parameter={"person_id": person_id, "security_ids_count": len(security_ids)})
    )
    return rows


def q5_components(db, args, params, repetition):
    q = "Q5_ReportsAndMetricDataOfCompany"
    corp_id = bench.get_param(params, q, "corporation_id")
    return [
        build_component_row(db, args, q, repetition, 1, "financialreport_reportelement_statementelement", "dbsr_rank13_financialreport_reportelement_statementelement", {"REPORTSOF": corp_id}, None, None, None, parameter={"corporation_id": corp_id})
    ]


def q6_components(db, args, params, repetition):
    q = "Q6_TechUSListedSecuritiesWithHighLastTradedValue"
    return [
        build_component_row(db, args, q, repetition, 1, "listedsecurity_capped_scan", "dbsr_rank01_listedsecurity", {}, {"LISTEDSECURITYID": 1}, 100, None, parameter={"limit": 100})
    ]


def q7_components(db, args, params, repetition):
    q = "Q7_PersonsWhoBoughtMoreIBMThanSold"
    corp_id = bench.get_param(params, q, "corporation_id")
    if corp_id is None:
        corp_id = bench.get_param(params, "Q1_CompanyProfileIBM", "corporation_id")

    security_ids = bench.security_ids_for_corporation(db, corp_id)

    return [
        build_component_row(db, args, q, repetition, 1, "corporation_security_lookup", "dbsr_rank12_listedsecurity_security_corporation", {"security.corporation.CORPORATIONID": corp_id}, {"LISTEDSECURITYID": 1, "security.SECURITYID": 1}, None, None, parameter={"corporation_id": corp_id}),
        build_component_row(db, args, q, repetition, 2, "transactions_for_corporation_securities", "dbsr_rank02_transaction_listedsecurity", {"REFERSTO": {"$in": security_ids}} if security_ids else {"_id": "__no_match__"}, None, None, None, parameter={"corporation_id": corp_id, "security_ids_count": len(security_ids)}),
    ]


def q8_components(db, args, params, repetition):
    q = "Q8_IBMTransactionsBelowAverageSellingPrice"
    corp_id = bench.get_param(params, q, "corporation_id")
    if corp_id is None:
        corp_id = bench.get_param(params, "Q1_CompanyProfileIBM", "corporation_id")

    security_ids = bench.security_ids_for_corporation(db, corp_id)

    return [
        build_component_row(db, args, q, repetition, 1, "corporation_security_lookup", "dbsr_rank12_listedsecurity_security_corporation", {"security.corporation.CORPORATIONID": corp_id}, {"LISTEDSECURITYID": 1, "security.SECURITYID": 1}, None, None, parameter={"corporation_id": corp_id}),
        build_component_row(db, args, q, repetition, 2, "transactions_for_average_price", "dbsr_rank02_transaction_listedsecurity", {"REFERSTO": {"$in": security_ids}} if security_ids else {"_id": "__no_match__"}, None, None, None, parameter={"corporation_id": corp_id, "security_ids_count": len(security_ids)}),
    ]


def q9_components(db, args, params, repetition):
    q = "Q9_PersonsWhoBoughtAndSoldSameStock"
    stock_id = bench.get_param(params, q, "matched_stock_id")
    return [
        build_component_row(db, args, q, repetition, 1, "transactions_for_same_stock", "dbsr_rank02_transaction_listedsecurity", {"REFERSTO": stock_id} if stock_id is not None else {"_id": "__no_match__"}, None, None, None, parameter={"matched_stock_id": stock_id})
    ]


COMPONENT_BUILDERS = {
    "Q1_CompanyProfileIBM": q1_components,
    "Q2_CompanyWithIndustryCountryAndListedSecurities": q2_components,
    "Q3_SecuritiesHeldInEachFinancialServiceAccount": q3_components,
    "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity": q4_components,
    "Q5_ReportsAndMetricDataOfCompany": q5_components,
    "Q6_TechUSListedSecuritiesWithHighLastTradedValue": q6_components,
    "Q7_PersonsWhoBoughtMoreIBMThanSold": q7_components,
    "Q8_IBMTransactionsBelowAverageSellingPrice": q8_components,
    "Q9_PersonsWhoBoughtAndSoldSameStock": q9_components,
}


def parse_json_list_cell(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, float) and math.isnan(value):
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            obj = json.loads(s)
            if isinstance(obj, list):
                return [str(v) for v in obj]
        except Exception:
            pass
        return [v for v in s.split(";") if v]
    return [str(value)]


def aggregate_summary(component_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[tuple, List[Dict[str, Any]]] = {}

    group_cols = [
        "candidate_id",
        "query_name",
        "final_benchmark_group",
        "design_pattern",
        "g_class",
        "root_entity",
        "scale_label",
        "run_phase",
        "repetition",
        "execution_db_name",
    ]

    for row in component_rows:
        key = tuple(row.get(c) for c in group_cols)
        groups.setdefault(key, []).append(row)

    out = []

    for key, grp in groups.items():
        kd = dict(zip(group_cols, key))

        completed = [r for r in grp if r.get("execution_status") == "completed"]
        failed = [r for r in grp if r.get("execution_status") == "failed"]
        skipped = [r for r in grp if r.get("execution_status") == "skipped"]

        all_stages = set()
        all_indexes = set()

        for r in grp:
            all_stages.update(parse_json_list_cell(r.get("all_stages_json")))
            all_indexes.update(parse_json_list_cell(r.get("all_index_names_json")))

        sum_n_returned = sum(int(r.get("n_returned") or 0) for r in grp)
        sum_docs_examined = sum(int(r.get("total_docs_examined") or 0) for r in grp)
        sum_keys_examined = sum(int(r.get("total_keys_examined") or 0) for r in grp)
        sum_exec_ms = sum(float(r.get("execution_time_millis") or 0.0) for r in grp)
        sum_est_docs_bytes = sum(float(r.get("estimated_docs_examined_bytes") or 0.0) for r in grp)
        sum_est_returned_bytes = sum(float(r.get("estimated_returned_bytes") or 0.0) for r in grp)

        status = "completed"
        if failed:
            status = "failed"
        elif skipped and not completed:
            status = "skipped"

        row = {}
        row.update(kd)
        row.update({
            "execution_status": status,
            "n_components": len(grp),
            "n_completed_components": len(completed),
            "n_failed_components": len(failed),
            "sum_execution_time_millis": round(sum_exec_ms, 6),
            "sum_n_returned": int(sum_n_returned),
            "sum_total_docs_examined": int(sum_docs_examined),
            "sum_total_keys_examined": int(sum_keys_examined),
            "docs_per_returned_total": (
                float(sum_docs_examined) / float(sum_n_returned)
                if sum_n_returned > 0 else None
            ),
            "keys_per_returned_total": (
                float(sum_keys_examined) / float(sum_n_returned)
                if sum_n_returned > 0 else None
            ),
            "has_IXSCAN": any(bool(r.get("has_IXSCAN")) for r in grp),
            "has_COLLSCAN": any(bool(r.get("has_COLLSCAN")) for r in grp),
            "has_FETCH": any(bool(r.get("has_FETCH")) for r in grp),
            "has_SORT": any(bool(r.get("has_SORT")) for r in grp),
            "has_AND_SORTED": any(bool(r.get("has_AND_SORTED")) for r in grp),
            "has_OR": any(bool(r.get("has_OR")) for r in grp),
            "has_PROJECTION": any(bool(r.get("has_PROJECTION")) for r in grp),
            "has_LOOKUP": any(bool(r.get("has_LOOKUP")) for r in grp),
            "has_GROUP": any(bool(r.get("has_GROUP")) for r in grp),
            "used_disk": any(bool(r.get("used_disk")) for r in grp),
            "all_stages": ";".join(sorted(all_stages)),
            "all_index_names": ";".join(sorted(all_indexes)),
            "query_hashes": ";".join(sorted({str(r.get("query_hash")) for r in grp if r.get("query_hash")})),
            "plan_cache_keys": ";".join(sorted({str(r.get("plan_cache_key")) for r in grp if r.get("plan_cache_key")})),
            "n_rejected_plans": sum(int(r.get("n_rejected_plans") or 0) for r in grp),
            "sum_estimated_docs_examined_bytes": round(sum_est_docs_bytes, 6),
            "sum_estimated_returned_bytes": round(sum_est_returned_bytes, 6),
            "estimated_examined_bytes_per_returned": (
                sum_est_docs_bytes / float(sum_n_returned)
                if sum_n_returned > 0 else None
            ),
            "max_docs_examined_collection_ratio": max(
                [float(r.get("docs_examined_collection_ratio") or 0.0) for r in grp],
                default=0.0,
            ),
            "max_index_to_data_size_ratio": max(
                [float(r.get("index_to_data_size_ratio") or 0.0) for r in grp],
                default=0.0,
            ),
            "max_collection_avg_obj_size_bytes": max(
                [float(r.get("collection_avg_obj_size_bytes") or 0.0) for r in grp],
                default=0.0,
            ),
            "collections_touched": ";".join(sorted({str(r.get("collection_name")) for r in grp if r.get("collection_name")})),
            "source_results_dir": grp[0].get("source_results_dir"),
        })
        out.append(row)

    return sorted(out, key=lambda r: (r["scale_label"], r["query_name"], int(r["repetition"])))


def compact_candidates(summary_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[tuple, List[Dict[str, Any]]] = {}

    for r in summary_rows:
        key = (
            r.get("scale_label"),
            r.get("query_name"),
            r.get("candidate_id"),
            r.get("final_benchmark_group"),
            r.get("g_class"),
            r.get("design_pattern"),
        )
        groups.setdefault(key, []).append(r)

    out = []
    for key, grp in groups.items():
        scale_label, query_name, candidate_id, group, g_class, pattern = key
        completed = [r for r in grp if r.get("execution_status") == "completed"]
        status = "completed" if len(completed) == len(grp) else grp[0].get("execution_status")
        reps = max(len(grp), 1)

        out.append({
            "scale_label": scale_label,
            "query_name": query_name,
            "candidate_id": candidate_id,
            "final_benchmark_group": group,
            "g_class": g_class,
            "design_pattern": pattern,
            "execution_status": status,
            "n_components": round(sum(int(r.get("n_components") or 0) for r in grp) / reps, 6),
            "sum_n_returned": round(sum(float(r.get("sum_n_returned") or 0) for r in grp) / reps, 6),
            "sum_total_docs_examined": round(sum(float(r.get("sum_total_docs_examined") or 0) for r in grp) / reps, 6),
            "sum_total_keys_examined": round(sum(float(r.get("sum_total_keys_examined") or 0) for r in grp) / reps, 6),
            "has_IXSCAN": any(bool(r.get("has_IXSCAN")) for r in grp),
            "has_COLLSCAN": any(bool(r.get("has_COLLSCAN")) for r in grp),
            "has_GROUP": any(bool(r.get("has_GROUP")) for r in grp),
            "sum_estimated_docs_examined_bytes": round(sum(float(r.get("sum_estimated_docs_examined_bytes") or 0) for r in grp) / reps, 6),
            "max_collection_avg_obj_size_bytes": max(float(r.get("max_collection_avg_obj_size_bytes") or 0) for r in grp),
            "collections_touched": ";".join(sorted({c for r in grp for c in str(r.get("collections_touched") or "").split(";") if c})),
            "source_results_dir": grp[0].get("source_results_dir"),
        })

    return sorted(out, key=lambda r: (r["scale_label"], r["query_name"]))


def overview_rows(compact_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for r in compact_rows:
        groups.setdefault((r["scale_label"], r["query_name"]), []).append(r)

    out = []
    for (scale_label, query_name), grp in groups.items():
        out.append({
            "scale_label": scale_label,
            "query_name": query_name,
            "n_candidates": len(grp),
            "n_completed": sum(1 for r in grp if r.get("execution_status") == "completed"),
            "n_skipped": sum(1 for r in grp if r.get("execution_status") == "skipped"),
            "n_failed": sum(1 for r in grp if r.get("execution_status") == "failed"),
            "candidate_groups": ";".join(sorted({str(r.get("final_benchmark_group")) for r in grp})),
            "g_classes": ";".join(sorted({str(r.get("g_class")) for r in grp})),
            "min_components": min(float(r.get("n_components") or 0) for r in grp),
            "max_components": max(float(r.get("n_components") or 0) for r in grp),
            "has_any_collscan": any(bool(r.get("has_COLLSCAN")) for r in grp),
            "has_any_group": any(bool(r.get("has_GROUP")) for r in grp),
            "total_docs_examined": round(sum(float(r.get("sum_total_docs_examined") or 0) for r in grp), 6),
            "total_keys_examined": round(sum(float(r.get("sum_total_keys_examined") or 0) for r in grp), 6),
            "total_estimated_docs_examined_bytes": round(sum(float(r.get("sum_estimated_docs_examined_bytes") or 0) for r in grp), 6),
        })
    return sorted(out, key=lambda r: (r["scale_label"], r["query_name"]))


def status_rows(compact_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[tuple, int] = {}
    for r in compact_rows:
        key = (r["scale_label"], r["query_name"], r["execution_status"])
        groups[key] = groups.get(key, 0) + 1
    return [
        {
            "scale_label": scale,
            "query_name": query,
            "execution_status": status,
            "n_candidates": n,
        }
        for (scale, query, status), n in sorted(groups.items())
    ]


def write_csv(path: Path, rows: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        columns = sorted({k for r in rows for k in r.keys()})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def connect_mongo(args: argparse.Namespace):
    from pymongo import MongoClient

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


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DBSR FIBEN MongoDB query-plan runner")
    p.add_argument("--parameter-probe", required=True)
    p.add_argument("--scale-label", required=True)
    p.add_argument("--mongo-db", required=True)
    p.add_argument("--mongo-host", default="127.0.0.1")
    p.add_argument("--mongo-port", type=int, default=27018)
    p.add_argument("--mongo-username", default=None)
    p.add_argument("--mongo-password", default=None)
    p.add_argument("--mongo-auth-source", default="admin")
    p.add_argument("--query-name", nargs="*", default=None)
    p.add_argument("--run-phase", default="hot", choices=["cold", "hot"])
    p.add_argument("--repetitions", type=int, default=1)
    p.add_argument("--explain-verbosity", default="executionStats", choices=["queryPlanner", "executionStats", "allPlansExecution"])
    p.add_argument("--save-raw-explain", action="store_true")
    p.add_argument("--out-dir", default="DBSR_implementation/results/fiben/query_plan")
    return p


def main() -> None:
    args = build_arg_parser().parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = connect_mongo(args)
    db = client[args.mongo_db]
    params = read_json(Path(args.parameter_probe))

    selected_queries = args.query_name or QUERY_NAMES

    component_rows: List[Dict[str, Any]] = []

    for query_name in selected_queries:
        if query_name not in QUERY_NAMES:
            raise SystemExit(f"Unknown query name: {query_name}")

        for rep in range(1, args.repetitions + 1):
            run_params = bench.params_for_repetition(params, query_name, rep)

            if query_name == "Q10_CreateAccountHoldingAndBuyTransaction":
                component_rows.append(skipped_q10_row(args, rep))
                continue

            builder = COMPONENT_BUILDERS[query_name]
            rows = builder(db, args, run_params, rep)
            component_rows.extend(rows)

            print(
                f"{args.scale_label} {query_name} rep={rep} "
                f"components={len(rows)} status="
                f"{','.join(sorted({str(r['execution_status']) for r in rows}))}"
            )

    summary = aggregate_summary(component_rows)
    compact = compact_candidates(summary)
    overview = overview_rows(compact)
    status = status_rows(compact)

    prefix = f"dbsr_fiben_query_plan_{args.scale_label}"

    components_path = out_dir / f"{prefix}_components_all.csv"
    summary_path = out_dir / f"{prefix}_summary_all.csv"
    compact_path = out_dir / f"{prefix}_compact_candidates.csv"
    overview_path = out_dir / f"{prefix}_query_scale_overview.csv"
    status_path = out_dir / f"{prefix}_query_scale_status.csv"
    manifest_path = out_dir / f"{prefix}_manifest.json"

    write_csv(components_path, component_rows, COMPONENT_COLUMNS)
    write_csv(summary_path, summary, SUMMARY_COLUMNS)
    write_csv(compact_path, compact)
    write_csv(overview_path, overview)
    write_csv(status_path, status)

    manifest = {
        "baseline": "DBSR",
        "dataset": "FIBEN",
        "scale_label": args.scale_label,
        "mongo_database": args.mongo_db,
        "parameter_probe": args.parameter_probe,
        "queries": selected_queries,
        "run_phase": args.run_phase,
        "repetitions": args.repetitions,
        "explain_verbosity": args.explain_verbosity,
        "components": str(components_path),
        "summary": str(summary_path),
        "compact_candidates": str(compact_path),
        "query_scale_overview": str(overview_path),
        "query_scale_status": str(status_path),
        "failed_components": sum(1 for r in component_rows if r.get("execution_status") == "failed"),
        "skipped_components": sum(1 for r in component_rows if r.get("execution_status") == "skipped"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print("DBSR FIBEN query-plan completed.")
    print(f"Wrote {components_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {compact_path}")
    print(f"Wrote {overview_path}")
    print(f"Wrote {status_path}")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
