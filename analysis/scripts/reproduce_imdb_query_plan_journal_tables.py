#!/usr/bin/env python3
"""
Reproduce IMDb journal-ready query-plan evidence tables from repository CSVs.

This script does not rerun MongoDB. It only combines existing benchmark,
baseline, ablation, analytical-matrix, and query-plan summary files already
stored in the repository.

Outputs:
  - imdb_journal_benchmark_ablation_values.csv
  - imdb_journal_plan_values.csv
  - imdb_journal_tables.tex
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

QUERY_ORDER = [
    "QG6_EpisodesOfSeries",
    "QG9_TopRatedSeriesByGenre",
    "QG4_AllPersonsOfTypeForWatchItem",
    "QG5_AllPersonsForEpisodesOfSeries",
    "QG8_AddPersonRoleToWatchItem",
    "QG3_RecommendationByGenreAndSubtype",
]

QUERY_SHORT = {
    "QG6_EpisodesOfSeries": "QG6",
    "QG9_TopRatedSeriesByGenre": "QG9",
    "QG4_AllPersonsOfTypeForWatchItem": "QG4",
    "QG5_AllPersonsForEpisodesOfSeries": "QG5",
    "QG8_AddPersonRoleToWatchItem": "QG8",
    "QG3_RecommendationByGenreAndSubtype": "QG3",
}

SCALE_ORDER = ["sf0.25", "sf0.5", "sf1"]
DETERMINISTIC_BASELINES = [
    "always_reference",
    "always_embed",
    "depth_only",
    "relationship_type_only",
]


def first_existing(root: Path, candidates: Iterable[str], required: bool = True) -> Optional[Path]:
    for rel in candidates:
        path = root / rel
        if path.exists():
            return path
    if required:
        msg = "None of the expected files exists:\n" + "\n".join(str(root / c) for c in candidates)
        raise FileNotFoundError(msg)
    return None


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def as_float(x, default=0.0) -> float:
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def fmt3(x) -> str:
    if pd.isna(x):
        return "--"
    return f"{float(x):.3f}"


def fmt_int(x) -> str:
    if pd.isna(x):
        return "--"
    return f"{int(round(float(x))):,}"


def fmt_bytes(x) -> str:
    if pd.isna(x):
        return "--"
    return f"{int(round(float(x))):,} B"


def safe_col(df: pd.DataFrame, names: list[str]) -> Optional[str]:
    for n in names:
        if n in df.columns:
            return n
    return None


def normalize_semantic(s: object) -> str:
    if pd.isna(s):
        return "--"
    txt = str(s).strip().lower()
    if "contain" in txt:
        return "Cont."
    if "associative" in txt:
        return "Assocv."
    if "association" in txt:
        return "Assoc."
    if "mixed" in txt:
        return "Mixed"
    return str(s).strip()


def load_matrix(root: Path) -> pd.DataFrame:
    path = first_existing(
        root,
        [
            "analysis/imdb/ablation_variables/query_analytical_metadata_imdb.csv",
            "analysis/generated/query_analytical_metadata_all_datasets.csv",
            "analysis/generated/query_plan/imdb/analytical_matrix_final_df.csv",
            "analytical_matrix_final_df.csv",
        ],
        required=False,
    )
    if path is None:
        return pd.DataFrame()
    try:
        df = read_csv(path)
    except Exception:
        return pd.DataFrame()
    if "dataset" in df.columns:
        df = df[df["dataset"].astype(str).str.lower().eq("imdb")].copy()
    return df


def matrix_lookup(matrix: pd.DataFrame, query: str) -> dict:
    # Conservative defaults used when metadata file is unavailable or inconsistent.
    defaults = {
        "QG6_EpisodesOfSeries": ("Series", "Cont.", "1/1/0"),
        "QG9_TopRatedSeriesByGenre": ("WatchItem", "Assoc.", "2/1/0"),
        "QG4_AllPersonsOfTypeForWatchItem": ("WatchItem", "Assocv.", "2/2/0"),
        "QG5_AllPersonsForEpisodesOfSeries": ("WatchItem", "Mixed", "4/2/0"),
        "QG8_AddPersonRoleToWatchItem": ("WatchItem", "Assocv.", "2/2/0"),
        "QG3_RecommendationByGenreAndSubtype": ("WatchItem", "Assoc.", "4/1/0"),
    }
    if matrix.empty or "query_name" not in matrix.columns:
        root, sem, rcdre = defaults[query]
        return {"Root": root, "Sem.": sem, "Rc/D/Re": rcdre}

    m = matrix[matrix["query_name"].astype(str).eq(query)].copy()
    if m.empty:
        root, sem, rcdre = defaults[query]
        return {"Root": root, "Sem.": sem, "Rc/D/Re": rcdre}

    row = m.iloc[0]
    root_col = safe_col(m, ["selected_root", "root", "selected_document_root"])
    sem_col = safe_col(m, ["dominant_semantic_group", "dominant_semantic_type", "dominant_semantic_detail", "semantic_type"])
    rc_col = safe_col(m, ["Rc", "rc"])
    d_col = safe_col(m, ["D_value", "D", "selected_document_depth"])
    re_col = safe_col(m, ["selected_Re", "Re", "re"])

    root = row[root_col] if root_col else defaults[query][0]
    sem = normalize_semantic(row[sem_col]) if sem_col else defaults[query][1]
    rc = int(round(as_float(row[rc_col], 0))) if rc_col else defaults[query][2].split("/")[0]
    d = int(round(as_float(row[d_col], 0))) if d_col else defaults[query][2].split("/")[1]
    re = int(round(as_float(row[re_col], 0))) if re_col else defaults[query][2].split("/")[2]
    return {"Root": str(root), "Sem.": sem, "Rc/D/Re": f"{rc}/{d}/{re}"}


def load_query_plan(root: Path) -> pd.DataFrame:
    paths = [
        "analysis/generated/query_plan/imdb/qg9_validation/query_plan_summary_qg9_all_sfs.csv",
        "analysis/generated/query_plan/imdb/group_A_light_no_roles/query_plan_summary_results_group_A.csv",
        "analysis/generated/query_plan/imdb/group_B_episodes/query_plan_summary_results_group_B.csv",
        "analysis/generated/query_plan/imdb/group_C_roles_sf025/query_plan_summary_results_group_C_roles_sf025.csv",
        "analysis/generated/query_plan/imdb/group_C_roles_sf050/query_plan_summary_results_group_C_roles_sf050.csv",
        "analysis/generated/query_plan/imdb/group_C_roles_sf1_assoc_only/query_plan_summary_results_group_C_roles_sf1_assoc_only.csv",
        "analysis/generated/query_plan/imdb/group_C_qg5_sf1_assoc_only_with_episodes/query_plan_summary_results_group_C_qg5_sf1_assoc_only_with_episodes.csv",
        "analysis/generated/query_plan/imdb/group_D_insert_qg8/query_plan_summary_results_group_D.csv",
    ]
    frames = []
    for rel in paths:
        p = root / rel
        if p.exists():
            frames.append(pd.read_csv(p))
    if not frames:
        raise FileNotFoundError("No IMDb query-plan summary CSV files were found under analysis/generated/query_plan/imdb/.")
    df = pd.concat(frames, ignore_index=True)
    # Prefer group_A for QG9 when both qg9_validation and group_A contain it, because group_A has all configs/SFs.
    df = df.drop_duplicates(subset=["scale_label", "query_name", "config_name", "run_phase"], keep="last")
    return df


def best_by_scale(bench: pd.DataFrame, query: str) -> tuple[str, str]:
    hot = bench[(bench["query_name"] == query) & (bench["run_phase"] == "hot")].copy()
    best_g, best_p95 = [], []
    for scale in SCALE_ORDER:
        s = hot[hot["scale_label"] == scale].copy()
        if s.empty:
            best_g.append("--")
            best_p95.append("--")
            continue
        row = s.loc[s["p95_latency_ms"].astype(float).idxmin()]
        best_g.append(str(row["activated_class"]))
        best_p95.append(fmt3(row["p95_latency_ms"]))
    return "/".join(best_g), "/".join(best_p95)


def baseline_summary(base: pd.DataFrame, query: str) -> tuple[str, str, str]:
    hot = base[(base["dataset"].astype(str).str.lower() == "imdb") & (base["query_name"] == query) & (base["run_phase"] == "hot")].copy()
    sl = hot[hot["baseline"] == "schema_lens"].copy()
    t1 = f"{int(sl['top1_preserved'].fillna(0).sum())}/{len(sl)}" if len(sl) else "--"
    sl_max = fmt3(sl["relative_regret"].max()) if len(sl) else "--"
    det = hot[hot["baseline"].isin(DETERMINISTIC_BASELINES)].copy()
    misses = int((det["top1_preserved"].fillna(0) < 1).sum()) if len(det) else 0
    maxr = fmt3(det["relative_regret"].max()) if len(det) else "--"
    return t1, sl_max, f"{misses}/{len(det)}; {maxr}"


def ablation_summary(ab: pd.DataFrame, query: str) -> str:
    hot = ab[(ab["dataset"].astype(str).str.lower() == "imdb") & (ab["query_name"] == query) & (ab["run_phase"] == "hot")].copy()
    variants = hot[hot["ablation_variant"] != "full_schema_lens"].copy()
    misses = int((variants["top1_preserved"].fillna(0) < 1).sum()) if len(variants) else 0
    maxr = fmt3(variants["relative_regret"].max()) if len(variants) else "--"
    return f"{misses}/{len(variants)}; {maxr}"


def make_benchmark_table(root: Path) -> pd.DataFrame:
    bench = read_csv(first_existing(root, ["analysis/imdb/benchmark_aggregate_results_imdb_all_sfs.csv"]))
    base = read_csv(first_existing(root, ["analysis/generated/baseline_performance_by_case.csv"]))
    ab = read_csv(first_existing(root, ["analysis/generated/ablation_performance_by_case.csv"]))
    matrix = load_matrix(root)
    rows = []
    for q in QUERY_ORDER:
        meta = matrix_lookup(matrix, q)
        best_g, best_p95 = best_by_scale(bench, q)
        sl_t1, sl_maxr, base_sig = baseline_summary(base, q)
        abl_sig = ablation_summary(ab, q)
        rows.append({
            "Query": QUERY_SHORT[q],
            **meta,
            "Best G": best_g,
            "Best p95": best_p95,
            "SL T1": sl_t1,
            "SL maxR": sl_maxr,
            "Base miss/maxR": base_sig,
            "Abl. miss/maxR": abl_sig,
        })
    return pd.DataFrame(rows)


def row_for(qp: pd.DataFrame, query: str, g: str, scale: str = "sf1") -> pd.Series:
    s = qp[(qp["query_name"] == query) & (qp["scale_label"] == scale) & (qp["activated_class"] == g)].copy()
    if s.empty:
        return pd.Series(dtype=object)
    return s.iloc[0]


def docs_keys(row: pd.Series) -> str:
    return f"{fmt_int(row.get('sum_total_docs_examined'))}/{fmt_int(row.get('sum_total_keys_examined'))}"


def size(row: pd.Series) -> str:
    return fmt_bytes(row.get("max_collection_avg_obj_size_bytes"))


def make_plan_table(root: Path) -> pd.DataFrame:
    qp = load_query_plan(root)
    rows = []

    # QG6
    q = "QG6_EpisodesOfSeries"
    g7, g8, g9 = [row_for(qp, q, g) for g in ["G7", "G8", "G9"]]
    rows.append({
        "Query": "QG6", "Compared configs": "G7 vs. G8/G9",
        "Main stages": "COUNT_SCAN vs. IXSCAN+FETCH+PROJ.",
        "Docs/Keys": f"G7 {docs_keys(g7)}; G8/G9 {docs_keys(g8)}",
        "Physical signal": f"{size(g7)} vs. {size(g8)}/{size(g9)}; external episodes vs. embedded arrays.",
    })

    # QG9
    q = "QG9_TopRatedSeriesByGenre"
    g7, g2, g8 = [row_for(qp, q, g) for g in ["G7", "G2", "G8"]]
    rows.append({
        "Query": "QG9", "Compared configs": "G7 vs. G2/G8",
        "Main stages": "IXSCAN+SORT vs. AND_SORTED/embedded payload",
        "Docs/Keys": f"G7 {docs_keys(g7)}; G2 {docs_keys(g2)}; G8 {docs_keys(g8)}",
        "Physical signal": f"{size(g7)} vs. {size(g2)}/{size(g8)}; series root vs. generic watchitems.",
    })

    # QG4
    q = "QG4_AllPersonsOfTypeForWatchItem"
    g4, g5, g6 = [row_for(qp, q, g) for g in ["G4", "G5", "G6"]]
    rows.append({
        "Query": "QG4", "Compared configs": "G4/G5/G6",
        "Main stages": "IXSCAN+FETCH+PROJ.",
        "Docs/Keys": f"{docs_keys(g4)} each" if docs_keys(g4) == docs_keys(g5) == docs_keys(g6) else f"{docs_keys(g4)}/{docs_keys(g5)}/{docs_keys(g6)}",
        "Physical signal": f"{size(g4)}/{size(g5)}/{size(g6)}; associative materialization in watchitems.",
    })

    # QG5
    q = "QG5_AllPersonsForEpisodesOfSeries"
    g4, g5, g6 = [row_for(qp, q, g) for g in ["G4", "G5", "G6"]]
    rows.append({
        "Query": "QG5", "Compared configs": "G4/G5/G6",
        "Main stages": "IXSCAN+FETCH+PROJ.",
        "Docs/Keys": docs_keys(g4),
        "Physical signal": "Requires episodes; then reaches Role/Person data.",
    })

    # QG8
    q = "QG8_AddPersonRoleToWatchItem"
    g4, g5, g6 = [row_for(qp, q, g) for g in ["G4", "G5", "G6"]]
    rows.append({
        "Query": "QG8", "Compared configs": "G4/G5/G6",
        "Main stages": "UPDATE+FETCH+IXSCAN",
        "Docs/Keys": f"{docs_keys(g4)} each" if docs_keys(g4) == docs_keys(g5) == docs_keys(g6) else f"{docs_keys(g4)}/{docs_keys(g5)}/{docs_keys(g6)}",
        "Physical signal": "Write maintenance over watchitem_id_1.",
    })

    # QG3
    q = "QG3_RecommendationByGenreAndSubtype"
    g8 = row_for(qp, q, "G8")
    rows.append({
        "Query": "QG3", "Compared configs": "G8 vs. G0/G2",
        "Main stages": "IXSCAN+SORT",
        "Docs/Keys": docs_keys(g8),
        "Physical signal": "Current run preserves G8; baselines/ablations may select weaker families.",
    })
    return pd.DataFrame(rows)


def escape_latex(s: object) -> str:
    if pd.isna(s):
        return "--"
    txt = str(s)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for a, b in replacements.items():
        txt = txt.replace(a, b)
    return txt


def df_to_latex_table(df: pd.DataFrame, caption: str, label: str, colspec: str) -> str:
    lines = []
    lines.append(r"\begin{table*}[t]")
    lines.append(r"\centering")
    lines.append(rf"\caption{{{caption}}}")
    lines.append(rf"\label{{{label}}}")
    lines.append(r"\scriptsize")
    lines.append(r"\setlength{\tabcolsep}{2.2pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.08}")
    lines.append(rf"\begin{{tabularx}}{{\textwidth}}{{{colspec}}}")
    lines.append(r"\toprule")
    lines.append(" & ".join(escape_latex(c) for c in df.columns) + r" \\")
    lines.append(r"\midrule")
    for _, row in df.iterrows():
        lines.append(" & ".join(escape_latex(row[c]) for c in df.columns) + r" \\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabularx}")
    lines.append(r"\end{table*}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".", help="Repository root. Default: current directory.")
    parser.add_argument(
        "--out-dir",
        default="analysis/generated/query_plan/imdb",
        help="Output directory relative to repo root.",
    )
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    out_dir = (root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    benchmark_df = make_benchmark_table(root)
    plan_df = make_plan_table(root)

    benchmark_csv = out_dir / "imdb_journal_benchmark_ablation_values.csv"
    plan_csv = out_dir / "imdb_journal_plan_values.csv"
    tex_file = out_dir / "imdb_journal_query_plan_tables.tex"

    benchmark_df.to_csv(benchmark_csv, index=False)
    plan_df.to_csv(plan_csv, index=False)

    tex = []
    tex.append("% Auto-generated by analysis/scripts/reproduce_imdb_query_plan_journal_tables.py")
    tex.append(df_to_latex_table(
        benchmark_df,
        "IMDb representative cases: analytical variables, benchmark preservation, deterministic baselines, and ablation results under hot-run p95. Baseline misses are counted over four deterministic baselines and three scales; ablation misses are counted over six ablation variants and three scales.",
        "tab:imdb_benchmark_ablation_values",
        r"l l l c l l c c c c",
    ))
    tex.append("\n")
    tex.append(df_to_latex_table(
        plan_df,
        "Representative MongoDB query-plan evidence for the IMDb cases. Values are reported for SF1. Docs/Keys denotes documents examined and keys examined.",
        "tab:imdb_plan_values",
        r"l p{2.0cm} p{3.0cm} p{2.2cm} X",
    ))
    tex_file.write_text("\n".join(tex), encoding="utf-8")

    print("Generated:")
    print(f"  {benchmark_csv.relative_to(root)}")
    print(f"  {plan_csv.relative_to(root)}")
    print(f"  {tex_file.relative_to(root)}")


if __name__ == "__main__":
    main()
