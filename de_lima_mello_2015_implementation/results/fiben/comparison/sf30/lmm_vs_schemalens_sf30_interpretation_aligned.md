# Lima and Mello vs SchemaLens on FIBEN SF30

Protocol: 10 cold runs and 10 hot runs per query. Comparison uses hot-run p95 latency.

## Winner summary

| winner     |   n_queries |
|:-----------|------------:|
| SchemaLens |           5 |
| LMM        |           4 |

## Per-query comparison

| query_id   | winner     |   lmm_hot_p95_ms |   schemalens_best_hot_p95_ms |   lmm_over_schemalens_ratio |   lmm_mean_returned |   schemalens_mean_returned | comparability_flag   | schemalens_candidate_id                                                                        | schemalens_group   | schemalens_g_class   |
|:-----------|:-----------|-----------------:|-----------------------------:|----------------------------:|--------------------:|---------------------------:|:---------------------|:-----------------------------------------------------------------------------------------------|:-------------------|:---------------------|
| Q1         | LMM        |         0.189443 |                     0.224772 |                   0.842823  |                   1 |                        1   | cardinality_aligned  | q1_company_profile_ibm__g0__root_only                                                          | primary            | G0                   |
| Q2         | SchemaLens |         0.520801 |                     0.250701 |                   2.07738   |                   1 |                        1   | cardinality_aligned  | q2_company_with_industry_country_and_listed_securities__g9__tradeoff_benchmark_candidate       | secondary_affected | G9                   |
| Q3         | LMM        |         0.562268 |                     1.65204  |                   0.340348  |                   1 |                      149.8 | lmm_returns_less     | q3_securities_held_in_each_financial_service_account__g5__shared_targets_as_references         | primary            | G5                   |
| Q4         | LMM        |         8.9      |                    17.1424   |                   0.519182  |                  61 |                     1608   | lmm_returns_less     | q4_companies_reached_from_person_through_account_holding_listed_security__g4__deep_nested_path | primary            | G4                   |
| Q5         | LMM        |         0.715147 |                    45.2172   |                   0.0158158 |                  24 |                     6801   | lmm_returns_less     | q5_reports_and_metric_data_of_company__control__normalized_reference_baseline                  | control            | CONTROL              |
| Q6         | SchemaLens |     24358.6      |                   418.835    |                  58.1579    |                1000 |                      100   | lmm_returns_more     | q6_tech_uslisted_securities_with_high_last_traded_value__g3__association_references            | primary            | G3                   |
| Q7         | SchemaLens |         1.45666  |                     1.32228  |                   1.10163   |                  97 |                       97   | cardinality_aligned  | q7_persons_who_bought_more_ibmthan_sold__g3__association_references                            | primary            | G3                   |
| Q8         | SchemaLens |         1.42846  |                     1.29288  |                   1.10487   |                  87 |                       88   | cardinality_aligned  | q8_ibmtransactions_below_average_selling_price__g5__shared_targets_as_references               | primary            | G5                   |
| Q9         | SchemaLens |         2.00734  |                     1.22386  |                   1.64017   |                   2 |                        0.3 | lmm_returns_more     | q9_persons_who_bought_and_sold_same_stock__g7__update_aware_references                         | secondary_affected | G7                   |