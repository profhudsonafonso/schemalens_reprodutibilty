from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_ARTIFACTS = [
    "benchmark_execution_plan.csv",
    "mongodb_candidate_specs_by_candidate_id.json",
    "benchmark_manifest.json",
]


def display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return "<external-path>"


def read_csv_shape(path: Path) -> tuple[int, int]:
    with path.open(newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        header = next(reader)
        n_rows = sum(1 for _ in reader)
    return n_rows, len(header)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute the LDBC SNB framework notebook and export MongoDB benchmark artifacts."
    )
    parser.add_argument("--notebook", default="ldbc_snb_methodology_core.ipynb")
    parser.add_argument("--ldbc-data-dir", required=True)
    parser.add_argument("--scale-label", default="sf0.1")
    parser.add_argument("--framework-output-dir", default="output/framework")
    parser.add_argument("--benchmark-output-dir", default="output/benchmark")
    parser.add_argument("--timeout", default="-1")
    return parser.parse_args()


def validate_ldbc_data_dir(data_dir: Path) -> None:
    expected = [
        data_dir / "social_network-sf0.1-CsvMergeForeign-StringDateFormatter",
        data_dir / "social_network-sf0.1-CsvMergeForeign-StringDateFormatter" / "dynamic",
        data_dir / "social_network-sf0.1-CsvMergeForeign-StringDateFormatter" / "static",
        data_dir / "substitution_parameters-sf0.1",
        data_dir / "social_network-sf0.1-numpart-1",
    ]

    missing = [p for p in expected if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Invalid LDBC SNB data directory. Missing:\n"
            + "\n".join(f" - {p}" for p in missing)
        )


def validate_artifacts(artifacts_dir: Path, root: Path) -> dict:
    info = {}

    for name in REQUIRED_ARTIFACTS:
        path = artifacts_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Required LDBC artifact not found: {path}")
        info[name] = {
            "path": display_path(path, root),
            "size_bytes": path.stat().st_size,
        }

    plan_path = artifacts_dir / "benchmark_execution_plan.csv"
    n_rows, n_cols = read_csv_shape(plan_path)
    info["benchmark_execution_plan.csv"]["rows_excluding_header"] = n_rows
    info["benchmark_execution_plan.csv"]["columns"] = n_cols

    specs_path = artifacts_dir / "mongodb_candidate_specs_by_candidate_id.json"
    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    info["mongodb_candidate_specs_by_candidate_id.json"]["n_specs"] = len(specs)

    manifest_path = artifacts_dir / "benchmark_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    info["benchmark_manifest.json"]["keys"] = list(manifest.keys())

    if n_rows <= 0:
        raise ValueError("LDBC benchmark_execution_plan.csv is empty.")

    if len(specs) <= 0:
        raise ValueError("LDBC candidate specs JSON is empty.")

    if n_rows != len(specs):
        raise ValueError(
            f"LDBC plan/spec mismatch: plan rows={n_rows}, specs={len(specs)}."
        )

    return info


def main() -> None:
    args = parse_args()

    run_root = Path.cwd().resolve()
    notebook = Path(args.notebook).resolve()
    ldbc_data_dir = Path(args.ldbc_data_dir).expanduser().resolve()
    framework_output_dir = Path(args.framework_output_dir).resolve()
    benchmark_output_dir = Path(args.benchmark_output_dir).resolve()

    if not notebook.exists():
        raise FileNotFoundError(f"Notebook not found: {notebook}")

    validate_ldbc_data_dir(ldbc_data_dir)

    framework_output_dir.mkdir(parents=True, exist_ok=True)
    benchmark_output_dir.parent.mkdir(parents=True, exist_ok=True)

    executed_dir = framework_output_dir / "executed_notebooks"
    executed_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["LDBC_DATA_DIR"] = str(ldbc_data_dir)
    env["LDBC_SCALE_LABEL"] = args.scale_label
    env["LDBC_FRAMEWORK_OUTPUT_DIR"] = str(framework_output_dir)

    command = [
        "jupyter",
        "nbconvert",
        "--to",
        "notebook",
        "--execute",
        str(notebook),
        "--output",
        "ldbc_snb_framework_executed.ipynb",
        "--output-dir",
        str(executed_dir),
        f"--ExecutePreprocessor.timeout={args.timeout}",
    ]

    print("Executing LDBC SNB framework notebook...")
    print(" ".join(command))
    subprocess.run(command, check=True, cwd=run_root, env=env)

    generated_artifacts_dir = (
        framework_output_dir
        / "benchmark_artifacts_dir"
        / "ldbc_snb_mongo_configurations"
    )

    generated_info = validate_artifacts(generated_artifacts_dir, run_root)

    if benchmark_output_dir.exists():
        shutil.rmtree(benchmark_output_dir)
    shutil.copytree(generated_artifacts_dir, benchmark_output_dir)

    benchmark_info = validate_artifacts(benchmark_output_dir, run_root)

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "notebook": display_path(notebook, run_root),
        "scale_label": args.scale_label,
        "framework_output_dir": display_path(framework_output_dir, run_root),
        "benchmark_output_dir": display_path(benchmark_output_dir, run_root),
        "note": "The external LDBC SNB data directory is intentionally not stored to avoid machine-specific paths.",
        "generated_artifacts": {
            "framework_artifacts": generated_info,
            "benchmark_artifacts": benchmark_info,
        },
    }

    manifest_path = framework_output_dir / "framework_artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("LDBC SNB framework artifacts generated.")
    print(f" - {benchmark_output_dir}")
    print(f" - {manifest_path}")


if __name__ == "__main__":
    main()
