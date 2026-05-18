# SchemaLens Analysis Outputs

This folder contains the analysis files used to verify and extend the experimental results of the SchemaLens paper.

The goal of this folder is to support lightweight reproducibility from aggregate benchmark outputs, without requiring reviewers to rerun the full MongoDB benchmark.

The analyses in this folder support:

- normalized aggregate benchmark outputs;
- baseline comparisons;
- ablation studies;
- near-best and regret analysis;
- failure and near-failure analysis;
- paper-ready tables.

These analyses use the aggregate benchmark result files already included in the repository.

---

## Folder structure

```text
analysis/
├── README.md
├── imdb/
│   ├── benchmark_aggregate_results_imdb_all_sfs.csv
│   ├── benchmark_aggregate_results_sf025.csv
│   ├── benchmark_aggregate_results_sf050.csv
│   └── benchmark_aggregate_results_sf1.csv
├── fiben/
│   ├── benchmark_aggregate_results_fiben_sf1.csv
│   ├── benchmark_aggregate_results_fiben_sf10.csv
│   ├── benchmark_aggregate_results_fiben_sf30.csv
│   └── benchmark_execution_plan.csv
├── ldbc_snb/
│   ├── benchmark_aggregate_results_ldbc_snb_sf0_1.csv
│   ├── benchmark_aggregate_results_ldbc_snb_sf1.csv
│   └── benchmark_aggregate_results_ldbc_snb_sf3.csv
├── scripts/
     ├── normalize_aggregate_outputs.py
     ├── check_baseline_coverage.py
     ├── simulate_baselines.py
     └── analyze_baseline_diagnostics.py
     └── generated/
     ├── aggregate_results_all_datasets.csv
generated/
     ├── aggregate_results_all_datasets.csv
     ├── normalization_report.txt
     ├── available_g_classes_by_query.csv
     ├── baseline_coverage_by_case.csv
     ├── baseline_coverage_summary.csv
     ├── missing_baseline_candidates.csv
     ├── query_metadata_template.csv
     ├── baseline_coverage_report.txt
     ├── baseline_performance_by_case.csv
     ├── baseline_performance_summary.csv
     ├── baseline_performance_by_dataset.csv
     ├── baseline_failure_cases.csv
     ├── baseline_performance_report.txt
     ├── baseline_performance_summary_hot.csv
     ├── baseline_performance_by_dataset_hot.csv
     ├── schema_lens_vs_random_k_by_case.csv
     ├── schema_lens_vs_random_k_summary.csv
     └── schema_lens_vs_random_k_report.txt
```
## Step 1 — Normalize aggregate benchmark outputs

### Purpose

The original aggregate benchmark files contain similar information, but their column names are not identical across datasets.

For IMDb, the aggregate file uses columns such as:

```text
config_name
activated_class
benchmark_family
query_group
```

For FIBEN and LDBC SNB, the aggregate files use columns such as:

```text
candidate_id
g_class
design_pattern
final_benchmark_group
```

The normalization script converts these dataset-specific formats into one common schema.

This makes it possible to run the same downstream analyses over IMDb, FIBEN, and LDBC SNB.

---

### Input files

#### IMDb

```text
analysis/imdb/benchmark_aggregate_results_imdb_all_sfs.csv
```

The following scale-specific files are also provided for easier inspection:

```text
analysis/imdb/benchmark_aggregate_results_sf025.csv
analysis/imdb/benchmark_aggregate_results_sf050.csv
analysis/imdb/benchmark_aggregate_results_sf1.csv
```

The normalization script uses the consolidated IMDb file:

```text
analysis/imdb/benchmark_aggregate_results_imdb_all_sfs.csv
```

#### FIBEN

```text
analysis/fiben/benchmark_aggregate_results_fiben_sf1.csv
analysis/fiben/benchmark_aggregate_results_fiben_sf10.csv
analysis/fiben/benchmark_aggregate_results_fiben_sf30.csv
```

#### LDBC SNB

```text
analysis/ldbc_snb/benchmark_aggregate_results_ldbc_snb_sf0_1.csv
analysis/ldbc_snb/benchmark_aggregate_results_ldbc_snb_sf1.csv
analysis/ldbc_snb/benchmark_aggregate_results_ldbc_snb_sf3.csv
```

---

### Output files

The normalization script generates:

```text
analysis/generated/aggregate_results_all_datasets.csv
analysis/generated/normalization_report.txt
```

The file `aggregate_results_all_datasets.csv` is the common input for the next analysis scripts.

The file `normalization_report.txt` summarizes the generated output and checks whether the normalization was successful.

---

### Normalized columns

The generated CSV uses the following common columns:

```text
dataset
scale_label
query_name
query_scale_phase_id
config_id
g_class
design_family
benchmark_group
run_phase
n_runs
n_success_runs
avg_latency_ms
median_latency_ms
p95_latency_ms
p99_latency_ms
min_latency_ms
max_latency_ms
std_latency_ms
avg_documents_returned
avg_documents_written
source_experiment_id
source_file
```

---

### Meaning of the main normalized columns

#### `dataset`

Identifies the dataset.

Expected values:

```text
imdb
fiben
ldbc_snb
```

#### `scale_label`

Identifies the scale factor used in the benchmark.

Examples:

```text
sf0.25
sf0.5
sf1
sf10
sf30
sf0.1
sf3
```

#### `query_name`

Identifies the workload query.

Examples:

```text
QG6_EpisodesOfSeries
Q5_ReportsAndMetricDataOfCompany
IC5_NewGroups
IS4_ContentOfMessage
```

#### `config_id`

Identifies the concrete benchmarked MongoDB configuration.

For IMDb, this comes from `config_name`.

For FIBEN and LDBC SNB, this comes from `candidate_id`.

#### `g_class`

Identifies the SchemaLens configuration class.

Examples:

```text
G0
G1
G2
G3
G4
G5
G6
G7
G8
G9
CONTROL
```

#### `design_family`

Identifies the design family or pattern.

For IMDb, this comes from `benchmark_family`.

For FIBEN and LDBC SNB, this comes from `design_pattern`.

#### `benchmark_group`

Identifies how the configuration is used in the evaluation.

Expected values:

```text
primary
secondary_affected
control
```

#### `run_phase`

Identifies whether the result comes from cold or hot benchmark runs.

Expected values:

```text
cold
hot
```

#### `p95_latency_ms`

The 95th percentile latency in milliseconds.

This is the main latency metric used in the paper.

---

### Run command

From the repository root, run:

```bash
python analysis/scripts/normalize_aggregate_outputs.py
```

On Windows PowerShell, run:

```powershell
py analysis\scripts\normalize_aggregate_outputs.py
```

---

### Expected result

The script should read the aggregate CSV files from IMDb, FIBEN, and LDBC SNB and generate:

```text
analysis/generated/aggregate_results_all_datasets.csv
analysis/generated/normalization_report.txt
```

Expected row counts:

```text
IMDb: 540 rows
FIBEN: 360 rows
LDBC SNB: 384 rows
Total: 1284 rows
```

Expected datasets:

```text
imdb
fiben
ldbc_snb
```

Expected run phases:

```text
cold
hot
```

---

### Validation report

The generated file:

```text
analysis/generated/normalization_report.txt
```

reports:

- total rows;
- rows by dataset;
- rows by dataset and scale;
- rows by dataset and run phase;
- benchmark groups;
- unique queries by dataset;
- G classes by dataset;
- rows with missing p95 latency;
- duplicated rows;
- source files used.

A successful normalization should report:

```text
Rows with missing p95_latency_ms: 0
```

The duplicate-row check should also be reviewed. If duplicates are reported, they must be inspected before running baseline or ablation analyses.

---

## Step 2 — Check baseline coverage

### Purpose

Before simulating baselines, we check whether each baseline strategy selects configuration classes that are available in the measured aggregate benchmark outputs.

This is necessary because some baselines may select configuration classes that were not instantiated or measured for a specific dataset, query, scale factor, and run phase.

This step does not compare latency.

This step does not compute regret.

This step does not rerun MongoDB benchmarks.

It only checks whether the required baseline configuration classes are available in the existing aggregate results.

---

### Input file

```text
analysis/generated/aggregate_results_all_datasets.csv
```

---

### Script

```text
analysis/scripts/check_baseline_coverage.py
```

---

### Generated files

```text
analysis/generated/available_g_classes_by_query.csv
analysis/generated/baseline_coverage_by_case.csv
analysis/generated/baseline_coverage_summary.csv
analysis/generated/missing_baseline_candidates.csv
analysis/generated/query_metadata_template.csv
analysis/generated/baseline_coverage_report.txt
```

---

### Baselines checked

```text
random_k
always_reference
always_embed
depth_only
relationship_type_only
```

---

### Meaning of the baseline coverage outputs

#### `available_g_classes_by_query.csv`

Lists the measured configuration classes available for each dataset, query, scale factor, and run phase.

#### `baseline_coverage_by_case.csv`

Shows, for each baseline and query-scale-phase case:

- desired G classes;
- available G classes;
- selected available G classes;
- missing G classes;
- coverage ratio;
- coverage status.

#### `baseline_coverage_summary.csv`

Summarizes coverage for each baseline.

The main columns are:

```text
baseline
total_cases
full
partial
none
usable_cases
unavailable_cases
usable_ratio
mean_coverage_ratio
```

A baseline is considered usable for a case when it selects at least one measured configuration class.

Therefore:

```text
usable_cases = full + partial
unavailable_cases = none + metadata_missing + no_desired_classes
```

#### `missing_baseline_candidates.csv`

Lists cases where a baseline requested configuration classes that were not available in the measured aggregate outputs.

#### `query_metadata_template.csv`

Stores the query-level metadata used by `depth_only` and `relationship_type_only`.

The LDBC SNB metadata is provisional and should be reviewed before using these two baselines in final paper text.

---

### Run command

From the repository root, run:

```bash
python analysis/scripts/check_baseline_coverage.py
```

On Windows PowerShell, run:

```powershell
py analysis\scripts\check_baseline_coverage.py
```

---

### Expected result

The script should generate coverage outputs for:

```text
252 query-scale-phase cases
```

Expected cases by dataset:

```text
IMDb: 60
FIBEN: 60
LDBC SNB: 132
```

Expected baseline coverage summary:

```text
random_k: 252 usable cases
always_reference: 252 usable cases
relationship_type_only: 234 usable cases
always_embed: 180 usable cases
depth_only: 180 usable cases
```

---

### Important note

The LDBC SNB query metadata used for `depth_only` and `relationship_type_only` is provisional in this script.

The metadata should be reviewed before using depth-only or relationship-type-only baseline results in the paper text.

---

## What these steps do not do

These steps do not simulate baseline performance.

These steps do not run ablation analysis.

These steps do not rerun MongoDB benchmarks.

They only create a common, clean input file and verify whether baseline candidates are available in the measured outputs.

---

## Next planned scripts

The next analysis scripts will use:

```text
analysis/generated/aggregate_results_all_datasets.csv
analysis/generated/baseline_coverage_by_case.csv
```

Planned scripts:

```text
analysis/scripts/simulate_baselines.py
analysis/scripts/run_ablation_analysis.py
analysis/scripts/analyze_failure_cases.py
```

---

## Reproducibility note

These analyses are based on aggregate benchmark outputs already included in the repository.

They are intended for lightweight verification of the paper results. Full benchmark reproduction is still possible, but it requires loading the datasets, materializing MongoDB candidate configurations, and rerunning repeated cold/hot benchmark executions.

The lightweight path is recommended for quickly verifying:

- p95 latency;
- Top-1 preservation;
- Top-3 preservation;
- near-best preservation within the 5% threshold;
- relative regret;
- control-winner cases;
- cross-scale behavior.



## Step 3 — Simulate baseline performance

### Purpose

After checking baseline coverage, we simulate the performance of simple reduction baselines over the measured aggregate benchmark outputs.

This step compares SchemaLens with simple alternative reduction strategies.

The goal is to evaluate whether SchemaLens preserves better configurations than simpler policies such as random selection, always-reference, always-embed, depth-only activation, and relationship-type-only activation.

This step does not rerun MongoDB benchmarks.

It only uses latency values already present in the normalized aggregate results.

---

### Input files

```text
analysis/generated/aggregate_results_all_datasets.csv
analysis/generated/baseline_coverage_by_case.csv
```

---

### Script

```text
analysis/scripts/simulate_baselines.py
```

---

### Baselines simulated

```text
schema_lens
random_k
always_reference
always_embed
depth_only
relationship_type_only
```

---

### Baseline definitions

#### `schema_lens`

Uses the configurations selected by SchemaLens.

In the normalized aggregate outputs, these are the configurations whose `benchmark_group` is not `control`.

#### `random_k`

Randomly selects the same number of measured configuration classes as SchemaLens selected for the same query-scale-phase case.

This random process is repeated multiple times, and the reported result is averaged across repetitions.

#### `always_reference`

Selects measured reference-oriented configuration classes when available.

The intended classes are:

```text
CONTROL
G0
G3
G6
G7
```

#### `always_embed`

Selects measured embedding-oriented configuration classes when available.

The intended classes are:

```text
G2
G4
G5
G8
G9
```

#### `depth_only`

Selects configuration classes using only the query depth metadata.

This baseline ignores relationship semantics, sharedness, update volatility, and residual traversal.

#### `relationship_type_only`

Selects configuration classes using only the dominant relationship type.

This baseline ignores root choice, depth, residual traversal, sharedness, and update volatility.

---

### Metrics computed

For each dataset, scale factor, query, run phase, and baseline, the script computes:

```text
global_best_g_class
global_best_p95
baseline_best_g_class
baseline_best_p95
top1_preserved
top3_preserved
near_best_preserved
relative_regret
availability_status
```

---

### Top-1 preservation

Top-1 preservation checks whether the baseline-selected set contains the best measured configuration for the same dataset, scale factor, query, and run phase.

```text
1 = the best measured configuration is preserved
0 = the best measured configuration is not preserved
```

---

### Top-3 preservation

Top-3 preservation checks whether the selected set contains at least one of the three best measured configurations.

```text
1 = at least one Top-3 configuration is preserved
0 = no Top-3 configuration is preserved
```

---

### Near-best preservation

A configuration is considered near-best when its p95 latency is within 5% of the best measured p95 for the same dataset, scale factor, query, and run phase.

```text
(selected_p95 - global_best_p95) / global_best_p95 <= 0.05
```

---

### Relative regret

Relative regret measures the latency loss of the best selected configuration relative to the best measured configuration.

```text
relative_regret = (baseline_best_p95 - global_best_p95) / global_best_p95
```

A regret of `0` means that the baseline preserved the best measured configuration.

---

### Handling unavailable cases

A baseline is available for a query-scale-phase case only when it selects at least one measured configuration class.

If a baseline selects no measured configuration class, the case is marked as unavailable.

No latency is inferred for unavailable cases.

---

### Generated files

```text
analysis/generated/baseline_performance_by_case.csv
analysis/generated/baseline_performance_summary.csv
analysis/generated/baseline_performance_by_dataset.csv
analysis/generated/baseline_failure_cases.csv
analysis/generated/baseline_performance_report.txt
```

---

### Expected scope

The input contains:

```text
252 query-scale-phase cases
```

Expected cases by dataset:

```text
IMDb: 60
FIBEN: 60
LDBC SNB: 132
```

The exact number of available cases depends on the baseline coverage.

The previous coverage step showed:

```text
random_k: 252 usable cases
always_reference: 252 usable cases
relationship_type_only: 234 usable cases
always_embed: 180 usable cases
depth_only: 180 usable cases
```

---

### Expected use in the paper

The generated summaries support the section comparing SchemaLens with simple reduction baselines.

They help answer whether SchemaLens preserves best or near-best configurations more reliably than simple strategies.

The results should be interpreted together with the coverage analysis, because some baselines are not available for all query-scale-phase cases.

---

### Run command

From the repository root, run:

```bash
python analysis/scripts/simulate_baselines.py
```

On Windows PowerShell, run:

```powershell
py analysis\scripts\simulate_baselines.py
```



## Step 4 — Baseline diagnostics and SchemaLens vs random-k

### Purpose

After simulating baseline performance, we add a diagnostic analysis to better understand the behavior of `random_k`.

The `random_k` baseline is stochastic. It randomly samples the same number of measured configuration classes as SchemaLens selects for each query-scale-phase case.

This means that `random_k` can perform well when:

- the measured configuration space is small;
- SchemaLens selects several classes;
- many configurations are close to the best observed p95;
- the global best has a high probability of being included by chance.

Therefore, `random_k` should be interpreted as a statistical sanity-check baseline, not as an explainable design method.

SchemaLens remains different from `random_k` because SchemaLens selects configurations using EER/workload evidence, while `random_k` selects configurations without semantic justification.

---

### Input file

```text
analysis/generated/baseline_performance_by_case.csv
```

---

### Script

```text
analysis/scripts/analyze_baseline_diagnostics.py
```

---

### Generated files

```text
analysis/generated/baseline_performance_summary_hot.csv
analysis/generated/baseline_performance_by_dataset_hot.csv
analysis/generated/schema_lens_vs_random_k_by_case.csv
analysis/generated/schema_lens_vs_random_k_summary.csv
analysis/generated/schema_lens_vs_random_k_report.txt
```

---

### Hot-run summaries

The diagnostic script generates hot-run-only summaries because the paper mainly interprets hot benchmark results when comparing p95 latency.

Generated files:

```text
analysis/generated/baseline_performance_summary_hot.csv
analysis/generated/baseline_performance_by_dataset_hot.csv
```

These files summarize:

- available cases;
- Top-1 preservation;
- near-best preservation;
- mean relative regret.

---

### SchemaLens vs random-k comparison

The diagnostic script also compares SchemaLens and `random_k` case by case.

Generated files:

```text
analysis/generated/schema_lens_vs_random_k_by_case.csv
analysis/generated/schema_lens_vs_random_k_summary.csv
analysis/generated/schema_lens_vs_random_k_report.txt
```

The comparison reports:

- cases where SchemaLens has higher Top-1 preservation;
- cases where `random_k` has higher Top-1 probability;
- tied cases;
- SchemaLens regret;
- expected `random_k` regret;
- dataset-level differences;
- hot-run and cold-run differences.

---

### Main interpretation

The baseline simulation shows that SchemaLens clearly outperforms deterministic heuristic baselines such as:

```text
always_reference
always_embed
depth_only
relationship_type_only
```

The `random_k` baseline can be competitive because it samples the same number of measured configuration classes as SchemaLens.

However, `random_k` is not an explainable design-space reduction method. It does not use EER semantics, workload structure, relationship type, depth, sharedness, or update volatility.

The diagnostic results should therefore be interpreted as follows:

```text
random_k = statistical sanity check
SchemaLens = explainable workload-aware reduction method
```

In the paper, the correct claim is not that SchemaLens always beats random selection.

The more accurate claim is:

```text
SchemaLens outperforms deterministic heuristic baselines and remains competitive with random-k, while providing an explainable and reproducible reduction based on EER/workload evidence.
```

For the official LDBC SNB workload, SchemaLens also slightly outperforms `random_k` in Top-1 preservation and mean regret.

---

### Run command

From the repository root, run:

```bash
python analysis/scripts/analyze_baseline_diagnostics.py
```

On Windows PowerShell, run:

```powershell
py analysis\scripts\analyze_baseline_diagnostics.py
```


## Step 5 — Normalize ablation variables

### Purpose

This step normalizes the analytical metadata used for the ablation study across IMDb, FIBEN, and LDBC SNB.

Each dataset stores SchemaLens methodology outputs with different column names and file structures. This normalization step converts them into common files so that the ablation analysis can use real methodology variables instead of proxy rules.

---

### Input folders

```text
analysis/imdb/ablation_variables/
analysis/fiben/ablation_variables/
analysis/ldbc_snb/ablation_variables/
```

---

### Main input files

IMDb:

```text
analysis/imdb/ablation_variables/query_analytical_metadata_imdb.csv
analysis/imdb/ablation_variables/query_class_activation_imdb.csv
analysis/imdb/ablation_variables/benchmark_coverage_imdb.csv
analysis/imdb/ablation_variables/reduction_summary_imdb.csv
```

FIBEN:

```text
analysis/fiben/ablation_variables/query_analytical_metadata_fiben.csv
analysis/fiben/ablation_variables/query_class_activation_fiben.csv
analysis/fiben/ablation_variables/query_class_activation_long_fiben.csv
analysis/fiben/ablation_variables/benchmark_configuration_selection_fiben.csv
analysis/fiben/ablation_variables/reduction_delta_by_query_depth_fiben.csv
```

LDBC SNB:

```text
analysis/ldbc_snb/ablation_variables/query_analytical_metadata_ldbc_snb.csv
analysis/ldbc_snb/ablation_variables/query_class_activation_ldbc_snb.csv
analysis/ldbc_snb/ablation_variables/query_class_activation_long_ldbc_snb.csv
analysis/ldbc_snb/ablation_variables/benchmark_execution_plan_ldbc_snb.csv
analysis/ldbc_snb/ablation_variables/reduction_metrics_ldbc_snb.csv
```

---

### Script

```text
analysis/scripts/normalize_ablation_variables.py
```

---

### Generated files

```text
analysis/generated/query_analytical_metadata_all_datasets.csv
analysis/generated/query_class_activation_all_datasets.csv
analysis/generated/benchmark_configuration_selection_all_datasets.csv
analysis/generated/ablation_variables_normalization_report.txt
```

---

### Normalized query metadata

The file:

```text
analysis/generated/query_analytical_metadata_all_datasets.csv
```

contains one row per query and dataset.

It standardizes the main analytical variables used by SchemaLens:

```text
dataset
query_name
selected_root
Rc
D
Re
DeltaR
DeltaRratio
dominant_semantic_type
association_count
associative_count
containment_count
update_volatility_mean
update_volatility_max
update_volatility_class
observed_sharedness_mean
observed_sharedness_max
observed_sharedness_class
```

---

### Normalized activation output

The file:

```text
analysis/generated/query_class_activation_all_datasets.csv
```

contains the normalized G-class activation output.

For FIBEN, the source file contains both active and inactive G-class rows. Downstream scripts must use:

```text
is_active == True
```

For IMDb and LDBC SNB, the activation files contain only activated classes.

---

### Normalized benchmark selection

The file:

```text
analysis/generated/benchmark_configuration_selection_all_datasets.csv
```

links query names, configuration identifiers, G-classes, design patterns, and benchmark groups.

The normalized benchmark groups are:

```text
primary
secondary_affected
control
```

---

### Validation result

The normalization report confirms:

```text
query_analytical_metadata_all_datasets.csv: 42 rows
query_class_activation_all_datasets.csv: 191 rows
benchmark_configuration_selection_all_datasets.csv: 214 rows
```

Query metadata by dataset:

```text
IMDb: 10 queries
FIBEN: 10 queries
LDBC SNB: 22 queries
```

The report also confirms that there are no missing required columns and no query mismatches between query metadata, activation output, and benchmark selection.

---

### Run command

From the repository root:

```bash
python analysis/scripts/normalize_ablation_variables.py
```

On Windows PowerShell:

```powershell
py analysis\scripts\normalize_ablation_variables.py
```