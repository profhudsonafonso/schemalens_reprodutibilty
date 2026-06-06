# LDBC SNB SF0.1 Physical Materialization Manifest

This folder contains the consolidated physical materialization manifest for the
LDBC SNB SF0.1 workload used in the SchemaLens journal-extension workflow.

The materialization phase was executed in groups:

- IS1--IS7
- IC1--IC7
- INS1--INS8
- INS6 retry, used to replace a transient connection failure observed during the grouped INS run

## Summary

- Total candidate materializations: 64
- Ready for benchmark: 64
- Not ready: 0

Materialization statuses:

- ready: query-specific physical materialization
- ready_generic: generic physical materialization derived from the activated MongoDB template
- ready_with_warnings: materialization validated as ready, with manual notes explaining warning cases

## Warning notes

Two candidates were marked as `ready_with_warnings` due to manifest/validation-summary recording issues:

- IS7_RepliesOfMessage / G0
- IC5_NewGroups / G0

Both were manually validated against MongoDB and confirmed to contain the required physical collections.

## Methodological rule

No candidate should be benchmarked unless it appears in
`physical_materialization_manifest.csv` with `ready_for_benchmark = True`.

The next phase is to run the physical benchmark and query-plan analysis using
this consolidated manifest.
