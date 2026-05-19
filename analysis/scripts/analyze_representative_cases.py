#!/usr/bin/env python3
"""
Representative case analysis for the SchemaLens experimental revision.

This script combines measured benchmark results, normalized analytical variables,
activation evidence, baseline outputs, and ablation outputs to explain why
specific configurations win in selected representative cases.

It does not rerun MongoDB benchmarks and does not infer latency for unmeasured
configurations. All performance statements are based only on measured aggregate
outputs.

Expected location in the repository:
    analysis/scripts/analyze_representative_cases.py

Run from the repository root:
    python analysis/scripts/analyze_representative_cases.py

Main outputs:
    analysis/generated/representative_case_table.csv
    analysis/generated/representative_case_analysis.md
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd


NEAR_BEST_THRESHOLD_DEFAULT = 0.05


@dataclass(frozen=True)
class RepresentativeCase:
    dataset: str
    query_name: str
    focus: str
    why_selected: str


REPRESENTATIVE_CASES: Sequence[RepresentativeCase] = (
    RepresentativeCase(
        dataset="imdb",
        query_name="QG6_EpisodesOfSeries",
        focus="containment / low-sharedness traversal",
        why_selected=(
            "Canonical IMDb containment-like case: a series retrieves its episodes. "
            "It is useful to show when embedding/containment-style candidates are semantically justified."
        ),
    ),
    RepresentativeCase(
        dataset="imdb",
        query_name="QG10_AdvancedSearchWatchItems",
        focus="association / sharedness / filtered search",
        why_selected=(
            "IMDb query with high sharedness and filter pressure over WatchItem-related structures. "
            "It helps explain why SchemaLens must consider trade-offs beyond simple containment."
        ),
    ),
    RepresentativeCase(
        dataset="fiben",
        query_name="Q10_CreateAccountHoldingAndBuyTransaction",
        focus="update + relationship creation",
        why_selected=(
            "Write-oriented FIBEN case with relationship creation and high update pressure. "
            "It helps show that SchemaLens does not blindly prefer embedding for every traversal."
        ),
    ),
    RepresentativeCase(
        dataset="fiben",
        query_name="Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity",
        focus="deep traversal",
        why_selected=(
            "Deep FIBEN traversal from Person through account, holding, security, and company. "
            "It is useful for explaining the role of depth and residual traversal."
        ),
    ),
    RepresentativeCase(
        dataset="ldbc_snb",
        query_name="IC1_TransitiveFriendsWithName",
        focus="official complex read / transitive association",
        why_selected=(
            "Official LDBC SNB complex query with repeated person-knows-person traversal and profile expansion. "
            "It tests whether activated configurations preserve strong candidates under graph-like access."
        ),
    ),
    RepresentativeCase(
        dataset="ldbc_snb",
        query_name="IC5_NewGroups",
        focus="official complex read / association + containment mix",
        why_selected=(
            "Official LDBC SNB query mixing friendship, forum membership, forum containment, and posts. "
            "It is useful for showing why secondary affected families may win."
        ),
    ),
    RepresentativeCase(
        dataset="ldbc_snb",
        query_name="IC7_RecentLikers",
        focus="official complex read / likes and friend check",
        why_selected=(
            "Official LDBC SNB query combining recent likes, message ownership, and friendship checks. "
            "It exposes association and associative-edge trade-offs."
        ),
    ),
    RepresentativeCase(
        dataset="ldbc_snb",
        query_name="IS2_RecentMessagesOfPerson",
        focus="official short read / messages of person",
        why_selected=(
            "Official LDBC SNB short read with posts/comments and reply context. "
            "It is a compact case for residual traversal and mixed message structures."
        ),
    ),
    RepresentativeCase(
        dataset="ldbc_snb",
        query_name="IS6_ForumOfMessage",
        focus="official short read / containment path",
        why_selected=(
            "Official LDBC SNB short read asking for the forum containing a message and the moderator. "
            "It highlights containment-like paths in the social-network workload."
        ),
    ),
    RepresentativeCase(
        dataset="ldbc_snb",
        query_name="IS7_RepliesOfMessage",
        focus="official short read / replies and author relation",
        why_selected=(
            "Official LDBC SNB short read over replies, authors, and whether authors know each other. "
            "It is useful for explaining mixed association and containment traversal."
        ),
    ),
)


G_CLASS_LABEL_FALLBACK = {
    "G0": "root_with_references",
    "G1": "primary_document_candidate",
    "G2": "primary_document_candidate",
    "G3": "root_with_references_or_summaries",
    "G4": "explicit_edge_collection",
    "G5": "sharedness_sensitive_candidate",
    "G6": "referenced_or_reverse_indexed_edges",
    "G7": "containment_baseline",
    "G8": "depth_or_residual_sensitive_candidate",
    "G9": "hybrid_containment",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build representative case table and narrative analysis for SchemaLens."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root. Defaults to two parents above this script.",
    )
    parser.add_argument(
        "--run-phase",
        default="hot",
        choices=["hot", "cold", "all"],
        help="Benchmark phase to use. Default: hot.",
    )
    parser.add_argument(
        "--scale-mode",
        default="all",
        choices=["all", "largest"],
        help=(
            "Use all available scales or only the largest scale per dataset/query. "
            "Default: all. Use largest for a compact paper table."
        ),
    )
    parser.add_argument(
        "--near-best-threshold",
        type=float,
        default=NEAR_BEST_THRESHOLD_DEFAULT,
        help="Near-best relative threshold. Default: 0.05."
    )
    return parser.parse_args()


def resolve_repo_root(cli_root: Optional[Path]) -> Path:
    if cli_root is not None:
        return cli_root.resolve()
    return Path(__file__).resolve().parents[2]


def read_csv_required(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input file: {path}")
    return pd.read_csv(path, encoding="utf-8-sig")


def read_csv_optional(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def safe_str(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value)


def safe_float(value) -> Optional[float]:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except Exception:
        return None


def safe_bool(value) -> bool:
    if value is None or pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def fmt_float(value, digits: int = 4) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def normalize_dataset(value) -> str:
    return safe_str(value).strip().lower()


def normalize_query(value) -> str:
    return safe_str(value).strip()


def normalize_g_class(value) -> str:
    return safe_str(value).strip().upper()


def normalize_phase(value) -> str:
    return safe_str(value).strip().lower()


def classes_to_string(values: Iterable[str]) -> str:
    return "|".join(sorted({normalize_g_class(v) for v in values if safe_str(v).strip()}))


def split_classes(value) -> set:
    text = safe_str(value)
    if not text:
        return set()
    return {x.strip().upper() for x in text.replace(",", "|").split("|") if x.strip()}


def sort_scale_labels(scale_labels: Sequence[str]) -> List[str]:
    def scale_key(label: str) -> Tuple[int, float, str]:
        text = safe_str(label).lower().replace("sf", "").replace("_", ".")
        try:
            return (0, float(text), label)
        except Exception:
            return (1, 0.0, label)

    return sorted(scale_labels, key=scale_key)


def largest_scale_label(scale_labels: Sequence[str]) -> Optional[str]:
    ordered = sort_scale_labels(scale_labels)
    return ordered[-1] if ordered else None


def first_existing_column(df: pd.DataFrame, candidates: Sequence[str]) -> Optional[str]:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def ensure_core_columns(aggregate_df: pd.DataFrame) -> None:
    required = [
        "dataset",
        "scale_label",
        "query_name",
        "run_phase",
        "config_id",
        "g_class",
        "benchmark_group",
        "p95_latency_ms",
    ]
    missing = [col for col in required if col not in aggregate_df.columns]
    if missing:
        raise ValueError(f"aggregate_results_all_datasets.csv missing columns: {missing}")


def load_inputs(repo_root: Path) -> Dict[str, pd.DataFrame]:
    generated = repo_root / "analysis" / "generated"

    paths = {
        "aggregate": generated / "aggregate_results_all_datasets.csv",
        "metadata": generated / "query_analytical_metadata_all_datasets.csv",
        "activation": generated / "query_class_activation_all_datasets.csv",
        "benchmark_selection": generated / "benchmark_configuration_selection_all_datasets.csv",
        "ablation_by_case": generated / "ablation_performance_by_case.csv",
        "baseline_by_case": generated / "baseline_performance_by_case.csv",
        "random_k_diagnostic": generated / "schema_lens_vs_random_k_by_case.csv",
    }

    data = {
        "aggregate": read_csv_required(paths["aggregate"]),
        "metadata": read_csv_required(paths["metadata"]),
        "activation": read_csv_required(paths["activation"]),
        "benchmark_selection": read_csv_required(paths["benchmark_selection"]),
        "ablation_by_case": read_csv_optional(paths["ablation_by_case"]),
        "baseline_by_case": read_csv_optional(paths["baseline_by_case"]),
        "random_k_diagnostic": read_csv_optional(paths["random_k_diagnostic"]),
    }

    ensure_core_columns(data["aggregate"])

    # Normalize common join columns.
    for name, df in data.items():
        if df.empty:
            continue
        if "dataset" in df.columns:
            df["dataset"] = df["dataset"].apply(normalize_dataset)
        if "query_name" in df.columns:
            df["query_name"] = df["query_name"].apply(normalize_query)
        if "scale_label" in df.columns:
            df["scale_label"] = df["scale_label"].astype(str)
        if "run_phase" in df.columns:
            df["run_phase"] = df["run_phase"].apply(normalize_phase)
        if "g_class" in df.columns:
            df["g_class"] = df["g_class"].apply(normalize_g_class)
        if "benchmark_group" in df.columns:
            df["benchmark_group"] = df["benchmark_group"].astype(str).str.lower()

    data["aggregate"]["p95_latency_ms"] = pd.to_numeric(
        data["aggregate"]["p95_latency_ms"], errors="coerce"
    )

    if "is_active" in data["activation"].columns:
        data["activation"]["is_active"] = data["activation"]["is_active"].apply(safe_bool)

    return data


def build_metadata_lookup(metadata_df: pd.DataFrame) -> Dict[Tuple[str, str], pd.Series]:
    lookup = {}
    for _, row in metadata_df.iterrows():
        lookup[(row["dataset"], row["query_name"])] = row
    return lookup


def build_label_lookup(activation_df: pd.DataFrame, selection_df: pd.DataFrame) -> Dict[Tuple[str, str, str], str]:
    lookup: Dict[Tuple[str, str, str], str] = {}

    for df in [selection_df, activation_df]:
        if df.empty:
            continue
        label_col = first_existing_column(df, ["g_label", "candidate_label", "config_label", "configuration_label"])
        if not label_col:
            continue
        for _, row in df.iterrows():
            key = (row.get("dataset", ""), row.get("query_name", ""), normalize_g_class(row.get("g_class", "")))
            label = safe_str(row.get(label_col, "")).strip()
            if label and key not in lookup:
                lookup[key] = label

    return lookup


def g_label(dataset: str, query_name: str, g_class: str, label_lookup: Dict[Tuple[str, str, str], str]) -> str:
    key = (dataset, query_name, normalize_g_class(g_class))
    return label_lookup.get(key) or G_CLASS_LABEL_FALLBACK.get(normalize_g_class(g_class), "")


def summarize_active_classes(activation_df: pd.DataFrame) -> Dict[Tuple[str, str], Dict[str, str]]:
    if activation_df.empty:
        return {}

    active_df = activation_df.copy()
    if "is_active" in active_df.columns:
        active_df = active_df[active_df["is_active"] == True].copy()

    reason_cols = [
        c
        for c in ["activation_status", "activation_strength", "activation_reason", "g_family", "g_role", "g_label"]
        if c in active_df.columns
    ]

    result: Dict[Tuple[str, str], Dict[str, str]] = {}
    for (dataset, query_name), group in active_df.groupby(["dataset", "query_name"], dropna=False):
        classes = classes_to_string(group["g_class"] if "g_class" in group.columns else [])
        reasons = []
        for _, row in group.iterrows():
            g = normalize_g_class(row.get("g_class", ""))
            reason_parts = [safe_str(row.get(c, "")).strip() for c in reason_cols]
            reason_parts = [p for p in reason_parts if p]
            if reason_parts:
                reasons.append(f"{g}: " + " / ".join(reason_parts))
        result[(dataset, query_name)] = {
            "activated_g_classes": classes,
            "activation_evidence": "; ".join(reasons),
        }
    return result


def summarize_benchmark_selection(selection_df: pd.DataFrame) -> Dict[Tuple[str, str], Dict[str, str]]:
    if selection_df.empty:
        return {}

    result: Dict[Tuple[str, str], Dict[str, str]] = {}
    for (dataset, query_name), group in selection_df.groupby(["dataset", "query_name"], dropna=False):
        measured_classes = classes_to_string(group["g_class"] if "g_class" in group.columns else [])
        measured_config_count = group["config_id"].nunique() if "config_id" in group.columns else len(group)

        by_group = {}
        if "benchmark_group" in group.columns and "g_class" in group.columns:
            for bench_group, sub in group.groupby("benchmark_group", dropna=False):
                by_group[f"{bench_group}_g_classes"] = classes_to_string(sub["g_class"])

        result[(dataset, query_name)] = {
            "measured_g_classes": measured_classes,
            "measured_config_count": measured_config_count,
            **by_group,
        }
    return result


def get_case_rows(
    aggregate_df: pd.DataFrame,
    dataset: str,
    query_name: str,
    run_phase: str,
    scale_mode: str,
) -> pd.DataFrame:
    case_rows = aggregate_df[
        (aggregate_df["dataset"] == dataset) & (aggregate_df["query_name"] == query_name)
    ].copy()

    if run_phase != "all":
        case_rows = case_rows[case_rows["run_phase"] == run_phase].copy()

    case_rows = case_rows.dropna(subset=["p95_latency_ms"]).copy()

    if scale_mode == "largest" and not case_rows.empty:
        largest = largest_scale_label(case_rows["scale_label"].dropna().astype(str).unique().tolist())
        if largest is not None:
            case_rows = case_rows[case_rows["scale_label"].astype(str) == str(largest)].copy()

    return case_rows


def evaluate_scale_phase(
    rows: pd.DataFrame,
    threshold: float,
) -> Dict[str, object]:
    ordered = rows.sort_values(["p95_latency_ms", "g_class", "config_id"]).reset_index(drop=True)
    best = ordered.iloc[0]
    global_best_p95 = float(best["p95_latency_ms"])

    non_control = ordered[ordered["benchmark_group"] != "control"].copy()
    if non_control.empty:
        schema_lens_best = None
        schema_lens_best_p95 = None
        schema_lens_regret = None
        top1_preserved = False
        near_best_preserved = False
    else:
        schema_lens_best = non_control.iloc[0]
        schema_lens_best_p95 = float(schema_lens_best["p95_latency_ms"])
        schema_lens_regret = (
            None
            if global_best_p95 <= 0
            else (schema_lens_best_p95 - global_best_p95) / global_best_p95
        )
        top1_preserved = str(best["config_id"]) in set(non_control["config_id"].astype(str))
        near_limit = global_best_p95 * (1.0 + threshold)
        near_best_preserved = bool((non_control["p95_latency_ms"] <= near_limit).any())

    near_limit = global_best_p95 * (1.0 + threshold)
    near_classes = classes_to_string(ordered[ordered["p95_latency_ms"] <= near_limit]["g_class"])

    return {
        "global_best_config_id": safe_str(best.get("config_id", "")),
        "global_best_g_class": normalize_g_class(best.get("g_class", "")),
        "global_best_benchmark_group": safe_str(best.get("benchmark_group", "")),
        "global_best_p95_ms": global_best_p95,
        "near_best_g_classes": near_classes,
        "schema_lens_best_config_id": safe_str(schema_lens_best.get("config_id", "")) if schema_lens_best is not None else "",
        "schema_lens_best_g_class": normalize_g_class(schema_lens_best.get("g_class", "")) if schema_lens_best is not None else "",
        "schema_lens_best_benchmark_group": safe_str(schema_lens_best.get("benchmark_group", "")) if schema_lens_best is not None else "",
        "schema_lens_best_p95_ms": schema_lens_best_p95,
        "schema_lens_top1_preserved": int(top1_preserved),
        "schema_lens_near_best_preserved": int(near_best_preserved),
        "schema_lens_relative_regret": schema_lens_regret,
        "all_measured_config_count": ordered["config_id"].nunique(),
        "all_measured_g_classes": classes_to_string(ordered["g_class"]),
    }


def summarize_ablation_for_case(
    ablation_df: pd.DataFrame,
    dataset: str,
    query_name: str,
    scale_label: str,
    run_phase: str,
) -> str:
    if ablation_df.empty:
        return ""

    required = {"dataset", "query_name", "scale_label", "run_phase", "ablation_variant"}
    if not required.issubset(ablation_df.columns):
        return ""

    sub = ablation_df[
        (ablation_df["dataset"] == dataset)
        & (ablation_df["query_name"] == query_name)
        & (ablation_df["scale_label"].astype(str) == str(scale_label))
        & (ablation_df["run_phase"] == run_phase)
    ].copy()

    if sub.empty:
        return ""

    pieces = []
    for _, row in sub.sort_values("ablation_variant").iterrows():
        variant = safe_str(row.get("ablation_variant", ""))
        if variant == "full_schema_lens":
            continue
        top1 = safe_str(row.get("top1_preserved", ""))
        near = safe_str(row.get("near_best_preserved", ""))
        regret = fmt_float(row.get("relative_regret", None), 4)
        removed = safe_str(row.get("removed_g_classes", ""))
        pieces.append(f"{variant}: top1={top1}, near={near}, regret={regret}, removed={removed}")
    return "; ".join(pieces)


def summarize_random_k_for_case(
    random_df: pd.DataFrame,
    dataset: str,
    query_name: str,
    scale_label: str,
    run_phase: str,
) -> str:
    if random_df.empty:
        return ""

    required = {"dataset", "query_name", "scale_label", "run_phase"}
    if not required.issubset(random_df.columns):
        return ""

    sub = random_df[
        (random_df["dataset"] == dataset)
        & (random_df["query_name"] == query_name)
        & (random_df["scale_label"].astype(str) == str(scale_label))
        & (random_df["run_phase"] == run_phase)
    ].copy()

    if sub.empty:
        return ""

    # Keep this flexible because the exact diagnostic columns may evolve.
    compact_cols = [
        c
        for c in [
            "schema_lens_top1_preserved",
            "random_k_top1_preservation_rate",
            "schema_lens_relative_regret",
            "random_k_mean_relative_regret",
            "winner",
        ]
        if c in sub.columns
    ]
    if compact_cols:
        row = sub.iloc[0]
        return "; ".join([f"{c}={safe_str(row.get(c, ''))}" for c in compact_cols])

    return f"diagnostic_rows={len(sub)}"


def interpret_case(
    case: RepresentativeCase,
    meta: Optional[pd.Series],
    metrics: Dict[str, object],
    best_label: str,
    schema_lens_label: str,
) -> str:
    if meta is None:
        return (
            "No analytical metadata was found for this query. "
            "The interpretation is therefore limited to measured benchmark behavior."
        )

    rc = safe_float(meta.get("Rc", None))
    depth = safe_float(meta.get("D", None))
    re_value = safe_float(meta.get("Re", None))
    delta_ratio = safe_float(meta.get("DeltaRratio", None))
    semantic = safe_str(meta.get("dominant_semantic_type", "")) or "not specified"
    root = safe_str(meta.get("selected_root", "")) or "not specified"
    update_class = safe_str(meta.get("update_volatility_class", ""))
    shared_class = safe_str(meta.get("observed_sharedness_class", ""))
    is_write = safe_bool(meta.get("is_write_query", False))

    sentences = []
    sentences.append(
        f"The query is rooted at {root} and has semantic profile `{semantic}` "
        f"with Rc={fmt_float(rc, 2)}, D={fmt_float(depth, 2)}, Re={fmt_float(re_value, 2)}, "
        f"and DeltaRratio={fmt_float(delta_ratio, 2)}."
    )

    if semantic.lower() == "containment" or "containment" in case.focus.lower():
        sentences.append(
            "This makes the case suitable for testing whether containment-aware or hybrid document candidates "
            "reduce traversal without introducing unnecessary cross-document joins."
        )
    elif depth is not None and depth >= 3:
        sentences.append(
            "The depth signal is important because the workload traverses several conceptual hops; "
            "removing depth from the activation logic should therefore make the selected space less reliable."
        )
    elif rc is not None and rc > 0:
        sentences.append(
            "The query is not a pure lookup; it depends on relationship traversal, so relationship semantics "
            "are expected to influence which document configurations should be benchmarked."
        )

    if re_value is not None and re_value > 0:
        sentences.append(
            "Because Re is greater than zero, some traversal remains after the selected document abstraction; "
            "this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive."
        )
    elif delta_ratio is not None and delta_ratio >= 0.95 and rc is not None and rc > 0:
        sentences.append(
            "The high DeltaRratio indicates that the selected candidate can absorb most of the conceptual traversal, "
            "which supports testing embedded or containment-oriented alternatives."
        )

    if is_write or "high" in update_class.lower() or "medium" in update_class.lower():
        sentences.append(
            "The update-volatility signal is relevant here; a good result for a reference or hybrid class means that "
            "SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality."
        )

    if "high" in shared_class.lower() or "medium" in shared_class.lower():
        sentences.append(
            "The sharedness signal warns against interpreting embedding as automatically best, because highly shared "
            "entities can create duplication and maintenance pressure."
        )

    global_group = safe_str(metrics.get("global_best_benchmark_group", ""))
    top1 = int(metrics.get("schema_lens_top1_preserved", 0))
    near = int(metrics.get("schema_lens_near_best_preserved", 0))
    regret = metrics.get("schema_lens_relative_regret", None)

    sentences.append(
        f"The measured hot-run winner is {metrics.get('global_best_g_class')} ({best_label}) "
        f"from the `{global_group}` group, with p95={fmt_float(metrics.get('global_best_p95_ms'), 4)} ms."
    )

    if top1:
        sentences.append(
            "SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the "
            "activation matrix keeps the relevant winner inside the reduced benchmark space."
        )
    elif near:
        sentences.append(
            f"SchemaLens did not preserve the exact Top-1, but it preserved a near-best alternative within the "
            f"configured threshold; the relative regret was {fmt_float(regret, 4)}."
        )
    else:
        sentences.append(
            f"SchemaLens missed the Top-1 and the near-best region for this scale/phase; this should be treated "
            f"as a failure or near-failure case with relative regret {fmt_float(regret, 4)}."
        )

    if metrics.get("schema_lens_best_g_class"):
        sentences.append(
            f"The best SchemaLens-selected configuration was {metrics.get('schema_lens_best_g_class')} "
            f"({schema_lens_label}), with p95={fmt_float(metrics.get('schema_lens_best_p95_ms'), 4)} ms."
        )

    return " ".join(sentences)


def build_rows(
    data: Dict[str, pd.DataFrame],
    threshold: float,
    run_phase: str,
    scale_mode: str,
) -> pd.DataFrame:
    aggregate_df = data["aggregate"]
    metadata_lookup = build_metadata_lookup(data["metadata"])
    activation_summary = summarize_active_classes(data["activation"])
    selection_summary = summarize_benchmark_selection(data["benchmark_selection"])
    label_lookup = build_label_lookup(data["activation"], data["benchmark_selection"])

    rows = []
    for case in REPRESENTATIVE_CASES:
        dataset = normalize_dataset(case.dataset)
        query_name = normalize_query(case.query_name)
        case_rows = get_case_rows(aggregate_df, dataset, query_name, run_phase, scale_mode)

        if case_rows.empty:
            rows.append(
                {
                    "dataset": dataset,
                    "query_name": query_name,
                    "case_focus": case.focus,
                    "why_selected": case.why_selected,
                    "availability_status": "missing_measured_rows",
                    "interpretation": "No measured aggregate benchmark rows found for this representative case.",
                }
            )
            continue

        group_cols = ["scale_label", "run_phase"]
        for (scale_label, phase), group in case_rows.groupby(group_cols, sort=True):
            metrics = evaluate_scale_phase(group, threshold)
            meta = metadata_lookup.get((dataset, query_name))
            active = activation_summary.get((dataset, query_name), {})
            selection = selection_summary.get((dataset, query_name), {})

            best_g = normalize_g_class(metrics.get("global_best_g_class", ""))
            schema_g = normalize_g_class(metrics.get("schema_lens_best_g_class", ""))
            best_label = g_label(dataset, query_name, best_g, label_lookup)
            schema_label = g_label(dataset, query_name, schema_g, label_lookup)

            interpretation = interpret_case(
                case=case,
                meta=meta,
                metrics=metrics,
                best_label=best_label,
                schema_lens_label=schema_label,
            )

            row = {
                "dataset": dataset,
                "query_name": query_name,
                "scale_label": scale_label,
                "run_phase": phase,
                "case_focus": case.focus,
                "why_selected": case.why_selected,
                "availability_status": "available",
                "query_family": safe_str(meta.get("query_family", "")) if meta is not None else "",
                "query_type": safe_str(meta.get("query_type", "")) if meta is not None else "",
                "selected_root": safe_str(meta.get("selected_root", "")) if meta is not None else "",
                "Rc": safe_float(meta.get("Rc", None)) if meta is not None else None,
                "D": safe_float(meta.get("D", None)) if meta is not None else None,
                "Re": safe_float(meta.get("Re", None)) if meta is not None else None,
                "DeltaRratio": safe_float(meta.get("DeltaRratio", None)) if meta is not None else None,
                "dominant_semantic_type": safe_str(meta.get("dominant_semantic_type", "")) if meta is not None else "",
                "dominant_semantic_detail": safe_str(meta.get("dominant_semantic_detail", "")) if meta is not None else "",
                "update_volatility_max": safe_float(meta.get("update_volatility_max", None)) if meta is not None else None,
                "update_volatility_class": safe_str(meta.get("update_volatility_class", "")) if meta is not None else "",
                "observed_sharedness_max": safe_float(meta.get("observed_sharedness_max", None)) if meta is not None else None,
                "observed_sharedness_class": safe_str(meta.get("observed_sharedness_class", "")) if meta is not None else "",
                "is_write_query": safe_bool(meta.get("is_write_query", False)) if meta is not None else False,
                "activated_g_classes": active.get("activated_g_classes", ""),
                "activation_evidence": active.get("activation_evidence", ""),
                "measured_g_classes": selection.get("measured_g_classes", metrics.get("all_measured_g_classes", "")),
                "measured_config_count": selection.get("measured_config_count", metrics.get("all_measured_config_count", "")),
                "primary_g_classes": selection.get("primary_g_classes", ""),
                "secondary_affected_g_classes": selection.get("secondary_affected_g_classes", ""),
                "control_g_classes": selection.get("control_g_classes", ""),
                "global_best_config_id": metrics["global_best_config_id"],
                "global_best_g_class": best_g,
                "global_best_g_label": best_label,
                "global_best_benchmark_group": metrics["global_best_benchmark_group"],
                "global_best_p95_ms": metrics["global_best_p95_ms"],
                "near_best_g_classes": metrics["near_best_g_classes"],
                "schema_lens_best_config_id": metrics["schema_lens_best_config_id"],
                "schema_lens_best_g_class": schema_g,
                "schema_lens_best_g_label": schema_label,
                "schema_lens_best_benchmark_group": metrics["schema_lens_best_benchmark_group"],
                "schema_lens_best_p95_ms": metrics["schema_lens_best_p95_ms"],
                "schema_lens_top1_preserved": metrics["schema_lens_top1_preserved"],
                "schema_lens_near_best_preserved": metrics["schema_lens_near_best_preserved"],
                "schema_lens_relative_regret": metrics["schema_lens_relative_regret"],
                "random_k_diagnostic": summarize_random_k_for_case(
                    data["random_k_diagnostic"], dataset, query_name, scale_label, phase
                ),
                "ablation_summary": summarize_ablation_for_case(
                    data["ablation_by_case"], dataset, query_name, scale_label, phase
                ),
                "interpretation": interpretation,
            }
            rows.append(row)

    return pd.DataFrame(rows)


def markdown_table(df: pd.DataFrame, columns: Sequence[str]) -> str:
    if df.empty:
        return "_No rows._"

    display = df.loc[:, [c for c in columns if c in df.columns]].copy()
    for col in display.columns:
        display[col] = display[col].apply(lambda x: fmt_float(x, 4) if isinstance(x, float) else safe_str(x))

    headers = list(display.columns)
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in display.iterrows():
        values = [safe_str(row[col]).replace("\n", " ").replace("|", "/") for col in headers]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_markdown_report(rows_df: pd.DataFrame, threshold: float, run_phase: str, scale_mode: str) -> str:
    lines: List[str] = []
    lines.append("# Representative Case Analysis")
    lines.append("")
    lines.append("This report explains selected representative cases using measured aggregate benchmark results and normalized SchemaLens methodology variables.")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(f"- Run phase: `{run_phase}`")
    lines.append(f"- Scale mode: `{scale_mode}`")
    lines.append(f"- Near-best threshold: `{threshold}`")
    lines.append("- No MongoDB benchmark is rerun.")
    lines.append("- No latency is inferred for unmeasured configurations.")
    lines.append("- Root-choice ablation is not included because it would require materializing and benchmarking alternative-root candidates.")
    lines.append("")

    available = rows_df[rows_df.get("availability_status", "") == "available"].copy()
    if not available.empty:
        lines.append("## Compact table")
        lines.append("")
        compact_cols = [
            "dataset",
            "query_name",
            "scale_label",
            "case_focus",
            "selected_root",
            "Rc",
            "D",
            "Re",
            "DeltaRratio",
            "dominant_semantic_type",
            "global_best_g_class",
            "global_best_benchmark_group",
            "global_best_p95_ms",
            "schema_lens_top1_preserved",
            "schema_lens_near_best_preserved",
            "schema_lens_relative_regret",
        ]
        lines.append(markdown_table(available, compact_cols))
        lines.append("")

    lines.append("## Case-by-case interpretation")
    lines.append("")

    sort_cols = [c for c in ["dataset", "query_name", "scale_label", "run_phase"] if c in rows_df.columns]
    for _, row in rows_df.sort_values(sort_cols).iterrows():
        dataset = safe_str(row.get("dataset", ""))
        query = safe_str(row.get("query_name", ""))
        scale = safe_str(row.get("scale_label", ""))
        phase = safe_str(row.get("run_phase", ""))
        lines.append(f"### {dataset} / {query} / {scale} / {phase}")
        lines.append("")
        lines.append(f"**Focus.** {safe_str(row.get('case_focus', ''))}")
        lines.append("")
        lines.append(f"**Why selected.** {safe_str(row.get('why_selected', ''))}")
        lines.append("")
        if safe_str(row.get("availability_status", "")) != "available":
            lines.append(f"**Status.** {safe_str(row.get('availability_status', ''))}")
            lines.append("")
            lines.append(safe_str(row.get("interpretation", "")))
            lines.append("")
            continue

        lines.append("**Analytical variables.** ")
        lines.append(
            f"Root={safe_str(row.get('selected_root', ''))}; "
            f"Rc={fmt_float(row.get('Rc', None), 2)}; "
            f"D={fmt_float(row.get('D', None), 2)}; "
            f"Re={fmt_float(row.get('Re', None), 2)}; "
            f"DeltaRratio={fmt_float(row.get('DeltaRratio', None), 2)}; "
            f"semantic={safe_str(row.get('dominant_semantic_type', ''))}; "
            f"update={safe_str(row.get('update_volatility_class', ''))}; "
            f"sharedness={safe_str(row.get('observed_sharedness_class', ''))}."
        )
        lines.append("")
        lines.append(
            f"**Activated classes.** {safe_str(row.get('activated_g_classes', '')) or 'NA'}"
        )
        lines.append("")
        lines.append(
            f"**Measured classes.** {safe_str(row.get('measured_g_classes', '')) or 'NA'} "
            f"({safe_str(row.get('measured_config_count', ''))} measured candidates in the benchmark-selection table)."
        )
        lines.append("")
        lines.append(
            f"**Measured winner.** {safe_str(row.get('global_best_g_class', ''))} "
            f"({safe_str(row.get('global_best_g_label', ''))}) from "
            f"`{safe_str(row.get('global_best_benchmark_group', ''))}`; "
            f"p95={fmt_float(row.get('global_best_p95_ms', None), 4)} ms."
        )
        lines.append("")
        lines.append(
            f"**Best SchemaLens-selected candidate.** {safe_str(row.get('schema_lens_best_g_class', ''))} "
            f"({safe_str(row.get('schema_lens_best_g_label', ''))}); "
            f"p95={fmt_float(row.get('schema_lens_best_p95_ms', None), 4)} ms; "
            f"Top-1 preserved={safe_str(row.get('schema_lens_top1_preserved', ''))}; "
            f"near-best preserved={safe_str(row.get('schema_lens_near_best_preserved', ''))}; "
            f"relative regret={fmt_float(row.get('schema_lens_relative_regret', None), 4)}."
        )
        lines.append("")
        if safe_str(row.get("ablation_summary", "")):
            lines.append(f"**Ablation signal.** {safe_str(row.get('ablation_summary', ''))}")
            lines.append("")
        if safe_str(row.get("random_k_diagnostic", "")):
            lines.append(f"**Random-k diagnostic.** {safe_str(row.get('random_k_diagnostic', ''))}")
            lines.append("")
        lines.append(f"**Interpretation.** {safe_str(row.get('interpretation', ''))}")
        lines.append("")

    lines.append("## Suggested text for the advisor response")
    lines.append("")
    lines.append(
        "I added a representative-case analysis that connects the analytical variables "
        "used by SchemaLens with the measured benchmark winners. For each selected IMDb, "
        "FIBEN, and LDBC SNB case, the analysis reports the selected root, traversal count, "
        "embedding depth, residual traversal, semantic type, sharedness, update pressure, "
        "activated G classes, measured benchmark candidates, the hot-run p95 winner, and "
        "whether the reduced SchemaLens space preserved the Top-1 or a near-best configuration. "
        "This complements the baseline and ablation studies by explaining why specific "
        "configurations win under specific workload and data characteristics, instead of only "
        "reporting aggregate preservation metrics."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    repo_root = resolve_repo_root(args.repo_root)
    output_dir = repo_root / "analysis" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading normalized experimental outputs...")
    data = load_inputs(repo_root)

    print("Building representative case table...")
    rows_df = build_rows(
        data=data,
        threshold=args.near_best_threshold,
        run_phase=args.run_phase,
        scale_mode=args.scale_mode,
    )

    table_path = output_dir / "representative_case_table.csv"
    report_path = output_dir / "representative_case_analysis.md"

    rows_df.to_csv(table_path, index=False, encoding="utf-8")

    print("Building representative case markdown report...")
    report = build_markdown_report(
        rows_df=rows_df,
        threshold=args.near_best_threshold,
        run_phase=args.run_phase,
        scale_mode=args.scale_mode,
    )
    report_path.write_text(report, encoding="utf-8")

    available_count = int((rows_df.get("availability_status", "") == "available").sum()) if not rows_df.empty else 0
    print("")
    print("Representative case analysis completed.")
    print(f"Rows: {len(rows_df)}")
    print(f"Available rows: {available_count}")
    print(f"Table: {table_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
