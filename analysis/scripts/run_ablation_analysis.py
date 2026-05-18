from pathlib import Path
import re
import pandas as pd


NEAR_BEST_THRESHOLD = 0.05

ABLATION_VARIANTS = [
    "full_schema_lens",
    "no_relationship_semantics",
    "no_depth",
    "no_residual_traversal",
    "no_sharedness",
    "no_update_volatility",
    "no_relationship_semantics_no_depth",
]


SEMANTIC_CLASSES = {"G1", "G2", "G3", "G5", "G6", "G8"}
DEPTH_CLASSES = {"G4", "G8"}
RESIDUAL_CLASSES = {"G4", "G8", "G9"}
SHAREDNESS_CLASSES = {"G5", "G6"}
UPDATE_CLASSES = {"G7"}

ROOT_FALLBACK_CLASSES = ["G0"]


def safe_str(value):
    if pd.isna(value):
        return ""
    return str(value)


def to_float(value):
    if pd.isna(value):
        return None
    try:
        return float(value)
    except Exception:
        return None


def to_bool(value):
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    if text in {"true", "1", "yes", "y"}:
        return True

    if text in {"false", "0", "no", "n", "", "nan", "none"}:
        return False

    return False


def string_to_classes(value):
    if pd.isna(value):
        return set()

    text = str(value).strip()

    if text == "":
        return set()

    return {x.strip().upper() for x in text.split("|") if x.strip()}


def classes_to_string(classes):
    classes = sorted({str(c).strip().upper() for c in classes if str(c).strip()})
    return "|".join(classes)


def normalize_g_class(value):
    return safe_str(value).strip().upper()


def contains_any(text, keywords):
    text = safe_str(text).lower()
    return any(k.lower() in text for k in keywords)


def load_inputs(repo_root: Path):
    generated = repo_root / "analysis" / "generated"

    aggregate_path = generated / "aggregate_results_all_datasets.csv"
    query_path = generated / "query_analytical_metadata_all_datasets.csv"
    activation_path = generated / "query_class_activation_all_datasets.csv"
    benchmark_path = generated / "benchmark_configuration_selection_all_datasets.csv"

    for path in [aggregate_path, query_path, activation_path, benchmark_path]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required input file: {path}")

    aggregate_df = pd.read_csv(aggregate_path, encoding="utf-8-sig")
    query_df = pd.read_csv(query_path, encoding="utf-8-sig")
    activation_df = pd.read_csv(activation_path, encoding="utf-8-sig")
    benchmark_df = pd.read_csv(benchmark_path, encoding="utf-8-sig")

    aggregate_df["dataset"] = aggregate_df["dataset"].astype(str)
    aggregate_df["scale_label"] = aggregate_df["scale_label"].astype(str)
    aggregate_df["query_name"] = aggregate_df["query_name"].astype(str)
    aggregate_df["run_phase"] = aggregate_df["run_phase"].astype(str).str.lower()
    aggregate_df["config_id"] = aggregate_df["config_id"].astype(str)
    aggregate_df["g_class"] = aggregate_df["g_class"].astype(str).str.upper()
    aggregate_df["benchmark_group"] = aggregate_df["benchmark_group"].astype(str).str.lower()
    aggregate_df["p95_latency_ms"] = pd.to_numeric(
        aggregate_df["p95_latency_ms"], errors="coerce"
    )

    query_df["dataset"] = query_df["dataset"].astype(str)
    query_df["query_name"] = query_df["query_name"].astype(str)

    activation_df["dataset"] = activation_df["dataset"].astype(str)
    activation_df["query_name"] = activation_df["query_name"].astype(str)
    activation_df["g_class"] = activation_df["g_class"].astype(str).str.upper()
    activation_df["is_active"] = activation_df["is_active"].apply(to_bool)

    benchmark_df["dataset"] = benchmark_df["dataset"].astype(str)
    benchmark_df["query_name"] = benchmark_df["query_name"].astype(str)
    benchmark_df["g_class"] = benchmark_df["g_class"].astype(str).str.upper()
    benchmark_df["benchmark_group"] = benchmark_df["benchmark_group"].astype(str).str.lower()
    benchmark_df["config_id"] = benchmark_df["config_id"].astype(str)

    return aggregate_df, query_df, activation_df, benchmark_df


def build_query_metadata_lookup(query_df):
    lookup = {}

    for _, row in query_df.iterrows():
        key = (row["dataset"], row["query_name"])
        lookup[key] = row

    return lookup


def build_activation_evidence_lookup(activation_df):
    active_df = activation_df[activation_df["is_active"] == True].copy()

    lookup = {}

    for _, row in active_df.iterrows():
        key = (row["dataset"], row["query_name"], row["g_class"])

        evidence = " ".join(
            [
                safe_str(row.get("activation_status", "")),
                safe_str(row.get("activation_strength", "")),
                safe_str(row.get("activation_reason", "")),
                safe_str(row.get("g_family", "")),
                safe_str(row.get("g_role", "")),
                safe_str(row.get("g_label", "")),
            ]
        )

        lookup[key] = evidence

    return lookup


def build_full_schema_lens_classes(benchmark_df):
    selected = benchmark_df[benchmark_df["benchmark_group"] != "control"].copy()

    lookup = {}

    for (dataset, query_name), group in selected.groupby(["dataset", "query_name"]):
        lookup[(dataset, query_name)] = set(group["g_class"].dropna().astype(str).str.upper())

    return lookup


def build_available_benchmark_classes(benchmark_df):
    lookup = {}

    for (dataset, query_name), group in benchmark_df.groupby(["dataset", "query_name"]):
        lookup[(dataset, query_name)] = set(group["g_class"].dropna().astype(str).str.upper())

    return lookup


def has_high_update_pressure(meta_row):
    if meta_row is None:
        return False

    update_max = to_float(meta_row.get("update_volatility_max", None))
    update_class = safe_str(meta_row.get("update_volatility_class", "")).lower()
    is_write = to_bool(meta_row.get("is_write_query", False))

    if is_write:
        return True

    if update_max is not None and update_max >= 0.5:
        return True

    if "high" in update_class or "medium" in update_class:
        return True

    return False


def has_high_sharedness_pressure(meta_row):
    if meta_row is None:
        return False

    shared_max = to_float(meta_row.get("observed_sharedness_max", None))
    shared_class = safe_str(meta_row.get("observed_sharedness_class", "")).lower()

    if shared_max is not None and shared_max > 1:
        return True

    if "high" in shared_class or "medium" in shared_class:
        return True

    return False


def has_residual_traversal(meta_row):
    if meta_row is None:
        return False

    re_value = to_float(meta_row.get("Re", None))
    delta_r_ratio = to_float(meta_row.get("DeltaRratio", None))

    if re_value is not None and re_value > 0:
        return True

    if delta_r_ratio is not None and delta_r_ratio < 1:
        return True

    return False


def is_deep_query(meta_row):
    if meta_row is None:
        return False

    d_value = to_float(meta_row.get("D", None))

    if d_value is not None and d_value >= 2:
        return True

    return False


def has_relationship_semantics(meta_row):
    if meta_row is None:
        return False

    rc = to_float(meta_row.get("Rc", None))

    if rc is not None and rc > 0:
        return True

    semantic = safe_str(meta_row.get("dominant_semantic_type", "")).lower()

    if semantic and semantic not in {"none", "lookup", "local"}:
        return True

    return False


def classify_removal_reason(g_class, evidence, meta_row, component):
    evidence = safe_str(evidence)
    g_class = normalize_g_class(g_class)

    if component == "relationship_semantics":
        if g_class in SEMANTIC_CLASSES:
            return "removed_semantic_g_class"
        if (
            g_class not in {"G0", "G7", "G9"}
            and contains_any(
                evidence,
                [
                    "association",
                    "associative",
                    "containment",
                    "descriptor",
                    "ownership",
                    "subtype",
                    "semantic",
                ],
            )
        ):
            return "removed_semantic_activation_evidence"
        return ""

    if component == "depth":
        if g_class in DEPTH_CLASSES:
            return "removed_depth_sensitive_g_class"
        if contains_any(evidence, ["deep", "depth", "nested"]):
            return "removed_depth_activation_evidence"
        return ""

    if component == "residual_traversal":
        if g_class in RESIDUAL_CLASSES:
            return "removed_residual_or_reduction_sensitive_g_class"
        if contains_any(evidence, ["residual", "deltar", "reduction", "remaining external"]):
            return "removed_residual_activation_evidence"
        return ""

    if component == "sharedness":
        if g_class in SHAREDNESS_CLASSES:
            return "removed_sharedness_sensitive_g_class"
        if contains_any(evidence, ["shared", "sharedness"]):
            return "removed_sharedness_activation_evidence"
        return ""

    if component == "update_volatility":
        if g_class in UPDATE_CLASSES:
            return "removed_update_sensitive_g_class"
        if contains_any(evidence, ["update", "volatility", "write"]):
            return "removed_update_activation_evidence"
        return ""

    return ""


def apply_component_removal(
    classes,
    dataset,
    query_name,
    component,
    meta_row,
    activation_evidence_lookup,
):
    selected = set(classes)
    removed = {}

    for g_class in sorted(classes):
        evidence = activation_evidence_lookup.get((dataset, query_name, g_class), "")
        reason = classify_removal_reason(g_class, evidence, meta_row, component)

        if reason:
            selected.discard(g_class)
            removed[g_class] = reason

    return selected, removed


def fallback_if_empty(selected, full_classes, available_classes):
    if selected:
        return selected, ""

    for g in ROOT_FALLBACK_CLASSES:
        if g in full_classes:
            return {g}, f"fallback_to_{g}_from_full_schema_lens"
        if g in available_classes:
            return {g}, f"fallback_to_{g}_from_available_measured_classes"

    return set(), "no_fallback_available"


def build_variant_classes_for_query(
    dataset,
    query_name,
    meta_row,
    full_classes,
    available_classes,
    activation_evidence_lookup,
):
    rows = []

    full_classes = set(full_classes)
    available_classes = set(available_classes)

    for variant in ABLATION_VARIANTS:
        selected = set(full_classes)
        removed = {}
        rule_note = ""

        if variant == "full_schema_lens":
            rule_note = "Full SchemaLens measured space: all non-control benchmark groups."

        elif variant == "no_relationship_semantics":
            selected, removed = apply_component_removal(
                selected,
                dataset,
                query_name,
                "relationship_semantics",
                meta_row,
                activation_evidence_lookup,
            )
            selected, fallback_note = fallback_if_empty(selected, full_classes, available_classes)
            rule_note = (
                "Removed relationship-semantics-driven classes. "
                "This ablation ignores association, associative, containment, descriptor, ownership, and subtype signals."
            )
            if fallback_note:
                rule_note += f" {fallback_note}."

        elif variant == "no_depth":
            selected, removed = apply_component_removal(
                selected,
                dataset,
                query_name,
                "depth",
                meta_row,
                activation_evidence_lookup,
            )
            selected, fallback_note = fallback_if_empty(selected, full_classes, available_classes)
            rule_note = (
                "Removed depth-sensitive classes. "
                "This ablation ignores embedding depth and deep/nested traversal evidence."
            )
            if fallback_note:
                rule_note += f" {fallback_note}."

        elif variant == "no_residual_traversal":
            selected, removed = apply_component_removal(
                selected,
                dataset,
                query_name,
                "residual_traversal",
                meta_row,
                activation_evidence_lookup,
            )
            selected, fallback_note = fallback_if_empty(selected, full_classes, available_classes)
            rule_note = (
                "Removed residual-traversal/reduction-sensitive classes. "
                "This ablation ignores Re, DeltaR, and DeltaRratio as activation evidence."
            )
            if fallback_note:
                rule_note += f" {fallback_note}."

        elif variant == "no_sharedness":
            selected, removed = apply_component_removal(
                selected,
                dataset,
                query_name,
                "sharedness",
                meta_row,
                activation_evidence_lookup,
            )
            selected, fallback_note = fallback_if_empty(selected, full_classes, available_classes)
            rule_note = (
                "Removed sharedness-sensitive classes. "
                "This ablation ignores observed sharedness pressure."
            )
            if fallback_note:
                rule_note += f" {fallback_note}."

        elif variant == "no_update_volatility":
            selected, removed = apply_component_removal(
                selected,
                dataset,
                query_name,
                "update_volatility",
                meta_row,
                activation_evidence_lookup,
            )
            selected, fallback_note = fallback_if_empty(selected, full_classes, available_classes)
            rule_note = (
                "Removed update/volatility-sensitive classes. "
                "This ablation ignores write pressure and update volatility."
            )
            if fallback_note:
                rule_note += f" {fallback_note}."

        elif variant == "no_relationship_semantics_no_depth":
            selected, removed_sem = apply_component_removal(
                selected,
                dataset,
                query_name,
                "relationship_semantics",
                meta_row,
                activation_evidence_lookup,
            )
            selected, removed_depth = apply_component_removal(
                selected,
                dataset,
                query_name,
                "depth",
                meta_row,
                activation_evidence_lookup,
            )
            removed = {**removed_sem, **removed_depth}
            selected, fallback_note = fallback_if_empty(selected, full_classes, available_classes)
            rule_note = (
                "Removed both relationship-semantics-driven and depth-sensitive classes. "
                "This ablation tests a reduced activation without semantic type or embedding depth."
            )
            if fallback_note:
                rule_note += f" {fallback_note}."

        selected = selected & available_classes

        rows.append(
            {
                "dataset": dataset,
                "query_name": query_name,
                "ablation_variant": variant,
                "full_schema_lens_g_classes": classes_to_string(full_classes),
                "available_g_classes": classes_to_string(available_classes),
                "selected_g_classes": classes_to_string(selected),
                "removed_g_classes": classes_to_string(removed.keys()),
                "removal_reasons": "; ".join(
                    [f"{g}:{reason}" for g, reason in sorted(removed.items())]
                ),
                "selected_count": len(selected),
                "full_count": len(full_classes),
                "has_relationship_semantics": has_relationship_semantics(meta_row),
                "is_deep_query": is_deep_query(meta_row),
                "has_residual_traversal": has_residual_traversal(meta_row),
                "has_high_update_pressure": has_high_update_pressure(meta_row),
                "has_high_sharedness_pressure": has_high_sharedness_pressure(meta_row),
                "rule_note": rule_note,
            }
        )

    return rows


def build_ablation_rules(
    query_df,
    benchmark_df,
    activation_evidence_lookup,
):
    query_lookup = build_query_metadata_lookup(query_df)
    full_lookup = build_full_schema_lens_classes(benchmark_df)
    available_lookup = build_available_benchmark_classes(benchmark_df)

    rows = []

    all_query_keys = sorted(set(query_lookup.keys()) | set(full_lookup.keys()) | set(available_lookup.keys()))

    for dataset, query_name in all_query_keys:
        meta_row = query_lookup.get((dataset, query_name))
        full_classes = full_lookup.get((dataset, query_name), set())
        available_classes = available_lookup.get((dataset, query_name), set())

        query_rows = build_variant_classes_for_query(
            dataset=dataset,
            query_name=query_name,
            meta_row=meta_row,
            full_classes=full_classes,
            available_classes=available_classes,
            activation_evidence_lookup=activation_evidence_lookup,
        )

        rows.extend(query_rows)

    return pd.DataFrame(rows)


def sort_case_rows(group):
    return group.sort_values(
        ["p95_latency_ms", "g_class", "config_id"],
        ascending=[True, True, True],
    ).reset_index(drop=True)


def get_global_info(group):
    ordered = sort_case_rows(group)

    best = ordered.iloc[0]
    global_best_p95 = float(best["p95_latency_ms"])

    top3_config_ids = set(ordered.head(3)["config_id"].astype(str))

    if global_best_p95 <= 0:
        near_best_config_ids = {str(best["config_id"])}
    else:
        near_mask = (
            (ordered["p95_latency_ms"] - global_best_p95)
            / global_best_p95
            <= NEAR_BEST_THRESHOLD
        )
        near_best_config_ids = set(ordered.loc[near_mask, "config_id"].astype(str))

    return {
        "global_best_config_id": str(best["config_id"]),
        "global_best_g_class": str(best["g_class"]),
        "global_best_p95": global_best_p95,
        "top3_config_ids": top3_config_ids,
        "near_best_config_ids": near_best_config_ids,
    }


def evaluate_selected_classes(case_rows, selected_classes, global_info):
    selected_classes = set(selected_classes)

    if not selected_classes:
        return {
            "availability_status": "unavailable",
            "selected_config_count": 0,
            "selected_g_classes": "",
            "ablation_best_config_id": "",
            "ablation_best_g_class": "",
            "ablation_best_p95": None,
            "top1_preserved": None,
            "top3_preserved": None,
            "near_best_preserved": None,
            "relative_regret": None,
        }

    selected_rows = case_rows[case_rows["g_class"].isin(selected_classes)].copy()

    if selected_rows.empty:
        return {
            "availability_status": "unavailable",
            "selected_config_count": 0,
            "selected_g_classes": classes_to_string(selected_classes),
            "ablation_best_config_id": "",
            "ablation_best_g_class": "",
            "ablation_best_p95": None,
            "top1_preserved": None,
            "top3_preserved": None,
            "near_best_preserved": None,
            "relative_regret": None,
        }

    selected_rows = sort_case_rows(selected_rows)

    best = selected_rows.iloc[0]
    selected_config_ids = set(selected_rows["config_id"].astype(str))

    ablation_best_p95 = float(best["p95_latency_ms"])
    global_best_p95 = global_info["global_best_p95"]

    if global_best_p95 <= 0:
        relative_regret = None
    else:
        relative_regret = (ablation_best_p95 - global_best_p95) / global_best_p95

    top1_preserved = 1 if ablation_best_p95 <= global_best_p95 * (1 + 1e-12) else 0
    top3_preserved = 1 if selected_config_ids & global_info["top3_config_ids"] else 0
    near_best_preserved = 1 if selected_config_ids & global_info["near_best_config_ids"] else 0

    return {
        "availability_status": "available",
        "selected_config_count": selected_rows["config_id"].nunique(),
        "selected_g_classes": classes_to_string(selected_classes),
        "ablation_best_config_id": str(best["config_id"]),
        "ablation_best_g_class": str(best["g_class"]),
        "ablation_best_p95": ablation_best_p95,
        "top1_preserved": top1_preserved,
        "top3_preserved": top3_preserved,
        "near_best_preserved": near_best_preserved,
        "relative_regret": relative_regret,
    }


def simulate_ablation_performance(aggregate_df, rules_df):
    rule_lookup = {}

    for _, row in rules_df.iterrows():
        key = (row["dataset"], row["query_name"], row["ablation_variant"])
        rule_lookup[key] = row

    rows = []

    group_cols = ["dataset", "scale_label", "query_name", "run_phase"]

    for case_key, case_rows in aggregate_df.groupby(group_cols, sort=True):
        dataset, scale_label, query_name, run_phase = case_key

        case_rows = case_rows.dropna(subset=["p95_latency_ms"]).copy()

        if case_rows.empty:
            continue

        global_info = get_global_info(case_rows)

        for variant in ABLATION_VARIANTS:
            rule = rule_lookup.get((dataset, query_name, variant))

            if rule is None:
                selected_classes = set()
                rule_note = "No ablation rule found for this query."
                removed_g_classes = ""
                removal_reasons = ""
            else:
                selected_classes = string_to_classes(rule["selected_g_classes"])
                rule_note = safe_str(rule["rule_note"])
                removed_g_classes = safe_str(rule["removed_g_classes"])
                removal_reasons = safe_str(rule["removal_reasons"])

            metrics = evaluate_selected_classes(case_rows, selected_classes, global_info)

            rows.append(
                {
                    "dataset": dataset,
                    "scale_label": scale_label,
                    "query_name": query_name,
                    "run_phase": run_phase,
                    "query_scale_phase_id": f"{dataset}::{scale_label}::{query_name}::{run_phase}",
                    "ablation_variant": variant,
                    "availability_status": metrics["availability_status"],
                    "selected_g_classes": metrics["selected_g_classes"],
                    "selected_config_count": metrics["selected_config_count"],
                    "removed_g_classes": removed_g_classes,
                    "removal_reasons": removal_reasons,
                    "global_best_config_id": global_info["global_best_config_id"],
                    "global_best_g_class": global_info["global_best_g_class"],
                    "global_best_p95": global_info["global_best_p95"],
                    "ablation_best_config_id": metrics["ablation_best_config_id"],
                    "ablation_best_g_class": metrics["ablation_best_g_class"],
                    "ablation_best_p95": metrics["ablation_best_p95"],
                    "top1_preserved": metrics["top1_preserved"],
                    "top3_preserved": metrics["top3_preserved"],
                    "near_best_preserved": metrics["near_best_preserved"],
                    "relative_regret": metrics["relative_regret"],
                    "rule_note": rule_note,
                }
            )

    return pd.DataFrame(rows)


def summarize_performance(perf_df, group_cols):
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
                "mean_ablation_best_p95": None,
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
                "mean_ablation_best_p95": available["ablation_best_p95"].mean(),
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


def build_failure_cases(perf_df):
    available = perf_df[perf_df["availability_status"] == "available"].copy()

    failures = available[
        (available["top1_preserved"] < 1)
        | (available["near_best_preserved"] < 1)
        | (available["relative_regret"] > NEAR_BEST_THRESHOLD)
    ].copy()

    failures = failures.sort_values(
        ["relative_regret", "ablation_variant", "dataset", "scale_label", "query_name"],
        ascending=[False, True, True, True, True],
    )

    return failures


def fmt_float(value, digits=4):
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def build_report(summary_df, by_dataset_df, hot_summary_df, hot_by_dataset_df, rules_df, failure_df):
    lines = []

    lines.append("# Ablation Analysis Report")
    lines.append("")
    lines.append("This report summarizes simulated ablations over the measured aggregate benchmark outputs.")
    lines.append("")
    lines.append("The analysis uses real SchemaLens methodology variables normalized from IMDb, FIBEN, and LDBC SNB artifacts.")
    lines.append("")
    lines.append("No MongoDB benchmark is rerun.")
    lines.append("No latency is inferred for unmeasured configurations.")
    lines.append("")

    lines.append("## Settings")
    lines.append(f"- Near-best threshold: {NEAR_BEST_THRESHOLD}")
    lines.append("")

    lines.append("## Ablation variants")
    lines.append("- full_schema_lens: all non-control measured SchemaLens configurations.")
    lines.append("- no_relationship_semantics: removes relationship-semantics-driven classes.")
    lines.append("- no_depth: removes depth-sensitive classes.")
    lines.append("- no_residual_traversal: removes classes driven by Re, DeltaR, or residual traversal.")
    lines.append("- no_sharedness: removes sharedness-sensitive classes.")
    lines.append("- no_update_volatility: removes update/volatility-sensitive classes.")
    lines.append("- no_relationship_semantics_no_depth: removes both relationship-semantics and depth-sensitive classes.")
    lines.append("")

    lines.append("## Overall summary")
    for _, row in summary_df.sort_values("ablation_variant").iterrows():
        lines.append(
            f"- {row['ablation_variant']}: "
            f"available={int(row['available_cases'])}/{int(row['total_cases'])}, "
            f"top1={fmt_float(row['top1_preservation_rate'])}, "
            f"top3={fmt_float(row['top3_preservation_rate'])}, "
            f"near_best={fmt_float(row['near_best_preservation_rate'])}, "
            f"mean_regret={fmt_float(row['mean_relative_regret'])}, "
            f"median_regret={fmt_float(row['median_relative_regret'])}"
        )

    lines.append("")
    lines.append("## Hot-run summary")
    for _, row in hot_summary_df.sort_values("ablation_variant").iterrows():
        lines.append(
            f"- {row['ablation_variant']}: "
            f"available={int(row['available_cases'])}/{int(row['total_cases'])}, "
            f"top1={fmt_float(row['top1_preservation_rate'])}, "
            f"near_best={fmt_float(row['near_best_preservation_rate'])}, "
            f"mean_regret={fmt_float(row['mean_relative_regret'])}"
        )

    lines.append("")
    lines.append("## Dataset-level summary")
    for _, row in by_dataset_df.sort_values(["dataset", "ablation_variant"]).iterrows():
        lines.append(
            f"- {row['dataset']} / {row['ablation_variant']}: "
            f"available={int(row['available_cases'])}/{int(row['total_cases'])}, "
            f"top1={fmt_float(row['top1_preservation_rate'])}, "
            f"near_best={fmt_float(row['near_best_preservation_rate'])}, "
            f"mean_regret={fmt_float(row['mean_relative_regret'])}"
        )

    lines.append("")
    lines.append("## Hot-run dataset-level summary")
    for _, row in hot_by_dataset_df.sort_values(["dataset", "ablation_variant"]).iterrows():
        lines.append(
            f"- {row['dataset']} / {row['ablation_variant']}: "
            f"available={int(row['available_cases'])}/{int(row['total_cases'])}, "
            f"top1={fmt_float(row['top1_preservation_rate'])}, "
            f"near_best={fmt_float(row['near_best_preservation_rate'])}, "
            f"mean_regret={fmt_float(row['mean_relative_regret'])}"
        )

    lines.append("")
    lines.append("## Rule coverage")
    lines.append(f"- Query-level ablation rule rows: {len(rules_df)}")
    for variant, group in rules_df.groupby("ablation_variant"):
        unavailable = (group["selected_count"] == 0).sum()
        lines.append(
            f"- {variant}: queries={len(group)}, empty_selections={int(unavailable)}"
        )

    lines.append("")
    lines.append("## Failure and near-failure candidates")
    lines.append(f"- Rows flagged: {len(failure_df)}")
    lines.append(
        "- A row is flagged when Top-1 is not preserved, near-best is not preserved, "
        "or relative regret is above the near-best threshold."
    )

    lines.append("")
    lines.append("## Methodological note")
    lines.append(
        "This is a simulated ablation over the measured comparison space. "
        "It removes component-specific G classes from the measured SchemaLens-selected space "
        "using the normalized analytical metadata and activation evidence."
    )
    lines.append(
        "The root-choice ablation is not simulated here because the benchmark artifacts do not "
        "include alternative-root MongoDB configurations for all queries. Testing root choice "
        "would require materializing and benchmarking additional candidates rooted at non-selected entities."
    )

    return "\n".join(lines)


def main():
    repo_root = Path(__file__).resolve().parents[2]
    output_dir = repo_root / "analysis" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading inputs...")
    aggregate_df, query_df, activation_df, benchmark_df = load_inputs(repo_root)

    print("Building ablation rules...")
    activation_evidence_lookup = build_activation_evidence_lookup(activation_df)
    rules_df = build_ablation_rules(
        query_df=query_df,
        benchmark_df=benchmark_df,
        activation_evidence_lookup=activation_evidence_lookup,
    )

    print("Simulating ablation performance...")
    perf_df = simulate_ablation_performance(aggregate_df, rules_df)

    print("Building summaries...")
    summary_df = summarize_performance(perf_df, ["ablation_variant"])
    by_dataset_df = summarize_performance(perf_df, ["dataset", "ablation_variant"])

    hot_df = perf_df[perf_df["run_phase"] == "hot"].copy()
    hot_summary_df = summarize_performance(hot_df, ["ablation_variant"])
    hot_by_dataset_df = summarize_performance(hot_df, ["dataset", "ablation_variant"])

    failure_df = build_failure_cases(perf_df)

    rules_path = output_dir / "ablation_rules_used.csv"
    by_case_path = output_dir / "ablation_performance_by_case.csv"
    summary_path = output_dir / "ablation_performance_summary.csv"
    by_dataset_path = output_dir / "ablation_performance_by_dataset.csv"
    hot_summary_path = output_dir / "ablation_performance_summary_hot.csv"
    hot_by_dataset_path = output_dir / "ablation_performance_by_dataset_hot.csv"
    failure_path = output_dir / "ablation_failure_cases.csv"
    report_path = output_dir / "ablation_report.txt"

    rules_df.to_csv(rules_path, index=False, encoding="utf-8")
    perf_df.to_csv(by_case_path, index=False, encoding="utf-8")
    summary_df.to_csv(summary_path, index=False, encoding="utf-8")
    by_dataset_df.to_csv(by_dataset_path, index=False, encoding="utf-8")
    hot_summary_df.to_csv(hot_summary_path, index=False, encoding="utf-8")
    hot_by_dataset_df.to_csv(hot_by_dataset_path, index=False, encoding="utf-8")
    failure_df.to_csv(failure_path, index=False, encoding="utf-8")

    report = build_report(
        summary_df=summary_df,
        by_dataset_df=by_dataset_df,
        hot_summary_df=hot_summary_df,
        hot_by_dataset_df=hot_by_dataset_df,
        rules_df=rules_df,
        failure_df=failure_df,
    )
    report_path.write_text(report, encoding="utf-8")

    print("")
    print("Ablation analysis completed.")
    print(f"Rules: {rules_path}")
    print(f"By case: {by_case_path}")
    print(f"Summary: {summary_path}")
    print(f"By dataset: {by_dataset_path}")
    print(f"Hot summary: {hot_summary_path}")
    print(f"Hot by dataset: {hot_by_dataset_path}")
    print(f"Failures: {failure_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()