# LDBC SNB Physical MongoDB Benchmark: SF1 and SF3

This folder contains the faithful physical MongoDB materialization and benchmark artifacts for the LDBC SNB SchemaLens experiment at SF1 and SF3.

## Scope

These results belong to the extended physical-materialization validation of SchemaLens. Unlike the earlier official-query-based benchmark execution, this run uses physical MongoDB candidate databases materialized from the generated SchemaLens candidate specifications.

The benchmark protocol follows the same measurement convention used for the physical SF0.1 run:

- 22 LDBC SNB query/update workloads
- 64 physical candidate configurations
- 2 phases: cold and hot
- 10 measured repetitions per phase
- no extra warmup repetitions
- query/write-plan summary collected for each candidate
- resource monitor files generated for each query/phase folder

In this benchmark, `cold` and `hot` are experimental phase labels aligned with the previous IMDb/FIBEN/LDBC workflow. They do not imply operating-system cache flushing unless explicitly added in a future experiment.

## Included scales

- SF1
- SF3

SF0.1 was already validated and consolidated separately. Together, SF0.1, SF1, and SF3 form the completed physical LDBC SNB benchmark set.

## Folder structure

- benchmark/ldbc_snb/physical_materialization/sf1_full_comparison_consolidated/
- benchmark/ldbc_snb/physical_materialization/sf3_full_comparison_consolidated/
- benchmark/ldbc_snb/physical_benchmark/ldbc_snb_sf1_full_10cold_10hot/consolidated/
- benchmark/ldbc_snb/physical_benchmark/ldbc_snb_sf3_full_10cold_10hot/consolidated/
- benchmark/ldbc_snb/parameter_pools/sf1_parameter_pools/
- benchmark/ldbc_snb/parameter_pools/sf3_parameter_pools/
- benchmark/ldbc_snb/scripts/build_sf1_physical_materializations.sh
- benchmark/ldbc_snb/scripts/build_sf3_physical_materializations.sh
- benchmark/ldbc_snb/scripts/run_sf1_full_10cold_10hot.sh
- benchmark/ldbc_snb/scripts/run_sf3_full_10cold_10hot.sh

## Validation summary

### SF1

- Expected query/phase folders: 44
- Existing resource_monitor.csv files: 44
- Missing folders: 0
- Missing required files: 0
- Aggregate rows: 128
- Raw rows: 1280
- Query/write-plan rows: 128
- Failed runs total: 0
- Semantic warning rows: 0
- Non-completed plan rows: 0
- COLLSCAN rows: 0
- INS rows with documents_written <= 0: 0
- Final validation: VALID_RUN = True

### SF3

- Expected query/phase folders: 44
- Existing resource_monitor.csv files: 44
- Missing folders: 0
- Missing required files: 0
- Aggregate rows: 128
- Raw rows: 1280
- Query/write-plan rows: 128
- Failed runs total: 0
- Semantic warning rows: 0
- Non-completed plan rows: 0
- COLLSCAN rows: 0
- INS rows with documents_written <= 0: 0
- Final validation: VALID_RUN = True

## Consolidated output files

Each scale contains these consolidated files:

- ldbc_snb_sf1_10cold_10hot_benchmark_aggregate_results.csv
- ldbc_snb_sf1_10cold_10hot_benchmark_raw_results.csv
- ldbc_snb_sf1_10cold_10hot_query_write_plan_summary_results.csv
- ldbc_snb_sf1_10cold_10hot_resource_monitor.csv
- ldbc_snb_sf1_10cold_10hot_query_phase_summary.csv
- ldbc_snb_sf1_10cold_10hot_global_summary.csv
- ldbc_snb_sf3_10cold_10hot_benchmark_aggregate_results.csv
- ldbc_snb_sf3_10cold_10hot_benchmark_raw_results.csv
- ldbc_snb_sf3_10cold_10hot_query_write_plan_summary_results.csv
- ldbc_snb_sf3_10cold_10hot_resource_monitor.csv
- ldbc_snb_sf3_10cold_10hot_query_phase_summary.csv
- ldbc_snb_sf3_10cold_10hot_global_summary.csv

## Notes

The SF1 IC3 parameter pool was regenerated after the first run because the original IC3 country/place parameters returned zero documents. The corrected SF1 IC3 pool uses validated person_id|India|China parameters that return documents.

The SF3 IS7 parameter pool was generated from comment_reply_of_post.post_id because the benchmark runner does not expose a public run_is7_candidate helper. The selected IDs are guaranteed to have replies in the physical SF3 database and passed the full benchmark validation with zero semantic warnings.

## Reproducibility scripts

The scripts folder contains the shell scripts used to build physical materializations and run the full 10 cold + 10 hot benchmark for SF1 and SF3.

These scripts assume the same server environment used during execution:

- MongoDB host: 127.0.0.1
- MongoDB port: 27018
- MongoDB user/password: mongo / mongo
- MongoDB auth source: admin
- LDBC SNB data paths:
  - data/sf1
  - data/sf3
