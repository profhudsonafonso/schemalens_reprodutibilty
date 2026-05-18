from pathlib import Path
import pandas as pd


def fmt_float(value, digits=4):
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def summarize_performance(perf_df: pd.DataFrame, group_cols):
    rows = []

    for keys, group in perf_df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)

        key_data = dict(zip(group_cols, keys))
        available = group[group["availability_status"] == "available"].copy()

        total_cases = len(group)
        available_cases = len(available)
        unavailable_cases = total_cases - available_cases

        if available_cases == 0:
            metrics = {
                "top1_preservation_rate": None,
                "top3_preservation_rate": None,
                "near_best_preservation_rate": None,
                "mean_relative_regret": None,
                "median_relative_regret": None,
                "max_relative_regret": None,
                "mean_baseline_best_p95": None,
                "mean_global_best_p95": None,
            }
        else:
            metrics = {
                "top1_preservation_rate": available["top1_preserved"].mean(),
                "top3_preservation_rate": available["top3_preserved"].mean(),
                "near_best_preservation_rate": available["near_best_preserved"].mean(),
                "mean_relative_regret": available["relative_regret"].mean(),
                "median_relative_regret": available["relative_regret"].median(),
                "max_relative_regret": available["relative_regret"].max(),
                "mean_baseline_best_p95": available["baseline_best_p95"].mean(),
                "mean_global_best_p95": available["global_best_p95"].mean(),
            }

        row = {
            **key_data,
            "total_cases": total_cases,
            "available_cases": available_cases,
            "unavailable_cases": unavailable_cases,
            "availability_ratio": available_cases / total_cases if total_cases else None,
            **metrics,
        }

        rows.append(row)

    return pd.DataFrame(rows)


def build_schema_lens_vs_random(perf_df: pd.DataFrame):
    key_cols = ["dataset", "scale_label", "query_name", "run_phase"]

    schema = perf_df[perf_df["baseline"] == "schema_lens"].copy()
    random_k = perf_df[perf_df["baseline"] == "random_k"].copy()

    schema_cols = key_cols + [
        "top1_preserved",
        "top3_preserved",
        "near_best_preserved",
        "relative_regret",
        "global_best_g_class",
        "global_best_p95",
        "baseline_best_g_class",
        "baseline_best_p95",
        "selected_g_classes",
    ]

    random_cols = key_cols + [
        "top1_preserved",
        "top3_preserved",
        "near_best_preserved",
        "relative_regret",
        "baseline_best_p95",
        "selected_g_classes",
        "random_k_size",
        "random_repetitions",
    ]

    schema = schema[schema_cols].rename(
        columns={
            "top1_preserved": "schema_lens_top1",
            "top3_preserved": "schema_lens_top3",
            "near_best_preserved": "schema_lens_near_best",
            "relative_regret": "schema_lens_regret",
            "baseline_best_g_class": "schema_lens_best_g_class",
            "baseline_best_p95": "schema_lens_best_p95",
            "selected_g_classes": "schema_lens_selected_g_classes",
        }
    )

    random_k = random_k[random_cols].rename(
        columns={
            "top1_preserved": "random_k_top1_probability",
            "top3_preserved": "random_k_top3_probability",
            "near_best_preserved": "random_k_near_best_probability",
            "relative_regret": "random_k_expected_regret",
            "baseline_best_p95": "random_k_expected_best_p95",
            "selected_g_classes": "random_k_selected_g_classes",
        }
    )

    merged = schema.merge(random_k, on=key_cols, how="inner")

    merged["top1_gap_random_minus_schema"] = (
        merged["random_k_top1_probability"] - merged["schema_lens_top1"]
    )

    merged["near_best_gap_random_minus_schema"] = (
        merged["random_k_near_best_probability"] - merged["schema_lens_near_best"]
    )

    merged["regret_gap_random_minus_schema"] = (
        merged["random_k_expected_regret"] - merged["schema_lens_regret"]
    )

    def classify_top1(row):
        gap = row["top1_gap_random_minus_schema"]
        if pd.isna(gap):
            return "unknown"
        if abs(gap) < 1e-12:
            return "tie"
        if gap > 0:
            return "random_k_higher_top1_probability"
        return "schema_lens_higher_top1"

    def classify_regret(row):
        gap = row["regret_gap_random_minus_schema"]
        if pd.isna(gap):
            return "unknown"
        if abs(gap) < 1e-12:
            return "tie"
        if gap > 0:
            return "schema_lens_lower_regret"
        return "random_k_lower_expected_regret"

    merged["top1_comparison"] = merged.apply(classify_top1, axis=1)
    merged["regret_comparison"] = merged.apply(classify_regret, axis=1)

    return merged


def summarize_schema_vs_random(comparison_df: pd.DataFrame):
    rows = []

    groupings = [
        ["dataset"],
        ["run_phase"],
        ["dataset", "run_phase"],
    ]

    for group_cols in groupings:
        for keys, group in comparison_df.groupby(group_cols, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)

            key_data = dict(zip(group_cols, keys))

            row = {
                "level": "+".join(group_cols),
                **key_data,
                "cases": len(group),
                "schema_lens_mean_top1": group["schema_lens_top1"].mean(),
                "random_k_mean_top1_probability": group["random_k_top1_probability"].mean(),
                "mean_top1_gap_random_minus_schema": group["top1_gap_random_minus_schema"].mean(),
                "schema_lens_mean_near_best": group["schema_lens_near_best"].mean(),
                "random_k_mean_near_best_probability": group["random_k_near_best_probability"].mean(),
                "mean_near_best_gap_random_minus_schema": group["near_best_gap_random_minus_schema"].mean(),
                "schema_lens_mean_regret": group["schema_lens_regret"].mean(),
                "random_k_mean_expected_regret": group["random_k_expected_regret"].mean(),
                "mean_regret_gap_random_minus_schema": group["regret_gap_random_minus_schema"].mean(),
                "schema_lens_higher_top1_cases": (group["top1_comparison"] == "schema_lens_higher_top1").sum(),
                "random_k_higher_top1_cases": (group["top1_comparison"] == "random_k_higher_top1_probability").sum(),
                "top1_tie_cases": (group["top1_comparison"] == "tie").sum(),
                "schema_lens_lower_regret_cases": (group["regret_comparison"] == "schema_lens_lower_regret").sum(),
                "random_k_lower_regret_cases": (group["regret_comparison"] == "random_k_lower_expected_regret").sum(),
                "regret_tie_cases": (group["regret_comparison"] == "tie").sum(),
            }

            rows.append(row)

    overall = {
        "level": "overall",
        "cases": len(comparison_df),
        "schema_lens_mean_top1": comparison_df["schema_lens_top1"].mean(),
        "random_k_mean_top1_probability": comparison_df["random_k_top1_probability"].mean(),
        "mean_top1_gap_random_minus_schema": comparison_df["top1_gap_random_minus_schema"].mean(),
        "schema_lens_mean_near_best": comparison_df["schema_lens_near_best"].mean(),
        "random_k_mean_near_best_probability": comparison_df["random_k_near_best_probability"].mean(),
        "mean_near_best_gap_random_minus_schema": comparison_df["near_best_gap_random_minus_schema"].mean(),
        "schema_lens_mean_regret": comparison_df["schema_lens_regret"].mean(),
        "random_k_mean_expected_regret": comparison_df["random_k_expected_regret"].mean(),
        "mean_regret_gap_random_minus_schema": comparison_df["regret_gap_random_minus_schema"].mean(),
        "schema_lens_higher_top1_cases": (comparison_df["top1_comparison"] == "schema_lens_higher_top1").sum(),
        "random_k_higher_top1_cases": (comparison_df["top1_comparison"] == "random_k_higher_top1_probability").sum(),
        "top1_tie_cases": (comparison_df["top1_comparison"] == "tie").sum(),
        "schema_lens_lower_regret_cases": (comparison_df["regret_comparison"] == "schema_lens_lower_regret").sum(),
        "random_k_lower_regret_cases": (comparison_df["regret_comparison"] == "random_k_lower_expected_regret").sum(),
        "regret_tie_cases": (comparison_df["regret_comparison"] == "tie").sum(),
    }

    rows.append(overall)

    return pd.DataFrame(rows)


def build_report(summary_hot, by_dataset_hot, comparison_summary, output_dir: Path, repo_root: Path):
    lines = []

    lines.append("# Baseline Diagnostics Report")
    lines.append("")
    lines.append("This report adds two diagnostics to the baseline simulation:")
    lines.append("")
    lines.append("1. hot-run-only summaries;")
    lines.append("2. direct comparison between SchemaLens and random-k.")
    lines.append("")
    lines.append("The goal is to understand whether random-k is genuinely stronger, or whether it benefits from sampling a large fraction of the measured configuration space.")
    lines.append("")

    lines.append("## Output files")
    for name in [
        "baseline_performance_summary_hot.csv",
        "baseline_performance_by_dataset_hot.csv",
        "schema_lens_vs_random_k_by_case.csv",
        "schema_lens_vs_random_k_summary.csv",
        "schema_lens_vs_random_k_report.txt",
    ]:
        path = output_dir / name
        lines.append(f"- {path.relative_to(repo_root).as_posix()}")

    lines.append("")
    lines.append("## Hot-run overall summary")
    for _, row in summary_hot.sort_values("baseline").iterrows():
        lines.append(
            f"- {row['baseline']}: "
            f"available={int(row['available_cases'])}/{int(row['total_cases'])}, "
            f"top1={fmt_float(row['top1_preservation_rate'])}, "
            f"near_best={fmt_float(row['near_best_preservation_rate'])}, "
            f"mean_regret={fmt_float(row['mean_relative_regret'])}"
        )

    lines.append("")
    lines.append("## Hot-run dataset summary")
    for _, row in by_dataset_hot.sort_values(["dataset", "baseline"]).iterrows():
        lines.append(
            f"- {row['dataset']} / {row['baseline']}: "
            f"available={int(row['available_cases'])}/{int(row['total_cases'])}, "
            f"top1={fmt_float(row['top1_preservation_rate'])}, "
            f"near_best={fmt_float(row['near_best_preservation_rate'])}, "
            f"mean_regret={fmt_float(row['mean_relative_regret'])}"
        )

    lines.append("")
    lines.append("## SchemaLens vs random-k summary")
    for _, row in comparison_summary.sort_values(["level"]).iterrows():
        label_parts = [row["level"]]
        for col in ["dataset", "run_phase"]:
            if col in row and not pd.isna(row[col]):
                label_parts.append(f"{col}={row[col]}")
        label = " / ".join(label_parts)

        lines.append(
            f"- {label}: "
            f"cases={int(row['cases'])}, "
            f"schema_top1={fmt_float(row['schema_lens_mean_top1'])}, "
            f"random_top1={fmt_float(row['random_k_mean_top1_probability'])}, "
            f"schema_regret={fmt_float(row['schema_lens_mean_regret'])}, "
            f"random_regret={fmt_float(row['random_k_mean_expected_regret'])}, "
            f"schema_higher_top1_cases={int(row['schema_lens_higher_top1_cases'])}, "
            f"random_higher_top1_cases={int(row['random_k_higher_top1_cases'])}, "
            f"top1_tie_cases={int(row['top1_tie_cases'])}"
        )

    lines.append("")
    lines.append("## Interpretation note")
    lines.append("Random-k is a stochastic baseline. It samples the same number of measured configuration classes as SchemaLens selects.")
    lines.append("When the measured configuration space is small or SchemaLens selects many classes, random-k has a high probability of including the global best by chance.")
    lines.append("Therefore, random-k should be interpreted as a statistical sanity check, not as an explainable design method.")

    return "\n".join(lines)


def main():
    repo_root = Path(__file__).resolve().parents[2]
    output_dir = repo_root / "analysis" / "generated"

    input_path = output_dir / "baseline_performance_by_case.csv"

    if not input_path.exists():
        raise FileNotFoundError(
            f"Missing input file: {input_path}. Run simulate_baselines.py first."
        )

    perf_df = pd.read_csv(input_path, encoding="utf-8-sig")

    numeric_cols = [
        "top1_preserved",
        "top3_preserved",
        "near_best_preserved",
        "relative_regret",
        "baseline_best_p95",
        "global_best_p95",
    ]

    for col in numeric_cols:
        perf_df[col] = pd.to_numeric(perf_df[col], errors="coerce")

    hot_df = perf_df[perf_df["run_phase"] == "hot"].copy()

    summary_hot = summarize_performance(hot_df, ["baseline"])
    by_dataset_hot = summarize_performance(hot_df, ["dataset", "baseline"])

    comparison = build_schema_lens_vs_random(perf_df)
    comparison_summary = summarize_schema_vs_random(comparison)

    summary_hot_path = output_dir / "baseline_performance_summary_hot.csv"
    by_dataset_hot_path = output_dir / "baseline_performance_by_dataset_hot.csv"
    comparison_path = output_dir / "schema_lens_vs_random_k_by_case.csv"
    comparison_summary_path = output_dir / "schema_lens_vs_random_k_summary.csv"
    report_path = output_dir / "schema_lens_vs_random_k_report.txt"

    summary_hot.to_csv(summary_hot_path, index=False, encoding="utf-8")
    by_dataset_hot.to_csv(by_dataset_hot_path, index=False, encoding="utf-8")
    comparison.to_csv(comparison_path, index=False, encoding="utf-8")
    comparison_summary.to_csv(comparison_summary_path, index=False, encoding="utf-8")

    report = build_report(
        summary_hot=summary_hot,
        by_dataset_hot=by_dataset_hot,
        comparison_summary=comparison_summary,
        output_dir=output_dir,
        repo_root=repo_root,
    )
    report_path.write_text(report, encoding="utf-8")

    print("Baseline diagnostics completed.")
    print(f"Hot summary: {summary_hot_path}")
    print(f"Hot dataset summary: {by_dataset_hot_path}")
    print(f"SchemaLens vs random-k by case: {comparison_path}")
    print(f"SchemaLens vs random-k summary: {comparison_summary_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()