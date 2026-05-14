# SchemaLens Artifact — FIBEN Case Study

This repository contains the code and documentation required to reproduce the FIBEN experiments used in the paper on **SchemaLens: Explainable Design-Space Reduction for Workload-Aware MongoDB Schema Selection**.

FIBEN is used in the paper as a finance-oriented comparative dataset. It evaluates whether SchemaLens can reduce the MongoDB design space for a workload involving companies, financial reports, securities, holdings, accounts, persons, and transactions.

The repository supports reproduction of:

- scale-factor preparation;
- methodology execution;
- MongoDB benchmark execution;
- result analysis;
- paper-support outputs.

---

# Repository structure

Current FIBEN-related files:


schemalens_reprodutibilty/
├── methodology/
│   └── feben_methdology.ipynb
│
├── scale_generator/
│   └── fiben/
│       ├── Fiben_generate_scale_factor.ipynb
│       └── readme_generate_scale_factor_fiben-miss link repository.md
│
├── benchmark/
│   └── fiben/
│       └── run_fiben_mongo_benchmark.py
│
└── analysis/
    └── fiben/
        ├── analyzi_results.ipynb
        ├── comparison sfs.ipynb
        └── benchmark_execution_plan.csv

Main FIBEN files:

methodology/feben_methdology.ipynb
scale_generator/fiben/Fiben_generate_scale_factor.ipynb
benchmark/fiben/run_fiben_mongo_benchmark.py
analysis/fiben/analyzi_results.ipynb
analysis/fiben/comparison sfs.ipynb
analysis/fiben/benchmark_execution_plan.csv

The large FIBEN scale-factor data files are not stored directly in this Git repository due to size constraints.

The artifact assumes an external FIBEN scale-factor package.

FIBEN scale package:
https://osf.io/532rn/overview?view_only=0a93fbed1db745d0978aa2e9f6cd7c78


Expected local folder structure:

datasets/
└── fiben/
    ├── sf1/
    ├── sf10/
    └── sf30/

Here:

sf1 is the workload-induced FIBEN baseline subset;
sf10 and sf30 are generated from sf1 using the FIBEN scale-factor generation workflow.
Environment

Requirements:

Python
Jupyter
Docker
MongoDB in Docker

Install the Python dependencies required by the notebooks and scripts, for example:

pip install pandas numpy duckdb pymongo

Start MongoDB, for example:

docker run -d \
  --name fiben_mongodb_artifact \
  -p 27018:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=mongo \
  -e MONGO_INITDB_ROOT_PASSWORD=mongo \
  mongo:8

Adjust host, port, and credentials if needed.

Reproduction paths
Full reproduction

From the original/raw FIBEN package to the final paper-support outputs.

Steps:

generate the workload-induced sf1 subset;
generate sf10 and sf30;
run the SchemaLens methodology notebook;
run the MongoDB benchmark;
run the corrected result analysis;
run the cross-scale comparison;
generate the final paper-support outputs.
Benchmark reproduction

If the scale-factor folders already exist locally:

run the methodology notebook;
run the MongoDB benchmark;
run the analysis notebook;
run the cross-scale comparison notebook;
generate the final table-support outputs.
Result verification

If benchmark outputs already exist:

use the benchmark aggregate outputs for sf1, sf10, and sf30;
run the corrected analysis;
regenerate the representative-case outputs;
regenerate the final table-support outputs.

This is the recommended lightweight verification path.

Workflow

#Step 1 — Scale-factor generation

Run:
scale_generator/fiben/Fiben_generate_scale_factor.ipynb

This notebook generates or documents the generation of:

sf1
sf10
sf30

The FIBEN scale-factor workflow builds a workload-induced sf1 subset and then creates larger synthetic instances while preserving the workload-relevant relationship structure.

The additional scale-generation notes are in:

scale_generator/fiben/readme_generate_scale_factor_fiben-miss link repository.md

#Step 2 — Methodology execution

Run:

methodology/feben_methdology.ipynb

This step executes the SchemaLens methodology for FIBEN. It derives the conceptual/workload matrix, applies the activation logic, and generates the artifacts used by the benchmark.

The key benchmark artifact currently stored in this repository is:

analysis/fiben/benchmark_execution_plan.csv

This file is used as the benchmark execution plan for the FIBEN MongoDB benchmark.


#Step 3 — MongoDB benchmark execution

Run:

benchmark/fiben/run_fiben_mongo_benchmark.py

This script:

loads the FIBEN scale-factor data;
materializes MongoDB configurations;
executes benchmark queries;
exports benchmark outputs.

Example command for sf1:

python benchmark/fiben/run_fiben_mongo_benchmark.py \
  --data-dir data/fiben/sf1 \
  --artifacts-dir analysis/fiben \
  --results-dir results/fiben/sf1 \
  --scale-label sf1 \
  --mongo-host 127.0.0.1 \
  --mongo-port 27018 \
  --mongo-username mongo \
  --mongo-password mongo \
  --mongo-auth-source admin \
  --batch-size 100000 \
  --repetitions 10 \
  --force-rebuild-db \
  --verbose

Repeat with the corresponding paths for:

sf10
sf30

Example:

python benchmark/fiben/run_fiben_mongo_benchmark.py \
  --data-dir data/fiben/sf10 \
  --artifacts-dir analysis/fiben \
  --results-dir results/fiben/sf10 \
  --scale-label sf10 \
  --mongo-host 127.0.0.1 \
  --mongo-port 27018 \
  --mongo-username mongo \
  --mongo-password mongo \
  --mongo-auth-source admin \
  --batch-size 100000 \
  --repetitions 10 \
  --force-rebuild-db \
  --verbose

python benchmark/fiben/run_fiben_mongo_benchmark.py \
  --data-dir data/fiben/sf30 \
  --artifacts-dir analysis/fiben \
  --results-dir results/fiben/sf30 \
  --scale-label sf30 \
  --mongo-host 127.0.0.1 \
  --mongo-port 27018 \
  --mongo-username mongo \
  --mongo-password mongo \
  --mongo-auth-source admin \
  --batch-size 100000 \
  --repetitions 10 \
  --force-rebuild-db \
  --verbose

#Step 4 — Corrected result analysis

Run:

analysis/fiben/analyzi_results.ipynb

This notebook computes the corrected SchemaLens metrics per:

query × scale factor × run phase

The metrics include:

DSR;
Top-1 preservation;
near-best preservation within 5%;
activated regret;
primary regret.

Expected analysis outputs include files such as:

schemalens_reduction_analysis_hot.csv
fiben_summary_hot_catalog_corrected.csv
fiben_representative_cases_hot.csv
fiben_secondary_winners_hot_catalog_corrected.csv
fiben_control_winners_hot_catalog_corrected.csv
fiben_best_by_query_scale_hot_catalog_corrected.csv
Step 5 — Cross-scale comparison

Run:

analysis/fiben/comparison sfs.ipynb

This notebook compares the FIBEN results across:

sf1
sf10
sf30

Expected cross-scale outputs include files such as:

cross_scale_summary.csv
cross_scale_p95.csv
cross_scale_configs.csv
cross_scale_regret.csv
cross_scale_near_best.csv
cross_scale_final_table.csv
Benchmark notes

The benchmark is executed through:

benchmark/fiben/run_fiben_mongo_benchmark.py

Important:

data loading is performed in batches;
larger batch sizes usually improve loading performance if memory is available;
each scale factor should use a separate result directory;
--scale-label, --data-dir, and --results-dir must match the intended scale.

Final experiment settings used in the paper:

Run phases: hot and cold
Repetitions: 10 each
Scale factors: sf1, sf10, sf30
MongoDB: Docker-based MongoDB instance
Expected benchmark outputs

Each benchmark run should generate files such as:

benchmark_aggregate_results.csv
benchmark_raw_results.csv
benchmark_run_manifest.json
candidate_load_summary.csv
scale_db_initialization_summary.csv
execution.log

The main file used by the analysis is:

benchmark_aggregate_results.csv

The raw file is kept for auditability:

benchmark_raw_results.csv
Representative FIBEN cases used in the paper

The paper uses three representative FIBEN cases:

Association:
Q2_CompanyWithIndustryCountryAndListedSecurities

Associative:
Q3_SecuritiesHeldInEachFinancialServiceAccount

Analytical / containment-like:
Q5_ReportsAndMetricDataOfCompany

These cases support the FIBEN rows in the final cross-dataset summary table.

Paper connection

The FIBEN outputs support the cross-dataset comparison in the SchemaLens paper.

The final table-support outputs are generated from the per-scale analysis and cross-scale comparison notebooks.

Expected final outputs include:

cross_scale_final_table.csv

Missing benchmark execution plan

If the benchmark reports a missing execution plan, check that this file exists:

analysis/fiben/benchmark_execution_plan.csv

and that the benchmark command uses:

--artifacts-dir analysis/fiben
Q5 returns zero documents

Check whether the benchmark runner uses normalized join fields for SF10/SF30. The corrected Q5 path is:

Corporation
→ FinancialReport
→ ReportElement
→ StatementElement
SF10 or SF30 results look identical to SF1

Check that these three arguments point to the correct scale:

--data-dir
--results-dir
--scale-label

Each scale factor must use a separate result directory.
