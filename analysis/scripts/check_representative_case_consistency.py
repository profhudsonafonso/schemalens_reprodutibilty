#!/usr/bin/env python3
"""
Check and clarify representative-case consistency for SchemaLens.

Purpose
-------
This script verifies whether the representative-case report is mixing two related,
but different, concepts:

1. activation_matrix_classes:
   Classes directly activated by the activation matrix.

2. schema_lens_selected_classes:
   Classes effectively selected for the benchmark by SchemaLens, including primary
   and secondary_affected groups, but excluding CONTROL.

This distinction is important because a winner may not appear in the raw activation
matrix classes but may still be part of the final SchemaLens benchmark-selected
space through the secondary_affected / benchmark-selection stage.

Inputs
------
Expected files under analysis/generated:

- representative_case_table.csv
- query_class_activation_all_datasets.csv
- benchmark_configuration_selection_all_datasets.csv

Optional:
- representative_case_analysis.md

Outputs
-------
- analysis/generated/representative_case_table_checked.csv
- analysis/generated/representative_case_consistency_issues.csv
- analysis/generated/representative_case_consistency_report.txt
- analysis/generated/advisor_representative_cases_section.md

Usage
-----
From the repository root:

    python analysis/scripts/check_representative_case_consistency.py

Optional:

    python analysis/scripts/check_representative_case_consistency.py \
        --generated-dir analysis/generated

Notes
-----
This script does not rerun MongoDB benchmarks and does not infer latency for
unmeasured configurations.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


ORDERED_CASES = [
    ("imdb", "QG6_EpisodesOfSeries"),
    ("imdb", "QG10_AdvancedSearchWatchItems"),
    ("fiben", "Q10_CreateAccountHoldingAndBuyTransaction"),
    ("fiben", "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity"),
    ("ldbc_snb", "IC1_TransitiveFriendsWithName"),
    ("ldbc_snb", "IC5_NewGroups"),
    ("ldbc_snb", "IC7_RecentLikers"),
    ("ldbc_snb", "IS2_RecentMessagesOfPerson"),
    ("ldbc_snb", "IS6_ForumOfMessage"),
    ("ldbc_snb", "IS7_RepliesOfMessage"),
]


CASE_COMMENTS = {
    ("ldbc_snb", "IC1_TransitiveFriendsWithName"): (
        "This is a strong official workload case. High traversal depth and residual traversal "
        "over associative relationships explain why a reference/summary-oriented Person-rooted "
        "configuration remains competitive instead of full embedding."
    ),
    ("ldbc_snb", "IC5_NewGroups"): (
        "This case is useful to justify secondary_affected candidates. The winners are secondary "
        "families across scales, showing that mixed association/containment workloads require more "
        "than only the primary family."
    ),
    ("ldbc_snb", "IC7_RecentLikers"): (
        "This query combines likes, message ownership, and friendship checks. The alternation between "
        "G4 and G3 shows that explicit associative-edge and reference-aware designs are both relevant "
        "under graph-like access."
    ),
    ("ldbc_snb", "IS2_RecentMessagesOfPerson"): (
        "This short-read case is compact but still has mixed message structures and residual traversal. "
        "It supports the need to preserve several secondary alternatives instead of choosing a single "
        "fixed document pattern."
    ),
    ("ldbc_snb", "IS6_ForumOfMessage"): (
        "This is a good containment/hybrid example. Even though the path is containment-like, residual "
        "traversal remains, explaining why hybrid or reference-aware candidates can win."
    ),
    ("ldbc_snb", "IS7_RepliesOfMessage"): (
        "This short-read case mixes replies, authors, and author relationships. It is useful for showing "
        "that update-aware and hybrid candidates can matter even in compact access patterns."
    ),
    ("fiben", "Q10_CreateAccountHoldingAndBuyTransaction"): (
        "This is the best FIBEN case for update volatility. The query creates relationships under high "
        "update pressure, so the winner changes across scales rather than always favoring embedding."
    ),
    ("fiben", "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity"): (
        "This is the main scale-sensitive FIBEN case. CONTROL wins at sf1, but activated designs win at "
        "larger scales, suggesting that the benefit of the activated space becomes clearer as traversal "
        "cost grows."
    ),
    ("imdb", "QG6_EpisodesOfSeries"): (
        "This is the canonical IMDb containment case. It fails at sf0.25, where a simple control candidate "
        "wins, but the expected containment family wins at sf0.5 and sf1."
    ),
    ("imdb", "QG10_AdvancedSearchWatchItems"): (
        "This is the IMDb sharedness/filtering case. Use it after checking the activation-vs-selection "
        "distinction, because the winners are secondary/hybrid candidates that may be selected beyond the "
        "raw activation-matrix classes."
    ),
}


def read_csv_if_exists(path: Path, required: bool = False) -> pd.DataFrame:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Required file not found: {path}")
        return pd.DataFrame()
    return pd.read_csv(path)


def find_col(df: pd.DataFrame, candidates: Iterable[str], required: bool = False) -> Optional[str]:
    if df.empty:
        if required:
            raise ValueError("Cannot find column in an empty DataFrame.")
        return None

    lower_map = {c.lower(): c for c in df.columns}
    for name in candidates:
        if name.lower() in lower_map:
            return lower_map[name.lower()]

    # relaxed matching: remove punctuation/underscore/case
    def norm(x: str) -> str:
        return re.sub(r"[^a-z0-9]", "", x.lower())

    norm_map = {norm(c): c for c in df.columns}
    for name in candidates:
        key = norm(name)
        if key in norm_map:
            return norm_map[key]

    if required:
        raise ValueError(
            f"Could not find any of the expected columns: {list(candidates)}\n"
            f"Available columns: {list(df.columns)}"
        )
    return None


def normalize_dataset(value) -> str:
    return str(value).strip().lower()


def normalize_query(value) -> str:
    return str(value).strip()


def normalize_class(value) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    upper = text.upper()
    if upper in {"CONTROL", "CTRL", "G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9"}:
        return upper if upper == "CONTROL" else upper
    match = re.search(r"\bG\d+\b|CONTROL", upper)
    return match.group(0) if match else text


def class_set_to_string(values: Iterable[str]) -> str:
    cleaned = sorted({normalize_class(v) for v in values if normalize_class(v)})
    return "|".join(cleaned)


def truthy(value) -> bool:
    if pd.isna(value):
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "active", "activated", "selected"}


def filter_by_case(df: pd.DataFrame, dataset: str, query_name: str, scale_label: Optional[str] = None) -> pd.DataFrame:
    if df.empty:
        return df

    dataset_col = find_col(df, ["dataset", "dataset_name"], required=False)
    query_col = find_col(df, ["query_name", "query", "workload_query"], required=False)
    scale_col = find_col(df, ["scale_label", "scale", "scale_name"], required=False)

    out = df.copy()

    if dataset_col:
        out = out[out[dataset_col].astype(str).str.lower().str.strip() == dataset.lower().strip()]
    if query_col:
        out = out[out[query_col].astype(str).str.strip() == query_name.strip()]
    if scale_label and scale_col:
        scale_filtered = out[out[scale_col].astype(str).str.strip() == str(scale_label).strip()]
        # Some selection/activation files are query-level rather than scale-level.
        # Only use scale filtering if it returns rows.
        if not scale_filtered.empty:
            out = scale_filtered

    return out


def extract_classes_from_df(df: pd.DataFrame, role: str) -> set[str]:
    if df.empty:
        return set()

    class_col = find_col(
        df,
        [
            "g_class",
            "G_class",
            "gclass",
            "g_class_id",
            "candidate_g_class",
            "candidate_class",
            "configuration_class",
            "config_class",
            "class_id",
            "template",
            "schema_template",
        ],
        required=False,
    )

    if class_col:
        raw = df[class_col].dropna().astype(str).tolist()
    else:
        # fallback: scan all row values for G0..G9 or CONTROL
        raw = []
        for _, row in df.iterrows():
            text = " ".join(str(v) for v in row.values if not pd.isna(v))
            raw.extend(re.findall(r"\bG\d+\b|CONTROL", text.upper()))

    return {normalize_class(x) for x in raw if normalize_class(x)}


def extract_activation_classes(activation_df: pd.DataFrame, dataset: str, query_name: str, scale_label: Optional[str]) -> set[str]:
    sub = filter_by_case(activation_df, dataset, query_name, scale_label)
    if sub.empty:
        return set()

    active_col = find_col(
        sub,
        ["is_active", "active", "activated", "is_activated", "activation", "selected"],
        required=False,
    )

    if active_col:
        # Keep active rows when a clear active flag exists. If the column is textual and contains
        # class names, this filter may remove everything; in that case, fall back to all rows.
        filtered = sub[sub[active_col].apply(truthy)]
        if not filtered.empty:
            sub = filtered

    return extract_classes_from_df(sub, role="activation")


def extract_selection_classes(selection_df: pd.DataFrame, dataset: str, query_name: str, scale_label: Optional[str]) -> tuple[set[str], set[str]]:
    sub = filter_by_case(selection_df, dataset, query_name, scale_label)
    if sub.empty:
        return set(), set()

    all_measured = extract_classes_from_df(sub, role="measured")

    group_col = find_col(
        sub,
        ["benchmark_group", "group", "candidate_group", "selection_group", "schema_lens_group", "role"],
        required=False,
    )

    if group_col:
        non_control = sub[
            ~sub[group_col].astype(str).str.lower().str.contains("control", na=False)
        ]
        schema_lens_selected = extract_classes_from_df(non_control, role="schema_lens_selected")
    else:
        # If no group is available, use every non-CONTROL class as a conservative approximation.
        schema_lens_selected = {c for c in all_measured if c != "CONTROL"}

    schema_lens_selected = {c for c in schema_lens_selected if c and c != "CONTROL"}
    return all_measured, schema_lens_selected


def build_checked_table(generated_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    rep_path = generated_dir / "representative_case_table.csv"
    activation_path = generated_dir / "query_class_activation_all_datasets.csv"
    selection_path = generated_dir / "benchmark_configuration_selection_all_datasets.csv"

    rep = read_csv_if_exists(rep_path, required=True)
    activation = read_csv_if_exists(activation_path, required=False)
    selection = read_csv_if_exists(selection_path, required=False)

    dataset_col = find_col(rep, ["dataset", "dataset_name"], required=True)
    query_col = find_col(rep, ["query_name", "query"], required=True)
    scale_col = find_col(rep, ["scale_label", "scale", "scale_name"], required=False)
    best_col = find_col(rep, ["global_best_g_class", "best_g_class", "winner_g_class"], required=True)
    top1_col = find_col(rep, ["schema_lens_top1_preserved", "top1_preserved"], required=True)
    near_col = find_col(rep, ["schema_lens_near_best_preserved", "near_best_preserved"], required=False)

    checked_rows = []
    issue_rows = []

    for idx, row in rep.iterrows():
        dataset = normalize_dataset(row[dataset_col])
        query_name = normalize_query(row[query_col])
        scale_label = str(row[scale_col]).strip() if scale_col else None
        global_best = normalize_class(row[best_col])
        top1_preserved = truthy(row[top1_col])
        near_preserved = truthy(row[near_col]) if near_col else None

        activation_classes = extract_activation_classes(activation, dataset, query_name, scale_label)
        measured_classes, schema_lens_selected_classes = extract_selection_classes(selection, dataset, query_name, scale_label)

        in_activation = global_best in activation_classes if activation_classes else None
        in_selected = global_best in schema_lens_selected_classes if schema_lens_selected_classes else None
        in_measured = global_best in measured_classes if measured_classes else None

        if global_best == "CONTROL":
            status = "CONTROL_WINNER"
            explanation = (
                "The global winner is CONTROL. This is a genuine missed Top-1 case if "
                "schema_lens_top1_preserved=0; it should be discussed as a failure or scale-sensitive case."
            )
        elif top1_preserved and in_selected is True:
            if in_activation is False:
                status = "OK_SELECTED_BEYOND_RAW_ACTIVATION"
                explanation = (
                    "The global winner is not listed in the raw activation-matrix classes, but it is in the "
                    "final SchemaLens benchmark-selected space. Report activation_matrix_classes and "
                    "schema_lens_selected_classes separately."
                )
            else:
                status = "OK"
                explanation = (
                    "The global winner is inside the final SchemaLens-selected benchmark space."
                )
        elif top1_preserved and in_selected is None:
            status = "CHECK_SELECTION_DATA_MISSING"
            explanation = (
                "Top-1 is marked as preserved, but the benchmark-selection file was missing or could not be "
                "matched. Verify the selection file before using this row in the paper."
            )
        elif top1_preserved and in_selected is False:
            status = "INCONSISTENT_TOP1_FLAG"
            explanation = (
                "Top-1 is marked as preserved, but the global winner was not found in the final "
                "SchemaLens-selected classes. This row requires correction before reporting."
            )
        else:
            status = "NOT_PRESERVED"
            explanation = (
                "SchemaLens did not preserve the measured Top-1 for this case/scale. Use as failure or "
                "near-failure evidence."
            )

        out = row.to_dict()
        out["activation_matrix_classes"] = class_set_to_string(activation_classes)
        out["benchmark_measured_classes"] = class_set_to_string(measured_classes)
        out["schema_lens_selected_classes"] = class_set_to_string(schema_lens_selected_classes)
        out["global_best_in_activation_matrix"] = in_activation
        out["global_best_in_schema_lens_selected_space"] = in_selected
        out["global_best_in_measured_space"] = in_measured
        out["consistency_status"] = status
        out["consistency_explanation"] = explanation
        checked_rows.append(out)

        if status in {
            "OK_SELECTED_BEYOND_RAW_ACTIVATION",
            "CHECK_SELECTION_DATA_MISSING",
            "INCONSISTENT_TOP1_FLAG",
            "CONTROL_WINNER",
            "NOT_PRESERVED",
        }:
            issue_rows.append({
                "dataset": dataset,
                "query_name": query_name,
                "scale_label": scale_label,
                "global_best_g_class": global_best,
                "schema_lens_top1_preserved": int(top1_preserved),
                "schema_lens_near_best_preserved": "" if near_preserved is None else int(near_preserved),
                "activation_matrix_classes": class_set_to_string(activation_classes),
                "schema_lens_selected_classes": class_set_to_string(schema_lens_selected_classes),
                "benchmark_measured_classes": class_set_to_string(measured_classes),
                "consistency_status": status,
                "consistency_explanation": explanation,
            })

    checked = pd.DataFrame(checked_rows)
    issues = pd.DataFrame(issue_rows)

    report = build_text_report(checked, issues, activation_path, selection_path)
    return checked, issues, report


def build_text_report(checked: pd.DataFrame, issues: pd.DataFrame, activation_path: Path, selection_path: Path) -> str:
    total = len(checked)
    status_counts = checked["consistency_status"].value_counts(dropna=False).to_dict()

    lines = []
    lines.append("# Representative Case Consistency Report")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("This report checks whether representative cases distinguish raw activation-matrix classes from the final SchemaLens benchmark-selected space.")
    lines.append("")
    lines.append("## Input availability")
    lines.append("")
    lines.append(f"- Activation file found: `{activation_path}` -> {activation_path.exists()}")
    lines.append(f"- Benchmark-selection file found: `{selection_path}` -> {selection_path.exists()}")
    lines.append("")
    lines.append("## Status summary")
    lines.append("")
    lines.append(f"- Total representative rows checked: {total}")
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status}: {count}")

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- `OK` means the measured winner is inside the final SchemaLens-selected benchmark space.")
    lines.append("- `OK_SELECTED_BEYOND_RAW_ACTIVATION` means the winner was preserved through the benchmark-selection/secondary stage, but it is not listed in the raw activation matrix. This is not necessarily an experimental error, but the report should name both sets separately.")
    lines.append("- `CONTROL_WINNER` and `NOT_PRESERVED` should be treated as failure or scale-sensitive cases.")
    lines.append("- `INCONSISTENT_TOP1_FLAG` requires correction before the row is used in the paper.")

    if not issues.empty:
        lines.append("")
        lines.append("## Rows requiring attention")
        lines.append("")
        display_cols = [
            "dataset",
            "query_name",
            "scale_label",
            "global_best_g_class",
            "schema_lens_top1_preserved",
            "activation_matrix_classes",
            "schema_lens_selected_classes",
            "consistency_status",
        ]
        keep_cols = [c for c in display_cols if c in issues.columns]
        lines.append(issues[keep_cols].to_markdown(index=False))

    return "\n".join(lines) + "\n"


def compact_winner_string(group: pd.DataFrame) -> str:
    parts = []
    for _, row in group.iterrows():
        scale = row.get("scale_label", row.get("scale", ""))
        winner = normalize_class(row.get("global_best_g_class", ""))
        benchmark_group = str(row.get("global_best_benchmark_group", "")).strip()
        p95 = row.get("global_best_p95_ms", "")
        try:
            p95_text = f"{float(p95):.4g} ms"
        except Exception:
            p95_text = str(p95)
        if benchmark_group:
            parts.append(f"{scale}: {winner} ({benchmark_group}, {p95_text})")
        else:
            parts.append(f"{scale}: {winner} ({p95_text})")
    return "; ".join(parts)


def first_non_empty(group: pd.DataFrame, col: str) -> str:
    if col not in group.columns:
        return ""
    for value in group[col].tolist():
        if pd.notna(value) and str(value).strip():
            return str(value).strip()
    return ""


def generate_advisor_section(checked: pd.DataFrame) -> str:
    dataset_col = find_col(checked, ["dataset"], required=True)
    query_col = find_col(checked, ["query_name"], required=True)
    top1_col = find_col(checked, ["schema_lens_top1_preserved"], required=True)
    near_col = find_col(checked, ["schema_lens_near_best_preserved"], required=False)

    lines = []
    lines.append("## Representative-case analysis")
    lines.append("")
    lines.append("I added a representative-case analysis to connect the analytical variables used by SchemaLens with the measured benchmark winners. The goal is to move the experimental section beyond aggregate preservation metrics and explain why particular configuration families win under specific workload and data characteristics.")
    lines.append("")
    lines.append("The analysis uses only measured hot-run p95 results. No MongoDB benchmark is rerun, no latency is inferred for unmeasured configurations, and root-choice ablation is not included because it would require materializing and benchmarking alternative-root candidates.")
    lines.append("")
    lines.append("### Representative cases and interpretation")
    lines.append("")
    lines.append("| Dataset | Query | Pattern / key signal | Hot-run winner(s) across scales | Preservation | Interpretation |")
    lines.append("|---|---|---|---|---|---|")

    for dataset, query in ORDERED_CASES:
        mask = (
            checked[dataset_col].astype(str).str.lower().str.strip().eq(dataset)
            & checked[query_col].astype(str).str.strip().eq(query)
        )
        group = checked[mask].copy()
        if group.empty:
            continue

        top1_count = int(group[top1_col].apply(truthy).sum())
        total = len(group)
        near_count = int(group[near_col].apply(truthy).sum()) if near_col else 0

        case_focus = first_non_empty(group, "case_focus")
        root = first_non_empty(group, "selected_root")
        rc = first_non_empty(group, "Rc")
        d = first_non_empty(group, "D")
        re_value = first_non_empty(group, "Re")
        delta = first_non_empty(group, "DeltaRratio")
        semantic = first_non_empty(group, "dominant_semantic_type")

        signal = f"{case_focus}; root={root}; Rc={rc}; D={d}; Re={re_value}; DeltaRratio={delta}; semantic={semantic}"
        winners = compact_winner_string(group)
        preservation = f"Top-1 {top1_count}/{total}; near-best {near_count}/{total}"
        comment = CASE_COMMENTS.get((dataset, query), "")

        lines.append(
            f"| {dataset} | `{query}` | {signal} | {winners} | {preservation} | {comment} |"
        )

    failures = checked[
        (~checked[top1_col].apply(truthy))
        | ((near_col is not None) & (~checked[near_col].apply(truthy)))
    ].copy()

    lines.append("")
    lines.append("### Failure and near-failure cases")
    lines.append("")
    lines.append("| Dataset | Query | Scale | Winner | Best SchemaLens candidate / regret | Interpretation |")
    lines.append("|---|---|---|---|---|---|")

    if failures.empty:
        lines.append("| - | - | - | - | - | No failure or near-failure rows were detected in the representative-case table. |")
    else:
        for _, row in failures.iterrows():
            dataset = row.get("dataset", "")
            query = row.get("query_name", "")
            scale = row.get("scale_label", "")
            winner = normalize_class(row.get("global_best_g_class", ""))
            group = row.get("global_best_benchmark_group", "")
            p95 = row.get("global_best_p95_ms", "")
            best_schema = normalize_class(row.get("best_schema_lens_g_class", row.get("schema_lens_best_g_class", "")))
            regret = row.get("schema_lens_relative_regret", "")
            try:
                regret_text = f"{float(regret):.4f}"
            except Exception:
                regret_text = str(regret)

            if dataset == "imdb" and query == "QG6_EpisodesOfSeries":
                interp = "Small-scale containment failure: a simple control/primary-style candidate wins at sf0.25, but the containment family wins at larger scales."
            elif dataset == "fiben" and query == "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity":
                interp = "Scale-sensitive deep-traversal failure: CONTROL wins at sf1, while activated configurations win at sf10 and sf30."
            else:
                interp = "Use as a failure or near-failure case and inspect whether the miss is scale-sensitive, control-driven, or due to missing activation signals."

            lines.append(
                f"| {dataset} | `{query}` | {scale} | {winner} ({group}, p95={p95}) | {best_schema}; regret={regret_text} | {interp} |"
            )

    lines.append("")
    lines.append("### Main takeaways")
    lines.append("")
    lines.append("1. The representative cases show that SchemaLens does not simply choose embedding or references by default. Different workload/data characteristics lead to different winning families.")
    lines.append("2. LDBC SNB provides the strongest evidence because it is an official workload and the selected cases consistently preserve Top-1 or near-best configurations.")
    lines.append("3. Secondary_affected candidates are important: several winners come from this group, especially in mixed association/containment cases.")
    lines.append("4. The failure cases are informative rather than fatal: IMDb QG6 at sf0.25 and FIBEN Q4 at sf1 are small-scale or scale-sensitive misses, while larger scales preserve the activated winners.")
    lines.append("5. For the final paper text, activation-matrix classes and final SchemaLens benchmark-selected classes should be reported separately to avoid ambiguity.")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--generated-dir",
        default="analysis/generated",
        help="Path to the analysis/generated directory.",
    )
    args = parser.parse_args()

    generated_dir = Path(args.generated_dir)
    generated_dir.mkdir(parents=True, exist_ok=True)

    checked, issues, report = build_checked_table(generated_dir)

    checked_path = generated_dir / "representative_case_table_checked.csv"
    issues_path = generated_dir / "representative_case_consistency_issues.csv"
    report_path = generated_dir / "representative_case_consistency_report.txt"
    advisor_path = generated_dir / "advisor_representative_cases_section.md"

    checked.to_csv(checked_path, index=False)
    issues.to_csv(issues_path, index=False)
    report_path.write_text(report, encoding="utf-8")
    advisor_path.write_text(generate_advisor_section(checked), encoding="utf-8")

    print(f"Saved: {checked_path}")
    print(f"Saved: {issues_path}")
    print(f"Saved: {report_path}")
    print(f"Saved: {advisor_path}")

    status_counts = checked["consistency_status"].value_counts(dropna=False).to_dict()
    print("Status summary:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")


if __name__ == "__main__":
    main()
