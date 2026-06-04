# Makefile-Based Reproduction Guide

This document describes the Makefile targets provided by the SchemaLens artifact.

The Makefile is intended to provide a simple entry point for reviewers. It separates lightweight paper verification from full MongoDB benchmark reproduction.

## Main idea

There are three reproduction levels:

1. Lightweight paper verification.
2. Analysis-output regeneration from existing aggregate benchmark files.
3. Full MongoDB benchmark reproduction.

The recommended reviewer path is the lightweight verification path.

## Quick commands

Show available commands:

    make help

Install the pinned analysis environment:

    make install-analysis

Start MongoDB with Docker Compose:

    make docker-up

Stop MongoDB:

    make docker-down

Check whether the required artifact files are present:

    make check-artifact

Reproduce the short-paper Table 1 and Table 2 CSV summaries:

    make reproduce-paper

Regenerate the analysis pipeline from existing aggregate outputs:

    make analysis-pipeline

## Lightweight paper verification

The lightweight verification path does not rerun MongoDB.

It uses existing aggregate, baseline, and ablation outputs already included in the repository.

Run:

    make check-artifact
    make reproduce-paper

The main output files are:

    analysis/generated/short_paper_table1_reproduced.csv
    analysis/generated/short_paper_table1_details.csv
    analysis/generated/short_paper_table2_reproduced.csv
    analysis/generated/short_paper_reproduction_report.txt

This is the fastest and recommended path for reviewers.

## Full benchmark reproduction

Full benchmark reproduction requires:

- MongoDB running through Docker Compose;
- scale-factor data downloaded or generated locally;
- dataset-specific paths passed through Makefile variables;
- benchmark dependencies installed from requirements-benchmark.txt.

Install benchmark dependencies:

    pip install -r requirements-benchmark.txt

Start MongoDB:

    make docker-up

## IMDb benchmark

Example command:

    make imdb-benchmark IMDB_SCALE=sf0.25 IMDB_RESULTS_DIR=results/imdb/sf0_25

The target runs:

    benchmark/imdb/run_mongo_benchmark_option_b_incremental.py

The IMDb target uses:

    benchmark/imdb/mongo_experiment_catalog.csv
    benchmark/imdb/benchmark_execution_template.csv

Important: the IMDb benchmark runner does not expose a data-directory argument in the current script interface. The scale-factor data location must therefore be consistent with the runner configuration and the dataset-specific README.

## FIBEN benchmark

Example command:

    make fiben-benchmark FIBEN_DATA_DIR=/path/to/fiben/sf1 FIBEN_SCALE=sf1 FIBEN_RESULTS_DIR=results/fiben/sf1

The target runs:

    benchmark/fiben/run_fiben_mongo_benchmark.py

Main variables:

    FIBEN_DATA_DIR
    FIBEN_SCALE
    FIBEN_RESULTS_DIR
    FIBEN_ARTIFACTS_DIR

Default artifact directory:

    analysis/fiben

## LDBC SNB benchmark

Example command:

    make ldbc-benchmark LDBC_DATA_DIR=/path/to/ldbc_snb/sf0_1 LDBC_ARTIFACTS_DIR=/path/to/ldbc_snb_mongo_configurations LDBC_SCALE=sf0.1 LDBC_RESULTS_DIR=results/ldbc_snb/sf0_1

The target runs:

    benchmark/ldbc_snb/run_ldbc_snb_mongo_benchmark.py

Main variables:

    LDBC_DATA_DIR
    LDBC_ARTIFACTS_DIR
    LDBC_SCALE
    LDBC_RESULTS_DIR

## MongoDB defaults

The Makefile uses the following MongoDB defaults:

    MONGO_HOST=127.0.0.1
    MONGO_PORT=27018
    MONGO_USERNAME=mongo
    MONGO_PASSWORD=mongo
    MONGO_AUTH_SOURCE=admin

These values match the Docker Compose configuration used by the artifact.

## Runtime guidance

The following runtimes are approximate and depend on hardware, storage, Docker performance, and dataset scale.

| Scenario | Command | Requires MongoDB | Requires external data | Expected time |
|---|---|---:|---:|---:|
| Artifact check | make check-artifact | no | no | seconds |
| Short-paper table reproduction | make reproduce-paper | no | no | less than 1 minute |
| Analysis pipeline | make analysis-pipeline | no | no | minutes |
| IMDb benchmark | make imdb-benchmark ... | yes | yes | dataset- and scale-dependent |
| FIBEN benchmark | make fiben-benchmark ... | yes | yes | dataset- and scale-dependent |
| LDBC SNB benchmark | make ldbc-benchmark ... | yes | yes | dataset- and scale-dependent |

Observed benchmark runtimes should be interpreted as machine-specific wall-clock guidance, not hardware-independent guarantees.

A separate runtime-estimation table can be generated from execution logs when benchmark logs are available.

## Methodology notebooks

The methodology notebooks are not yet forced into the default Makefile workflow because they may require notebook-specific execution order, external files, or manual inspection.

Relevant notebooks are:

    methodology/imdb_methodology.ipynb
    methodology/fiben_methodology.ipynb
    methodology/ldbc_snb_methodology.ipynb

If these notebooks are later validated for linear execution, additional targets can be added:

    make imdb-framework
    make fiben-framework
    make ldbc-framework
