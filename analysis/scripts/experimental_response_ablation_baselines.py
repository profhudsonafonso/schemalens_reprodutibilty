from pathlib import Path
import pandas as pd


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return pd.read_csv(path, encoding="utf-8-sig")


def fmt(value, digits=4):
    if value is None or pd.isna(value):
        return "NA"
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def fmt_cases(available, total):
    try:
        return f"{int(available)}/{int(total)}"
    except Exception:
        return "NA"


def markdown_table(df: pd.DataFrame, columns, headers=None):
    if headers is None:
        headers = columns

    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for _, row in df.iterrows():
        values = []
        for col in columns:
            values.append(str(row.get(col, "")))
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


def add_interpretation_column(df: pd.DataFrame, kind: str):
    df = df.copy()

    baseline_notes = {
        "schema_lens": "Explainable semantic/workload-aware reduction.",
        "random_k": "Statistical sanity check; not explainable.",
        "always_reference": "Reference-only strategy; misses embedding/hybrid cases.",
        "always_embed": "Embedding-only strategy; misses reference-sensitive cases.",
        "depth_only": "Uses depth only; ignores semantic/update/sharedness signals.",
        "relationship_type_only": "Uses relationship type only; ignores other analytical signals.",
    }

    ablation_notes = {
        "full_schema_lens": "Complete analytical matrix.",
        "no_depth": "Removes depth-sensitive activation evidence.",
        "no_relationship_semantics": "Removes relationship-semantics evidence.",
        "no_relationship_semantics_no_depth": "Removes both semantic and depth evidence.",
        "no_residual_traversal": "Removes Re, DeltaR, and residual traversal evidence.",
        "no_sharedness": "Removes observed sharedness evidence.",
        "no_update_volatility": "Removes update/write-pressure evidence.",
    }

    if kind == "baseline":
        df["interpretation"] = df["baseline"].map(baseline_notes).fillna("")
    elif kind == "ablation":
        df["interpretation"] = df["ablation_variant"].map(ablation_notes).fillna("")
    else:
        df["interpretation"] = ""

    return df


def prepare_baseline_summary(df: pd.DataFrame):
    df = df.copy()

    order = [
        "schema_lens",
        "random_k",
        "always_reference",
        "always_embed",
        "depth_only",
        "relationship_type_only",
    ]

    df["order"] = df["baseline"].apply(lambda x: order.index(x) if x in order else 999)
    df = df.sort_values("order")

    out = pd.DataFrame()
    out["Method"] = df["baseline"]
    out["Available cases"] = [
        fmt_cases(a, t) for a, t in zip(df["available_cases"], df["total_cases"])
    ]
    out["Top-1"] = df["top1_preservation_rate"].apply(fmt)
    out["Top-3"] = df["top3_preservation_rate"].apply(fmt)
    out["Near-best"] = df["near_best_preservation_rate"].apply(fmt)
    out["Mean regret"] = df["mean_relative_regret"].apply(fmt)
    out["Median regret"] = df["median_relative_regret"].apply(fmt)

    df = add_interpretation_column(df, "baseline")
    out["Interpretation"] = df["interpretation"]

    return out


def prepare_baseline_hot_summary(df: pd.DataFrame):
    df = df.copy()

    order = [
        "schema_lens",
        "random_k",
        "always_reference",
        "depth_only",
        "relationship_type_only",
        "always_embed",
    ]

    df["order"] = df["baseline"].apply(lambda x: order.index(x) if x in order else 999)
    df = df.sort_values("order")

    out = pd.DataFrame()
    out["Method"] = df["baseline"]
    out["Available hot cases"] = [
        fmt_cases(a, t) for a, t in zip(df["available_cases"], df["total_cases"])
    ]
    out["Top-1"] = df["top1_preservation_rate"].apply(fmt)
    out["Near-best"] = df["near_best_preservation_rate"].apply(fmt)
    out["Mean regret"] = df["mean_relative_regret"].apply(fmt)

    df = add_interpretation_column(df, "baseline")
    out["Interpretation"] = df["interpretation"]

    return out


def prepare_ablation_summary(df: pd.DataFrame, hot=False):
    df = df.copy()

    order = [
        "full_schema_lens",
        "no_depth",
        "no_relationship_semantics",
        "no_relationship_semantics_no_depth",
        "no_residual_traversal",
        "no_sharedness",
        "no_update_volatility",
    ]

    df["order"] = df["ablation_variant"].apply(lambda x: order.index(x) if x in order else 999)
    df = df.sort_values("order")

    out = pd.DataFrame()
    out["Variant"] = df["ablation_variant"]

    if hot:
        out["Available hot cases"] = [
            fmt_cases(a, t) for a, t in zip(df["available_cases"], df["total_cases"])
        ]
    else:
        out["Available cases"] = [
            fmt_cases(a, t) for a, t in zip(df["available_cases"], df["total_cases"])
        ]

    out["Top-1"] = df["top1_preservation_rate"].apply(fmt)

    if not hot and "top3_preservation_rate" in df.columns:
        out["Top-3"] = df["top3_preservation_rate"].apply(fmt)

    out["Near-best"] = df["near_best_preservation_rate"].apply(fmt)
    out["Mean regret"] = df["mean_relative_regret"].apply(fmt)

    if not hot and "median_relative_regret" in df.columns:
        out["Median regret"] = df["median_relative_regret"].apply(fmt)

    df = add_interpretation_column(df, "ablation")
    out["Interpretation"] = df["interpretation"]

    return out


def prepare_hot_dataset_ablation(df: pd.DataFrame):
    df = df.copy()

    keep_variants = [
        "full_schema_lens",
        "no_relationship_semantics",
        "no_relationship_semantics_no_depth",
        "no_residual_traversal",
    ]

    df = df[df["ablation_variant"].isin(keep_variants)].copy()

    dataset_order = {"fiben": 1, "imdb": 2, "ldbc_snb": 3}
    variant_order = {v: i for i, v in enumerate(keep_variants)}

    df["dataset_order"] = df["dataset"].map(dataset_order).fillna(999)
    df["variant_order"] = df["ablation_variant"].map(variant_order).fillna(999)
    df = df.sort_values(["dataset_order", "variant_order"])

    out = pd.DataFrame()
    out["Dataset"] = df["dataset"]
    out["Variant"] = df["ablation_variant"]
    out["Top-1"] = df["top1_preservation_rate"].apply(fmt)
    out["Near-best"] = df["near_best_preservation_rate"].apply(fmt)
    out["Mean regret"] = df["mean_relative_regret"].apply(fmt)

    return out


def extract_random_k_diagnostics(comparison_summary: pd.DataFrame):
    lines = []

    if comparison_summary.empty:
        return ["Random-k diagnostics file is empty."]

    overall = comparison_summary[comparison_summary["level"] == "overall"]

    if not overall.empty:
        row = overall.iloc[0]
        lines.append(
            f"- Overall, SchemaLens Top-1 = {fmt(row.get('schema_lens_mean_top1'))}, "
            f"random-k Top-1 = {fmt(row.get('random_k_mean_top1_probability'))}."
        )
        lines.append(
            f"- Overall, SchemaLens mean regret = {fmt(row.get('schema_lens_mean_regret'))}, "
            f"random-k expected regret = {fmt(row.get('random_k_mean_expected_regret'))}."
        )
        lines.append(
            f"- Case-level Top-1 comparison: SchemaLens higher in "
            f"{int(row.get('schema_lens_higher_top1_cases', 0))} cases, "
            f"random-k higher in {int(row.get('random_k_higher_top1_cases', 0))} cases, "
            f"ties in {int(row.get('top1_tie_cases', 0))} cases."
        )

    ldbc = comparison_summary[
        (comparison_summary.get("level") == "dataset") &
        (comparison_summary.get("dataset") == "ldbc_snb")
    ]

    if not ldbc.empty:
        row = ldbc.iloc[0]
        lines.append(
            f"- On LDBC SNB, SchemaLens Top-1 = {fmt(row.get('schema_lens_mean_top1'))}, "
            f"random-k Top-1 = {fmt(row.get('random_k_mean_top1_probability'))}; "
            f"SchemaLens mean regret = {fmt(row.get('schema_lens_mean_regret'))}, "
            f"random-k expected regret = {fmt(row.get('random_k_mean_expected_regret'))}."
        )

    ldbc_hot = comparison_summary[
        (comparison_summary.get("level") == "dataset+run_phase") &
        (comparison_summary.get("dataset") == "ldbc_snb") &
        (comparison_summary.get("run_phase") == "hot")
    ]

    if not ldbc_hot.empty:
        row = ldbc_hot.iloc[0]
        lines.append(
            f"- On LDBC SNB hot runs, SchemaLens Top-1 = {fmt(row.get('schema_lens_mean_top1'))}, "
            f"random-k Top-1 = {fmt(row.get('random_k_mean_top1_probability'))}; "
            f"SchemaLens mean regret = {fmt(row.get('schema_lens_mean_regret'))}, "
            f"random-k expected regret = {fmt(row.get('random_k_mean_expected_regret'))}."
        )

    return lines


def build_report(repo_root: Path):
    generated = repo_root / "analysis" / "generated"

    baseline_summary = read_csv(generated / "baseline_performance_summary.csv")
    baseline_hot = read_csv(generated / "baseline_performance_summary_hot.csv")
    baseline_by_dataset_hot = read_csv(generated / "baseline_performance_by_dataset_hot.csv")
    random_k_summary = read_csv(generated / "schema_lens_vs_random_k_summary.csv")

    ablation_summary = read_csv(generated / "ablation_performance_summary.csv")
    ablation_hot = read_csv(generated / "ablation_performance_summary_hot.csv")
    ablation_by_dataset_hot = read_csv(generated / "ablation_performance_by_dataset_hot.csv")

    query_metadata = read_csv(generated / "query_analytical_metadata_all_datasets.csv")
    activation = read_csv(generated / "query_class_activation_all_datasets.csv")
    benchmark_selection = read_csv(generated / "benchmark_configuration_selection_all_datasets.csv")

    lines = []

    lines.append("# Advisor Experimental Response - Baselines and Ablation")
    lines.append("")
    lines.append("This document summarizes the additional experimental analyses added in response to the advisor comments.")
    lines.append("")
    lines.append("The goal is to move the evaluation from a descriptive workflow demonstration to a deeper analysis of:")
    lines.append("")
    lines.append("1. whether SchemaLens performs better than simple reduction baselines;")
    lines.append("2. whether the analytical variables used by SchemaLens actually matter;")
    lines.append("3. how to interpret random-k;")
    lines.append("4. what evidence should be included later in the paper.")
    lines.append("")

    lines.append("## 1. What was added")
    lines.append("")
    added = pd.DataFrame(
        [
            {
                "Advisor concern": "Evaluation was too descriptive.",
                "Action taken": "Added baseline comparison and ablation study over all datasets.",
            },
            {
                "Advisor concern": "Need simple baselines.",
                "Action taken": "Added random-k, always-reference, always-embed, depth-only, and relationship-type-only.",
            },
            {
                "Advisor concern": "Need to show which analytical variables matter.",
                "Action taken": "Added ablations removing relationship semantics, depth, residual traversal, sharedness, and update volatility.",
            },
            {
                "Advisor concern": "Repository had aggregate outputs only for one dataset.",
                "Action taken": "Added aggregate outputs for IMDb, FIBEN, and LDBC SNB.",
            },
            {
                "Advisor concern": "Need reproducible analysis.",
                "Action taken": "Added scripts under analysis/scripts and generated outputs under analysis/generated.",
            },
        ]
    )
    lines.append(markdown_table(added, list(added.columns)))
    lines.append("")

    lines.append("## 2. Normalized analysis scope")
    lines.append("")
    scope = pd.DataFrame(
        [
            {
                "Normalized file": "query_analytical_metadata_all_datasets.csv",
                "Rows": len(query_metadata),
                "Meaning": "One row per query with real methodology variables.",
            },
            {
                "Normalized file": "query_class_activation_all_datasets.csv",
                "Rows": len(activation),
                "Meaning": "Normalized G-class activation output.",
            },
            {
                "Normalized file": "benchmark_configuration_selection_all_datasets.csv",
                "Rows": len(benchmark_selection),
                "Meaning": "Links query, configuration, G-class, and benchmark group.",
            },
        ]
    )
    lines.append(markdown_table(scope, list(scope.columns)))
    lines.append("")

    dataset_scope = query_metadata.groupby("dataset")["query_name"].nunique().reset_index()
    dataset_scope.columns = ["Dataset", "Number of queries"]
    lines.append("Query coverage by dataset:")
    lines.append("")
    lines.append(markdown_table(dataset_scope, list(dataset_scope.columns)))
    lines.append("")

    lines.append("## 3. Baseline comparison - all runs")
    lines.append("")
    baseline_table = prepare_baseline_summary(baseline_summary)
    lines.append(markdown_table(baseline_table, list(baseline_table.columns)))
    lines.append("")
    lines.append("Interpretation:")
    lines.append("")
    lines.append(
        "SchemaLens clearly outperforms the deterministic heuristic baselines. "
        "The deterministic baselines lose Top-1 and near-best preservation because they use only one simple rule, "
        "such as always referencing, always embedding, using only depth, or using only relationship type."
    )
    lines.append("")
    lines.append(
        "Random-k is competitive in the aggregate because it samples the same number of measured configuration classes as SchemaLens. "
        "Therefore, when the measured space is small or SchemaLens selects several classes, random-k has a high probability of including the global best by chance."
    )
    lines.append("")

    lines.append("## 4. Baseline comparison - hot runs")
    lines.append("")
    baseline_hot_table = prepare_baseline_hot_summary(baseline_hot)
    lines.append(markdown_table(baseline_hot_table, list(baseline_hot_table.columns)))
    lines.append("")
    lines.append(
        "The hot-run table is the best candidate for the paper because the paper mainly interprets hot p95 latency."
    )
    lines.append("")

    lines.append("## 5. Random-k diagnostic")
    lines.append("")
    for item in extract_random_k_diagnostics(random_k_summary):
        lines.append(item)
    lines.append("")
    lines.append(
        "The correct interpretation is not that random selection is a better design method. "
        "Random-k is a statistical sanity check: it asks what happens if we select the same number of measured classes without using any semantic explanation."
    )
    lines.append("")
    lines.append(
        "SchemaLens remains different because it provides an explainable and reproducible reduction based on EER/workload evidence. "
        "On the official LDBC SNB workload, SchemaLens also slightly outperforms random-k in Top-1 preservation and regret."
    )
    lines.append("")

    lines.append("## 6. Ablation study - all runs")
    lines.append("")
    ablation_table = prepare_ablation_summary(ablation_summary, hot=False)
    lines.append(markdown_table(ablation_table, list(ablation_table.columns)))
    lines.append("")
    lines.append(
        "The all-run ablation shows that removing any major analytical component reduces preservation quality and increases regret."
    )
    lines.append("")

    lines.append("## 7. Ablation study - hot runs")
    lines.append("")
    ablation_hot_table = prepare_ablation_summary(ablation_hot, hot=True)
    lines.append(markdown_table(ablation_hot_table, list(ablation_hot_table.columns)))
    lines.append("")
    lines.append(
        "The hot-run ablation is especially useful for the paper. "
        "The full SchemaLens variant preserves near-best configurations in more than 92% of hot cases, "
        "while all ablated variants show lower Top-1 and near-best preservation."
    )
    lines.append("")

    lines.append("## 8. Dataset-level ablation - hot runs")
    lines.append("")
    dataset_ablation = prepare_hot_dataset_ablation(ablation_by_dataset_hot)
    lines.append(markdown_table(dataset_ablation, list(dataset_ablation.columns)))
    lines.append("")
    lines.append(
        "The LDBC SNB results are particularly important because this is the official workload. "
        "There, the complete SchemaLens variant almost always preserves the best or near-best configuration, "
        "while removing analytical components causes a large drop."
    )
    lines.append("")

    lines.append("## 9. Main conclusions for the advisor")
    lines.append("")
    lines.append("1. SchemaLens is stronger than deterministic heuristic baselines.")
    lines.append("")
    lines.append(
        "The deterministic baselines are weaker because each one uses only a single signal. "
        "SchemaLens combines relationship semantics, traversal structure, residual traversal, sharedness, and update volatility."
    )
    lines.append("")
    lines.append("2. Random-k should be kept, but interpreted carefully.")
    lines.append("")
    lines.append(
        "Random-k is useful as a sanity check, but it is not an explainable design method. "
        "It can perform well because it samples the same number of classes as SchemaLens."
    )
    lines.append("")
    lines.append("3. The ablation study supports the analytical matrix.")
    lines.append("")
    lines.append(
        "Removing relationship semantics, depth, residual traversal, sharedness, or update volatility consistently reduces Top-1 and near-best preservation. "
        "The strongest degradation occurs when relationship semantics and depth are removed together."
    )
    lines.append("")
    lines.append("4. Root-choice ablation should be reported as not executed in this simulation.")
    lines.append("")
    lines.append(
        "The current benchmark artifacts do not include alternative-root MongoDB configurations for all queries. "
        "A fair root-choice ablation would require generating and benchmarking additional candidates rooted at non-selected entities."
    )
    lines.append("")

    lines.append("## 10. Suggested text for the advisor response")
    lines.append("")
    lines.append("> I added two new experimental analyses to address the concern that the evaluation was too descriptive.")
    lines.append(">")
    lines.append("> First, I added a baseline comparison over the normalized aggregate benchmark outputs. The baselines include random-k, always-reference, always-embed, depth-only, and relationship-type-only strategies. This analysis does not rerun MongoDB benchmarks; it uses the measured p95 values already available in the aggregate outputs. SchemaLens clearly outperforms the deterministic heuristic baselines. Random-k is competitive in the aggregate because it samples the same number of measured configuration classes as SchemaLens, so it has a high probability of including the global best when the measured space is small. However, random-k has no semantic explanation. On the official LDBC SNB workload, SchemaLens slightly outperforms random-k in Top-1 preservation and regret.")
    lines.append(">")
    lines.append("> Second, I added an ablation study using real methodology variables extracted from the IMDb, FIBEN, and LDBC SNB artifacts. The ablation removes relationship semantics, depth, residual traversal, sharedness, and update volatility from the measured SchemaLens-selected space. The full SchemaLens variant achieves high Top-1 and near-best preservation on hot runs with low mean regret. All ablated variants perform substantially worse. The strongest degradation occurs when relationship semantics and depth are removed together. This supports the claim that the analytical matrix materially contributes to preserving best or near-best configurations.")
    lines.append("")

    lines.append("## 11. Recommended next steps")
    lines.append("")
    lines.append("1. Select which baseline table should go into the paper.")
    lines.append("2. Select which ablation table should go into the paper.")
    lines.append("3. Add a short paragraph explaining random-k as a statistical sanity check.")
    lines.append("4. Add a short paragraph explaining why root-choice ablation requires additional benchmark candidates.")
    lines.append("5. Add representative query-level explanations showing why specific configurations win.")
    lines.append("6. Decide what stays in the paper and what remains as supplementary repository material.")
    lines.append("")

    return "\n".join(lines)


def main():
    repo_root = Path(__file__).resolve().parents[2]
    output_path = repo_root / "analysis" / "generated" / "advisor_experimental_response.md"

    report = build_report(repo_root)
    output_path.write_text(report, encoding="utf-8")

    print("Advisor experimental response generated.")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()