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
│   ├── normalize_aggregate_outputs.py
│   └── check_baseline_coverage.py
└── generated/
    ├── aggregate_results_all_datasets.csv
    ├── normalization_report.txt
    ├── available_g_classes_by_query.csv
    ├── baseline_coverage_by_case.csv
    ├── baseline_coverage_summary.csv
    ├── missing_baseline_candidates.csv
    ├── query_metadata_template.csv
    └── baseline_coverage_report.txt
```

---

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