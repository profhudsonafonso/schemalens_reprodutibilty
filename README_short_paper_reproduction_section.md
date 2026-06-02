## Reproducing short-paper Table 1 and Table 2

The short paper reports two compact result tables:

- **Table 1**: selected cross-dataset evidence for activated families, best observed configurations, DSR, Top-1 preservation, and regret.
- **Table 2**: diagnostic cases showing baseline failures and ablation signals.

These tables can be regenerated from the aggregate benchmark outputs already stored in this repository. This verification path does **not** rerun MongoDB; it only reads the existing aggregate, baseline, and ablation CSV files.

### Command

From the repository root:

```bash
python analysis/scripts/reproduce_short_paper_tables.py
```

On Windows PowerShell:

```powershell
py analysis\scripts\reproduce_short_paper_tables.py
```

### Inputs

The script expects:

```text
analysis/generated/aggregate_results_all_datasets.csv
analysis/generated/baseline_performance_by_case.csv
analysis/generated/ablation_performance_by_case.csv
```

If the normalized aggregate file is not available, first run:

```bash
python analysis/scripts/normalize_aggregate_outputs.py
python analysis/scripts/simulate_baselines.py
python analysis/scripts/run_ablation_analysis.py
```

### Outputs

The script writes:

```text
analysis/generated/short_paper_table1_reproduced.csv
analysis/generated/short_paper_table1_details.csv
analysis/generated/short_paper_table2_reproduced.csv
analysis/generated/short_paper_reproduction_report.txt
```

### Meaning of the outputs

- `short_paper_table1_reproduced.csv` contains the paper-facing summary for Table 1.
- `short_paper_table1_details.csv` contains the per-scale evidence behind the summary rows.
- `short_paper_table2_reproduced.csv` contains the compact diagnostic rows used for Table 2, including the IMDb QG4 and QG6 cases.
- `short_paper_reproduction_report.txt` records the input files used and the generated outputs.

The script uses hot-run p95 as the main comparison signal, following the paper text. DSR is computed against the fixed MongoDB template space \(G0,\ldots,G9\).
