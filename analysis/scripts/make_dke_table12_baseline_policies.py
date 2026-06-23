#!/usr/bin/env python3
"""
Generate DKE Table 12 baseline-policy examples from benchmark artifacts.

This script does not rerun benchmarks. It reads the baseline comparison artifact
and extracts real candidate sets used by each baseline for representative cases
that are discussed in the paper.

Input:
  analysis/generated/baseline_performance_by_case.csv

Outputs:
  analysis/generated/dke_table12_baseline_policy_examples.csv
  analysis/generated/dke_table12_baseline_policy_sets_summary.csv
  analysis/generated/dke_table12_baseline_policy_examples.tex
"""

from pathlib import Path
import pandas as pd

INPUT = Path("analysis/generated/baseline_performance_by_case.csv")

OUT_EXAMPLES = Path("analysis/generated/dke_table12_baseline_policy_examples.csv")
OUT_SUMMARY = Path("analysis/generated/dke_table12_baseline_policy_sets_summary.csv")
OUT_TEX = Path("analysis/generated/dke_table12_baseline_policy_examples.tex")

# These are representative cases already discussed in the paper.
# The candidate sets themselves are NOT hard-coded; they are extracted from INPUT.
REPRESENTATIVE_CASES = [
    {
        "label": "IMDb QG9",
        "dataset": "imdb",
        "query_contains": "QG9_TopRatedSeriesByGenre",
    },
    {
        "label": "FIBEN Q2",
        "dataset": "fiben",
        "query_contains": "Q2_CompanyWithIndustryCountryAndListedSecurities",
    },
    {
        "label": "LDBC IC7",
        "dataset": "ldbc_snb",
        "query_contains": "IC7_RecentLikers",
    },
]

BASELINE_ORDER = [
    "schema_lens",
    "always_reference",
    "always_embed",
    "depth_only",
    "relationship_type_only",
    "random_k",
]

BASELINE_LABELS = {
    "schema_lens": "SchemaLens",
    "always_reference": "Always-reference",
    "always_embed": "Always-embed",
    "depth_only": "Depth-only",
    "relationship_type_only": "Relationship-type-only",
    "random_k": "Random-$k$",
}

BASELINE_RULES = {
    "schema_lens": "Use the EER/workload analytical matrix to activate a query-specific family.",
    "always_reference": "Preserve candidates that keep entities external or reference-oriented.",
    "always_embed": "Preserve candidates that materialise related data under, or close to, the selected root.",
    "depth_only": "Select candidates using structural depth without relationship semantics, sharedness, or update-volatility evidence.",
    "relationship_type_only": "Use the dominant relationship type without the full analytical matrix.",
    "random_k": "Sample the same number of candidates as SchemaLens for the same query-scale case.",
}

BASELINE_PURPOSES = {
    "schema_lens": "Main method under evaluation.",
    "always_reference": "Tests whether reference-preserving designs alone are sufficient.",
    "always_embed": "Tests whether locality-oriented embedding is sufficient.",
    "depth_only": "Tests whether structural coverage alone explains the winners.",
    "relationship_type_only": "Tests whether semantic family alone is enough.",
    "random_k": "Non-explanatory sanity check for reduced-space size.",
}


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "_": r"\_",
        "%": r"\%",
        "&": r"\&",
        "#": r"\#",
    }
    out = str(text)
    for old, new in replacements.items():
        out = out.replace(old, new)
    return out


def format_set_for_paper(value: str) -> str:
    value = str(value)
    if value.startswith("random_sample_k="):
        k = value.split("=", 1)[1]
        return f"random sample with $k={k}$"

    parts = [p.strip() for p in value.split("|") if p.strip()]
    formatted = []
    for p in parts:
        if p.upper() == "CONTROL":
            formatted.append("Control")
        elif p.upper().startswith("G"):
            formatted.append(p.upper())
        else:
            formatted.append(latex_escape(p))
    return "$" + ",".join(formatted) + "$"


def extract_case_set(hot: pd.DataFrame, baseline: str, case: dict) -> str:
    sub = hot[
        (hot["baseline"] == baseline)
        & (hot["dataset"] == case["dataset"])
        & (hot["query_name"].astype(str).str.contains(case["query_contains"], case=False, regex=False))
    ].copy()

    if sub.empty:
        return "not available"

    unique_sets = sorted(sub["selected_g_classes"].astype(str).unique())

    if len(unique_sets) == 1:
        return format_set_for_paper(unique_sets[0])

    # If a baseline changes by scale, keep the scale-specific sets.
    chunks = []
    for scale, group in sub.groupby("scale_label", sort=True):
        scale_sets = sorted(group["selected_g_classes"].astype(str).unique())
        joined = "; ".join(format_set_for_paper(s) for s in scale_sets)
        chunks.append(f"{latex_escape(scale)}: {joined}")
    return "; ".join(chunks)


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input artifact: {INPUT}")

    df = pd.read_csv(INPUT)

    required = [
        "dataset",
        "scale_label",
        "query_name",
        "run_phase",
        "baseline",
        "availability_status",
        "selected_g_classes",
        "selected_config_count",
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {INPUT}: {missing}")

    df["dataset"] = df["dataset"].astype(str).str.lower()
    df["run_phase"] = df["run_phase"].astype(str).str.lower()
    df["baseline"] = df["baseline"].astype(str)
    df["availability_status"] = df["availability_status"].astype(str).str.lower()

    hot = df[
        (df["run_phase"] == "hot")
        & (df["availability_status"] == "available")
    ].copy()

    # Full audit summary: all real selected candidate sets observed by baseline/dataset.
    summary = (
        hot.groupby(["baseline", "dataset", "selected_g_classes"])
        .size()
        .reset_index(name="n_cases")
        .sort_values(["baseline", "dataset", "n_cases", "selected_g_classes"], ascending=[True, True, False, True])
    )
    summary.to_csv(OUT_SUMMARY, index=False)

    rows = []
    for baseline in BASELINE_ORDER:
        examples = []
        for case in REPRESENTATIVE_CASES:
            case_set = extract_case_set(hot, baseline, case)
            examples.append(f"{case['label']}: {case_set}")

        rows.append(
            {
                "baseline": baseline,
                "baseline_label": BASELINE_LABELS[baseline],
                "real_artifact_examples": "; ".join(examples),
                "rule": BASELINE_RULES[baseline],
                "purpose": BASELINE_PURPOSES[baseline],
            }
        )

    examples_df = pd.DataFrame(rows)
    examples_df.to_csv(OUT_EXAMPLES, index=False)

    tex_rows = []
    for _, r in examples_df.iterrows():
        tex_rows.append(
            f"{r['baseline_label']} & "
            f"{r['real_artifact_examples']} & "
            f"{latex_escape(r['rule'])} & "
            f"{latex_escape(r['purpose'])} \\\\"
        )

    latex = r"""\begin{table*}[t]
\centering
\caption{Baseline policies used in the comparison. Candidate sets are real sets observed in the benchmark artifact.}
\label{tab:baseline-policies}
\small
\setlength{\tabcolsep}{3pt}
\begin{tabular}{p{0.15\textwidth}p{0.38\textwidth}p{0.25\textwidth}p{0.16\textwidth}}
\toprule
Baseline & Real artifact examples & Rule & Purpose \\
\midrule
""" + "\n\\midrule\n".join(tex_rows) + r"""
\bottomrule
\end{tabular}
\end{table*}
"""

    OUT_TEX.write_text(latex, encoding="utf-8")

    print("Generated:")
    print(f" - {OUT_EXAMPLES}")
    print(f" - {OUT_SUMMARY}")
    print(f" - {OUT_TEX}")
    print()
    print(examples_df.to_string(index=False))


if __name__ == "__main__":
    main()
