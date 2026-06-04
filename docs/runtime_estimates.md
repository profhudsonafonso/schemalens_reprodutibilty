# Runtime Estimates

This document reports observed runtime estimates extracted from execution logs included in the artifact.

The reported values are wall-clock intervals between the first and last parseable timestamp in each log file.
They should be interpreted as approximate machine-specific guidance, not hardware-independent guarantees.

## Lightweight verification

| Scenario | Command | Requires MongoDB | Requires external data | Expected time |
|---|---|---:|---:|---:|
| Artifact check | `make check-artifact` | no | no | seconds |
| Short-paper table reproduction | `make reproduce-paper` | no | no | less than 1 minute |
| Analysis pipeline | `make analysis-pipeline` | no | no | minutes |

## Runtime estimates from available logs

| Dataset | Scenario | Runtime | Log file |
|---|---|---:|---|
| IMDb | IMDb query-plan Group A | 15 h 53 min | `analysis/generated/query_plan/imdb/group_A_light_no_roles/execution_group_A.log` |
| IMDb | IMDb query-plan Group B / QG6 | 16 h 23 min | `analysis/generated/query_plan/imdb/group_B_episodes/execution_group_B.log` |
| IMDb | IMDb query-plan QG5 assoc-only with episodes / sf1 | 10 h 34 min | `analysis/generated/query_plan/imdb/group_C_qg5_sf1_assoc_only_with_episodes/execution_group_C_qg5_sf1_assoc_only_with_episodes.log` |
| IMDb | IMDb query-plan Group C roles / sf0.25 | 2 h 29 min | `analysis/generated/query_plan/imdb/group_C_roles_sf025/execution_group_C_roles_sf025.log` |
| IMDb | IMDb query-plan Group C roles / sf0.5 | 6 h 7 min | `analysis/generated/query_plan/imdb/group_C_roles_sf050/execution_group_C_roles_sf050.log` |
| IMDb | IMDb query-plan Group C assoc-only / sf1 | 10 h 10 min | `analysis/generated/query_plan/imdb/group_C_roles_sf1_assoc_only/execution_group_C_roles_sf1_assoc_only.log` |
| IMDb | IMDb query-plan Group D / QG8 | 13 h 38 min | `analysis/generated/query_plan/imdb/group_D_insert_qg8/execution_group_D.log` |
| IMDb | IMDb QG9 query-plan validation | 3 h 22 min | `analysis/generated/query_plan/imdb/qg9_validation/execution_qg9_sf025_sf050.log` |
| IMDb | IMDb QG9 query-plan validation | 2 h 59 min | `analysis/generated/query_plan/imdb/qg9_validation/execution_qg9_sf1.log` |

## Notes

- Full benchmark runtimes depend on hardware, storage, Docker performance, and selected scale factor.
- Some full benchmark runs may not have complete execution logs in this lightweight artifact.
- Query-plan validation logs are included as reproducibility evidence for selected IMDb cases.
- The Makefile benchmark targets provide entry points for rerunning full benchmarks when local datasets are available.
