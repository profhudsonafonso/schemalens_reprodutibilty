#!/usr/bin/env python3
from pathlib import Path
import argparse
import pandas as pd
import json

def log(msg):
    print(f"[control-plan] {msg}")

def read_csv_safe(path):
    try:
        return pd.read_csv(path)
    except Exception:
        return None

def normalize_group(value):
    if pd.isna(value):
        return ""
    v = str(value).strip()
    mapping = {
        "secondary": "secondary_affected",
        "secondary-affected": "secondary_affected",
        "secondary_affected": "secondary_affected",
        "primary": "primary",
        "control": "control",
        "baseline": "control",
    }
    return mapping.get(v, v)

def find_candidate_csvs(root):
    root = Path(root)
    csvs = []
    for p in root.rglob("*.csv"):
        try:
            head = pd.read_csv(p, nrows=5)
        except Exception:
            continue

        cols = set(head.columns)
        if "candidate_id" in cols and ("official_id" in cols or "query_name" in cols):
            csvs.append(p)
    return csvs

def first_existing_col(df, names):
    for n in names:
        if n in df.columns:
            return n
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifacts-dir", required=True)
    ap.add_argument("--activated-manifest", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    artifacts_dir = Path(args.artifacts_dir)
    activated_manifest_path = Path(args.activated_manifest)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not activated_manifest_path.exists():
        raise FileNotFoundError(f"Activated manifest not found: {activated_manifest_path}")

    activated = pd.read_csv(activated_manifest_path)
    if "candidate_id" not in activated.columns:
        raise ValueError("Activated manifest does not contain candidate_id")

    activated_ids = set(activated["candidate_id"].astype(str))

    log(f"Activated manifest rows: {len(activated)}")
    log(f"Activated unique candidates: {len(activated_ids)}")

    candidate_csvs = find_candidate_csvs(artifacts_dir)
    log(f"Candidate-like CSV files found: {len(candidate_csvs)}")

    inventory_frames = []

    for p in candidate_csvs:
        df = read_csv_safe(p)
        if df is None or df.empty:
            continue

        if "candidate_id" not in df.columns:
            continue

        official_col = first_existing_col(df, ["official_id", "query_id"])
        query_col = first_existing_col(df, ["query_name", "official_title", "query"])
        group_col = first_existing_col(df, ["benchmark_group", "final_benchmark_group", "query_group", "group"])
        g_col = first_existing_col(df, ["g_class", "g", "template", "class"])
        pattern_col = first_existing_col(df, ["mongodb_pattern", "design_pattern", "pattern"])
        strategy_col = first_existing_col(df, ["document_strategy", "strategy"])
        root_col = first_existing_col(df, ["root_entity", "root_collection"])

        keep = pd.DataFrame()
        keep["source_file"] = str(p)
        keep["candidate_id"] = df["candidate_id"].astype(str)

        keep["official_id"] = df[official_col].astype(str) if official_col else ""
        keep["query_name"] = df[query_col].astype(str) if query_col else ""
        keep["benchmark_group_raw"] = df[group_col].astype(str) if group_col else ""
        keep["benchmark_group"] = keep["benchmark_group_raw"].map(normalize_group)

        keep["g_class"] = df[g_col].astype(str) if g_col else ""
        keep["mongodb_pattern"] = df[pattern_col].astype(str) if pattern_col else ""
        keep["document_strategy"] = df[strategy_col].astype(str) if strategy_col else ""
        keep["root_entity"] = df[root_col].astype(str) if root_col else ""

        inventory_frames.append(keep)

    if not inventory_frames:
        raise RuntimeError(f"No candidate inventory found under {artifacts_dir}")

    inv = pd.concat(inventory_frames, ignore_index=True)

    # Drop exact duplicates but keep source_file evidence if same candidate appears in multiple files.
    inv = inv.drop_duplicates()

    # Prefer rows with explicit benchmark_group.
    inv["has_group"] = inv["benchmark_group"].astype(str).str.len() > 0

    # Candidate-level compact inventory.
    sort_cols = ["candidate_id", "has_group"]
    inv = inv.sort_values(sort_cols, ascending=[True, False])

    compact_rows = []
    for cid, gdf in inv.groupby("candidate_id", sort=False):
        best = gdf.iloc[0].copy()
        best["all_source_files"] = " | ".join(
            sorted(
                {
                    str(x)
                    for x in gdf["source_file"].dropna().tolist()
                    if str(x).strip() and str(x).strip().lower() != "nan"
                }
            )
        )
        groups = sorted(set([x for x in gdf["benchmark_group"].astype(str) if x and x != "nan"]))
        best["all_benchmark_groups_found"] = ",".join(groups)
        compact_rows.append(best)

    compact = pd.DataFrame(compact_rows)

    compact["already_materialized"] = compact["candidate_id"].astype(str).isin(activated_ids)
    compact["needs_materialization"] = (
        (compact["benchmark_group"] == "control") &
        (~compact["already_materialized"])
    )

    compact["materialization_role"] = compact["benchmark_group"].map(
        lambda x: "activated" if x in {"primary", "secondary_affected"} else ("control" if x == "control" else "unknown")
    )

    compact["reason"] = ""
    compact.loc[compact["already_materialized"], "reason"] = "already_materialized_in_phase_1A"
    compact.loc[compact["needs_materialization"], "reason"] = "control_candidate_missing_from_phase_1A"
    compact.loc[
        (~compact["already_materialized"]) &
        (compact["benchmark_group"] != "control"),
        "reason"
    ] = "not_materialized_and_not_explicit_control_in_discovered_plan"

    inv.to_csv(out_dir / "candidate_source_inventory_raw.csv", index=False)
    compact.to_csv(out_dir / "candidate_source_inventory_compact.csv", index=False)

    control_plan = compact[compact["benchmark_group"] == "control"].copy()
    control_plan.to_csv(out_dir / "sf0_1_control_expansion_plan.csv", index=False)

    missing_controls = control_plan[control_plan["needs_materialization"] == True].copy()
    missing_controls.to_csv(out_dir / "sf0_1_controls_to_materialize.csv", index=False)

    summary = {
        "activated_manifest_rows": int(len(activated)),
        "activated_unique_candidates": int(len(activated_ids)),
        "candidate_like_csv_files_found": int(len(candidate_csvs)),
        "inventory_unique_candidates": int(compact["candidate_id"].nunique()),
        "primary_rows_discovered": int((compact["benchmark_group"] == "primary").sum()),
        "secondary_affected_rows_discovered": int((compact["benchmark_group"] == "secondary_affected").sum()),
        "control_rows_discovered": int((compact["benchmark_group"] == "control").sum()),
        "control_already_materialized": int(((compact["benchmark_group"] == "control") & (compact["already_materialized"] == True)).sum()),
        "control_needs_materialization": int(((compact["benchmark_group"] == "control") & (compact["needs_materialization"] == True)).sum()),
    }

    pd.DataFrame([summary]).to_csv(out_dir / "sf0_1_control_expansion_summary.csv", index=False)

    readme = out_dir / "README_control_expansion_plan.md"
    readme.write_text(
        "# LDBC SNB SF0.1 control expansion plan\n\n"
        "This folder contains the Phase 1B control-expansion inventory.\n\n"
        "Phase 1A materialized the activated SchemaLens space, i.e., "
        "`primary + secondary_affected` candidates. Phase 1B identifies the "
        "`control` candidates from the original benchmark-planning artifacts that "
        "are not yet physically materialized.\n\n"
        "Files:\n\n"
        "- `candidate_source_inventory_raw.csv`: all candidate-like rows found under the artifact directory.\n"
        "- `candidate_source_inventory_compact.csv`: candidate-level deduplicated inventory.\n"
        "- `sf0_1_control_expansion_plan.csv`: all discovered control candidates.\n"
        "- `sf0_1_controls_to_materialize.csv`: control candidates missing from Phase 1A.\n"
        "- `sf0_1_control_expansion_summary.csv`: summary counts.\n\n"
        "Methodological rule:\n\n"
        "- DSR uses only activated candidates: `primary + secondary_affected`.\n"
        "- Top-1 preservation, near-best, activated regret, and primary regret use "
        "`primary + secondary_affected + control` as the broader benchmarked comparison space.\n",
        encoding="utf-8"
    )

    log("Wrote outputs to:")
    log(str(out_dir))
    log("Summary:")
    for k, v in summary.items():
        log(f"  {k}: {v}")

    if summary["control_needs_materialization"] == 0:
        log("No missing control candidates found in discovered artifacts.")
    else:
        log("Missing controls to materialize:")
        cols = ["official_id", "query_name", "candidate_id", "g_class", "benchmark_group", "mongodb_pattern", "document_strategy"]
        cols = [c for c in cols if c in missing_controls.columns]
        print(missing_controls[cols].to_string(index=False))

if __name__ == "__main__":
    main()
