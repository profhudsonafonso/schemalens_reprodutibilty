# Final Lima and Mello SF10 query-plan summary

This file summarizes the final query-plan validation after aligning the Lima and Mello SF10 runner with the SchemaLens benchmark parameters.


## Final parameters

| Parameter | Value |
|---|---|
| corporation_id | 2860 |
| corporation_ticker | IBM |
| person_id_for_q4 | SF10_PERS_R01_400000035163 |
| corporation_security_ids | ['SF10_SEC_R01_1002518'] |
| q9_listed_security_id | SF10_SEC_R01_1001538 |

## Query-plan results

| query_id   | status    |   n_returned_accumulated |   total_docs_examined_accumulated |   total_keys_examined_accumulated |   execution_time_ms_max | has_ixscan   | has_collscan   | has_group   | interpretation_note                                                                    |
|:-----------|:----------|-------------------------:|----------------------------------:|----------------------------------:|------------------------:|:-------------|:---------------|:------------|:---------------------------------------------------------------------------------------|
| Q1         | completed |                        5 |                                 1 |                                 1 |                       0 | True         | False          | False       | Completed with index usage and no collection scan.                                     |
| Q2         | completed |                       35 |                                 4 |                                 4 |                       0 | True         | False          | False       | Completed with index usage and no collection scan.                                     |
| Q3         | completed |                        5 |                                 1 |                                 1 |                       0 | True         | False          | False       | Completed with index usage and no collection scan.                                     |
| Q4         | completed |                      317 |                                62 |                                62 |                      11 | True         | False          | False       | Uses Q4-compatible person parameter; now returns non-zero benchmark results.           |
| Q5         | completed |                       77 |                                 1 |                                 1 |                       0 | True         | False          | False       | Completed with index usage and no collection scan.                                     |
| Q6         | completed |                   199343 |                            601029 |                              1000 |                    2790 | False        | True           | False       | Main LMM query-plan outlier: COLLSCAN, no IXSCAN, and high documents examined.         |
| Q7         | completed |                     1268 |                               179 |                               179 |                       8 | True         | False          | True        | Uses indexed transaction access and grouping; aligned with final benchmark parameters. |
| Q8         | completed |                     1428 |                               179 |                               179 |                       1 | True         | False          | True        | Uses indexed transaction access and grouping; aligned with final benchmark parameters. |
| Q9         | completed |                     2513 |                               458 |                               458 |                      10 | True         | False          | True        | Uses indexed transaction access and grouping; aligned with final benchmark parameters. |


## Interpretation

- All Q1--Q9 query-plan executions completed successfully.
- Q4 now uses a valid person with a complete path and is consistent with the final benchmark.
- Q7 and Q8 now use the deterministic IBM security variant that avoids artificial SF10 replica multiplication.
- Q6 is the main query-plan outlier: it uses a collection scan, does not use an index scan, examines 601029 documents, and explains the very high LMM p95 latency observed in the final benchmark.
- Q7, Q8, and Q9 use indexed transaction access and grouping operations, which is consistent with the expected query semantics.