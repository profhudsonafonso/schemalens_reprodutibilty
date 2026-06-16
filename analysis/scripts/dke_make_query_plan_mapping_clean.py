from pathlib import Path
import pandas as pd

OUT = Path("analysis/generated")
TABLE_PATH = OUT / "dke_extended_table15_compact.csv"

compact = pd.read_csv(TABLE_PATH)

mapping = {
    # IMDb
    "QG1_WatchItemById": {
        "scope": "group-level",
        "experiment": "IMDb Group A light/no-roles query-plan",
        "files": [
            "analysis/generated/query_plan/imdb/group_A_light_no_roles/query_plan_summary_results_group_A.csv",
            "analysis/generated/query_plan/imdb/group_A_light_no_roles/query_plan_component_results_group_A.csv",
        ],
        "signal": "indexed lookup over WatchItem or specialized candidate root",
        "status": "available",
    },
    "QG2_WatchItemByTitle": {
        "scope": "group-level",
        "experiment": "IMDb Group A light/no-roles query-plan",
        "files": [
            "analysis/generated/query_plan/imdb/group_A_light_no_roles/query_plan_summary_results_group_A.csv",
            "analysis/generated/query_plan/imdb/group_A_light_no_roles/query_plan_component_results_group_A.csv",
        ],
        "signal": "title-based indexed lookup over WatchItem-oriented candidates",
        "status": "available",
    },
    "QG3_RecommendationByGenreAndSubtype": {
        "scope": "group-level",
        "experiment": "IMDb Group A light/no-roles query-plan",
        "files": [
            "analysis/generated/query_plan/imdb/group_A_light_no_roles/query_plan_summary_results_group_A.csv",
            "analysis/generated/query_plan/imdb/group_A_light_no_roles/query_plan_component_results_group_A.csv",
        ],
        "signal": "genre/subtype predicates and candidate root specialization",
        "status": "available",
    },
    "QG4_AllPersonsOfTypeForWatchItem": {
        "scope": "detailed/group-level",
        "experiment": "IMDb Group C roles query-plan",
        "files": [
            "analysis/generated/query_plan/imdb/group_C_roles_sf025/query_plan_summary_results_group_C_roles_sf025.csv",
            "analysis/generated/query_plan/imdb/group_C_roles_sf050/query_plan_summary_results_group_C_roles_sf050.csv",
            "analysis/generated/query_plan/imdb/group_C_roles_sf1_assoc_only/query_plan_summary_results_group_C_roles_sf1_assoc_only.csv",
            "analysis/generated/query_plan/imdb/group_C_roles_sf025/query_plan_component_results_group_C_roles_sf025.csv",
            "analysis/generated/query_plan/imdb/group_C_roles_sf050/query_plan_component_results_group_C_roles_sf050.csv",
            "analysis/generated/query_plan/imdb/group_C_roles_sf1_assoc_only/query_plan_component_results_group_C_roles_sf1_assoc_only.csv",
        ],
        "signal": "bridge/role traversal and indexed person access",
        "status": "available",
    },
    "QG5_AllPersonsForEpisodesOfSeries": {
        "scope": "detailed/group-level",
        "experiment": "IMDb Group C QG5 with episodes query-plan",
        "files": [
            "analysis/generated/query_plan/imdb/group_C_qg5_sf1_assoc_only_with_episodes/query_plan_summary_results_group_C_qg5_sf1_assoc_only_with_episodes.csv",
            "analysis/generated/query_plan/imdb/group_C_qg5_sf1_assoc_only_with_episodes/query_plan_component_results_group_C_qg5_sf1_assoc_only_with_episodes.csv",
            "analysis/generated/query_plan/imdb/group_C_roles_sf025/query_plan_summary_results_group_C_roles_sf025.csv",
            "analysis/generated/query_plan/imdb/group_C_roles_sf050/query_plan_summary_results_group_C_roles_sf050.csv",
        ],
        "signal": "episode traversal combined with role/person access",
        "status": "available",
    },
    "QG6_EpisodesOfSeries": {
        "scope": "detailed",
        "experiment": "IMDb Group B episodes query-plan",
        "files": [
            "analysis/generated/query_plan/imdb/group_B_episodes/query_plan_summary_results_group_B.csv",
            "analysis/generated/query_plan/imdb/group_B_episodes/query_plan_component_results_group_B.csv",
        ],
        "signal": "COUNT_SCAN over external episodes versus embedded series document size",
        "status": "available",
    },
    "QG7_UpdateWatchItemMetadata": {
        "scope": "group-level/write-related",
        "experiment": "IMDb Group A light/no-roles query-plan",
        "files": [
            "analysis/generated/query_plan/imdb/group_A_light_no_roles/query_plan_summary_results_group_A.csv",
            "analysis/generated/query_plan/imdb/group_A_light_no_roles/query_plan_component_results_group_A.csv",
        ],
        "signal": "update maintenance over WatchItem-oriented physical layouts",
        "status": "available",
    },
    "QG8_AddPersonRoleToWatchItem": {
        "scope": "detailed/write-related",
        "experiment": "IMDb Group D insert QG8 query-plan",
        "files": [
            "analysis/generated/query_plan/imdb/group_D_insert_qg8/query_plan_summary_results_group_D.csv",
            "analysis/generated/query_plan/imdb/group_D_insert_qg8/query_plan_component_results_group_D.csv",
        ],
        "signal": "insert/update maintenance path for associative Role structures",
        "status": "available",
    },
    "QG9_TopRatedSeriesByGenre": {
        "scope": "detailed",
        "experiment": "IMDb QG9 validation",
        "files": [
            "analysis/generated/query_plan/imdb/qg9_validation/query_plan_summary_qg9_all_sfs.csv",
            "analysis/generated/query_plan/imdb/qg9_validation/query_plan_components_qg9_all_sfs.csv",
            "analysis/generated/query_plan/imdb/qg9_validation/query_plan_summary_results_qg9_sf025_sf050.csv",
            "analysis/generated/query_plan/imdb/qg9_validation/query_plan_summary_results_qg9_sf1.csv",
        ],
        "signal": "generic watchitems root versus specialized series root",
        "status": "available",
    },
    "QG10_AdvancedSearchWatchItems": {
        "scope": "group-level",
        "experiment": "IMDb Group A light/no-roles query-plan",
        "files": [
            "analysis/generated/query_plan/imdb/group_A_light_no_roles/query_plan_summary_results_group_A.csv",
            "analysis/generated/query_plan/imdb/group_A_light_no_roles/query_plan_component_results_group_A.csv",
        ],
        "signal": "multi-predicate filtered search over WatchItem-oriented candidates",
        "status": "available",
    },

    # FIBEN
    "Q1_CompanyProfileIBM": {
        "scope": "dataset-level",
        "experiment": "FIBEN read-query explain-plan validation",
        "files": [
            "analysis/generated/query_plan/fiben/fiben_query_plan_summary_all.csv",
            "analysis/generated/query_plan/fiben/fiben_query_plan_components_all.csv",
        ],
        "signal": "selective company-root lookup; control can be competitive at small absolute latency",
        "status": "available",
    },
    "Q2_CompanyWithIndustryCountryAndListedSecurities": {
        "scope": "detailed/dataset-level",
        "experiment": "FIBEN Q2 detailed query-plan validation",
        "files": [
            "analysis/generated/query_plan/fiben/fiben_query_plan_summary_all.csv",
            "analysis/generated/query_plan/fiben/fiben_query_plan_components_all.csv",
        ],
        "signal": "indexed corporation lookup plus descriptor/security dereferencing",
        "status": "available",
    },
    "Q3_SecuritiesHeldInEachFinancialServiceAccount": {
        "scope": "dataset-level",
        "experiment": "FIBEN read-query explain-plan validation",
        "files": [
            "analysis/generated/query_plan/fiben/fiben_query_plan_summary_all.csv",
            "analysis/generated/query_plan/fiben/fiben_query_plan_components_all.csv",
        ],
        "signal": "holding/security/account traversal",
        "status": "available",
    },
    "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity": {
        "scope": "dataset-level",
        "experiment": "FIBEN read-query explain-plan validation",
        "files": [
            "analysis/generated/query_plan/fiben/fiben_query_plan_summary_all.csv",
            "analysis/generated/query_plan/fiben/fiben_query_plan_components_all.csv",
        ],
        "signal": "person-account-holding-security-company traversal",
        "status": "available",
    },
    "Q5_ReportsAndMetricDataOfCompany": {
        "scope": "dataset-level",
        "experiment": "FIBEN read-query explain-plan validation",
        "files": [
            "analysis/generated/query_plan/fiben/fiben_query_plan_summary_all.csv",
            "analysis/generated/query_plan/fiben/fiben_query_plan_components_all.csv",
        ],
        "signal": "analytical report hierarchy traversal",
        "status": "available",
    },
    "Q6_TechUSListedSecuritiesWithHighLastTradedValue": {
        "scope": "dataset-level",
        "experiment": "FIBEN read-query explain-plan validation",
        "files": [
            "analysis/generated/query_plan/fiben/fiben_query_plan_summary_all.csv",
            "analysis/generated/query_plan/fiben/fiben_query_plan_components_all.csv",
        ],
        "signal": "filtered listed-security and market-value access",
        "status": "available",
    },
    "Q7_PersonsWhoBoughtMoreIBMThanSold": {
        "scope": "dataset-level",
        "experiment": "FIBEN read-query explain-plan validation",
        "files": [
            "analysis/generated/query_plan/fiben/fiben_query_plan_summary_all.csv",
            "analysis/generated/query_plan/fiben/fiben_query_plan_components_all.csv",
        ],
        "signal": "transaction aggregation over buy/sell activity",
        "status": "available",
    },
    "Q8_IBMTransactionsBelowAverageSellingPrice": {
        "scope": "dataset-level",
        "experiment": "FIBEN read-query explain-plan validation",
        "files": [
            "analysis/generated/query_plan/fiben/fiben_query_plan_summary_all.csv",
            "analysis/generated/query_plan/fiben/fiben_query_plan_components_all.csv",
        ],
        "signal": "transaction filtering against aggregate selling-price threshold",
        "status": "available",
    },
    "Q9_PersonsWhoBoughtAndSoldSameStock": {
        "scope": "dataset-level",
        "experiment": "FIBEN read-query explain-plan validation",
        "files": [
            "analysis/generated/query_plan/fiben/fiben_query_plan_summary_all.csv",
            "analysis/generated/query_plan/fiben/fiben_query_plan_components_all.csv",
        ],
        "signal": "transaction overlap between buy and sell paths",
        "status": "available",
    },
    "Q10_CreateAccountHoldingAndBuyTransaction": {
        "scope": "write/skipped-read-explain",
        "experiment": "FIBEN Q10 write workload",
        "files": [
            "analysis/generated/query_plan/fiben/fiben_query_plan_summary_all.csv",
            "analysis/generated/query_plan/fiben/fiben_query_plan_components_all.csv",
        ],
        "signal": "insert/update case; read-style executionStats skipped or reported separately",
        "status": "skipped_read_style_explain",
    },

    # LDBC
    "IC7_RecentLikers": {
        "scope": "detailed",
        "experiment": "LDBC SNB physical IC7 query-plan",
        "files": [
            "analysis/generated/ldbc_snb_physical_query_plan/ldbc_snb_physical_query_plan_component_results.csv",
            "analysis/generated/ldbc_snb_physical_query_plan/ldbc_snb_physical_query_plan_candidate_summary.csv",
            "analysis/generated/ldbc_snb_physical_query_plan/ldbc_snb_physical_hot_winners_with_query_plan.csv",
            "analysis/generated/ldbc_snb_physical_query_plan/ldbc_snb_physical_ic7_baseline_behavior.csv",
            "analysis/generated/ldbc_snb_physical_query_plan/ldbc_snb_physical_ic7_ablation_behavior.csv",
        ],
        "signal": "person-rooted access plus likes associative edge",
        "status": "available",
    },
    "Official IC/IS/INS aggregate": {
        "scope": "aggregate",
        "experiment": "LDBC SNB physical query-plan aggregate",
        "files": [
            "analysis/generated/ldbc_snb_physical_query_plan/ldbc_snb_physical_query_plan_component_results.csv",
            "analysis/generated/ldbc_snb_physical_query_plan/ldbc_snb_physical_query_plan_candidate_summary.csv",
            "analysis/generated/ldbc_snb_physical_query_plan/ldbc_snb_physical_query_plan_scale_summary.csv",
            "analysis/generated/ldbc_snb_physical_query_plan/ldbc_snb_physical_query_plan_coverage.csv",
            "analysis/generated/ldbc_snb_physical_query_plan/ldbc_snb_physical_query_plan_report.md",
        ],
        "signal": "official workload query-plan evidence across IC, IS, and INS operations",
        "status": "available",
    },
}

rows = []

for _, r in compact.iterrows():
    query_name = r["query_name"]
    info = mapping.get(query_name, {})

    files = info.get("files", [])
    missing = [p for p in files if not Path(p).exists()]
    existing = [p for p in files if Path(p).exists()]

    final_status = info.get("status", "not_mapped")
    if missing and final_status == "available":
        final_status = "mapped_but_some_files_missing"

    rows.append({
        "dataset": r["dataset"],
        "query_name": query_name,
        "semantic_family": r.get("semantic_family", ""),
        "query_plan_scope": info.get("scope", ""),
        "query_plan_experiment": info.get("experiment", ""),
        "main_physical_signal": info.get("signal", ""),
        "query_plan_files": " | ".join(files),
        "existing_files": len(existing),
        "missing_files": len(missing),
        "missing_file_list": " | ".join(missing),
        "status": final_status,
    })

clean = pd.DataFrame(rows)
clean.to_csv(OUT / "dke_query_plan_mapping_clean.csv", index=False)

# Update compact table with clean mapping
m = clean.set_index(["dataset", "query_name"])

compact["query_plan_scope"] = compact.apply(
    lambda x: m.loc[(x["dataset"], x["query_name"]), "query_plan_scope"]
    if (x["dataset"], x["query_name"]) in m.index else "",
    axis=1,
)
compact["query_plan_experiment"] = compact.apply(
    lambda x: m.loc[(x["dataset"], x["query_name"]), "query_plan_experiment"]
    if (x["dataset"], x["query_name"]) in m.index else "",
    axis=1,
)
compact["query_plan_signal"] = compact.apply(
    lambda x: m.loc[(x["dataset"], x["query_name"]), "main_physical_signal"]
    if (x["dataset"], x["query_name"]) in m.index else "",
    axis=1,
)
compact["query_plan_evidence"] = compact.apply(
    lambda x: m.loc[(x["dataset"], x["query_name"]), "status"]
    if (x["dataset"], x["query_name"]) in m.index else "",
    axis=1,
)

compact.to_csv(OUT / "dke_extended_table15_compact_with_queryplan_clean.csv", index=False)

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

latex_cols = [
    "dataset",
    "query_name",
    "query_plan_scope",
    "query_plan_experiment",
    "main_physical_signal",
    "status",
]

lines = []
lines.append("\\begin{longtable}{llllll}")
lines.append("\\caption{Mapping between extended results and query-plan evidence.}\\\\")
lines.append("\\toprule")
lines.append("Dataset & Query & Scope & Query-plan experiment & Main physical signal & Status \\\\")
lines.append("\\midrule")
lines.append("\\endfirsthead")
lines.append("\\toprule")
lines.append("Dataset & Query & Scope & Query-plan experiment & Main physical signal & Status \\\\")
lines.append("\\midrule")
lines.append("\\endhead")

for _, r in clean[latex_cols].iterrows():
    lines.append(" & ".join(latex_escape(v) for v in r.tolist()) + " \\\\")

lines.append("\\bottomrule")
lines.append("\\end{longtable}")

(OUT / "dke_query_plan_mapping_clean.tex").write_text("\n".join(lines), encoding="utf-8")

print("Generated:")
print(" - analysis/generated/dke_query_plan_mapping_clean.csv")
print(" - analysis/generated/dke_extended_table15_compact_with_queryplan_clean.csv")
print(" - analysis/generated/dke_query_plan_mapping_clean.tex")
print()
print(clean[[
    "dataset",
    "query_name",
    "query_plan_scope",
    "existing_files",
    "missing_files",
    "status",
]].to_string(index=False))
