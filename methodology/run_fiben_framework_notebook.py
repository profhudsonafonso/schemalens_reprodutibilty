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
        description="Execute the FIBEN framework notebook and export benchmark artifacts."
    )
    parser.add_argument("--notebook", default="fiben_methodology_core.ipynb")
    parser.add_argument("--fiben-sf-root", required=True)
    parser.add_argument("--active-scale-label", default="SF1", choices=["SF1", "SF10", "SF30"])
    parser.add_argument("--framework-output-dir", default="output/framework")
    parser.add_argument("--benchmark-output-dir", default="output/benchmark")
    parser.add_argument("--timeout", default="-1")
    return parser.parse_args()


def resolve_scale_dir(root: Path, scale_label: str) -> Path:
    candidates = {
        "SF1": [root / "sf1_materialized" / "tables"],
        "SF10": [root / "scaled_corp_rooted" / "SF10" / "tables"],
        "SF30": [root / "scaled_corp_rooted" / "SF30" / "tables"],
    }

    for candidate in candidates[scale_label]:
        if candidate.exists():
            return candidate

    tried = ", ".join(str(p) for p in candidates[scale_label])
    raise FileNotFoundError(f"No FIBEN scale folder found for {scale_label}. Tried: {tried}")


def validate_artifacts(artifacts_dir: Path, root: Path) -> dict:
    info = {}

    for name in REQUIRED_ARTIFACTS:
        path = artifacts_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Required FIBEN artifact not found: {path}")
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

    if n_rows != 60:
        raise ValueError(f"Expected 60 FIBEN benchmark plan rows, observed {n_rows}.")

    if len(specs) != 60:
        raise ValueError(f"Expected 60 FIBEN candidate specs, observed {len(specs)}.")

    return info


def main() -> None:
    args = parse_args()

    run_root = Path.cwd().resolve()
    notebook = Path(args.notebook).resolve()
    fiben_sf_root = Path(args.fiben_sf_root).expanduser().resolve()
    framework_output_dir = Path(args.framework_output_dir).resolve()
    benchmark_output_dir = Path(args.benchmark_output_dir).resolve()

    if not notebook.exists():
        raise FileNotFoundError(f"Notebook not found: {notebook}")

    scale_dir = resolve_scale_dir(fiben_sf_root, args.active_scale_label)

    framework_output_dir.mkdir(parents=True, exist_ok=True)
    benchmark_output_dir.mkdir(parents=True, exist_ok=True)

    executed_dir = framework_output_dir / "executed_notebooks"
    executed_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["FIBEN_SF_ROOT"] = str(fiben_sf_root)
    env["FIBEN_ACTIVE_SCALE"] = args.active_scale_label
    env["FIBEN_FRAMEWORK_OUTPUT_DIR"] = str(framework_output_dir)

    command = [
        "jupyter",
        "nbconvert",
        "--to",
        "notebook",
        "--execute",
        str(notebook),
        "--output",
        "fiben_framework_executed.ipynb",
        "--output-dir",
        str(executed_dir),
        f"--ExecutePreprocessor.timeout={args.timeout}",
    ]

    print("Executing FIBEN framework notebook...")
    print(" ".join(command))
    subprocess.run(command, check=True, cwd=run_root, env=env)

    generated_artifacts_dir = (
        framework_output_dir
        / "benchmark_artifacts"
        / "fiben_mongodb_configurations"
    )

    generated_info = validate_artifacts(generated_artifacts_dir, run_root)

    if benchmark_output_dir.exists():
        shutil.rmtree(benchmark_output_dir)
    shutil.copytree(generated_artifacts_dir, benchmark_output_dir)

    benchmark_info = validate_artifacts(benchmark_output_dir, run_root)

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "notebook": display_path(notebook, run_root),
        "active_scale_label": args.active_scale_label,
        "resolved_scale_folder_name": scale_dir.name,
        "framework_output_dir": display_path(framework_output_dir, run_root),
        "benchmark_output_dir": display_path(benchmark_output_dir, run_root),
        "note": "The external FIBEN scale-factor root is intentionally not stored to avoid machine-specific paths.",
        "generated_artifacts": {
            "framework_artifacts": generated_info,
            "benchmark_artifacts": benchmark_info,
        },
    }

    manifest_path = framework_output_dir / "framework_artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("FIBEN framework artifacts generated.")
    print(f" - {benchmark_output_dir}")
    print(f" - {manifest_path}")


if __name__ == "__main__":
    main()
