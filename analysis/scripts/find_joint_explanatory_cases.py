#!/usr/bin/env python3
"""
Find joint explanatory cases for SchemaLens.

This script combines two kinds of evidence:

1. Baseline separation:
   Cases where SchemaLens preserves the Top-1 winner but deterministic baselines
   such as always-reference, always-embed, depth-only, or relationship-type-only
   miss it.

2. Ablation sensitivity:
   Cases where the full SchemaLens variant preserves the Top-1 winner but one or
   more ablated variants miss it.

Why this script exists
----------------------
Some cases are strong against baselines but not very sensitive to ablation
(e.g., a query where simple heuristics fail, but several SchemaLens signals are
redundant). Other cases are ablation-sensitive but not strong against baselines
(e.g., simple baselines may preserve the winner by chance in a small measured
space). This script helps identify:

- baseline-strong cases;
- ablation-strong cases;
- joint-strong cases;
- balanced explanatory cases.

Inputs
------
Expected under analysis/generated:

- baseline_performance_by_case.csv
- ablation_performance_by_case.csv

Optional, if available:

- representative_case_table_checked.csv
- representative_case_table.csv
- query_analytical_metadata_all_datasets.csv

Outputs
-------
- analysis/generated/joint_explanatory_cases_hot.csv
- analysis/generated/joint_explanatory_cases_by_query_hot.csv
- analysis/generated/joint_explanatory_cases_hot.md

Usage
-----
From repository root:

    python analysis/scripts/find_joint_explanatory_cases.py

Optional:

    python analysis/scripts/find_joint_explanatory_cases.py --run-phase hot
    python analysis/scripts/find_joint_explanatory_cases.py --generated-dir analysis/generated
    python analysis/scripts/find_joint_explanatory_cases.py --min-regret 0.10
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


DETERMINISTIC_BASELINES_DEFAULT = {
    "always_reference",
    "always-reference",
    "always_ref",
    "always_embed",
    "always-embed",
    "depth_only",
    "depth-only",
    "relationship_type_only",
    "relationship-type-only",
}

SCHEMALENS_NAMES = {"schema_lens", "schemalens", "full_schema_lens", "full-schemalens"}
RANDOM_NAMES = {"random_k", "random-k", "randomk"}


def norm_text(x) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    return str(x).strip()


def norm_key(x) -> str:
    return norm_text(x).strip().lower().replace("-", "_")


def safe_float(x, default: float = 0.0) -> float:
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def truthy(x) -> bool:
    if pd.isna(x):
        return False
    text = str(x).strip().lower()
    return text in {"1", "1.0", "true", "yes", "y", "preserved"}


def fmt(x, nd=3) -> str:
    try:
        if pd.isna(x):
            return ""
        return f"{float(x):.{nd}f}"
    except Exception:
        return str(x)


def find_col(df: pd.DataFrame, candidates: Iterable[str], required: bool = False) -> Optional[str]:
    if df.empty:
        if required:
            raise ValueError("Cannot find column in an empty DataFrame")
        return None

    exact = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in exact:
            return exact[c.lower()]

    def clean(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", s.lower())

    cleaned = {clean(c): c for c in df.columns}
    for c in candidates:
        if clean(c) in cleaned:
            return cleaned[clean(c)]

    if required:
        raise ValueError(
            f"Could not find any of these columns: {list(candidates)}\n"
            f"Available columns: {list(df.columns)}"
        )
    return None


def filter_run_phase(df: pd.DataFrame, run_phase: str) -> pd.DataFrame:
    phase_col = find_col(df, ["run_phase", "phase", "execution_phase"], required=False)
    if not phase_col:
        return df.copy()
    return df[df[phase_col].astype(str).str.lower().str.strip() == run_phase.lower()].copy()


def availability_filter(df: pd.DataFrame) -> pd.DataFrame:
    col = find_col(df, ["availability_status", "available", "status"], required=False)
    if not col:
        return df.copy()
    text = df[col].astype(str).str.lower()
    # Accept normal available rows. If the column is not a textual availability column,
    # this filter may remove too much, so only apply when at least one available row exists.
    available = df[text.str.contains("available|true|yes|1", regex=True, na=False)].copy()
    if not available.empty:
        return available
    return df.copy()


def standard_case_cols(df: pd.DataFrame) -> dict[str, str]:
    return {
        "dataset": find_col(df, ["dataset", "dataset_name"], required=True),
        "scale_label": find_col(df, ["scale_label", "scale", "scale_name"], required=True),
        "query_name": find_col(df, ["query_name", "query", "workload_query"], required=True),
    }


def get_first_matching_row(df: pd.DataFrame, method_col: str, names: set[str]) -> Optional[pd.Series]:
    mask = df[method_col].apply(lambda x: norm_key(x) in names)
    sub = df[mask]
    if sub.empty:
        return None
    return sub.iloc[0]


def infer_choice_cols(df: pd.DataFrame, prefix: str) -> tuple[Optional[str], Optional[str]]:
    """Return best_g_col, best_p95_col for baseline or ablation rows."""
    if prefix == "baseline":
        g_candidates = [
            "baseline_best_g_class",
            "baseline_best_class",
            "baseline_choice",
            "best_g_class",
            "selected_best_g_class",
            "choice",
        ]
        p95_candidates = [
            "baseline_best_p95",
            "baseline_best_p95_ms",
            "baseline_p95",
            "best_p95",
            "best_p95_ms",
            "choice_p95",
        ]
    else:
        g_candidates = [
            "ablated_best_g_class",
            "ablation_best_g_class",
            "variant_best_g_class",
            "best_g_class",
            "selected_best_g_class",
            "choice",
        ]
        p95_candidates = [
            "ablated_best_p95",
            "ablation_best_p95",
            "variant_best_p95",
            "best_p95",
            "best_p95_ms",
            "choice_p95",
        ]
    return find_col(df, g_candidates, required=False), find_col(df, p95_candidates, required=False)


def summarize_baselines(df: pd.DataFrame, run_phase: str, min_regret: float) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    df = filter_run_phase(df, run_phase)
    cols = standard_case_cols(df)

    method_col = find_col(df, ["baseline", "method", "strategy", "variant"], required=True)
    top1_col = find_col(df, ["top1_preserved", "top_1_preserved", "preserved_top1"], required=True)
    regret_col = find_col(df, ["relative_regret", "regret", "mean_regret"], required=True)
    global_g_col = find_col(df, ["global_best_g_class", "winner_g_class", "global_best_class"], required=True)
    global_p95_col = find_col(df, ["global_best_p95", "global_best_p95_ms", "winner_p95", "winner_p95_ms"], required=True)
    choice_g_col, choice_p95_col = infer_choice_cols(df, "baseline")
    selected_space_col = find_col(df, ["selected_g_classes", "schema_lens_selected_classes"], required=False)

    group_cols = [cols["dataset"], cols["scale_label"], cols["query_name"]]
    rows = []

    for key, g in df.groupby(group_cols, dropna=False):
        dataset, scale, query = [norm_text(x) for x in key]

        schema_row = get_first_matching_row(g, method_col, SCHEMALENS_NAMES)
        if schema_row is None or not truthy(schema_row[top1_col]):
            # We are interested in cases where SchemaLens itself succeeds.
            continue

        global_best = norm_text(schema_row[global_g_col])
        global_p95 = safe_float(schema_row[global_p95_col])
        schema_space = norm_text(schema_row[selected_space_col]) if selected_space_col else ""

        available = availability_filter(g)
        available["_method_norm"] = available[method_col].apply(norm_key)

        det = available[available["_method_norm"].isin(DETERMINISTIC_BASELINES_DEFAULT)].copy()
        random_row = get_first_matching_row(available, method_col, RANDOM_NAMES)

        if det.empty:
            continue

        det["_top1_bool"] = det[top1_col].apply(truthy)
        det["_regret"] = det[regret_col].apply(safe_float)

        misses = det[~det["_top1_bool"]].copy()
        hits = det[det["_top1_bool"]].copy()

        def detail_rows(frame: pd.DataFrame) -> str:
            details = []
            for _, r in frame.iterrows():
                method = norm_text(r[method_col])
                choice = norm_text(r[choice_g_col]) if choice_g_col else ""
                p95 = safe_float(r[choice_p95_col]) if choice_p95_col else float("nan")
                regret = safe_float(r[regret_col])
                delta = p95 - global_p95 if not math.isnan(p95) else float("nan")
                details.append(
                    f"{method}->{choice} p95={fmt(p95)} "
                    f"delta={fmt(delta)} regret={fmt(regret)}"
                )
            return "; ".join(details)

        random_top1 = ""
        random_regret = ""
        random_p95 = ""
        if random_row is not None:
            random_top1 = safe_float(random_row[top1_col])
            random_regret = safe_float(random_row[regret_col])
            if choice_p95_col and choice_p95_col in random_row.index:
                random_p95 = safe_float(random_row[choice_p95_col])
            elif "baseline_expected_p95" in random_row.index:
                random_p95 = safe_float(random_row["baseline_expected_p95"])

        miss_count = int(len(misses))
        hit_count = int(len(hits))
        available_count = int(len(det))
        mean_regret = float(misses["_regret"].mean()) if miss_count else 0.0
        max_regret = float(misses["_regret"].max()) if miss_count else 0.0

        rows.append({
            "dataset": dataset,
            "scale_label": scale,
            "query_name": query,
            "global_best_g_class": global_best,
            "global_best_p95": global_p95,
            "schema_lens_selected_space": schema_space,
            "baseline_available_count": available_count,
            "baseline_hit_count": hit_count,
            "baseline_miss_count": miss_count,
            "baseline_mean_miss_regret": mean_regret,
            "baseline_max_miss_regret": max_regret,
            "baseline_has_strong_miss": int(max_regret >= min_regret and miss_count > 0),
            "baseline_hit_details": detail_rows(hits),
            "baseline_miss_details": detail_rows(misses),
            "random_k_top1_or_probability": random_top1,
            "random_k_expected_p95": random_p95,
            "random_k_regret": random_regret,
        })

    return pd.DataFrame(rows)


def summarize_ablations(df: pd.DataFrame, run_phase: str, min_regret: float) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    df = filter_run_phase(df, run_phase)
    cols = standard_case_cols(df)

    variant_col = find_col(df, ["variant", "ablation", "ablation_variant", "method", "strategy"], required=True)
    top1_col = find_col(df, ["top1_preserved", "top_1_preserved", "preserved_top1"], required=True)
    regret_col = find_col(df, ["relative_regret", "regret", "mean_regret"], required=True)
    global_g_col = find_col(df, ["global_best_g_class", "winner_g_class", "global_best_class"], required=True)
    global_p95_col = find_col(df, ["global_best_p95", "global_best_p95_ms", "winner_p95", "winner_p95_ms"], required=True)
    choice_g_col, choice_p95_col = infer_choice_cols(df, "ablation")
    remaining_col = find_col(df, ["remaining_g_classes", "selected_g_classes", "variant_selected_g_classes"], required=False)
    removed_col = find_col(df, ["removed_g_classes", "removed_classes"], required=False)

    group_cols = [cols["dataset"], cols["scale_label"], cols["query_name"]]
    rows = []

    for key, g in df.groupby(group_cols, dropna=False):
        dataset, scale, query = [norm_text(x) for x in key]

        full_row = get_first_matching_row(g, variant_col, SCHEMALENS_NAMES)
        if full_row is None:
            full_row = get_first_matching_row(g, variant_col, {"full"})
        if full_row is None or not truthy(full_row[top1_col]):
            continue

        global_best = norm_text(full_row[global_g_col])
        global_p95 = safe_float(full_row[global_p95_col])

        available = availability_filter(g)
        available["_variant_norm"] = available[variant_col].apply(norm_key)
        ablated = available[~available["_variant_norm"].isin(SCHEMALENS_NAMES | {"full"})].copy()

        if ablated.empty:
            continue

        ablated["_top1_bool"] = ablated[top1_col].apply(truthy)
        ablated["_regret"] = ablated[regret_col].apply(safe_float)

        misses = ablated[~ablated["_top1_bool"]].copy()
        hits = ablated[ablated["_top1_bool"]].copy()

        def detail_rows(frame: pd.DataFrame) -> str:
            details = []
            for _, r in frame.iterrows():
                variant = norm_text(r[variant_col])
                choice = norm_text(r[choice_g_col]) if choice_g_col else ""
                p95 = safe_float(r[choice_p95_col]) if choice_p95_col else float("nan")
                regret = safe_float(r[regret_col])
                delta = p95 - global_p95 if not math.isnan(p95) else float("nan")
                remaining = norm_text(r[remaining_col]) if remaining_col else ""
                removed = norm_text(r[removed_col]) if removed_col else ""
                extra = []
                if remaining:
                    extra.append(f"space={remaining}")
                if removed:
                    extra.append(f"removed={removed}")
                suffix = f" ({'; '.join(extra)})" if extra else ""
                details.append(
                    f"{variant}->{choice} p95={fmt(p95)} "
                    f"delta={fmt(delta)} regret={fmt(regret)}{suffix}"
                )
            return "; ".join(details)

        miss_count = int(len(misses))
        hit_count = int(len(hits))
        available_count = int(len(ablated))
        mean_regret = float(misses["_regret"].mean()) if miss_count else 0.0
        max_regret = float(misses["_regret"].max()) if miss_count else 0.0

        rows.append({
            "dataset": dataset,
            "scale_label": scale,
            "query_name": query,
            "global_best_g_class": global_best,
            "global_best_p95": global_p95,
            "ablation_available_count": available_count,
            "ablation_hit_count": hit_count,
            "ablation_miss_count": miss_count,
            "ablation_mean_miss_regret": mean_regret,
            "ablation_max_miss_regret": max_regret,
            "ablation_has_strong_miss": int(max_regret >= min_regret and miss_count > 0),
            "ablation_hit_details": detail_rows(hits),
            "ablation_miss_details": detail_rows(misses),
        })

    return pd.DataFrame(rows)


def attach_metadata(joint: pd.DataFrame, generated_dir: Path) -> pd.DataFrame:
    if joint.empty:
        return joint

    metadata_sources = [
        generated_dir / "representative_case_table_checked.csv",
        generated_dir / "representative_case_table.csv",
        generated_dir / "query_analytical_metadata_all_datasets.csv",
    ]

    meta_frames = []
    for path in metadata_sources:
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if df.empty:
            continue

        try:
            cols = standard_case_cols(df)
        except Exception:
            continue

        keep_candidates = [
            cols["dataset"],
            cols["scale_label"],
            cols["query_name"],
            "case_focus",
            "selected_root",
            "Rc",
            "D",
            "Re",
            "DeltaRratio",
            "dominant_semantic_type",
            "update_volatility_max",
            "observed_sharedness_max",
            "query_family",
            "query_type",
        ]
        keep = [c for c in keep_candidates if c in df.columns]
        meta = df[keep].copy()
        meta = meta.rename(columns={
            cols["dataset"]: "dataset",
            cols["scale_label"]: "scale_label",
            cols["query_name"]: "query_name",
        })
        meta_frames.append(meta)

    if not meta_frames:
        return joint

    # Prefer earlier sources, fill missing with later ones.
    meta_all = pd.concat(meta_frames, ignore_index=True)
    meta_all = meta_all.drop_duplicates(subset=["dataset", "scale_label", "query_name"], keep="first")

    out = joint.merge(meta_all, how="left", on=["dataset", "scale_label", "query_name"])
    return out


def classify_case(row: pd.Series, min_regret: float) -> str:
    b_miss = safe_float(row.get("baseline_miss_count", 0))
    b_max = safe_float(row.get("baseline_max_miss_regret", 0))
    a_miss = safe_float(row.get("ablation_miss_count", 0))
    a_max = safe_float(row.get("ablation_max_miss_regret", 0))

    baseline_strong = b_miss >= 2 and b_max >= min_regret
    ablation_strong = a_miss >= 2 and a_max >= min_regret
    baseline_some = b_miss >= 1 and b_max >= min_regret
    ablation_some = a_miss >= 1 and a_max >= min_regret

    if baseline_strong and ablation_strong:
        return "joint_strong"
    if baseline_strong and ablation_some:
        return "baseline_strong_with_ablation_signal"
    if ablation_strong and baseline_some:
        return "ablation_strong_with_baseline_signal"
    if baseline_strong:
        return "baseline_strong"
    if ablation_strong:
        return "ablation_strong"
    if baseline_some and ablation_some:
        return "balanced_moderate"
    if baseline_some:
        return "baseline_moderate"
    if ablation_some:
        return "ablation_moderate"
    return "weak_or_redundant"


def compute_scores(joint: pd.DataFrame, min_regret: float) -> pd.DataFrame:
    if joint.empty:
        return joint

    for c in [
        "baseline_miss_count",
        "baseline_mean_miss_regret",
        "baseline_max_miss_regret",
        "ablation_miss_count",
        "ablation_mean_miss_regret",
        "ablation_max_miss_regret",
    ]:
        if c not in joint.columns:
            joint[c] = 0.0

    joint["baseline_score"] = (
        joint["baseline_miss_count"].apply(safe_float) * 2.0
        + joint["baseline_mean_miss_regret"].apply(lambda x: min(safe_float(x), 2.0))
        + joint["baseline_max_miss_regret"].apply(lambda x: min(safe_float(x), 5.0))
    )

    joint["ablation_score"] = (
        joint["ablation_miss_count"].apply(safe_float) * 2.0
        + joint["ablation_mean_miss_regret"].apply(lambda x: min(safe_float(x), 2.0))
        + joint["ablation_max_miss_regret"].apply(lambda x: min(safe_float(x), 5.0))
    )

    # Reward balance: cases with both dimensions should rise.
    joint["joint_score"] = (
        joint["baseline_score"]
        + joint["ablation_score"]
        + joint[["baseline_score", "ablation_score"]].min(axis=1) * 0.5
    )

    joint["case_type"] = joint.apply(lambda r: classify_case(r, min_regret), axis=1)

    return joint


def aggregate_by_query(joint: pd.DataFrame) -> pd.DataFrame:
    if joint.empty:
        return pd.DataFrame()

    rows = []
    for (dataset, query), g in joint.groupby(["dataset", "query_name"], dropna=False):
        scales = list(g["scale_label"].astype(str))
        winners = [f"{r.scale_label}:{r.global_best_g_class}" for r in g.itertuples()]
        case_types = sorted(set(g["case_type"].astype(str)))

        rows.append({
            "dataset": dataset,
            "query_name": query,
            "scale_count": len(g),
            "scales": "|".join(scales),
            "winner_sequence": "|".join(winners),
            "baseline_miss_total": int(g["baseline_miss_count"].apply(safe_float).sum()),
            "baseline_max_regret": float(g["baseline_max_miss_regret"].apply(safe_float).max()),
            "ablation_miss_total": int(g["ablation_miss_count"].apply(safe_float).sum()),
            "ablation_max_regret": float(g["ablation_max_miss_regret"].apply(safe_float).max()),
            "joint_score_sum": float(g["joint_score"].apply(safe_float).sum()),
            "joint_score_max": float(g["joint_score"].apply(safe_float).max()),
            "case_types": "|".join(case_types),
        })

    out = pd.DataFrame(rows)
    out = out.sort_values(
        ["joint_score_sum", "baseline_max_regret", "ablation_max_regret"],
        ascending=[False, False, False],
    )
    return out


def make_markdown_report(case_df: pd.DataFrame, query_df: pd.DataFrame, run_phase: str, min_regret: float) -> str:
    lines = []
    lines.append(f"# Joint explanatory cases - {run_phase} runs")
    lines.append("")
    lines.append("This report combines baseline-separation and ablation-sensitivity evidence.")
    lines.append("")
    lines.append(f"- Run phase: `{run_phase}`")
    lines.append(f"- Strong-regret threshold: `{min_regret}`")
    lines.append("- Baseline-strong means SchemaLens preserves Top-1 while multiple deterministic baselines miss it.")
    lines.append("- Ablation-strong means full SchemaLens preserves Top-1 while multiple ablated variants miss it.")
    lines.append("- Joint-strong means both conditions occur for the same dataset/scale/query case.")
    lines.append("")

    if case_df.empty:
        lines.append("No cases found.")
        return "\n".join(lines) + "\n"

    lines.append("## Case-type counts")
    lines.append("")
    counts = case_df["case_type"].value_counts().reset_index()
    counts.columns = ["case_type", "count"]
    lines.append(counts.to_markdown(index=False))
    lines.append("")

    display_cols = [
        "dataset",
        "scale_label",
        "query_name",
        "global_best_g_class",
        "global_best_p95",
        "baseline_miss_count",
        "baseline_max_miss_regret",
        "ablation_miss_count",
        "ablation_max_miss_regret",
        "case_type",
        "joint_score",
    ]

    lines.append("## Top case-level candidates")
    lines.append("")
    lines.append(case_df[display_cols].head(30).to_markdown(index=False, floatfmt=".4f"))
    lines.append("")

    if not query_df.empty:
        q_cols = [
            "dataset",
            "query_name",
            "scale_count",
            "winner_sequence",
            "baseline_miss_total",
            "baseline_max_regret",
            "ablation_miss_total",
            "ablation_max_regret",
            "case_types",
            "joint_score_sum",
        ]
        lines.append("## Top query-level candidates")
        lines.append("")
        lines.append(query_df[q_cols].head(20).to_markdown(index=False, floatfmt=".4f"))
        lines.append("")

    lines.append("## Recommended reading of the results")
    lines.append("")
    lines.append("- Use `baseline_strong` or `baseline_strong_with_ablation_signal` cases to explain why fixed heuristics are unstable.")
    lines.append("- Use `ablation_strong` or `ablation_strong_with_baseline_signal` cases to explain why analytical variables matter.")
    lines.append("- Use `joint_strong` cases, if present, as the most complete examples connecting baselines, ablation, workload structure, and winners.")
    lines.append("- Cases like FIBEN Q2 may be excellent baseline-separation cases even if ablation is moderate, because several SchemaLens signals may overlap.")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-dir", default="analysis/generated")
    parser.add_argument("--run-phase", default="hot")
    parser.add_argument("--min-regret", type=float, default=0.10)
    args = parser.parse_args()

    generated_dir = Path(args.generated_dir)
    baseline_path = generated_dir / "baseline_performance_by_case.csv"
    ablation_path = generated_dir / "ablation_performance_by_case.csv"

    if not baseline_path.exists():
        raise FileNotFoundError(f"Missing required file: {baseline_path}")
    if not ablation_path.exists():
        raise FileNotFoundError(f"Missing required file: {ablation_path}")

    baseline_df = pd.read_csv(baseline_path)
    ablation_df = pd.read_csv(ablation_path)

    baseline_summary = summarize_baselines(baseline_df, args.run_phase, args.min_regret)
    ablation_summary = summarize_ablations(ablation_df, args.run_phase, args.min_regret)

    if baseline_summary.empty:
        raise RuntimeError("No baseline summary rows found. Check column names or run_phase.")
    if ablation_summary.empty:
        raise RuntimeError("No ablation summary rows found. Check column names or run_phase.")

    joint = baseline_summary.merge(
        ablation_summary,
        how="outer",
        on=["dataset", "scale_label", "query_name", "global_best_g_class", "global_best_p95"],
        suffixes=("", "_ablation"),
    ).fillna({
        "baseline_available_count": 0,
        "baseline_hit_count": 0,
        "baseline_miss_count": 0,
        "baseline_mean_miss_regret": 0,
        "baseline_max_miss_regret": 0,
        "ablation_available_count": 0,
        "ablation_hit_count": 0,
        "ablation_miss_count": 0,
        "ablation_mean_miss_regret": 0,
        "ablation_max_miss_regret": 0,
    })

    joint = attach_metadata(joint, generated_dir)
    joint = compute_scores(joint, args.min_regret)
    joint = joint.sort_values(
        ["joint_score", "baseline_max_miss_regret", "ablation_max_miss_regret"],
        ascending=[False, False, False],
    )

    query_level = aggregate_by_query(joint)

    suffix = args.run_phase.lower()
    out_cases = generated_dir / f"joint_explanatory_cases_{suffix}.csv"
    out_queries = generated_dir / f"joint_explanatory_cases_by_query_{suffix}.csv"
    out_md = generated_dir / f"joint_explanatory_cases_{suffix}.md"

    joint.to_csv(out_cases, index=False)
    query_level.to_csv(out_queries, index=False)
    out_md.write_text(make_markdown_report(joint, query_level, args.run_phase, args.min_regret), encoding="utf-8")

    print(f"Saved: {out_cases}")
    print(f"Saved: {out_queries}")
    print(f"Saved: {out_md}")
    print("")
    print("Case-type counts:")
    print(joint["case_type"].value_counts().to_string())
    print("")
    print("Top 15 case-level candidates:")
    cols = [
        "dataset",
        "scale_label",
        "query_name",
        "global_best_g_class",
        "baseline_miss_count",
        "baseline_max_miss_regret",
        "ablation_miss_count",
        "ablation_max_miss_regret",
        "case_type",
        "joint_score",
    ]
    print(joint[cols].head(15).to_string(index=False))


if __name__ == "__main__":
    main()
