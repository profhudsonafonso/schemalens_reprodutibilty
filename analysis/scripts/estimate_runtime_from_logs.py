from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

LOG_GLOBS = [
    "analysis/generated/**/*.log",
]

OUT_CSV = ROOT / "analysis/generated/runtime_estimates_from_logs.csv"
OUT_MD = ROOT / "docs/runtime_estimates.md"

TS_RE = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")


def classify_log(path: Path) -> tuple[str, str, str]:
    rel = path.relative_to(ROOT).as_posix()
    parent = path.parent.name

    dataset = "unknown"
    scenario = parent
    reproduction_level = "benchmark evidence"

    if "/imdb/" in rel:
        dataset = "IMDb"
    elif "/fiben/" in rel:
        dataset = "FIBEN"
    elif "/ldbc_snb/" in rel:
        dataset = "LDBC SNB"

    if "qg9_validation" in rel:
        scenario = "IMDb QG9 query-plan validation"
        reproduction_level = "query-plan validation"
    elif "group_A_light_no_roles" in rel:
        scenario = "IMDb query-plan Group A"
        reproduction_level = "query-plan validation"
    elif "group_B_episodes" in rel:
        scenario = "IMDb query-plan Group B / QG6"
        reproduction_level = "query-plan validation"
    elif "group_D_insert_qg8" in rel:
        scenario = "IMDb query-plan Group D / QG8"
        reproduction_level = "query-plan validation"
    elif "group_C_roles_sf025" in rel:
        scenario = "IMDb query-plan Group C roles / sf0.25"
        reproduction_level = "query-plan validation"
    elif "group_C_roles_sf050" in rel:
        scenario = "IMDb query-plan Group C roles / sf0.5"
        reproduction_level = "query-plan validation"
    elif "group_C_roles_sf1_assoc_only" in rel:
        scenario = "IMDb query-plan Group C assoc-only / sf1"
        reproduction_level = "query-plan validation"
    elif "group_C_qg5_sf1_assoc_only_with_episodes" in rel:
        scenario = "IMDb query-plan QG5 assoc-only with episodes / sf1"
        reproduction_level = "query-plan validation"

    return dataset, scenario, reproduction_level


def parse_timestamps(path: Path) -> list[datetime]:
    timestamps: list[datetime] = []

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return timestamps

    for match in TS_RE.finditer(text):
        timestamps.append(datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S"))

    return timestamps


def format_duration(seconds: float) -> str:
    seconds = int(round(seconds))

    if seconds < 60:
        return f"{seconds} sec"

    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} min {sec} sec"

    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes} min"


def collect_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    logs: list[Path] = []
    for pattern in LOG_GLOBS:
        logs.extend(ROOT.glob(pattern))

    for path in sorted(set(logs)):
        timestamps = parse_timestamps(path)
        rel = path.relative_to(ROOT).as_posix()
        dataset, scenario, reproduction_level = classify_log(path)

        if not timestamps:
            rows.append(
                {
                    "dataset": dataset,
                    "scenario": scenario,
                    "reproduction_level": reproduction_level,
                    "log_file": rel,
                    "start_time": "",
                    "end_time": "",
                    "runtime_seconds": "",
                    "runtime_human": "not available",
                    "note": "No parseable timestamps found.",
                }
            )
            continue

        start = min(timestamps)
        end = max(timestamps)
        runtime_seconds = (end - start).total_seconds()

        rows.append(
            {
                "dataset": dataset,
                "scenario": scenario,
                "reproduction_level": reproduction_level,
                "log_file": rel,
                "start_time": start.isoformat(sep=" "),
                "end_time": end.isoformat(sep=" "),
                "runtime_seconds": str(int(runtime_seconds)),
                "runtime_human": format_duration(runtime_seconds),
                "note": "Observed wall-clock interval from first to last timestamp in the log.",
            }
        )

    return rows


def write_csv(rows: list[dict[str, str]]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "dataset",
        "scenario",
        "reproduction_level",
        "log_file",
        "start_time",
        "end_time",
        "runtime_seconds",
        "runtime_human",
        "note",
    ]

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict[str, str]]) -> None:
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Runtime Estimates")
    lines.append("")
    lines.append("This document reports observed runtime estimates extracted from execution logs included in the artifact.")
    lines.append("")
    lines.append("The reported values are wall-clock intervals between the first and last parseable timestamp in each log file.")
    lines.append("They should be interpreted as approximate machine-specific guidance, not hardware-independent guarantees.")
    lines.append("")
    lines.append("## Lightweight verification")
    lines.append("")
    lines.append("| Scenario | Command | Requires MongoDB | Requires external data | Expected time |")
    lines.append("|---|---|---:|---:|---:|")
    lines.append("| Artifact check | `make check-artifact` | no | no | seconds |")
    lines.append("| Short-paper table reproduction | `make reproduce-paper` | no | no | less than 1 minute |")
    lines.append("| Analysis pipeline | `make analysis-pipeline` | no | no | minutes |")
    lines.append("")
    lines.append("## Runtime estimates from available logs")
    lines.append("")
    lines.append("| Dataset | Scenario | Runtime | Log file |")
    lines.append("|---|---|---:|---|")

    for row in rows:
        lines.append(
            f"| {row['dataset']} | {row['scenario']} | {row['runtime_human']} | `{row['log_file']}` |"
        )

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Full benchmark runtimes depend on hardware, storage, Docker performance, and selected scale factor.")
    lines.append("- Some full benchmark runs may not have complete execution logs in this lightweight artifact.")
    lines.append("- Query-plan validation logs are included as reproducibility evidence for selected IMDb cases.")
    lines.append("- The Makefile benchmark targets provide entry points for rerunning full benchmarks when local datasets are available.")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = collect_rows()
    write_csv(rows)
    write_markdown(rows)

    print(f"Wrote {OUT_CSV.relative_to(ROOT)}")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")
    print(f"Parsed log files: {len(rows)}")


if __name__ == "__main__":
    main()
