# Lima and Mello 2015 Baseline on FIBEN SF1

## Aligned benchmark and comparison with SchemaLens

This report documents the corrected and aligned FIBEN SF1 experiment for the faithful implementation of the workload-driven NoSQL logical design method proposed by Lima and Mello.

The original SF1 baseline experiment was valid as an initial implementation, but after the SF10 alignment phase we corrected the parameter-selection logic to make the Lima and Mello runner closer to the SchemaLens benchmark semantics. Therefore, SF1 was re-executed using the same aligned parameter strategy used in SF10.

## 1. Goal

The goal of this aligned SF1 experiment is to compare the faithful Lima and Mello baseline against SchemaLens under a methodologically consistent setup.

The comparison uses:

- the same FIBEN conceptual interpretation used in the SchemaLens workflow;
- the same MongoDB materialized Lima and Mello baseline database;
- aligned query parameters for parameter-sensitive queries;
- the same 10-cold and 10-hot repetition protocol observed in the SchemaLens SF1 artifacts;
- hot-run p95 latency as the main comparison metric.

## 2. Database and main artifacts

Lima and Mello MongoDB database:

- lmm_fiben_sf1_source_full

Main benchmark outputs:

- de_lima_mello_2015_implementation/results/fiben/benchmark/sf1/lmm_fiben_sf1_source_full/lmm_fiben_benchmark_raw_results.csv
- de_lima_mello_2015_implementation/results/fiben/benchmark/sf1/lmm_fiben_sf1_source_full/lmm_fiben_benchmark_aggregate_results.csv
- de_lima_mello_2015_implementation/results/fiben/benchmark/sf1/lmm_fiben_sf1_source_full/lmm_fiben_benchmark_manifest.json

Main query-plan outputs:

- de_lima_mello_2015_implementation/results/fiben/query_plan/sf1/lmm_fiben_sf1_source_full/

Main comparison outputs:

- de_lima_mello_2015_implementation/results/fiben/comparison/sf1/lmm_vs_schemalens_sf1_hot_best_aligned.csv
- de_lima_mello_2015_implementation/results/fiben/comparison/sf1/lmm_vs_schemalens_sf1_winner_summary_aligned.csv
- de_lima_mello_2015_implementation/results/fiben/comparison/sf1/lmm_vs_schemalens_sf1_interpretation_aligned.md

## 3. Parameter alignment

After the SF10 experiment, the Lima and Mello query runner was corrected to use type-aware and scale-aware parameters.

This was necessary because SF1 stores several identifiers as numeric values, while SF10 stores some identifiers using replicated string prefixes.

### 3.1 SF1 identifier type correction

The SF1 MongoDB database stores IBM and security identifiers as integers.

| Field | Value | Type |
|---|---:|---|
| CORPORATIONID | 2860 | int |
| ISPROVIDEDBY | 2860 | int |
| REFERSTO for IBM security | 1002518 | int |
| REFERSTO for Q9 stock | 1001538 | int |

Before correction, some parameters were converted to strings. This caused Q1, Q2, Q5, Q7, and Q8 to return zero in query-plan validation. The runner was corrected to preserve the original MongoDB identifier type.

### 3.2 Final SF1 parameters

| Parameter | Value |
|---|---:|
| IBM corporation id | 2860 |
| IBM ticker | IBM |
| Q4 person id | 400000035163 |
| Q7/Q8 IBM security id | 1002518 |
| Q9 listed security id | 1001538 |
| Account id | 150000000000 |

## 4. Query-plan validation

After applying the type-aware parameter correction, the SF1 query-plan runner was re-executed for Q1--Q9.

### 4.1 Final SF1 query-plan summary

| Query | Status | Returned accumulated | Docs examined | Keys examined | Max time ms | IXSCAN | COLLSCAN | GROUP |
|---|---|---:|---:|---:|---:|---|---|---|
| Q1 | completed | 5 | 1 | 1 | 0 | true | false | false |
| Q2 | completed | 35 | 4 | 4 | 4 | true | false | false |
| Q3 | completed | 5 | 1 | 1 | 0 | true | false | false |
| Q4 | completed | 317 | 94 | 94 | 16 | true | false | false |
| Q5 | completed | 77 | 1 | 1 | 3 | true | false | false |
| Q6 | completed | 11048 | 22006 | 1485 | 242 | false | true | false |
| Q7 | completed | 1268 | 179 | 179 | 1 | true | false | true |
| Q8 | completed | 1428 | 179 | 179 | 1 | true | false | true |
| Q9 | completed | 2513 | 458 | 458 | 2 | true | false | true |

### 4.2 Query-plan interpretation

All Q1--Q9 query-plan executions completed successfully.

The type-aware correction fixed the previous zero-return issue in Q1, Q2, Q5, Q7, and Q8. Q7 and Q8 now use the IBM security identifier 1002518, which matches transaction references in the SF1 database.

Q6 remains the main query-plan outlier. It uses a collection scan, examines 22006 documents, and does not use an index scan. This explains why Q6 is also the slowest Lima and Mello query in the final benchmark.

## 5. Benchmark protocol

The SchemaLens SF1 artifacts show the same protocol used in SF10.

| Phase | Raw rows |
|---|---:|
| cold | 600 |
| hot | 600 |

The aggregate file contains:

| Phase | Aggregate rows |
|---|---:|
| cold | 60 |
| hot | 60 |

Thus, 600 raw rows divided by 60 aggregate rows indicates 10 repetitions.

The final Lima and Mello SF1 aligned benchmark used:

| Parameter | Value |
|---|---:|
| Warmup runs | 0 |
| Cold runs per query | 10 |
| Hot runs per query | 10 |
| Number of read queries | 9 |
| Result limit | 1000 |

## 6. Final SF1 benchmark validation

The final aligned SF1 benchmark produced:

| Metric | Value |
|---|---:|
| Queries | 9 |
| Raw executions | 180 |
| Completed executions | 180 |
| Cold executions | 90 |
| Hot executions | 90 |
| Cold executions per query | 10 |
| Hot executions per query | 10 |
| Zero-returned hot queries | 0 |

### 6.1 Count per query and phase

| Query | Cold | Hot |
|---|---:|---:|
| Q1 | 10 | 10 |
| Q2 | 10 | 10 |
| Q3 | 10 | 10 |
| Q4 | 10 | 10 |
| Q5 | 10 | 10 |
| Q6 | 10 | 10 |
| Q7 | 10 | 10 |
| Q8 | 10 | 10 |
| Q9 | 10 | 10 |

### 6.2 Returned documents by query

| Query | Count | Min | Max | Mean |
|---|---:|---:|---:|---:|
| Q1 | 20 | 1 | 1 | 1.0 |
| Q2 | 20 | 1 | 1 | 1.0 |
| Q3 | 20 | 1 | 1 | 1.0 |
| Q4 | 20 | 61 | 61 | 61.0 |
| Q5 | 20 | 24 | 24 | 24.0 |
| Q6 | 20 | 1000 | 1000 | 1000.0 |
| Q7 | 20 | 97 | 97 | 97.0 |
| Q8 | 20 | 87 | 87 | 87.0 |
| Q9 | 20 | 2 | 2 | 2.0 |

## 7. Final Lima and Mello SF1 hot results

| Query | Completed | Mean ms | Median ms | P95 ms | Max ms | Mean returned |
|---|---:|---:|---:|---:|---:|---:|
| Q1 | 10 | 0.317772 | 0.311815 | 0.338933 | 0.342812 | 1.0 |
| Q2 | 10 | 0.611923 | 0.607061 | 0.636918 | 0.638514 | 1.0 |
| Q3 | 10 | 0.308819 | 0.302807 | 0.333562 | 0.334165 | 1.0 |
| Q4 | 10 | 13.279074 | 13.282140 | 13.401979 | 13.426539 | 61.0 |
| Q5 | 10 | 9.518727 | 9.538306 | 9.564318 | 9.567968 | 24.0 |
| Q6 | 10 | 647.605049 | 659.837838 | 737.187028 | 744.679515 | 1000.0 |
| Q7 | 10 | 1.366284 | 1.376769 | 1.413641 | 1.433865 | 97.0 |
| Q8 | 10 | 1.184986 | 1.198937 | 1.257368 | 1.281821 | 87.0 |
| Q9 | 10 | 1.271536 | 1.241646 | 1.421117 | 1.428374 | 2.0 |

### 7.1 LMM-only interpretation

The Lima and Mello baseline is fast for Q1, Q2, Q3, Q7, Q8, and Q9.

Q4 and Q5 are more expensive after parameter alignment, but they now return non-zero and methodologically consistent results.

Q6 is the main outlier, reaching 737.187 ms at hot p95 and returning the result limit of 1000 documents.

## 8. Lima and Mello vs SchemaLens on SF1

### 8.1 Winner summary

| Winner | Number of queries |
|---|---:|
| SchemaLens | 7 |
| Lima and Mello | 2 |

SchemaLens wins 7 out of 9 read queries.

Lima and Mello wins 2 out of 9 read queries.

### 8.2 Per-query comparison

| Query | Winner | LMM p95 ms | SchemaLens p95 ms | LMM / SchemaLens | LMM returned | SchemaLens returned | Cardinality flag | SchemaLens group | SchemaLens class |
|---|---|---:|---:|---:|---:|---:|---|---|---|
| Q1 | SchemaLens | 0.338933 | 0.233373 | 1.452323 | 1.0 | 1.0 | cardinality aligned | control | CONTROL |
| Q2 | SchemaLens | 0.636918 | 0.117117 | 5.438281 | 1.0 | 1.0 | cardinality aligned | primary | G5 |
| Q3 | Lima and Mello | 0.333562 | 0.434946 | 0.766903 | 1.0 | 10.6 | LMM returns less | primary | G5 |
| Q4 | SchemaLens | 13.401979 | 1.002833 | 13.364115 | 61.0 | 53.6 | cardinality aligned | control | CONTROL |
| Q5 | Lima and Mello | 9.564318 | 37.626791 | 0.254189 | 24.0 | 6801.0 | LMM returns less | primary | G2 |
| Q6 | SchemaLens | 737.187028 | 0.385924 | 1910.188848 | 1000.0 | 100.0 | LMM returns more | secondary affected | G9 |
| Q7 | SchemaLens | 1.413641 | 1.186999 | 1.190938 | 97.0 | 97.0 | cardinality aligned | primary | G4 |
| Q8 | SchemaLens | 1.257368 | 0.863551 | 1.456043 | 87.0 | 88.0 | cardinality aligned | secondary affected | G7 |
| Q9 | SchemaLens | 1.421117 | 0.851476 | 1.669003 | 2.0 | 0.3 | LMM returns more | secondary affected | G7 |

## 9. Cardinality analysis

The cleanest comparisons are Q1, Q2, Q4, Q7, and Q8 because the returned cardinalities are aligned or nearly aligned.

| Query | Winner | LMM p95 ms | SchemaLens p95 ms | LMM returned | SchemaLens returned |
|---|---|---:|---:|---:|---:|
| Q1 | SchemaLens | 0.338933 | 0.233373 | 1.0 | 1.0 |
| Q2 | SchemaLens | 0.636918 | 0.117117 | 1.0 | 1.0 |
| Q4 | SchemaLens | 13.401979 | 1.002833 | 61.0 | 53.6 |
| Q7 | SchemaLens | 1.413641 | 1.186999 | 97.0 | 97.0 |
| Q8 | SchemaLens | 1.257368 | 0.863551 | 87.0 | 88.0 |

SchemaLens wins all aligned-cardinality comparisons.

This is the strongest part of the SF1 result. It shows that SchemaLens does not only win because of returning fewer documents. In the most comparable cases, SchemaLens still achieves lower p95 latency.

## 10. Query-level interpretation

### Q1

Q1 is a clean SchemaLens win. Both methods return one document, and SchemaLens is 1.452 times faster.

### Q2

Q2 is a clear SchemaLens win. Both methods return one document, and SchemaLens is 5.438 times faster.

### Q3

Q3 is a Lima and Mello latency win, but with a cardinality caveat. Lima and Mello returns one document, while SchemaLens returns 10.6 documents on average.

### Q4

Q4 is a strong SchemaLens win. The returned cardinalities are aligned, with Lima and Mello returning 61 documents and SchemaLens returning 53.6 documents. SchemaLens is 13.364 times faster.

### Q5

Q5 is a Lima and Mello latency win, but with a major cardinality caveat. Lima and Mello returns 24 documents, while SchemaLens returns 6801 documents.

### Q6

Q6 is the strongest SchemaLens win. Lima and Mello is 1910 times slower and returns the result limit of 1000 documents. This is consistent with the query-plan result showing a collection scan and high documents examined.

### Q7

Q7 is a clean SchemaLens win. Both methods return 97 documents, and SchemaLens is 1.191 times faster.

### Q8

Q8 is a clean or near-clean SchemaLens win. Lima and Mello returns 87 documents and SchemaLens returns 88 documents. SchemaLens is 1.456 times faster.

### Q9

Q9 is a SchemaLens win, but it is a low-cardinality case. Lima and Mello returns 2 documents, while SchemaLens returns 0.3 on average.

## 11. Main conclusions

The aligned SF1 experiment leads to four conclusions.

### 11.1 SchemaLens wins most queries

SchemaLens wins 7 out of 9 read queries.

### 11.2 SchemaLens wins all aligned-cardinality cases

SchemaLens wins Q1, Q2, Q4, Q7, and Q8, where returned cardinality is aligned or almost aligned.

### 11.3 Lima and Mello wins Q3 and Q5, but with caveats

Lima and Mello wins Q3 and Q5 in raw latency, but it returns substantially fewer documents in both cases.

### 11.4 Q6 is the strongest SchemaLens advantage

Q6 strongly favors SchemaLens. Lima and Mello reaches 737.187 ms p95, while SchemaLens reaches 0.386 ms p95. The query-plan result confirms that Lima and Mello uses a collection scan for Q6.

## 12. Recommended paper interpretation

After aligning the Lima and Mello SF1 parameters with the SchemaLens benchmark semantics, SchemaLens outperforms the faithful baseline in 7 out of 9 read queries. More importantly, SchemaLens wins all aligned-cardinality cases, including Q1, Q2, Q4, Q7, and Q8. Lima and Mello is faster in Q3 and Q5, but both cases return substantially fewer documents, so they should be reported as latency wins with cardinality caveats. The strongest SchemaLens advantage appears in Q6, where the Lima and Mello baseline uses a collection scan and is more than three orders of magnitude slower.

## 13. Final status

| Item | Status |
|---|---|
| SF1 parameter alignment | completed |
| Type-aware id correction | completed |
| SF1 query-plan rerun | completed |
| SF1 final benchmark rerun | completed |
| SF1 LMM vs SchemaLens comparison | completed |

The aligned FIBEN SF1 Lima and Mello experiment is complete and consistent with the SF10 methodology.
