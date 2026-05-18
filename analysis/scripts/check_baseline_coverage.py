from pathlib import Path
import pandas as pd


REFERENCE_CLASSES = {"CONTROL", "G0", "G3", "G6", "G7"}
EMBED_CLASSES = {"G2", "G4", "G5", "G8", "G9"}

RELATIONSHIP_TYPE_RULES = {
    "local": {"CONTROL", "G0", "G1", "G2"},
    "association": {"G0", "G2", "G3"},
    "associative": {"G4", "G5", "G6"},
    "containment": {"G7", "G8", "G9"},
}

DEFAULT_QUERY_METADATA = [
    # IMDb
    ("imdb", "QG1_WatchItemById", "local", 0, "confirmed"),
    ("imdb", "QG2_WatchItemByTitle", "local", 0, "confirmed"),
    ("imdb", "QG3_RecommendationByGenreAndSubtype", "association", 1, "confirmed"),
    ("imdb", "QG4_AllPersonsOfTypeForWatchItem", "associative", 2, "confirmed"),
    ("imdb", "QG5_AllPersonsForEpisodesOfSeries", "associative", 2, "confirmed"),
    ("imdb", "QG6_EpisodesOfSeries", "containment", 1, "confirmed"),
    ("imdb", "QG7_UpdateWatchItemMetadata", "local", 0, "confirmed"),
    ("imdb", "QG8_AddPersonRoleToWatchItem", "associative", 2, "confirmed"),
    ("imdb", "QG9_TopRatedSeriesByGenre", "association", 1, "confirmed"),
    ("imdb", "QG10_AdvancedSearchWatchItems", "association", 1, "confirmed"),

    # FIBEN
    ("fiben", "Q1_CompanyProfileIBM", "local", 0, "confirmed"),
    ("fiben", "Q2_CompanyWithIndustryCountryAndListedSecurities", "association", 1, "confirmed"),
    ("fiben", "Q3_SecuritiesHeldInEachFinancialServiceAccount", "associative", 2, "confirmed"),
    ("fiben", "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity", "associative", 4, "confirmed"),
    ("fiben", "Q5_ReportsAndMetricDataOfCompany", "containment", 3, "confirmed"),
    ("fiben", "Q6_TechUSListedSecuritiesWithHighLastTradedValue", "association", 1, "confirmed"),
    ("fiben", "Q7_PersonsWhoBoughtMoreIBMThanSold", "associative", 2, "confirmed"),
    ("fiben", "Q8_IBMTransactionsBelowAverageSellingPrice", "associative", 2, "confirmed"),
    ("fiben", "Q9_PersonsWhoBoughtAndSoldSameStock", "associative", 2, "confirmed"),
    ("fiben", "Q10_CreateAccountHoldingAndBuyTransaction", "associative", 2, "confirmed"),

    # LDBC SNB: provisional metadata for coverage checking.
    # These labels should be reviewed before using depth-only or relationship-type-only baseline results in the paper.
    ("ldbc_snb", "IC1_TransitiveFriendsWithName", "association", 2, "provisional"),
    ("ldbc_snb", "IC2_RecentMessagesByFriends", "association", 2, "provisional"),
    ("ldbc_snb", "IC3_FriendsAndFriendsOfFriendsInCountries", "association", 3, "provisional"),
    ("ldbc_snb", "IC4_NewTopics", "association", 2, "provisional"),
    ("ldbc_snb", "IC5_NewGroups", "association", 2, "provisional"),
    ("ldbc_snb", "IC6_TagCoOccurrence", "association", 2, "provisional"),
    ("ldbc_snb", "IC7_RecentLikers", "association", 2, "provisional"),
    ("ldbc_snb", "INS1_AddPerson", "local", 0, "provisional"),
    ("ldbc_snb", "INS2_AddLikeToPost", "association", 1, "provisional"),
    ("ldbc_snb", "INS3_AddLikeToComment", "association", 1, "provisional"),
    ("ldbc_snb", "INS4_AddForum", "local", 0, "provisional"),
    ("ldbc_snb", "INS5_AddForumMembership", "association", 1, "provisional"),
    ("ldbc_snb", "INS6_AddPost", "containment", 1, "provisional"),
    ("ldbc_snb", "INS7_AddComment", "containment", 1, "provisional"),
    ("ldbc_snb", "INS8_AddFriendship", "association", 1, "provisional"),
    ("ldbc_snb", "IS1_ProfileOfPerson", "local", 0, "provisional"),
    ("ldbc_snb", "IS2_RecentMessagesOfPerson", "association", 1, "provisional"),
    ("ldbc_snb", "IS3_FriendsOfPerson", "association", 1, "provisional"),
    ("ldbc_snb", "IS4_ContentOfMessage", "local", 0, "provisional"),
    ("ldbc_snb", "IS5_CreatorOfMessage", "association", 1, "provisional"),
    ("ldbc_snb", "IS6_ForumOfMessage", "association", 1, "provisional"),
    ("ldbc_snb", "IS7_RepliesOfMessage", "containment", 1, "provisional"),
]


def depth_only_classes(depth):
    if pd.isna(depth):
        return set()

    depth = int(depth)

    if depth <= 1:
        return {"G2", "G8", "G9"}

    if depth == 2:
        return {"G3", "G4", "G5", "G6", "G9"}

    return {"G0", "G3", "G6", "G7"}


def write_default_metadata_if_missing(path: Path):
    if path.exists():
        return

    rows = []
    for dataset, query_name, dominant_semantics, depth, status in DEFAULT_QUERY_METADATA:
        rows.append(
            {
                "dataset": dataset,
                "query_name": query_name,
                "dominant_semantics": dominant_semantics,
                "depth_D": depth,
                "metadata_status": status,
            }
        )

    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8")


def load_metadata(path: Path) -> pd.DataFrame:
    write_default_metadata_if_missing(path)

    metadata = pd.read_csv(path, encoding="utf-8-sig")

    required = {
        "dataset",
        "query_name",
        "dominant_semantics",
        "depth_D",
        "metadata_status",
    }

    missing = required - set(metadata.columns)
    if missing:
        raise ValueError(f"Metadata file is missing columns: {sorted(missing)}")

    metadata["dataset"] = metadata["dataset"].astype(str)
    metadata["query_name"] = metadata["query_name"].astype(str)
    metadata["dominant_semantics"] = metadata["dominant_semantics"].astype(str).str.lower()
    metadata["depth_D"] = pd.to_numeric(metadata["depth_D"], errors="coerce")
    metadata["metadata_status"] = metadata["metadata_status"].astype(str)

    return metadata


def classes_to_string(classes):
    if not classes:
        return ""
    return "|".join(sorted(classes))


def string_to_classes(value):
    if pd.isna(value):
        return set()

    value = str(value).strip()
    if value == "":
        return set()

    return {x.strip().upper() for x in value.split("|") if x.strip()}


def compute_case_table(df: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    rows = []
    group_cols = ["dataset", "scale_label", "query_name", "run_phase"]

    for keys, group in df.groupby(group_cols):
        dataset, scale_label, query_name, run_phase = keys

        available_classes = set(
            group["g_class"]
            .dropna()
            .astype(str)
            .str.upper()
            .unique()
        )

        available_config_count = group["config_id"].nunique()

        schema_lens_classes = set(
            group.loc[group["benchmark_group"] != "control", "g_class"]
            .dropna()
            .astype(str)
            .str.upper()
            .unique()
        )

        metadata_match = metadata[
            (metadata["dataset"] == dataset)
            & (metadata["query_name"] == query_name)
        ]

        if len(metadata_match) == 0:
            dominant_semantics = ""
            depth_D = None
            metadata_status = "missing"
        else:
            metadata_row = metadata_match.iloc[0]
            dominant_semantics = metadata_row["dominant_semantics"]
            depth_D = metadata_row["depth_D"]
            metadata_status = metadata_row["metadata_status"]

        rows.append(
            {
                "dataset": dataset,
                "scale_label": scale_label,
                "query_name": query_name,
                "run_phase": run_phase,
                "available_config_count": available_config_count,
                "available_g_classes": classes_to_string(available_classes),
                "schema_lens_g_classes": classes_to_string(schema_lens_classes),
                "schema_lens_class_count": len(schema_lens_classes),
                "dominant_semantics": dominant_semantics,
                "depth_D": depth_D,
                "metadata_status": metadata_status,
            }
        )

    return pd.DataFrame(rows)


def baseline_desired_classes(baseline_name, case_row):
    dominant_semantics = str(case_row.get("dominant_semantics", "")).lower()
    depth_D = case_row.get("depth_D")

    if baseline_name == "random_k":
        return set()

    if baseline_name == "always_reference":
        return set(REFERENCE_CLASSES)

    if baseline_name == "always_embed":
        return set(EMBED_CLASSES)

    if baseline_name == "depth_only":
        return depth_only_classes(depth_D)

    if baseline_name == "relationship_type_only":
        return set(RELATIONSHIP_TYPE_RULES.get(dominant_semantics, set()))

    raise ValueError(f"Unknown baseline: {baseline_name}")


def compute_coverage(case_df: pd.DataFrame) -> pd.DataFrame:
    baselines = [
        "random_k",
        "always_reference",
        "always_embed",
        "depth_only",
        "relationship_type_only",
    ]

    rows = []

    for _, case in case_df.iterrows():
        available = string_to_classes(case["available_g_classes"])

        for baseline in baselines:
            note = ""

            if baseline == "random_k":
                desired = set(available)
                metadata_needed = False
                note = "Random-k samples from available measured classes; coverage is always defined."
            else:
                desired = baseline_desired_classes(baseline, case)
                metadata_needed = baseline in {"depth_only", "relationship_type_only"}

            if metadata_needed and case["metadata_status"] == "missing":
                selected_available = set()
                missing = set(desired)
                coverage_ratio = None
                coverage_status = "metadata_missing"
            else:
                selected_available = desired & available
                missing = desired - available

                if len(desired) == 0:
                    coverage_ratio = None
                    coverage_status = "no_desired_classes"
                else:
                    coverage_ratio = len(selected_available) / len(desired)

                    if len(selected_available) == len(desired):
                        coverage_status = "full"
                    elif len(selected_available) == 0:
                        coverage_status = "none"
                    else:
                        coverage_status = "partial"

            rows.append(
                {
                    "dataset": case["dataset"],
                    "scale_label": case["scale_label"],
                    "query_name": case["query_name"],
                    "run_phase": case["run_phase"],
                    "baseline": baseline,
                    "metadata_status": case["metadata_status"],
                    "dominant_semantics": case["dominant_semantics"],
                    "depth_D": case["depth_D"],
                    "available_g_classes": case["available_g_classes"],
                    "desired_g_classes": classes_to_string(desired),
                    "selected_available_g_classes": classes_to_string(selected_available),
                    "missing_g_classes": classes_to_string(missing),
                    "desired_count": len(desired),
                    "selected_available_count": len(selected_available),
                    "coverage_ratio": coverage_ratio,
                    "coverage_status": coverage_status,
                    "note": note,
                }
            )

    return pd.DataFrame(rows)


def summarize_coverage(coverage_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        coverage_df.groupby(["baseline", "coverage_status"])
        .size()
        .reset_index(name="cases")
    )

    pivot = summary.pivot_table(
        index="baseline",
        columns="coverage_status",
        values="cases",
        fill_value=0,
        aggfunc="sum",
    ).reset_index()

    for col in ["full", "partial", "none", "metadata_missing", "no_desired_classes"]:
        if col not in pivot.columns:
            pivot[col] = 0

    ratio_summary = (
        coverage_df.dropna(subset=["coverage_ratio"])
        .groupby("baseline")["coverage_ratio"]
        .mean()
        .reset_index(name="mean_coverage_ratio")
    )

    out = pivot.merge(ratio_summary, on="baseline", how="left")

    count_summary = (
        coverage_df.groupby("baseline")
        .size()
        .reset_index(name="total_cases")
    )

    out = count_summary.merge(out, on="baseline", how="left")

    out["usable_cases"] = out["full"] + out["partial"]
    out["unavailable_cases"] = (
        out["none"] + out["metadata_missing"] + out["no_desired_classes"]
    )
    out["usable_ratio"] = out["usable_cases"] / out["total_cases"]

    out = out[
        [
            "baseline",
            "total_cases",
            "full",
            "partial",
            "none",
            "metadata_missing",
            "no_desired_classes",
            "usable_cases",
            "unavailable_cases",
            "usable_ratio",
            "mean_coverage_ratio",
        ]
    ]

    return out.sort_values("baseline")


def build_report(case_df, coverage_df, summary_df, output_dir: Path, repo_root: Path) -> str:
    lines = []

    lines.append("# Baseline Coverage Report")
    lines.append("")
    lines.append(
        "This report checks whether the baseline strategies select configuration classes "
        "that are available in the measured aggregate benchmark outputs."
    )
    lines.append("")
    lines.append("This step does not compare latency and does not simulate baseline performance.")
    lines.append("It only checks coverage.")
    lines.append("")

    lines.append("## Output files")
    for name in [
        "available_g_classes_by_query.csv",
        "baseline_coverage_by_case.csv",
        "baseline_coverage_summary.csv",
        "missing_baseline_candidates.csv",
        "query_metadata_template.csv",
        "baseline_coverage_report.txt",
    ]:
        path = output_dir / name
        lines.append(f"- {path.relative_to(repo_root).as_posix()}")

    lines.append("")
    lines.append("## Total query-scale-phase cases")
    lines.append(str(len(case_df)))

    lines.append("")
    lines.append("## Cases by dataset")
    for dataset, count in case_df["dataset"].value_counts().sort_index().items():
        lines.append(f"- {dataset}: {count}")

    lines.append("")
    lines.append("## Coverage summary")
    for _, row in summary_df.iterrows():
        lines.append(
            f"- {row['baseline']}: "
            f"total={row['total_cases']}, "
            f"full={row['full']}, "
            f"partial={row['partial']}, "
            f"none={row['none']}, "
            f"metadata_missing={row['metadata_missing']}, "
            f"usable_cases={row['usable_cases']}, "
            f"unavailable_cases={row['unavailable_cases']}, "
            f"usable_ratio={row['usable_ratio']:.4f}, "
            f"mean_coverage_ratio={row['mean_coverage_ratio']:.4f}"
        )

    missing = coverage_df[
        (coverage_df["missing_g_classes"] != "")
        & (coverage_df["coverage_status"].isin(["partial", "none"]))
    ]

    lines.append("")
    lines.append("## Missing baseline candidates")
    lines.append(f"Rows with missing baseline classes: {len(missing)}")

    lines.append("")
    lines.append("## Interpretation")
    lines.append(
        "A baseline is considered usable for a query-scale-phase case when it selects "
        "at least one measured configuration class. Therefore, both full and partial "
        "coverage are usable for the next performance simulation step. Cases with none, "
        "metadata_missing, or no_desired_classes are unavailable for that baseline."
    )

    lines.append("")
    lines.append("## Important note")
    lines.append("The LDBC SNB query metadata is provisional in this coverage script.")
    lines.append(
        "It should be reviewed before using depth-only or relationship-type-only "
        "baseline results in the paper text."
    )

    return "\n".join(lines)


def main():
    repo_root = Path(__file__).resolve().parents[2]

    input_csv = repo_root / "analysis" / "generated" / "aggregate_results_all_datasets.csv"
    output_dir = repo_root / "analysis" / "generated"
    metadata_csv = output_dir / "query_metadata_template.csv"

    if not input_csv.exists():
        raise FileNotFoundError(
            f"Missing input file: {input_csv}. Run normalize_aggregate_outputs.py first."
        )

    df = pd.read_csv(input_csv, encoding="utf-8-sig")
    metadata = load_metadata(metadata_csv)

    case_df = compute_case_table(df, metadata)
    coverage_df = compute_coverage(case_df)
    summary_df = summarize_coverage(coverage_df)

    missing_df = coverage_df[
        (coverage_df["missing_g_classes"] != "")
        | (coverage_df["coverage_status"] == "metadata_missing")
    ].copy()

    case_path = output_dir / "available_g_classes_by_query.csv"
    coverage_path = output_dir / "baseline_coverage_by_case.csv"
    summary_path = output_dir / "baseline_coverage_summary.csv"
    missing_path = output_dir / "missing_baseline_candidates.csv"
    report_path = output_dir / "baseline_coverage_report.txt"

    case_df.to_csv(case_path, index=False, encoding="utf-8")
    coverage_df.to_csv(coverage_path, index=False, encoding="utf-8")
    summary_df.to_csv(summary_path, index=False, encoding="utf-8")
    missing_df.to_csv(missing_path, index=False, encoding="utf-8")

    report = build_report(case_df, coverage_df, summary_df, output_dir, repo_root)
    report_path.write_text(report, encoding="utf-8")

    print("Baseline coverage check completed.")
    print(f"Query-scale-phase cases: {len(case_df)}")
    print(f"Coverage rows: {len(coverage_df)}")
    print(f"Summary: {summary_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()