from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd


QUERY_NAME_MAP = {
    "Q1": "Q1_CompanyProfileIBM",
    "Q2": "Q2_CompanyWithIndustryCountryAndListedSecurities",
    "Q3": "Q3_SecuritiesHeldInEachFinancialServiceAccount",
    "Q4": "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity",
    "Q5": "Q5_ReportsAndMetricDataOfCompany",
    "Q6": "Q6_TechUSListedSecuritiesWithHighLastTradedValue",
    "Q7": "Q7_PersonsWhoBoughtMoreIBMThanSold",
    "Q8": "Q8_IBMTransactionsBelowAverageSellingPrice",
    "Q9": "Q9_PersonsWhoBoughtAndSoldSameStock",
}


def normalize_query_id(value: Any) -> Optional[str]:
    if value is None or pd.isna(value):
        return None
    text = str(value)
    m = re.search(r"\bQ(\d+)\b", text, flags=re.IGNORECASE)
    if m:
        return f"Q{int(m.group(1))}"
    m = re.search(r"Q(\d+)_", text, flags=re.IGNORECASE)
    if m:
        return f"Q{int(m.group(1))}"
    return text


def to_bool(value: Any) -> Optional[bool]:
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


def bool_any(series: pd.Series) -> bool:
    return bool(series.map(to_bool).fillna(False).any())


def contains_unwind(series: pd.Series) -> bool:
    text = " ".join(series.fillna("").astype(str).tolist()).lower()
    return "$unwind" in text or "unwind" in text


def safe_num(value: Any) -> Optional[float]:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def ratio(a: Any, b: Any) -> Optional[float]:
    aa = safe_num(a)
    bb = safe_num(b)
    if aa is None or bb is None or bb == 0:
        return None
    return aa / bb


def normalize_lmm(lmm: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["query_id"] = lmm["query_id"].map(normalize_query_id)
    out["query_name"] = out["query_id"].map(QUERY_NAME_MAP)
    out["lmm_status"] = lmm["status"]
    out["lmm_root_or_path"] = lmm["root_collection"]
    out["lmm_selected_config"] = "lmm_materialized_design"
    out["lmm_execution_time_ms"] = pd.to_numeric(lmm["execution_time_ms_max"], errors="coerce")
    out["lmm_docs_examined"] = pd.to_numeric(lmm["total_docs_examined_accumulated"], errors="coerce")
    out["lmm_keys_examined"] = pd.to_numeric(lmm["total_keys_examined_accumulated"], errors="coerce")
    out["lmm_has_ixscan"] = lmm["has_ixscan"].map(to_bool)
    out["lmm_has_collscan"] = lmm["has_collscan"].map(to_bool)
    out["lmm_has_lookup"] = lmm["has_lookup"].map(to_bool)
    out["lmm_has_group"] = lmm["has_group"].map(to_bool)
    out["lmm_has_unwind"] = lmm["has_unwind"].map(to_bool)
    return out


def build_schemalens_best(best: pd.DataFrame, compact: pd.DataFrame, components: pd.DataFrame, scale: str) -> pd.DataFrame:
    best_sf = best[best["scale_label"].astype(str).eq(scale)].copy()
    compact_sf = compact[compact["scale_label"].astype(str).eq(scale)].copy()
    comp_sf = components[components["scale_label"].astype(str).eq(scale)].copy()

    # Q10 is insert/update, not part of read-query comparison.
    best_sf = best_sf[~best_sf["query_name"].astype(str).str.startswith("Q10_")].copy()

    rows = []

    for _, brow in best_sf.iterrows():
        qname = str(brow["query_name"])
        qid = normalize_query_id(qname)
        cid = str(brow["best_candidate_id"])

        crows = compact_sf[compact_sf["candidate_id"].astype(str).eq(cid)].copy()
        comp_rows = comp_sf[comp_sf["candidate_id"].astype(str).eq(cid)].copy()

        if len(crows) > 0:
            crow = crows.iloc[0]
            docs = crow.get("sum_total_docs_examined")
            keys = crow.get("sum_total_keys_examined")
            has_ixscan = to_bool(crow.get("has_IXSCAN"))
            has_collscan = to_bool(crow.get("has_COLLSCAN"))
            has_group = to_bool(crow.get("has_GROUP"))
            collections = crow.get("collections_touched")
            status = crow.get("execution_status")
        else:
            docs = brow.get("best_docs_examined")
            keys = brow.get("best_keys_examined")
            has_ixscan = None
            has_collscan = to_bool(brow.get("best_has_COLLSCAN"))
            has_group = to_bool(brow.get("best_has_GROUP"))
            collections = brow.get("best_collections_touched")
            status = "unknown_compact_missing"

        if len(comp_rows) > 0:
            has_lookup = bool_any(comp_rows["has_LOOKUP"]) if "has_LOOKUP" in comp_rows.columns else None
            has_fetch = bool_any(comp_rows["has_FETCH"]) if "has_FETCH" in comp_rows.columns else None
            has_sort = bool_any(comp_rows["has_SORT"]) if "has_SORT" in comp_rows.columns else None
            has_unwind = contains_unwind(comp_rows["pipeline_json"]) if "pipeline_json" in comp_rows.columns else None
            used_disk = bool_any(comp_rows["used_disk"]) if "used_disk" in comp_rows.columns else None
            max_exec_ms = pd.to_numeric(comp_rows.get("execution_time_millis"), errors="coerce").max()
            component_names = ";".join(comp_rows.get("component_name", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
        else:
            has_lookup = None
            has_fetch = None
            has_sort = None
            has_unwind = None
            used_disk = None
            max_exec_ms = None
            component_names = ""

        rows.append({
            "query_id": qid,
            "query_name": qname,
            "schemalens_status": status,
            "schemalens_selected_config": cid,
            "schemalens_g_class": brow.get("best_g_class"),
            "schemalens_group": brow.get("best_group"),
            "schemalens_design_pattern": brow.get("best_design_pattern"),
            "schemalens_root_or_path": collections,
            "schemalens_n_components": brow.get("best_n_components"),
            "schemalens_execution_time_ms": max_exec_ms,
            "schemalens_docs_examined": pd.to_numeric(pd.Series([docs]), errors="coerce").iloc[0],
            "schemalens_keys_examined": pd.to_numeric(pd.Series([keys]), errors="coerce").iloc[0],
            "schemalens_estimated_docs_examined_bytes": brow.get("best_estimated_docs_examined_bytes"),
            "schemalens_has_ixscan": has_ixscan,
            "schemalens_has_collscan": has_collscan,
            "schemalens_has_lookup": has_lookup,
            "schemalens_has_group": has_group,
            "schemalens_has_unwind": has_unwind,
            "schemalens_has_fetch": has_fetch,
            "schemalens_has_sort": has_sort,
            "schemalens_used_disk": used_disk,
            "schemalens_component_names": component_names,
        })

    return pd.DataFrame(rows)


def interpret(row: pd.Series) -> str:
    parts = []

    l_docs = row.get("lmm_docs_examined")
    s_docs = row.get("schemalens_docs_examined")

    if pd.notna(l_docs) and pd.notna(s_docs):
        if l_docs < s_docs:
            parts.append("Lima & Mello examines fewer documents")
        elif l_docs > s_docs:
            parts.append("SchemaLens examines fewer documents")
        else:
            parts.append("both examine the same number of documents")

    l_coll = row.get("lmm_has_collscan")
    s_coll = row.get("schemalens_has_collscan")
    if l_coll is True and s_coll is not True:
        parts.append("Lima & Mello uses COLLSCAN while SchemaLens avoids it")
    elif s_coll is True and l_coll is not True:
        parts.append("SchemaLens uses COLLSCAN while Lima & Mello avoids it")
    elif s_coll is True and l_coll is True:
        parts.append("both use COLLSCAN")
    elif s_coll is False and l_coll is False:
        parts.append("both avoid COLLSCAN")

    l_lookup = row.get("lmm_has_lookup")
    s_lookup = row.get("schemalens_has_lookup")
    if l_lookup is True and s_lookup is not True:
        parts.append("Lima & Mello uses LOOKUP while SchemaLens avoids it")
    elif s_lookup is True and l_lookup is not True:
        parts.append("SchemaLens uses LOOKUP while Lima & Mello avoids it")
    elif s_lookup is True and l_lookup is True:
        parts.append("both use LOOKUP")

    if not parts:
        return "evidence is incomplete or plans are similar."

    return "; ".join(parts) + "."


def method_summary(joined: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for prefix, method in [("lmm", "LimaMello2015"), ("schemalens", "SchemaLens")]:
        rows.append({
            "method": method,
            "n_queries": int(joined[f"{prefix}_docs_examined"].notna().sum()),
            "total_docs_examined": joined[f"{prefix}_docs_examined"].sum(skipna=True),
            "total_keys_examined": joined[f"{prefix}_keys_examined"].sum(skipna=True),
            "n_ixscan": int(joined[f"{prefix}_has_ixscan"].fillna(False).astype(bool).sum()),
            "n_collscan": int(joined[f"{prefix}_has_collscan"].fillna(False).astype(bool).sum()),
            "n_lookup": int(joined[f"{prefix}_has_lookup"].fillna(False).astype(bool).sum()),
            "n_group": int(joined[f"{prefix}_has_group"].fillna(False).astype(bool).sum()),
            "n_unwind": int(joined[f"{prefix}_has_unwind"].fillna(False).astype(bool).sum()),
        })
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="sf1")
    ap.add_argument("--lmm", default="de_lima_mello_2015_implementation/results/fiben/query_plan/sf1/lmm_fiben_sf1_source_full/lmm_fiben_query_plan_summary_results.csv")
    ap.add_argument("--schemalens-dir", default="de_lima_mello_2015_implementation/generated/fiben/schemalens_query_plan_full")
    ap.add_argument("--output-dir", default="de_lima_mello_2015_implementation/results/fiben/reports")
    args = ap.parse_args()

    schemalens_dir = Path(args.schemalens_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lmm = pd.read_csv(args.lmm)
    best = pd.read_csv(schemalens_dir / "fiben_query_plan_best_by_estimated_bytes.csv")
    compact = pd.read_csv(schemalens_dir / "fiben_query_plan_compact_candidates.csv")
    components = pd.read_csv(schemalens_dir / "fiben_query_plan_components_all.csv")

    lmm_norm = normalize_lmm(lmm)
    schema_norm = build_schemalens_best(best, compact, components, args.scale)

    joined = lmm_norm.merge(schema_norm, on=["query_id"], how="outer", suffixes=("", "_schema"))
    joined["query_name"] = joined["query_id"].map(QUERY_NAME_MAP)

    joined["docs_ratio_lmm_over_schemalens"] = joined.apply(
        lambda r: ratio(r.get("lmm_docs_examined"), r.get("schemalens_docs_examined")),
        axis=1,
    )
    joined["keys_ratio_lmm_over_schemalens"] = joined.apply(
        lambda r: ratio(r.get("lmm_keys_examined"), r.get("schemalens_keys_examined")),
        axis=1,
    )
    joined["estimated_bytes_ratio_lmm_over_schemalens"] = None
    joined["interpretation"] = joined.apply(interpret, axis=1)

    ordered = [
        "query_id",
        "query_name",
        "lmm_status",
        "schemalens_status",
        "lmm_selected_config",
        "schemalens_selected_config",
        "schemalens_g_class",
        "schemalens_group",
        "schemalens_design_pattern",
        "lmm_root_or_path",
        "schemalens_root_or_path",
        "schemalens_n_components",
        "lmm_execution_time_ms",
        "schemalens_execution_time_ms",
        "lmm_docs_examined",
        "schemalens_docs_examined",
        "docs_ratio_lmm_over_schemalens",
        "lmm_keys_examined",
        "schemalens_keys_examined",
        "keys_ratio_lmm_over_schemalens",
        "schemalens_estimated_docs_examined_bytes",
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
        "schemalens_has_fetch",
        "schemalens_has_sort",
        "schemalens_used_disk",
        "schemalens_component_names",
        "interpretation",
    ]

    for c in ordered:
        if c not in joined.columns:
            joined[c] = pd.NA

    joined = joined[ordered].sort_values("query_id")

    summary = method_summary(joined)

    comparison_csv = output_dir / f"lmm_vs_schemalens_fiben_query_plan_full_comparison_{args.scale}.csv"
    summary_csv = output_dir / f"lmm_vs_schemalens_fiben_query_plan_full_summary_{args.scale}.csv"
    report_md = output_dir / f"lmm_vs_schemalens_fiben_query_plan_full_report_{args.scale}.md"

    joined.to_csv(comparison_csv, index=False)
    summary.to_csv(summary_csv, index=False)

    lines = []
    lines.append("# Lima & Mello 2015 vs SchemaLens FIBEN query-plan comparison")
    lines.append("")
    lines.append(f"Scale: `{args.scale}`")
    lines.append("")
    lines.append("## Method summary")
    lines.append("")
    lines.append(summary.to_markdown(index=False))
    lines.append("")
    lines.append("## Query interpretation")
    lines.append("")
    for _, row in joined.iterrows():
        lines.append(f"- **{row['query_id']}**: {row['interpretation']}")

    report_md.write_text("\n".join(lines), encoding="utf-8")

    print("Wrote:")
    print(" -", comparison_csv)
    print(" -", summary_csv)
    print(" -", report_md)
    print()
    print("=== summary ===")
    print(summary.to_string(index=False))
    print()
    print("=== comparison preview ===")
    print(joined[
        [
            "query_id",
            "lmm_docs_examined",
            "schemalens_docs_examined",
            "docs_ratio_lmm_over_schemalens",
            "lmm_has_ixscan",
            "schemalens_has_ixscan",
            "lmm_has_collscan",
            "schemalens_has_collscan",
            "lmm_has_lookup",
            "schemalens_has_lookup",
            "lmm_has_unwind",
            "schemalens_has_unwind",
            "interpretation",
        ]
    ].to_string(index=False))


if __name__ == "__main__":
    main()
