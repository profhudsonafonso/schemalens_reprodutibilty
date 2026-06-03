# Reproducing Short-Paper Tables

This page documents how to reproduce the paper-facing summaries used in the short paper.

The script verifies Table 1 and the diagnostic cases used in Table 2 from existing aggregate, baseline, and ablation outputs. It does not rerun MongoDB.

## Inputs

The script uses the following files:

    analysis/generated/aggregate_results_all_datasets.csv
    analysis/generated/baseline_performance_by_case.csv
    analysis/generated/ablation_performance_by_case.csv

## Command

From the repository root, run:

    python analysis/scripts/reproduce_short_paper_tables.py

On Windows, run:

    py analysis\scripts\reproduce_short_paper_tables.py

## Outputs

The script generates:

    analysis/generated/short_paper_table1_reproduced.csv
    analysis/generated/short_paper_table1_details.csv
    analysis/generated/short_paper_table2_reproduced.csv
    analysis/generated/short_paper_reproduction_report.txt

## Output meaning

- short_paper_table1_reproduced.csv contains the paper-facing summary for Table 1.
- short_paper_table1_details.csv contains the per-scale evidence behind Table 1.
- short_paper_table2_reproduced.csv contains the compact diagnostic rows used for Table 2, including IMDb QG4 and QG6.
- short_paper_reproduction_report.txt records input files, generated files, and reproduced cases.

## Notes

This is a lightweight verification path for reviewers. Full benchmark reproduction requires materializing MongoDB candidate configurations and rerunning cold/hot benchmark executions.
