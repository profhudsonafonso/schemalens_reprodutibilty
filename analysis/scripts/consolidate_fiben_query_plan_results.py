#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


SUMMARY_FILE = "query_plan_summary_results.csv"
COMPONENT_FILE = "query_plan_component_results.csv"
STATUS_FILE = "query_plan_status_summary.csv"


def read_csv_if_exists(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
        df["source_results_dir"] = str(path.parent)
        return df
    except Exception as exc:
        print(f"[WARN] Could not read {path}: {exc}")
        return None


def collect_results(root_dir: Path, file_name: str) -> pd.DataFrame:
    frames = []
    for path in sorted(root_dir.rglob(file_name)):
        df = read_csv_if_exists(path)
        if df is not None and not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def make_query_scale_status(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()

    return (
        summary
        .groupby(["scale_label", "query_name", "execution_status"], dropna=False)
        .size()
        .reset_index(name="n_candidates")
        .sort_values(["scale_label", "query_name", "execution_status"])
    )


def make_query_scale_overview(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()

    rows = []
    for (scale, query), g in summary.groupby(["scale_label", "query_name"], dropna=False):
        rows.append({
            "scale_label": scale,
            "query_name": query,
            "n_candidates": len(g),
            "n_completed": int((g["execution_status"] == "completed").sum()),
            "n_skipped": int((g["execution_status"] == "skipped").sum()),
            "n_failed": int((g["execution_status"] == "failed").sum()) if "failed" in set(g["execution_status"]) else 0,
            "candidate_groups": ";".join(sorted(g["final_benchmark_group"].dropna().astype(str).unique())),
            "g_classes": ";".join(sorted(g["g_class"].dropna().astype(str).unique())),
            "min_components": g["n_components"].min() if "n_components" in g else None,
            "max_components": g["n_components"].max() if "n_components" in g else None,
            "has_any_collscan": bool(g["has_COLLSCAN"].fillna(False).any()) if "has_COLLSCAN" in g else None,
            "has_any_group": bool(g["has_GROUP"].fillna(False).any()) if "has_GROUP" in g else None,
            "total_docs_examined": g["sum_total_docs_examined"].sum() if "sum_total_docs_examined" in g else None,
            "total_keys_examined": g["sum_total_keys_examined"].sum() if "sum_total_keys_examined" in g else None,
            "total_estimated_docs_examined_bytes": g["sum_estimated_docs_examined_bytes"].sum()
                if "sum_estimated_docs_examined_bytes" in g else None,
        })

    return pd.DataFrame(rows).sort_values(["scale_label", "query_name"])


def make_best_by_query_scale(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()

    completed = summary[summary["execution_status"] == "completed"].copy()
    if completed.empty:
        return pd.DataFrame()

    metric = "sum_estimated_docs_examined_bytes"
    if metric not in completed.columns:
        return pd.DataFrame()

    rows = []
    for (scale, query), g in completed.groupby(["scale_label", "query_name"], dropna=False):
        g2 = g.sort_values(
            [metric, "sum_total_docs_examined", "sum_total_keys_examined", "n_components"],
            ascending=[True, True, True, True],
        )
        best = g2.iloc[0]
        rows.append({
            "scale_label": scale,
            "query_name": query,
            "best_candidate_id": best.get("candidate_id"),
            "best_g_class": best.get("g_class"),
            "best_group": best.get("final_benchmark_group"),
            "best_design_pattern": best.get("design_pattern"),
            "best_n_components": best.get("n_components"),
            "best_docs_examined": best.get("sum_total_docs_examined"),
            "best_keys_examined": best.get("sum_total_keys_examined"),
            "best_estimated_docs_examined_bytes": best.get(metric),
            "best_has_COLLSCAN": best.get("has_COLLSCAN"),
            "best_has_GROUP": best.get("has_GROUP"),
            "best_collections_touched": best.get("collections_touched"),
        })

    return pd.DataFrame(rows).sort_values(["scale_label", "query_name"])


def make_compact_candidate_table(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()

    cols = [
        "scale_label",
        "query_name",
        "candidate_id",
        "final_benchmark_group",
        "g_class",
        "design_pattern",
        "execution_status",
        "n_components",
        "sum_n_returned",
        "sum_total_docs_examined",
        "sum_total_keys_examined",
        "has_IXSCAN",
        "has_COLLSCAN",
        "has_GROUP",
        "sum_estimated_docs_examined_bytes",
        "max_collection_avg_obj_size_bytes",
        "collections_touched",
        "source_results_dir",
    ]

    existing = [c for c in cols if c in summary.columns]
    return summary[existing].sort_values(["scale_label", "query_name", "g_class", "candidate_id"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root-dir",
        default="/home/hudson/Documents/framework_test/fiben/analysis",
        help="Root directory containing per-query query-plan result folders.",
    )
    parser.add_argument(
        "--out-dir",
        default="/home/hudson/Documents/framework_test/fiben/analysis/generated/query_plan/fiben",
        help="Output directory for consolidated files.",
    )
    args = parser.parse_args()

    root_dir = Path(args.root_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Collecting results from: {root_dir}")
    print(f"[INFO] Writing consolidated outputs to: {out_dir}")

    summary = collect_results(root_dir, SUMMARY_FILE)
    components = collect_results(root_dir, COMPONENT_FILE)
    status = collect_results(root_dir, STATUS_FILE)

    summary_out = out_dir / "fiben_query_plan_summary_all.csv"
    components_out = out_dir / "fiben_query_plan_components_all.csv"
    status_out = out_dir / "fiben_query_plan_status_all.csv"

    summary.to_csv(summary_out, index=False)
    components.to_csv(components_out, index=False)
    status.to_csv(status_out, index=False)

    query_scale_status = make_query_scale_status(summary)
    query_scale_overview = make_query_scale_overview(summary)
    best_by_query_scale = make_best_by_query_scale(summary)
    compact_candidates = make_compact_candidate_table(summary)

    query_scale_status.to_csv(out_dir / "fiben_query_plan_query_scale_status.csv", index=False)
    query_scale_overview.to_csv(out_dir / "fiben_query_plan_query_scale_overview.csv", index=False)
    best_by_query_scale.to_csv(out_dir / "fiben_query_plan_best_by_estimated_bytes.csv", index=False)
    compact_candidates.to_csv(out_dir / "fiben_query_plan_compact_candidates.csv", index=False)

    print("[OK] Consolidation complete.")
    print(f"summary rows:    {len(summary)}")
    print(f"component rows:  {len(components)}")
    print(f"status rows:     {len(status)}")
    print()
    print("Generated files:")
    for p in sorted(out_dir.glob("*.csv")):
        print(f"- {p}")


if __name__ == "__main__":
    main()
