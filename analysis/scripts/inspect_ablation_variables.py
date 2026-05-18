from pathlib import Path
import pandas as pd


REQUIRED_BY_DATASET = {
    "imdb": {
        "query_metadata": [
            "query_name",
            "selected_root",
            "Rc",
            "D_value",
            "selected_Re",
            "selected_DeltaR",
            "selected_DeltaR_ratio",
            "n_association",
            "n_associative",
            "n_containment",
            "query_avg_update_volatility",
            "query_max_update_volatility",
            "query_volatility_class",
            "query_avg_sharedness",
            "query_max_sharedness",
            "query_sharedness_class",
            "has_any_association",
            "has_any_associative",
            "has_any_containment",
        ],
        "activation": [
            "query_name",
            "activated_class",
            "activation_reason",
        ],
        "benchmark": [
            "config_name",
            "activated_class",
            "benchmark_family",
            "primary_queries",
            "secondary_affected_queries",
            "control_queries",
        ],
        "reduction": [
            "query_name",
            "selected_root",
            "test_depth",
            "Rc",
            "Re",
            "DeltaR",
            "DeltaRratio",
        ],
    },
    "fiben": {
        "query_metadata": [
            "query_name",
            "selected_root",
            "document_depth",
            "Rc",
            "Re",
            "DeltaR",
            "DeltaRratio",
            "touches_association",
            "touches_containment",
            "touches_descriptor",
            "touches_ownership",
            "touches_subtype",
            "query_update_volatility_score",
            "query_update_volatility_level",
            "has_query_update_volatility",
            "avg_observed_sharedness_score",
            "max_observed_sharedness_score",
            "query_observed_sharedness_level",
            "has_observed_sharedness",
            "activation_has_relationship_traversal",
            "activation_has_read_reduction",
            "activation_has_update_pressure",
            "activation_has_sharedness_pressure",
        ],
        "activation": [
            "query_name",
            "active_g_classes",
            "primary_activation_class",
            "activation_has_g0",
            "activation_has_g1",
            "activation_has_g2",
            "activation_has_g3",
            "activation_has_g4",
            "activation_has_g5",
            "activation_has_g6",
            "activation_has_g7",
            "activation_has_g8",
            "activation_has_g9",
        ],
        "activation_long": [
            "query_name",
            "g_class",
            "is_active",
            "activation_status",
            "activation_score",
            "activation_reason",
        ],
        "benchmark": [
            "candidate_id",
            "query_name",
            "g_class",
            "design_pattern",
            "final_benchmark_group",
            "selection_role",
            "candidate_selection_score",
        ],
        "reduction": [
            "query_name",
            "selected_root",
            "document_depth",
            "Rc",
            "Re",
            "DeltaR",
            "DeltaRratio",
        ],
    },
    "ldbc_snb": {
        "query_metadata": [
            "query_name",
            "official_id",
            "query_group",
            "operation_type",
            "root_entity",
            "Rc_weighted",
            "D",
            "Re",
            "DeltaR",
            "DeltaRratio",
            "association_count",
            "associative_count",
            "containment_count",
            "lookup_count",
            "dominant_semantic_type",
            "update_volatility_mean",
            "update_volatility_max",
            "update_volatility_class",
            "observed_sharedness_mean",
            "observed_sharedness_max",
            "observed_sharedness_class",
        ],
        "activation_long": [
            "query_name",
            "official_id",
            "g_class",
            "activation_strength",
            "activation_reason",
            "g_family",
            "g_role",
            "g_label",
        ],
        "activation": [
            "query_name",
            "official_id",
            "activated_g_classes",
            "primary_g_classes",
            "secondary_g_classes",
            "control_g_classes",
            "n_activated_classes",
        ],
        "benchmark": [
            "candidate_id",
            "query_name",
            "official_id",
            "benchmark_group",
            "activation_strength",
            "activation_reason",
            "root_entity",
            "g_class",
            "g_family",
            "g_role",
            "mongodb_pattern",
            "document_strategy",
            "Rc_weighted",
            "D",
            "Re",
            "DeltaRratio",
            "dominant_semantic_type",
            "update_volatility_max",
            "observed_sharedness_max",
        ],
        "reduction": [
            "query_name",
            "official_id",
            "Rc_weighted",
            "D",
            "Re",
            "DeltaR",
            "DeltaRratio",
        ],
    },
}


ROLE_KEYWORDS = {
    "query_metadata": [
        "query_analytical_metadata",
        "document_variable_matrix",
        "final_document_variable_matrix",
        "snb_final_analytical_matrix",
    ],
    "activation": [
        "query_class_activation",
        "activation_summary",
        "g_class_activation_by_query",
        "snb_activation_summary",
    ],
    "activation_long": [
        "query_class_activation_long",
        "g_class_activation_long",
        "activation_matrix",
        "snb_activation_matrix",
    ],
    "benchmark": [
        "benchmark_configuration_selection",
        "benchmark_execution_plan",
        "benchmark_coverage",
    ],
    "reduction": [
        "reduction",
        "re_delta",
        "re_full",
        "snb_reduction_metrics",
        "structural_reduction",
        "best_depth",
    ],
}


def guess_roles(file_name: str):
    name = file_name.lower()
    roles = []
    for role, keywords in ROLE_KEYWORDS.items():
        if any(k in name for k in keywords):
            roles.append(role)
    return roles or ["unknown"]


def inspect_file(path: Path, dataset: str):
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception as exc:
        return {
            "dataset": dataset,
            "file": str(path),
            "status": f"ERROR: {exc}",
            "rows": None,
            "cols": None,
            "roles": "unknown",
            "matched_required_columns": "",
            "missing_required_columns": "",
            "all_columns": "",
        }

    roles = guess_roles(path.name)

    matched = {}
    missing = {}

    for role in roles:
        if role in REQUIRED_BY_DATASET.get(dataset, {}):
            required = REQUIRED_BY_DATASET[dataset][role]
            matched[role] = [c for c in required if c in df.columns]
            missing[role] = [c for c in required if c not in df.columns]

    return {
        "dataset": dataset,
        "file": str(path),
        "status": "OK",
        "rows": len(df),
        "cols": len(df.columns),
        "roles": "|".join(roles),
        "matched_required_columns": str(matched),
        "missing_required_columns": str(missing),
        "all_columns": str(list(df.columns)),
    }


def main():
    repo_root = Path(__file__).resolve().parents[2]
    output_dir = repo_root / "analysis" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    text_lines = []

    for dataset in ["imdb", "fiben", "ldbc_snb"]:
        folder = repo_root / "analysis" / dataset / "ablation_variables"

        text_lines.append("=" * 120)
        text_lines.append(f"DATASET: {dataset}")
        text_lines.append(f"FOLDER: {folder}")

        if not folder.exists():
            text_lines.append("STATUS: FOLDER MISSING")
            text_lines.append("")
            continue

        files = sorted(folder.glob("*.csv"))

        if not files:
            text_lines.append("STATUS: NO CSV FILES FOUND")
            text_lines.append("")
            continue

        text_lines.append(f"CSV files found: {len(files)}")
        text_lines.append("")

        for path in files:
            info = inspect_file(path, dataset)
            rows.append(info)

            text_lines.append("-" * 120)
            text_lines.append(f"FILE: {path.name}")
            text_lines.append(f"STATUS: {info['status']}")
            text_lines.append(f"ROWS: {info['rows']}")
            text_lines.append(f"COLS: {info['cols']}")
            text_lines.append(f"ROLES: {info['roles']}")
            text_lines.append(f"MATCHED REQUIRED COLUMNS:")
            text_lines.append(info["matched_required_columns"])
            text_lines.append(f"MISSING REQUIRED COLUMNS:")
            text_lines.append(info["missing_required_columns"])
            text_lines.append("")

            if info["status"] == "OK":
                df = pd.read_csv(path, encoding="utf-8-sig")
                text_lines.append("FIRST 2 ROWS:")
                text_lines.append(df.head(2).to_string(index=False))
                text_lines.append("")

    report_df = pd.DataFrame(rows)

    csv_path = output_dir / "ablation_variables_inventory.csv"
    report_path = output_dir / "ablation_variables_inventory_report.txt"

    report_df.to_csv(csv_path, index=False, encoding="utf-8")
    report_path.write_text("\n".join(text_lines), encoding="utf-8")

    print("Ablation variable inventory completed.")
    print(f"CSV: {csv_path}")
    print(f"Report: {report_path}")

    if not report_df.empty:
        print("")
        print("Short summary:")
        print(report_df[["dataset", "file", "status", "rows", "cols", "roles"]].to_string(index=False))


if __name__ == "__main__":
    main()