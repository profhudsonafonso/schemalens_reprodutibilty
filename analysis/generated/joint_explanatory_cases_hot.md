# Joint explanatory cases - hot runs

This report combines baseline-separation and ablation-sensitivity evidence.

- Run phase: `hot`
- Strong-regret threshold: `0.1`
- Baseline-strong means SchemaLens preserves Top-1 while multiple deterministic baselines miss it.
- Ablation-strong means full SchemaLens preserves Top-1 while multiple ablated variants miss it.
- Joint-strong means both conditions occur for the same dataset/scale/query case.

## Case-type counts

| case_type                            |   count |
|:-------------------------------------|--------:|
| weak_or_redundant                    |      45 |
| joint_strong                         |      20 |
| baseline_strong                      |      13 |
| ablation_strong                      |      13 |
| baseline_strong_with_ablation_signal |       8 |
| ablation_strong_with_baseline_signal |       7 |
| ablation_moderate                    |       2 |
| baseline_moderate                    |       1 |

## Top case-level candidates

| dataset   | scale_label   | query_name                                       | global_best_g_class   |   global_best_p95 |   baseline_miss_count |   baseline_max_miss_regret |   ablation_miss_count |   ablation_max_miss_regret | case_type                            |   joint_score |
|:----------|:--------------|:-------------------------------------------------|:----------------------|------------------:|----------------------:|---------------------------:|----------------------:|---------------------------:|:-------------------------------------|--------------:|
| ldbc_snb  | sf1           | INS5_AddForumMembership                          | G4                    |            2.4010 |                     3 |                     4.4598 |                     4 |                     4.4598 | joint_strong                         |       32.3793 |
| ldbc_snb  | sf0.1         | INS1_AddPerson                                   | G3                    |            1.1844 |                     3 |                     1.0907 |                     6 |                     1.0907 | joint_strong                         |       25.3629 |
| ldbc_snb  | sf1           | INS1_AddPerson                                   | G3                    |            1.6241 |                     3 |                     0.4702 |                     6 |                     0.4702 | joint_strong                         |       22.8807 |
| ldbc_snb  | sf0.1         | INS7_AddComment                                  | G3                    |            1.1866 |                     3 |                     0.6497 |                     6 |                     0.0530 | baseline_strong                      |       22.8266 |
| ldbc_snb  | sf3           | INS4_AddForum                                    | G3                    |            1.4340 |                     3 |                     0.3957 |                     6 |                     0.3957 | joint_strong                         |       22.5829 |
| ldbc_snb  | sf3           | IS1_ProfileOfPerson                              | G3                    |            1.2298 |                     3 |                     0.1085 |                     6 |                     0.1085 | joint_strong                         |       21.4340 |
| ldbc_snb  | sf3           | INS1_AddPerson                                   | G3                    |            1.4326 |                     3 |                     0.0449 |                     6 |                     0.0449 | weak_or_redundant                    |       21.1796 |
| ldbc_snb  | sf0.1         | INS5_AddForumMembership                          | G4                    |            1.1133 |                     3 |                     1.1541 |                     4 |                     1.1541 | joint_strong                         |       21.0393 |
| ldbc_snb  | sf1           | IC7_RecentLikers                                 | G3                    |            7.0093 |                     1 |                     0.7492 |                     6 |                     2.6478 | ablation_strong_with_baseline_signal |       21.0356 |
| ldbc_snb  | sf0.1         | INS3_AddLikeToComment                            | G4                    |            1.2223 |                     3 |                     0.8463 |                     4 |                     0.8463 | joint_strong                         |       19.9621 |
| ldbc_snb  | sf3           | INS3_AddLikeToComment                            | G4                    |            1.3124 |                     3 |                     0.6239 |                     4 |                     0.6239 | joint_strong                         |       19.1835 |
| ldbc_snb  | sf3           | INS8_AddFriendship                               | G3                    |            1.5669 |                     2 |                     0.0000 |                     6 |                     0.5902 | ablation_strong                      |       19.1804 |
| imdb      | sf0.5         | QG9_TopRatedSeriesByGenre                        | G7                    |            2.0542 |                     3 |                    37.0366 |                     1 |                     0.8960 | baseline_strong_with_ablation_signal |       18.6880 |
| ldbc_snb  | sf0.1         | IS3_FriendsOfPerson                              | G3                    |            2.8537 |                     2 |                     0.0000 |                     6 |                     0.2370 | ablation_strong                      |       18.4740 |
| ldbc_snb  | sf0.1         | INS8_AddFriendship                               | G3                    |            1.9487 |                     2 |                     0.0000 |                     6 |                     0.2045 | ablation_strong                      |       18.4089 |
| ldbc_snb  | sf1           | INS8_AddFriendship                               | G3                    |            1.9326 |                     2 |                     0.0000 |                     6 |                     0.0680 | weak_or_redundant                    |       18.1361 |
| fiben     | sf10          | Q2_CompanyWithIndustryCountryAndListedSecurities | G1                    |            0.1554 |                     4 |                     0.7593 |                     2 |                     0.7593 | joint_strong                         |       17.5918 |
| ldbc_snb  | sf0.1         | INS2_AddLikeToPost                               | G4                    |            1.0496 |                     3 |                     0.1298 |                     4 |                     0.1298 | joint_strong                         |       17.4544 |
| ldbc_snb  | sf3           | INS2_AddLikeToPost                               | G6                    |            1.6308 |                     3 |                     0.5479 |                     3 |                     0.5479 | joint_strong                         |       16.8264 |
| imdb      | sf1           | QG9_TopRatedSeriesByGenre                        | G7                    |            4.0780 |                     3 |                    38.0907 |                     1 |                     0.2349 | baseline_strong_with_ablation_signal |       16.7047 |
| ldbc_snb  | sf0.1         | IS2_RecentMessagesOfPerson                       | G6                    |            2.2558 |                     3 |                     0.8848 |                     3 |                     0.0367 | baseline_strong                      |       16.6128 |
| ldbc_snb  | sf3           | IS4_ContentOfMessage                             | G1                    |            1.2614 |                     3 |                     1.0574 |                     2 |                     1.0574 | joint_strong                         |       16.5823 |
| imdb      | sf0.25        | QG9_TopRatedSeriesByGenre                        | G7                    |            3.0066 |                     3 |                    12.3697 |                     1 |                     0.1216 | baseline_strong_with_ablation_signal |       16.3649 |
| ldbc_snb  | sf0.1         | IS6_ForumOfMessage                               | G9                    |            1.1708 |                     2 |                     0.0610 |                     3 |                     2.8790 | ablation_strong                      |       16.2869 |
| ldbc_snb  | sf3           | INS5_AddForumMembership                          | G6                    |            1.6525 |                     3 |                     0.3706 |                     3 |                     0.3706 | joint_strong                         |       16.2354 |
| ldbc_snb  | sf0.1         | IC7_RecentLikers                                 | G4                    |            7.4644 |                     2 |                     0.3591 |                     4 |                     0.3591 | joint_strong                         |       15.7957 |
| ldbc_snb  | sf0.1         | IC4_NewTopics                                    | G3                    |           44.0561 |                     1 |                     0.0000 |                     6 |                     0.3916 | ablation_strong                      |       15.7833 |
| fiben     | sf1           | Q5_ReportsAndMetricDataOfCompany                 | G2                    |           37.6268 |                     3 |                     0.2446 |                     3 |                     0.1105 | joint_strong                         |       15.6945 |
| imdb      | sf1           | QG4_AllPersonsOfTypeForWatchItem                 | G6                    |            0.2024 |                     1 |                     0.6599 |                     3 |                     2.6487 | ablation_strong_with_baseline_signal |       15.6284 |
| fiben     | sf1           | Q2_CompanyWithIndustryCountryAndListedSecurities | G5                    |            0.1171 |                     3 |                     0.1412 |                     3 |                     0.0999 | baseline_strong                      |       15.5621 |

## Top query-level candidates

| dataset   | query_name                                       |   scale_count | winner_sequence           |   baseline_miss_total |   baseline_max_regret |   ablation_miss_total |   ablation_max_regret | case_types                                                             |   joint_score_sum |
|:----------|:-------------------------------------------------|--------------:|:--------------------------|----------------------:|----------------------:|----------------------:|----------------------:|:-----------------------------------------------------------------------|------------------:|
| ldbc_snb  | INS5_AddForumMembership                          |             3 | sf1:G4|sf0.1:G4|sf3:G6    |                     9 |                4.4598 |                    11 |                4.4598 | joint_strong                                                           |           69.6540 |
| ldbc_snb  | INS1_AddPerson                                   |             3 | sf0.1:G3|sf1:G3|sf3:G3    |                     9 |                1.0907 |                    18 |                1.0907 | joint_strong|weak_or_redundant                                         |           69.4232 |
| ldbc_snb  | INS8_AddFriendship                               |             3 | sf3:G3|sf0.1:G3|sf1:G3    |                     6 |                0.0000 |                    18 |                0.5902 | ablation_strong|weak_or_redundant                                      |           55.7254 |
| ldbc_snb  | INS3_AddLikeToComment                            |             3 | sf0.1:G4|sf3:G4|sf1:G6    |                     9 |                0.8463 |                    11 |                0.8463 | joint_strong                                                           |           54.4861 |
| ldbc_snb  | IC7_RecentLikers                                 |             3 | sf1:G3|sf0.1:G4|sf3:G4    |                     5 |                0.7492 |                    14 |                2.6478 | ablation_strong_with_baseline_signal|joint_strong                      |           51.8831 |
| imdb      | QG9_TopRatedSeriesByGenre                        |             3 | sf0.5:G7|sf1:G7|sf0.25:G7 |                     9 |               38.0907 |                     3 |                0.8960 | baseline_strong_with_ablation_signal                                   |           51.7576 |
| ldbc_snb  | INS2_AddLikeToPost                               |             3 | sf0.1:G4|sf3:G6|sf1:G6    |                     9 |                0.5479 |                    10 |                0.5479 | joint_strong                                                           |           49.8039 |
| fiben     | Q2_CompanyWithIndustryCountryAndListedSecurities |             3 | sf10:G1|sf1:G5|sf30:G9    |                     9 |                5.1483 |                     6 |                0.7593 | baseline_strong|joint_strong                                           |           47.3607 |
| ldbc_snb  | IC1_TransitiveFriendsWithName                    |             3 | sf0.1:G3|sf1:G3|sf3:G3    |                     3 |                0.0000 |                    18 |                0.1615 | ablation_strong|weak_or_redundant                                      |           45.6471 |
| imdb      | QG3_RecommendationByGenreAndSubtype              |             3 | sf0.25:G8|sf0.5:G8|sf1:G8 |                     6 |                0.0955 |                    12 |                0.0597 | weak_or_redundant                                                      |           42.6098 |
| ldbc_snb  | INS7_AddComment                                  |             3 | sf0.1:G3|sf1:G9|sf3:G7    |                     6 |                0.7611 |                    10 |                0.1323 | baseline_strong|baseline_strong_with_ablation_signal|weak_or_redundant |           40.7922 |
| imdb      | QG4_AllPersonsOfTypeForWatchItem                 |             3 | sf1:G6|sf0.25:G6|sf0.5:G5 |                     3 |                0.7146 |                     9 |                2.6487 | ablation_strong|ablation_strong_with_baseline_signal                   |           39.5499 |
| ldbc_snb  | IS6_ForumOfMessage                               |             3 | sf0.1:G9|sf1:G9|sf3:G0    |                     6 |                1.4082 |                     6 |                2.8790 | ablation_strong|baseline_strong|weak_or_redundant                      |           35.1922 |
| ldbc_snb  | IC6_TagCoOccurrence                              |             3 | sf1:G3|sf0.1:G3|sf3:G0    |                     4 |                0.0483 |                    12 |                0.2470 | ablation_strong|weak_or_redundant                                      |           34.5795 |
| ldbc_snb  | IS2_RecentMessagesOfPerson                       |             3 | sf0.1:G6|sf1:G9|sf3:G0    |                     7 |                0.9106 |                     6 |                0.0863 | baseline_strong|weak_or_redundant                                      |           34.5127 |
| ldbc_snb  | IC2_RecentMessagesByFriends                      |             3 | sf1:G3|sf0.1:G3|sf3:G0    |                     4 |                0.0055 |                    12 |                0.1365 | ablation_strong|weak_or_redundant                                      |           34.2987 |
| imdb      | QG5_AllPersonsForEpisodesOfSeries                |             3 | sf0.5:G4|sf0.25:G4|sf1:G4 |                     3 |                0.4070 |                     9 |                0.4365 | ablation_strong_with_baseline_signal                                   |           32.4787 |
| ldbc_snb  | IC5_NewGroups                                    |             3 | sf1:G6|sf0.1:G7|sf3:G7    |                     8 |                0.1848 |                     5 |                0.0454 | baseline_strong|weak_or_redundant                                      |           30.8053 |
| ldbc_snb  | INS4_AddForum                                    |             3 | sf3:G3|sf0.1:G0|sf1:G0    |                     7 |                0.3957 |                     6 |                0.3957 | joint_strong|weak_or_redundant                                         |           30.5829 |
| ldbc_snb  | IS1_ProfileOfPerson                              |             3 | sf3:G3|sf0.1:G0|sf1:G0    |                     7 |                0.1085 |                     6 |                0.1085 | joint_strong|weak_or_redundant                                         |           29.4340 |

## Recommended reading of the results

- Use `baseline_strong` or `baseline_strong_with_ablation_signal` cases to explain why fixed heuristics are unstable.
- Use `ablation_strong` or `ablation_strong_with_baseline_signal` cases to explain why analytical variables matter.
- Use `joint_strong` cases, if present, as the most complete examples connecting baselines, ablation, workload structure, and winners.
- Cases like FIBEN Q2 may be excellent baseline-separation cases even if ablation is moderate, because several SchemaLens signals may overlap.

