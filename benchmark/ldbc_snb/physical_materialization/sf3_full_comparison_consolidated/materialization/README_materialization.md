# LDBC SNB physical materialization build

This folder contains the physical materialization manifest generated before running the physical-materialization-aware benchmark.

## Scope

- Scale label: `sf3`
- Data directory: `data/sf3`
- Artifacts directory: `ldbc_snb_sf0_1_mongo_benchmark_bundle`
- Execution plan: `benchmark_execution_plan.csv`
- Selected candidates: 64
- Ready for benchmark: 64
- Unsupported/failed: 0

## Methodological rule

A candidate should enter the physical benchmark only if it appears in `physical_materialization_manifest.csv` with `ready_for_benchmark = True`.
Unsupported candidates are listed in `physical_impossibility_report.csv` with the reason.

## Output files

- `physical_materialization_manifest.csv`: candidate-level manifest used by the benchmark runner.
- `physical_materialization_manifest.json`: JSON version with candidate-spec excerpts.
- `physical_support_matrix.csv`: compact matrix of physical support by candidate.
- `physical_impossibility_report.csv`: candidates that could not be materialized and why.
- `materialization_validation_summary.csv`: collection-level stats after materialization.
- `scale_db_initialization_summary.csv`: loaded LDBC dataframes.
- `selected_experiments_summary.csv`: artifact plan rows selected for this build.
- `execution.log`: full execution log.

## Status counts

```text
{
  "ready_generic": 34,
  "ready": 30
}
```

## Next step

Run the physical benchmark/query-plan script from this manifest, not directly from the original execution plan. The benchmark script must not run candidates absent from this manifest or marked unsupported.
