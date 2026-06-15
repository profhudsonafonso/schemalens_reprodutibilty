# LDBC SNB Physical MongoDB Cross-Scale Analysis

This report summarizes the faithful physical MongoDB benchmark for LDBC SNB across SF0.1, SF1, and SF3 when available.

## Validation summary

| scale_label   |   query_count |   aggregate_rows |   raw_rows |   query_write_plan_rows |   failed_runs_total |   semantic_warning_total |   raw_failed_rows |   non_completed_plan_rows |   collscan_rows | valid_run   |
|:--------------|--------------:|-----------------:|-----------:|------------------------:|--------------------:|-------------------------:|------------------:|--------------------------:|----------------:|:------------|
| sf0.1         |            22 |              128 |       1280 |                     128 |                   0 |                        0 |                 0 |                         0 |               0 | True        |
| sf1           |            22 |              128 |       1280 |                     128 |                   0 |                        0 |                 0 |                         0 |               0 | True        |
| sf3           |            22 |              128 |       1280 |                     128 |                   0 |                        0 |                 0 |                         0 |               0 | True        |

## Hot-phase cross-scale metrics

| scale_label   | run_phase   |   query_count |   activated_top1_preservation |   primary_top1_preservation |   mean_activated_regret |   mean_primary_regret |   primary_winners |   secondary_affected_winners |   control_winners |
|:--------------|:------------|--------------:|------------------------------:|----------------------------:|------------------------:|----------------------:|------------------:|-----------------------------:|------------------:|
| sf0.1         | hot         |            22 |                      0.954545 |                    0.772727 |             5.52038e-06 |             0.0650759 |                17 |                            4 |                 1 |
| sf1           | hot         |            22 |                      0.954545 |                    0.636364 |             0.00189778  |             0.0520932 |                14 |                            7 |                 1 |
| sf3           | hot         |            22 |                      0.954545 |                    0.636364 |             0.00147291  |             0.0411185 |                14 |                            7 |                 1 |

## Hot-phase winner matrix

| official_id   | sf0.1                               | sf1                                    | sf3                                     |
|:--------------|:------------------------------------|:---------------------------------------|:----------------------------------------|
| IC1           | G0 / primary / p95=407.677          | G0 / primary / p95=2827.206            | G0 / primary / p95=5567.528             |
| IC2           | G3 / primary / p95=11.365           | G3 / primary / p95=16.605              | G0 / primary / p95=36.357               |
| IC3           | G3 / primary / p95=645.505          | G7 / secondary_affected / p95=3664.198 | G7 / secondary_affected / p95=5790.022  |
| IC4           | G0 / primary / p95=15.355           | G3 / primary / p95=61.062              | G0 / primary / p95=62.667               |
| IC5           | G3 / primary / p95=2962.312         | G7 / secondary_affected / p95=8636.625 | G9 / secondary_affected / p95=16242.847 |
| IC6           | G0 / primary / p95=49.478           | G0 / primary / p95=82.237              | G3 / primary / p95=99.29                |
| IC7           | G3 / primary / p95=0.781            | G6 / secondary_affected / p95=1.172    | G3 / primary / p95=0.859                |
| INS1          | G3 / primary / p95=0.992            | G3 / primary / p95=1.874               | G3 / primary / p95=1.234                |
| INS2          | G6 / primary / p95=1.07             | G6 / primary / p95=0.555               | G4 / primary / p95=1.665                |
| INS3          | G6 / primary / p95=1.3              | G6 / primary / p95=1.054               | G6 / primary / p95=1.113                |
| INS4          | G0 / primary / p95=1.989            | G3 / primary / p95=1.452               | G3 / primary / p95=1.982                |
| INS5          | G6 / primary / p95=0.652            | G6 / primary / p95=0.681               | G6 / primary / p95=0.591                |
| INS6          | G7 / secondary_affected / p95=1.562 | G7 / secondary_affected / p95=1.757    | G7 / secondary_affected / p95=1.019     |
| INS7          | G7 / secondary_affected / p95=1.109 | G7 / secondary_affected / p95=1.599    | G7 / secondary_affected / p95=1.596     |
| INS8          | G0 / primary / p95=0.513            | G3 / primary / p95=0.858               | G0 / primary / p95=0.508                |
| IS1           | G3 / primary / p95=0.332            | G3 / primary / p95=0.351               | G3 / primary / p95=0.286                |
| IS2           | G9 / secondary_affected / p95=1.376 | G9 / secondary_affected / p95=1.877    | G7 / secondary_affected / p95=1.288     |
| IS3           | G3 / primary / p95=0.704            | G3 / primary / p95=0.707               | G3 / primary / p95=0.704                |
| IS4           | G0 / control / p95=93.523           | G0 / control / p95=1247.114            | G0 / control / p95=4795.356             |
| IS5           | G0 / primary / p95=1.25             | G3 / primary / p95=0.55                | G3 / primary / p95=0.922                |
| IS6           | G9 / primary / p95=94.482           | G3 / secondary_affected / p95=1294.504 | G3 / secondary_affected / p95=4783.009  |
| IS7           | G9 / secondary_affected / p95=0.874 | G3 / primary / p95=1.258               | G7 / secondary_affected / p95=1.341     |

## Winner counts by group

| scale_label   | run_phase   | global_best_group   |   winner_count |
|:--------------|:------------|:--------------------|---------------:|
| sf0.1         | cold        | control             |              1 |
| sf0.1         | cold        | primary             |             14 |
| sf0.1         | cold        | secondary_affected  |              7 |
| sf0.1         | hot         | control             |              1 |
| sf0.1         | hot         | primary             |             17 |
| sf0.1         | hot         | secondary_affected  |              4 |
| sf1           | cold        | control             |              1 |
| sf1           | cold        | primary             |             15 |
| sf1           | cold        | secondary_affected  |              6 |
| sf1           | hot         | control             |              1 |
| sf1           | hot         | primary             |             14 |
| sf1           | hot         | secondary_affected  |              7 |
| sf3           | cold        | control             |              1 |
| sf3           | cold        | primary             |             18 |
| sf3           | cold        | secondary_affected  |              3 |
| sf3           | hot         | control             |              1 |
| sf3           | hot         | primary             |             14 |
| sf3           | hot         | secondary_affected  |              7 |

## Notes

- Activated candidates are defined as primary plus secondary_affected candidates.
- Activated regret is computed relative to the global best candidate for the same query, scale, and phase.
- Near-best candidates are candidates within 5% of the best p95 latency for the same query, scale, and phase.
- The benchmark protocol uses 10 measured cold repetitions and 10 measured hot repetitions, with no extra warmup repetitions.