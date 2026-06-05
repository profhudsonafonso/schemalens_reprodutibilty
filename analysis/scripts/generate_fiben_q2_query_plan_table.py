#!/usr/bin/env python3
"""
Generate the LaTeX query-plan explanation table for FIBEN Q2.

This script is intended to be run from the root of the SchemaLens
reproducibility repository.

Inputs expected in the repository:
  - analysis/generated/query_plan/fiben/fiben_query_plan_summary_all.csv
  - FIBEN aggregate benchmark CSVs for SF1, SF10, and SF30, usually under:
      analysis/fiben/benchmark_aggregate_results_fiben_sf1.csv
      analysis/fiben/benchmark_aggregate_results_fiben_sf10.csv
      analysis/fiben/benchmark_aggregate_results_fiben_sf30.csv

Outputs:
  - analysis/generated/query_plan/fiben/fiben_q2_query_plan_table_rows.csv
  - analysis/generated/query_plan/fiben/fiben_q2_query_plan_table.tex
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Iterable

import pandas as pd


Q2 = "Q2_CompanyWithIndustryCountryAndListedSecurities"
SCALE_ORDER = {"sf1": 1, "sf10": 2, "sf30": 3}
G_ORDER = {"CONTROL": 0, "G1": 1, "G3": 2, "G5": 3, "G7": 4, "G9": 5}


MATRIX_SIGNAL = {
    "CONTROL": "baseline refs",
    "G1": "descriptor embedding",
    "G3": "association refs",
    "G5": "shared refs",
    "G7": "update-aware refs",
    "G9": "trade-off",
}


EXPLANATION = {
    "CONTROL": (
        "Normalized baseline; uses separate indexed dereferencing steps for "
        "the descriptor/listed-security path."
    ),
    "G1": (
        "Descriptor embedding colocates Industry and Country near the root, "
        "reducing one dereferencing component."
    ),
    "G3": (
        "Reference-oriented alternative; preserves indexed dereferencing through "
        "association references."
    ),
    "G5": (
        "Shared-reference alternative; keeps indexed dereferencing while accounting "
        "for shared target entities."
    ),
    "G7": (
        "Update-aware reference design; fewer indexed components, but potentially "
        "larger root documents."
    ),
    "G9": (
        "Trade-off candidate preserved by SchemaLens to benchmark a secondary "
        "read/update alternative."
    ),
}


def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / ".git").exists() or (p / "analysis").exists():
            return p
    raise FileNotFoundError("Could not infer repository root. Pass --repo-root explicitly.")


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return pd.read_csv(path)


def find_benchmark_files(repo: Path) -> list[Path]:
    """Find likely FIBEN aggregate benchmark CSVs in the repository."""
    candidates: list[Path] = []

    preferred_names = [
        "benchmark_aggregate_results_fiben_sf1.csv",
        "benchmark_aggregate_results_fiben_sf10.csv",
        "benchmark_aggregate_results_fiben_sf30.csv",
        # Older/local names sometimes used during the experiments:
        "benchmark_aggregate_resultssf1.csv",
        "benchmark_aggregate_resultssf10.csv",
        "benchmark_aggregate_resultssf30.csv",
        "benchmark_aggregate_results_sf1.csv",
        "benchmark_aggregate_results_sf10.csv",
        "benchmark_aggregate_results_sf30.csv",
    ]

    for name in preferred_names:
        candidates.extend(repo.glob(f"**/{name}"))

    # Fallback: any aggregate CSV containing FIBEN scale labels and p95.
    candidates.extend(repo.glob("**/*aggregate*sf*.csv"))
    candidates.extend(repo.glob("**/*benchmark*aggregate*.csv"))

    # Deduplicate while preserving order.
    seen: set[Path] = set()
    out: list[Path] = []
    for p in candidates:
        rp = p.resolve()
        if rp not in seen and rp.is_file():
            seen.add(rp)
            out.append(rp)
    return out


def load_benchmark(repo: Path) -> pd.DataFrame:
    frames = []
    for path in find_benchmark_files(repo):
        try:
            df = pd.read_csv(path)
        except Exception:
            continue

        required = {"query_name", "scale_label", "run_phase", "candidate_id", "p95_latency_ms"}
        if required.issubset(df.columns):
            df = df.copy()
            df["source_benchmark_file"] = str(path.relative_to(repo))
            frames.append(df)

    if not frames:
        raise FileNotFoundError(
            "Could not find FIBEN aggregate benchmark files with columns "
            "query_name, scale_label, run_phase, candidate_id, and p95_latency_ms. "
            "Expected files such as analysis/fiben/benchmark_aggregate_results_fiben_sf1.csv."
        )

    bench = pd.concat(frames, ignore_index=True)
    bench = bench[bench["query_name"].eq(Q2) & bench["run_phase"].eq("hot")].copy()

    # Keep only expected scales.
    bench = bench[bench["scale_label"].isin(SCALE_ORDER)].copy()

    # If duplicates exist because several copies were found, keep the first exact row.
    bench = bench.drop_duplicates(
        subset=["scale_label", "query_name", "candidate_id", "run_phase"],
        keep="first",
    )

    if bench.empty:
        raise ValueError("No hot benchmark rows found for FIBEN Q2.")

    return bench


def latex_escape_text(s: object) -> str:
    """Escape text for normal LaTeX mode, not for \texttt."""
    if pd.isna(s):
        return ""
    text = str(s)
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(ch, ch) for ch in text)


def latex_texttt(s: object) -> str:
    """Escape only what is needed inside a simple \texttt{...}."""
    if pd.isna(s):
        return ""
    text = str(s)
    text = text.replace("\\", r"\textbackslash{}")
    text = text.replace("_", r"\_")
    text = text.replace("{", r"\{").replace("}", r"\}")
    text = text.replace("&", r"\&")
    text = text.replace("%", r"\%")
    text = text.replace("$", r"\$")
    text = text.replace("#", r"\#")
    return r"\texttt{" + text + "}"


def fmt_float(x: object, digits: int = 2) -> str:
    try:
        value = float(x)
    except Exception:
        return "--"
    if math.isnan(value) or math.isinf(value):
        return "--"
    return f"{value:.{digits}f}"


def fmt_ratio(x: object) -> str:
    try:
        value = float(x)
    except Exception:
        return "--"
    if math.isnan(value) or math.isinf(value):
        return "--"
    return f"{value:.2f}x"


def fmt_int(x: object) -> str:
    try:
        value = float(x)
    except Exception:
        return "--"
    if math.isnan(value) or math.isinf(value):
        return "--"
    return str(int(round(value)))


def short_plan_pattern(stages: object) -> str:
    """Build a compact operator pattern from the all_stages field."""
    if pd.isna(stages) or not str(stages).strip():
        return "N/A"

    parts = [p.strip() for p in str(stages).split(";") if p.strip()]

    # Keep stable logical order for readability.
    order = [
        "COLLSCAN",
        "EXPRESS_IXSCAN",
        "IXSCAN",
        "FETCH",
        "PROJECTION_SIMPLE",
        "PROJECTION_DEFAULT",
        "SORT",
        "AND_SORTED",
        "OR",
        "GROUP",
        "MATCH",
        "LIMIT",
        "SUBPLAN",
    ]

    present = []
    for item in order:
        if item in parts:
            present.append(item)

    # Add any extra stages not in the ordering list.
    for item in parts:
        if item not in present:
            present.append(item)

    return "+".join(present) if present else "N/A"


def build_table_rows(summary: pd.DataFrame, bench: pd.DataFrame) -> pd.DataFrame:
    qplan = summary[
        summary["query_name"].eq(Q2)
        & summary["execution_status"].eq("completed")
        & summary["scale_label"].isin(SCALE_ORDER)
    ].copy()

    if qplan.empty:
        raise ValueError("No completed query-plan rows found for FIBEN Q2.")

    qplan = qplan.merge(
        bench[["scale_label", "candidate_id", "p95_latency_ms"]],
        on=["scale_label", "candidate_id"],
        how="left",
    )

    if qplan["p95_latency_ms"].isna().any():
        missing = qplan[qplan["p95_latency_ms"].isna()][
            ["scale_label", "candidate_id", "g_class"]
        ]
        raise ValueError(
            "Some Q2 query-plan rows could not be matched to p95 benchmark rows:\n"
            + missing.to_string(index=False)
        )

    # p95 winner per scale.
    winners = (
        qplan.sort_values(["scale_label", "p95_latency_ms"])
        .groupby("scale_label", as_index=False)
        .first()[["scale_label", "candidate_id"]]
        .rename(columns={"candidate_id": "winner_candidate_id"})
    )
    qplan = qplan.merge(winners, on="scale_label", how="left")
    qplan["is_p95_winner"] = qplan["candidate_id"].eq(qplan["winner_candidate_id"])

    # Add baseline values for ratios.
    base_cols = [
        "scale_label",
        "sum_total_docs_examined",
        "max_collection_avg_obj_size_bytes",
        "sum_estimated_docs_examined_bytes",
    ]
    base = qplan[qplan["is_p95_winner"]][base_cols].rename(
        columns={
            "sum_total_docs_examined": "base_docs",
            "max_collection_avg_obj_size_bytes": "base_obj",
            "sum_estimated_docs_examined_bytes": "base_bytes",
        }
    )
    qplan = qplan.merge(base, on="scale_label", how="left")

    def safe_div(a, b):
        try:
            a = float(a)
            b = float(b)
        except Exception:
            return float("nan")
        if b == 0 or math.isnan(a) or math.isnan(b):
            return float("nan")
        return a / b

    qplan["docs_ratio"] = [
        safe_div(a, b)
        for a, b in zip(qplan["sum_total_docs_examined"], qplan["base_docs"])
    ]
    qplan["obj_ratio"] = [
        safe_div(a, b)
        for a, b in zip(qplan["max_collection_avg_obj_size_bytes"], qplan["base_obj"])
    ]
    qplan["est_bytes_ratio"] = [
        safe_div(a, b)
        for a, b in zip(qplan["sum_estimated_docs_examined_bytes"], qplan["base_bytes"])
    ]

    qplan["matrix_signal"] = qplan["g_class"].map(MATRIX_SIGNAL).fillna(qplan["design_pattern"])
    qplan["mongodb_plan_pattern"] = qplan["all_stages"].map(short_plan_pattern)
    qplan["explanation"] = qplan["g_class"].map(EXPLANATION).fillna("Activated candidate.")

    qplan["scale_order"] = qplan["scale_label"].map(SCALE_ORDER)
    qplan["g_order"] = qplan["g_class"].map(G_ORDER).fillna(99).astype(int)

    return qplan.sort_values(["scale_order", "g_order"]).reset_index(drop=True)


def make_latex_table(rows: pd.DataFrame) -> str:
    lines: list[str] = []
    lines.append(r"\begin{table*}[t]")
    lines.append(r"\centering")
    lines.append(
        r"\caption{Query-plan explanation for FIBEN Q2 under MongoDB "
        r"\texttt{executionStats}. Ratios are computed relative to the "
        r"hot-p95 winning configuration at the same scale.}"
    )
    lines.append(r"\label{tab:fiben_q2_query_plan_explanation}")
    lines.append(r"\tiny")
    lines.append(r"\setlength{\tabcolsep}{2.0pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.12}")
    lines.append(
        r"\begin{tabular}{p{0.045\textwidth}p{0.055\textwidth}"
        r"p{0.115\textwidth}p{0.155\textwidth}r r r p{0.390\textwidth}}"
    )
    lines.append(r"\hline")
    lines.append(
        r"Scale & Config. & Matrix signal & MongoDB plan & Docs ratio & "
        r"Obj. ratio & Est. bytes ratio & Explanation \tabularnewline"
    )
    lines.append(r"\hline")

    previous_scale = None
    for _, row in rows.iterrows():
        scale = str(row["scale_label"]).upper()
        if previous_scale is not None and previous_scale != scale:
            lines.append(r"\hline")
        previous_scale = scale

        config = str(row["g_class"])
        if bool(row.get("is_p95_winner", False)):
            config_tex = r"\textbf{" + latex_escape_text(config) + "}"
        else:
            config_tex = latex_escape_text(config)

        plan_tex = latex_texttt(row["mongodb_plan_pattern"])

        line = (
            f"{latex_escape_text(scale)} & "
            f"{config_tex} & "
            f"{latex_escape_text(row['matrix_signal'])} & "
            f"{plan_tex} & "
            f"{fmt_ratio(row['docs_ratio'])} & "
            f"{fmt_ratio(row['obj_ratio'])} & "
            f"{fmt_ratio(row['est_bytes_ratio'])} & "
            f"{latex_escape_text(row['explanation'])} "
            r"\tabularnewline"
        )
        lines.append(line)

    lines.append(r"\hline")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table*}")
    return "\n".join(lines) + "\n"


def make_rows_csv(rows: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "scale_label",
        "g_class",
        "candidate_id",
        "final_benchmark_group",
        "design_pattern",
        "matrix_signal",
        "is_p95_winner",
        "p95_latency_ms",
        "mongodb_plan_pattern",
        "n_components",
        "sum_total_docs_examined",
        "sum_total_keys_examined",
        "max_collection_avg_obj_size_bytes",
        "sum_estimated_docs_examined_bytes",
        "docs_ratio",
        "obj_ratio",
        "est_bytes_ratio",
        "collections_touched",
        "all_stages",
        "all_index_names",
    ]
    return rows[[c for c in cols if c in rows.columns]].copy()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None, help="Path to repository root.")
    parser.add_argument(
        "--query-plan-summary",
        default="analysis/generated/query_plan/fiben/fiben_query_plan_summary_all.csv",
        help="Path to consolidated FIBEN query-plan summary CSV, relative to repo root.",
    )
    parser.add_argument(
        "--out-dir",
        default="analysis/generated/query_plan/fiben",
        help="Output directory, relative to repo root.",
    )
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve() if args.repo_root else find_repo_root(Path.cwd())
    summary_path = repo / args.query_plan_summary
    out_dir = repo / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = read_csv(summary_path)
    bench = load_benchmark(repo)
    rows = build_table_rows(summary, bench)

    rows_csv = make_rows_csv(rows)
    rows_csv_path = out_dir / "fiben_q2_query_plan_table_rows.csv"
    latex_path = out_dir / "fiben_q2_query_plan_table.tex"

    rows_csv.to_csv(rows_csv_path, index=False)
    latex_path.write_text(make_latex_table(rows), encoding="utf-8")

    print("[OK] Generated FIBEN Q2 query-plan table artifacts")
    print(f"- {rows_csv_path.relative_to(repo)}")
    print(f"- {latex_path.relative_to(repo)}")
    print()
    print("p95 winners by scale:")
    winners = rows[rows["is_p95_winner"]][
        ["scale_label", "g_class", "p95_latency_ms", "candidate_id"]
    ]
    print(winners.to_string(index=False))


if __name__ == "__main__":
    main()
