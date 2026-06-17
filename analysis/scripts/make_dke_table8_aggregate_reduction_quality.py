#!/usr/bin/env python3
"""
Generate DKE Table 8: aggregate reduction-quality summary.

This script uses only existing repository artifacts and does not rerun benchmarks.

Input:
  analysis/generated/baseline_performance_by_case.csv

Outputs:
  analysis/generated/dke_table8_aggregate_reduction_quality.csv
  analysis/generated/dke_table8_aggregate_reduction_quality_by_case.csv
  analysis/generated/dke_table8_aggregate_reduction_quality.tex
"""

from pathlib import Path
import pandas as pd
import math

INPUT = Path("analysis/generated/baseline_performance_by_case.csv")

OUT_CSV = Path("analysis/generated/dke_table8_aggregate_reduction_quality.csv")
OUT_CASES = Path("analysis/generated/dke_table8_aggregate_reduction_quality_by_case.csv")
OUT_TEX = Path("analysis/generated/dke_table8_aggregate_reduction_quality.tex")

TEMPLATE_SPACE_SIZE = 10

DATASET_LABELS = {
    "imdb": "IMDb",
    "fiben": "FIBEN",
    "ldbc_snb": "LDBC SNB",
}

DATASET_ORDER = ["imdb", "fiben", "ldbc_snb"]


def count_activated_without_control(value, fallback):
    """
    Count activated G-classes from selected_g_classes, excluding CONTROL.
    This keeps DSR aligned with the paper definition over C={G0,...,G9}.
    """
    if pd.isna(value):
        return int(fallback)

    parts = [
        p.strip().upper()
        for p in str(value).split("|")
        if p.strip() and p.strip().upper() not in {"CONTROL", "NAN", "NONE"}
    ]

    if not parts:
        return int(fallback)

    return len(set(parts))


def fmt_count_ratio(value, total):
    return f"{int(value)}/{int(total)}"


def fmt_pct(value):
    return f"{100.0 * float(value):.1f}\\%"


def fmt_float(value, digits=3):
    return f"{float(value):.{digits}f}"


def summarize_group(df, dataset_label):
    n = len(df)

    if n == 0:
        raise ValueError(f"No rows found for {dataset_label}")

    return {
        "Dataset": dataset_label,
        "#cases": n,
        "avg_|A|": df["activated_count"].mean(),
        "avg_DSR": df["dsr"].mean(),
        "Top-1": int(df["top1_preserved"].sum()),
        "Top-3": int(df["top3_preserved"].sum()),
        "Near-best": int(df["near_best_preserved"].sum()),
        "Mean_regret": df["relative_regret"].mean(),
        "Max_regret": df["relative_regret"].max(),
    }


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT}")

    df = pd.read_csv(INPUT)

    required = [
        "dataset",
        "run_phase",
        "baseline",
        "availability_status",
        "selected_g_classes",
        "selected_config_count",
        "top1_preserved",
        "top3_preserved",
        "near_best_preserved",
        "relative_regret",
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {INPUT}: {missing}")

    df["dataset"] = df["dataset"].astype(str).str.lower()
    df["run_phase"] = df["run_phase"].astype(str).str.lower()
    df["baseline"] = df["baseline"].astype(str)
    df["availability_status"] = df["availability_status"].astype(str).str.lower()

    table_cases = df[
        (df["baseline"] == "schema_lens")
        & (df["run_phase"] == "hot")
        & (df["availability_status"] == "available")
    ].copy()

    numeric_cols = [
        "selected_config_count",
        "top1_preserved",
        "top3_preserved",
        "near_best_preserved",
        "relative_regret",
    ]

    for col in numeric_cols:
        table_cases[col] = pd.to_numeric(table_cases[col], errors="coerce")

    if table_cases[numeric_cols].isna().any().any():
        bad = table_cases[table_cases[numeric_cols].isna().any(axis=1)]
        raise ValueError(
            "Some SchemaLens hot available rows contain missing numeric metrics:\n"
            + bad[["dataset", "scale_label", "query_name"] + numeric_cols].to_string(index=False)
        )

    table_cases["activated_count"] = table_cases.apply(
        lambda r: count_activated_without_control(
            r["selected_g_classes"],
            r["selected_config_count"],
        ),
        axis=1,
    )

    table_cases["dsr"] = 1.0 - (table_cases["activated_count"] / TEMPLATE_SPACE_SIZE)

    # Keep a full case-level audit file for reproducibility.
    audit_cols = [
        "dataset",
        "scale_label",
        "query_name",
        "run_phase",
        "selected_g_classes",
        "selected_config_count",
        "activated_count",
        "dsr",
        "global_best_g_class",
        "baseline_best_g_class",
        "top1_preserved",
        "top3_preserved",
        "near_best_preserved",
        "relative_regret",
    ]
    table_cases[audit_cols].to_csv(OUT_CASES, index=False)

    rows = []

    for dataset in DATASET_ORDER:
        subset = table_cases[table_cases["dataset"] == dataset].copy()
        rows.append(summarize_group(subset, DATASET_LABELS[dataset]))

    rows.append(summarize_group(table_cases, "All"))

    out = pd.DataFrame(rows)

    # Numeric output for checking.
    out.to_csv(OUT_CSV, index=False)

    # Paper-facing formatted LaTeX.
    tex_rows = []

    for _, r in out.iterrows():
        n = int(r["#cases"])
        tex_rows.append(
            f"{r['Dataset']} & "
            f"{n} & "
            f"{float(r['avg_|A|']):.2f} & "
            f"{fmt_pct(r['avg_DSR'])} & "
            f"{fmt_count_ratio(r['Top-1'], n)} & "
            f"{fmt_count_ratio(r['Top-3'], n)} & "
            f"{fmt_count_ratio(r['Near-best'], n)} & "
            f"{fmt_float(r['Mean_regret'])} & "
            f"{fmt_float(r['Max_regret'])} \\\\"
        )

    latex = r"""\begin{table*}[t]
\centering
\caption{Aggregate reduction-quality summary across evaluated query-scale cases.}
\label{tab:aggregate-reduction-quality}
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{lrrrrrrrr}
\toprule
Dataset & \#cases & avg. $|A|$ & avg. DSR & Top-1 & Top-3 & Near-best & Mean regret & Max regret \\
\midrule
""" + "\n".join(tex_rows) + r"""
\bottomrule
\end{tabular}
\end{table*}
"""

    OUT_TEX.write_text(latex, encoding="utf-8")

    print("Generated:")
    print(f" - {OUT_CSV}")
    print(f" - {OUT_CASES}")
    print(f" - {OUT_TEX}")
    print()
    print(out.to_string(index=False))

    # Validation against the current article text for LDBC SNB.
    ldbc = out[out["Dataset"] == "LDBC SNB"].iloc[0]
    print("\nValidation checkpoint for LDBC SNB:")
    print(f"cases        = {int(ldbc['#cases'])}")
    print(f"avg DSR      = {100.0 * float(ldbc['avg_DSR']):.1f}%")
    print(f"Top-1        = {int(ldbc['Top-1'])}/{int(ldbc['#cases'])}")
    print(f"Mean regret  = {float(ldbc['Mean_regret']):.3f}")
    print()
    print("Expected from current article text: cases=66, avg DSR=71.4%, Top-1=65/66, Mean regret=0.008")


if __name__ == "__main__":
    main()
