# de Lima & Mello 2015 Implementation for FIBEN

This folder implements and evaluates the workload-driven logical design approach proposed by de Lima and Mello (2015) for NoSQL document databases.

The immediate goal is to use this implementation as a related-work baseline for the SchemaLens/DKE comparison on FIBEN.

A possible future work is to transform the standalone implementation and benchmark validation of the Lima & Mello method into a separate implementation/validation paper.

## Current scope

The implementation is organized in phases.

## Phase 1: Logical-decision reproduction

The first phase focuses on reproducing how the method generates a NoSQL document logical schema from:

- EER conceptual schema;
- volume/load information;
- workload operations;
- General Access Frequency (GAF);
- Minimal Access Frequency (MAF);
- hierarchy conversion rules;
- relationship conversion rules.

Expected outputs:

```text
generated/fiben/lmm_fiben_volume_profile_sf1.json
generated/fiben/lmm_fiben_volume_profile_sf10.json
generated/fiben/lmm_fiben_volume_profile_sf30.json

generated/fiben/lmm_fiben_gaf_maf_sf1.csv
generated/fiben/lmm_fiben_gaf_maf_sf10.csv
generated/fiben/lmm_fiben_gaf_maf_sf30.csv

generated/fiben/lmm_fiben_workload_access_paths.csv
generated/fiben/lmm_fiben_logical_schema_sf1.json
generated/fiben/lmm_fiben_logical_schema_sf10.json
generated/fiben/lmm_fiben_logical_schema_sf30.json
```

## Phase 2: MongoDB physical materialization

The second phase will materialize the generated logical schema in MongoDB.

Protected databases that must not be dropped:

```text
fiben_exec_sf1
fiben_exec_sf10
fiben_exec_sf30

dbsr_fiben_sf1_source_full
dbsr_fiben_sf10_source_full
dbsr_fiben_sf30_source_full
```

New Lima & Mello databases should use names such as:

```text
lmm_fiben_sf1_source_full
lmm_fiben_sf10_source_full
lmm_fiben_sf30_source_full
```

## Phase 3: Benchmark and query-plan comparison

The third phase will execute FIBEN Q1-Q9, skip Q10 for read-query query-plan comparison, and compare the Lima & Mello baseline against SchemaLens using:

- hot p95 latency;
- returned-count parity;
- regret;
- SchemaLens wins;
- Lima & Mello wins;
- near-best within 5%;
- MongoDB explain/query-plan metrics.

## Methodological notes

The original Lima & Mello method focuses on logical design.

The MongoDB implementation layer, including indexes and physical materialization, is treated as an execution layer required for empirical comparison.

The comparison with SchemaLens is scientifically useful because Lima & Mello generates a workload-driven optimized logical schema, while SchemaLens reduces the design space to explainable candidate families and then benchmarks alternatives.

## Repository safety notes

Do not drop or overwrite existing SchemaLens or DBSR databases.

Do not use `git add .`.

Before committing, run:

```bash
python -m py_compile de_lima_mello_2015_implementation/src/*.py

git status
git diff --stat

git diff --name-only -z | xargs -0 grep -nE "Hudson|profhudson|batistah|/home/|/afs/|mongo:mongo|token|secret" || true
```

If the grep only reports this README safety command, it is an acceptable false positive.

If local paths or credentials appear in generated files, sanitize them before committing.

## FIBEN SF1 MongoDB materialization and query-plan comparison

This phase implements and validates the Lima & Mello 2015 workload-driven document-design baseline over FIBEN SF1, then compares its MongoDB query-plan evidence with the best SchemaLens FIBEN query-plan candidates.

### Materialized database

The full SF1 Lima & Mello materialization was loaded into:

    lmm_fiben_sf1_source_full

The materialization completed successfully with 14 MongoDB collections. All 9 Rule-5 embedding edges completed, and 3 Rule-6 reference fields were added. The bridge reference for `corporation_has_listed_security` was intentionally preserved as a bridge/reference case.

Main output folder:

    de_lima_mello_2015_implementation/results/fiben/materialization/sf1/lmm_fiben_sf1_source_full

Important files:

    lmm_materialization_load_summary.csv
    lmm_materialization_embedding_summary.csv
    lmm_materialization_reference_summary.csv
    lmm_materialization_collection_counts.csv
    lmm_materialization_report.json

### Lima & Mello query-plan runner

The Lima & Mello query-plan runner executed MongoDB `explain("executionStats")` for FIBEN read queries Q1--Q9. Q10 is excluded because it is an insert/update workload.

Main command:

    python de_lima_mello_2015_implementation/benchmark/fiben/run_lmm_fiben_query_plan.py \
      --db-name lmm_fiben_sf1_source_full \
      --scale sf1 \
      --queries Q1,Q2,Q3,Q4,Q5,Q6,Q7,Q8,Q9 \
      --result-limit 1000 \
      --max-time-ms 180000

Main output folder:

    de_lima_mello_2015_implementation/results/fiben/query_plan/sf1/lmm_fiben_sf1_source_full

The runner completed 9/9 read queries.

### SchemaLens evidence used for comparison

SchemaLens query-plan artifacts were copied from:

    /home/hudson/Documents/framework_test/fiben/analysis/generated/query_plan/fiben

Local copy:

    de_lima_mello_2015_implementation/generated/fiben/schemalens_query_plan_full

Files:

    fiben_query_plan_best_by_estimated_bytes.csv
    fiben_query_plan_compact_candidates.csv
    fiben_query_plan_components_all.csv
    fiben_query_plan_summary_all.csv

The comparison uses:

- `fiben_query_plan_best_by_estimated_bytes.csv` to identify the best SchemaLens candidate per query and scale.
- `fiben_query_plan_compact_candidates.csv` to collect aggregate docs/keys and candidate-level flags.
- `fiben_query_plan_components_all.csv` to recover component-level execution evidence such as `has_LOOKUP`, `has_IXSCAN`, `has_COLLSCAN`, `has_FETCH`, `has_SORT`, `has_GROUP`, and pipeline evidence.

### SF1 comparison summary

Final comparison folder:

    de_lima_mello_2015_implementation/results/fiben/reports

Files:

    lmm_vs_schemalens_fiben_query_plan_full_comparison_sf1.csv
    lmm_vs_schemalens_fiben_query_plan_full_summary_sf1.csv
    lmm_vs_schemalens_fiben_query_plan_full_report_sf1.md

Summary:

| Method | Total docs examined | Total keys examined | IXSCAN queries | COLLSCAN queries | LOOKUP queries | GROUP queries | UNWIND queries |
|---|---:|---:|---:|---:|---:|---:|---:|
| Lima & Mello 2015 | 22,410 | 1,889 | 8 | 1 | 3 | 3 | 6 |
| SchemaLens | 15,866 | 14,938 | 9 | 2 | 0 | 3 | 0 |

Query-level interpretation:

- Q1: both methods examine 1 document and avoid COLLSCAN.
- Q2: both methods examine 4 documents and avoid COLLSCAN; Lima & Mello uses MongoDB `$lookup`, while the selected SchemaLens plan does not.
- Q3: Lima & Mello examines fewer documents: 1 vs 7.
- Q4: Lima & Mello examines fewer documents: 3 vs 2446; SchemaLens uses COLLSCAN in the selected best-by-estimated-bytes plan.
- Q5: Lima & Mello examines fewer documents: 1 vs 6718.
- Q6: SchemaLens examines fewer documents: 5514 vs 22006; both use COLLSCAN, but Lima & Mello also uses `$lookup`.
- Q7: Lima & Mello examines fewer documents: 1 vs 359.
- Q8: SchemaLens examines fewer documents: 359 vs 392.
- Q9: Lima & Mello examines fewer documents: 1 vs 458.

Main interpretation:

Lima & Mello's workload-driven materialization produces very selective access paths for several local or path-oriented queries. However, its faithful SF1 materialization is less robust for Q6, where the query starts from transactions and the plan falls back to COLLSCAN over a larger transaction collection. SchemaLens also uses COLLSCAN in Q6, but examines about four times fewer documents. Therefore, this comparison should be reported as a mixed result: Lima & Mello is highly competitive and sometimes better for specific path-oriented reads, while SchemaLens is stronger on the dominant high-cost Q6 case and has a lower total document-examination count across Q1--Q9.
