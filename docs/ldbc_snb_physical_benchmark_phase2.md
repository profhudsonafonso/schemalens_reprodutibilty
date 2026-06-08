# LDBC SNB physical benchmark phase 2

This document records the current status of the faithful physical MongoDB benchmark phase for LDBC SNB SF0.1.

The goal of this phase is to execute the already materialized MongoDB candidates through candidate-specific physical access paths, instead of evaluating all candidates through a shared simplified execution layer.

## Input manifest

The benchmark uses the Phase 1C full comparison manifest:

    analysis/generated/physical_materialization/ldbc_snb/sf0_1/phase1C_full_comparison/physical_materialization_manifest.csv

This manifest contains:

    total_candidates = 64
    primary = 41
    secondary_affected = 22
    control = 1
    ready_for_benchmark = 64

## Runner

The current runner is:

    benchmark/ldbc_snb/run_ldbc_snb_physical_benchmark.py

A validated IC7-specific pilot runner is also preserved:

    benchmark/ldbc_snb/run_ldbc_snb_physical_benchmark_ic7.py

The runner separates performance timing from query-plan capture:

1. Benchmark phase: executes the query without explain and records latency.
2. Query-plan phase: runs MongoDB explain after the timed benchmark.
3. Resource-monitor phase: records container, memory, CPU, and disk status for debugging.

## Important implementation corrections

During Phase 2 validation, two important corrections were made:

1. LDBC SNB identifiers must be treated as strings, because the MongoDB collections loaded from CSV store identifiers as string values.
2. IS7 must use the real materialized reply field `parent_comment_id`, not the non-existing field `comment1_id`.

The IS7 correction removed the previous COLLSCAN over `comment_reply_of_comment`.

## Validated IC7 pilot

Output folder:

    analysis/generated/physical_benchmark/ldbc_snb/sf0_1/ic7_pilot_validated/

Validation status:

    failed_runs = 0
    semantic_warning = 0
    has_COLLSCAN = False
    has_IXSCAN = True

IC7 validated candidates:

    G0: root_with_references
    G3: root_with_references_or_summaries
    G4: explicit_edge_collection
    G6: referenced_or_reverse_indexed_edges

In the validated pilot, G3 was the best candidate because it correctly used the materialized owner-level summary:

    ic7_g3_person_recent_liker_summary

## Validated IS group

Output folder:

    analysis/generated/physical_benchmark/ldbc_snb/sf0_1/is_validated/

The consolidated IS validation covers:

    IS1, IS2, IS3, IS4, IS5, IS6, IS7

Summary:

    aggregate_rows = 22
    raw_rows = 220
    query_plan_summary_rows = 22
    query_plan_component_rows = 58
    failed_runs_total = 0
    semantic_warning_rows = 0
    collscan_rows = 0

This means all IS candidates returned documents, all timed benchmark runs completed, and all query plans used indexed access without COLLSCAN.

## Notes

These outputs are pilot validation runs with small run counts. They validate semantic correctness, candidate-specific physical access paths, query-plan capture, and resource monitoring. They are not yet the final large-run p95 experiment.

The next phase is to validate IC1--IC6 and then consolidate IC1--IC7.
