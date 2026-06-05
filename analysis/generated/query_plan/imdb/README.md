# IMDb MongoDB Query-Plan Analysis

This folder contains the MongoDB query-plan evidence used to explain the IMDb results in the SchemaLens paper.

The query-plan analysis complements the aggregate benchmark, baseline, and ablation outputs. It does **not** rerun the full benchmark. Instead, it uses MongoDB `explain("executionStats")` and collection statistics to explain why selected configurations are fast, slow, preserved, or missed by baselines/ablations.

## Runner

The IMDb query-plan experiments were executed with:

```bash
python benchmark/imdb/run_imdb_mongo_query_plan.py
```

The runner reuses the IMDb MongoDB materialization logic and collects:

- MongoDB `explain("executionStats")` metrics;
- `totalDocsExamined`, `totalKeysExamined`, and `nReturned`;
- plan stages such as `IXSCAN`, `FETCH`, `SORT`, `COUNT_SCAN`, `AND_SORTED`, and `UPDATE`;
- index names used by the plan;
- collection statistics such as document count, collection size, index size, and average object size;
- estimated examined bytes and returned bytes.

Raw MongoDB explain JSON files are not committed because they can become large. The committed CSV summaries are sufficient for lightweight reproduction of the paper tables.

## Folder structure

```text
analysis/generated/query_plan/imdb/
├── qg9_validation/
├── group_A_light_no_roles/
├── group_B_episodes/
├── group_C_roles_sf025/
├── group_C_roles_sf050/
├── group_C_roles_sf1_assoc_only/
├── group_C_qg5_sf1_assoc_only_with_episodes/
├── group_D_insert_qg8/
└── README_group_C_roles.md
```

## Query groups

| Folder | Queries | Purpose |
|---|---|---|
| `qg9_validation/` | `QG9_TopRatedSeriesByGenre` | Detailed validation for ranking/filtering over Series. |
| `group_A_light_no_roles/` | QG1, QG2, QG3, QG7, QG9, QG10 | Lightweight group that does not require the heavy `roles/persons/episodes` base collections. |
| `group_B_episodes/` | `QG6_EpisodesOfSeries` | Containment case comparing external indexed episodes with embedded episode arrays. |
| `group_C_roles_sf025/` | QG4, QG5 | Full associative/deep-traversal run for `sf0.25`. |
| `group_C_roles_sf050/` | QG4, QG5 | Full associative/deep-traversal run for `sf0.5`. |
| `group_C_roles_sf1_assoc_only/` | QG4 and QG5 for G4/G5/G6 | Targeted `sf1` associative run. Valid for QG4; QG5 requires an additional run with `episodes`. |
| `group_C_qg5_sf1_assoc_only_with_episodes/` | QG5 for G4/G5/G6 | Targeted `sf1` QG5 run with `episodes` loaded and `persons/roles` skipped. |
| `group_D_insert_qg8/` | `QG8_AddPersonRoleToWatchItem` | Insert/update-oriented case. Pure inserts are marked as not explainable; update components are captured when available. |

## Important Group C note

The full Group C run completed for `sf0.25` and `sf0.5`. For `sf1`, the full run was repeatedly interrupted during materialization of the external `roles` collection before query-plan extraction. This was a data-loading limitation, not a query-plan failure.

To preserve the main associative evidence at `sf1`, targeted runs were executed for:

- `watchitem_g4`
- `watchitem_g5`
- `watchitem_g6`

The first targeted run, `group_C_roles_sf1_assoc_only/`, is valid for QG4 because the relevant Role/Person structures are materialized inside `watchitems` for G4/G5/G6. However, QG5 starts from the Series--Episode traversal, so it requires the `episodes` collection. Therefore, the additional run `group_C_qg5_sf1_assoc_only_with_episodes/` loads `episodes` while still skipping `persons` and `roles`.

For details, see:

```text
analysis/generated/query_plan/imdb/README_group_C_roles.md
```

## Reproducing journal-ready IMDb tables

The journal-ready IMDb tables can be regenerated from committed CSV files with:

```bash
python analysis/scripts/reproduce_imdb_query_plan_journal_tables.py
```

This script uses:

```text
analysis/imdb/benchmark_aggregate_results_imdb_all_sfs.csv
analysis/generated/baseline_performance_by_case.csv
analysis/generated/ablation_performance_by_case.csv
analysis/imdb/ablation_variables/query_analytical_metadata_imdb.csv
analysis/generated/query_plan/imdb/**/query_plan_summary*.csv
```

It generates:

```text
analysis/generated/query_plan/imdb/imdb_journal_benchmark_ablation_values.csv
analysis/generated/query_plan/imdb/imdb_journal_plan_values.csv
analysis/generated/query_plan/imdb/imdb_journal_query_plan_tables.tex
```

The generated LaTeX tables summarize:

1. analytical variables, best configuration, SchemaLens preservation, deterministic baseline failures, and ablation failures;
2. representative MongoDB physical-plan evidence for QG3, QG4, QG5, QG6, QG8, and QG9.

## Interpretation summary

The IMDb query-plan evidence supports different parts of the SchemaLens argument:

- QG6 shows that containment does not imply always embedding; external indexed episodes can be competitive or better.
- QG9 shows that a specialized `series` root can strongly outperform a generic `watchitems` root.
- QG4 shows the value of associative materialization for the `WatchItem`--`Role`--`Person` path.
- QG5 shows that deep traversal combines Series--Episode traversal with Role/Person access.
- QG8 shows that write-oriented operations expose maintenance costs that are not visible in read-only plans.
- QG3 shows that even when Top-1 is preserved, deterministic baselines and ablations can still select weaker families.

Together, the query-plan results explain why SchemaLens preserves a compact family of semantically justified alternatives instead of applying a single universal rule such as always embedding or always referencing.
