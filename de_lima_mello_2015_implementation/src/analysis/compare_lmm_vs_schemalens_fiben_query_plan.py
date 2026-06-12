"""
Compare Lima & Mello 2015 FIBEN query-plan evidence against SchemaLens FIBEN query-plan evidence.

Inputs:
- Lima & Mello query-plan summary:
  de_lima_mello_2015_implementation/results/fiben/query_plan/sf1/lmm_fiben_sf1_source_full/lmm_fiben_query_plan_summary_results.csv

- SchemaLens best-by-estimated-bytes query-plan summary:
  analysis/generated/query_plan/fiben/fiben_query_plan_best_by_estimated_bytes.csv

Outputs:
- joined comparison table;
- method-level summary;
- query-level interpretation draft.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


QUERY_NAME_MAP = {
    "Q1": "Q1_CompanyProfile",
    "Q2": "Q2_CompanyWithIndustryCountryAndListedSecurities",
    "Q3": "Q3_SecuritiesHeldInEachFinancialServiceAccount",
    "Q4": "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity",
    "Q5": "Q5_ReportsAndMetricDataOfCompany",
    "Q6": "Q6_TechUSListedSecuritiesWithHighLastTradedValue",
    "Q7": "Q7_PersonsWhoBoughtMoreIBMThanSold",
    "Q8": "Q8_IBMTransactionsBelowAverageSellingPrice",
    "Q9": "Q9_PersonsWhoBoughtAndSoldSameStock",
}


def first_existing(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cols = set(df.columns)
    for c in candidates:
        if c in cols:
            return c
    return None


def normalize_query_id(value: Any) -> Optional[str]:
    if value is None or pd.isna(value):
        return None

    text = str(value)

    # Prefer Q1..Q10 pattern.
    m = re.search(r"\bQ(?:G)?(\d+)\b", text, flags=re.IGNORECASE)
    if m:
        return f"Q{int(m.group(1))}"

    # Also handle names starting with Q1_...
    m = re.search(r"Q(\d+)_", text, flags=re.IGNORECASE)
    if m:
        return f"Q{int(m.group(1))}"

    return text


def bool_value(value: Any) -> Optional[bool]:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def numeric(df: pd.DataFrame, col: Optional[str]) -> pd.Series:
    if col is None:
        return pd.Series([pd.NA] * len(df))
    return pd.to_numeric(df[col], errors="coerce")


def normalize_lmm(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["query_id"] = df["query_id"].map(normalize_query_id)
    out["query_name"] = df.get("query_name", out["query_id"].map(QUERY_NAME_MAP))
    out["method"] = "LimaMello2015"
    out["selected_config"] = "lmm_materialized_design"
    out["root_or_path"] = df.get("root_collection", pd.NA)
    out["status"] = df.get("status", pd.NA)

    out["execution_time_ms"] = numeric(df, "execution_time_ms_max")
    out["docs_examined"] = numeric(df, "total_docs_examined_accumulated")
    out["keys_examined"] = numeric(df, "total_keys_examined_accumulated")

    for flag in ["has_ixscan", "has_collscan", "has_lookup", "has_group", "has_unwind"]:
        if flag in df.columns:
            out[flag] = df[flag].map(bool_value)
        else:
            out[flag] = pd.NA

    out["raw_source"] = "lmm_fiben_query_plan_summary_results.csv"
    return out


def normalize_schemalens(df: pd.DataFrame, scale: str) -> pd.DataFrame:
    out = pd.DataFrame()

    query_col = first_existing(df, [
        "query_id",
        "query",
        "query_name",
        "workload_query",
        "operation_id",
        "operation_name",
    ])
    if query_col is None:
        raise RuntimeError(
            "Could not detect SchemaLens query column. Available columns: "
            + ", ".join(df.columns)
        )

    scale_col = first_existing(df, ["scale_label", "scale", "scale_factor", "sf"])
    sdf = df.copy()
    if scale_col is not None:
        sdf = sdf[sdf[scale_col].astype(str).str.lower().eq(scale.lower())].copy()

    out["query_id"] = sdf[query_col].map(normalize_query_id)
    out["query_name"] = out["query_id"].map(QUERY_NAME_MAP)
    out["method"] = "SchemaLens"

    config_col = first_existing(sdf, [
        "best_candidate_id",
        "best_g_class",
        "best_group",
        "best_design_pattern",
        "candidate_id",
        "candidate",
        "config",
        "config_id",
        "configuration",
        "schema_config",
        "best_config",
        "physical_config",
        "group_id",
        "family",
    ])
    root_col = first_existing(sdf, [
        "best_collections_touched",
        "root_collection",
        "collection",
        "main_collection",
        "physical_path",
        "path",
        "root_or_path",
        "mongo_collection",
    ])

    out["selected_config"] = sdf[config_col].astype(str) if config_col else "schemalens_best"
    out["root_or_path"] = sdf[root_col].astype(str) if root_col else pd.NA

    status_col = first_existing(sdf, ["status", "execution_status"])
    out["status"] = sdf[status_col].astype(str) if status_col else "completed"

    exec_col = first_existing(sdf, [
        "execution_time_ms_max",
        "execution_time_ms",
        "executionStats_executionTimeMillis",
        "execution_time_millis",
        "execution_time_ms_estimate",
    ])
    docs_col = first_existing(sdf, [
        "best_docs_examined",
        "total_docs_examined_accumulated",
        "total_docs_examined",
        "docs_examined",
        "totalDocsExamined",
        "documents_examined",
    ])
    keys_col = first_existing(sdf, [
        "best_keys_examined",
        "total_keys_examined_accumulated",
        "total_keys_examined",
        "keys_examined",
        "totalKeysExamined",
    ])

    out["execution_time_ms"] = numeric(sdf, exec_col)
    out["docs_examined"] = numeric(sdf, docs_col)
    out["keys_examined"] = numeric(sdf, keys_col)

    flag_map = {
        "has_ixscan": ["has_ixscan", "IXSCAN", "uses_ixscan"],
        "has_collscan": ["best_has_COLLSCAN", "has_collscan", "COLLSCAN", "uses_collscan"],
        "has_lookup": ["has_lookup", "LOOKUP", "uses_lookup"],
        "has_group": ["best_has_GROUP", "has_group", "GROUP", "uses_group"],
        "has_unwind": ["has_unwind", "UNWIND", "uses_unwind"],
    }

    for target, candidates in flag_map.items():
        c = first_existing(sdf, candidates)
        out[target] = sdf[c].map(bool_value) if c else pd.NA

    out["raw_source"] = "fiben_query_plan_best_by_estimated_bytes.csv"

    # Keep one SchemaLens row per query. If the file has multiple rows per query,
    # prefer smallest docs_examined, then smallest keys_examined, then smallest execution time.
    out = out.sort_values(
        ["query_id", "docs_examined", "keys_examined", "execution_time_ms"],
        na_position="last",
    )
    out = out.drop_duplicates(subset=["query_id"], keep="first")

    return out


def ratio(a: Any, b: Any) -> Optional[float]:
    try:
        if pd.isna(a) or pd.isna(b) or float(b) == 0:
            return None
        return float(a) / float(b)
    except Exception:
        return None


def interpret_row(row: pd.Series) -> str:
    q = row["query_id"]

    l_docs = row.get("lmm_docs_examined")
    s_docs = row.get("schemalens_docs_examined")
    l_coll = row.get("lmm_has_collscan")
    s_coll = row.get("schemalens_has_collscan")
    l_lookup = row.get("lmm_has_lookup")
    s_lookup = row.get("schemalens_has_lookup")

    parts = []

    if pd.notna(l_docs) and pd.notna(s_docs):
        if l_docs > s_docs:
            parts.append("SchemaLens examines fewer documents")
        elif l_docs < s_docs:
            parts.append("Lima & Mello examines fewer documents")
        else:
            parts.append("both examine the same number of documents")

    if l_coll is True and s_coll is not True:
        parts.append("Lima & Mello uses COLLSCAN while SchemaLens avoids it")
    elif s_coll is True and l_coll is not True:
        parts.append("SchemaLens uses COLLSCAN while Lima & Mello avoids it")
    elif l_coll is True and s_coll is True:
        parts.append("both use COLLSCAN")

    if l_lookup is True and s_lookup is not True:
        parts.append("Lima & Mello requires lookup")
    elif s_lookup is True and l_lookup is not True:
        parts.append("SchemaLens requires lookup")
    elif l_lookup is True and s_lookup is True:
        parts.append("both require lookup")

    if not parts:
        return f"{q}: plans are similar under the collected metrics."

    return f"{q}: " + "; ".join(parts) + "."


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lmm",
        default="de_lima_mello_2015_implementation/results/fiben/query_plan/sf1/lmm_fiben_sf1_source_full/lmm_fiben_query_plan_summary_results.csv",
    )
    parser.add_argument(
        "--schemalens",
        default="analysis/generated/query_plan/fiben/fiben_query_plan_best_by_estimated_bytes.csv",
    )
    parser.add_argument(
        "--scale",
        default="sf1",
    )
    parser.add_argument(
        "--output-dir",
        default="de_lima_mello_2015_implementation/results/fiben/reports",
    )
    args = parser.parse_args()

    lmm_path = Path(args.lmm)
    schemalens_path = Path(args.schemalens)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lmm_raw = pd.read_csv(lmm_path)
    schemalens_raw = pd.read_csv(schemalens_path)

    lmm = normalize_lmm(lmm_raw)
    schemalens = normalize_schemalens(schemalens_raw, args.scale)

    joined = lmm.merge(
        schemalens,
        on="query_id",
        how="outer",
        suffixes=("_lmm", "_schemalens"),
    )

    joined = joined.rename(columns={
        "query_name_lmm": "lmm_query_name",
        "query_name_schemalens": "schemalens_query_name",
        "method_lmm": "lmm_method",
        "method_schemalens": "schemalens_method",
        "selected_config_lmm": "lmm_selected_config",
        "selected_config_schemalens": "schemalens_selected_config",
        "root_or_path_lmm": "lmm_root_or_path",
        "root_or_path_schemalens": "schemalens_root_or_path",
        "status_lmm": "lmm_status",
        "status_schemalens": "schemalens_status",
        "execution_time_ms_lmm": "lmm_execution_time_ms",
        "execution_time_ms_schemalens": "schemalens_execution_time_ms",
        "docs_examined_lmm": "lmm_docs_examined",
        "docs_examined_schemalens": "schemalens_docs_examined",
        "keys_examined_lmm": "lmm_keys_examined",
        "keys_examined_schemalens": "schemalens_keys_examined",
        "has_ixscan_lmm": "lmm_has_ixscan",
        "has_ixscan_schemalens": "schemalens_has_ixscan",
        "has_collscan_lmm": "lmm_has_collscan",
        "has_collscan_schemalens": "schemalens_has_collscan",
        "has_lookup_lmm": "lmm_has_lookup",
        "has_lookup_schemalens": "schemalens_has_lookup",
        "has_group_lmm": "lmm_has_group",
        "has_group_schemalens": "schemalens_has_group",
        "has_unwind_lmm": "lmm_has_unwind",
        "has_unwind_schemalens": "schemalens_has_unwind",
    })

    joined["query_name"] = joined["query_id"].map(QUERY_NAME_MAP)
    joined["docs_examined_ratio_lmm_over_schemalens"] = joined.apply(
        lambda r: ratio(r.get("lmm_docs_examined"), r.get("schemalens_docs_examined")),
        axis=1,
    )
    joined["keys_examined_ratio_lmm_over_schemalens"] = joined.apply(
        lambda r: ratio(r.get("lmm_keys_examined"), r.get("schemalens_keys_examined")),
        axis=1,
    )
    joined["execution_time_ratio_lmm_over_schemalens"] = joined.apply(
        lambda r: ratio(r.get("lmm_execution_time_ms"), r.get("schemalens_execution_time_ms")),
        axis=1,
    )

    joined["interpretation"] = joined.apply(interpret_row, axis=1)

    ordered_cols = [
        "query_id",
        "query_name",
        "lmm_status",
        "schemalens_status",
        "lmm_selected_config",
        "schemalens_selected_config",
        "lmm_root_or_path",
        "schemalens_root_or_path",
        "lmm_execution_time_ms",
        "schemalens_execution_time_ms",
        "execution_time_ratio_lmm_over_schemalens",
        "lmm_docs_examined",
        "schemalens_docs_examined",
        "docs_examined_ratio_lmm_over_schemalens",
        "lmm_keys_examined",
        "schemalens_keys_examined",
        "keys_examined_ratio_lmm_over_schemalens",
        "lmm_has_ixscan",
        "schemalens_has_ixscan",
        "lmm_has_collscan",
        "schemalens_has_collscan",
        "lmm_has_lookup",
        "schemalens_has_lookup",
        "lmm_has_group",
        "schemalens_has_group",
        "lmm_has_unwind",
        "schemalens_has_unwind",
        "interpretation",
    ]

    for col in ordered_cols:
        if col not in joined.columns:
            joined[col] = pd.NA

    joined = joined[ordered_cols].sort_values("query_id")

    comparison_csv = output_dir / f"lmm_vs_schemalens_fiben_query_plan_comparison_{args.scale}.csv"
    interpretation_md = output_dir / f"lmm_vs_schemalens_fiben_query_plan_interpretation_{args.scale}.md"
    method_summary_csv = output_dir / f"lmm_vs_schemalens_fiben_query_plan_method_summary_{args.scale}.csv"

    joined.to_csv(comparison_csv, index=False)

    method_rows = []
    for prefix, label in [("lmm", "LimaMello2015"), ("schemalens", "SchemaLens")]:
        method_rows.append({
            "method": label,
            "n_queries": int(joined[f"{prefix}_status"].notna().sum()),
            "n_completed": int(joined[f"{prefix}_status"].astype(str).str.contains("completed", case=False, na=False).sum()),
            "total_docs_examined": joined[f"{prefix}_docs_examined"].sum(skipna=True),
            "total_keys_examined": joined[f"{prefix}_keys_examined"].sum(skipna=True),
            "n_collscan": int(joined[f"{prefix}_has_collscan"].fillna(False).astype(bool).sum()),
            "n_ixscan": int(joined[f"{prefix}_has_ixscan"].fillna(False).astype(bool).sum()),
            "n_lookup": int(joined[f"{prefix}_has_lookup"].fillna(False).astype(bool).sum()),
            "n_group": int(joined[f"{prefix}_has_group"].fillna(False).astype(bool).sum()),
            "n_unwind": int(joined[f"{prefix}_has_unwind"].fillna(False).astype(bool).sum()),
        })

    method_summary = pd.DataFrame(method_rows)
    method_summary.to_csv(method_summary_csv, index=False)

    lines = []
    lines.append("# Lima & Mello 2015 vs SchemaLens: FIBEN query-plan comparison")
    lines.append("")
    lines.append(f"Scale: `{args.scale}`")
    lines.append("")
    lines.append("## Method-level summary")
    lines.append("")
    lines.append(method_summary.to_markdown(index=False))
    lines.append("")
    lines.append("## Query-level interpretation")
    lines.append("")
    for _, row in joined.iterrows():
        lines.append(f"- **{row['query_id']}**: {row['interpretation']}")

    interpretation_md.write_text("\n".join(lines), encoding="utf-8")

    print("Wrote:")
    print(" -", comparison_csv)
    print(" -", method_summary_csv)
    print(" -", interpretation_md)
    print()
    print("=== method summary ===")
    print(method_summary.to_string(index=False))
    print()
    print("=== comparison preview ===")
    preview_cols = [
        "query_id",
        "lmm_docs_examined",
        "schemalens_docs_examined",
        "docs_examined_ratio_lmm_over_schemalens",
        "lmm_has_collscan",
        "schemalens_has_collscan",
        "interpretation",
    ]
    print(joined[preview_cols].to_string(index=False))


if __name__ == "__main__":
    main()
