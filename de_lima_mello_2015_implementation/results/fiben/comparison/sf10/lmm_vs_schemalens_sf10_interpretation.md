# Lima & Mello vs SchemaLens on FIBEN SF10

Protocol: 10 cold runs and 10 hot runs per query. Comparison uses hot p95 latency.


## Winner summary

| winner     |   n_queries |
|:-----------|------------:|
| SchemaLens |           7 |
| LMM        |           2 |


## Per-query interpretation

| query_id   | winner     |   lmm_hot_p95_ms |   schemalens_best_hot_p95_ms |   lmm_over_schemalens_ratio |   lmm_mean_returned |   schemalens_mean_returned | comparability_flag   | interpretation_note                                                                      |
|:-----------|:-----------|-----------------:|-----------------------------:|----------------------------:|--------------------:|---------------------------:|:---------------------|:-----------------------------------------------------------------------------------------|
| Q1         | SchemaLens |         0.318401 |                     0.295784 |                   1.07646   |                   1 |                        1   | cardinality_aligned  | Near tie; same returned cardinality.                                                     |
| Q2         | SchemaLens |         0.65767  |                     0.155368 |                   4.23298   |                   1 |                        1   | cardinality_aligned  | Clear SchemaLens win with same returned cardinality.                                     |
| Q3         | LMM        |         0.307812 |                     0.899143 |                   0.342339  |                   1 |                       53.8 | lmm_returns_less     | LMM is faster, but returns far fewer documents; interpret with cardinality caution.      |
| Q4         | SchemaLens |         9.04895  |                     4.30841  |                   2.1003    |                  61 |                      536   | lmm_returns_less     | Strong SchemaLens win; faster despite returning more documents.                          |
| Q5         | LMM        |         0.689555 |                    28.4328   |                   0.0242521 |                  24 |                     6801   | lmm_returns_less     | LMM is faster, but returns far fewer documents; not a clean semantic win without caveat. |
| Q6         | SchemaLens |      2944.97     |                    91.4743   |                  32.1945    |                1000 |                      100   | lmm_returns_more     | Strong SchemaLens win; LMM is much slower and returns more documents.                    |
| Q7         | SchemaLens |         1.37993  |                     0.857698 |                   1.60888   |                  97 |                       97   | cardinality_aligned  | Clean SchemaLens win; returned cardinality is aligned.                                   |
| Q8         | SchemaLens |         1.37605  |                     0.921652 |                   1.49303   |                  87 |                       88   | cardinality_aligned  | Clean/near-clean SchemaLens win; returned cardinality is almost aligned.                 |
| Q9         | SchemaLens |         1.44156  |                     1.05687  |                   1.36399   |                   2 |                        0.3 | lmm_returns_more     | SchemaLens win, but low-cardinality query with small parameter-pool difference.          |

