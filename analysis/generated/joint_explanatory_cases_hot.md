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
| weak_or_redundant                    |      41 |
| joint_strong                         |      21 |
| baseline_strong_with_ablation_signal |      14 |
| ablation_strong                      |      10 |
| ablation_strong_with_baseline_signal |       9 |
| baseline_strong                      |       9 |
| ablation_moderate                    |       2 |
| baseline_moderate                    |       1 |

## Top case-level candidates

| dataset   | scale_label   | query_name                                       | global_best_g_class   |   global_best_p95 |   baseline_miss_count |   baseline_max_miss_regret |   ablation_miss_count |   ablation_max_miss_regret | case_type                            |   joint_score |
|:----------|:--------------|:-------------------------------------------------|:----------------------|------------------:|----------------------:|---------------------------:|----------------------:|---------------------------:|:-------------------------------------|--------------:|
| ldbc_snb  | sf3           | IC7_RecentLikers                                 | G3                    |            0.8586 |                     1 |                     1.0786 |                     6 |                     4.8735 | ablation_strong_with_baseline_signal |       25.1092 |
| ldbc_snb  | sf3           | INS1_AddPerson                                   | G3                    |            1.2337 |                     3 |                     0.9828 |                     6 |                     0.9828 | joint_strong                         |       24.9312 |
| ldbc_snb  | sf3           | IS1_ProfileOfPerson                              | G3                    |            0.2857 |                     3 |                     0.9634 |                     6 |                     0.9634 | joint_strong                         |       24.8538 |
| ldbc_snb  | sf1           | IS1_ProfileOfPerson                              | G3                    |            0.3515 |                     3 |                     0.6185 |                     6 |                     0.6185 | joint_strong                         |       23.4741 |
| ldbc_snb  | sf0.1         | INS1_AddPerson                                   | G3                    |            0.9918 |                     3 |                     0.4009 |                     6 |                     0.4009 | joint_strong                         |       22.6036 |
| ldbc_snb  | sf1           | IS7_RepliesOfMessage                             | G3                    |            1.2580 |                     3 |                     0.1379 |                     6 |                     0.4087 | joint_strong                         |       22.0584 |
| ldbc_snb  | sf1           | INS4_AddForum                                    | G3                    |            1.4520 |                     3 |                     0.2287 |                     6 |                     0.2287 | joint_strong                         |       21.9147 |
| ldbc_snb  | sf3           | INS4_AddForum                                    | G3                    |            1.9816 |                     3 |                     0.2261 |                     6 |                     0.2261 | joint_strong                         |       21.9045 |
| ldbc_snb  | sf1           | INS2_AddLikeToPost                               | G6                    |            0.5551 |                     3 |                     2.0416 |                     3 |                     2.0416 | joint_strong                         |       21.8052 |
| ldbc_snb  | sf1           | INS1_AddPerson                                   | G3                    |            1.8742 |                     3 |                     0.0935 |                     6 |                     0.0935 | weak_or_redundant                    |       21.3741 |
| ldbc_snb  | sf0.1         | IS1_ProfileOfPerson                              | G3                    |            0.3323 |                     3 |                     0.0909 |                     6 |                     0.0909 | weak_or_redundant                    |       21.3638 |
| ldbc_snb  | sf3           | IS3_FriendsOfPerson                              | G3                    |            0.7044 |                     2 |                     0.0000 |                     6 |                     1.5049 | ablation_strong                      |       21.0098 |
| ldbc_snb  | sf0.1         | IC7_RecentLikers                                 | G3                    |            0.7809 |                     1 |                     0.2223 |                     6 |                     3.5315 | ablation_strong_with_baseline_signal |       20.4511 |
| ldbc_snb  | sf0.1         | INS5_AddForumMembership                          | G6                    |            0.6517 |                     3 |                     1.3329 |                     3 |                     1.3329 | joint_strong                         |       19.4431 |
| ldbc_snb  | sf1           | IS5_CreatorOfMessage                             | G3                    |            0.5504 |                     2 |                     0.0000 |                     6 |                     0.6515 | ablation_strong                      |       19.3030 |
| ldbc_snb  | sf3           | IS5_CreatorOfMessage                             | G3                    |            0.9216 |                     2 |                     0.0000 |                     6 |                     0.6018 | ablation_strong                      |       19.2036 |
| ldbc_snb  | sf1           | IS3_FriendsOfPerson                              | G3                    |            0.7069 |                     2 |                     0.0000 |                     6 |                     0.5915 | ablation_strong                      |       19.1829 |
| ldbc_snb  | sf1           | INS5_AddForumMembership                          | G6                    |            0.6806 |                     3 |                     1.2452 |                     3 |                     1.2452 | joint_strong                         |       19.1507 |
| ldbc_snb  | sf0.1         | IS3_FriendsOfPerson                              | G3                    |            0.7042 |                     2 |                     0.0000 |                     6 |                     0.5021 | ablation_strong                      |       19.0042 |
| imdb      | sf0.5         | QG9_TopRatedSeriesByGenre                        | G7                    |            2.0542 |                     3 |                    37.0366 |                     1 |                     0.8960 | baseline_strong_with_ablation_signal |       18.6880 |
| ldbc_snb  | sf1           | IS6_ForumOfMessage                               | G3                    |         1294.5043 |                     2 |                     0.0961 |                     6 |                     0.0578 | weak_or_redundant                    |       18.4041 |
| ldbc_snb  | sf3           | IS6_ForumOfMessage                               | G3                    |         4783.0087 |                     2 |                     0.0533 |                     6 |                     0.0530 | weak_or_redundant                    |       18.2392 |
| ldbc_snb  | sf1           | INS8_AddFriendship                               | G3                    |            0.8584 |                     2 |                     0.0000 |                     6 |                     0.0427 | weak_or_redundant                    |       18.0855 |
| ldbc_snb  | sf1           | IC7_RecentLikers                                 | G6                    |            1.1722 |                     2 |                     0.7984 |                     3 |                     2.0534 | joint_strong                         |       17.8402 |
| fiben     | sf10          | Q2_CompanyWithIndustryCountryAndListedSecurities | G1                    |            0.1554 |                     4 |                     0.7593 |                     2 |                     0.7593 | joint_strong                         |       17.5918 |
| ldbc_snb  | sf3           | INS2_AddLikeToPost                               | G4                    |            1.6649 |                     3 |                     0.1386 |                     4 |                     0.1386 | joint_strong                         |       17.4852 |
| ldbc_snb  | sf3           | INS5_AddForumMembership                          | G6                    |            0.5914 |                     3 |                     0.6981 |                     3 |                     0.6981 | joint_strong                         |       17.3268 |
| ldbc_snb  | sf3           | INS3_AddLikeToComment                            | G6                    |            1.1133 |                     3 |                     0.6879 |                     3 |                     0.6879 | joint_strong                         |       17.2932 |
| imdb      | sf1           | QG9_TopRatedSeriesByGenre                        | G7                    |            4.0780 |                     3 |                    38.0907 |                     1 |                     0.2349 | baseline_strong_with_ablation_signal |       16.7047 |
| ldbc_snb  | sf1           | INS3_AddLikeToComment                            | G6                    |            1.0541 |                     3 |                     0.4257 |                     3 |                     0.4257 | joint_strong                         |       16.4189 |

## Top query-level candidates

| dataset   | query_name                                       |   scale_count | winner_sequence           |   baseline_miss_total |   baseline_max_regret |   ablation_miss_total |   ablation_max_regret | case_types                                                          |   joint_score_sum |
|:----------|:-------------------------------------------------|--------------:|:--------------------------|----------------------:|----------------------:|----------------------:|----------------------:|:--------------------------------------------------------------------|------------------:|
| ldbc_snb  | IS1_ProfileOfPerson                              |             3 | sf3:G3|sf1:G3|sf0.1:G3    |                     9 |                0.9634 |                    18 |                0.9634 | joint_strong|weak_or_redundant                                      |           69.6917 |
| ldbc_snb  | INS1_AddPerson                                   |             3 | sf3:G3|sf0.1:G3|sf1:G3    |                     9 |                0.9828 |                    18 |                0.9828 | joint_strong|weak_or_redundant                                      |           68.9090 |
| ldbc_snb  | IC7_RecentLikers                                 |             3 | sf3:G3|sf0.1:G3|sf1:G6    |                     4 |                1.0786 |                    15 |                4.8735 | ablation_strong_with_baseline_signal|joint_strong                   |           63.4005 |
| ldbc_snb  | IS3_FriendsOfPerson                              |             3 | sf3:G3|sf1:G3|sf0.1:G3    |                     6 |                0.0000 |                    18 |                1.5049 | ablation_strong                                                     |           59.1970 |
| ldbc_snb  | INS5_AddForumMembership                          |             3 | sf0.1:G6|sf1:G6|sf3:G6    |                     9 |                1.3329 |                     9 |                1.3329 | joint_strong                                                        |           55.9206 |
| ldbc_snb  | INS2_AddLikeToPost                               |             3 | sf1:G6|sf3:G4|sf0.1:G6    |                     9 |                2.0416 |                    10 |                2.0416 | joint_strong                                                        |           55.6787 |
| imdb      | QG9_TopRatedSeriesByGenre                        |             3 | sf0.5:G7|sf1:G7|sf0.25:G7 |                     9 |               38.0907 |                     3 |                0.8960 | baseline_strong_with_ablation_signal                                |           51.7576 |
| ldbc_snb  | INS3_AddLikeToComment                            |             3 | sf3:G6|sf1:G6|sf0.1:G6    |                     9 |                0.6879 |                     9 |                0.6879 | joint_strong                                                        |           49.4135 |
| ldbc_snb  | IS6_ForumOfMessage                               |             3 | sf1:G3|sf3:G3|sf0.1:G9    |                     6 |                0.0961 |                    15 |                0.0578 | weak_or_redundant                                                   |           48.6733 |
| ldbc_snb  | INS4_AddForum                                    |             3 | sf1:G3|sf3:G3|sf0.1:G0    |                     8 |                0.2287 |                    12 |                0.2287 | joint_strong|weak_or_redundant                                      |           47.8193 |
| fiben     | Q2_CompanyWithIndustryCountryAndListedSecurities |             3 | sf10:G1|sf1:G5|sf30:G9    |                     9 |                5.1483 |                     6 |                0.7593 | baseline_strong|joint_strong                                        |           47.3607 |
| ldbc_snb  | IS7_RepliesOfMessage                             |             3 | sf1:G3|sf0.1:G9|sf3:G7    |                     6 |                0.5696 |                    10 |                1.0573 | ablation_moderate|ablation_strong_with_baseline_signal|joint_strong |           44.2767 |
| imdb      | QG3_RecommendationByGenreAndSubtype              |             3 | sf0.25:G8|sf0.5:G8|sf1:G8 |                     6 |                0.0955 |                    12 |                0.0597 | weak_or_redundant                                                   |           42.6098 |
| ldbc_snb  | IS5_CreatorOfMessage                             |             3 | sf1:G3|sf3:G3|sf0.1:G0    |                     6 |                0.0000 |                    12 |                0.6515 | ablation_strong|weak_or_redundant                                   |           42.5067 |
| imdb      | QG4_AllPersonsOfTypeForWatchItem                 |             3 | sf1:G6|sf0.25:G6|sf0.5:G5 |                     3 |                0.7146 |                     9 |                2.6487 | ablation_strong|ablation_strong_with_baseline_signal                |           39.5499 |
| ldbc_snb  | IS2_RecentMessagesOfPerson                       |             3 | sf0.1:G9|sf1:G9|sf3:G7    |                     7 |                0.5984 |                     7 |                0.5144 | ablation_strong|baseline_strong_with_ablation_signal|joint_strong   |           37.0542 |
| ldbc_snb  | IC5_NewGroups                                    |             3 | sf0.1:G3|sf3:G9|sf1:G7    |                     6 |                0.0293 |                    10 |                0.0255 | weak_or_redundant                                                   |           36.2218 |
| ldbc_snb  | IC2_RecentMessagesByFriends                      |             3 | sf1:G3|sf0.1:G3|sf3:G0    |                     4 |                0.3972 |                    12 |                0.5218 | ablation_strong|baseline_strong|weak_or_redundant                   |           35.6925 |
| imdb      | QG5_AllPersonsForEpisodesOfSeries                |             3 | sf0.5:G4|sf0.25:G4|sf1:G4 |                     3 |                0.4070 |                     9 |                0.4365 | ablation_strong_with_baseline_signal                                |           32.4787 |
| ldbc_snb  | IC3_FriendsAndFriendsOfFriendsInCountries        |             3 | sf0.1:G3|sf1:G7|sf3:G7    |                     5 |                0.1305 |                     8 |                0.1131 | ablation_moderate|baseline_moderate|weak_or_redundant               |           30.1001 |

## Recommended reading of the results

- Use `baseline_strong` or `baseline_strong_with_ablation_signal` cases to explain why fixed heuristics are unstable.
- Use `ablation_strong` or `ablation_strong_with_baseline_signal` cases to explain why analytical variables matter.
- Use `joint_strong` cases, if present, as the most complete examples connecting baselines, ablation, workload structure, and winners.
- Cases like FIBEN Q2 may be excellent baseline-separation cases even if ablation is moderate, because several SchemaLens signals may overlap.

