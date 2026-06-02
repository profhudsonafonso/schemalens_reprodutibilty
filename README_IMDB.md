# SchemaLens Artifact — IMDb Case Study

This README describes how to reproduce or verify the IMDb part of the SchemaLens evaluation.

IMDb is used in the paper as the detailed running example because it contains the three semantic patterns handled by SchemaLens:

* association;
* associative structures;
* containment-like structures.

The IMDb case study supports reproduction of:

1. scale-factor preparation or reuse;
2. methodology execution;
3. MongoDB candidate benchmarking;
4. result analysis;
5. paper-support outputs for the IMDb rows in the cross-dataset summary.

## Repository files

Main files for the IMDb case study:

```
methodology/imdb_methodology.ipynb

scale_generator/imdb/README.md
scale_generator/imdb/IMDB_sf_commented_english.ipynb

benchmark/imdb/run_mongo_benchmark_option_b_incremental.py
benchmark/imdb/mongo_experiment_catalog.csv
benchmark/imdb/benchmark_execution_template.csv

analysis/imdb/analyze_results_using_catalog.ipynb
analysis/imdb/compare_scale_factors_imdb.ipynb
analysis/imdb/benchmark_aggregate_results_imdb_all_sfs.csv
```

## Data availability

The raw IMDb TSV files and prepared IMDb scale-factor folders are not stored directly in this Git repository because of size and licensing constraints.

The prepared scale-factor package used in the paper is available on OSF:

```
https://osf.io/532rn/overview?view_only=0a93fbed1db745d0978aa2e9f6cd7c78
```

Reviewers can either use the prepared OSF package or regenerate the scale factors using the notebook in:

```
scale_generator/imdb/
```

The experiments use the IMDb non-commercial dataset files:

```
name.basics.tsv
title.akas.tsv
title.basics.tsv
title.crew.tsv
title.episode.tsv
title.principals.tsv
title.ratings.tsv
```

The scale-factor folders used in the experiments are:

```
sf0.25
sf0.5
sf1
```

After downloading or generating the data, organize them locally as:

```
data/
  imdb/
    sf_025/
    sf_050/
    sf_1/
```

Each scale-factor folder should contain the required IMDb TSV files.

If your local paths are different, update the `IMDB_SF_PATHS` dictionary in:

```
benchmark/imdb/run_mongo_benchmark_option_b_incremental.py
```

## Two reproduction options

### Option A — Use the prepared OSF scale-factor package

This is the recommended path for reviewers.

1. Download the prepared IMDb scale-factor package from OSF.
2. Extract it locally using the folder structure shown above.
3. Run the SchemaLens methodology notebook.
4. Run the MongoDB benchmark script using the extracted scale-factor folders.
5. Run the IMDb analysis notebooks to verify the reported results.

This option avoids the time-consuming scale-factor generation step.

### Option B — Regenerate the scale factors

Use this option only if you want to reproduce the IMDb scale-factor generation process.

Run the IMDb scale-generation notebook:

```
scale_generator/imdb/IMDB_sf_commented_english.ipynb
```

The notebook documents how the IMDb scale factors were prepared from the IMDb source TSV files.

The preparation creates the scale-factor folders used by the benchmark:

```
sf_025
sf_050
sf_1
```

Additional scale-generation instructions are provided in:

```
scale_generator/imdb/README.md
```

## Methodology reproduction

Run the notebook:

```
methodology/imdb_methodology.ipynb
```

This notebook generates or documents the IMDb SchemaLens methodology outputs, including:

* conceptual and semantic view preparation;
* analytical matrix generation;
* query classification;
* activated MongoDB configuration families.

The key methodology artifact used by the benchmark is the MongoDB experiment catalog:

```
benchmark/imdb/mongo_experiment_catalog.csv
```

## Benchmark reproduction

The benchmark runner is:

```
benchmark/imdb/run_mongo_benchmark_option_b_incremental.py
```

The runner requires:

```
benchmark/imdb/mongo_experiment_catalog.csv
benchmark/imdb/benchmark_execution_template.csv
```

Example command:

```
python benchmark/imdb/run_mongo_benchmark_option_b_incremental.py \
  --catalog-csv benchmark/imdb/mongo_experiment_catalog.csv \
  --template-csv benchmark/imdb/benchmark_execution_template.csv \
  --results-dir results/imdb/sf0_25 \
  --scale-label sf0.25 \
  --run-phase cold hot \
  --batch-size 10000 \
  --force-rebuild-scale-db
```

Repeat the benchmark for the other scale factors by changing:

```
--results-dir
--scale-label
```

The benchmark uses 10 cold-run and 10 hot-run repetitions per candidate/query pair.

MongoDB can be started from the repository root with:

```
docker compose up -d
```

The default MongoDB port is:

```
27018
```

## Result analysis

The main IMDb analysis notebooks are:

```
analysis/imdb/analyze_results_using_catalog.ipynb
analysis/imdb/compare_scale_factors_imdb.ipynb
```

The aggregate all-scale result file is:

```
analysis/imdb/benchmark_aggregate_results_imdb_all_sfs.csv
```

These files support the IMDb results reported in the paper, including:

* QG6 containment case;
* hot-run results across scale factors;
* primary, secondary-affected, and control query comparison;
* IMDb representative rows in the cross-dataset summary.

## Paper connection

The IMDb artifact supports:

* the end-to-end SchemaLens walkthrough;
* the QG6 containment example;
* the IMDb association, associative, and containment rows in the cross-dataset table;
* the IMDb diagnostic cases used in the short-paper Table 2.

The main representative IMDb queries are:

```
QG3_RecommendationByGenreAndSubtype
QG4_AllPersonsOfTypeForWatchItem
QG6_EpisodesOfSeries
```

For the short paper, QG4 and QG6 are also used as diagnostic examples:

* QG4 illustrates an associative bridge case over the WatchItem--Role--Person path.
* QG6 illustrates the containment case over the Series--Episode path.

## Lightweight verification

To verify the IMDb part of the paper without rerunning the full benchmark, use the provided aggregate benchmark outputs.

Consolidated all-scale file:

```
analysis/imdb/benchmark_aggregate_results_imdb_all_sfs.csv
```

Scale-specific files:

```
analysis/imdb/benchmark_aggregate_results_sf025.csv
analysis/imdb/benchmark_aggregate_results_sf050.csv
analysis/imdb/benchmark_aggregate_results_sf1.csv
```

The consolidated file is used for cross-scale analysis. The scale-specific files are provided for easier inspection of each IMDb scale factor.

These files support verification of:

* the IMDb containment case study;
* the G7/G8/G9 comparison for QG6_EpisodesOfSeries;
* p95 latency;
* near-best preservation within the 5% threshold;
* workload-level trade-offs across primary, secondary-affected, and control queries.

Full benchmark reproduction is supported, but it is more time-consuming because it requires materializing MongoDB candidate configurations and executing repeated cold/hot benchmark runs.

## Notes

The scale-factor data are large and are therefore distributed through OSF rather than stored directly in this Git repository.

The Git repository contains the methodology notebook, scale-generation notebook, benchmark script, benchmark input files, aggregate outputs, and analysis notebooks needed to reproduce or verify the IMDb part of the paper.
