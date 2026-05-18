from pathlib import Path
import random
import pandas as pd


NEAR_BEST_THRESHOLD = 0.05
RANDOM_REPETITIONS = 1000
RANDOM_SEED = 42

BASELINES = [
    "schema_lens",
    "random_k",
    "always_reference",
    "always_embed",
    "depth_only",
    "relationship_type_only",
]


def string_to_classes(value):
    if pd.isna(value):
        return set()

    value = str(value).strip()
    if value == "":
        return set()

    return {x.strip().upper() for x in value.split("|") if x.strip()}


def classes_to_string(classes):
    if not classes:
        return ""
    return "|".join(sorted(classes))


def load_inputs(repo_root: Path):
    aggregate_path = repo_root / "analysis" / "generated" / "aggregate_results_all_datasets.csv"
    coverage_path = repo_root / "analysis" / "generated" / "baseline_coverage_by_case.csv"

    if not aggregate_path.exists():
        raise FileNotFoundError(
            f"Missing input file: {aggregate_path}. Run normalize_aggregate_outputs.py first."
        )

    if not coverage_path.exists():
        raise FileNotFoundError(
            f"Missing input file: {coverage_path}. Run check_baseline_coverage.py first."
        )

    df = pd.read_csv(aggregate_path, encoding="utf-8-sig")
    coverage_df = pd.read_csv(coverage_path, encoding="utf-8-sig")

    required_df_cols = {
        "dataset",
        "scale_label",
        "query_name",
        "config_id",
        "g_class",
        "benchmark_group",
        "run_phase",
        "p95_latency_ms",
    }

    required_coverage_cols = {
        "dataset",
        "scale_label",
        "query_name",
        "run_phase",
        "baseline",
        "selected_available_g_classes",
        "coverage_status",
    }

    missing_df = required_df_cols - set(df.columns)
    missing_cov = required_coverage_cols - set(coverage_df.columns)

    if missing_df:
        raise ValueError(f"Aggregate file is missing columns: {sorted(missing_df)}")

    if missing_cov:
        raise ValueError(f"Coverage file is missing columns: {sorted(missing_cov)}")

    df["dataset"] = df["dataset"].astype(str)
    df["scale_label"] = df["scale_label"].astype(str)
    df["query_name"] = df["query_name"].astype(str)
    df["run_phase"] = df["run_phase"].astype(str).str.lower()
    df["config_id"] = df["config_id"].astype(str)
    df["g_class"] = df["g_class"].astype(str).str.upper()
    df["benchmark_group"] = df["benchmark_group"].astype(str).str.lower()
    df["p95_latency_ms"] = pd.to_numeric(df["p95_latency_ms"], errors="coerce")

    coverage_df["dataset"] = coverage_df["dataset"].astype(str)
    coverage_df["scale_label"] = coverage_df["scale_label"].astype(str)
    coverage_df["query_name"] = coverage_df["query_name"].astype(str)
    coverage_df["run_phase"] = coverage_df["run_phase"].astype(str).str.lower()
    coverage_df["baseline"] = coverage_df["baseline"].astype(str)
    coverage_df["coverage_status"] = coverage_df["coverage_status"].astype(str)

    return df, coverage_df


def build_coverage_lookup(coverage_df: pd.DataFrame):
    lookup = {}

    for _, row in coverage_df.iterrows():
        key = (
            row["dataset"],
            row["scale_label"],
            row["query_name"],
            row["run_phase"],
            row["baseline"],
        )
        lookup[key] = row

    return lookup


def get_case_key(dataset, scale_label, query_name, run_phase):
    return dataset, scale_label, query_name, run_phase


def get_query_scale_phase_id(case_key):
    dataset, scale_label, query_name, run_phase = case_key
    return f"{dataset}::{scale_label}::{query_name}::{run_phase}"


def prepare_case_info(group: pd.DataFrame):
    group = group.dropna(subset=["p95_latency_ms"]).copy()

    ordered = group.sort_values(
        ["p95_latency_ms", "g_class", "config_id"],
        ascending=[True, True, True],
    ).reset_index(drop=True)

    if ordered.empty:
        return None

    best = ordered.iloc[0]
    global_best_p95 = float(best["p95_latency_ms"])

    top3_config_ids = set(ordered.head(3)["config_id"].astype(str))

    if global_best_p95 <= 0:
        near_best_config_ids = {str(best["config_id"])}
    else:
        near_mask = (
            (ordered["p95_latency_ms"] - global_best_p95) / global_best_p95
            <= NEAR_BEST_THRESHOLD
        )
        near_best_config_ids = set(ordered.loc[near_mask, "config_id"].astype(str))

    class_best = {}
    for g_class, class_group in ordered.groupby("g_class"):
        class_ordered = class_group.sort_values(
            ["p95_latency_ms", "config_id"],
            ascending=[True, True],
        ).reset_index(drop=True)
        row = class_ordered.iloc[0]

        class_best[str(g_class).upper()] = {
            "config_id": str(row["config_id"]),
            "g_class": str(row["g_class"]).upper(),
            "p95": float(row["p95_latency_ms"]),
        }

    schema_lens_classes = set(
        ordered.loc[ordered["benchmark_group"] != "control", "g_class"]
        .astype(str)
        .str.upper()
        .unique()
    )

    available_classes = set(class_best.keys())

    return {
        "global_best_config_id": str(best["config_id"]),
        "global_best_g_class": str(best["g_class"]).upper(),
        "global_best_p95": global_best_p95,
        "top3_config_ids": top3_config_ids,
        "near_best_config_ids": near_best_config_ids,
        "class_best": class_best,
        "available_classes": available_classes,
        "schema_lens_classes": schema_lens_classes,
        "available_config_count": ordered["config_id"].nunique(),
    }


def evaluate_selected_classes(selected_classes: set, case_info: dict):
    selected_classes = {x for x in selected_classes if x in case_info["class_best"]}

    if not selected_classes:
        return {
            "availability_status": "unavailable",
            "selected_config_count": 0,
            "selected_g_classes": "",
            "baseline_best_config_id": "",
            "baseline_best_g_class": "",
            "baseline_best_p95": None,
            "top1_preserved": None,
            "top3_preserved": None,
            "near_best_preserved": None,
            "relative_regret": None,
        }

    selected_best_rows = [case_info["class_best"][g] for g in selected_classes]
    selected_best_rows = sorted(
        selected_best_rows,
        key=lambda x: (x["p95"], x["g_class"], x["config_id"]),
    )

    best = selected_best_rows[0]
    baseline_best_p95 = float(best["p95"])
    global_best_p95 = float(case_info["global_best_p95"])

    if global_best_p95 <= 0:
        relative_regret = None
    else:
        relative_regret = (baseline_best_p95 - global_best_p95) / global_best_p95

    selected_config_ids = {x["config_id"] for x in selected_best_rows}

    top1_preserved = 1 if baseline_best_p95 <= global_best_p95 * (1 + 1e-12) else 0

    top3_preserved = 1 if selected_config_ids & case_info["top3_config_ids"] else 0

    near_best_preserved = (
        1 if selected_config_ids & case_info["near_best_config_ids"] else 0
    )

    return {
        "availability_status": "available",
        "selected_config_count": len(selected_classes),
        "selected_g_classes": classes_to_string(selected_classes),
        "baseline_best_config_id": best["config_id"],
        "baseline_best_g_class": best["g_class"],
        "baseline_best_p95": baseline_best_p95,
        "top1_preserved": top1_preserved,
        "top3_preserved": top3_preserved,
        "near_best_preserved": near_best_preserved,
        "relative_regret": relative_regret,
    }


def evaluate_random_k(case_info: dict, schema_lens_class_count: int, rng: random.Random):
    available_classes = sorted(case_info["available_classes"])

    if schema_lens_class_count <= 0 or not available_classes:
        return {
            "availability_status": "unavailable",
            "selected_config_count": 0,
            "selected_g_classes": "",
            "baseline_best_config_id": "",
            "baseline_best_g_class": "",
            "baseline_best_p95": None,
            "top1_preserved": None,
            "top3_preserved": None,
            "near_best_preserved": None,
            "relative_regret": None,
            "random_repetitions": RANDOM_REPETITIONS,
            "random_k_size": schema_lens_class_count,
            "random_top1_std": None,
            "random_top3_std": None,
            "random_near_best_std": None,
            "random_regret_std": None,
        }

    k = min(schema_lens_class_count, len(available_classes))

    top1_values = []
    top3_values = []
    near_best_values = []
    regret_values = []
    best_p95_values = []

    for _ in range(RANDOM_REPETITIONS):
        sampled_classes = set(rng.sample(available_classes, k))
        metrics = evaluate_selected_classes(sampled_classes, case_info)

        if metrics["availability_status"] == "available":
            top1_values.append(metrics["top1_preserved"])
            top3_values.append(metrics["top3_preserved"])
            near_best_values.append(metrics["near_best_preserved"])

            if metrics["relative_regret"] is not None:
                regret_values.append(metrics["relative_regret"])

            if metrics["baseline_best_p95"] is not None:
                best_p95_values.append(metrics["baseline_best_p95"])

    if not top1_values:
        return {
            "availability_status": "unavailable",
            "selected_config_count": 0,
            "selected_g_classes": "",
            "baseline_best_config_id": "",
            "baseline_best_g_class": "",
            "baseline_best_p95": None,
            "top1_preserved": None,
            "top3_preserved": None,
            "near_best_preserved": None,
            "relative_regret": None,
            "random_repetitions": RANDOM_REPETITIONS,
            "random_k_size": k,
            "random_top1_std": None,
            "random_top3_std": None,
            "random_near_best_std": None,
            "random_regret_std": None,
        }

    top1_series = pd.Series(top1_values, dtype="float64")
    top3_series = pd.Series(top3_values, dtype="float64")
    near_series = pd.Series(near_best_values, dtype="float64")
    regret_series = pd.Series(regret_values, dtype="float64")
    best_p95_series = pd.Series(best_p95_values, dtype="float64")

    return {
        "availability_status": "available",
        "selected_config_count": k,
        "selected_g_classes": f"random_sample_k={k}",
        "baseline_best_config_id": "",
        "baseline_best_g_class": "",
        "baseline_best_p95": float(best_p95_series.mean()),
        "top1_preserved": float(top1_series.mean()),
        "top3_preserved": float(top3_series.mean()),
        "near_best_preserved": float(near_series.mean()),
        "relative_regret": float(regret_series.mean()) if len(regret_series) else None,
        "random_repetitions": RANDOM_REPETITIONS,
        "random_k_size": k,
        "random_top1_std": float(top1_series.std(ddof=0)),
        "random_top3_std": float(top3_series.std(ddof=0)),
        "random_near_best_std": float(near_series.std(ddof=0)),
        "random_regret_std": float(regret_series.std(ddof=0)) if len(regret_series) else None,
    }


def make_result_row(case_key, baseline, case_info, metrics, note=""):
    dataset, scale_label, query_name, run_phase = case_key

    return {
        "dataset": dataset,
        "scale_label": scale_label,
        "query_name": query_name,
        "run_phase": run_phase,
        "query_scale_phase_id": get_query_scale_phase_id(case_key),
        "baseline": baseline,
        "availability_status": metrics.get("availability_status"),
        "selected_g_classes": metrics.get("selected_g_classes"),
        "selected_config_count": metrics.get("selected_config_count"),
        "global_best_config_id": case_info["global_best_config_id"],
        "global_best_g_class": case_info["global_best_g_class"],
        "global_best_p95": case_info["global_best_p95"],
        "baseline_best_config_id": metrics.get("baseline_best_config_id"),
        "baseline_best_g_class": metrics.get("baseline_best_g_class"),
        "baseline_best_p95": metrics.get("baseline_best_p95"),
        "top1_preserved": metrics.get("top1_preserved"),
        "top3_preserved": metrics.get("top3_preserved"),
        "near_best_preserved": metrics.get("near_best_preserved"),
        "relative_regret": metrics.get("relative_regret"),
        "random_repetitions": metrics.get("random_repetitions", ""),
        "random_k_size": metrics.get("random_k_size", ""),
        "random_top1_std": metrics.get("random_top1_std", ""),
        "random_top3_std": metrics.get("random_top3_std", ""),
        "random_near_best_std": metrics.get("random_near_best_std", ""),
        "random_regret_std": metrics.get("random_regret_std", ""),
        "note": note,
    }


def simulate_baselines(df: pd.DataFrame, coverage_df: pd.DataFrame) -> pd.DataFrame:
    coverage_lookup = build_coverage_lookup(coverage_df)
    rng = random.Random(RANDOM_SEED)

    rows = []
    group_cols = ["dataset", "scale_label", "query_name", "run_phase"]
    grouped = df.groupby(group_cols, sort=True)

    total_groups = len(grouped)
    print(f"Simulating baselines for {total_groups} query-scale-phase cases...")

    for idx, (case_key, group) in enumerate(grouped, start=1):
        if idx % 25 == 0 or idx == 1 or idx == total_groups:
            print(f"  Processing case {idx}/{total_groups}: {case_key}")

        case_info = prepare_case_info(group)

        if case_info is None:
            continue

        schema_lens_classes = case_info["schema_lens_classes"]
        schema_lens_metrics = evaluate_selected_classes(schema_lens_classes, case_info)
        schema_lens_class_count = len(schema_lens_classes)

        rows.append(
            make_result_row(
                case_key=case_key,
                baseline="schema_lens",
                case_info=case_info,
                metrics=schema_lens_metrics,
                note="SchemaLens selects all non-control measured configuration classes for this case.",
            )
        )

        random_metrics = evaluate_random_k(
            case_info=case_info,
            schema_lens_class_count=schema_lens_class_count,
            rng=rng,
        )

        rows.append(
            make_result_row(
                case_key=case_key,
                baseline="random_k",
                case_info=case_info,
                metrics=random_metrics,
                note="Random-k is averaged over repeated samples from measured configuration classes.",
            )
        )

        for baseline in [
            "always_reference",
            "always_embed",
            "depth_only",
            "relationship_type_only",
        ]:
            lookup_key = (
                case_key[0],
                case_key[1],
                case_key[2],
                case_key[3],
                baseline,
            )

            coverage_row = coverage_lookup.get(lookup_key)

            if coverage_row is None:
                selected_classes = set()
                metrics = evaluate_selected_classes(selected_classes, case_info)
                metrics["availability_status"] = "coverage_missing"
                note = "Coverage row not found for this baseline and case."
            else:
                selected_classes = string_to_classes(
                    coverage_row.get("selected_available_g_classes", "")
                )
                metrics = evaluate_selected_classes(selected_classes, case_info)

                if metrics["availability_status"] == "unavailable":
                    note = (
                        "Baseline selected no measured configuration class for this case; "
                        "no latency was inferred."
                    )
                else:
                    note = (
                        f"Coverage status: {coverage_row.get('coverage_status')}; "
                        "performance computed over selected measured classes."
                    )

            rows.append(
                make_result_row(
                    case_key=case_key,
                    baseline=baseline,
                    case_info=case_info,
                    metrics=metrics,
                    note=note,
                )
            )

    return pd.DataFrame(rows)


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


def build_failure_cases(perf_df: pd.DataFrame) -> pd.DataFrame:
    available = perf_df[perf_df["availability_status"] == "available"].copy()

    failures = available[
        (available["top1_preserved"] < 1)
        | (available["near_best_preserved"] < 1)
        | (available["relative_regret"] > NEAR_BEST_THRESHOLD)
    ].copy()

    failures = failures.sort_values(
        ["relative_regret", "baseline", "dataset", "scale_label", "query_name"],
        ascending=[False, True, True, True, True],
    )

    return failures


def fmt_float(value, digits=4):
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def build_report(summary_df, by_dataset_df, failure_df, output_dir: Path, repo_root: Path):
    lines = []

    lines.append("# Baseline Performance Report")
    lines.append("")
    lines.append(
        "This report summarizes baseline performance simulation over the measured aggregate benchmark outputs."
    )
    lines.append("")
    lines.append("This step does not rerun MongoDB benchmarks.")
    lines.append("It uses p95 latency values already present in the normalized aggregate results.")
    lines.append("")

    lines.append("## Settings")
    lines.append(f"- Near-best threshold: {NEAR_BEST_THRESHOLD}")
    lines.append(f"- Random-k repetitions: {RANDOM_REPETITIONS}")
    lines.append(f"- Random seed: {RANDOM_SEED}")

    lines.append("")
    lines.append("## Output files")
    for name in [
        "baseline_performance_by_case.csv",
        "baseline_performance_summary.csv",
        "baseline_performance_by_dataset.csv",
        "baseline_failure_cases.csv",
        "baseline_performance_report.txt",
    ]:
        path = output_dir / name
        lines.append(f"- {path.relative_to(repo_root).as_posix()}")

    lines.append("")
    lines.append("## Overall summary")
    for _, row in summary_df.sort_values("baseline").iterrows():
        lines.append(
            f"- {row['baseline']}: "
            f"available={int(row['available_cases'])}/{int(row['total_cases'])}, "
            f"top1={fmt_float(row['top1_preservation_rate'])}, "
            f"top3={fmt_float(row['top3_preservation_rate'])}, "
            f"near_best={fmt_float(row['near_best_preservation_rate'])}, "
            f"mean_regret={fmt_float(row['mean_relative_regret'])}, "
            f"median_regret={fmt_float(row['median_relative_regret'])}"
        )

    lines.append("")
    lines.append("## Dataset-level summary")
    for _, row in by_dataset_df.sort_values(["dataset", "baseline"]).iterrows():
        lines.append(
            f"- {row['dataset']} / {row['baseline']}: "
            f"available={int(row['available_cases'])}/{int(row['total_cases'])}, "
            f"top1={fmt_float(row['top1_preservation_rate'])}, "
            f"near_best={fmt_float(row['near_best_preservation_rate'])}, "
            f"mean_regret={fmt_float(row['mean_relative_regret'])}"
        )

    lines.append("")
    lines.append("## Failure and near-failure candidates")
    lines.append(f"- Rows flagged: {len(failure_df)}")
    lines.append(
        "- A row is flagged when top-1 is not preserved, near-best is not preserved, "
        "or relative regret is above the near-best threshold."
    )

    lines.append("")
    lines.append("## Interpretation note")
    lines.append(
        "Unavailable cases are not assigned inferred latency values. "
        "A baseline is evaluated only when it selects at least one measured configuration class."
    )

    return "\n".join(lines)


def main():
    repo_root = Path(__file__).resolve().parents[2]
    output_dir = repo_root / "analysis" / "generated"

    df, coverage_df = load_inputs(repo_root)

    perf_df = simulate_baselines(df, coverage_df)

    summary_df = summarize_performance(perf_df, ["baseline"])
    by_dataset_df = summarize_performance(perf_df, ["dataset", "baseline"])
    failure_df = build_failure_cases(perf_df)

    by_case_path = output_dir / "baseline_performance_by_case.csv"
    summary_path = output_dir / "baseline_performance_summary.csv"
    by_dataset_path = output_dir / "baseline_performance_by_dataset.csv"
    failure_path = output_dir / "baseline_failure_cases.csv"
    report_path = output_dir / "baseline_performance_report.txt"

    perf_df.to_csv(by_case_path, index=False, encoding="utf-8")
    summary_df.to_csv(summary_path, index=False, encoding="utf-8")
    by_dataset_df.to_csv(by_dataset_path, index=False, encoding="utf-8")
    failure_df.to_csv(failure_path, index=False, encoding="utf-8")

    report = build_report(summary_df, by_dataset_df, failure_df, output_dir, repo_root)
    report_path.write_text(report, encoding="utf-8")

    print("")
    print("Baseline performance simulation completed.")
    print(f"Rows by case: {len(perf_df)}")
    print(f"Summary: {summary_path}")
    print(f"Dataset summary: {by_dataset_path}")
    print(f"Failure cases: {failure_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()