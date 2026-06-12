#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


READ_QUERIES = {
    "Q1_CompanyProfileIBM",
    "Q2_CompanyWithIndustryCountryAndListedSecurities",
    "Q3_SecuritiesHeldInEachFinancialServiceAccount",
    "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity",
    "Q5_ReportsAndMetricDataOfCompany",
    "Q6_TechUSListedSecuritiesWithHighLastTradedValue",
    "Q7_PersonsWhoBoughtMoreIBMThanSold",
    "Q8_IBMTransactionsBelowAverageSellingPrice",
    "Q9_PersonsWhoBoughtAndSoldSameStock",
}


def safe_div(a, b):
    try:
        a = float(a)
        b = float(b)
        if b == 0:
            return None
        return a / b
    except Exception:
        return None


def load_dbsr_compact(query_plan_dir: Path) -> pd.DataFrame:
    frames = []
    for scale in ["sf1", "sf10", "sf30"]:
        p = query_plan_dir / f"dbsr_fiben_query_plan_{scale}_compact_candidates.csv"
        if not p.exists():
            raise FileNotFoundError(p)
        df = pd.read_csv(p)
        df["scale_label"] = scale
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--schemalens-best",
        default="analysis/generated/query_plan/fiben/fiben_query_plan_best_by_estimated_bytes.csv",
    )
    ap.add_argument(
        "--dbsr-query-plan-dir",
        default="DBSR_implementation/results/fiben/query_plan",
    )
    ap.add_argument(
        "--out-dir",
        default="DBSR_implementation/results/fiben/query_plan",
    )
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sl = pd.read_csv(args.schemalens_best)
    dbsr = load_dbsr_compact(Path(args.dbsr_query_plan_dir))

    sl = sl[sl["query_name"].isin(READ_QUERIES)].copy()
    dbsr = dbsr[dbsr["query_name"].isin(READ_QUERIES)].copy()

    sl_small = sl[[
        "scale_label",
        "query_name",
        "best_candidate_id",
        "best_g_class",
        "best_group",
        "best_design_pattern",
        "best_n_components",
        "best_docs_examined",
        "best_keys_examined",
        "best_estimated_docs_examined_bytes",
        "best_has_COLLSCAN",
        "best_has_GROUP",
        "best_collections_touched",
    ]].copy()

    dbsr_small = dbsr[[
        "scale_label",
        "query_name",
        "candidate_id",
        "execution_status",
        "n_components",
        "sum_n_returned",
        "sum_total_docs_examined",
        "sum_total_keys_examined",
        "sum_estimated_docs_examined_bytes",
        "has_IXSCAN",
        "has_COLLSCAN",
        "has_GROUP",
        "collections_touched",
    ]].copy()

    merged = sl_small.merge(
        dbsr_small,
        on=["scale_label", "query_name"],
        how="outer",
        validate="one_to_one",
    )

    rows = []
    for _, r in merged.iterrows():
        row = r.to_dict()

        row["docs_examined_ratio_dbsr_over_schemalens"] = safe_div(
            r.get("sum_total_docs_examined"),
            r.get("best_docs_examined"),
        )
        row["keys_examined_ratio_dbsr_over_schemalens"] = safe_div(
            r.get("sum_total_keys_examined"),
            r.get("best_keys_examined"),
        )
        row["estimated_bytes_ratio_dbsr_over_schemalens"] = safe_div(
            r.get("sum_estimated_docs_examined_bytes"),
            r.get("best_estimated_docs_examined_bytes"),
        )

        dbsr_bytes = r.get("sum_estimated_docs_examined_bytes")
        sl_bytes = r.get("best_estimated_docs_examined_bytes")

        try:
            if float(dbsr_bytes) < float(sl_bytes):
                row["lower_estimated_bytes_method"] = "DBSR"
            elif float(sl_bytes) < float(dbsr_bytes):
                row["lower_estimated_bytes_method"] = "SchemaLens"
            else:
                row["lower_estimated_bytes_method"] = "Tie"
        except Exception:
            row["lower_estimated_bytes_method"] = "unknown"

        dbsr_docs = r.get("sum_total_docs_examined")
        sl_docs = r.get("best_docs_examined")

        try:
            if float(dbsr_docs) < float(sl_docs):
                row["lower_docs_examined_method"] = "DBSR"
            elif float(sl_docs) < float(dbsr_docs):
                row["lower_docs_examined_method"] = "SchemaLens"
            else:
                row["lower_docs_examined_method"] = "Tie"
        except Exception:
            row["lower_docs_examined_method"] = "unknown"

        rows.append(row)

    comp = pd.DataFrame(rows).sort_values(["scale_label", "query_name"])

    comp_path = out_dir / "dbsr_vs_schemalens_fiben_query_plan_best_comparison.csv"
    comp.to_csv(comp_path, index=False)

    summary = (
        comp.groupby("scale_label")
        .agg(
            queries=("query_name", "count"),
            dbsr_lower_estimated_bytes=("lower_estimated_bytes_method", lambda x: int((x == "DBSR").sum())),
            schemalens_lower_estimated_bytes=("lower_estimated_bytes_method", lambda x: int((x == "SchemaLens").sum())),
            ties_estimated_bytes=("lower_estimated_bytes_method", lambda x: int((x == "Tie").sum())),
            dbsr_lower_docs=("lower_docs_examined_method", lambda x: int((x == "DBSR").sum())),
            schemalens_lower_docs=("lower_docs_examined_method", lambda x: int((x == "SchemaLens").sum())),
            ties_docs=("lower_docs_examined_method", lambda x: int((x == "Tie").sum())),
            avg_docs_ratio=("docs_examined_ratio_dbsr_over_schemalens", "mean"),
            avg_keys_ratio=("keys_examined_ratio_dbsr_over_schemalens", "mean"),
            avg_estimated_bytes_ratio=("estimated_bytes_ratio_dbsr_over_schemalens", "mean"),
        )
        .reset_index()
    )

    summary_path = out_dir / "dbsr_vs_schemalens_fiben_query_plan_best_summary.csv"
    summary.to_csv(summary_path, index=False)

    focus = comp[comp["query_name"].isin([
        "Q3_SecuritiesHeldInEachFinancialServiceAccount",
        "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity",
        "Q5_ReportsAndMetricDataOfCompany",
        "Q6_TechUSListedSecuritiesWithHighLastTradedValue",
    ])].copy()

    focus_path = out_dir / "dbsr_vs_schemalens_fiben_query_plan_focus_q3_q4_q5_q6.csv"
    focus.to_csv(focus_path, index=False)

    print("Wrote", comp_path)
    print("Wrote", summary_path)
    print("Wrote", focus_path)

    print("\nSummary:")
    print(summary.to_string(index=False))

    print("\nFocus Q3/Q4/Q5/Q6:")
    cols = [
        "scale_label",
        "query_name",
        "best_g_class",
        "best_design_pattern",
        "best_docs_examined",
        "sum_total_docs_examined",
        "docs_examined_ratio_dbsr_over_schemalens",
        "best_keys_examined",
        "sum_total_keys_examined",
        "keys_examined_ratio_dbsr_over_schemalens",
        "best_estimated_docs_examined_bytes",
        "sum_estimated_docs_examined_bytes",
        "estimated_bytes_ratio_dbsr_over_schemalens",
        "lower_estimated_bytes_method",
    ]
    print(focus[cols].to_string(index=False))


if __name__ == "__main__":
    main()
