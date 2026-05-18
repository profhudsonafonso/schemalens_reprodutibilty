from pathlib import Path
import sys
import pandas as pd


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    return pd.read_csv(path, encoding="utf-8-sig")


def normalize_imdb(df: pd.DataFrame, dataset: str, source_file: str) -> pd.DataFrame:
    required = {
        "experiment_id",
        "config_name",
        "activated_class",
        "benchmark_family",
        "scale_label",
        "query_name",
        "query_group",
        "run_phase",
        "n_runs",
        "n_success_runs",
        "avg_latency_ms",
        "median_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
        "min_latency_ms",
        "max_latency_ms",
        "std_latency_ms",
        "avg_documents_returned",
        "avg_documents_written",
    }

    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"IMDb file is missing columns: {sorted(missing)}")

    out = df.rename(
        columns={
            "experiment_id": "source_experiment_id",
            "config_name": "config_id",
            "activated_class": "g_class",
            "benchmark_family": "design_family",
            "query_group": "benchmark_group",
        }
    ).copy()

    out["dataset"] = dataset
    out["source_file"] = source_file
    return out


def normalize_fiben_or_ldbc(df: pd.DataFrame, dataset: str, source_file: str) -> pd.DataFrame:
    required = {
        "candidate_id",
        "query_name",
        "final_benchmark_group",
        "design_pattern",
        "g_class",
        "scale_label",
        "run_phase",
        "n_runs",
        "n_success_runs",
        "avg_latency_ms",
        "median_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
        "min_latency_ms",
        "max_latency_ms",
        "std_latency_ms",
        "avg_documents_returned",
        "avg_documents_written",
    }

    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{dataset} file is missing columns: {sorted(missing)}")

    out = df.rename(
        columns={
            "candidate_id": "config_id",
            "final_benchmark_group": "benchmark_group",
            "design_pattern": "design_family",
        }
    ).copy()

    out["dataset"] = dataset
    out["source_experiment_id"] = ""
    out["source_file"] = source_file
    return out


def coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = [
        "n_runs",
        "n_success_runs",
        "avg_latency_ms",
        "median_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
        "min_latency_ms",
        "max_latency_ms",
        "std_latency_ms",
        "avg_documents_returned",
        "avg_documents_written",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def build_report(df: pd.DataFrame, output_path: Path, repo_root: Path) -> str:
    lines = []

    lines.append("# Normalization Report")
    lines.append("")
    relative_output_path = output_path.relative_to(repo_root).as_posix()
    lines.append(f"Output file: {relative_output_path}")
    lines.append(f"Total rows: {len(df)}")
    lines.append("")

    lines.append("## Rows by dataset")
    for dataset, count in df["dataset"].value_counts().sort_index().items():
        lines.append(f"- {dataset}: {count}")

    lines.append("")
    lines.append("## Rows by dataset and scale")
    scale_counts = (
        df.groupby(["dataset", "scale_label"])
        .size()
        .reset_index(name="rows")
        .sort_values(["dataset", "scale_label"])
    )
    for _, row in scale_counts.iterrows():
        lines.append(f"- {row['dataset']} / {row['scale_label']}: {row['rows']}")

    lines.append("")
    lines.append("## Rows by dataset and run phase")
    phase_counts = (
        df.groupby(["dataset", "run_phase"])
        .size()
        .reset_index(name="rows")
        .sort_values(["dataset", "run_phase"])
    )
    for _, row in phase_counts.iterrows():
        lines.append(f"- {row['dataset']} / {row['run_phase']}: {row['rows']}")

    lines.append("")
    lines.append("## Benchmark groups")
    group_counts = (
        df.groupby(["dataset", "benchmark_group"])
        .size()
        .reset_index(name="rows")
        .sort_values(["dataset", "benchmark_group"])
    )
    for _, row in group_counts.iterrows():
        lines.append(f"- {row['dataset']} / {row['benchmark_group']}: {row['rows']}")

    lines.append("")
    lines.append("## Unique queries by dataset")
    for dataset in sorted(df["dataset"].unique()):
        n_queries = df.loc[df["dataset"] == dataset, "query_name"].nunique()
        lines.append(f"- {dataset}: {n_queries}")

    lines.append("")
    lines.append("## G classes by dataset")
    for dataset in sorted(df["dataset"].unique()):
        classes = sorted(df.loc[df["dataset"] == dataset, "g_class"].dropna().unique())
        lines.append(f"- {dataset}: {', '.join(classes)}")

    lines.append("")
    lines.append("## Validation checks")
    null_p95 = df["p95_latency_ms"].isna().sum()
    lines.append(f"- Rows with missing p95_latency_ms: {null_p95}")

    key_cols = ["dataset", "scale_label", "query_name", "config_id", "g_class", "run_phase"]
    duplicate_count = df.duplicated(subset=key_cols).sum()
    lines.append(f"- Duplicate rows by {key_cols}: {duplicate_count}")

    lines.append("")
    lines.append("## Source files")
    for source in sorted(df["source_file"].unique()):
        lines.append(f"- {source}")

    return "\n".join(lines)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]

    output_dir = repo_root / "analysis" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    inputs = [
        {
            "dataset": "imdb",
            "path": repo_root / "analysis" / "imdb" / "benchmark_aggregate_results_imdb_all_sfs.csv",
            "kind": "imdb",
        },
        {
            "dataset": "fiben",
            "path": repo_root / "analysis" / "fiben" / "benchmark_aggregate_results_fiben_sf1.csv",
            "kind": "fiben_or_ldbc",
        },
        {
            "dataset": "fiben",
            "path": repo_root / "analysis" / "fiben" / "benchmark_aggregate_results_fiben_sf10.csv",
            "kind": "fiben_or_ldbc",
        },
        {
            "dataset": "fiben",
            "path": repo_root / "analysis" / "fiben" / "benchmark_aggregate_results_fiben_sf30.csv",
            "kind": "fiben_or_ldbc",
        },
        {
            "dataset": "ldbc_snb",
            "path": repo_root / "analysis" / "ldbc_snb" / "benchmark_aggregate_results_ldbc_snb_sf0_1.csv",
            "kind": "fiben_or_ldbc",
        },
        {
            "dataset": "ldbc_snb",
            "path": repo_root / "analysis" / "ldbc_snb" / "benchmark_aggregate_results_ldbc_snb_sf1.csv",
            "kind": "fiben_or_ldbc",
        },
        {
            "dataset": "ldbc_snb",
            "path": repo_root / "analysis" / "ldbc_snb" / "benchmark_aggregate_results_ldbc_snb_sf3.csv",
            "kind": "fiben_or_ldbc",
        },
    ]

    normalized_frames = []

    for item in inputs:
        source_path = item["path"]
        dataset = item["dataset"]
        source_file = str(source_path.relative_to(repo_root)).replace("\\", "/")

        print(f"Reading {source_file}")
        df = read_csv(source_path)

        if item["kind"] == "imdb":
            norm = normalize_imdb(df, dataset=dataset, source_file=source_file)
        else:
            norm = normalize_fiben_or_ldbc(df, dataset=dataset, source_file=source_file)

        normalized_frames.append(norm)

    combined = pd.concat(normalized_frames, ignore_index=True)
    combined = coerce_numeric(combined)

    combined["benchmark_group"] = combined["benchmark_group"].astype(str).str.lower()
    combined["run_phase"] = combined["run_phase"].astype(str).str.lower()
    combined["g_class"] = combined["g_class"].astype(str).str.upper()

    combined["query_scale_phase_id"] = (
        combined["dataset"].astype(str)
        + "::"
        + combined["scale_label"].astype(str)
        + "::"
        + combined["query_name"].astype(str)
        + "::"
        + combined["run_phase"].astype(str)
    )

    ordered_cols = [
        "dataset",
        "scale_label",
        "query_name",
        "query_scale_phase_id",
        "config_id",
        "g_class",
        "design_family",
        "benchmark_group",
        "run_phase",
        "n_runs",
        "n_success_runs",
        "avg_latency_ms",
        "median_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
        "min_latency_ms",
        "max_latency_ms",
        "std_latency_ms",
        "avg_documents_returned",
        "avg_documents_written",
        "source_experiment_id",
        "source_file",
    ]

    combined = combined[ordered_cols].sort_values(
        ["dataset", "scale_label", "query_name", "run_phase", "g_class", "config_id"]
    )

    output_csv = output_dir / "aggregate_results_all_datasets.csv"
    output_report = output_dir / "normalization_report.txt"

    combined.to_csv(output_csv, index=False, encoding="utf-8")
    report = build_report(combined, output_csv, repo_root)
    output_report.write_text(report, encoding="utf-8")

    print("")
    print("Normalization completed.")
    print(f"Rows written: {len(combined)}")
    print(f"CSV: {output_csv}")
    print(f"Report: {output_report}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise