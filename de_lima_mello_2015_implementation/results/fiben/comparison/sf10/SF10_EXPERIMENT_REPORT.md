# Lima and Mello 2015 Baseline on FIBEN SF10

## Materialization, benchmark, and comparison with SchemaLens

This report documents the FIBEN SF10 experiment for the faithful implementation of the workload-driven NoSQL logical design method proposed by Lima and Mello. The goal is to compare this related-work baseline against SchemaLens using the same FIBEN workload and a comparable MongoDB execution protocol.

The experiment extends the previous FIBEN SF1 baseline implementation to SF10. It includes source profiling, MongoDB materialization, query-plan validation, parameter alignment, benchmark execution, and comparison with the best SchemaLens candidate per query.

---

## 1. Goal of the experiment

The goal of this experiment is to answer the following question:

> When a faithful implementation of the Lima and Mello 2015 workload-driven NoSQL design method is materialized in MongoDB for FIBEN SF10, how does its query performance compare with the best SchemaLens candidate for each FIBEN read query?

This comparison is important because Lima and Mello is treated as an independent related-work baseline. We do not map Lima and Mello outputs into SchemaLens candidate families. Instead, we:

1. implement the baseline method faithfully;
2. materialize its resulting MongoDB schema;
3. execute the FIBEN workload;
4. compare the measured latency with the best SchemaLens MongoDB candidate for each query.

---

## 2. Scope

This SF10 report covers the read workload Q1--Q9.

Q10 is an insert/update workload and was not included in this read-query comparison. The current comparison focuses on hot-run p95 latency for read queries, using the same 10-cold and 10-hot protocol observed in the SchemaLens SF10 benchmark artifacts.

---

## 3. Repository paths

Main implementation folder:

```text
de_lima_mello_2015_implementation/
```

Main scripts used in this SF10 phase:

```text
de_lima_mello_2015_implementation/benchmark/fiben/run_lmm_fiben_mongodb_materialization.py
de_lima_mello_2015_implementation/benchmark/fiben/run_lmm_fiben_query_plan.py
de_lima_mello_2015_implementation/benchmark/fiben/run_lmm_fiben_benchmark.py
de_lima_mello_2015_implementation/benchmark/fiben/repair_lmm_fiben_transaction_listed_security_embedding.py
de_lima_mello_2015_implementation/src/lmm_fiben_column_schema.py
```

Generated SF10 source profile:

```text
de_lima_mello_2015_implementation/generated/fiben/source_profile/sf10/
```

Generated SF10 materialization artifacts:

```text
de_lima_mello_2015_implementation/results/fiben/materialization/sf10/
```

Generated SF10 query-plan artifacts:

```text
de_lima_mello_2015_implementation/results/fiben/query_plan/sf10/
```

Generated SF10 benchmark artifacts:

```text
de_lima_mello_2015_implementation/results/fiben/benchmark/sf10/
```

Generated SF10 comparison artifacts:

```text
de_lima_mello_2015_implementation/results/fiben/comparison/sf10/
```

Main comparison outputs:

```text
de_lima_mello_2015_implementation/results/fiben/comparison/sf10/lmm_vs_schemalens_sf10_hot_best.csv
de_lima_mello_2015_implementation/results/fiben/comparison/sf10/lmm_vs_schemalens_sf10_hot_best_interpreted.csv
de_lima_mello_2015_implementation/results/fiben/comparison/sf10/lmm_vs_schemalens_sf10_winner_summary.csv
de_lima_mello_2015_implementation/results/fiben/comparison/sf10/lmm_vs_schemalens_sf10_interpretation.md
```

---

## 4. Database and execution environment

The Lima and Mello SF10 materialization was loaded into the following MongoDB database:

```text
lmm_fiben_sf10_source_full
```

MongoDB connection used in the experiments:

```text
mongodb://mongo:mongo@127.0.0.1:27018/admin
```

The experiment was executed in the repository:

```text
/home/hudson/Documents/schemalens_reprodutibilty
```

Branch:

```text
llmf_imp_fiben
```

---

## 5. Methodological decisions

### 5.1 Faithful baseline implementation

The Lima and Mello baseline was implemented as a related-work method, not as a SchemaLens candidate. This means:

* the baseline is not classified as G0--G9;
* the baseline is not evaluated through SchemaLens activation logic;
* the baseline is materialized independently;
* the final comparison uses measured MongoDB performance.

This preserves the methodological difference between SchemaLens and the related-work baseline.

### 5.2 Reusing the FIBEN conceptual interpretation

The experiment reused the same FIBEN conceptual interpretation used in the SchemaLens workflow. This avoids comparing two methods over different conceptual inputs.

The baseline therefore receives the same conceptual assumptions used in the SchemaLens FIBEN experiments, but it produces its own workload-driven document design.

### 5.3 Query-parameter alignment

The main challenge in SF10 was making sure the Lima and Mello queries used parameters comparable with the SchemaLens benchmark.

Parameter-sensitive queries were aligned as follows:

| Query | Alignment decision                                                                         |
| ----- | ------------------------------------------------------------------------------------------ |
| Q1    | IBM used as target corporation                                                             |
| Q2    | IBM used as target corporation                                                             |
| Q4    | Person selected with complete Person -> Account -> Holding -> Security -> Corporation path |
| Q5    | IBM used as target corporation                                                             |
| Q7    | IBM used as target corporation and one deterministic IBM security identifier               |
| Q8    | IBM used as target corporation and one deterministic IBM security identifier               |
| Q9    | Transaction-based REFERSTO stock identifier selected from transaction pool                 |

The final key parameters were:

| Parameter             | Value                      |
| --------------------- | -------------------------- |
| IBM corporation id    | 2860                       |
| IBM ticker            | IBM                        |
| Q4 person id          | SF10_PERS_R01_400000035163 |
| Q7/Q8 IBM security id | SF10_SEC_R01_1002518       |
| Q9 listed security id | SF10_SEC_R01_1001538       |
| Account id            | 150000000000               |

### 5.4 Avoiding artificial SF10 replica multiplication

An important correction was applied to Q7 and Q8.

Initially, the runner expanded the IBM security id across multiple SF10 replicas:

```text
1002518
SF10_SEC_R01_1002518
SF10_SEC_R02_1002518
...
SF10_SEC_R10_1002518
```

This caused Q7 and Q8 to return too many documents:

| Query | Returned documents with all replicated ids |
| ----- | -----------------------------------------: |
| Q7    |                                        873 |
| Q8    |                                        783 |

This was not comparable with the SchemaLens SF10 benchmark, where Q7 and Q8 returned approximately 97 and 88 documents.

A diagnostic showed that a single deterministic transaction-backed security variant was enough to match SchemaLens cardinality:

| Security id          | Q7 returned | Q8 returned |
| -------------------- | ----------: | ----------: |
| SF10_SEC_R01_1002518 |          97 |          87 |
| SF10_SEC_R02_1002518 |          97 |          87 |
| SF10_SEC_R03_1002518 |          97 |          87 |
| SF10_SEC_R04_1002518 |          97 |          87 |
| SF10_SEC_R05_1002518 |          97 |          87 |
| SF10_SEC_R06_1002518 |          97 |          87 |
| SF10_SEC_R07_1002518 |          97 |          87 |
| SF10_SEC_R08_1002518 |          97 |          87 |
| SF10_SEC_R09_1002518 |          97 |          87 |
| 1002518              |           0 |           0 |
| SF10_SEC_R10_1002518 |           0 |           0 |

Therefore, the runner was corrected to select one deterministic transaction-backed SF10 variant per raw security id. The selected final id was:

```text
SF10_SEC_R01_1002518
```

This made Q7 and Q8 comparable with SchemaLens.

---

## 6. SF10 materialization

The Lima and Mello SF10 materialization was completed in MongoDB using the database:

```text
lmm_fiben_sf10_source_full
```

The final database contained 14 collections.

### 6.1 Collection counts

| Collection                    | Documents |
| ----------------------------- | --------: |
| _src_fiben_countries          |       250 |
| _src_fiben_holdings           |  20844448 |
| _src_fiben_industries         |       453 |
| lmm_corporation               |     23241 |
| lmm_disclosure                |   2081581 |
| lmm_financial_report          |    483011 |
| lmm_financial_service_account |   3793531 |
| lmm_listed_security           |     27451 |
| lmm_person                    |   1953901 |
| lmm_report_element            |  81200841 |
| lmm_security                  |     27451 |
| lmm_sell_transaction          |  19500001 |
| lmm_statement_element         |   4437941 |
| lmm_transaction               |  19500001 |

### 6.2 Materialization status

The materialization generated the full SF10 baseline database. Most embeddings and references were completed successfully.

Summary:

| Item                     | Status |
| ------------------------ | ------ |
| Collections materialized | 14     |
| Completed embeddings     | 8      |
| Timed-out embedding      | 1      |
| Completed references     | 3      |
| Bridge skip              | 1      |

One expensive embedding involving transaction-to-listed-security data timed out or required special handling because of the size and synthetic SF10 identifier structure. We did not force artificial semantic matches. Instead, we preserved the materialized baseline and corrected the query parameter logic so that query execution remained comparable with SchemaLens where possible.

---

## 7. Query-plan validation

Before running the final benchmark, we validated important parameter-sensitive queries with the query-plan runner.

### 7.1 Final Q7--Q9 query-plan summary

| Query | Status    | Returned accumulated | Docs examined | Keys examined | Max time ms | IXSCAN | COLLSCAN | GROUP |
| ----- | --------- | -------------------: | ------------: | ------------: | ----------: | ------ | -------- | ----- |
| Q7    | completed |                 1268 |           179 |           179 |           3 | true   | false    | true  |
| Q8    | completed |                 1428 |           179 |           179 |           1 | true   | false    | true  |
| Q9    | completed |                 2513 |           458 |           458 |           3 | true   | false    | true  |

The query-plan field `Returned accumulated` is an internal explain-style accumulated metric and is not the same as the benchmark-level number of returned documents. The benchmark-level returned documents are reported in later sections.

The important validation result is that Q7, Q8, and Q9 completed successfully, used indexes, avoided collection scans, and included the expected grouping operations.

### 7.2 Q4 validation

Q4 initially returned zero documents because the runner used `person_id = null`. The runner was corrected to select a person with a complete path:

```text
Person -> FinancialServiceAccount -> Holding -> Security -> Corporation
```

The final selected Q4 person was:

```text
SF10_PERS_R01_400000035163
```

After the correction, Q4 returned 61 documents in the benchmark.

---

## 8. Benchmark protocol

The final Lima and Mello SF10 benchmark used the same repetition protocol observed in the SchemaLens SF10 benchmark artifacts.

SchemaLens SF10 raw results showed:

| Phase | Raw rows |
| ----- | -------: |
| cold  |      600 |
| hot   |      600 |

SchemaLens SF10 aggregate results showed:

| Phase | Aggregate rows |
| ----- | -------------: |
| cold  |             60 |
| hot   |             60 |

This implies:

```text
600 raw rows / 60 aggregate rows = 10 repetitions
```

Therefore, the final Lima and Mello SF10 benchmark used:

| Parameter              | Value |
| ---------------------- | ----: |
| Warmup runs            |     0 |
| Cold runs per query    |    10 |
| Hot runs per query     |    10 |
| Number of read queries |     9 |
| Result limit           |  1000 |

The final command used the following structure:

```bash
python de_lima_mello_2015_implementation/benchmark/fiben/run_lmm_fiben_benchmark.py \
  --db-name lmm_fiben_sf10_source_full \
  --scale sf10 \
  --queries Q1,Q2,Q3,Q4,Q5,Q6,Q7,Q8,Q9 \
  --warmup-runs 0 \
  --cold-runs 10 \
  --hot-runs 10 \
  --result-limit 1000 \
  --max-time-ms 600000
```

---

## 9. Final Lima and Mello SF10 benchmark validation

The final benchmark produced:

| Metric                    | Value |
| ------------------------- | ----: |
| Queries                   |     9 |
| Raw executions            |   180 |
| Completed executions      |   180 |
| Cold executions           |    90 |
| Hot executions            |    90 |
| Cold executions per query |    10 |
| Hot executions per query  |    10 |
| Zero-returned hot queries |     0 |

All executions completed successfully.

### 9.1 Count per query and phase

| Query | Cold | Hot |
| ----- | ---: | --: |
| Q1    |   10 |  10 |
| Q2    |   10 |  10 |
| Q3    |   10 |  10 |
| Q4    |   10 |  10 |
| Q5    |   10 |  10 |
| Q6    |   10 |  10 |
| Q7    |   10 |  10 |
| Q8    |   10 |  10 |
| Q9    |   10 |  10 |

### 9.2 Returned documents by query

| Query | Count |  Min |  Max |   Mean |
| ----- | ----: | ---: | ---: | -----: |
| Q1    |    20 |    1 |    1 |    1.0 |
| Q2    |    20 |    1 |    1 |    1.0 |
| Q3    |    20 |    1 |    1 |    1.0 |
| Q4    |    20 |   61 |   61 |   61.0 |
| Q5    |    20 |   24 |   24 |   24.0 |
| Q6    |    20 | 1000 | 1000 | 1000.0 |
| Q7    |    20 |   97 |   97 |   97.0 |
| Q8    |    20 |   87 |   87 |   87.0 |
| Q9    |    20 |    2 |    2 |    2.0 |

---

## 10. Final Lima and Mello SF10 hot results

The table below reports the final hot-run results for the Lima and Mello baseline.

| Query | Completed |     Mean ms |   Median ms |      P95 ms |      Max ms | Mean returned |
| ----- | --------: | ----------: | ----------: | ----------: | ----------: | ------------: |
| Q1    |        10 |    0.307053 |    0.301719 |    0.318401 |    0.319255 |           1.0 |
| Q2    |        10 |    0.635836 |    0.629533 |    0.657670 |    0.661106 |           1.0 |
| Q3    |        10 |    0.299810 |    0.299308 |    0.307812 |    0.312103 |           1.0 |
| Q4    |        10 |    8.913675 |    8.877421 |    9.048946 |    9.074449 |          61.0 |
| Q5    |        10 |    0.646150 |    0.636365 |    0.689555 |    0.703215 |          24.0 |
| Q6    |        10 | 2345.032492 | 2433.193750 | 2944.970120 | 2946.633058 |        1000.0 |
| Q7    |        10 |    1.369034 |    1.371445 |    1.379932 |    1.384043 |          97.0 |
| Q8    |        10 |    1.356491 |    1.351040 |    1.376053 |    1.379292 |          87.0 |
| Q9    |        10 |    1.291569 |    1.256041 |    1.441561 |    1.472349 |           2.0 |

### 10.1 Interpretation of LMM-only results

The Lima and Mello baseline is very fast in Q1, Q3, and Q5, with sub-millisecond p95 latency.

Q4, Q7, Q8, and Q9 are also completed with low p95 latency, below 10 ms.

Q6 is the main LMM outlier. It reaches 2944.970 ms at p95 and returns the result limit of 1000 documents. This shows that the LMM materialization is not well suited to Q6 at SF10. Q6 is a selective query over technology-related United States listed securities with high last traded value. The LMM design does not provide the same query-targeted access path as the best SchemaLens candidate for this workload pattern.

---

## 11. Comparison with SchemaLens on SF10

The comparison uses hot-run p95 latency.

For each query, the Lima and Mello result is compared with the best SchemaLens candidate observed for the same query in the SF10 benchmark.

### 11.1 Winner summary

| Winner         | Number of queries |
| -------------- | ----------------: |
| SchemaLens     |                 7 |
| Lima and Mello |                 2 |

SchemaLens wins 7 out of 9 read queries.

Lima and Mello wins 2 out of 9 read queries.

### 11.2 Per-query comparison

| Query | Winner         |  LMM p95 ms | SchemaLens p95 ms | LMM / SchemaLens | LMM returned | SchemaLens returned | SchemaLens group   | SchemaLens class |
| ----- | -------------- | ----------: | ----------------: | ---------------: | -----------: | ------------------: | ------------------ | ---------------- |
| Q1    | SchemaLens     |    0.318401 |          0.295784 |         1.076464 |          1.0 |                 1.0 | control            | CONTROL          |
| Q2    | SchemaLens     |    0.657670 |          0.155368 |         4.232979 |          1.0 |                 1.0 | primary            | G1               |
| Q3    | Lima and Mello |    0.307812 |          0.899143 |         0.342339 |          1.0 |                53.8 | primary            | G4               |
| Q4    | SchemaLens     |    9.048946 |          4.308413 |         2.100297 |         61.0 |               536.0 | primary            | G5               |
| Q5    | Lima and Mello |    0.689555 |         28.432783 |         0.024252 |         24.0 |              6801.0 | secondary_affected | G9               |
| Q6    | SchemaLens     | 2944.970120 |         91.474332 |        32.194497 |       1000.0 |               100.0 | control            | CONTROL          |
| Q7    | SchemaLens     |    1.379932 |          0.857698 |         1.608878 |         97.0 |                97.0 | primary            | G6               |
| Q8    | SchemaLens     |    1.376053 |          0.921652 |         1.493028 |         87.0 |                88.0 | primary            | G5               |
| Q9    | SchemaLens     |    1.441561 |          1.056870 |         1.363991 |          2.0 |                 0.3 | primary            | G5               |

### 11.3 SchemaLens best candidate per query

| Query | SchemaLens best candidate id                                                                               |
| ----- | ---------------------------------------------------------------------------------------------------------- |
| Q1    | q1_company_profile_ibm__control__normalized_reference_baseline                                             |
| Q2    | q2_company_with_industry_country_and_listed_securities__g1__embed_descriptors                              |
| Q3    | q3_securities_held_in_each_financial_service_account__g4__deep_nested_path                                 |
| Q4    | q4_companies_reached_from_person_through_account_holding_listed_security__g5__shared_targets_as_references |
| Q5    | q5_reports_and_metric_data_of_company__g9__tradeoff_benchmark_candidate                                    |
| Q6    | q6_tech_uslisted_securities_with_high_last_traded_value__control__normalized_reference_baseline            |
| Q7    | q7_persons_who_bought_more_ibmthan_sold__g6__materialized_query_view                                       |
| Q8    | q8_ibmtransactions_below_average_selling_price__g5__shared_targets_as_references                           |
| Q9    | q9_persons_who_bought_and_sold_same_stock__g5__shared_targets_as_references                                |

---

## 12. Cardinality analysis

Latency must be interpreted together with returned cardinality.

Some query comparisons are clean because Lima and Mello and SchemaLens return the same or almost the same number of documents. Other cases require caution because one method returns substantially fewer or more documents.

### 12.1 Returned cardinality comparison

| Query | LMM returned | SchemaLens returned | Cardinality interpretation     |
| ----- | -----------: | ------------------: | ------------------------------ |
| Q1    |          1.0 |                 1.0 | aligned                        |
| Q2    |          1.0 |                 1.0 | aligned                        |
| Q3    |          1.0 |                53.8 | LMM returns fewer              |
| Q4    |         61.0 |               536.0 | LMM returns fewer              |
| Q5    |         24.0 |              6801.0 | LMM returns fewer              |
| Q6    |       1000.0 |               100.0 | LMM returns more               |
| Q7    |         97.0 |                97.0 | aligned                        |
| Q8    |         87.0 |                88.0 | nearly aligned                 |
| Q9    |          2.0 |                 0.3 | low-cardinality parameter case |

### 12.2 Cleanest comparisons

The cleanest comparisons are Q1, Q2, Q7, and Q8 because the returned cardinalities are aligned or nearly aligned.

| Query | Winner     | LMM p95 ms | SchemaLens p95 ms | LMM returned | SchemaLens returned |
| ----- | ---------- | ---------: | ----------------: | -----------: | ------------------: |
| Q1    | SchemaLens |   0.318401 |          0.295784 |          1.0 |                 1.0 |
| Q2    | SchemaLens |   0.657670 |          0.155368 |          1.0 |                 1.0 |
| Q7    | SchemaLens |   1.379932 |          0.857698 |         97.0 |                97.0 |
| Q8    | SchemaLens |   1.376053 |          0.921652 |         87.0 |                88.0 |

SchemaLens wins all four aligned or nearly aligned comparisons.

This is important because it shows that SchemaLens does not only win because of lower returned cardinality. In these cases, the returned cardinalities are comparable, and SchemaLens still provides lower hot-run p95 latency.

---

## 13. Query-by-query interpretation

### Q1

Q1 is a near tie.

| Metric        |      LMM | SchemaLens |
| ------------- | -------: | ---------: |
| P95 ms        | 0.318401 |   0.295784 |
| Returned docs |      1.0 |        1.0 |

SchemaLens is slightly faster, with a ratio of 1.076. Since both methods return one document, this is a clean comparison. The difference is small, so Q1 should be interpreted as a near tie with a slight SchemaLens advantage.

### Q2

Q2 is a clear SchemaLens win.

| Metric        |      LMM | SchemaLens |
| ------------- | -------: | ---------: |
| P95 ms        | 0.657670 |   0.155368 |
| Returned docs |      1.0 |        1.0 |

Both methods return one document, but SchemaLens is 4.233 times faster. This suggests that the SchemaLens candidate selected for Q2 provides a better access path for retrieving a company together with its industry, country, and listed securities.

### Q3

Q3 is a raw latency win for Lima and Mello, but with a cardinality caveat.

| Metric        |      LMM | SchemaLens |
| ------------- | -------: | ---------: |
| P95 ms        | 0.307812 |   0.899143 |
| Returned docs |      1.0 |       53.8 |

Lima and Mello is faster in raw p95 latency. However, it returns only one document, while SchemaLens returns 53.8 documents on average. This means Q3 should not be treated as a fully clean semantic win for Lima and Mello without further discussion. It is a useful latency observation, but the returned cardinality is not aligned.

### Q4

Q4 is a strong SchemaLens win.

| Metric        |      LMM | SchemaLens |
| ------------- | -------: | ---------: |
| P95 ms        | 9.048946 |   4.308413 |
| Returned docs |     61.0 |      536.0 |

SchemaLens is 2.100 times faster even though it returns many more documents. This is strong evidence in favor of the SchemaLens candidate for the person-to-account-to-holding-to-security-to-corporation traversal pattern.

### Q5

Q5 is a raw latency win for Lima and Mello, but with a major cardinality caveat.

| Metric        |      LMM | SchemaLens |
| ------------- | -------: | ---------: |
| P95 ms        | 0.689555 |  28.432783 |
| Returned docs |     24.0 |     6801.0 |

Lima and Mello is much faster in raw p95 latency. However, it returns 24 documents, while SchemaLens returns 6801 documents. This is a major cardinality difference. Therefore, Q5 should be described as a Lima and Mello latency win with caution, not as a clean semantic win.

### Q6

Q6 is the strongest SchemaLens win.

| Metric        |         LMM | SchemaLens |
| ------------- | ----------: | ---------: |
| P95 ms        | 2944.970120 |  91.474332 |
| Returned docs |      1000.0 |      100.0 |

Lima and Mello is 32.194 times slower than SchemaLens. It also reaches the result limit of 1000 documents. This indicates that the Lima and Mello materialization is not well suited to the selective filtering pattern of Q6 at SF10.

### Q7

Q7 is a clean SchemaLens win.

| Metric        |      LMM | SchemaLens |
| ------------- | -------: | ---------: |
| P95 ms        | 1.379932 |   0.857698 |
| Returned docs |     97.0 |       97.0 |

Both methods return exactly 97 documents. SchemaLens is 1.609 times faster. This is one of the most important comparisons because Q7 required careful parameter alignment over IBM and its associated security identifier.

### Q8

Q8 is a clean or near-clean SchemaLens win.

| Metric        |      LMM | SchemaLens |
| ------------- | -------: | ---------: |
| P95 ms        | 1.376053 |   0.921652 |
| Returned docs |     87.0 |       88.0 |

The returned cardinality is almost identical. SchemaLens is 1.493 times faster. This confirms the SchemaLens advantage for the IBM transaction pattern below average selling price.

### Q9

Q9 is a SchemaLens win, but with low cardinality.

| Metric        |      LMM | SchemaLens |
| ------------- | -------: | ---------: |
| P95 ms        | 1.441561 |   1.056870 |
| Returned docs |      2.0 |        0.3 |

SchemaLens is 1.364 times faster. However, both returned cardinalities are very small, and the SchemaLens value is an average over its parameter/repetition behavior. Q9 should therefore be interpreted as a small low-cardinality win for SchemaLens.

---

## 14. Main conclusions

The SF10 experiment leads to four main conclusions.

### 14.1 SchemaLens wins most queries

SchemaLens wins 7 out of 9 read queries.

This shows that SchemaLens performs better than the faithful Lima and Mello baseline in most SF10 read-query cases.

### 14.2 SchemaLens wins all aligned-cardinality cases

The aligned or nearly aligned queries are Q1, Q2, Q7, and Q8.

SchemaLens wins all four:

| Query | Winner     |
| ----- | ---------- |
| Q1    | SchemaLens |
| Q2    | SchemaLens |
| Q7    | SchemaLens |
| Q8    | SchemaLens |

This strengthens the comparison because these wins are not explained by SchemaLens returning fewer documents.

### 14.3 Lima and Mello wins Q3 and Q5, but with caveats

Lima and Mello wins Q3 and Q5 in raw p95 latency.

However:

* in Q3, Lima and Mello returns 1 document, while SchemaLens returns 53.8;
* in Q5, Lima and Mello returns 24 documents, while SchemaLens returns 6801.

Therefore, Q3 and Q5 should be reported as latency wins for Lima and Mello with cardinality caveats.

### 14.4 Q6 shows the strongest SchemaLens advantage

Q6 is the largest performance gap.

Lima and Mello p95:

```text
2944.970 ms
```

SchemaLens p95:

```text
91.474 ms
```

Ratio:

```text
32.194
```

This suggests that SchemaLens provides a much better candidate for the selective query pattern in Q6.

---

## 15. Recommended paper interpretation

A concise interpretation for the paper is:

> On FIBEN SF10, SchemaLens outperforms the faithful Lima and Mello baseline in 7 out of 9 read queries under the same 10-cold and 10-hot protocol. The strongest SchemaLens gains occur in Q2, Q4, Q6, Q7, and Q8. The Q7 and Q8 comparisons are especially meaningful because their returned cardinalities are aligned or nearly aligned. Lima and Mello is faster in Q3 and Q5, but these cases return substantially fewer documents than the best SchemaLens candidate, so they should be interpreted as raw latency wins with cardinality caveats rather than clean semantic wins.

---

## 16. Reproducibility commands

### 16.1 Compile runners

```bash
python -m py_compile de_lima_mello_2015_implementation/benchmark/fiben/run_lmm_fiben_query_plan.py
python -m py_compile de_lima_mello_2015_implementation/benchmark/fiben/run_lmm_fiben_benchmark.py
```

### 16.2 Validate final parameters

```bash
python - <<'PY'
from pymongo import MongoClient
import importlib.util
from pathlib import Path
import json

script = Path("de_lima_mello_2015_implementation/benchmark/fiben/run_lmm_fiben_query_plan.py")
spec = importlib.util.spec_from_file_location("runner", script)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

client = MongoClient("mongodb://mongo:mongo@127.0.0.1:27018/admin")
db = client["lmm_fiben_sf10_source_full"]

params = runner.build_params(db)

print(json.dumps({
    "corporation_id": params.get("corporation_id"),
    "corporation_ticker": params.get("corporation_ticker"),
    "person_id_for_q4": params.get("person_id"),
    "account_id": params.get("account_id"),
    "corporation_security_ids": params.get("corporation_security_ids"),
    "q9_listed_security_id": params.get("listed_security_id"),
}, indent=2, sort_keys=True))
PY
```

Expected final parameters:

```json
{
  "account_id": "150000000000",
  "corporation_id": "2860",
  "corporation_security_ids": [
    "SF10_SEC_R01_1002518"
  ],
  "corporation_ticker": "IBM",
  "person_id_for_q4": "SF10_PERS_R01_400000035163",
  "q9_listed_security_id": "SF10_SEC_R01_1001538"
}
```

### 16.3 Run final benchmark

```bash
python de_lima_mello_2015_implementation/benchmark/fiben/run_lmm_fiben_benchmark.py \
  --db-name lmm_fiben_sf10_source_full \
  --scale sf10 \
  --queries Q1,Q2,Q3,Q4,Q5,Q6,Q7,Q8,Q9 \
  --warmup-runs 0 \
  --cold-runs 10 \
  --hot-runs 10 \
  --result-limit 1000 \
  --max-time-ms 600000 \
  | tee de_lima_mello_2015_implementation/results/fiben/materialization/sf10/logs/lmm_fiben_sf10_benchmark_final_schemalens_aligned_10cold_10hot.log
```

### 16.4 Validate final benchmark

```bash
python - <<'PY'
from pathlib import Path
import pandas as pd
import json

base = Path("de_lima_mello_2015_implementation/results/fiben/benchmark/sf10/lmm_fiben_sf10_source_full")

raw = pd.read_csv(base / "lmm_fiben_benchmark_raw_results.csv")
agg = pd.read_csv(base / "lmm_fiben_benchmark_aggregate_results.csv")
manifest = json.loads((base / "lmm_fiben_benchmark_manifest.json").read_text())

print(json.dumps({
    "scale": manifest.get("scale"),
    "queries": manifest.get("queries"),
    "warmup_runs": manifest.get("warmup_runs"),
    "cold_runs": manifest.get("cold_runs"),
    "hot_runs": manifest.get("hot_runs"),
}, indent=2))

print(raw["status"].value_counts(dropna=False).to_string())
print(raw["run_phase"].value_counts(dropna=False).to_string())
print(raw.groupby(["query_id", "run_phase"]).size().unstack(fill_value=0).to_string())

hot = agg[agg["run_phase"] == "hot"].copy()
print(hot[[
    "query_id",
    "n_completed",
    "mean_ms",
    "median_ms",
    "p95_ms",
    "max_ms",
    "mean_n_returned"
]].to_string(index=False))
PY
```

---

## 17. Files generated by this SF10 phase

Main benchmark outputs:

```text
de_lima_mello_2015_implementation/results/fiben/benchmark/sf10/lmm_fiben_sf10_source_full/lmm_fiben_benchmark_raw_results.csv
de_lima_mello_2015_implementation/results/fiben/benchmark/sf10/lmm_fiben_sf10_source_full/lmm_fiben_benchmark_aggregate_results.csv
de_lima_mello_2015_implementation/results/fiben/benchmark/sf10/lmm_fiben_sf10_source_full/lmm_fiben_benchmark_manifest.json
```

Main comparison outputs:

```text
de_lima_mello_2015_implementation/results/fiben/comparison/sf10/lmm_vs_schemalens_sf10_hot_best.csv
de_lima_mello_2015_implementation/results/fiben/comparison/sf10/lmm_vs_schemalens_sf10_hot_best_interpreted.csv
de_lima_mello_2015_implementation/results/fiben/comparison/sf10/lmm_vs_schemalens_sf10_winner_summary.csv
de_lima_mello_2015_implementation/results/fiben/comparison/sf10/lmm_vs_schemalens_sf10_interpretation.md
```

Main query-plan outputs:

```text
de_lima_mello_2015_implementation/results/fiben/query_plan/sf10/
```

Main materialization outputs:

```text
de_lima_mello_2015_implementation/results/fiben/materialization/sf10/
```

---

## 18. Final status

The FIBEN SF10 Lima and Mello baseline experiment is complete.

Final status:

| Item                             | Status    |
| -------------------------------- | --------- |
| SF10 source profile              | completed |
| SF10 materialization             | completed |
| Query parameter alignment        | completed |
| Q4 zero-return fix               | completed |
| Q7/Q8 replica multiplication fix | completed |
| Query-plan validation            | completed |
| Final 10-cold/10-hot benchmark   | completed |
| LMM vs SchemaLens comparison     | completed |
| README/report update             | completed |

This experiment is ready to be used as part of the SchemaLens journal-extension baseline comparison.


<!-- SF10_QUERY_PLAN_FINAL_START -->
## Final query-plan validation after parameter alignment

After completing the final benchmark, we reran the SF10 query-plan validation using the same parameter logic adopted by the final Lima and Mello benchmark. This step ensures that the query-plan artifacts and the benchmark artifacts are methodologically consistent.

### Final query-plan parameters

| Parameter | Value |
|---|---|
| IBM corporation id | 2860 |
| IBM ticker | IBM |
| Q4 person id | SF10_PERS_R01_400000035163 |
| Q7/Q8 IBM security id | SF10_SEC_R01_1002518 |
| Q9 listed security id | SF10_SEC_R01_1001538 |

### Final query-plan summary

| Query | Status | Returned accumulated | Docs examined | Keys examined | Max time ms | IXSCAN | COLLSCAN | GROUP |
|---|---|---:|---:|---:|---:|---|---|---|
| Q1 | completed | 5 | 1 | 1 | 0 | true | false | false |
| Q2 | completed | 35 | 4 | 4 | 0 | true | false | false |
| Q3 | completed | 5 | 1 | 1 | 0 | true | false | false |
| Q4 | completed | 317 | 62 | 62 | 11 | true | false | false |
| Q5 | completed | 77 | 1 | 1 | 0 | true | false | false |
| Q6 | completed | 199343 | 601029 | 1000 | 2790 | false | true | false |
| Q7 | completed | 1268 | 179 | 179 | 8 | true | false | true |
| Q8 | completed | 1428 | 179 | 179 | 1 | true | false | true |
| Q9 | completed | 2513 | 458 | 458 | 10 | true | false | true |

### Query-plan interpretation

All Q1--Q9 query-plan executions completed successfully with the final aligned parameters. Q4 now uses a valid person with a complete path from person to account, holding, security, and corporation. Q7 and Q8 use the deterministic IBM security variant selected to avoid artificial multiplication across SF10 replicated identifiers.

The main query-plan outlier is Q6. It uses a collection scan, does not use an index scan, examines 601029 documents, and reaches 2790 ms in the query-plan measurement. This explains the final benchmark result where Q6 reached 2944.970 ms at hot-run p95. Therefore, Q6 provides direct evidence that the Lima and Mello materialization does not provide an efficient access path for this selective filtering workload at SF10.

Q7, Q8, and Q9 use indexed transaction access and grouping operations. This is consistent with the final benchmark, where Q7 and Q8 also showed returned cardinalities aligned or nearly aligned with SchemaLens.
<!-- SF10_QUERY_PLAN_FINAL_END -->
