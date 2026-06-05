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

## Quick links

- Normalize aggregate outputs: `analysis/scripts/normalize_aggregate_outputs.py`
- Baseline coverage: `analysis/scripts/check_baseline_coverage.py`
- Baseline simulation: `analysis/scripts/simulate_baselines.py`
- Baseline diagnostics: `analysis/scripts/analyze_baseline_diagnostics.py`
- Ablation normalization: `analysis/scripts/normalize_ablation_variables.py`
- Ablation analysis: `analysis/scripts/run_ablation_analysis.py`
- Representative cases: `analysis/scripts/analyze_representative_cases.py`
- Joint explanatory cases: `analysis/scripts/find_joint_explanatory_cases.py`
- Short-paper table reproduction: `analysis/scripts/reproduce_short_paper_tables.py`
- IMDb query-plan validation: `analysis/generated/query_plan/imdb/`

For short-paper Table 1 and Table 2 reproduction, see:

    docs/short_paper_reproduction.md

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
│   ├── check_baseline_coverage.py
│   ├── simulate_baselines.py
│   ├── analyze_baseline_diagnostics.py
│   ├── normalize_ablation_variables.py
│   ├── run_ablation_analysis.py
│   ├── experimental_response_ablation_baselines.py
│   ├── analyze_representative_cases.py
│   ├── find_joint_explanatory_cases.py
│   └── reproduce_short_paper_tables.py
└── generated/
    ├── aggregate_results_all_datasets.csv
    ├── baseline_performance_by_case.csv
    ├── ablation_performance_by_case.csv
    ├── representative_case_table.csv
    ├── joint_explanatory_cases_hot.csv
    ├── short_paper_table1_reproduced.csv
    ├── short_paper_table1_details.csv
    ├── short_paper_table2_reproduced.csv
    ├── short_paper_reproduction_report.txt
    └── query_plan/
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

## Step 6 — Run ablation analysis

### Purpose

This step evaluates how much each analytical component contributes to SchemaLens.

The ablation analysis compares the full SchemaLens activation with reduced variants that remove one type of activation evidence at a time.

This analysis uses the normalized methodology variables generated in the previous step.

No MongoDB benchmark is rerun.

No latency is inferred for unmeasured configurations.

---

### Input files

```text
analysis/generated/aggregate_results_all_datasets.csv
analysis/generated/query_analytical_metadata_all_datasets.csv
analysis/generated/query_class_activation_all_datasets.csv
analysis/generated/benchmark_configuration_selection_all_datasets.csv
```

---

### Script

```text
analysis/scripts/run_ablation_analysis.py
```

---

### Ablation variants

```text
full_schema_lens
no_relationship_semantics
no_depth
no_residual_traversal
no_sharedness
no_update_volatility
no_relationship_semantics_no_depth
```

---

### Meaning of the variants

#### `full_schema_lens`

Uses the complete measured SchemaLens-selected space.

This corresponds to all non-control configurations selected for benchmark evaluation.

#### `no_relationship_semantics`

Removes activation evidence based on relationship semantics, such as association, associative, containment, descriptor, ownership, and subtype signals.

#### `no_depth`

Removes activation evidence based on embedding depth or deep/nested traversal.

#### `no_residual_traversal`

Removes activation evidence based on residual traversal and structural reduction, including `Re`, `DeltaR`, and `DeltaRratio`.

#### `no_sharedness`

Removes activation evidence based on observed sharedness.

#### `no_update_volatility`

Removes activation evidence based on update pressure or update volatility.

#### `no_relationship_semantics_no_depth`

Removes both relationship semantics and depth-sensitive activation evidence.

---

### Generated files

```text
analysis/generated/ablation_rules_used.csv
analysis/generated/ablation_performance_by_case.csv
analysis/generated/ablation_performance_summary.csv
analysis/generated/ablation_performance_by_dataset.csv
analysis/generated/ablation_performance_summary_hot.csv
analysis/generated/ablation_performance_by_dataset_hot.csv
analysis/generated/ablation_failure_cases.csv
analysis/generated/ablation_report.txt
```

---

### Main metrics

For each dataset, scale factor, query, run phase, and ablation variant, the script computes:

```text
top1_preserved
top3_preserved
near_best_preserved
relative_regret
```

Near-best uses the 5% threshold:

```text
(selected_p95 - global_best_p95) / global_best_p95 <= 0.05
```

---

### Main result

The ablation analysis shows that removing analytical components reduces the ability to preserve best or near-best configurations.

The full SchemaLens variant preserves substantially more Top-1 and near-best configurations than the ablated variants.

Hot-run summary:

```text
full_schema_lens: top1=0.8651, near_best=0.9206, mean_regret=0.0324
no_depth: top1=0.5794, near_best=0.6825, mean_regret=0.1435
no_relationship_semantics: top1=0.4786, near_best=0.6325, mean_regret=0.1580
no_relationship_semantics_no_depth: top1=0.4274, near_best=0.5641, mean_regret=0.1986
no_residual_traversal: top1=0.4921, near_best=0.6508, mean_regret=0.1573
no_sharedness: top1=0.5317, near_best=0.6905, mean_regret=0.1232
no_update_volatility: top1=0.5397, near_best=0.6905, mean_regret=0.1286
```

---

### Methodological note

This is a simulated ablation over the measured comparison space.

It removes component-specific G classes from the measured SchemaLens-selected space using normalized analytical metadata and activation evidence.

The root-choice ablation is not simulated because the benchmark artifacts do not include alternative-root MongoDB configurations for all queries.

Testing root choice would require materializing and benchmarking additional candidates rooted at non-selected entities.

---

### Run command

From the repository root:

```bash
python analysis/scripts/run_ablation_analysis.py
```

On Windows PowerShell:

```powershell
py analysis\scripts\run_ablation_analysis.py
```

## Step 7 — Generate advisor experimental response

### Purpose

This step generates a Markdown report summarizing the additional experimental analyses prepared in response to the advisor comments.

The report is intended as an intermediate explanation document. It is not necessarily the final paper text.

It includes:

```text
baseline comparison
random-k diagnostic
ablation study
dataset-level ablation
main interpretation
suggested response text for the advisor
recommended next steps
```

---

### Input files

```text
analysis/generated/baseline_performance_summary.csv
analysis/generated/baseline_performance_summary_hot.csv
analysis/generated/schema_lens_vs_random_k_summary.csv
analysis/generated/ablation_performance_summary.csv
analysis/generated/ablation_performance_summary_hot.csv
analysis/generated/ablation_performance_by_dataset_hot.csv
analysis/generated/query_analytical_metadata_all_datasets.csv
analysis/generated/query_class_activation_all_datasets.csv
analysis/generated/benchmark_configuration_selection_all_datasets.csv
```

---

### Script

```text
analysis/scripts/experimental_response_ablation_baselines.py
```

---

### Generated file

```text
analysis/generated/advisor_experimental_response.md
```

---

### Main purpose of the generated report

The generated report explains that:

```text
SchemaLens outperforms deterministic heuristic baselines.
random-k is competitive but should be interpreted as a statistical sanity check.
The ablation study shows that the analytical matrix components materially contribute to preservation quality.
Removing relationship semantics, depth, residual traversal, sharedness, or update volatility reduces Top-1 and near-best preservation.
```

---

### Run command

From the repository root:

```bash
python analysis/scripts/experimental_response_ablation_baselines.py
```

On Windows PowerShell:

```powershell
py analysis\scripts\experimental_response_ablation_baselines.py
```

---

### Expected output

After running the script, the following file is generated:

```text
analysis/generated/advisor_experimental_response.md
```

This file can be used as a detailed advisor-facing explanation of the baseline and ablation results before deciding which parts should be moved into the paper.



### Representative case analysis

After running the aggregate normalization, baseline, random-k diagnostic, and ablation scripts, generate the representative-case analysis with:

```bash
python analysis/scripts/analyze_representative_cases.py
```

This script does **not** rerun MongoDB benchmarks. It only combines already measured aggregate benchmark outputs with normalized SchemaLens methodology variables.

Inputs:

- `analysis/generated/aggregate_results_all_datasets.csv`
- `analysis/generated/query_analytical_metadata_all_datasets.csv`
- `analysis/generated/query_class_activation_all_datasets.csv`
- `analysis/generated/benchmark_configuration_selection_all_datasets.csv`
- `analysis/generated/ablation_performance_by_case.csv`
- `analysis/generated/baseline_performance_by_case.csv`
- `analysis/generated/schema_lens_vs_random_k_by_case.csv`

Outputs:

- `analysis/generated/representative_case_table.csv`
- `analysis/generated/representative_case_analysis.md`

The report explains selected IMDb, FIBEN, and LDBC SNB cases using:

- selected root;
- conceptual traversal count (`Rc`);
- depth (`D`);
- residual traversal (`Re`);
- `DeltaRratio`;
- dominant semantic type;
- update-volatility signal;
- observed-sharedness signal;
- activated G classes;
- measured benchmark classes;
- hot-run p95 winner;
- whether SchemaLens preserved Top-1 or a near-best configuration.

For a compact paper-oriented version using only the largest scale per dataset/query, run:

```bash
python analysis/scripts/analyze_representative_cases.py --scale-mode largest
```

The near-best threshold defaults to 5%, consistent with the paper revision:

```bash
python analysis/scripts/analyze_representative_cases.py --near-best-threshold 0.05
```

Methodological note: the script does not simulate root-choice ablation. Testing alternative roots would require materializing and benchmarking additional MongoDB configurations rooted at non-selected entities.

### Joint explanatory case selection

This step identifies representative cases that jointly explain baseline separation and ablation sensitivity.

The goal is to find cases where SchemaLens preserves the Top-1 configuration while deterministic baselines and/or ablated SchemaLens variants miss the winner.

Script:

```bash
python analysis/scripts/find_joint_explanatory_cases.py
```

Inputs:

- `analysis/generated/baseline_performance_by_case.csv`
- `analysis/generated/ablation_performance_by_case.csv`

Outputs:

- `analysis/generated/joint_explanatory_cases_hot.csv`
- `analysis/generated/joint_explanatory_cases_by_query_hot.csv`
- `analysis/generated/joint_explanatory_cases_hot.md`

The script classifies each hot-run case into one of the following categories:

- `joint_strong`
- `baseline_strong`
- `ablation_strong`
- `baseline_strong_with_ablation_signal`
- `ablation_strong_with_baseline_signal`
- `baseline_moderate`
- `ablation_moderate`
- `weak_or_redundant`

Interpretation:

- `baseline_strong` cases are useful to explain why fixed heuristics such as always-reference, always-embed, depth-only, or relationship-type-only are unstable.
- `ablation_strong` cases are useful to explain why SchemaLens analytical variables matter.
- `joint_strong` cases are the most complete examples because they connect baseline failure, ablation sensitivity, workload structure, and measured winners.

In the current revision, three representative explanatory cases are used as candidate examples:

- LDBC SNB `IC7_RecentLikers`: mixed workload, primary vs. secondary_affected candidates, and ablation sensitivity.
- FIBEN `Q2_CompanyWithIndustryCountryAndListedSecurities`: baseline separation and scale-dependent winner changes.
- IMDb `QG9_TopRatedSeriesByGenre`: extreme baseline failure, especially for `relationship_type_only`.

This step does not rerun MongoDB benchmarks. It reuses measured hot-run p95 results and the already generated baseline and ablation outputs.


### IMDb query-plan validation

The IMDb query-plan experiments were executed with the MongoDB query-plan-only runner:

`benchmark/imdb/run_imdb_mongo_query_plan.py`

The runner reuses the IMDb MongoDB materialization logic and collects `explain("executionStats")` metrics together with physical collection statistics.

Runner:

`python benchmark/imdb/run_imdb_mongo_query_plan.py`

The runner collects MongoDB `explain("executionStats")` metrics and physical collection statistics, including:

* `totalDocsExamined`
* `totalKeysExamined`
* `nReturned`
* plan stages such as `IXSCAN`, `FETCH`, `SORT`, and `AND_SORTED`
* collection document count
* collection size
* average object size
* estimated examined bytes

The first detailed validation case is IMDb `QG9_TopRatedSeriesByGenre`.

QG9 results are stored in:

`analysis/generated/query_plan/imdb/qg9_validation/`

This case explains why `G7 / series_g7` wins over WatchItem-rooted alternatives and over more embedded Series-rooted alternatives. `G7 / series_g7` uses a specialized `series` root with small documents. `G8 / series_g8` and `G9 / series_g9` use the same `series` root, but embed episode data that QG9 does not use, increasing physical document size. WatchItem-rooted configurations operate over the more generic `watchitems` collection and require a more complex indexed plan.

The first full IMDb query-plan group is stored in:

`analysis/generated/query_plan/imdb/group_A_light_no_roles/`

Group A covers the following queries:

* `QG1_WatchItemById`
* `QG2_WatchItemByTitle`
* `QG3_RecommendationByGenreAndSubtype`
* `QG7_UpdateWatchItemMetadata`
* `QG9_TopRatedSeriesByGenre`
* `QG10_AdvancedSearchWatchItems`

Group A was executed with `--minimal-base-load` because these queries do not require the auxiliary MongoDB collections `persons`, `roles`, or `episodes`.

This option does not simplify the candidate collections under evaluation. Candidate root collections such as `watchitems` and `series` are still fully materialized for each selected configuration. The option only skips auxiliary collections that are not accessed by the selected query group.

Main Group A files:

* `analysis/generated/query_plan/imdb/group_A_light_no_roles/query_plan_summary_results_group_A.csv`
* `analysis/generated/query_plan/imdb/group_A_light_no_roles/query_plan_component_results_group_A.csv`
* `analysis/generated/query_plan/imdb/group_A_light_no_roles/query_plan_status_summary_group_A.csv`
* `analysis/generated/query_plan/imdb/group_A_light_no_roles/benchmark_run_manifest_group_A.json`
* `analysis/generated/query_plan/imdb/group_A_light_no_roles/execution_group_A.log`

Main QG9 validation files:

* `analysis/generated/query_plan/imdb/qg9_validation/README_QG9_query_plan.md`
* `analysis/generated/query_plan/imdb/qg9_validation/qg9_query_plan_analysis.md`
* `analysis/generated/query_plan/imdb/qg9_validation/query_plan_summary_qg9_all_sfs.csv`
* `analysis/generated/query_plan/imdb/qg9_validation/query_plan_components_qg9_all_sfs.csv`

Raw MongoDB `explain` JSON files are not committed by default because they can become large in full query-plan runs.


Group B results are stored in:

`analysis/generated/query_plan/imdb/group_B_episodes/`

Group B covers:

- `QG6_EpisodesOfSeries`

The run completed for `sf0.25`, `sf0.5`, and `sf1`. No failed query-plan rows were detected. A `query_plan_zero_returned_rows_group_B.csv` file was generated, but these rows correspond to expected MongoDB `COUNT` / `COUNT_SCAN` behavior over the `episodes` collection and should not be interpreted as execution failures.


Group D results are stored in:

`analysis/generated/query_plan/imdb/group_D_insert_qg8/`

Group D covers:

- `QG8_AddPersonRoleToWatchItem`

The run completed for `sf0.25`, `sf0.5`, and `sf1`. No failed query-plan rows were detected. Because QG8 is an insert/update-oriented operation, pure `insert_one` components are recorded as `not_explainable`, which is expected in MongoDB. For associative configurations such as `G4`, `G5`, and `G6`, the runner captured explainable update components using `UPDATE`, `FETCH`, and `IXSCAN` over the `watchitem_id_1` index.

Group C results are documented in:

`analysis/generated/query_plan/imdb/README_group_C_roles.md`

Group C covers:

- `QG4_AllPersonsOfTypeForWatchItem`
- `QG5_AllPersonsForEpisodesOfSeries`

The full runs completed for `sf0.25` and `sf0.5`. For `sf1`, the full run was repeatedly interrupted during the materialization of the external `roles` collection. Therefore, the repository includes targeted associative runs for `watchitem_g4`, `watchitem_g5`, and `watchitem_g6`. The QG4 `sf1` associative run is stored in `group_C_roles_sf1_assoc_only/`. QG5 additionally requires the `episodes` collection, so its valid `sf1` run is stored in `group_C_qg5_sf1_assoc_only_with_episodes/`.

All IMDb query-plan groups were executed with:

`benchmark/imdb/run_imdb_mongo_query_plan.py`

For IMDb query-plan details and journal-ready table reproduction, see:

`analysis/generated/query_plan/imdb/README.md`
- IMDb journal query-plan table reproduction: `analysis/scripts/reproduce_imdb_query_plan_journal_tables.py`

### FIBEN MongoDB query-plan validation

The FIBEN MongoDB query-plan validation results are available in:

`analysis/generated/query_plan/fiben/`

This folder contains consolidated query-plan summaries and component-level explain results for FIBEN across SF1, SF10, and SF30. Read queries Q1–Q9 completed successfully across all scales. Q10 was consistently marked as skipped because it is an insert/update workload and is not comparable under read-query MongoDB `executionStats`.

Main files:

- `fiben_query_plan_summary_all.csv`
- `fiben_query_plan_components_all.csv`
- `fiben_query_plan_query_scale_status.csv`
- `fiben_query_plan_query_scale_overview.csv`
- `fiben_query_plan_best_by_estimated_bytes.csv`
- `fiben_query_plan_compact_candidates.csv`