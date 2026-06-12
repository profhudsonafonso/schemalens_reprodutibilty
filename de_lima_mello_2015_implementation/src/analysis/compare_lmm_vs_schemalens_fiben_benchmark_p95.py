from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Optional

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


def first_existing(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def numeric_col(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
    c = first_existing(df, candidates)
    if c is None:
        return pd.Series([pd.NA] * len(df))
    return pd.to_numeric(df[c], errors="coerce")


def text_col(df: pd.DataFrame, candidates: list[str], default: str = "") -> pd.Series:
    c = first_existing(df, candidates)
    if c is None:
        return pd.Series([default] * len(df))
    return df[c].astype(str)


def ratio(a: Any, b: Any) -> Optional[float]:
    try:
        if pd.isna(a) or pd.isna(b) or float(b) == 0:
            return None
        return float(a) / float(b)
    except Exception:
        return None


def normalize_lmm(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["query_id"] = df["query_id"].map(normalize_query_id)
    out["query_name"] = out["query_id"].map(QUERY_NAME_MAP)
    out["run_phase"] = df["run_phase"].astype(str)
    out["lmm_p95_ms"] = pd.to_numeric(df["p95_ms"], errors="coerce")
    out["lmm_mean_ms"] = pd.to_numeric(df["mean_ms"], errors="coerce")
    out["lmm_median_ms"] = pd.to_numeric(df["median_ms"], errors="coerce")
    out["lmm_max_ms"] = pd.to_numeric(df["max_ms"], errors="coerce")
    out["lmm_n_completed"] = pd.to_numeric(df["n_completed"], errors="coerce")
    out["lmm_mean_n_returned"] = pd.to_numeric(df["mean_n_returned"], errors="coerce")
    return out


def normalize_schemalens(df: pd.DataFrame) -> pd.DataFrame:
    q_col = first_existing(df, ["query_id", "query_name", "query", "operation_id", "operation_name"])
    if q_col is None:
        raise RuntimeError("Could not detect SchemaLens query column. Columns: " + ", ".join(df.columns))

    phase_col = first_existing(df, ["run_phase", "phase", "benchmark_phase"])

    sdf = df.copy()
    sdf["query_id_norm"] = sdf[q_col].map(normalize_query_id)

    if phase_col is not None:
        sdf["run_phase_norm"] = sdf[phase_col].astype(str)
    else:
        sdf["run_phase_norm"] = "hot"

    # Keep only read queries Q1--Q9.
    sdf = sdf[sdf["query_id_norm"].isin([f"Q{i}" for i in range(1, 10)])].copy()

    # Prefer hot phase if available.
    p95 = numeric_col(sdf, [
        "p95_ms", "p95", "p95_latency_ms", "latency_p95_ms",
        "p95_hot_ms", "best_p95", "best_p95_ms"
    ])
    mean = numeric_col(sdf, ["mean_ms", "avg_ms", "average_ms", "mean_latency_ms"])
    median = numeric_col(sdf, ["median_ms", "p50_ms", "median_latency_ms"])
    maxv = numeric_col(sdf, ["max_ms", "max_latency_ms"])
    n_completed = numeric_col(sdf, ["n_completed", "successful_runs", "n_success", "completed_runs"])

    sdf["_p95"] = p95
    sdf["_mean"] = mean
    sdf["_median"] = median
    sdf["_max"] = maxv
    sdf["_n_completed"] = n_completed

    sdf["_candidate_id"] = text_col(sdf, ["candidate_id", "config_id", "configuration_id", "best_candidate_id"], "schemalens")
    sdf["_g_class"] = text_col(sdf, ["g_class", "best_g_class"], "")
    sdf["_group"] = text_col(sdf, ["final_benchmark_group", "benchmark_group", "best_group", "group"], "")
    sdf["_design_pattern"] = text_col(sdf, ["design_pattern", "best_design_pattern"], "")

    # If there are multiple SchemaLens candidates for the same query and phase,
    # pick the lowest p95. This gives the best observed p95 baseline.
    sdf = sdf.sort_values(["query_id_norm", "run_phase_norm", "_p95"], na_position="last")
    sdf = sdf.drop_duplicates(subset=["query_id_norm", "run_phase_norm"], keep="first")

    out = pd.DataFrame()
    out["query_id"] = sdf["query_id_norm"]
    out["query_name"] = out["query_id"].map(QUERY_NAME_MAP)
    out["run_phase"] = sdf["run_phase_norm"]
    out["schemalens_p95_ms"] = sdf["_p95"]
    out["schemalens_mean_ms"] = sdf["_mean"]
    out["schemalens_median_ms"] = sdf["_median"]
    out["schemalens_max_ms"] = sdf["_max"]
    out["schemalens_n_completed"] = sdf["_n_completed"]
    out["schemalens_candidate_id"] = sdf["_candidate_id"]
    out["schemalens_g_class"] = sdf["_g_class"]
    out["schemalens_group"] = sdf["_group"]
    out["schemalens_design_pattern"] = sdf["_design_pattern"]
    return out


def interpret(row: pd.Series) -> str:
    q = row["query_id"]
    l = row.get("lmm_p95_ms")
    s = row.get("schemalens_p95_ms")

    if pd.isna(l) or pd.isna(s):
        return f"{q}: p95 evidence is incomplete."

    if l < s:
        return f"{q}: Lima & Mello has lower p95 latency."
    if l > s:
        return f"{q}: SchemaLens has lower p95 latency."
    return f"{q}: both have the same p95 latency."


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--lmm",
        default="de_lima_mello_2015_implementation/results/fiben/benchmark/sf1/lmm_fiben_sf1_source_full/lmm_fiben_benchmark_aggregate_results.csv",
    )
    ap.add_argument(
        "--schemalens",
        default="de_lima_mello_2015_implementation/generated/fiben/schemalens_benchmark/benchmark_aggregate_results_fiben_sf1.csv",
    )
    ap.add_argument(
        "--output-dir",
        default="de_lima_mello_2015_implementation/results/fiben/reports",
    )
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    lmm = normalize_lmm(pd.read_csv(args.lmm))
    schema = normalize_schemalens(pd.read_csv(args.schemalens))

    joined = lmm.merge(schema, on=["query_id", "run_phase"], how="outer", suffixes=("", "_schema"))
    joined["query_name"] = joined["query_id"].map(QUERY_NAME_MAP)
    joined["p95_ratio_lmm_over_schemalens"] = joined.apply(
        lambda r: ratio(r.get("lmm_p95_ms"), r.get("schemalens_p95_ms")),
        axis=1,
    )
    joined["winner_by_p95"] = joined.apply(
        lambda r: "LimaMello2015"
        if pd.notna(r.get("lmm_p95_ms")) and pd.notna(r.get("schemalens_p95_ms")) and r.get("lmm_p95_ms") < r.get("schemalens_p95_ms")
        else "SchemaLens"
        if pd.notna(r.get("lmm_p95_ms")) and pd.notna(r.get("schemalens_p95_ms")) and r.get("schemalens_p95_ms") < r.get("lmm_p95_ms")
        else "tie_or_incomplete",
        axis=1,
    )
    joined["interpretation"] = joined.apply(interpret, axis=1)

    ordered = [
        "query_id",
        "query_name",
        "run_phase",
        "winner_by_p95",
        "lmm_p95_ms",
        "schemalens_p95_ms",
        "p95_ratio_lmm_over_schemalens",
        "lmm_mean_ms",
        "schemalens_mean_ms",
        "lmm_median_ms",
        "schemalens_median_ms",
        "lmm_max_ms",
        "schemalens_max_ms",
        "lmm_n_completed",
        "schemalens_n_completed",
        "lmm_mean_n_returned",
        "schemalens_candidate_id",
        "schemalens_g_class",
        "schemalens_group",
        "schemalens_design_pattern",
        "interpretation",
    ]

    for c in ordered:
        if c not in joined.columns:
            joined[c] = pd.NA

    joined = joined[ordered].sort_values(["run_phase", "query_id"])

    comparison_csv = out_dir / "lmm_vs_schemalens_fiben_benchmark_p95_comparison_sf1.csv"
    summary_csv = out_dir / "lmm_vs_schemalens_fiben_benchmark_p95_summary_sf1.csv"
    report_md = out_dir / "lmm_vs_schemalens_fiben_benchmark_p95_report_sf1.md"

    joined.to_csv(comparison_csv, index=False)

    summary = (
        joined[joined["run_phase"] == "hot"]
        .groupby("winner_by_p95", as_index=False)
        .agg(n_queries=("query_id", "count"))
    )
    summary.to_csv(summary_csv, index=False)

    lines = []
    lines.append("# Lima & Mello 2015 vs SchemaLens FIBEN p95 benchmark comparison")
    lines.append("")
    lines.append("Scale: `sf1`")
    lines.append("")
    lines.append("## Hot-phase summary")
    lines.append("")
    lines.append(summary.to_markdown(index=False))
    lines.append("")
    lines.append("## Hot p95 by query")
    lines.append("")
    hot = joined[joined["run_phase"] == "hot"].copy()
    lines.append(hot[[
        "query_id",
        "winner_by_p95",
        "lmm_p95_ms",
        "schemalens_p95_ms",
        "p95_ratio_lmm_over_schemalens",
        "schemalens_g_class",
        "schemalens_design_pattern",
    ]].to_markdown(index=False))
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    for _, row in hot.iterrows():
        lines.append(f"- **{row['query_id']}**: {row['interpretation']}")

    report_md.write_text("\n".join(lines), encoding="utf-8")

    print("Wrote:")
    print(" -", comparison_csv)
    print(" -", summary_csv)
    print(" -", report_md)
    print()
    print("=== hot comparison ===")
    print(hot[[
        "query_id",
        "winner_by_p95",
        "lmm_p95_ms",
        "schemalens_p95_ms",
        "p95_ratio_lmm_over_schemalens",
        "schemalens_g_class",
        "schemalens_design_pattern",
        "interpretation",
    ]].to_string(index=False))
    print()
    print("=== hot winner summary ===")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
