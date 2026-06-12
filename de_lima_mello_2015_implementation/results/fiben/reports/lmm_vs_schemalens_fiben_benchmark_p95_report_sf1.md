# Lima & Mello 2015 vs SchemaLens FIBEN p95 benchmark comparison

Scale: `sf1`

## Hot-phase summary

| winner_by_p95   |   n_queries |
|:----------------|------------:|
| LimaMello2015   |           5 |
| SchemaLens      |           4 |

## Hot p95 by query

| query_id   | winner_by_p95   |   lmm_p95_ms |   schemalens_p95_ms |   p95_ratio_lmm_over_schemalens | schemalens_g_class   | schemalens_design_pattern        |
|:-----------|:----------------|-------------:|--------------------:|--------------------------------:|:---------------------|:---------------------------------|
| Q1         | SchemaLens      |     0.309134 |            0.233373 |                        1.32464  | CONTROL              | normalized_reference_baseline    |
| Q2         | SchemaLens      |     0.59793  |            0.117117 |                        5.10539  | G5                   | shared_target_reference_strategy |
| Q3         | LimaMello2015   |     0.289551 |            0.434946 |                        0.665717 | G5                   | shared_target_reference_strategy |
| Q4         | LimaMello2015   |     0.876651 |            1.00283  |                        0.874175 | CONTROL              | normalized_reference_baseline    |
| Q5         | LimaMello2015   |    10.2762   |           37.6268   |                        0.273107 | G2                   | embedded_containment             |
| Q6         | SchemaLens      |   744.705    |            0.385924 |                     1929.67     | G9                   | benchmark_tradeoff_alternative   |
| Q7         | LimaMello2015   |     0.45703  |            1.187    |                        0.38503  | G4                   | deep_nested_document             |
| Q8         | SchemaLens      |     1.22774  |            0.863551 |                        1.42174  | G7                   | update_aware_reference_design    |
| Q9         | LimaMello2015   |     0.352317 |            0.851476 |                        0.413772 | G7                   | update_aware_reference_design    |

## Interpretation

- **Q1**: Q1: SchemaLens has lower p95 latency.
- **Q2**: Q2: SchemaLens has lower p95 latency.
- **Q3**: Q3: Lima & Mello has lower p95 latency.
- **Q4**: Q4: Lima & Mello has lower p95 latency.
- **Q5**: Q5: Lima & Mello has lower p95 latency.
- **Q6**: Q6: SchemaLens has lower p95 latency.
- **Q7**: Q7: Lima & Mello has lower p95 latency.
- **Q8**: Q8: SchemaLens has lower p95 latency.
- **Q9**: Q9: Lima & Mello has lower p95 latency.