from pathlib import Path
import pandas as pd
import numpy as np

OUT = Path("analysis/generated")
AGG_PATH = OUT / "aggregate_results_all_datasets.csv"
CONTROLLED_SPACE_SIZE = 10  # G0--G9

agg = pd.read_csv(AGG_PATH)

# Paper-facing comparison uses hot-run p95
hot = agg[agg["run_phase"] == "hot"].copy()

target_queries = {
    "imdb": [
        "QG1_WatchItemById",
        "QG2_WatchItemByTitle",
        "QG3_RecommendationByGenreAndSubtype",
        "QG4_AllPersonsOfTypeForWatchItem",
        "QG5_AllPersonsForEpisodesOfSeries",
        "QG6_EpisodesOfSeries",
        "QG7_UpdateWatchItemMetadata",
        "QG8_AddPersonRoleToWatchItem",
        "QG9_TopRatedSeriesByGenre",
        "QG10_AdvancedSearchWatchItems",
    ],
    "fiben": [
        "Q1_CompanyProfileIBM",
        "Q2_CompanyWithIndustryCountryAndListedSecurities",
        "Q3_SecuritiesHeldInEachFinancialServiceAccount",
        "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity",
        "Q5_ReportsAndMetricDataOfCompany",
        "Q6_TechUSListedSecuritiesWithHighLastTradedValue",
        "Q7_PersonsWhoBoughtMoreIBMThanSold",
        "Q8_IBMTransactionsBelowAverageSellingPrice",
        "Q9_PersonsWhoBoughtAndSoldSameStock",
        "Q10_CreateAccountHoldingAndBuyTransaction",
    ],
    "ldbc_snb": [
        "IC7_RecentLikers",
    ],
}

semantic_family = {
    # IMDb
    "QG1_WatchItemById": "local lookup",
    "QG2_WatchItemByTitle": "filtered lookup",
    "QG3_RecommendationByGenreAndSubtype": "association / recommendation",
    "QG4_AllPersonsOfTypeForWatchItem": "associative",
    "QG5_AllPersonsForEpisodesOfSeries": "deep associative / containment-affected",
    "QG6_EpisodesOfSeries": "containment",
    "QG7_UpdateWatchItemMetadata": "update",
    "QG8_AddPersonRoleToWatchItem": "insert / associative update",
    "QG9_TopRatedSeriesByGenre": "ranking / containment-affected",
    "QG10_AdvancedSearchWatchItems": "filtered search",

    # FIBEN
    "Q1_CompanyProfileIBM": "rooted lookup",
    "Q2_CompanyWithIndustryCountryAndListedSecurities": "association / descriptor",
    "Q3_SecuritiesHeldInEachFinancialServiceAccount": "associative / bridge",
    "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity": "deep traversal",
    "Q5_ReportsAndMetricDataOfCompany": "analytical hierarchy",
    "Q6_TechUSListedSecuritiesWithHighLastTradedValue": "filtered analytical",
    "Q7_PersonsWhoBoughtMoreIBMThanSold": "aggregation / transaction",
    "Q8_IBMTransactionsBelowAverageSellingPrice": "aggregation / transaction",
    "Q9_PersonsWhoBoughtAndSoldSameStock": "transaction overlap",
    "Q10_CreateAccountHoldingAndBuyTransaction": "insert / update",

    # LDBC
    "IC7_RecentLikers": "mixed graph / associative edge",
}

def group_is_activated(v):
    return str(v).lower() in {
        "primary",
        "secondary_affected",
        "secondary",
        "activated",
    }

def fmt_float(x, digits=3):
    if pd.isna(x):
        return ""
    return f"{float(x):.{digits}f}"

def latex_escape(s):
    s = str(s)
    return (
        s.replace("\\", "\\textbackslash{}")
         .replace("&", "\\&")
         .replace("%", "\\%")
         .replace("$", "\\$")
         .replace("#", "\\#")
         .replace("_", "\\_")
         .replace("{", "\\{")
         .replace("}", "\\}")
    )

rows = []

for dataset, queries in target_queries.items():
    ds = hot[hot["dataset"] == dataset].copy()

    for query_order, query_name in enumerate(queries, start=1):
        qdf = ds[ds["query_name"] == query_name].copy()

        if qdf.empty:
            rows.append({
                "dataset": dataset,
                "query_order": query_order,
                "query_name": query_name,
                "status": "missing_in_aggregate_results",
            })
            continue

        for scale, sg in qdf.groupby("scale_label"):
            sg = sg.copy()

            full_best = sg.loc[sg["p95_latency_ms"].idxmin()]

            activated = sg[sg["benchmark_group"].apply(group_is_activated)].copy()

            # Fallback if labels are unexpected
            if activated.empty:
                activated = sg[
                    sg["benchmark_group"].astype(str).str.lower() != "control"
                ].copy()

            if activated.empty:
                rows.append({
                    "dataset": dataset,
                    "query_order": query_order,
                    "query_name": query_name,
                    "scale_label": scale,
                    "status": "no_activated_configs",
                })
                continue

            activated_best = activated.loc[activated["p95_latency_ms"].idxmin()]

            full_best_p95 = float(full_best["p95_latency_ms"])
            activated_best_p95 = float(activated_best["p95_latency_ms"])
            regret = (
                (activated_best_p95 - full_best_p95) / full_best_p95
                if full_best_p95 > 0
                else np.nan
            )

            activated_g = sorted(
                activated["g_class"].dropna().astype(str).unique()
            )
            activated_config_ids = set(activated["config_id"].astype(str))

            # Correct DSR for the paper: controlled template space G0--G9
            dsr = 1 - (len(activated_g) / CONTROLLED_SPACE_SIZE)

            top1 = str(full_best["config_id"]) in activated_config_ids
            near_best = bool(regret <= 0.05) if not pd.isna(regret) else False

            rows.append({
                "dataset": dataset,
                "query_order": query_order,
                "query_name": query_name,
                "scale_label": scale,
                "semantic_family": semantic_family.get(query_name, ""),
                "activated_configs": ",".join(activated_g),
                "best_observed_config": full_best["config_id"],
                "best_observed_g": full_best["g_class"],
                "activated_best_config": activated_best["config_id"],
                "activated_best_g": activated_best["g_class"],
                "full_best_p95_ms": full_best_p95,
                "activated_best_p95_ms": activated_best_p95,
                "dsr": dsr,
                "top1_preserved": int(top1),
                "near_best_preserved": int(near_best),
                "relative_regret": regret,
                "status": "ok",
            })

by_scale = pd.DataFrame(rows)
by_scale.to_csv(OUT / "dke_extended_table15_by_scale.csv", index=False)

# Compact paper-facing version: one row per dataset/query
compact_rows = []
ok = by_scale[by_scale["status"] == "ok"].copy()

for (dataset, query_name), g in ok.groupby(["dataset", "query_name"], sort=False):
    g = g.sort_values("scale_label")

    best_by_scale = "; ".join(
        f"{r.scale_label}:{r.best_observed_g}" for r in g.itertuples()
    )
    activated_best_by_scale = "; ".join(
        f"{r.scale_label}:{r.activated_best_g}" for r in g.itertuples()
    )

    activated_union = sorted(
        set(",".join(g["activated_configs"].dropna().astype(str)).split(",")) - {""}
    )

    compact_rows.append({
        "dataset": dataset,
        "query_order": int(g["query_order"].iloc[0]),
        "query_name": query_name,
        "semantic_family": g["semantic_family"].iloc[0],
        "activated_configs_union": ",".join(activated_union),
        "best_observed_by_scale": best_by_scale,
        "activated_best_by_scale": activated_best_by_scale,
        "avg_dsr": g["dsr"].mean(),
        "top1_preservation": f"{int(g['top1_preserved'].sum())}/{len(g)}",
        "near_best_preservation": f"{int(g['near_best_preserved'].sum())}/{len(g)}",
        "mean_regret": g["relative_regret"].mean(),
        "max_regret": g["relative_regret"].max(),
        "query_plan_evidence": "",
        "interpretation": "",
        "status": "ok",
    })

compact = pd.DataFrame(compact_rows)

dataset_order = {"imdb": 1, "fiben": 2, "ldbc_snb": 3}
compact["dataset_order"] = compact["dataset"].map(dataset_order).fillna(99)
compact = compact.sort_values(["dataset_order", "query_order"]).drop(
    columns=["dataset_order"]
)

# Add LDBC aggregate row
ldbc = hot[hot["dataset"] == "ldbc_snb"].copy()

if not ldbc.empty:
    tmp = []

    for (query_name, scale), sg in ldbc.groupby(["query_name", "scale_label"]):
        full_best = sg.loc[sg["p95_latency_ms"].idxmin()]

        activated = sg[sg["benchmark_group"].apply(group_is_activated)].copy()

        if activated.empty:
            activated = sg[
                sg["benchmark_group"].astype(str).str.lower() != "control"
            ].copy()

        if activated.empty:
            continue

        activated_best = activated.loc[activated["p95_latency_ms"].idxmin()]

        full_best_p95 = float(full_best["p95_latency_ms"])
        activated_best_p95 = float(activated_best["p95_latency_ms"])

        regret = (
            (activated_best_p95 - full_best_p95) / full_best_p95
            if full_best_p95 > 0
            else np.nan
        )

        activated_g = sorted(
            activated["g_class"].dropna().astype(str).unique()
        )

        tmp.append({
            "query_name": query_name,
            "scale_label": scale,
            "top1": int(str(full_best["config_id"]) in set(activated["config_id"].astype(str))),
            "near_best": int(regret <= 0.05 if not pd.isna(regret) else False),
            "regret": regret,
            "dsr": 1 - (len(activated_g) / CONTROLLED_SPACE_SIZE),
        })

    ldbc_summary = pd.DataFrame(tmp)

    if not ldbc_summary.empty:
        compact = pd.concat([
            compact,
            pd.DataFrame([{
                "dataset": "ldbc_snb",
                "query_order": 999,
                "query_name": "Official IC/IS/INS aggregate",
                "semantic_family": "official workload aggregate",
                "activated_configs_union": "query-specific",
                "best_observed_by_scale": "varies",
                "activated_best_by_scale": "varies",
                "avg_dsr": ldbc_summary["dsr"].mean(),
                "top1_preservation": f"{int(ldbc_summary['top1'].sum())}/{len(ldbc_summary)}",
                "near_best_preservation": f"{int(ldbc_summary['near_best'].sum())}/{len(ldbc_summary)}",
                "mean_regret": ldbc_summary["regret"].mean(),
                "max_regret": ldbc_summary["regret"].max(),
                "query_plan_evidence": "",
                "interpretation": "",
                "status": "ok",
            }])
        ], ignore_index=True)

compact.to_csv(OUT / "dke_extended_table15_compact.csv", index=False)

# LaTeX draft without pandas.to_latex, so no jinja2 dependency
latex_cols = [
    "dataset",
    "query_name",
    "semantic_family",
    "activated_configs_union",
    "best_observed_by_scale",
    "top1_preservation",
    "near_best_preservation",
    "mean_regret",
    "avg_dsr",
]

latex_df = compact[latex_cols].copy()
latex_df["mean_regret"] = latex_df["mean_regret"].apply(lambda x: fmt_float(x, 3))
latex_df["avg_dsr"] = latex_df["avg_dsr"].apply(lambda x: fmt_float(x, 3))

lines = []
lines.append("\\begin{longtable}{lllllllll}")
lines.append("\\caption{Extended representative reduction-quality results.}\\\\")
lines.append("\\toprule")
lines.append("Dataset & Query & Family & Activated & Best by scale & Top-1 & Near-best & Regret & DSR \\\\")
lines.append("\\midrule")
lines.append("\\endfirsthead")
lines.append("\\toprule")
lines.append("Dataset & Query & Family & Activated & Best by scale & Top-1 & Near-best & Regret & DSR \\\\")
lines.append("\\midrule")
lines.append("\\endhead")

for _, r in latex_df.iterrows():
    vals = [
        r["dataset"],
        r["query_name"],
        r["semantic_family"],
        r["activated_configs_union"],
        r["best_observed_by_scale"],
        r["top1_preservation"],
        r["near_best_preservation"],
        r["mean_regret"],
        r["avg_dsr"],
    ]
    lines.append(" & ".join(latex_escape(v) for v in vals) + " \\\\")

lines.append("\\bottomrule")
lines.append("\\end{longtable}")

(OUT / "dke_extended_table15_compact.tex").write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print("Generated:")
print(" - analysis/generated/dke_extended_table15_by_scale.csv")
print(" - analysis/generated/dke_extended_table15_compact.csv")
print(" - analysis/generated/dke_extended_table15_compact.tex")
print()
print("By-scale status:")
print(by_scale["status"].value_counts(dropna=False))
print()
print("Compact rows:", len(compact))

# ---------------------------------------------------------------------
# Paper-style cross-dataset summary
# ---------------------------------------------------------------------
# This table follows the interpretation used in the paper section
# "Comparative Results Across Datasets": the activated configs are the
# primary semantic family, while the best observed config is selected from
# the broader comparison space.

paper_selected = [
    # IMDb: required QG2, QG3, QG4 + two strong additional cases
    ("imdb", "QG2_WatchItemByTitle", "Filtered lookup"),
    ("imdb", "QG3_RecommendationByGenreAndSubtype", "Association"),
    ("imdb", "QG4_AllPersonsOfTypeForWatchItem", "Associative"),
    ("imdb", "QG6_EpisodesOfSeries", "Containment"),
    ("imdb", "QG9_TopRatedSeriesByGenre", "Ranking / containment-like"),

    # FIBEN: required Q2, Q3, Q5 + two strong additional cases
    ("fiben", "Q2_CompanyWithIndustryCountryAndListedSecurities", "Association"),
    ("fiben", "Q3_SecuritiesHeldInEachFinancialServiceAccount", "Associative"),
    ("fiben", "Q5_ReportsAndMetricDataOfCompany", "Analytical / containment-like"),
    ("fiben", "Q8_IBMTransactionsBelowAverageSellingPrice", "Transaction filtering"),
    ("fiben", "Q9_PersonsWhoBoughtAndSoldSameStock", "Transaction overlap"),
]

paper_short_names = {
    "QG2_WatchItemByTitle": "QG2\\_WatchItem By Title",
    "QG3_RecommendationByGenreAndSubtype": "QG3\\_Recommendation By Genre And Subtype",
    "QG4_AllPersonsOfTypeForWatchItem": "QG4\\_All Persons Of Type For WatchItem",
    "QG6_EpisodesOfSeries": "QG6\\_Episodes Of Series",
    "QG9_TopRatedSeriesByGenre": "QG9\\_Top Rated Series By Genre",
    "Q2_CompanyWithIndustryCountryAndListedSecurities": "Q2\\_Company With Industry, Country, and Listed Securities",
    "Q3_SecuritiesHeldInEachFinancialServiceAccount": "Q3\\_Securities Held In Each Financial Service Account",
    "Q5_ReportsAndMetricDataOfCompany": "Q5\\_Reports And Metric Data Of Company",
    "Q8_IBMTransactionsBelowAverageSellingPrice": "Q8\\_IBM Transactions Below Average Selling Price",
    "Q9_PersonsWhoBoughtAndSoldSameStock": "Q9\\_Persons Who Bought And Sold Same Stock",
}

paper_interpretations = {
    "QG2_WatchItemByTitle": "Filtered lookup case; the primary family does not preserve the global winner, but keeps low regret.",
    "QG3_RecommendationByGenreAndSubtype": "Association-oriented recommendation case; evaluates whether the primary association family remains near-best against the broader space.",
    "QG4_AllPersonsOfTypeForWatchItem": "Associative traversal case; bridge-aware alternatives preserve the best observed design.",
    "QG6_EpisodesOfSeries": "Containment case; evaluates the trade-off between references and embedded containment across scale.",
    "QG9_TopRatedSeriesByGenre": "Ranking and containment-like case; evaluates whether the activated family preserves the specialized series-root access pattern.",
    "Q2_CompanyWithIndustryCountryAndListedSecurities": "Association and descriptor case; corporation-centred access with descriptors and listed securities remains inside the reduced family.",
    "Q3_SecuritiesHeldInEachFinancialServiceAccount": "Associative bridge case; account, holding, and security traversal is preserved by the activated family.",
    "Q5_ReportsAndMetricDataOfCompany": "Analytical hierarchy case; the activated family remains near-best even when the control wins at one scale.",
    "Q8_IBMTransactionsBelowAverageSellingPrice": "Transaction filtering case; transaction-oriented alternatives preserve the best observed configuration.",
    "Q9_PersonsWhoBoughtAndSoldSameStock": "Transaction overlap case; buy/sell overlap remains inside the activated family.",
}

def paper_fmt_g_list(values):
    vals = []
    for v in values:
        s = str(v)
        if s.upper() == "CONTROL":
            vals.append("\\mathrm{Control}")
        elif s.startswith("G"):
            vals.append(f"G_{s[1:]}")
        else:
            vals.append(s)
    return "$" + ", ".join(vals) + "$"

def paper_fmt_best(values):
    vals = []
    for v in values:
        s = str(v)
        if s.upper() == "CONTROL":
            vals.append("\\mathrm{Control}")
        elif s.startswith("G"):
            vals.append(f"G_{s[1:]}")
        else:
            vals.append(s)
    return "$" + " / ".join(vals) + "$"

def paper_top1_label(top1_count, near_count, n):
    if top1_count == n:
        return "yes"
    if near_count == n:
        return "near-best"
    if top1_count == 0:
        return "no"
    return f"{top1_count}/{n}"

paper_by_scale_rows = []
paper_compact_rows = []

for dataset, query_name, family in paper_selected:
    qdf = hot[(hot["dataset"] == dataset) & (hot["query_name"] == query_name)].copy()

    if qdf.empty:
        raise ValueError(f"Missing query in aggregate results: {dataset} {query_name}")

    per_scale = []

    for scale, sg in qdf.groupby("scale_label"):
        sg = sg.copy()

        full_best = sg.loc[sg["p95_latency_ms"].idxmin()]
        primary = sg[
            sg["benchmark_group"].astype(str).str.lower() == "primary"
        ].copy()

        if primary.empty:
            raise ValueError(f"No primary rows for {dataset} {query_name} {scale}")

        primary_best = primary.loc[primary["p95_latency_ms"].idxmin()]

        full_best_p95 = float(full_best["p95_latency_ms"])
        primary_best_p95 = float(primary_best["p95_latency_ms"])

        regret = (
            (primary_best_p95 - full_best_p95) / full_best_p95
            if full_best_p95 > 0
            else np.nan
        )

        primary_g = sorted(primary["g_class"].dropna().astype(str).unique())
        full_best_g = str(full_best["g_class"])

        top1 = int(full_best_g in primary_g)
        near = int(regret <= 0.05 if not pd.isna(regret) else False)
        dsr = 1 - (len(primary_g) / CONTROLLED_SPACE_SIZE)

        row = {
            "dataset": dataset,
            "query_name": query_name,
            "scale_label": scale,
            "family": family,
            "primary_activated_g": ",".join(primary_g),
            "best_observed_g": full_best_g,
            "primary_best_g": str(primary_best["g_class"]),
            "full_best_p95_ms": full_best_p95,
            "primary_best_p95_ms": primary_best_p95,
            "dsr": dsr,
            "top1_preserved": top1,
            "near_best_preserved": near,
            "relative_regret": regret,
        }

        paper_by_scale_rows.append(row)
        per_scale.append(row)

    ps = pd.DataFrame(per_scale)

    activated_union = sorted(
        set(",".join(ps["primary_activated_g"].dropna().astype(str)).split(",")) - {""}
    )
    best_by_scale = list(ps["best_observed_g"])

    n = len(ps)
    top1_count = int(ps["top1_preserved"].sum())
    near_count = int(ps["near_best_preserved"].sum())

    paper_compact_rows.append({
        "dataset": "IMDb" if dataset == "imdb" else "FIBEN",
        "family": family,
        "query_name": query_name,
        "query_latex": paper_short_names[query_name],
        "activated_configs_latex": paper_fmt_g_list(activated_union),
        "best_observed_latex": paper_fmt_best(best_by_scale),
        "dsr_pct": float(ps["dsr"].mean()) * 100,
        "top1": paper_top1_label(top1_count, near_count, n),
        "top1_count": f"{top1_count}/{n}",
        "near_best_count": f"{near_count}/{n}",
        "mean_regret": float(ps["relative_regret"].mean()),
        "interpretation": paper_interpretations[query_name],
    })

paper_by_scale = pd.DataFrame(paper_by_scale_rows)
paper_compact = pd.DataFrame(paper_compact_rows)

paper_by_scale.to_csv(
    OUT / "dke_cross_dataset_summary_paper_by_scale.csv",
    index=False,
)

paper_compact.to_csv(
    OUT / "dke_cross_dataset_summary_paper_compact.csv",
    index=False,
)

paper_lines = []
paper_lines.append("\\begin{sidewaystable}[p]")
paper_lines.append("\\centering")
paper_lines.append("\\caption{Cross-dataset summary of representative activated families and official-workload validation.}")
paper_lines.append("\\label{tab:cross_dataset_summary}")
paper_lines.append("\\scriptsize")
paper_lines.append("\\setlength{\\tabcolsep}{3.2pt}")
paper_lines.append("\\begin{tabular}{p{1.3cm} ")
paper_lines.append("                p{1.6cm} ")
paper_lines.append("                p{2.3cm} ")
paper_lines.append("                p{1.7cm} ")
paper_lines.append("                p{1.5cm} ")
paper_lines.append("                p{1.1cm} ")
paper_lines.append("                p{1.1cm} ")
paper_lines.append("                p{1.2cm} ")
paper_lines.append("                p{3.0cm}}")
paper_lines.append("\\toprule")
paper_lines.append("\\textbf{Dataset} & ")
paper_lines.append("\\textbf{Family} & ")
paper_lines.append("\\textbf{Representative query} & ")
paper_lines.append("\\textbf{Activated configs} & ")
paper_lines.append("\\textbf{Best config/Instantiation} & ")
paper_lines.append("\\textbf{DSR} & ")
paper_lines.append("\\textbf{Top-1} & ")
paper_lines.append("\\textbf{Regret} & ")
paper_lines.append("\\textbf{Interpretation} \\\\")
paper_lines.append("\\midrule")

for _, r in paper_compact.iterrows():
    paper_lines.append("")
    paper_lines.append(f"{r['dataset']} & ")
    paper_lines.append(f"{r['family']} & ")
    paper_lines.append(f"{r['query_latex']} & ")
    paper_lines.append(f"{r['activated_configs_latex']} & ")
    paper_lines.append(f"{r['best_observed_latex']} & ")
    paper_lines.append(f"{r['dsr_pct']:.1f}\\% & ")
    paper_lines.append(f"{r['top1']} & ")
    paper_lines.append(f"{r['mean_regret']:.3f} & ")
    paper_lines.append(f"{r['interpretation']} \\\\")

paper_lines.append("")
paper_lines.append("\\bottomrule")
paper_lines.append("\\end{tabular}")
paper_lines.append("\\end{sidewaystable}")

(OUT / "dke_cross_dataset_summary_paper.tex").write_text(
    "\n".join(paper_lines),
    encoding="utf-8",
)

print()
print("Generated paper-style cross-dataset summary:")
print(" - analysis/generated/dke_cross_dataset_summary_paper_by_scale.csv")
print(" - analysis/generated/dke_cross_dataset_summary_paper_compact.csv")
print(" - analysis/generated/dke_cross_dataset_summary_paper.tex")
print()
print(
    paper_compact[
        [
            "dataset",
            "query_name",
            "activated_configs_latex",
            "best_observed_latex",
            "dsr_pct",
            "top1",
            "mean_regret",
        ]
    ].to_string(index=False)
)