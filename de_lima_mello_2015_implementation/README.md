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

## FIBEN SF1 p95 benchmark comparison

After the query-plan comparison, we also executed a real MongoDB latency benchmark for the Lima & Mello 2015 materialization over FIBEN SF1.

The benchmark executed FIBEN read queries Q1--Q9 with:

- 3 warmup runs;
- 5 cold runs;
- 20 hot runs;
- MongoDB aggregation execution over `lmm_fiben_sf1_source_full`;
- Q10 excluded because it is an insert/update workload and requires an isolated reset/rollback strategy.

Main command:

    python de_lima_mello_2015_implementation/benchmark/fiben/run_lmm_fiben_benchmark.py \
      --db-name lmm_fiben_sf1_source_full \
      --scale sf1 \
      --queries Q1,Q2,Q3,Q4,Q5,Q6,Q7,Q8,Q9 \
      --warmup-runs 3 \
      --cold-runs 5 \
      --hot-runs 20 \
      --result-limit 1000 \
      --max-time-ms 180000

Main output folder:

    de_lima_mello_2015_implementation/results/fiben/benchmark/sf1/lmm_fiben_sf1_source_full

Important files:

    lmm_fiben_benchmark_raw_results.csv
    lmm_fiben_benchmark_aggregate_results.csv
    lmm_fiben_benchmark_manifest.json

The benchmark completed 225 executions successfully.

### Lima & Mello hot p95 results

| Query | Hot p95 ms |
|---|---:|
| Q1 | 0.309 |
| Q2 | 0.598 |
| Q3 | 0.290 |
| Q4 | 0.877 |
| Q5 | 10.276 |
| Q6 | 744.705 |
| Q7 | 0.457 |
| Q8 | 1.228 |
| Q9 | 0.352 |

### Lima & Mello vs SchemaLens p95 comparison

The p95 comparison against SchemaLens is stored in:

    de_lima_mello_2015_implementation/results/fiben/reports

Files:

    lmm_vs_schemalens_fiben_benchmark_p95_comparison_sf1.csv
    lmm_vs_schemalens_fiben_benchmark_p95_summary_sf1.csv
    lmm_vs_schemalens_fiben_benchmark_p95_report_sf1.md

Hot-phase winner summary:

| Winner | Number of queries |
|---|---:|
| Lima & Mello 2015 | 5 |
| SchemaLens | 4 |

Query-level p95 winners:

| Query | Winner | Lima & Mello p95 ms | SchemaLens p95 ms | Ratio LMM / SchemaLens |
|---|---|---:|---:|---:|
| Q1 | SchemaLens | 0.309 | 0.233 | 1.325 |
| Q2 | SchemaLens | 0.598 | 0.117 | 5.105 |
| Q3 | Lima & Mello | 0.290 | 0.435 | 0.666 |
| Q4 | Lima & Mello | 0.877 | 1.003 | 0.874 |
| Q5 | Lima & Mello | 10.276 | 37.627 | 0.273 |
| Q6 | SchemaLens | 744.705 | 0.386 | 1929.668 |
| Q7 | Lima & Mello | 0.457 | 1.187 | 0.385 |
| Q8 | SchemaLens | 1.228 | 0.864 | 1.422 |
| Q9 | Lima & Mello | 0.352 | 0.851 | 0.414 |

Main interpretation:

Lima & Mello is highly competitive on several path-oriented queries, winning Q3, Q4, Q5, Q7, and Q9 by p95 latency. However, SchemaLens is substantially stronger on Q6, where Lima & Mello reaches 744.705 ms p95 while SchemaLens reaches 0.386 ms p95. Therefore, the result is mixed: Lima & Mello provides strong local materialization benefits, but SchemaLens better controls the dominant high-cost case.

This p95 evidence complements the query-plan evidence. The query-plan comparison showed that Q6 is also the dominant problematic case for Lima & Mello, because it examines many more documents and uses COLLSCAN plus lookup over the transaction-oriented access path.

## Integrated SF1 p95 and query-plan comparison

We also generated an integrated comparison combining p95 latency and MongoDB query-plan evidence for the same SF1 comparison.

Output files:

    de_lima_mello_2015_implementation/results/fiben/reports/lmm_vs_schemalens_fiben_integrated_p95_query_plan_sf1.csv
    de_lima_mello_2015_implementation/results/fiben/reports/lmm_vs_schemalens_fiben_integrated_summary_sf1.csv
    de_lima_mello_2015_implementation/results/fiben/reports/lmm_vs_schemalens_fiben_integrated_report_sf1.md

The integrated table confirms that Lima & Mello wins five queries by hot p95 latency: Q3, Q4, Q5, Q7, and Q9. SchemaLens wins Q1, Q2, Q6, and Q8.

The most important case is Q6. Lima & Mello reaches 744.705 ms p95, while SchemaLens reaches 0.386 ms p95. The query-plan evidence explains this gap: Lima & Mello examines 22,006 documents and uses COLLSCAN plus LOOKUP, while SchemaLens examines 5,514 documents and avoids LOOKUP. Thus, although Lima & Mello is highly competitive on several path-oriented queries, SchemaLens better controls the dominant high-cost case.

Query-level integrated summary:

| Query | p95 winner | LMM p95 ms | SchemaLens p95 ms | LMM docs | SchemaLens docs | Main observation |
|---|---|---:|---:|---:|---:|---|
| Q1 | SchemaLens | 0.309 | 0.233 | 1 | 1 | Same docs; SchemaLens lower p95. |
| Q2 | SchemaLens | 0.598 | 0.117 | 4 | 4 | Same docs; LMM uses LOOKUP. |
| Q3 | Lima & Mello | 0.290 | 0.435 | 1 | 7 | LMM is more selective. |
| Q4 | Lima & Mello | 0.877 | 1.003 | 3 | 2453 | LMM avoids SchemaLens COLLSCAN case. |
| Q5 | Lima & Mello | 10.276 | 37.627 | 1 | 6718 | LMM benefits from materialized report path. |
| Q6 | SchemaLens | 744.705 | 0.386 | 22006 | 5514 | Dominant high-cost case; SchemaLens strongly better. |
| Q7 | Lima & Mello | 0.457 | 1.187 | 1 | 359 | LMM is more selective. |
| Q8 | SchemaLens | 1.228 | 0.864 | 392 | 359 | SchemaLens slightly better. |
| Q9 | Lima & Mello | 0.352 | 0.851 | 1 | 458 | LMM is more selective. |


<!-- FIBEN_SF10_LMM_COMPARISON_START -->
## FIBEN SF10 final benchmark and SchemaLens comparison

This phase extends the faithful Lima and Mello 2015 baseline from FIBEN SF1 to FIBEN SF10 and compares it against the best SchemaLens MongoDB candidate per query.

### Protocol

The final SF10 benchmark was executed with the same repetition protocol observed in the SchemaLens SF10 benchmark artifacts:

- `warmup_runs = 0`
- `cold_runs = 10`
- `hot_runs = 10`
- queries: Q1--Q9 read workload
- metric used for comparison: hot-run p95 latency
- result limit: 1000 documents
- MongoDB database: `lmm_fiben_sf10_source_full`

The final LMM SF10 benchmark produced:

- 180 raw executions
- 180 completed executions
- 90 cold executions
- 90 hot executions
- 10 cold and 10 hot executions per query
- no zero-returned hot queries

### SF10 parameter-alignment notes

Some FIBEN queries are parameter-sensitive. To make the Lima and Mello baseline comparable with SchemaLens, the runner was aligned with the SchemaLens parameter semantics:

- Q1/Q2/Q5 use IBM as the target corporation.
- Q4 uses a person with a complete `Person -> FinancialServiceAccount -> Holding -> Security -> Corporation` path.
- Q7/Q8 use IBM as the target corporation and one deterministic transaction-backed IBM security variant, avoiding artificial multiplication across SF10 replicated security identifiers.
- Q9 uses a transaction `REFERSTO` value from the transaction-based stock pool.

The final relevant parameters were:

- IBM corporation id: `2860`
- IBM security for Q7/Q8: `SF10_SEC_R01_1002518`
- Q4 person: `SF10_PERS_R01_400000035163`
- Q9 listed security id: `SF10_SEC_R01_1001538`

### Final LMM SF10 hot p95 results

| Query | LMM hot p95 ms | Mean returned documents |
|---|---:|---:|
| Q1 | 0.318401 | 1 |
| Q2 | 0.657670 | 1 |
| Q3 | 0.307812 | 1 |
| Q4 | 9.048946 | 61 |
| Q5 | 0.689555 | 24 |
| Q6 | 2944.970120 | 1000 |
| Q7 | 1.379932 | 97 |
| Q8 | 1.376053 | 87 |
| Q9 | 1.441561 | 2 |

### Lima and Mello vs SchemaLens on FIBEN SF10

SchemaLens outperformed the faithful Lima and Mello baseline in 7 out of 9 read queries. Lima and Mello was faster in 2 out of 9 queries.

| Query | Winner | LMM p95 ms | SchemaLens best p95 ms | LMM / SchemaLens | LMM returned | SchemaLens returned | Interpretation |
|---|---|---:|---:|---:|---:|---:|---|
| Q1 | SchemaLens | 0.318401 | 0.295784 | 1.076 | 1 | 1 | Near tie; same returned cardinality. |
| Q2 | SchemaLens | 0.657670 | 0.155368 | 4.233 | 1 | 1 | Clear SchemaLens win. |
| Q3 | LMM | 0.307812 | 0.899143 | 0.342 | 1 | 53.8 | LMM is faster, but returns far fewer documents. |
| Q4 | SchemaLens | 9.048946 | 4.308413 | 2.100 | 61 | 536 | SchemaLens is faster despite returning more documents. |
| Q5 | LMM | 0.689555 | 28.432783 | 0.024 | 24 | 6801 | LMM is faster, but returns far fewer documents; interpret with caution. |
| Q6 | SchemaLens | 2944.970120 | 91.474332 | 32.194 | 1000 | 100 | Strong SchemaLens win. |
| Q7 | SchemaLens | 1.379932 | 0.857698 | 1.609 | 97 | 97 | Clean SchemaLens win with aligned cardinality. |
| Q8 | SchemaLens | 1.376053 | 0.921652 | 1.493 | 87 | 88 | Clean/near-clean SchemaLens win with almost aligned cardinality. |
| Q9 | SchemaLens | 1.441561 | 1.056870 | 1.364 | 2 | 0.3 | SchemaLens win, but this is a low-cardinality parameter-pool case. |

### Interpretation

The SF10 result strengthens the baseline comparison. Under the same 10-cold/10-hot protocol, SchemaLens wins most queries and shows its strongest advantages in Q2, Q4, Q6, Q7, and Q8. The Q7 and Q8 comparison is especially important because their returned cardinalities are aligned or nearly aligned after parameter correction.

Lima and Mello wins Q3 and Q5 in raw p95 latency, but both wins require caution because the LMM execution returns substantially fewer documents than the best SchemaLens candidate. Therefore, these cases should be reported as latency wins with cardinality caveats, not as fully clean semantic wins.

### Generated artifacts

Main generated SF10 artifacts:

- `results/fiben/benchmark/sf10/lmm_fiben_sf10_source_full/lmm_fiben_benchmark_raw_results.csv`
- `results/fiben/benchmark/sf10/lmm_fiben_sf10_source_full/lmm_fiben_benchmark_aggregate_results.csv`
- `results/fiben/benchmark/sf10/lmm_fiben_sf10_source_full/lmm_fiben_benchmark_manifest.json`
- `results/fiben/comparison/sf10/lmm_vs_schemalens_sf10_hot_best.csv`
- `results/fiben/comparison/sf10/lmm_vs_schemalens_sf10_hot_best_interpreted.csv`
- `results/fiben/comparison/sf10/lmm_vs_schemalens_sf10_winner_summary.csv`
- `results/fiben/comparison/sf10/lmm_vs_schemalens_sf10_interpretation.md`
<!-- FIBEN_SF10_LMM_COMPARISON_END -->


<!-- FIBEN_SF10_QUERY_PLAN_FINAL_START -->
## FIBEN SF10 final query-plan validation

After aligning the Lima and Mello SF10 benchmark parameters with the SchemaLens benchmark semantics, the query-plan runner was rerun for Q1--Q9.

Final parameter highlights:

- IBM corporation id: `2860`
- Q4 person id: `SF10_PERS_R01_400000035163`
- Q7/Q8 IBM security id: `SF10_SEC_R01_1002518`
- Q9 listed security id: `SF10_SEC_R01_1001538`

All nine query-plan executions completed successfully. Q1, Q2, Q3, Q4, Q5, Q7, Q8, and Q9 used index scans and avoided collection scans. Q6 was the main outlier: it used a collection scan, examined 601029 documents, and reached 2790 ms in the query-plan measurement. This explains the high Q6 hot-run p95 latency observed in the final benchmark.

Generated final query-plan interpretation files:

- `results/fiben/comparison/sf10/lmm_sf10_query_plan_final_summary_interpreted.csv`
- `results/fiben/comparison/sf10/lmm_sf10_query_plan_final_summary_interpreted.md`
<!-- FIBEN_SF10_QUERY_PLAN_FINAL_END -->
