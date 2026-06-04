from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_CATALOG_HEADER = [
    "experiment_id",
    "config_name",
    "activated_class",
    "benchmark_family",
    "scale_factor",
    "scale_label",
    "execution_phase",
    "mongo_db_name",
    "selected_root",
    "primary_collection",
    "embedding_depth",
    "embedding_variant",
    "embedded_entities",
    "snapshot_entities",
    "referenced_entities",
    "changed_region_entities",
    "derived_from_queries",
    "n_supporting_queries",
    "primary_queries",
    "secondary_affected_queries",
    "control_queries",
    "n_primary_queries",
    "n_secondary_affected_queries",
    "n_control_queries",
    "experiment_goal",
]

EXPECTED_TEMPLATE_HEADER = [
    "benchmark_run_id",
    "experiment_id",
    "config_name",
    "activated_class",
    "benchmark_family",
    "scale_factor",
    "scale_label",
    "mongo_db_name",
    "selected_root",
    "primary_collection",
    "embedding_depth",
    "embedding_variant",
    "embedded_entities",
    "snapshot_entities",
    "referenced_entities",
    "query_name",
    "query_group",
    "run_phase",
    "phase_order",
    "repetition",
    "execution_status",
    "error_message",
    "start_ts",
    "end_ts",
    "latency_ms",
    "success",
    "documents_returned",
    "documents_written",
    "bytes_read_estimate",
    "bytes_written_estimate",
    "experiment_goal",
    "query_group_order",
]


def read_header_and_count(path: Path) -> tuple[list[str], int]:
    with path.open(newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        header = next(reader)
        n_rows = sum(1 for _ in reader)
    return header, n_rows


def validate_csv(path: Path, expected_header: list[str], label: str, root: Path | None = None) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Expected {label} file not found: {path}")

    header, n_rows = read_header_and_count(path)

    if header != expected_header:
        raise ValueError(
            f"Unexpected header for {label}: {path}\n"
            f"Expected: {expected_header}\n"
            f"Observed: {header}"
        )

    display = str(path)
    if root is not None:
        display = display_path(path, root)

    return {
        "path": display,
        "rows_excluding_header": n_rows,
        "columns": len(header),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute the IMDb framework notebook and export benchmark artifacts."
    )

    parser.add_argument(
        "--notebook",
        default="methodology/imdb_methodology.ipynb",
        help="Path to the IMDb framework notebook.",
    )
    parser.add_argument(
        "--imdb-sf-root",
        required=True,
        help="Directory containing IMDb scale-factor folders: sf_025, sf_050/sf_05, and sf_1.",
    )
    parser.add_argument(
        "--active-scale-label",
        default="sf0.25",
        choices=["sf0.25", "sf0.5", "sf1"],
        help="Active IMDb scale label used by the framework notebook.",
    )
    parser.add_argument(
        "--framework-output-dir",
        default="analysis/generated/framework/imdb",
        help="Directory for framework trace artifacts.",
    )
    parser.add_argument(
        "--benchmark-output-dir",
        default="benchmark/imdb",
        help="Directory where benchmark-ready IMDb artifacts are written.",
    )
    parser.add_argument(
        "--timeout",
        default="-1",
        help="Notebook execution timeout passed to nbconvert. Use -1 for no timeout.",
    )

    return parser.parse_args()


def resolve_scale_dir(imdb_sf_root: Path, active_scale_label: str) -> Path:
    scale_folder_candidates = {
        "sf0.25": ["sf_025"],
        "sf0.5": ["sf_050", "sf_05"],
        "sf1": ["sf_1"],
    }

    for folder_name in scale_folder_candidates[active_scale_label]:
        candidate = imdb_sf_root / folder_name
        if candidate.exists():
            return candidate

    tried = ", ".join(scale_folder_candidates[active_scale_label])
    raise FileNotFoundError(
        f"No scale folder found for {active_scale_label} under {imdb_sf_root}. "
        f"Tried: {tried}"
    )


def display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return "<external-path>"


def main() -> None:
    args = parse_args()

    run_root = Path.cwd().resolve()
    notebook = Path(args.notebook).resolve()
    imdb_sf_root = Path(args.imdb_sf_root).expanduser().resolve()
    framework_output_dir = Path(args.framework_output_dir).resolve()
    benchmark_output_dir = Path(args.benchmark_output_dir).resolve()

    if not notebook.exists():
        raise FileNotFoundError(f"Notebook not found: {notebook}")

    scale_dir = resolve_scale_dir(imdb_sf_root, args.active_scale_label)

    framework_output_dir.mkdir(parents=True, exist_ok=True)
    benchmark_output_dir.mkdir(parents=True, exist_ok=True)

    executed_dir = framework_output_dir / "executed_notebooks"
    executed_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["IMDB_SF_ROOT"] = str(imdb_sf_root)
    env["IMDB_ACTIVE_SCALE"] = args.active_scale_label
    env["IMDB_FRAMEWORK_OUTPUT_DIR"] = str(framework_output_dir)

    command = [
        "jupyter",
        "nbconvert",
        "--to",
        "notebook",
        "--execute",
        str(notebook),
        "--output",
        "imdb_framework_executed.ipynb",
        "--output-dir",
        str(executed_dir),
        f"--ExecutePreprocessor.timeout={args.timeout}",
    ]

    print("Executing IMDb framework notebook...")
    print(" ".join(command))

    try:
        subprocess.run(command, check=True, cwd=Path.cwd(), env=env)
    except FileNotFoundError as exc:
        raise SystemExit(
            "Could not find the `jupyter` executable. "
            "Install the analysis environment first with: pip install -r requirements.txt"
        ) from exc

    generated_catalog = framework_output_dir / "mongo_experiment_catalog_df.csv"
    generated_template = framework_output_dir / "benchmark_execution_template_df.csv"

    target_catalog = benchmark_output_dir / "mongo_experiment_catalog.csv"
    target_template = benchmark_output_dir / "benchmark_execution_template.csv"

    framework_catalog_info = validate_csv(
        generated_catalog,
        EXPECTED_CATALOG_HEADER,
        "framework IMDb experiment catalog",
        run_root,
    )
    framework_template_info = validate_csv(
        generated_template,
        EXPECTED_TEMPLATE_HEADER,
        "framework IMDb benchmark execution template",
        run_root,
    )

    shutil.copy2(generated_catalog, target_catalog)
    shutil.copy2(generated_template, target_template)

    benchmark_catalog_info = validate_csv(
        target_catalog,
        EXPECTED_CATALOG_HEADER,
        "benchmark IMDb experiment catalog",
        run_root,
    )
    benchmark_template_info = validate_csv(
        target_template,
        EXPECTED_TEMPLATE_HEADER,
        "benchmark IMDb execution template",
        run_root,
    )

    warnings: list[str] = []

    if benchmark_catalog_info["rows_excluding_header"] != 27:
        warnings.append(
            "mongo_experiment_catalog.csv row count differs from the current artifact baseline "
            f"(expected 27, observed {benchmark_catalog_info['rows_excluding_header']})."
        )

    if benchmark_template_info["rows_excluding_header"] != 5400:
        warnings.append(
            "benchmark_execution_template.csv row count differs from the current artifact baseline "
            f"(expected 5400, observed {benchmark_template_info['rows_excluding_header']})."
        )

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "notebook": display_path(notebook, run_root),
        "active_scale_label": args.active_scale_label,
        "resolved_scale_folder_name": scale_dir.name,
        "framework_output_dir": display_path(framework_output_dir, run_root),
        "benchmark_output_dir": display_path(benchmark_output_dir, run_root),
        "note": "The external IMDb scale-factor root is intentionally not stored to avoid machine-specific paths.",
        "generated_artifacts": {
            "framework_catalog": framework_catalog_info,
            "framework_template": framework_template_info,
            "benchmark_catalog": benchmark_catalog_info,
            "benchmark_template": benchmark_template_info,
        },
        "warnings": warnings,
    }

    manifest_path = framework_output_dir / "framework_artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("IMDb framework artifacts generated.")
    print(f" - {target_catalog}")
    print(f" - {target_template}")
    print(f" - {manifest_path}")

    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f" - {warning}")


if __name__ == "__main__":
    main()
