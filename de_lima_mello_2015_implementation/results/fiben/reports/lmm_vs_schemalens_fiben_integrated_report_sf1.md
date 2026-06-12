# Integrated p95 and query-plan comparison: Lima & Mello 2015 vs SchemaLens

Scale: `sf1`

## Summary

| scale   |   n_queries |   lmm_p95_wins |   schemalens_p95_wins |   sum_lmm_p95_ms |   sum_schemalens_p95_ms |   mean_lmm_p95_ms |   mean_schemalens_p95_ms |   sum_lmm_docs_examined |   sum_schemalens_docs_examined |   sum_p95_ratio_lmm_over_schemalens |
|:--------|------------:|---------------:|----------------------:|-----------------:|------------------------:|------------------:|-------------------------:|------------------------:|-------------------------------:|------------------------------------:|
| sf1     |           9 |              5 |                     4 |          759.091 |                  42.703 |           84.3434 |                  4.74478 |                   22410 |                          15873 |                             17.7761 |

## Query-level integrated table

| query_id   | winner_by_p95   |   lmm_p95_ms |   schemalens_p95_ms |   p95_ratio_lmm_over_schemalens |   lmm_docs_examined |   schemalens_docs_examined |   docs_ratio_lmm_over_schemalens | schemalens_g_class   | schemalens_design_pattern        |
|:-----------|:----------------|-------------:|--------------------:|--------------------------------:|--------------------:|---------------------------:|---------------------------------:|:---------------------|:---------------------------------|
| Q1         | SchemaLens      |     0.309134 |            0.233373 |                        1.32464  |                   1 |                          1 |                      1           | CONTROL              | normalized_reference_baseline    |
| Q2         | SchemaLens      |     0.59793  |            0.117117 |                        5.10539  |                   4 |                          4 |                      1           | G5                   | shared_target_reference_strategy |
| Q3         | LimaMello2015   |     0.289551 |            0.434946 |                        0.665717 |                   1 |                          7 |                      0.142857    | G5                   | shared_target_reference_strategy |
| Q4         | LimaMello2015   |     0.876651 |            1.00283  |                        0.874175 |                   3 |                       2453 |                      0.00122299  | CONTROL              | normalized_reference_baseline    |
| Q5         | LimaMello2015   |    10.2762   |           37.6268   |                        0.273107 |                   1 |                       6718 |                      0.000148854 | G2                   | embedded_containment             |
| Q6         | SchemaLens      |   744.705    |            0.385924 |                     1929.67     |               22006 |                       5514 |                      3.99093     | G9                   | benchmark_tradeoff_alternative   |
| Q7         | LimaMello2015   |     0.45703  |            1.187    |                        0.38503  |                   1 |                        359 |                      0.00278552  | G4                   | deep_nested_document             |
| Q8         | SchemaLens      |     1.22774  |            0.863551 |                        1.42174  |                 392 |                        359 |                      1.09192     | G7                   | update_aware_reference_design    |
| Q9         | LimaMello2015   |     0.352317 |            0.851476 |                        0.413772 |                   1 |                        458 |                      0.00218341  | G7                   | update_aware_reference_design    |

## Interpretation

- **Q1**: SchemaLens is faster by p95; this indicates that the activated candidate selected by benchmarking better matches the physical execution cost.
- **Q2**: SchemaLens is faster by p95; this indicates that the activated candidate selected by benchmarking better matches the physical execution cost.
- **Q3**: Lima & Mello is faster by p95; this supports that its faithful workload-driven materialization is effective for this path-oriented query.
- **Q4**: Lima & Mello is faster by p95; this supports that its faithful workload-driven materialization is effective for this path-oriented query.
- **Q5**: Lima & Mello is faster by p95; this supports that its faithful workload-driven materialization is effective for this path-oriented query.
- **Q6**: Q6 is the dominant case: SchemaLens strongly reduces p95 latency (LMM/SchemaLens ratio 1929.7x) and avoids the transaction-heavy cost pattern.
- **Q7**: Lima & Mello is faster by p95; this supports that its faithful workload-driven materialization is effective for this path-oriented query.
- **Q8**: SchemaLens is faster by p95; this indicates that the activated candidate selected by benchmarking better matches the physical execution cost.
- **Q9**: Lima & Mello is faster by p95; this supports that its faithful workload-driven materialization is effective for this path-oriented query.