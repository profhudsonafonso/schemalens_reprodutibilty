from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(".")
IN_DIR = ROOT / "benchmark" / "ldbc_snb" / "physical_benchmark"
OUT_DIR = ROOT / "analysis" / "generated" / "ldbc_snb_physical_cross_scale"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ACTIVATED_GROUPS = {"primary", "secondary_affected"}
NEAR_BEST_THRESHOLD = 0.05

def infer_scale(path: Path) -> str:
    s = str(path).lower()
    if "sf0_1" in s or "sf0.1" in s:
        return "sf0.1"
    if "sf1" in s and "sf10" not in s:
        return "sf1"
    if "sf3" in s:
        return "sf3"
    return "unknown"

def read_all(pattern_suffix: str) -> pd.DataFrame:
    rows = []
    for p in sorted(IN_DIR.glob(f"*/consolidated/*{pattern_suffix}")):
        scale = infer_scale(p)
        df = pd.read_csv(p)
        df["scale_label"] = scale
        df["source_file"] = str(p)
        rows.append(df)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)

agg = read_all("benchmark_aggregate_results.csv")
raw = read_all("benchmark_raw_results.csv")
plan = read_all("query_write_plan_summary_results.csv")
global_summary = read_all("global_summary.csv")
existing_qps = read_all("query_phase_summary.csv")

if agg.empty:
    raise SystemExit(f"No aggregate result files found under {IN_DIR}")

for col in ["p95_latency_ms", "avg_latency_ms", "failed_runs", "successful_runs", "avg_documents_returned", "documents_written"]:
    if col in agg.columns:
        agg[col] = pd.to_numeric(agg[col], errors="coerce")

agg["benchmark_group"] = agg["benchmark_group"].astype(str)
agg["g_class"] = agg["g_class"].astype(str)
agg["official_id"] = agg["official_id"].astype(str)
agg["run_phase"] = agg["run_phase"].astype(str)

validation_rows = []

for scale, gdf in agg.groupby("scale_label"):
    raw_g = raw[raw["scale_label"] == scale] if not raw.empty else pd.DataFrame()
    plan_g = plan[plan["scale_label"] == scale] if not plan.empty else pd.DataFrame()

    semantic_warning_total = 0
    if "semantic_warning" in gdf.columns:
        semantic_warning_total = int(gdf["semantic_warning"].fillna("").astype(str).str.strip().ne("").sum())

    raw_failed_rows = 0
    if not raw_g.empty and "execution_status" in raw_g.columns:
        raw_failed_rows = int((raw_g["execution_status"].astype(str).str.lower() != "completed").sum())

    plan_bad_rows = 0
    collscan_rows = 0
    if not plan_g.empty:
        if "execution_status" in plan_g.columns:
            plan_bad_rows = int((plan_g["execution_status"].astype(str).str.lower() != "completed").sum())
        if "has_COLLSCAN" in plan_g.columns:
            collscan_rows = int(plan_g["has_COLLSCAN"].astype(str).str.lower().isin(["true", "1"]).sum())

    failed_runs_total = int(gdf["failed_runs"].fillna(0).sum()) if "failed_runs" in gdf.columns else 0

    validation_rows.append({
        "scale_label": scale,
        "query_count": gdf["official_id"].nunique(),
        "aggregate_rows": len(gdf),
        "raw_rows": len(raw_g),
        "query_write_plan_rows": len(plan_g),
        "failed_runs_total": failed_runs_total,
        "semantic_warning_total": semantic_warning_total,
        "raw_failed_rows": raw_failed_rows,
        "non_completed_plan_rows": plan_bad_rows,
        "collscan_rows": collscan_rows,
        "valid_run": (
            failed_runs_total == 0
            and semantic_warning_total == 0
            and raw_failed_rows == 0
            and plan_bad_rows == 0
            and collscan_rows == 0
        )
    })

validation = pd.DataFrame(validation_rows).sort_values("scale_label")
validation.to_csv(OUT_DIR / "physical_cross_scale_validation_summary.csv", index=False)

winner_rows = []
near_best_rows = []

for (scale, qid, phase), gdf in agg.groupby(["scale_label", "official_id", "run_phase"], dropna=False):
    gdf = gdf.copy().sort_values("p95_latency_ms")
    global_best = gdf.iloc[0]
    global_best_p95 = float(global_best["p95_latency_ms"])

    activated = gdf[gdf["benchmark_group"].isin(ACTIVATED_GROUPS)].copy()
    primary = gdf[gdf["benchmark_group"].eq("primary")].copy()
    secondary = gdf[gdf["benchmark_group"].eq("secondary_affected")].copy()
    control = gdf[gdf["benchmark_group"].eq("control")].copy()

    best_activated = activated.sort_values("p95_latency_ms").iloc[0] if not activated.empty else None
    best_primary = primary.sort_values("p95_latency_ms").iloc[0] if not primary.empty else None
    best_secondary = secondary.sort_values("p95_latency_ms").iloc[0] if not secondary.empty else None
    best_control = control.sort_values("p95_latency_ms").iloc[0] if not control.empty else None

    def regret(best):
        if best is None or global_best_p95 <= 0:
            return np.nan
        return (float(best["p95_latency_ms"]) - global_best_p95) / global_best_p95

    winner_rows.append({
        "scale_label": scale,
        "official_id": qid,
        "query_name": global_best.get("query_name", ""),
        "run_phase": phase,
        "candidate_count": len(gdf),
        "global_best_candidate_id": global_best["candidate_id"],
        "global_best_g_class": global_best["g_class"],
        "global_best_group": global_best["benchmark_group"],
        "global_best_p95_latency_ms": global_best_p95,
        "activated_best_candidate_id": best_activated["candidate_id"] if best_activated is not None else "",
        "activated_best_g_class": best_activated["g_class"] if best_activated is not None else "",
        "activated_best_group": best_activated["benchmark_group"] if best_activated is not None else "",
        "activated_best_p95_latency_ms": float(best_activated["p95_latency_ms"]) if best_activated is not None else np.nan,
        "activated_regret": regret(best_activated),
        "primary_best_candidate_id": best_primary["candidate_id"] if best_primary is not None else "",
        "primary_best_g_class": best_primary["g_class"] if best_primary is not None else "",
        "primary_best_p95_latency_ms": float(best_primary["p95_latency_ms"]) if best_primary is not None else np.nan,
        "primary_regret": regret(best_primary),
        "secondary_best_candidate_id": best_secondary["candidate_id"] if best_secondary is not None else "",
        "secondary_best_g_class": best_secondary["g_class"] if best_secondary is not None else "",
        "secondary_best_p95_latency_ms": float(best_secondary["p95_latency_ms"]) if best_secondary is not None else np.nan,
        "control_best_candidate_id": best_control["candidate_id"] if best_control is not None else "",
        "control_best_g_class": best_control["g_class"] if best_control is not None else "",
        "control_best_p95_latency_ms": float(best_control["p95_latency_ms"]) if best_control is not None else np.nan,
        "activated_top1_preserved": global_best["benchmark_group"] in ACTIVATED_GROUPS,
        "primary_top1_preserved": global_best["benchmark_group"] == "primary",
    })

    threshold = global_best_p95 * (1.0 + NEAR_BEST_THRESHOLD)
    nb = gdf[gdf["p95_latency_ms"] <= threshold].copy()
    nb["near_best_threshold_pct"] = NEAR_BEST_THRESHOLD
    nb["global_best_p95_latency_ms"] = global_best_p95
    nb["near_best_regret"] = (nb["p95_latency_ms"] - global_best_p95) / global_best_p95
    nb["scale_label"] = scale
    nb["official_id"] = qid
    nb["run_phase"] = phase
    near_best_rows.append(nb)

winners = pd.DataFrame(winner_rows)
near_best = pd.concat(near_best_rows, ignore_index=True) if near_best_rows else pd.DataFrame()

winners.to_csv(OUT_DIR / "physical_query_phase_winners_and_regrets.csv", index=False)
near_best.to_csv(OUT_DIR / "physical_near_best_5pct_candidates.csv", index=False)

metrics_rows = []

for (scale, phase), gdf in winners.groupby(["scale_label", "run_phase"]):
    metrics_rows.append({
        "scale_label": scale,
        "run_phase": phase,
        "query_count": len(gdf),
        "activated_top1_preservation": float(gdf["activated_top1_preserved"].mean()),
        "primary_top1_preservation": float(gdf["primary_top1_preserved"].mean()),
        "mean_activated_regret": float(gdf["activated_regret"].fillna(0).mean()),
        "mean_primary_regret": float(gdf["primary_regret"].dropna().mean()),
        "primary_winners": int((gdf["global_best_group"] == "primary").sum()),
        "secondary_affected_winners": int((gdf["global_best_group"] == "secondary_affected").sum()),
        "control_winners": int((gdf["global_best_group"] == "control").sum()),
    })

metrics = pd.DataFrame(metrics_rows).sort_values(["scale_label", "run_phase"])
metrics.to_csv(OUT_DIR / "physical_cross_scale_metrics_by_phase.csv", index=False)

hot = winners[winners["run_phase"] == "hot"].copy()
hot_summary = metrics[metrics["run_phase"] == "hot"].copy()
hot_summary.to_csv(OUT_DIR / "physical_hot_cross_scale_metrics.csv", index=False)

winner_matrix = hot.copy()
winner_matrix["winner_label"] = (
    winner_matrix["global_best_g_class"].astype(str)
    + " / "
    + winner_matrix["global_best_group"].astype(str)
    + " / p95="
    + winner_matrix["global_best_p95_latency_ms"].round(3).astype(str)
)

pivot = winner_matrix.pivot(index="official_id", columns="scale_label", values="winner_label").reset_index()
pivot.to_csv(OUT_DIR / "physical_hot_winner_matrix.csv", index=False)

regret = hot[[
    "official_id", "scale_label", "activated_regret", "primary_regret",
    "global_best_g_class", "global_best_group", "global_best_p95_latency_ms"
]].copy()
regret.to_csv(OUT_DIR / "physical_hot_regret_detail.csv", index=False)

winner_counts = (
    winners.groupby(["scale_label", "run_phase", "global_best_group"])
    .size()
    .reset_index(name="winner_count")
    .sort_values(["scale_label", "run_phase", "global_best_group"])
)
winner_counts.to_csv(OUT_DIR / "physical_winner_counts_by_group.csv", index=False)

report = []
report.append("# LDBC SNB Physical MongoDB Cross-Scale Analysis")
report.append("")
report.append("This report summarizes the faithful physical MongoDB benchmark for LDBC SNB across SF0.1, SF1, and SF3 when available.")
report.append("")
report.append("## Validation summary")
report.append("")
report.append(validation.to_markdown(index=False))
report.append("")
report.append("## Hot-phase cross-scale metrics")
report.append("")
report.append(hot_summary.to_markdown(index=False))
report.append("")
report.append("## Hot-phase winner matrix")
report.append("")
report.append(pivot.to_markdown(index=False))
report.append("")
report.append("## Winner counts by group")
report.append("")
report.append(winner_counts.to_markdown(index=False))
report.append("")
report.append("## Notes")
report.append("")
report.append("- Activated candidates are defined as primary plus secondary_affected candidates.")
report.append("- Activated regret is computed relative to the global best candidate for the same query, scale, and phase.")
report.append("- Near-best candidates are candidates within 5% of the best p95 latency for the same query, scale, and phase.")
report.append("- The benchmark protocol uses 10 measured cold repetitions and 10 measured hot repetitions, with no extra warmup repetitions.")

(OUT_DIR / "physical_cross_scale_report.md").write_text("\n".join(report), encoding="utf-8")

print("Wrote outputs to:", OUT_DIR)
print("")
print("Validation summary:")
print(validation.to_string(index=False))
print("")
print("Metrics by phase:")
print(metrics.to_string(index=False))
print("")
print("Hot winner matrix:")
print(pivot.to_string(index=False))
