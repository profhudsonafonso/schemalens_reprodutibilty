# SchemaLens Artifact — IMDb Case Study

This repository contains the code and documentation required to reproduce the **IMDb case study** used in the paper on **SchemaLens: Explainable Design-Space Reduction for Workload-Aware MongoDB Schema Selection**.

IMDb is used in the paper as the detailed running example because it contains the three semantic patterns handled by SchemaLens:

- **association**
- **associative**
- **containment**

The repository supports reproduction of:

- scale-factor preparation
- methodology execution
- MongoDB benchmark
- result analysis
- paper-support outputs

---

# Repository structure


schemalens-artifact/
├── README.md
├── requirements.txt
├── docker-compose.yml
├── methodology/
├── scale_generation/
├── benchmark/
├── analysis/
└── docs/

Main IMDb files:

methodology/imdb_methodology.ipynb
scale_generation/imdb_scale_generation.ipynb
benchmark/run_imdb_mongo_benchmark.py
analysis/analyze_single_scale.py
analysis/compare_scales.py

The large IMDb data files are not stored directly in this Git repository due to size constraints.

The artifact assumes an external IMDb sf1 data package, from which the smaller scale factors used in the paper are generated.

IMDb sf package: https://osf.io/532rn/overview?view_only=0a93fbed1db745d0978aa2e9f6cd7c78

Expected local folder structure:

data/
└── imdb/
    ├── sf_1/
    ├── sf_025/
    └── sf_050/

Here:

sf_1 is the reference package
sf_025 and sf_050 are generated from sf_1
Environment

Requirements:

Python 
Jupyter
Docker
MongoDB in Docker

Install Python dependencies with:

pip install -r requirements.txt

Start MongoDB, for example:

docker run -d --name imdb_mongodb_artifact -p 27018:27017 mongo:8

Adjust host, port, and container name if needed.

Reproduction paths
1. Full reproduction

From the IMDb sf1 package to the final paper-support outputs.

Steps:

generate sf0.25 and sf0.50 from sf1
run the methodology notebook
run the MongoDB benchmark
run the corrected analysis
run the cross-scale comparison
generate the final paper-support outputs
2. Benchmark reproduction

If the scale-factor folders already exist locally:

run the methodology notebook
run the benchmark
run the analysis
run the comparison
generate the final table-support outputs
3. Result verification

If benchmark outputs already exist:

consolidate benchmark aggregate outputs across sf0.25, sf0.50, and sf1
run the corrected analysis
regenerate the representative-case outputs
regenerate the final table-support outputs

This is the recommended lightweight verification path.

Workflow
Step 1 — Scale-factor generation

Run:

scale_generation/imdb_scale_generation.ipynb

This generates:

sf0.25
sf0.50

from the IMDb sf1 package.

Step 2 — Methodology execution

Run:

methodology/imdb_methodology.ipynb

This step generates the analytical outputs used by the benchmark, especially:

mongo_experiment_catalog.csv
benchmark_execution_template.csv
Step 3 — Benchmark execution

Run:

benchmark/run_imdb_mongo_benchmark.py

This step:

materializes MongoDB configurations
loads IMDb data
executes benchmark queries
exports benchmark outputs
Step 4 — Corrected result analysis

Run:

analysis/analyze_single_scale.py

This computes, per (query, scale factor, run phase):

DSR
Top-1 preservation
near-best preservation within 5%
activated regret
primary regret
Step 5 — Cross-scale comparison

Run:

analysis/compare_scales.py

This compares the IMDb results across:

sf0.25
sf0.50
sf1
Step 6 — Paper-support outputs

Run:

analysis/table12_generation.py

This produces the representative-case summaries used in the paper.

Benchmark notes

The benchmark is executed through:

benchmark/run_imdb_mongo_benchmark.py

Important:

data loading is performed in batches
smaller batch sizes make the load slower
larger batch sizes usually improve performance if memory is available

Document here the final experiment settings used in the paper:


Run phase(s): hot and cold
Repetitions: 10 each

Example command:

python benchmark/run_imdb_mongo_benchmark.py \
  --catalog-csv [PATH_TO_CATALOG] \
  --template-csv [PATH_TO_TEMPLATE] \
  --results-dir [PATH_TO_RESULTS] \
  --run-phase hot \
  --max-runs [N] \
  --verbose
Expected analysis outputs

The corrected IMDb analysis should generate files such as:

imdb_summary_hot_catalog_corrected.csv
imdb_representative_cases_hot.csv
imdb_secondary_winners_hot_catalog_corrected.csv
imdb_control_winners_hot_catalog_corrected.csv
imdb_best_by_query_scale_hot_catalog_corrected.csv

These outputs support:

the detailed IMDb case study
the cross-scale comparison
the IMDb rows in the final cross-dataset summary table
Representative IMDb cases used in the paper

The paper uses three representative IMDb cases:

Containment: QG6_EpisodesOfSeries
Association: QG3_RecommendationByGenreAndSubtype
Associative: QG4_AllPersonsOfTypeForWatchItem

The detailed end-to-end walkthrough is only given for the containment case.
The other two are discussed briefly due to page limits.

