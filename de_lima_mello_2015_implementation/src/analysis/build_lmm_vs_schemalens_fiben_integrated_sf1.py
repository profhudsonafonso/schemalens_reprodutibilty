from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd


BASE = Path("de_lima_mello_2015_implementation")

P95_CSV = BASE / "results/fiben/reports/lmm_vs_schemalens_fiben_benchmark_p95_comparison_sf1.csv"
LMM_QP_CSV = BASE / "results/fiben/query_plan/sf1/lmm_fiben_sf1_source_full/lmm_fiben_query_plan_summary_results.csv"
SCHEMA_COMPACT_CSV = BASE / "generated/fiben/schemalens_query_plan_full/fiben_query_plan_compact_candidates.csv"
SCHEMA_COMPONENTS_CSV = BASE / "generated/fiben/schemalens_query_plan_full/fiben_query_plan_components_all.csv"

OUT_DIR = BASE / "results/fiben/reports"
OUT_CSV = OUT_DIR / "lmm_vs_schemalens_fiben_integrated_p95_query_plan_sf1.csv"
OUT_SUMMARY = OUT_DIR / "lmm_vs_schemalens_fiben_integrated_summary_sf1.csv"
OUT_MD = OUT_DIR / "lmm_vs_schemalens_fiben_integrated_report_sf1.md"


def normalize_query_id(value: Any) -> Optional[str]:
    if value is None or pd.isna(value):
        return None
    text = str(value)
    m = re.search(r"\bQ(\d+)\b", text, flags=re.IGNORECASE)
    if m:
        return f"Q{int(m.group(1))}"
    m = re.search(r"Q(\d+)_", text, flags=re.IGNORECASE)
    if m:
        return f"Q{int(m.group(1))}"
    return text


def get_col(df: pd.DataFrame, names: list[str]) -> Optional[str]:
    for name in names:
        if name in df.columns:
            return name
    return None


def as_bool(value: Any) -> bool:
    if value is None or pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def safe_num(value: Any) -> Optional[float]:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def ratio(a: Any, b: Any) -> Optional[float]:
    a = safe_num(a)
    b = safe_num(b)
    if a is None or b is None or b == 0:
        return None
    return a / b


def pick_lmm_query_plan() -> pd.DataFrame:
    df = pd.read_csv(LMM_QP_CSV)
    df["query_id"] = df[get_col(df, ["query_id", "query_name"])].map(normalize_query_id)

    docs_col = get_col(df, [
        "total_docs_examined_accumulated",
        "total_docs_examined",
        "docs_examined",
    ])

    keys_col = get_col(df, [
        "total_keys_examined_accumulated",
        "total_keys_examined",
        "keys_examined",
    ])

    if docs_col is None:
        raise RuntimeError("Could not detect LMM docs examined column. Columns: " + ", ".join(df.columns))
    if keys_col is None:
        raise RuntimeError("Could not detect LMM keys examined column. Columns: " + ", ".join(df.columns))

    out = pd.DataFrame()
    out["query_id"] = df["query_id"]
    out["lmm_docs_examined"] = pd.to_numeric(df[docs_col], errors="coerce") if docs_col else pd.NA
    out["lmm_keys_examined"] = pd.to_numeric(df[keys_col], errors="coerce") if keys_col else pd.NA

    for flag in ["IXSCAN", "COLLSCAN", "LOOKUP", "GROUP", "UNWIND"]:
        c = get_col(df, [f"has_{flag}", f"has_{flag.lower()}"])
        if c:
            out[f"lmm_has_{flag.lower()}"] = df[c].map(as_bool)
        else:
            out[f"lmm_has_{flag.lower()}"] = False

    return out.drop_duplicates("query_id")


def pick_schema_query_plan_for_p95_winner(p95: pd.DataFrame) -> pd.DataFrame:
    compact = pd.read_csv(SCHEMA_COMPACT_CSV)
    components = pd.read_csv(SCHEMA_COMPONENTS_CSV)

    compact = compact.copy()
    components = components.copy()

    if "scale_label" in compact.columns:
        compact = compact[compact["scale_label"].astype(str) == "sf1"].copy()
    if "scale_label" in components.columns:
        components = components[components["scale_label"].astype(str) == "sf1"].copy()

    compact["query_id"] = compact[get_col(compact, ["query_name", "query_id"])].map(normalize_query_id)
    components["query_id"] = components[get_col(components, ["query_name", "query_id"])].map(normalize_query_id)

    rows = []

    for _, p in p95.iterrows():
        if str(p.get("run_phase")) != "hot":
            continue

        qid = p["query_id"]
        candidate_id = str(p.get("schemalens_candidate_id", ""))

        crows = compact[
            (compact["query_id"] == qid)
            & (compact["candidate_id"].astype(str) == candidate_id)
        ].copy()

        comp_rows = components[
            (components["query_id"] == qid)
            & (components["candidate_id"].astype(str) == candidate_id)
        ].copy()

        if crows.empty:
            rows.append({
                "query_id": qid,
                "schemalens_docs_examined": pd.NA,
                "schemalens_keys_examined": pd.NA,
                "schemalens_has_ixscan": pd.NA,
                "schemalens_has_collscan": pd.NA,
                "schemalens_has_lookup": pd.NA,
                "schemalens_has_group": pd.NA,
                "schemalens_has_unwind": pd.NA,
                "schemalens_n_components": pd.NA,
                "schemalens_collections_touched": pd.NA,
            })
            continue

        c = crows.iloc[0]

        stage_text = ""
        if not comp_rows.empty:
            stage_cols = [x for x in ["all_stages", "all_stages_json", "pipeline_json"] if x in comp_rows.columns]
            for sc in stage_cols:
                values = []
                for x in comp_rows[sc].tolist():
                    if x is None:
                        continue
                    try:
                        if pd.isna(x):
                            continue
                    except Exception:
                        pass
                    values.append(str(x))
                stage_text += " ".join(values) + " "

        has_lookup = False
        if "has_LOOKUP" in comp_rows.columns and not comp_rows.empty:
            has_lookup = bool(comp_rows["has_LOOKUP"].map(as_bool).any())

        has_unwind = "UNWIND" in stage_text.upper() or "$UNWIND" in stage_text.upper()

        rows.append({
            "query_id": qid,
            "schemalens_docs_examined": safe_num(c.get("sum_total_docs_examined")),
            "schemalens_keys_examined": safe_num(c.get("sum_total_keys_examined")),
            "schemalens_has_ixscan": as_bool(c.get("has_IXSCAN")),
            "schemalens_has_collscan": as_bool(c.get("has_COLLSCAN")),
            "schemalens_has_lookup": has_lookup,
            "schemalens_has_group": as_bool(c.get("has_GROUP")),
            "schemalens_has_unwind": has_unwind,
            "schemalens_n_components": safe_num(c.get("n_components")),
            "schemalens_collections_touched": c.get("collections_touched"),
        })

    return pd.DataFrame(rows)


def interpretation(row: pd.Series) -> str:
    q = row["query_id"]
    winner = row["winner_by_p95"]
    ratio_p95 = row.get("p95_ratio_lmm_over_schemalens")
    docs_ratio = row.get("docs_ratio_lmm_over_schemalens")

    if q == "Q6":
        return (
            "Q6 is the dominant case: SchemaLens strongly reduces p95 latency "
            f"(LMM/SchemaLens ratio {ratio_p95:.1f}x) and avoids the transaction-heavy cost pattern."
        )

    if winner == "LimaMello2015":
        return (
            "Lima & Mello is faster by p95; this supports that its faithful workload-driven "
            "materialization is effective for this path-oriented query."
        )

    if winner == "SchemaLens":
        return (
            "SchemaLens is faster by p95; this indicates that the activated candidate selected by "
            "benchmarking better matches the physical execution cost."
        )

    return "Tie or incomplete p95 evidence."


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    p95 = pd.read_csv(P95_CSV)
    p95 = p95[p95["run_phase"].astype(str) == "hot"].copy()
    p95["query_id"] = p95["query_id"].map(normalize_query_id)

    lmm_qp = pick_lmm_query_plan()
    schema_qp = pick_schema_query_plan_for_p95_winner(p95)

    out = (
        p95
        .merge(lmm_qp, on="query_id", how="left")
        .merge(schema_qp, on="query_id", how="left")
    )

    out["docs_ratio_lmm_over_schemalens"] = out.apply(
        lambda r: ratio(r.get("lmm_docs_examined"), r.get("schemalens_docs_examined")),
        axis=1,
    )
    out["keys_ratio_lmm_over_schemalens"] = out.apply(
        lambda r: ratio(r.get("lmm_keys_examined"), r.get("schemalens_keys_examined")),
        axis=1,
    )
    out["integrated_interpretation"] = out.apply(interpretation, axis=1)

    cols = [
        "query_id",
        "query_name",
        "winner_by_p95",
        "lmm_p95_ms",
        "schemalens_p95_ms",
        "p95_ratio_lmm_over_schemalens",
        "schemalens_candidate_id",
        "schemalens_g_class",
        "schemalens_design_pattern",
        "lmm_docs_examined",
        "schemalens_docs_examined",
        "docs_ratio_lmm_over_schemalens",
        "lmm_keys_examined",
        "schemalens_keys_examined",
        "lmm_has_ixscan",
        "schemalens_has_ixscan",
        "lmm_has_collscan",
        "schemalens_has_collscan",
        "lmm_has_lookup",
        "schemalens_has_lookup",
        "lmm_has_unwind",
        "schemalens_has_unwind",
        "integrated_interpretation",
    ]

    for c in cols:
        if c not in out.columns:
            out[c] = pd.NA

    out = out[cols].sort_values("query_id")
    out.to_csv(OUT_CSV, index=False)

    summary = pd.DataFrame([{
        "scale": "sf1",
        "n_queries": len(out),
        "lmm_p95_wins": int((out["winner_by_p95"] == "LimaMello2015").sum()),
        "schemalens_p95_wins": int((out["winner_by_p95"] == "SchemaLens").sum()),
        "sum_lmm_p95_ms": out["lmm_p95_ms"].sum(),
        "sum_schemalens_p95_ms": out["schemalens_p95_ms"].sum(),
        "mean_lmm_p95_ms": out["lmm_p95_ms"].mean(),
        "mean_schemalens_p95_ms": out["schemalens_p95_ms"].mean(),
        "sum_lmm_docs_examined": out["lmm_docs_examined"].sum(),
        "sum_schemalens_docs_examined": out["schemalens_docs_examined"].sum(),
    }])
    summary["sum_p95_ratio_lmm_over_schemalens"] = (
        summary["sum_lmm_p95_ms"] / summary["sum_schemalens_p95_ms"]
    )
    summary.to_csv(OUT_SUMMARY, index=False)

    lines = []
    lines.append("# Integrated p95 and query-plan comparison: Lima & Mello 2015 vs SchemaLens")
    lines.append("")
    lines.append("Scale: `sf1`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(summary.to_markdown(index=False))
    lines.append("")
    lines.append("## Query-level integrated table")
    lines.append("")
    lines.append(out[[
        "query_id",
        "winner_by_p95",
        "lmm_p95_ms",
        "schemalens_p95_ms",
        "p95_ratio_lmm_over_schemalens",
        "lmm_docs_examined",
        "schemalens_docs_examined",
        "docs_ratio_lmm_over_schemalens",
        "schemalens_g_class",
        "schemalens_design_pattern",
    ]].to_markdown(index=False))
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    for _, r in out.iterrows():
        lines.append(f"- **{r['query_id']}**: {r['integrated_interpretation']}")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print("Wrote:")
    print(" -", OUT_CSV)
    print(" -", OUT_SUMMARY)
    print(" -", OUT_MD)
    print()
    print("=== integrated summary ===")
    print(summary.to_string(index=False))
    print()
    print("=== integrated table ===")
    print(out[[
        "query_id",
        "winner_by_p95",
        "lmm_p95_ms",
        "schemalens_p95_ms",
        "p95_ratio_lmm_over_schemalens",
        "lmm_docs_examined",
        "schemalens_docs_examined",
        "docs_ratio_lmm_over_schemalens",
        "schemalens_g_class",
        "schemalens_design_pattern",
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
