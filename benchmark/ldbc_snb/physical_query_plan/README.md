# LDBC SNB Physical MongoDB Query-Plan Analysis

This folder stores the reproducibility scripts used to extract MongoDB `explain("executionStats")` evidence for the physically materialized LDBC SNB candidates.

The benchmark latency results are taken from the full physical benchmark runs for SF0.1, SF1, and SF3. The query-plan analysis complements those results by reporting physical operators, documents examined, keys examined, and index usage for read-style queries.

## Scope

- Read queries with detailed query-plan evidence: IC1--IC7 and IS1--IS7.
- Write queries: INS1--INS8 are included in the benchmark latency analysis, but they do not have read-style `executionStats` plans.
- IC7 required chunking large `$in` predicates during auxiliary materialization to avoid MongoDB's 16 MB BSON command limit. This preserves the full materialized data and does not reduce the benchmark dataset.

## Generated analysis

The consolidated outputs are stored in:

`analysis/generated/ldbc_snb_physical_query_plan/`

Main files:

- `ldbc_snb_physical_query_plan_component_results.csv`
- `ldbc_snb_physical_query_plan_candidate_summary.csv`
- `ldbc_snb_physical_benchmark_query_plan_joined.csv`
- `ldbc_snb_physical_hot_winners_with_query_plan.csv`
- `ldbc_snb_physical_query_plan_scale_summary.csv`
- `ldbc_snb_physical_query_plan_coverage.csv`
- `ldbc_snb_physical_query_plan_report.md`

Final coverage result:

- No missing read-query plans.
- Remaining rows without read-style plans correspond only to INS1--INS8.
- Across SF0.1, SF1, and SF3, no read-query plan used COLLSCAN.
