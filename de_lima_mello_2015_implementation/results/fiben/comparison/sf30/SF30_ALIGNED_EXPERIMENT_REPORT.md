# Lima and Mello 2015 Baseline on FIBEN SF30

## Aligned benchmark and comparison with SchemaLens

This report documents the corrected and aligned FIBEN SF30 experiment for the faithful implementation of the workload-driven NoSQL logical design method proposed by Lima and Mello.

The SF30 run uses the same parameter-alignment strategy adopted after the SF10 and SF1 corrections. In particular, the runner was updated to prefer active-scale transaction references, so SF30 uses `SF30_SEC_R01_*` identifiers instead of accidentally selecting `SF10_SEC_R01_*` identifiers when both exist in the materialized database.

## 1. Goal

The goal of this SF30 experiment is to compare the faithful Lima and Mello baseline against SchemaLens at a larger FIBEN scale.

The comparison uses:

- the same FIBEN conceptual interpretation used in the SchemaLens workflow;
- the full Lima and Mello MongoDB materialization for SF30;
- aligned query parameters for Q1--Q9;
- the same 10-cold and 10-hot repetition protocol observed in the SchemaLens SF30 artifacts;
- hot-run p95 latency as the main comparison metric.

## 2. Database and main artifacts

Lima and Mello MongoDB database:

- lmm_fiben_sf30_source_full

Main benchmark outputs:

- de_lima_mello_2015_implementation/results/fiben/benchmark/sf30/lmm_fiben_sf30_source_full/lmm_fiben_benchmark_raw_results.csv
- de_lima_mello_2015_implementation/results/fiben/benchmark/sf30/lmm_fiben_sf30_source_full/lmm_fiben_benchmark_aggregate_results.csv
- de_lima_mello_2015_implementation/results/fiben/benchmark/sf30/lmm_fiben_sf30_source_full/lmm_fiben_benchmark_manifest.json

Main query-plan outputs:

- de_lima_mello_2015_implementation/results/fiben/query_plan/sf30/lmm_fiben_sf30_source_full/

Main comparison outputs:

- de_lima_mello_2015_implementation/results/fiben/comparison/sf30/lmm_vs_schemalens_sf30_hot_best_aligned.csv
- de_lima_mello_2015_implementation/results/fiben/comparison/sf30/lmm_vs_schemalens_sf30_winner_summary_aligned.csv
- de_lima_mello_2015_implementation/results/fiben/comparison/sf30/lmm_vs_schemalens_sf30_interpretation_aligned.md

## 3. Source profile and materialization

The SF30 source profile was generated without row counting because the source CSV directory is large.

Source profile status:

| Metric | Value |
|---|---:|
| Required views | 15 |
| Matched views | 15 |
| Unmatched views | 0 |
| Missing required columns | 0 |

The full materialization completed successfully.

Main collection counts:

| Collection | Documents |
|---|---:|
| lmm_corporation | 69721 |
| lmm_disclosure | 6244741 |
| lmm_financial_report | 1449031 |
| lmm_financial_service_account | 2918101 |
| lmm_listed_security | 82351 |
| lmm_person | 1503001 |
| lmm_report_element | 81200841 |
| lmm_security | 82351 |
| lmm_sell_transaction | 19500001 |
| lmm_statement_element | 13313821 |
| lmm_transaction | 19500001 |
| _src_fiben_holdings | 16034191 |

One embedding failed due to a MongoDB aggregation timeout:

- transaction_refers_to_listed_security

This does not block the benchmark because Q7, Q8, and Q9 use transaction `REFERSTO` identifiers directly.

## 4. Parameter alignment

The final SF30 parameters were:

| Parameter | Value |
|---|---|
| IBM corporation id | 2860 |
| IBM ticker | IBM |
| Q4 person id | SF30_PERS_R01_400000035163 |
| Account id | 150000000000 |
| Q7/Q8 IBM security id | SF30_SEC_R01_1002518 |
| Q9 listed security id | SF30_SEC_R01_1001538 |

The active-scale correction is important because SF30 contains both `SF10_SEC_R01_*` and `SF30_SEC_R01_*` transaction references. The final runner correctly selects `SF30_SEC_R01_*` references for SF30.

## 5. Query-plan validation

The final SF30 query-plan execution completed Q1--Q9 successfully.

| Query | Status | Returned accumulated | Docs examined | Keys examined | Max time ms | IXSCAN | COLLSCAN | GROUP |
|---|---|---:|---:|---:|---:|---|---|---|
| Q1 | completed | 5 | 1 | 1 | 0 | true | false | false |
| Q2 | completed | 35 | 4 | 4 | 0 | true | false | false |
| Q3 | completed | 5 | 1 | 1 | 0 | true | false | false |
| Q4 | completed | 317 | 62 | 62 | 5 | true | false | false |
| Q5 | completed | 77 | 1 | 1 | 0 | true | false | false |
| Q6 | completed | 2030495 | 5069820 | 1000 | 21975 | false | true | false |
| Q7 | completed | 1268 | 179 | 179 | 1 | true | false | true |
| Q8 | completed | 1428 | 179 | 179 | 0 | true | false | true |
| Q9 | completed | 2513 | 458 | 458 | 2 | true | false | true |

Q6 is the main query-plan outlier. It performs a collection scan and examines 5069820 documents. This explains why Q6 is also the slowest Lima and Mello query in the benchmark.

## 6. Benchmark protocol

The final benchmark used:

| Parameter | Value |
|---|---:|
| Warmup runs | 0 |
| Cold runs per query | 10 |
| Hot runs per query | 10 |
| Number of read queries | 9 |
| Result limit | 1000 |

Benchmark validation:

| Metric | Value |
|---|---:|
| Raw executions | 180 |
| Completed executions | 180 |
| Cold executions | 90 |
| Hot executions | 90 |
| Zero-returned hot queries | 0 |

## 7. Final Lima and Mello SF30 hot results

| Query | Completed | Mean ms | Median ms | P95 ms | Max ms | Mean returned |
|---|---:|---:|---:|---:|---:|---:|
| Q1 | 10 | 0.168466 | 0.164815 | 0.189443 | 0.191522 | 1.0 |
| Q2 | 10 | 0.486641 | 0.492837 | 0.520801 | 0.528161 | 1.0 |
| Q3 | 10 | 0.230111 | 0.151871 | 0.562268 | 0.743399 | 1.0 |
| Q4 | 10 | 8.839228 | 8.847326 | 8.899998 | 8.905172 | 61.0 |
| Q5 | 10 | 0.674876 | 0.690832 | 0.715147 | 0.717956 | 24.0 |
| Q6 | 10 | 21227.471463 | 20659.300486 | 24358.562708 | 25857.949024 | 1000.0 |
| Q7 | 10 | 1.394046 | 1.389193 | 1.456658 | 1.464542 | 97.0 |
| Q8 | 10 | 1.370263 | 1.358410 | 1.428464 | 1.450021 | 87.0 |
| Q9 | 10 | 1.956004 | 1.966729 | 2.007336 | 2.034292 | 2.0 |

## 8. Lima and Mello vs SchemaLens on SF30

### 8.1 Winner summary

| Winner | Number of queries |
|---|---:|
| SchemaLens | 5 |
| Lima and Mello | 4 |

SchemaLens wins 5 out of 9 read queries.

Lima and Mello wins 4 out of 9 read queries.

### 8.2 Per-query comparison

| Query | Winner | LMM p95 ms | SchemaLens p95 ms | LMM / SchemaLens | LMM returned | SchemaLens returned | Cardinality flag | SchemaLens group | SchemaLens class |
|---|---|---:|---:|---:|---:|---:|---|---|---|
| Q1 | Lima and Mello | 0.189443 | 0.224772 | 0.842823 | 1.0 | 1.0 | cardinality aligned | primary | G0 |
| Q2 | SchemaLens | 0.520801 | 0.250701 | 2.077379 | 1.0 | 1.0 | cardinality aligned | secondary affected | G9 |
| Q3 | Lima and Mello | 0.562268 | 1.652037 | 0.340348 | 1.0 | 149.8 | LMM returns less | primary | G5 |
| Q4 | Lima and Mello | 8.899998 | 17.142359 | 0.519182 | 61.0 | 1608.0 | LMM returns less | primary | G4 |
| Q5 | Lima and Mello | 0.715147 | 45.217182 | 0.015816 | 24.0 | 6801.0 | LMM returns less | control | CONTROL |
| Q6 | SchemaLens | 24358.562708 | 418.834830 | 58.157920 | 1000.0 | 100.0 | LMM returns more | primary | G3 |
| Q7 | SchemaLens | 1.456658 | 1.322278 | 1.101627 | 97.0 | 97.0 | cardinality aligned | primary | G3 |
| Q8 | SchemaLens | 1.428464 | 1.292882 | 1.104868 | 87.0 | 88.0 | cardinality aligned | primary | G5 |
| Q9 | SchemaLens | 2.007336 | 1.223861 | 1.640167 | 2.0 | 0.3 | LMM returns more | secondary affected | G7 |

## 9. Cardinality analysis

The cleanest SF30 comparisons are Q1, Q2, Q7, and Q8.

| Query | Winner | LMM p95 ms | SchemaLens p95 ms | LMM returned | SchemaLens returned |
|---|---|---:|---:|---:|---:|
| Q1 | Lima and Mello | 0.189443 | 0.224772 | 1.0 | 1.0 |
| Q2 | SchemaLens | 0.520801 | 0.250701 | 1.0 | 1.0 |
| Q7 | SchemaLens | 1.456658 | 1.322278 | 97.0 | 97.0 |
| Q8 | SchemaLens | 1.428464 | 1.292882 | 87.0 | 88.0 |

SchemaLens wins 3 out of 4 aligned-cardinality comparisons.

Lima and Mello wins Q1, but the difference is small in absolute terms. SchemaLens wins Q2, Q7, and Q8 under aligned or nearly aligned cardinality.

## 10. Query-level interpretation

### Q1

Q1 is a clean Lima and Mello win. Both methods return one document, and Lima and Mello is slightly faster.

### Q2

Q2 is a clean SchemaLens win. Both methods return one document, and SchemaLens is about 2.08 times faster.

### Q3

Q3 is a Lima and Mello latency win, but with a strong cardinality caveat. Lima and Mello returns 1 document, while SchemaLens returns 149.8 documents on average.

### Q4

Q4 is a Lima and Mello latency win, but with a strong cardinality caveat. Lima and Mello returns 61 documents, while SchemaLens returns 1608 documents on average.

### Q5

Q5 is a Lima and Mello latency win, but with a major cardinality caveat. Lima and Mello returns 24 documents, while SchemaLens returns 6801 documents.

### Q6

Q6 is the strongest SchemaLens win. Lima and Mello reaches 24358.563 ms p95, while SchemaLens reaches 418.835 ms p95. The query-plan confirms that Lima and Mello uses a collection scan and examines more than 5 million documents.

### Q7

Q7 is a clean SchemaLens win. Both methods return 97 documents, and SchemaLens is about 1.10 times faster.

### Q8

Q8 is a clean or near-clean SchemaLens win. Lima and Mello returns 87 documents and SchemaLens returns 88 documents. SchemaLens is about 1.10 times faster.

### Q9

Q9 is a SchemaLens win, but it is a low-cardinality case. Lima and Mello returns 2 documents, while SchemaLens returns 0.3 documents on average.

## 11. Main conclusions

The aligned SF30 experiment leads to four conclusions.

### 11.1 SF30 is more balanced than SF1 and SF10

SchemaLens wins 5 out of 9 queries, while Lima and Mello wins 4 out of 9 queries.

### 11.2 SchemaLens still wins most aligned-cardinality cases

Among aligned-cardinality cases, SchemaLens wins Q2, Q7, and Q8. Lima and Mello wins Q1.

### 11.3 Lima and Mello wins Q3, Q4, and Q5 with cardinality caveats

Lima and Mello is faster in Q3, Q4, and Q5, but it returns substantially fewer documents than SchemaLens in all three cases.

### 11.4 Q6 remains the strongest SchemaLens advantage

Q6 strongly favors SchemaLens. Lima and Mello reaches 24358.563 ms p95 and uses a collection scan, while SchemaLens reaches 418.835 ms p95.

## 12. Recommended paper interpretation

At SF30, the comparison becomes more balanced: SchemaLens wins 5 out of 9 queries and the faithful Lima and Mello baseline wins 4. However, the clean aligned-cardinality cases still favor SchemaLens in 3 out of 4 queries. Lima and Mello wins Q1 and is faster in Q3--Q5, but the latter three cases return substantially fewer documents and must be interpreted as latency wins with cardinality caveats. The strongest SchemaLens advantage remains Q6, where Lima and Mello performs a collection scan, examines more than 5 million documents, and is 58 times slower at hot p95.

## 13. Final status

| Item | Status |
|---|---|
| SF30 source profile | completed |
| SF30 column validation | completed |
| SF30 materialization | completed |
| Active-scale parameter correction | completed |
| SF30 query-plan rerun | completed |
| SF30 final benchmark rerun | completed |
| SF30 LMM vs SchemaLens comparison | completed |

The aligned FIBEN SF30 Lima and Mello experiment is complete.
