# LDBC SNB physical MongoDB validation — IC1–IC7 SF0.1

This folder contains the pilot validation artifacts for faithful physical MongoDB materializations of LDBC SNB IC1–IC7.

## Scope

The validation covers the activated SchemaLens candidate families for the interactive complex queries IC1–IC7 at SF0.1.

The goal is to validate physical access paths and semantic equivalence before running larger benchmark campaigns.

## Included files

### Consolidated validation

Located in:

    physical_validation/ic1_ic7_consolidated_sf0_1/

Main files:

- `ic1_ic7_validation_summary.csv`
- `ic1_ic7_benchmark_aggregate_results.csv`
- `ic1_ic7_query_plan_summary_results.csv`
- `ic1_ic7_semantic_equivalence_results.csv`
- `README_ic1_ic7_physical_validation.md`

### Query-level validation notes

Located in:

    physical_validation/query_readmes/

These files explain the physical path validated for each IC query.

## Validated status

All IC1–IC7 pilots are validated:

- successful runs: yes
- failed runs: 0
- semantic warnings: 0
- semantic equivalence: true
- query-plan status: completed
- IXSCAN observed: true
- COLLSCAN observed: false

## Important methodological note

For some candidates, especially G3 and G9, the materialized `root_summary` collection is touched and used as the candidate-specific physical structure. When the generic summary does not contain enough information to preserve final top-k ordering, aggregation, bidirectional traversal, or exact semantic equivalence, the runner uses indexed base references to complete the query semantics.

This keeps the materialization faithful to the generated candidate while ensuring that latency comparisons are made over equivalent logical results.

## IS1–IS7 physical validation

The folder also includes the pilot physical validation for LDBC SNB interactive short queries IS1–IS7 at SF0.1:

    physical_validation/is1_is7_consolidated_sf0_1/

Main files:

- `is1_is7_validation_summary.csv`
- `is1_is7_benchmark_aggregate_results.csv`
- `is1_is7_query_plan_summary_results.csv`
- `is1_is7_semantic_equivalence_results.csv`
- `README_is1_is7_physical_validation.md`

The validation confirms that IS1–IS7 physical candidates execute successfully, preserve semantic equivalence across candidate families, produce query-plan evidence, use indexes, and avoid collection scans in the inspected plans.
