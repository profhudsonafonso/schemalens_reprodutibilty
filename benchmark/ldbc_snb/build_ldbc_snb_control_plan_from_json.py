#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import pandas as pd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-json", required=True)
    ap.add_argument("--activated-manifest", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    candidate_json = Path(args.candidate_json)
    activated_manifest = Path(args.activated_manifest)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(candidate_json.read_text())

    activated = pd.read_csv(activated_manifest)
    activated_ids = set(activated["candidate_id"].astype(str))

    rows = []
    for cid, spec in data.items():
        strength = str(spec.get("activation_strength", "")).strip()

        benchmark_group = {
            "primary": "primary",
            "secondary": "secondary_affected",
            "secondary_affected": "secondary_affected",
            "control": "control",
        }.get(strength, strength)

        row = {
            "candidate_id": cid,
            "official_id": spec.get("official_id", ""),
            "query_name": spec.get("query_name", ""),
            "benchmark_group": benchmark_group,
            "activation_strength_raw": strength,
            "g_class": spec.get("g_class", ""),
            "mongodb_pattern": spec.get("mongodb_pattern", ""),
            "document_strategy": spec.get("document_strategy", ""),
            "root_entity": spec.get("root_entity", ""),
            "activation_reason": spec.get("activation_reason", ""),
            "already_materialized": cid in activated_ids,
        }

        row["is_activated"] = row["benchmark_group"] in {"primary", "secondary_affected"}
        row["needs_materialization"] = (
            row["benchmark_group"] == "control"
            and not row["already_materialized"]
        )

        if row["already_materialized"]:
            row["reason"] = "already_materialized_in_phase_1A"
        elif row["benchmark_group"] == "control":
            row["reason"] = "control_candidate_missing_from_phase_1A"
        elif row["is_activated"]:
            row["reason"] = "activated_candidate_missing_unexpected"
        else:
            row["reason"] = "unknown_group"

        rows.append(row)

    df = pd.DataFrame(rows)

    df.to_csv(out_dir / "candidate_inventory_from_json.csv", index=False)

    controls = df[df["benchmark_group"] == "control"].copy()
    controls.to_csv(out_dir / "sf0_1_control_expansion_plan.csv", index=False)

    missing_controls = controls[controls["needs_materialization"] == True].copy()
    missing_controls.to_csv(out_dir / "sf0_1_controls_to_materialize.csv", index=False)

    activated_missing = df[(df["is_activated"] == True) & (df["already_materialized"] == False)].copy()
    activated_missing.to_csv(out_dir / "sf0_1_activated_missing_unexpected.csv", index=False)

    summary = {
        "json_total_candidates": int(len(df)),
        "activated_manifest_rows": int(len(activated)),
        "activated_manifest_unique_candidates": int(len(activated_ids)),
        "primary_candidates": int((df["benchmark_group"] == "primary").sum()),
        "secondary_affected_candidates": int((df["benchmark_group"] == "secondary_affected").sum()),
        "control_candidates": int((df["benchmark_group"] == "control").sum()),
        "primary_already_materialized": int(((df["benchmark_group"] == "primary") & (df["already_materialized"] == True)).sum()),
        "secondary_already_materialized": int(((df["benchmark_group"] == "secondary_affected") & (df["already_materialized"] == True)).sum()),
        "control_already_materialized": int(((df["benchmark_group"] == "control") & (df["already_materialized"] == True)).sum()),
        "control_needs_materialization": int((missing_controls["needs_materialization"] == True).sum()),
        "activated_missing_unexpected": int(len(activated_missing)),
    }

    pd.DataFrame([summary]).to_csv(out_dir / "sf0_1_control_expansion_summary.csv", index=False)

    readme = out_dir / "README_control_expansion_plan.md"
    readme.write_text(
        "# LDBC SNB SF0.1 Phase 1B control expansion plan\n\n"
        "This plan was generated from `mongodb_candidate_specs_by_candidate_id.json`, "
        "because the candidate JSON stores `activation_strength` values for "
        "`primary`, `secondary`, and `control` candidates.\n\n"
        "Phase 1A materialized the activated SchemaLens space, i.e., "
        "`primary + secondary_affected` candidates. Phase 1B identifies the "
        "`control` candidates that are part of the broader benchmarked comparison "
        "space and are not yet physically materialized.\n\n"
        "Methodological rule:\n\n"
        "- `primary + secondary_affected` form the activated family A(Q).\n"
        "- `control` candidates are not counted in DSR.\n"
        "- Top-1 preservation, near-best preservation, activated regret, and primary "
        "regret compare against `primary + secondary_affected + control`.\n",
        encoding="utf-8"
    )

    print("Wrote:", out_dir)
    print(pd.DataFrame([summary]).to_string(index=False))

    print("\nControls to materialize:")
    cols = [
        "official_id", "query_name", "candidate_id", "g_class",
        "mongodb_pattern", "document_strategy", "activation_reason"
    ]
    cols = [c for c in cols if c in missing_controls.columns]
    print(missing_controls[cols].to_string(index=False))

    if len(activated_missing):
        print("\nWARNING: activated candidates missing unexpectedly:")
        print(activated_missing[cols].to_string(index=False))

if __name__ == "__main__":
    main()
