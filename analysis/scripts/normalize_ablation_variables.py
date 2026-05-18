from pathlib import Path
import ast
import pandas as pd


DATASETS = ["imdb", "fiben", "ldbc_snb"]


# ---------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------

def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return pd.read_csv(path, encoding="utf-8-sig")


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


def parse_list(value):
    if pd.isna(value):
        return []

    if isinstance(value, list):
        return [str(x) for x in value]

    text = str(value).strip()

    if text == "" or text.lower() in {"nan", "none"}:
        return []

    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
        return [str(parsed)]
    except Exception:
        if "|" in text:
            return [x.strip() for x in text.split("|") if x.strip()]
        if "," in text and not text.startswith("["):
            return [x.strip() for x in text.split(",") if x.strip()]
        return [text]


def list_to_pipe(values):
    values = [str(v).strip() for v in values if str(v).strip()]
    if not values:
        return ""
    return "|".join(sorted(set(values)))


def first_existing(row, columns, default=""):
    for col in columns:
        if col in row.index and not pd.isna(row[col]):
            return row[col]
    return default


def first_existing_numeric(row, columns, default=None):
    for col in columns:
        if col in row.index and not pd.isna(row[col]):
            value = to_float(row[col])
            if value is not None:
                return value
    return default


def derive_generic_class(query_name):
    text = safe_str(query_name)

    if text.startswith("QG"):
        return text.split("_")[0]

    if "_" in text:
        prefix = text.split("_")[0]
        if prefix.startswith(("IC", "IS", "INS")):
            return prefix

    return ""


def derive_fiben_semantic_type(row):
    active = []

    if to_bool(first_existing(row, ["touches_association"], False)):
        active.append("association")

    if to_bool(first_existing(row, ["touches_containment"], False)):
        active.append("containment")

    if to_bool(first_existing(row, ["touches_descriptor"], False)):
        active.append("descriptor")

    if to_bool(first_existing(row, ["touches_ownership"], False)):
        active.append("ownership")

    if to_bool(first_existing(row, ["touches_subtype"], False)):
        active.append("subtype")

    if not active:
        return "none"

    if len(active) == 1:
        return active[0]

    return "mixed"


def fill_zero_if_no_traversal(row):
    rc = to_float(row.get("Rc"))
    if rc is None:
        rc = to_float(row.get("Rc_weighted"))

    if rc == 0:
        for col in ["D", "Re", "DeltaR", "DeltaRratio"]:
            if pd.isna(row.get(col, None)):
                row[col] = 0.0

    return row


# ---------------------------------------------------------------------
# Query analytical metadata normalization
# ---------------------------------------------------------------------

def normalize_imdb_query_metadata(repo_root: Path) -> pd.DataFrame:
    path = repo_root / "analysis" / "imdb" / "ablation_variables" / "query_analytical_metadata_imdb.csv"
    df = read_csv(path)

    rows = []

    for _, row in df.iterrows():
        query_name = safe_str(row["query_name"])
        rc = first_existing_numeric(row, ["Rc"], 0.0)
        d = first_existing_numeric(row, ["D_value"], 0.0)
        re = first_existing_numeric(row, ["selected_Re"], None)
        delta_r = first_existing_numeric(row, ["selected_DeltaR"], None)
        delta_r_ratio = first_existing_numeric(row, ["selected_DeltaR_ratio"], None)

        if rc == 0:
            re = 0.0 if re is None else re
            delta_r = 0.0 if delta_r is None else delta_r
            delta_r_ratio = 0.0 if delta_r_ratio is None else delta_r_ratio

        rows.append({
            "dataset": "imdb",
            "query_name": query_name,
            "query_id": "",
            "generic_class": derive_generic_class(query_name),
            "query_family": "",
            "query_type": safe_str(first_existing(row, ["query_type"])),
            "selected_root": safe_str(first_existing(row, ["selected_root"])),
            "Rc": rc,
            "D": d,
            "selected_document_depth": first_existing_numeric(row, ["selected_document_depth"], d),
            "Re": re,
            "DeltaR": delta_r,
            "DeltaRratio": delta_r_ratio,
            "structural_coverage": safe_str(first_existing(row, ["selected_structural_coverage"])),
            "dominant_semantic_type": safe_str(first_existing(row, ["dominant_semantic_group"], "none")),
            "dominant_semantic_detail": safe_str(first_existing(row, ["dominant_semantic_detail"], "")),
            "association_count": first_existing_numeric(row, ["n_association"], 0.0),
            "associative_count": first_existing_numeric(row, ["n_associative"], 0.0),
            "containment_count": first_existing_numeric(row, ["n_containment"], 0.0),
            "lookup_count": 1.0 if rc == 0 else 0.0,
            "has_association": to_bool(first_existing(row, ["has_any_association"], False)),
            "has_associative": to_bool(first_existing(row, ["has_any_associative"], False)),
            "has_containment": to_bool(first_existing(row, ["has_any_containment"], False)),
            "update_volatility_mean": first_existing_numeric(row, ["query_avg_update_volatility"], None),
            "update_volatility_max": first_existing_numeric(row, ["query_max_update_volatility"], None),
            "update_volatility_class": safe_str(first_existing(row, ["query_volatility_class"], "")),
            "has_update_volatility": first_existing_numeric(row, ["query_entities_with_nonzero_volatility"], 0.0) > 0,
            "observed_sharedness_mean": first_existing_numeric(row, ["query_avg_sharedness"], None),
            "observed_sharedness_max": first_existing_numeric(row, ["query_max_sharedness"], None),
            "observed_sharedness_class": safe_str(first_existing(row, ["query_sharedness_class"], "")),
            "has_observed_sharedness": first_existing_numeric(row, ["query_entities_with_sharedness_gt_1"], 0.0) > 0,
            "document_candidate_assessment": safe_str(first_existing(row, ["document_candidate_assessment"], "")),
            "is_write_query": safe_str(first_existing(row, ["query_type"], "")).lower() in {"insert", "update", "delete", "write"},
            "source_file": str(path.relative_to(repo_root)).replace("\\", "/"),
        })

    return pd.DataFrame(rows)


def normalize_fiben_query_metadata(repo_root: Path) -> pd.DataFrame:
    path = repo_root / "analysis" / "fiben" / "ablation_variables" / "query_analytical_metadata_fiben.csv"
    df = read_csv(path)

    rows = []

    for _, row in df.iterrows():
        query_name = safe_str(row["query_name"])
        rc = first_existing_numeric(row, ["Rc"], 0.0)

        rows.append({
            "dataset": "fiben",
            "query_name": query_name,
            "query_id": "",
            "generic_class": safe_str(first_existing(row, ["generic_class"], derive_generic_class(query_name))),
            "query_family": safe_str(first_existing(row, ["query_family"], "")),
            "query_type": safe_str(first_existing(row, ["query_type"], "")),
            "selected_root": safe_str(first_existing(row, ["selected_root"], "")),
            "Rc": rc,
            "D": first_existing_numeric(row, ["document_depth", "selected_document_depth"], 0.0),
            "selected_document_depth": first_existing_numeric(row, ["selected_document_depth", "document_depth"], 0.0),
            "Re": first_existing_numeric(row, ["Re"], 0.0),
            "DeltaR": first_existing_numeric(row, ["DeltaR"], 0.0),
            "DeltaRratio": first_existing_numeric(row, ["DeltaRratio"], 0.0),
            "structural_coverage": safe_str(first_existing(row, ["document_potential_class"], "")),
            "dominant_semantic_type": derive_fiben_semantic_type(row),
            "dominant_semantic_detail": safe_str(first_existing(row, ["semantic_types_touched"], "")),
            "association_count": first_existing_numeric(row, ["n_association_edges"], 0.0),
            "associative_count": 0.0,
            "containment_count": first_existing_numeric(row, ["n_containment_edges"], 0.0),
            "lookup_count": 1.0 if rc == 0 else 0.0,
            "has_association": to_bool(first_existing(row, ["touches_association"], False)),
            "has_associative": False,
            "has_containment": to_bool(first_existing(row, ["touches_containment"], False)),
            "update_volatility_mean": first_existing_numeric(row, ["avg_touched_update_volatility", "query_update_volatility_score"], None),
            "update_volatility_max": first_existing_numeric(row, ["max_touched_update_volatility", "query_update_volatility_score"], None),
            "update_volatility_class": safe_str(first_existing(row, ["query_update_volatility_level"], "")),
            "has_update_volatility": to_bool(first_existing(row, ["has_query_update_volatility"], False)),
            "observed_sharedness_mean": first_existing_numeric(row, ["avg_observed_sharedness_score"], None),
            "observed_sharedness_max": first_existing_numeric(row, ["max_observed_sharedness_score"], None),
            "observed_sharedness_class": safe_str(first_existing(row, ["query_observed_sharedness_level"], "")),
            "has_observed_sharedness": to_bool(first_existing(row, ["has_observed_sharedness"], False)),
            "document_candidate_assessment": safe_str(first_existing(row, ["combined_document_design_risk_class", "document_potential_class"], "")),
            "is_write_query": to_bool(first_existing(row, ["is_write_query"], False)),
            "source_file": str(path.relative_to(repo_root)).replace("\\", "/"),
        })

    return pd.DataFrame(rows)


def normalize_ldbc_query_metadata(repo_root: Path) -> pd.DataFrame:
    path = repo_root / "analysis" / "ldbc_snb" / "ablation_variables" / "query_analytical_metadata_ldbc_snb.csv"
    df = read_csv(path)

    rows = []

    for _, row in df.iterrows():
        query_name = safe_str(row["query_name"])

        rows.append({
            "dataset": "ldbc_snb",
            "query_name": query_name,
            "query_id": safe_str(first_existing(row, ["official_id"], "")),
            "generic_class": safe_str(first_existing(row, ["official_id"], derive_generic_class(query_name))),
            "query_family": safe_str(first_existing(row, ["query_group"], "")),
            "query_type": safe_str(first_existing(row, ["operation_type"], "")),
            "selected_root": safe_str(first_existing(row, ["root_entity"], "")),
            "Rc": first_existing_numeric(row, ["Rc_weighted", "Rc_distinct"], 0.0),
            "D": first_existing_numeric(row, ["D"], 0.0),
            "selected_document_depth": first_existing_numeric(row, ["D"], 0.0),
            "Re": first_existing_numeric(row, ["Re"], 0.0),
            "DeltaR": first_existing_numeric(row, ["DeltaR"], 0.0),
            "DeltaRratio": first_existing_numeric(row, ["DeltaRratio"], 0.0),
            "structural_coverage": safe_str(first_existing(row, ["structural_reduction_class"], "")),
            "dominant_semantic_type": safe_str(first_existing(row, ["dominant_semantic_type"], "")),
            "dominant_semantic_detail": safe_str(first_existing(row, ["weighted_relationships"], "")),
            "association_count": first_existing_numeric(row, ["association_count"], 0.0),
            "associative_count": first_existing_numeric(row, ["associative_count"], 0.0),
            "containment_count": first_existing_numeric(row, ["containment_count"], 0.0),
            "lookup_count": first_existing_numeric(row, ["lookup_count"], 0.0),
            "has_association": first_existing_numeric(row, ["association_count"], 0.0) > 0,
            "has_associative": first_existing_numeric(row, ["associative_count"], 0.0) > 0,
            "has_containment": first_existing_numeric(row, ["containment_count"], 0.0) > 0,
            "update_volatility_mean": first_existing_numeric(row, ["update_volatility_mean"], None),
            "update_volatility_max": first_existing_numeric(row, ["update_volatility_max"], None),
            "update_volatility_class": safe_str(first_existing(row, ["update_volatility_class"], "")),
            "has_update_volatility": first_existing_numeric(row, ["update_volatility_max"], 0.0) > 0,
            "observed_sharedness_mean": first_existing_numeric(row, ["observed_sharedness_mean"], None),
            "observed_sharedness_max": first_existing_numeric(row, ["observed_sharedness_max"], None),
            "observed_sharedness_class": safe_str(first_existing(row, ["observed_sharedness_class"], "")),
            "has_observed_sharedness": first_existing_numeric(row, ["observed_sharedness_max"], 0.0) > 0,
            "document_candidate_assessment": safe_str(first_existing(row, ["description"], "")),
            "is_write_query": safe_str(first_existing(row, ["operation_type"], "")).lower() in {"insert", "update", "delete", "write"},
            "source_file": str(path.relative_to(repo_root)).replace("\\", "/"),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Activation normalization
# ---------------------------------------------------------------------

def normalize_imdb_activation(repo_root: Path) -> pd.DataFrame:
    path = repo_root / "analysis" / "imdb" / "ablation_variables" / "query_class_activation_imdb.csv"
    df = read_csv(path)

    rows = []

    for _, row in df.iterrows():
        rows.append({
            "dataset": "imdb",
            "query_name": safe_str(row["query_name"]),
            "query_id": "",
            "generic_class": safe_str(first_existing(row, ["generic_class"], derive_generic_class(row["query_name"]))),
            "selected_root": safe_str(first_existing(row, ["selected_root"], "")),
            "g_class": safe_str(first_existing(row, ["activated_class"], "")).upper(),
            "is_active": True,
            "activation_status": "active",
            "activation_strength": "active",
            "activation_score": 1.0,
            "activation_reason": safe_str(first_existing(row, ["activation_reason"], "")),
            "g_family": "",
            "g_role": "",
            "g_label": "",
            "source_file": str(path.relative_to(repo_root)).replace("\\", "/"),
        })

    return pd.DataFrame(rows)


def normalize_fiben_activation(repo_root: Path) -> pd.DataFrame:
    path = repo_root / "analysis" / "fiben" / "ablation_variables" / "query_class_activation_long_fiben.csv"
    df = read_csv(path)

    rows = []

    for _, row in df.iterrows():
        rows.append({
            "dataset": "fiben",
            "query_name": safe_str(row["query_name"]),
            "query_id": "",
            "generic_class": safe_str(first_existing(row, ["generic_class"], derive_generic_class(row["query_name"]))),
            "selected_root": safe_str(first_existing(row, ["selected_root"], "")),
            "g_class": safe_str(first_existing(row, ["g_class"], "")).upper(),
            "is_active": to_bool(first_existing(row, ["is_active"], False)),
            "activation_status": safe_str(first_existing(row, ["activation_status"], "")),
            "activation_strength": safe_str(first_existing(row, ["activation_status"], "")),
            "activation_score": first_existing_numeric(row, ["activation_score"], None),
            "activation_reason": safe_str(first_existing(row, ["activation_reason"], "")),
            "g_family": "",
            "g_role": "",
            "g_label": safe_str(first_existing(row, ["g_class_name"], "")),
            "source_file": str(path.relative_to(repo_root)).replace("\\", "/"),
        })

    return pd.DataFrame(rows)


def normalize_ldbc_activation(repo_root: Path) -> pd.DataFrame:
    path = repo_root / "analysis" / "ldbc_snb" / "ablation_variables" / "query_class_activation_long_ldbc_snb.csv"
    df = read_csv(path)

    rows = []

    for _, row in df.iterrows():
        rows.append({
            "dataset": "ldbc_snb",
            "query_name": safe_str(row["query_name"]),
            "query_id": safe_str(first_existing(row, ["official_id"], "")),
            "generic_class": safe_str(first_existing(row, ["official_id"], derive_generic_class(row["query_name"]))),
            "selected_root": safe_str(first_existing(row, ["root_entity"], "")),
            "g_class": safe_str(first_existing(row, ["g_class"], "")).upper(),
            "is_active": True,
            "activation_status": safe_str(first_existing(row, ["activation_strength"], "active")),
            "activation_strength": safe_str(first_existing(row, ["activation_strength"], "active")),
            "activation_score": None,
            "activation_reason": safe_str(first_existing(row, ["activation_reason"], "")),
            "g_family": safe_str(first_existing(row, ["g_family"], "")),
            "g_role": safe_str(first_existing(row, ["g_role"], "")),
            "g_label": safe_str(first_existing(row, ["g_label"], "")),
            "source_file": str(path.relative_to(repo_root)).replace("\\", "/"),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Benchmark/candidate normalization
# ---------------------------------------------------------------------

def normalize_imdb_benchmark(repo_root: Path) -> pd.DataFrame:
    path = repo_root / "analysis" / "imdb" / "ablation_variables" / "benchmark_coverage_imdb.csv"
    df = read_csv(path)

    rows = []

    group_columns = {
        "primary_queries": "primary",
        "secondary_affected_queries": "secondary_affected",
        "control_queries": "control",
    }

    for _, row in df.iterrows():
        config_id = safe_str(row["config_name"])
        g_class = safe_str(row["activated_class"]).upper()

        for col, benchmark_group in group_columns.items():
            queries = parse_list(row.get(col, ""))

            for query_name in queries:
                rows.append({
                    "dataset": "imdb",
                    "query_name": query_name,
                    "query_id": "",
                    "config_id": config_id,
                    "candidate_id": config_id,
                    "g_class": g_class,
                    "design_family": safe_str(first_existing(row, ["benchmark_family"], "")),
                    "design_pattern": safe_str(first_existing(row, ["embedding_variant", "benchmark_family"], "")),
                    "benchmark_group": benchmark_group,
                    "selection_role": "",
                    "selected_root": safe_str(first_existing(row, ["selected_root"], "")),
                    "candidate_selection_score": None,
                    "source_file": str(path.relative_to(repo_root)).replace("\\", "/"),
                })

    return pd.DataFrame(rows)


def normalize_fiben_benchmark(repo_root: Path) -> pd.DataFrame:
    path = repo_root / "analysis" / "fiben" / "ablation_variables" / "benchmark_configuration_selection_fiben.csv"
    df = read_csv(path)

    rows = []

    for _, row in df.iterrows():
        rows.append({
            "dataset": "fiben",
            "query_name": safe_str(row["query_name"]),
            "query_id": "",
            "config_id": safe_str(row["candidate_id"]),
            "candidate_id": safe_str(row["candidate_id"]),
            "g_class": safe_str(row["g_class"]).upper(),
            "design_family": safe_str(first_existing(row, ["design_pattern"], "")),
            "design_pattern": safe_str(first_existing(row, ["design_pattern"], "")),
            "benchmark_group": safe_str(first_existing(row, ["final_benchmark_group"], "")).lower(),
            "selection_role": safe_str(first_existing(row, ["selection_role"], "")),
            "selected_root": safe_str(first_existing(row, ["root_entity"], "")),
            "candidate_selection_score": first_existing_numeric(row, ["candidate_selection_score"], None),
            "source_file": str(path.relative_to(repo_root)).replace("\\", "/"),
        })

    return pd.DataFrame(rows)


def normalize_ldbc_benchmark(repo_root: Path) -> pd.DataFrame:
    path = repo_root / "analysis" / "ldbc_snb" / "ablation_variables" / "benchmark_execution_plan_ldbc_snb.csv"
    df = read_csv(path)

    rows = []

    for _, row in df.iterrows():
        rows.append({
            "dataset": "ldbc_snb",
            "query_name": safe_str(row["query_name"]),
            "query_id": safe_str(first_existing(row, ["official_id"], "")),
            "config_id": safe_str(row["candidate_id"]),
            "candidate_id": safe_str(row["candidate_id"]),
            "g_class": safe_str(row["g_class"]).upper(),
            "design_family": safe_str(first_existing(row, ["g_family"], "")),
            "design_pattern": safe_str(first_existing(row, ["mongodb_pattern", "document_strategy"], "")),
            "benchmark_group": safe_str(first_existing(row, ["benchmark_group"], "")).lower(),
            "selection_role": safe_str(first_existing(row, ["activation_strength"], "")),
            "selected_root": safe_str(first_existing(row, ["root_entity"], "")),
            "candidate_selection_score": None,
            "source_file": str(path.relative_to(repo_root)).replace("\\", "/"),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------

def validate_outputs(query_df, activation_df, benchmark_df):
    lines = []

    lines.append("# Ablation Variables Normalization Report")
    lines.append("")
    lines.append("This report summarizes normalized analytical metadata, activation outputs, and benchmark configuration selections.")
    lines.append("")

    lines.append("## Output row counts")
    lines.append(f"- query_analytical_metadata_all_datasets.csv: {len(query_df)} rows")
    lines.append(f"- query_class_activation_all_datasets.csv: {len(activation_df)} rows")
    lines.append(f"- benchmark_configuration_selection_all_datasets.csv: {len(benchmark_df)} rows")
    lines.append("")

    lines.append("## Query metadata by dataset")
    for dataset, group in query_df.groupby("dataset"):
        lines.append(f"- {dataset}: rows={len(group)}, unique_queries={group['query_name'].nunique()}")

    lines.append("")
    lines.append("## Activation rows by dataset")
    for dataset, group in activation_df.groupby("dataset"):
        active = group[group["is_active"] == True]
        lines.append(
            f"- {dataset}: rows={len(group)}, active_rows={len(active)}, "
            f"unique_queries={group['query_name'].nunique()}, "
            f"active_g_classes={list_to_pipe(active['g_class'].dropna().unique())}"
        )

    lines.append("")
    lines.append("## Benchmark selection rows by dataset")
    for dataset, group in benchmark_df.groupby("dataset"):
        groups = group["benchmark_group"].dropna().unique()
        lines.append(
            f"- {dataset}: rows={len(group)}, unique_queries={group['query_name'].nunique()}, "
            f"groups={list_to_pipe(groups)}, g_classes={list_to_pipe(group['g_class'].dropna().unique())}"
        )

    lines.append("")
    lines.append("## Validation checks")

    required_query_cols = [
        "dataset", "query_name", "selected_root", "Rc", "D", "Re",
        "DeltaR", "DeltaRratio", "dominant_semantic_type",
        "update_volatility_max", "observed_sharedness_max"
    ]

    required_activation_cols = [
        "dataset", "query_name", "g_class", "is_active", "activation_reason"
    ]

    required_benchmark_cols = [
        "dataset", "query_name", "config_id", "g_class", "benchmark_group"
    ]

    for label, df, cols in [
        ("query metadata", query_df, required_query_cols),
        ("activation", activation_df, required_activation_cols),
        ("benchmark selection", benchmark_df, required_benchmark_cols),
    ]:
        missing_cols = [c for c in cols if c not in df.columns]
        lines.append(f"- Missing columns in {label}: {missing_cols}")

    for dataset in DATASETS:
        q_queries = set(query_df.loc[query_df["dataset"] == dataset, "query_name"])
        a_queries = set(activation_df.loc[activation_df["dataset"] == dataset, "query_name"])
        b_queries = set(benchmark_df.loc[benchmark_df["dataset"] == dataset, "query_name"])

        lines.append(f"- {dataset}: query metadata not in activation = {sorted(q_queries - a_queries)}")
        lines.append(f"- {dataset}: query metadata not in benchmark selection = {sorted(q_queries - b_queries)}")
        lines.append(f"- {dataset}: benchmark selection not in query metadata = {sorted(b_queries - q_queries)}")

    lines.append("")
    lines.append("## Important note")
    lines.append(
        "FIBEN activation contains both active and inactive G-class rows. "
        "For full SchemaLens selection, downstream scripts should use only rows where is_active is True."
    )
    lines.append(
        "IMDb activation contains only activated rows. "
        "LDBC SNB activation also contains activated rows with activation strength."
    )

    return "\n".join(lines)


def main():
    repo_root = Path(__file__).resolve().parents[2]
    output_dir = repo_root / "analysis" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Normalizing query analytical metadata...")
    query_df = pd.concat(
        [
            normalize_imdb_query_metadata(repo_root),
            normalize_fiben_query_metadata(repo_root),
            normalize_ldbc_query_metadata(repo_root),
        ],
        ignore_index=True,
    )

    print("Normalizing class activation outputs...")
    activation_df = pd.concat(
        [
            normalize_imdb_activation(repo_root),
            normalize_fiben_activation(repo_root),
            normalize_ldbc_activation(repo_root),
        ],
        ignore_index=True,
    )

    print("Normalizing benchmark configuration selections...")
    benchmark_df = pd.concat(
        [
            normalize_imdb_benchmark(repo_root),
            normalize_fiben_benchmark(repo_root),
            normalize_ldbc_benchmark(repo_root),
        ],
        ignore_index=True,
    )

    # Stable ordering
    query_df = query_df.sort_values(["dataset", "query_name"]).reset_index(drop=True)
    activation_df = activation_df.sort_values(["dataset", "query_name", "g_class"]).reset_index(drop=True)
    benchmark_df = benchmark_df.sort_values(["dataset", "query_name", "benchmark_group", "g_class", "config_id"]).reset_index(drop=True)

    query_path = output_dir / "query_analytical_metadata_all_datasets.csv"
    activation_path = output_dir / "query_class_activation_all_datasets.csv"
    benchmark_path = output_dir / "benchmark_configuration_selection_all_datasets.csv"
    report_path = output_dir / "ablation_variables_normalization_report.txt"

    query_df.to_csv(query_path, index=False, encoding="utf-8")
    activation_df.to_csv(activation_path, index=False, encoding="utf-8")
    benchmark_df.to_csv(benchmark_path, index=False, encoding="utf-8")

    report = validate_outputs(query_df, activation_df, benchmark_df)
    report_path.write_text(report, encoding="utf-8")

    print("")
    print("Ablation variable normalization completed.")
    print(f"Query metadata rows: {len(query_df)}")
    print(f"Activation rows: {len(activation_df)}")
    print(f"Benchmark selection rows: {len(benchmark_df)}")
    print("")
    print(f"CSV: {query_path}")
    print(f"CSV: {activation_path}")
    print(f"CSV: {benchmark_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()