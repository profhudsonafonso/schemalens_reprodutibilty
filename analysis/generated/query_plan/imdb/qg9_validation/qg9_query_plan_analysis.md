# IMDb QG9 Query-Plan Validation

This folder contains the MongoDB query-plan validation results for IMDb `QG9_TopRatedSeriesByGenre`.

The goal of this analysis is to complement the benchmark p95 results with MongoDB `explain("executionStats")` evidence and physical collection statistics. The query-plan analysis does not replace the repeated benchmark. Instead, it explains why the benchmark winner is plausible by showing how each MongoDB configuration is physically organized, which indexes are used, how many documents and keys are examined, and how large the accessed documents are.

## 1. Query

`QG9_TopRatedSeriesByGenre` retrieves top-rated series for a given genre.

Representative parameter:

```text
Comedy
```

Conceptually, the query filters titles or series by genre and ranks them by rating. Therefore, it is useful for comparing generic `WatchItem`-rooted configurations against specialized `Series`-rooted configurations.

## 2. Compared configurations

The complete QG9 validation from Group A includes all relevant IMDb configurations across the three scale factors:

| Configuration  | Template | Concrete organization                                                                      |
| -------------- | -------- | ------------------------------------------------------------------------------------------ |
| `watchitem_g0` | G0       | Generic WatchItem-rooted baseline over `watchitems`.                                       |
| `watchitem_g2` | G2       | WatchItem-rooted shared-descriptor variant.                                                |
| `watchitem_g3` | G3       | WatchItem-rooted structural-association variant.                                           |
| `watchitem_g4` | G4       | WatchItem-rooted associative/bridge-oriented variant.                                      |
| `watchitem_g5` | G5       | WatchItem-rooted associative variant with larger embedded bridge fragments.                |
| `watchitem_g6` | G6       | WatchItem-rooted associative variant with larger endpoint/person-oriented materialization. |
| `series_g7`    | G7       | Series-rooted containment reference baseline.                                              |
| `series_g8`    | G8       | Series-rooted containment with reduced embedded episodes.                                  |
| `series_g9`    | G9       | Series-rooted hybrid/richer containment variant.                                           |

In the IMDb instantiation, `G7 / series_g7` means that `Series` is the root collection and episodes are kept external/referenced. This follows the generic definition of G7 as the containment reference-baseline template.

## 3. Execution status

The full Group A query-plan run completed successfully for:

* `sf0.25`
* `sf0.5`
* `sf1`

The run covered the following queries:

* `QG1_WatchItemById`
* `QG2_WatchItemByTitle`
* `QG3_RecommendationByGenreAndSubtype`
* `QG7_UpdateWatchItemMetadata`
* `QG9_TopRatedSeriesByGenre`
* `QG10_AdvancedSearchWatchItems`

For QG9, the resulting summary contains:

```text
3 scale factors × 9 configurations = 27 QG9 query-plan rows
```

No failed query-plan rows were detected in the Group A execution.

## 4. MongoDB query-plan evidence

The table below summarizes the main `explain("executionStats")` evidence for QG9. It reports the root collection, documents returned, documents examined, keys examined, average object size, estimated examined bytes, plan stages, and index names.

| Scale  |  G | Config         | Collection   | Returned | Docs examined | Keys examined | Avg obj size (B) | Est. examined bytes | Plan stages | Indexes |        |       |               |                  |              |                  |
| ------ | -: | -------------- | ------------ | -------: | ------------: | ------------: | ---------------: | ------------------: | ----------- | ------- | ------ | ----- | ------------- | ---------------- | ------------ | ---------------- |
| sf0.25 | G0 | `watchitem_g0` | `watchitems` |       20 |         6,311 |         6,311 |              332 |           2,095,252 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf0.25 | G2 | `watchitem_g2` | `watchitems` |       20 |         6,311 |         6,311 |              364 |           2,297,204 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf0.25 | G3 | `watchitem_g3` | `watchitems` |       20 |         6,311 |         6,311 |              414 |           2,612,754 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf0.25 | G4 | `watchitem_g4` | `watchitems` |       20 |         6,311 |         6,311 |            1,152 |           7,270,272 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf0.25 | G5 | `watchitem_g5` | `watchitems` |       20 |         6,311 |         6,311 |            1,752 |          11,056,872 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf0.25 | G6 | `watchitem_g6` | `watchitems` |       20 |         6,311 |         6,311 |            2,209 |          13,940,999 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf0.25 | G7 | `series_g7`    | `series`     |       20 |            76 |            76 |              254 |              19,304 | `LIMIT      | FETCH   | IXSCAN | SORT` | `avg_rating_1 | primary_genre_1` |              |                  |
| sf0.25 | G8 | `series_g8`    | `series`     |       20 |            76 |            76 |            1,354 |             102,904 | `LIMIT      | FETCH   | IXSCAN | SORT` | `avg_rating_1 | primary_genre_1` |              |                  |
| sf0.25 | G9 | `series_g9`    | `series`     |       20 |            76 |            76 |            2,575 |             195,700 | `LIMIT      | FETCH   | IXSCAN | SORT` | `avg_rating_1 | primary_genre_1` |              |                  |
| sf0.5  | G0 | `watchitem_g0` | `watchitems` |       20 |        12,327 |        12,327 |              332 |           4,092,564 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf0.5  | G2 | `watchitem_g2` | `watchitems` |       20 |        12,327 |        12,327 |              365 |           4,499,355 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf0.5  | G3 | `watchitem_g3` | `watchitems` |       20 |        12,327 |        12,327 |              414 |           5,103,378 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf0.5  | G4 | `watchitem_g4` | `watchitems` |       20 |        12,327 |        12,327 |            1,147 |          14,139,069 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf0.5  | G5 | `watchitem_g5` | `watchitems` |       20 |        12,327 |        12,327 |            1,744 |          21,498,288 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf0.5  | G6 | `watchitem_g6` | `watchitems` |       20 |        12,327 |        12,327 |            2,199 |          27,107,073 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf0.5  | G7 | `series_g7`    | `series`     |       20 |            84 |            84 |              254 |              21,336 | `LIMIT      | FETCH   | IXSCAN | SORT` | `avg_rating_1 | primary_genre_1` |              |                  |
| sf0.5  | G8 | `series_g8`    | `series`     |       20 |            84 |            84 |            2,027 |             170,268 | `LIMIT      | FETCH   | IXSCAN | SORT` | `avg_rating_1 | primary_genre_1` |              |                  |
| sf0.5  | G9 | `series_g9`    | `series`     |       20 |            84 |            84 |            4,005 |             336,420 | `LIMIT      | FETCH   | IXSCAN | SORT` | `avg_rating_1 | primary_genre_1` |              |                  |
| sf1    | G0 | `watchitem_g0` | `watchitems` |       20 |        24,226 |        24,226 |              331 |           8,018,806 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf1    | G2 | `watchitem_g2` | `watchitems` |       20 |        24,226 |        24,226 |              363 |           8,794,038 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf1    | G3 | `watchitem_g3` | `watchitems` |       20 |        24,226 |        24,226 |              413 |          10,005,338 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf1    | G4 | `watchitem_g4` | `watchitems` |       20 |        24,226 |        24,226 |            1,134 |          27,472,284 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf1    | G5 | `watchitem_g5` | `watchitems` |       20 |        24,226 |        24,226 |            1,730 |          41,910,980 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf1    | G6 | `watchitem_g6` | `watchitems` |       20 |        24,226 |        24,226 |            2,184 |          52,909,584 | `LIMIT      | FETCH   | IXSCAN | SORT  | AND_SORTED`   | `avg_rating_1    | title_type_1 | primary_genre_1` |
| sf1    | G7 | `series_g7`    | `series`     |       20 |            91 |            91 |              255 |              23,205 | `LIMIT      | FETCH   | IXSCAN | SORT` | `avg_rating_1 | primary_genre_1` |              |                  |
| sf1    | G8 | `series_g8`    | `series`     |       20 |            91 |            91 |            3,085 |             280,735 | `LIMIT      | FETCH   | IXSCAN | SORT` | `avg_rating_1 | primary_genre_1` |              |                  |
| sf1    | G9 | `series_g9`    | `series`     |       20 |            91 |            91 |            6,222 |             566,202 | `LIMIT      | FETCH   | IXSCAN | SORT` | `avg_rating_1 | primary_genre_1` |              |                  |

## 5. Main plan-level patterns

The query-plan evidence shows a clear separation between the generic `watchitems` root and the specialized `series` root.

### WatchItem-rooted configurations

The `watchitem_*` configurations query the generic `watchitems` collection. This collection contains movies, series, and episodes. Therefore, QG9 must filter for series-like items and genre before ranking by rating.

Typical plan shape:

```text
LIMIT | FETCH | IXSCAN | SORT | AND_SORTED
```

Typical indexes used:

```text
avg_rating_1 | title_type_1 | primary_genre_1
```

This indicates that MongoDB combines indexed predicates over title type, genre, and rating inside a heterogeneous collection.

### Series-rooted configurations

The `series_*` configurations query the specialized `series` collection. This collection already materializes series as the root entity, so QG9 does not need to filter a generic title collection to isolate series.

Typical plan shape:

```text
LIMIT | FETCH | IXSCAN | SORT
```

Typical indexes used:

```text
avg_rating_1 | primary_genre_1
```

This plan is simpler and avoids the `AND_SORTED` stage observed in the WatchItem-rooted configurations.

## 6. Derived comparisons against G7

The following table compares representative alternatives against `G7 / series_g7`, the benchmark winner for QG9.

| Scale  | Comparison | Docs examined ratio | Avg object size ratio | Estimated examined bytes ratio | Meaning                                                                  |
| ------ | ---------- | ------------------: | --------------------: | -----------------------------: | ------------------------------------------------------------------------ |
| sf0.25 | G0 vs G7   |              83.04× |                 1.31× |                        108.54× | Generic WatchItem root examines many more documents.                     |
| sf0.25 | G2 vs G7   |              83.04× |                 1.43× |                        119.00× | Shared descriptor variant still uses generic WatchItem root.             |
| sf0.25 | G8 vs G7   |               1.00× |                 5.33× |                          5.33× | Same Series root, but larger documents due to embedded episodes.         |
| sf0.25 | G9 vs G7   |               1.00× |                10.14× |                         10.14× | Same Series root, but much richer/larger embedded containment.           |
| sf0.5  | G0 vs G7   |             146.75× |                 1.31× |                        191.81× | Generic WatchItem root becomes more expensive as scale grows.            |
| sf0.5  | G2 vs G7   |             146.75× |                 1.44× |                        210.88× | Shared descriptor variant still examines far more documents.             |
| sf0.5  | G8 vs G7   |               1.00× |                 7.98× |                          7.98× | Same Series root, but larger documents due to embedded episodes.         |
| sf0.5  | G9 vs G7   |               1.00× |                15.77× |                         15.77× | Same Series root, but much larger rich containment documents.            |
| sf1    | G0 vs G7   |             266.22× |                 1.30× |                        345.56× | Generic WatchItem root examines far more documents.                      |
| sf1    | G2 vs G7   |             266.22× |                 1.42× |                        378.97× | Relationship-type-only selects this weaker WatchItem-rooted alternative. |
| sf1    | G8 vs G7   |               1.00× |                12.10× |                         12.10× | Same Series root, but carries unnecessary embedded episode data.         |
| sf1    | G9 vs G7   |               1.00× |                24.40× |                         24.40× | Same Series root, but documents are much larger than G7.                 |

## 7. Benchmark baseline behavior

The benchmark results show that `G7` is the measured winner across all IMDb scales for QG9. SchemaLens preserves this winner because it keeps the relevant `series_g7` candidate in the reduced space.

| Scale  | Baseline                 | Winner | Winner p95 | Baseline choice | Choice p95 | Top-1 | Regret |
| ------ | ------------------------ | -----: | ---------: | --------------- | ---------: | ----- | -----: |
| sf0.25 | `schema_lens`            |     G7 |      3.007 | G7              |      3.007 | yes   |  0.000 |
| sf0.25 | `random_k`               |     G7 |      3.007 | sample avg.     |      3.007 | yes   |  0.000 |
| sf0.25 | `always_reference`       |     G7 |      3.007 | G7              |      3.007 | yes   |  0.000 |
| sf0.25 | `always_embed`           |     G7 |      3.007 | G8              |      3.372 | no    |  0.122 |
| sf0.25 | `depth_only`             |     G7 |      3.007 | G8              |      3.372 | no    |  0.122 |
| sf0.25 | `relationship_type_only` |     G7 |      3.007 | G0              |     40.198 | no    | 12.370 |
| sf0.5  | `schema_lens`            |     G7 |      2.054 | G7              |      2.054 | yes   |  0.000 |
| sf0.5  | `random_k`               |     G7 |      2.054 | sample avg.     |      2.054 | yes   |  0.000 |
| sf0.5  | `always_reference`       |     G7 |      2.054 | G7              |      2.054 | yes   |  0.000 |
| sf0.5  | `always_embed`           |     G7 |      2.054 | G8              |      3.895 | no    |  0.896 |
| sf0.5  | `depth_only`             |     G7 |      2.054 | G8              |      3.895 | no    |  0.896 |
| sf0.5  | `relationship_type_only` |     G7 |      2.054 | G2              |     78.136 | no    | 37.037 |
| sf1    | `schema_lens`            |     G7 |      4.078 | G7              |      4.078 | yes   |  0.000 |
| sf1    | `random_k`               |     G7 |      4.078 | sample avg.     |      4.078 | yes   |  0.000 |
| sf1    | `always_reference`       |     G7 |      4.078 | G7              |      4.078 | yes   |  0.000 |
| sf1    | `always_embed`           |     G7 |      4.078 | G8              |      5.036 | no    |  0.235 |
| sf1    | `depth_only`             |     G7 |      4.078 | G8              |      5.036 | no    |  0.235 |
| sf1    | `relationship_type_only` |     G7 |      4.078 | G2              |    159.413 | no    | 38.091 |

## 8. Connecting query plans to baseline failures

The query-plan evidence helps explain why the baselines behave differently.

### SchemaLens

SchemaLens preserves `G7` in all three scales. This is the desired behavior: the method keeps the relevant series-rooted containment reference baseline inside the reduced benchmark space.

The query-plan evidence explains why this is useful. `series_g7` queries a specialized `series` collection, examines very few documents, and keeps documents small.

### Always-reference

`always_reference` also preserves `G7` for this specific case. However, this is not evidence of an explainable reduction method by itself. It succeeds here because the empirical winner happens to be a reference-based containment candidate.

SchemaLens is different because it preserves `G7` as part of a semantically justified containment family, not because it always favors references.

### Always-embed and depth-only

`always_embed` and `depth_only` select `G8`. This means they preserve the correct `Series` root, but choose a heavier embedded variant.

The query plan explains the loss:

* `G7`, `G8`, and `G9` examine the same number of documents within each scale.
* However, `G8` and `G9` have much larger documents because they embed episode structures.
* QG9 does not use episode data; it only needs series-level genre/rating information.

At `sf1`, `G8` examines the same 91 documents as `G7`, but its average object size is 3,085 B instead of 255 B. Its estimated examined bytes are therefore 12.10× larger than G7.

### Relationship-type-only

`relationship_type_only` is the strongest failure case. It selects WatchItem-rooted configurations: `G0` at `sf0.25` and `G2` at `sf0.5` and `sf1`.

The query-plan evidence explains why this is poor:

* `G0/G2` query the generic `watchitems` collection.
* `watchitems` contains movies, series, and episodes.
* QG9 must combine predicates over title type, genre, and rating.
* The plan includes `AND_SORTED`.
* The number of examined documents grows sharply with scale.

At `sf1`:

```text
G2: 24,226 documents examined
G7:     91 documents examined
```

This is a 266.22× difference in documents examined and a 378.97× difference in estimated examined bytes. This explains why `relationship_type_only` has very high benchmark regret at `sf1`.

## 9. Main interpretation

QG9 is a strong baseline-separation case.

The same winner, `G7`, is stable across all three IMDb scale factors. However, simple deterministic baselines still fail:

* `always_embed` and `depth_only` choose `G8`, which has the right root but unnecessarily large documents.
* `relationship_type_only` chooses `G0/G2`, which use the wrong root for this query and examine far more documents.
* `always_reference` succeeds in this specific case, but only because the winner happens to be reference-based.

Therefore, QG9 shows that a good document-schema decision cannot be explained by a single simple rule. The winner is explained by the interaction between:

1. query root;
2. collection specialization;
3. relationship semantics;
4. index plan shape;
5. physical document size.

## 10. Relation to benchmark results

The benchmark identifies `G7` as the best observed configuration for QG9.

The query-plan analysis explains why this result is plausible:

```text
G7 / series_g7 = specialized Series root + small documents + simple indexed plan
```

In contrast:

```text
G0/G2 = generic WatchItem root + many more examined documents + AND_SORTED plan
G8/G9 = correct Series root, but larger documents due to embedded episodes
```

Thus, the query-plan evidence strengthens the interpretation of the p95 benchmark results.

## 11. Files

### Main Group A files

* `query_plan_summary_results_group_A.csv`: full Group A query-plan summary, including QG9 and the other Group A queries.
* `query_plan_component_results_group_A.csv`: component-level query-plan details for Group A.
* `query_plan_status_summary_group_A.csv`: execution-status summary for Group A.
* `benchmark_run_manifest_group_A.json`: execution metadata for Group A.
* `execution_group_A.log`: execution log for Group A.

### QG9 validation files

* `query_plan_summary_qg9_all_sfs.csv`: QG9-only consolidated summary across all validated scale factors.
* `query_plan_components_qg9_all_sfs.csv`: QG9-only component-level details across all validated scale factors.
* `README_QG9_query_plan.md`: this document.

Raw `explain` JSON files are not committed by default because they can become large in full query-plan runs.

## 12. Reproducibility

The Group A run was executed with the IMDb query-plan runner:

```bash
python benchmark/imdb/run_imdb_mongo_query_plan.py
```

The Group A execution used `--minimal-base-load` because the selected queries do not require the auxiliary MongoDB collections `persons`, `roles`, or `episodes`.

This option does not simplify the candidate collections under evaluation. Candidate root collections, such as `watchitems` and `series`, are still fully materialized for each selected configuration. The option only skips auxiliary collections that are not accessed by the selected query group.

## 13. Takeaway

QG9 demonstrates how query-plan evidence strengthens the interpretation of the benchmark results.

The benchmark shows that `G7` wins. The query-plan analysis explains why:

```text
G7 / series_g7 = specialized Series root + small documents + simple indexed plan
```

Meanwhile:

```text
G0/G2 = generic WatchItem root + many more examined documents + AND_SORTED plan
G8/G9 = correct Series root, but larger documents due to embedded episodes
```

This supports the main SchemaLens argument: the best configuration is not determined by one simple rule such as always referencing, always embedding, depth only, or relationship type only. It depends on the interaction between query root, relationship semantics, index behavior, and physical document size.
