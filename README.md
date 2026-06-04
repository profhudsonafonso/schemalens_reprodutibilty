# SchemaLens Reproducibility Artifact

This repository contains the reproducibility artifact for the paper **SchemaLens: Explainable Design-Space Reduction for Workload-Aware MongoDB Schema Selection**.

SchemaLens is an EER- and workload-guided methodology for reducing the MongoDB document-schema design space before benchmarking. Instead of recommending one final schema directly, it explains why a smaller, semantically justified subset of candidate configurations should be benchmarked.

## What this artifact contains

The repository supports reproduction of the main experimental workflow used in the paper:

1. methodology execution from conceptual schema and workload;
2. generation of MongoDB candidate configurations;
3. MongoDB benchmark execution;
4. result analysis;
5. paper-support outputs for the cross-dataset evaluation.

The artifact covers three datasets:

| Dataset  | Role in the paper                    | Main use                                                                |
| -------- | ------------------------------------ | ----------------------------------------------------------------------- |
| IMDb     | Detailed running example             | Association, associative, and containment-like patterns                 |
| FIBEN    | Finance-oriented comparative dataset | Business, analytical, associative, and containment-like access patterns |
| LDBC SNB | Official benchmark workload          | Social-network workload with IC, IS, and INS official queries           |

## Repository structure

```
schemalens_reprodutibilty/
  methodology/
    imdb_methodology.ipynb
    fiben_methodology.ipynb
    ldbc_snb_methodology.ipynb

  scale_generator/
    imdb/
    fiben/

  benchmark/
    imdb/
    fiben/
    ldbc_snb/

  analysis/
    imdb/
    fiben/
    ldbc_snb/
    generated/
    scripts/

  docs/
    short_paper_reproduction.md

  README.md
  README_IMDB.md
  README_FIBEN.md
  README_LDBC_SNB.md
  requirements.txt
  requirements-analysis.txt
  requirements-benchmark.txt
  docker-compose.yml
```

## Reproduction levels

The artifact supports three levels of reproduction.

### 1. Full reproduction

Use this path to regenerate the dataset scale factors, run the methodology, execute the MongoDB benchmark, and regenerate the paper-support outputs.

This path can be time-consuming because it requires loading and benchmarking multiple MongoDB configurations.

### 2. Benchmark reproduction

Use this path when the scale-factor data folders already exist locally.

Run the methodology notebooks, execute the MongoDB benchmark scripts, and run the analysis notebooks/scripts.

### 3. Result verification

Use this path when benchmark outputs already exist.

Run the analysis notebooks/scripts over the provided aggregate benchmark outputs to verify the reported DSR, Top-1 preservation, near-best preservation, relative regret, and representative cases.

This is the recommended lightweight path for reviewers.

## Makefile-based reproduction

The artifact provides a Makefile with lightweight verification and benchmark-entry targets.

Common commands include:

    make docker-up
    make check-artifact
    make reproduce-paper
    make analysis-pipeline
    make imdb-benchmark
    make fiben-benchmark
    make ldbc-benchmark

For details and required variables, see:

    docs/makefile_reproduction.md

Observed runtime estimates for lightweight verification, full benchmarks, and query-plan evidence are provided in:

    docs/runtime_estimates.md

## Short-paper table reproduction

For reproducing the short-paper Table 1 summaries and the Table 2 diagnostic cases, see:

```
docs/short_paper_reproduction.md
```

The reproduction script generates paper-facing CSV summaries from existing aggregate, baseline, and ablation outputs. It does not rerun MongoDB.

## Provided aggregate benchmark outputs

The repository includes aggregate benchmark result files for lightweight verification. These files allow reviewers to inspect the reported p95 latency, design-space reduction, Top-1 preservation, near-best preservation, relative regret, and cross-scale behavior without rerunning the full MongoDB benchmark.

### IMDb

```
analysis/imdb/benchmark_aggregate_results_imdb_all_sfs.csv
analysis/imdb/benchmark_aggregate_results_sf025.csv
analysis/imdb/benchmark_aggregate_results_sf050.csv
analysis/imdb/benchmark_aggregate_results_sf1.csv
```

### FIBEN

```
analysis/fiben/benchmark_aggregate_results_fiben_sf1.csv
analysis/fiben/benchmark_aggregate_results_fiben_sf10.csv
analysis/fiben/benchmark_aggregate_results_fiben_sf30.csv
```

### LDBC SNB

```
analysis/ldbc_snb/benchmark_aggregate_results_ldbc_snb_sf0_1.csv
analysis/ldbc_snb/benchmark_aggregate_results_ldbc_snb_sf1.csv
analysis/ldbc_snb/benchmark_aggregate_results_ldbc_snb_sf3.csv
```

Each aggregate file contains cold and hot benchmark summaries, including average latency, median latency, p95 latency, p99 latency, standard deviation, number of successful runs, and average documents returned or written.

## Data availability

Large raw and scale-factor datasets are not stored directly in this Git repository because of size constraints.

Dataset-specific instructions are provided in:

```
README_IMDB.md
README_FIBEN.md
README_LDBC_SNB.md
```

Each dataset README explains the expected local folder structure and the files needed to reproduce or verify the experiments.

## Environment

The experiments use Python, Jupyter, Docker, and MongoDB.

The artifact separates Python dependencies by reproduction mode to improve reproducibility and avoid mixing the analysis environment with the benchmark-server environment.

### Python dependency files

The dependency files are:

```
requirements.txt
requirements-analysis.txt
requirements-benchmark.txt
```

Use `requirements.txt` for the default lightweight verification environment. This file points to the pinned analysis environment:

```
-r requirements-analysis.txt
```

Use `requirements-analysis.txt` for notebooks, aggregate-result analysis, short-paper table reproduction, baseline diagnostics, ablation analysis, and paper-support scripts.

Use `requirements-benchmark.txt` for full MongoDB benchmark reproduction on the benchmark server.

For lightweight verification, install:

```
pip install -r requirements.txt
```

For full MongoDB benchmark reproduction, install:

```
pip install -r requirements-benchmark.txt
```

Start MongoDB with Docker Compose:

```
docker compose up -d
```

The default MongoDB port used by the benchmark scripts is `27018`.

## Dataset-specific instructions

Use the following README files for detailed instructions:

```
README_IMDB.md
README_FIBEN.md
README_LDBC_SNB.md
```

## Paper connection

The artifact supports the paper results as follows:

* IMDb supports the detailed end-to-end walkthrough and the representative IMDb rows in the cross-dataset table.
* FIBEN supports the finance-oriented representative cases in the cross-dataset comparison.
* LDBC SNB supports the aggregate official-workload validation across IC, IS, and INS queries.

## Notes for reviewers

The fastest way to verify the results is to use the provided aggregate benchmark outputs and run the analysis scripts/notebooks.

Full benchmark reproduction is supported but may take substantially longer because it requires materializing MongoDB candidate configurations and executing repeated cold/hot benchmark runs.

For this reason, the recommended reviewer path is:

1. install the lightweight analysis environment with `pip install -r requirements.txt`;
2. run the short-paper table reproduction script;
3. inspect the generated CSV summaries and aggregate benchmark outputs;
4. use the dataset-specific READMEs only if full benchmark reproduction is needed.
