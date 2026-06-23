# LDBC SNB Physical Query-Plan Analysis

This report consolidates MongoDB explain executionStats JSON files generated during the physical LDBC SNB benchmark.

## Scale-level summary

| scale_label   |   candidate_phase_rows |   component_rows |   total_docs_examined |   total_keys_examined |   rows_with_ixscan |   rows_with_collscan |   rows_with_sort |   rows_with_lookup |   rows_with_group |   rows_with_unwind |
|:--------------|-----------------------:|-----------------:|----------------------:|----------------------:|-------------------:|---------------------:|-----------------:|-------------------:|------------------:|-------------------:|
| sf0.1         |                    128 |              316 |                 15084 |                 15248 |                 76 |                    0 |               26 |                  0 |                 0 |                  0 |
| sf1           |                    128 |              316 |                 41044 |                 41224 |                 76 |                    0 |               26 |                  0 |                 0 |                  0 |
| sf3           |                    128 |              316 |                 85654 |                 85894 |                 76 |                    0 |               26 |                  0 |                 0 |                  0 |

## Hot winners with query-plan evidence

| scale_label   | official_id   | g_class   | benchmark_group    |   p95_latency_ms |   total_docs_examined |   total_keys_examined | has_IXSCAN   | has_COLLSCAN   | has_SORT   | has_LOOKUP   | has_GROUP   | has_UNWIND   |
|:--------------|:--------------|:----------|:-------------------|-----------------:|----------------------:|----------------------:|:-------------|:---------------|:-----------|:-------------|:------------|:-------------|
| sf0.1         | IC1           | G0        | primary            |       407.677    |                     5 |                     5 | True         | False          | False      | False        | False       | False        |
| sf0.1         | IC2           | G3        | primary            |        11.3646   |                  1596 |                  1602 | True         | False          | True       | False        | False       | False        |
| sf0.1         | IC3           | G3        | primary            |       645.505    |                   125 |                   125 | True         | False          | False      | False        | False       | False        |
| sf0.1         | IC4           | G0        | primary            |        15.3551   |                   530 |                   540 | True         | False          | True       | False        | False       | False        |
| sf0.1         | IC5           | G3        | primary            |      2962.31     |                    46 |                    47 | True         | False          | False      | False        | False       | False        |
| sf0.1         | IC6           | G0        | primary            |        49.4785   |                    44 |                    48 | True         | False          | False      | False        | False       | False        |
| sf0.1         | IC7           | G3        | primary            |         0.780906 |                     1 |                     1 | True         | False          | False      | False        | False       | False        |
| sf0.1         | INS1          | G3        | primary            |         0.991834 |                   nan |                   nan |              |                |            |              |             |              |
| sf0.1         | INS2          | G6        | primary            |         1.07025  |                   nan |                   nan |              |                |            |              |             |              |
| sf0.1         | INS3          | G6        | primary            |         1.30031  |                   nan |                   nan |              |                |            |              |             |              |
| sf0.1         | INS4          | G0        | primary            |         1.98922  |                   nan |                   nan |              |                |            |              |             |              |
| sf0.1         | INS5          | G6        | primary            |         0.651735 |                   nan |                   nan |              |                |            |              |             |              |
| sf0.1         | INS6          | G7        | secondary_affected |         1.56204  |                   nan |                   nan |              |                |            |              |             |              |
| sf0.1         | INS7          | G7        | secondary_affected |         1.10863  |                   nan |                   nan |              |                |            |              |             |              |
| sf0.1         | INS8          | G0        | primary            |         0.513484 |                   nan |                   nan |              |                |            |              |             |              |
| sf0.1         | IS1           | G3        | primary            |         0.332335 |                     1 |                     1 | False        | False          | False      | False        | False       | False        |
| sf0.1         | IS2           | G9        | secondary_affected |         1.37614  |                   412 |                   412 | True         | False          | True       | False        | False       | False        |
| sf0.1         | IS3           | G3        | primary            |         0.704153 |                     3 |                     3 | True         | False          | False      | False        | False       | False        |
| sf0.1         | IS4           | G0        | control            |        93.523    |                     1 |                     1 | False        | False          | False      | False        | False       | False        |
| sf0.1         | IS5           | G0        | primary            |         1.25018  |                     1 |                     1 | False        | False          | False      | False        | False       | False        |
| sf0.1         | IS6           | G9        | primary            |        94.4819   |                     1 |                     1 | True         | False          | False      | False        | False       | False        |
| sf0.1         | IS7           | G9        | secondary_affected |         0.87405  |                     4 |                     4 | True         | False          | False      | False        | False       | False        |
| sf1           | IC1           | G0        | primary            |      2827.21     |                    10 |                    10 | True         | False          | False      | False        | False       | False        |
| sf1           | IC2           | G3        | primary            |        16.6052   |                  6688 |                  6693 | True         | False          | True       | False        | False       | False        |
| sf1           | IC3           | G7        | secondary_affected |      3664.2      |                     6 |                     6 | True         | False          | False      | False        | False       | False        |
| sf1           | IC4           | G3        | primary            |        61.0618   |                  2067 |                  2079 | True         | False          | True       | False        | False       | False        |
| sf1           | IC5           | G7        | secondary_affected |      8636.63     |                    41 |                    41 | True         | False          | False      | False        | False       | False        |
| sf1           | IC6           | G0        | primary            |        82.2368   |                    46 |                    56 | True         | False          | False      | False        | False       | False        |
| sf1           | IC7           | G6        | secondary_affected |         1.17221  |                    15 |                    20 | True         | False          | True       | False        | False       | False        |
| sf1           | INS1          | G3        | primary            |         1.87424  |                   nan |                   nan |              |                |            |              |             |              |
| sf1           | INS2          | G6        | primary            |         0.555136 |                   nan |                   nan |              |                |            |              |             |              |
| sf1           | INS3          | G6        | primary            |         1.05414  |                   nan |                   nan |              |                |            |              |             |              |
| sf1           | INS4          | G3        | primary            |         1.45195  |                   nan |                   nan |              |                |            |              |             |              |
| sf1           | INS5          | G6        | primary            |         0.680568 |                   nan |                   nan |              |                |            |              |             |              |
| sf1           | INS6          | G7        | secondary_affected |         1.7575   |                   nan |                   nan |              |                |            |              |             |              |
| sf1           | INS7          | G7        | secondary_affected |         1.59862  |                   nan |                   nan |              |                |            |              |             |              |
| sf1           | INS8          | G3        | primary            |         0.858354 |                   nan |                   nan |              |                |            |              |             |              |
| sf1           | IS1           | G3        | primary            |         0.351455 |                     1 |                     1 | False        | False          | False      | False        | False       | False        |
| sf1           | IS2           | G9        | secondary_affected |         1.87659  |                   370 |                   370 | True         | False          | True       | False        | False       | False        |
| sf1           | IS3           | G3        | primary            |         0.706883 |                     5 |                     5 | True         | False          | False      | False        | False       | False        |
| sf1           | IS4           | G0        | control            |      1247.11     |                     1 |                     1 | False        | False          | False      | False        | False       | False        |
| sf1           | IS5           | G3        | primary            |         0.550412 |                     1 |                     1 | False        | False          | False      | False        | False       | False        |
| sf1           | IS6           | G3        | secondary_affected |      1294.5      |                     1 |                     1 | True         | False          | False      | False        | False       | False        |
| sf1           | IS7           | G3        | primary            |         1.25797  |                     4 |                     4 | True         | False          | False      | False        | False       | False        |
| sf3           | IC1           | G0        | primary            |      5567.53     |                    20 |                    20 | True         | False          | False      | False        | False       | False        |
| sf3           | IC2           | G0        | primary            |        36.3568   |                 15528 |                 15536 | True         | False          | True       | False        | False       | False        |
| sf3           | IC3           | G7        | secondary_affected |      5790.02     |                     9 |                     9 | True         | False          | False      | False        | False       | False        |
| sf3           | IC4           | G0        | primary            |        62.6666   |                  4161 |                  4173 | True         | False          | True       | False        | False       | False        |
| sf3           | IC5           | G9        | secondary_affected |     16242.8      |                    42 |                    42 | True         | False          | False      | False        | False       | False        |
| sf3           | IC6           | G3        | primary            |        99.2899   |                    50 |                    54 | True         | False          | False      | False        | False       | False        |
| sf3           | IC7           | G3        | primary            |         0.858621 |                     1 |                     1 | True         | False          | False      | False        | False       | False        |
| sf3           | INS1          | G3        | primary            |         1.23365  |                   nan |                   nan |              |                |            |              |             |              |
| sf3           | INS2          | G4        | primary            |         1.66491  |                   nan |                   nan |              |                |            |              |             |              |
| sf3           | INS3          | G6        | primary            |         1.1133   |                   nan |                   nan |              |                |            |              |             |              |
| sf3           | INS4          | G3        | primary            |         1.98157  |                   nan |                   nan |              |                |            |              |             |              |
| sf3           | INS5          | G6        | primary            |         0.591354 |                   nan |                   nan |              |                |            |              |             |              |
| sf3           | INS6          | G7        | secondary_affected |         1.01882  |                   nan |                   nan |              |                |            |              |             |              |
| sf3           | INS7          | G7        | secondary_affected |         1.596    |                   nan |                   nan |              |                |            |              |             |              |
| sf3           | INS8          | G0        | primary            |         0.507634 |                   nan |                   nan |              |                |            |              |             |              |
| sf3           | IS1           | G3        | primary            |         0.28569  |                     1 |                     1 | False        | False          | False      | False        | False       | False        |
| sf3           | IS2           | G7        | secondary_affected |         1.28807  |                   418 |                   418 | True         | False          | True       | False        | False       | False        |
| sf3           | IS3           | G3        | primary            |         0.704401 |                     8 |                     8 | True         | False          | False      | False        | False       | False        |
| sf3           | IS4           | G0        | control            |      4795.36     |                     1 |                     1 | False        | False          | False      | False        | False       | False        |
| sf3           | IS5           | G3        | primary            |         0.921583 |                     1 |                     1 | False        | False          | False      | False        | False       | False        |
| sf3           | IS6           | G3        | secondary_affected |      4783.01     |                     1 |                     1 | True         | False          | False      | False        | False       | False        |
| sf3           | IS7           | G7        | secondary_affected |         1.34114  |                     4 |                     4 | True         | False          | False      | False        | False       | False        |

## Notes

- Component rows correspond to individual explain JSON files.
- Candidate summaries aggregate all explain components for the same scale, query, phase, and candidate.
- The joined file links benchmark latency with query-plan metrics.
- Raw JSON files are not copied to the repository; only consolidated CSV/Markdown artifacts should be committed.