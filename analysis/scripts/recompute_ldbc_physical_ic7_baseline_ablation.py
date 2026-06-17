from pathlib import Path
import pandas as pd

IN = Path("analysis/generated/ldbc_snb_physical_query_plan/ldbc_snb_physical_benchmark_query_plan_joined.csv")
OUT = Path("analysis/generated/ldbc_snb_physical_query_plan")
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(IN)

ic7 = df[
    (df["official_id"].astype(str).str.upper() == "IC7") &
    (df["run_phase"].astype(str).str.lower() == "hot")
].copy()

ic7["g_class"] = ic7["g_class"].astype(str).str.upper()
ic7["scale_order"] = ic7["scale_label"].map({"sf0.1": 1, "sf1": 2, "sf3": 3})

if ic7.empty:
    raise SystemExit("No IC7 hot rows found.")

required = {"sf0.1", "sf1", "sf3"}
found = set(ic7["scale_label"].astype(str))
missing = required - found
if missing:
    raise SystemExit(f"Missing IC7 scales: {sorted(missing)}")

def best_in_space(scale_df, allowed_g):
    sub = scale_df[scale_df["g_class"].isin(allowed_g)].copy()
    if sub.empty:
        return None
    return sub.loc[sub["p95_latency_ms"].idxmin()]

def fmt_space(gs):
    return ",".join(gs)

baseline_spaces = {
    "SchemaLens": ["G0", "G3", "G4", "G6"],
    "random-k": ["G0", "G3", "G4", "G6"],
    "always-reference": ["G0", "G3", "G6"],
    "always-embed": ["G4"],
    "depth-only": ["G3", "G4", "G6"],
    "relationship-type-only": ["G0", "G3"],
}

ablation_spaces = {
    "full SchemaLens": ["G0", "G3", "G4", "G6"],
    "no-relationship-semantics": ["G0"],
    "no-depth": ["G0", "G6"],
    "no-residual-traversal": ["G0", "G6"],
    "no-sharedness": ["G0", "G4"],
    "no-update-volatility": ["G0", "G4", "G6"],
    "no-rel.-semantics-no-depth": ["G0"],
}

baseline_rows = []
ablation_rows = []

for scale, sdf in ic7.groupby("scale_label", sort=False):
    sdf = sdf.copy()
    global_best = sdf.loc[sdf["p95_latency_ms"].idxmin()]
    global_g = global_best["g_class"]
    global_p95 = float(global_best["p95_latency_ms"])

    for method, gs in baseline_spaces.items():
        choice = best_in_space(sdf, gs)
        choice_g = choice["g_class"]
        choice_p95 = float(choice["p95_latency_ms"])
        delta = choice_p95 - global_p95
        regret = delta / global_p95 if global_p95 else 0.0
        baseline_rows.append({
            "scale_label": scale,
            "global_winner": global_g,
            "global_winner_p95_ms": global_p95,
            "baseline": method,
            "selected_space": fmt_space(gs),
            "choice_g": choice_g,
            "choice_p95_ms": choice_p95,
            "delta_ms": delta,
            "regret": regret,
            "top1_preserved": choice_g == global_g,
        })

    for ablation, gs in ablation_spaces.items():
        choice = best_in_space(sdf, gs)
        choice_g = choice["g_class"]
        choice_p95 = float(choice["p95_latency_ms"])
        delta = choice_p95 - global_p95
        regret = delta / global_p95 if global_p95 else 0.0
        ablation_rows.append({
            "scale_label": scale,
            "global_winner": global_g,
            "global_winner_p95_ms": global_p95,
            "ablation": ablation,
            "remaining_space": fmt_space(gs),
            "choice_g": choice_g,
            "choice_p95_ms": choice_p95,
            "delta_ms": delta,
            "regret": regret,
            "top1_preserved": choice_g == global_g,
        })

baseline = pd.DataFrame(baseline_rows)
ablation = pd.DataFrame(ablation_rows)

order_map = {"sf0.1": 1, "sf1": 2, "sf3": 3}
baseline["scale_order"] = baseline["scale_label"].map(order_map)
ablation["scale_order"] = ablation["scale_label"].map(order_map)

baseline = baseline.sort_values(["scale_order", "baseline"]).drop(columns=["scale_order"])
ablation = ablation.sort_values(["scale_order", "ablation"]).drop(columns=["scale_order"])

baseline_csv = OUT / "ldbc_snb_physical_ic7_baseline_behavior.csv"
ablation_csv = OUT / "ldbc_snb_physical_ic7_ablation_behavior.csv"
baseline_tex = OUT / "ldbc_snb_physical_ic7_baseline_ablation_tables.tex"

baseline.to_csv(baseline_csv, index=False)
ablation.to_csv(ablation_csv, index=False)

def yesno(x):
    return "yes" if bool(x) else "no"

def tex_num(x, nd=3):
    return f"{float(x):.{nd}f}"

lines = []

lines.append(r"\begin{table}[t]")
lines.append(r"\centering")
lines.append(r"\caption{Baseline behavior for LDBC SNB IC7 under physical MongoDB hot-run p95.}")
lines.append(r"\label{tab:ldbc-ic7-physical-baseline}")
lines.append(r"\small")
lines.append(r"\begin{tabular}{llllrrrl}")
lines.append(r"\toprule")
lines.append(r"Scale & Winner & Baseline & Choice & p95 & $\Delta$ms & Regret & Top-1 \\")
lines.append(r"\midrule")
for _, r in baseline.iterrows():
    winner = f"{r['global_winner']}, {tex_num(r['global_winner_p95_ms'])}"
    lines.append(
        f"{r['scale_label']} & {winner} & {r['baseline']} & {r['choice_g']} & "
        f"{tex_num(r['choice_p95_ms'])} & {tex_num(r['delta_ms'])} & {tex_num(r['regret'])} & {yesno(r['top1_preserved'])} \\\\"
    )
lines.append(r"\bottomrule")
lines.append(r"\end{tabular}")
lines.append(r"\end{table}")
lines.append("")

lines.append(r"\begin{table}[t]")
lines.append(r"\centering")
lines.append(r"\caption{Ablation behavior for LDBC SNB IC7 under physical MongoDB hot-run p95.}")
lines.append(r"\label{tab:ldbc-ic7-physical-ablation}")
lines.append(r"\small")
lines.append(r"\begin{tabular}{llllrrrl}")
lines.append(r"\toprule")
lines.append(r"Scale & Winner & Ablation / remaining space & Choice & p95 & $\Delta$ms & Regret & Top-1 \\")
lines.append(r"\midrule")
for _, r in ablation.iterrows():
    winner = f"{r['global_winner']}, {tex_num(r['global_winner_p95_ms'])}"
    abl = f"{r['ablation']}: {r['remaining_space']}"
    lines.append(
        f"{r['scale_label']} & {winner} & {abl} & {r['choice_g']} & "
        f"{tex_num(r['choice_p95_ms'])} & {tex_num(r['delta_ms'])} & {tex_num(r['regret'])} & {yesno(r['top1_preserved'])} \\\\"
    )
lines.append(r"\bottomrule")
lines.append(r"\end{tabular}")
lines.append(r"\end{table}")

baseline_tex.write_text("\n".join(lines))

print("Wrote:", baseline_csv)
print("Wrote:", ablation_csv)
print("Wrote:", baseline_tex)

print("\n=== Baseline summary ===")
print(baseline.to_string(index=False))

print("\n=== Ablation summary ===")
print(ablation.to_string(index=False))
