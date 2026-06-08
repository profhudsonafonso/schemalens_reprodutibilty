# SchemaLens Artifact — LDBC SNB Case Study

This README describes how to reproduce or verify the LDBC Social Network Benchmark (LDBC SNB) part of the SchemaLens evaluation.

LDBC SNB is used in the paper as an official benchmark workload. Unlike IMDb and FIBEN, which use representative workloads designed to cover generic access classes, LDBC SNB keeps the official benchmark queries unchanged. SchemaLens maps these official queries to analytical features after extracting touched entities, relationship paths, traversal depth, access type, and write operations.

The LDBC SNB case study supports reproduction of:

1. methodology execution over the LDBC SNB conceptual structure;
2. mapping of official IC, IS, and INS queries to SchemaLens analytical features;
3. MongoDB candidate generation and benchmark execution;
4. cross-scale result analysis;
5. aggregate official-workload validation used in the paper.

## Repository files

Main files for the LDBC SNB case study:

```
methodology/ldbc_snb_methodology.ipynb

benchmark/ldbc_snb/run_ldbc_snb_mongo_benchmark.py

analysis/ldbc_snb/analyze_results_sf0_1.ipynb
analysis/ldbc_snb/analyze_results_sf1.ipynb
analysis/ldbc_snb/analyze_results_sf3.ipynb
analysis/ldbc_snb/compare_scale_factors.ipynb
```

## Data availability

The raw LDBC SNB data files are not stored directly in this Git repository because of size constraints.

The official LDBC SNB dataset downloads are available from:

```
https://ldbcouncil.org/benchmarks/snb/datasets/
```

The official LDBC SNB benchmark documentation and query specifications are available from:

```
https://github.com/ldbc/ldbc_snb_docs
```

The LDBC SNB scale factors used in this paper are:

```
sf0.1
sf1
sf3
```

For each scale factor, three downloaded artifacts are needed:

* the social-network CSV data archive;
* the substitution-parameter archive;
* the generated workload/query/update stream archive.

The files used in our experiments follow this naming pattern.

### Scale factor sf0.1

```
social_network-sf0.1-CsvMergeForeign-StringDateFormatter.tar.zst
substitution_parameters-sf0.1.tar.zst
social_network-sf0.1-numpart-1.tar.zst
```

### Scale factor sf1

```
social_network-sf1-CsvMergeForeign-StringDateFormatter.tar.zst
substitution_parameters-sf1.tar.zst
social_network-sf1-numpart-1.tar.zst
```

### Scale factor sf3

```
social_network-sf3-CsvMergeForeign-StringDateFormatter.tar.zst
substitution_parameters-sf3.tar.zst
social_network-sf3-numpart-1.tar.zst
```

The `CsvMergeForeign-StringDateFormatter` archive contains the generated social-network CSV data used by the benchmark. The `substitution_parameters` archive contains the scale-specific substitution parameters used by the official workload. The `numpart-1` archive contains the generated workload stream material for a single partition.

The official query definitions are kept unchanged and are documented in the LDBC SNB specification repository.

If you use the `CsvComposite-StringDateFormatter` archive instead of the `CsvMergeForeign-StringDateFormatter` archive, update the local data path and loader configuration accordingly. The experiments reported in the paper used the merge-foreign CSV layout.

## Expected local data layout

After downloading and extracting the files, organize them locally as:

```
data/
  ldbc_snb/
    sf0_1/
      social_network-sf0.1-CsvMergeForeign-StringDateFormatter/
      substitution_parameters-sf0.1/
      social_network-sf0.1-numpart-1/

    sf1/
      social_network-sf1-CsvMergeForeign-StringDateFormatter/
      substitution_parameters-sf1/
      social_network-sf1-numpart-1/

    sf3/
      social_network-sf3-CsvMergeForeign-StringDateFormatter/
      substitution_parameters-sf3/
      social_network-sf3-numpart-1/
```

Each scale-factor folder should contain the static, dynamic, substitution-parameter, and workload-stream files required by the benchmark runner.

The benchmark runner receives the scale-factor folder through the `--data-dir` argument.

## Official workload used in the paper

The official workload queries evaluated in the paper are:

```
IC1--IC7
IS1--IS7
INS1--INS8
```

These queries are kept unchanged and mapped to SchemaLens analytical features before activation.

In the paper, LDBC SNB is reported as an aggregate official-workload result rather than as one representative semantic-family case. This is because the official benchmark workload contains multiple query types and is not rewritten into generic representative queries.

## Methodology reproduction

Run the notebook:

```
methodology/ldbc_snb_methodology.ipynb
```

This notebook documents the SchemaLens methodology execution for LDBC SNB, including:

* conceptual view preparation;
* official query mapping;
* touched-entity extraction;
* relationship-path extraction;
* analytical matrix generation;
* activation of MongoDB configuration families;
* benchmark-planning artifacts.

## Benchmark reproduction

The benchmark runner is:

```
benchmark/ldbc_snb/run_ldbc_snb_mongo_benchmark.py
```

Example command for `sf0.1`:

```
python benchmark/ldbc_snb/run_ldbc_snb_mongo_benchmark.py \
  --data-dir data/ldbc_snb/sf0_1 \
  --artifacts-dir path/to/ldbc_snb/benchmark_artifacts/ldbc_snb_mongo_configurations \
  --results-dir results/ldbc_snb/sf0_1 \
  --scale-label sf0.1 \
  --mongo-host 127.0.0.1 \
  --mongo-port 27018 \
  --batch-size 5000 \
  --force-rebuild-db
```

Repeat the execution for:

```
sf0.1
sf1
sf3
```

For each scale factor, change the scale-specific arguments:

```
--data-dir
--results-dir
--scale-label
```

MongoDB can be started from the repository root with:

```
docker compose up -d
```

The default MongoDB port is:

```
27018
```

## Faithful physical materialization extension

In addition to the original benchmark runner, this repository includes a reproducibility record for the faithful MongoDB physical materialization of the LDBC SNB SF0.1 candidate space.

The original SchemaLens evaluation logic is preserved: `primary` and `secondary_affected` candidates form the activated family used for DSR, while `control` candidates are part of the broader benchmarked comparison space used for Top-1 preservation, near-best preservation, activated regret, and primary regret.

The generated Phase 1 manifests are stored in:

    analysis/generated/physical_materialization/ldbc_snb/sf0_1/

The final SF0.1 physical comparison manifest is:

    analysis/generated/physical_materialization/ldbc_snb/sf0_1/phase1C_full_comparison/physical_materialization_manifest.csv

The corresponding documentation is available in:

    docs/ldbc_snb_physical_materialization.md

This extension does not change the analytical matrix, activation rules, candidate identifiers, or benchmark groups. It only replaces the previous simplified execution layer with faithful MongoDB physical materializations for the generated candidates.

## Faithful physical benchmark phase 2 status

The repository also includes the current Phase 2 validation outputs for the faithful MongoDB physical benchmark on LDBC SNB SF0.1.

The Phase 2 runner executes each candidate through its candidate-specific physical access path, separates timed p95 measurement from MongoDB explain, and records resource-monitor logs for debugging.

Current validated outputs:

    analysis/generated/physical_benchmark/ldbc_snb/sf0_1/ic7_pilot_validated/
    analysis/generated/physical_benchmark/ldbc_snb/sf0_1/is_validated/

Documentation:

    docs/ldbc_snb_physical_benchmark_phase2.md

Current status:

    IC7 pilot validated
    IS1--IS7 validated
    failed_runs_total = 0 for the validated IS group
    semantic_warning_rows = 0 for the validated IS group
    collscan_rows = 0 for the validated IS group

These are pilot validation runs. Final larger p95 runs will be executed after IC1--IC6 and INS1--INS8 are validated.

## Result analysis

The main LDBC SNB analysis notebooks are:

```
analysis/ldbc_snb/analyze_results_sf0_1.ipynb
analysis/ldbc_snb/analyze_results_sf1.ipynb
analysis/ldbc_snb/analyze_results_sf3.ipynb
analysis/ldbc_snb/compare_scale_factors.ipynb
```

These files support the LDBC SNB results reported in the paper, including:

* design-space reduction;
* Top-1 preservation;
* near-best preservation;
* activated-family regret;
* primary, secondary, and control winners;
* cross-scale comparison across sf0.1, sf1, and sf3.

## Paper connection

The LDBC SNB artifact supports the official-workload validation in the cross-dataset evaluation.

The aggregate paper result summarizes:

```
22 official queries per scale
3 scale factors
66 query-scale cases
65/66 Top-1 preservation
71.4% average design-space reduction
0.008 mean activated regret
```

This means that SchemaLens was evaluated on 22 official LDBC SNB queries across three scale factors. Across the 66 query-scale cases, the activated families preserved the best observed configuration in 65 cases.

In the short-paper Table 1, LDBC SNB is represented as an official workload aggregate rather than as an individual representative query.

## Lightweight verification

To verify the LDBC SNB part of the paper without rerunning the full benchmark, use the provided aggregate benchmark outputs:

```
analysis/ldbc_snb/benchmark_aggregate_results_ldbc_snb_sf0_1.csv
analysis/ldbc_snb/benchmark_aggregate_results_ldbc_snb_sf1.csv
analysis/ldbc_snb/benchmark_aggregate_results_ldbc_snb_sf3.csv
```

These files contain the aggregate cold and hot benchmark results for the three LDBC SNB scale factors used in the paper.

They support verification of:

* the official IC1--IC7, IS1--IS7, and INS1--INS8 workload results;
* p95 latency;
* Top-1 preservation;
* near-best preservation within the 5% threshold;
* activated regret;
* primary regret;
* control-winner cases;
* cross-scale behavior.

The LDBC SNB benchmark queries are kept unchanged. SchemaLens maps them to analytical features after extracting touched entities, relationship paths, traversal depth, access type, and write operations.

Full benchmark reproduction is supported, but it is more time-consuming because it requires loading LDBC SNB scale-factor data, materializing MongoDB candidate configurations, and executing repeated benchmark runs over the official workload.

## Notes

The LDBC SNB scale-factor data are large and are therefore distributed through the official LDBC dataset repository rather than stored directly in this Git repository.

This Git repository contains the methodology notebook, benchmark runner, aggregate outputs, and analysis notebooks needed to reproduce or verify the LDBC SNB part of the paper once the official data archives have been downloaded.

## LDBC SNB framework artifacts

The LDBC SNB framework step is implemented by:

    methodology/ldbc_snb_methodology.ipynb
    methodology/run_ldbc_snb_framework_notebook.py

To regenerate the LDBC SNB MongoDB benchmark configuration artifacts from the LDBC SNB SF0.1 data, run:

    make ldbc-framework LDBC_DATA_DIR=<path-to-ldbc-snb-sf0.1-data> LDBC_FRAMEWORK_SCALE=sf0.1

The expected `LDBC_DATA_DIR` should contain the LDBC SNB SF0.1 folders used by the framework, including:

    social_network-sf0.1-CsvMergeForeign-StringDateFormatter/
    social_network-sf0.1-numpart-1/
    substitution_parameters-sf0.1/

The generated benchmark artifacts are written to:

    benchmark/ldbc_snb/ldbc_snb_mongo_configurations/

The main benchmark input files are:

    benchmark_execution_plan.csv
    mongodb_candidate_specs_by_candidate_id.json
    benchmark_manifest.json

Additional trace artifacts are written to:

    analysis/generated/framework/ldbc_snb/

The LDBC SNB benchmark runner consumes these artifacts through `LDBC_ARTIFACTS_DIR`, whose default is:

    benchmark/ldbc_snb/ldbc_snb_mongo_configurations

