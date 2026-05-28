#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

GENERATED = Path("analysis/generated")
INPUT = GENERATED / "baseline_performance_by_case.csv"
OUT_CSV = GENERATED / "strong_baseline_cases_hot.csv"
OUT_MD = GENERATED / "strong_baseline_cases_hot.md"

DETERMINISTIC_BASELINES = [
    "always_reference",
    "always_embed",
    "depth_only",
    "relationship_type_only",
]

def fmt(x, nd=3):
    if pd.isna(x):
        return ""
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return str(x)

def main():
    df = pd.read_csv(INPUT)

    hot = df[df["run_phase"] == "hot"].copy()

    rows = []

    group_cols = ["dataset", "scale_label", "query_name", "query_scale_phase_id"]

    for key, g in hot.groupby(group_cols):
        dataset, scale, query, qid = key

        schema = g[g["baseline"] == "schema_lens"]
        if schema.empty:
            continue

        schema = schema.iloc[0]

        # keep only cases where SchemaLens preserves Top-1
        if float(schema["top1_preserved"]) != 1.0:
            continue

        global_best = schema["global_best_g_class"]
        global_best_p95 = float(schema["global_best_p95"])

        det = g[g["baseline"].isin(DETERMINISTIC_BASELINES)].copy()
        available = det[det["availability_status"] == "available"].copy()

        if available.empty:
            continue

        misses = available[available["top1_preserved"].astype(float) == 0.0].copy()
        hits = available[available["top1_preserved"].astype(float) == 1.0].copy()

        if misses.empty:
            continue

        miss_details = []
        for _, r in misses.iterrows():
            miss_details.append(
                f"{r['baseline']}->{r['baseline_best_g_class']}"
                f" p95={fmt(r['baseline_best_p95'])}"
                f" regret={fmt(r['relative_regret'])}"
            )

        hit_details = []
        for _, r in hits.iterrows():
            hit_details.append(
                f"{r['baseline']}->{r['baseline_best_g_class']}"
            )

        rows.append({
            "dataset": dataset,
            "scale_label": scale,
            "query_name": query,
            "winner": global_best,
            "winner_p95": global_best_p95,
            "schema_lens_space": schema["selected_g_classes"],
            "available_deterministic_baselines": len(available),
            "deterministic_hit_count": len(hits),
            "deterministic_miss_count": len(misses),
            "mean_miss_regret": misses["relative_regret"].astype(float).mean(),
            "max_miss_regret": misses["relative_regret"].astype(float).max(),
            "miss_details": "; ".join(miss_details),
            "hit_details": "; ".join(hit_details),
        })

    out = pd.DataFrame(rows)

    if out.empty:
        print("No strong cases found.")
        return

    out = out.sort_values(
        by=["deterministic_miss_count", "max_miss_regret", "mean_miss_regret"],
        ascending=[False, False, False],
    )

    out.to_csv(OUT_CSV, index=False)

    # Markdown report
    keep = [
        "dataset",
        "scale_label",
        "query_name",
        "winner",
        "winner_p95",
        "deterministic_hit_count",
        "deterministic_miss_count",
        "mean_miss_regret",
        "max_miss_regret",
        "miss_details",
    ]

    md = []
    md.append("# Strong baseline-separation cases - hot runs")
    md.append("")
    md.append(
        "This report lists hot-run cases where SchemaLens preserves Top-1 "
        "but deterministic baselines miss the winner."
    )
    md.append("")
    md.append(out[keep].head(30).to_markdown(index=False))
    md.append("")

    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"Saved: {OUT_CSV}")
    print(f"Saved: {OUT_MD}")
    print("")
    print(out[keep].head(15).to_string(index=False))

if __name__ == "__main__":
    main()