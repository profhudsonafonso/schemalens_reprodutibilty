# Lima and Mello vs SchemaLens on FIBEN SF1

Protocol: 10 cold runs and 10 hot runs per query. Comparison uses hot-run p95 latency.

## Winner summary

| winner     |   n_queries |
|:-----------|------------:|
| SchemaLens |           7 |
| LMM        |           2 |

## Per-query comparison

| query_id   | winner     |   lmm_hot_p95_ms |   schemalens_best_hot_p95_ms |   lmm_over_schemalens_ratio |   lmm_mean_returned |   schemalens_mean_returned | comparability_flag   | schemalens_candidate_id                                                                                          | schemalens_group   | schemalens_g_class   |
|:-----------|:-----------|-----------------:|-----------------------------:|----------------------------:|--------------------:|---------------------------:|:---------------------|:-----------------------------------------------------------------------------------------------------------------|:-------------------|:---------------------|
| Q1         | SchemaLens |         0.338933 |                     0.233373 |                    1.45232  |                   1 |                        1   | cardinality_aligned  | q1_company_profile_ibm__control__normalized_reference_baseline                                                   | control            | CONTROL              |
| Q2         | SchemaLens |         0.636918 |                     0.117117 |                    5.43828  |                   1 |                        1   | cardinality_aligned  | q2_company_with_industry_country_and_listed_securities__g5__shared_targets_as_references                         | primary            | G5                   |
| Q3         | LMM        |         0.333562 |                     0.434946 |                    0.766903 |                   1 |                       10.6 | lmm_returns_less     | q3_securities_held_in_each_financial_service_account__g5__shared_targets_as_references                           | primary            | G5                   |
| Q4         | SchemaLens |        13.402    |                     1.00283  |                   13.3641   |                  61 |                       53.6 | cardinality_aligned  | q4_companies_reached_from_person_through_account_holding_listed_security__control__normalized_reference_baseline | control            | CONTROL              |
| Q5         | LMM        |         9.56432  |                    37.6268   |                    0.254189 |                  24 |                     6801   | lmm_returns_less     | q5_reports_and_metric_data_of_company__g2__embed_containment_children                                            | primary            | G2                   |
| Q6         | SchemaLens |       737.187    |                     0.385924 |                 1910.19     |                1000 |                      100   | lmm_returns_more     | q6_tech_uslisted_securities_with_high_last_traded_value__g9__tradeoff_benchmark_candidate                        | secondary_affected | G9                   |
| Q7         | SchemaLens |         1.41364  |                     1.187    |                    1.19094  |                  97 |                       97   | cardinality_aligned  | q7_persons_who_bought_more_ibmthan_sold__g4__deep_nested_path                                                    | primary            | G4                   |
| Q8         | SchemaLens |         1.25737  |                     0.863551 |                    1.45604  |                  87 |                       88   | cardinality_aligned  | q8_ibmtransactions_below_average_selling_price__g7__update_aware_references                                      | secondary_affected | G7                   |
| Q9         | SchemaLens |         1.42112  |                     0.851476 |                    1.669    |                   2 |                        0.3 | lmm_returns_more     | q9_persons_who_bought_and_sold_same_stock__g7__update_aware_references                                           | secondary_affected | G7                   |