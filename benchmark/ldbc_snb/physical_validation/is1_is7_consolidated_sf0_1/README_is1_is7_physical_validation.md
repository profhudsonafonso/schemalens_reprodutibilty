# LDBC SNB IS1–IS7 physical benchmark validation — SF0.1

This folder consolidates the pilot physical benchmark validation for LDBC SNB interactive short queries IS1–IS7.

## Scope

The validation covers the physical MongoDB materializations generated for the activated SchemaLens candidates at SF0.1.

Validated queries:

- IS1_ProfileOfPerson
- IS2_RecentMessagesOfPerson
- IS3_FriendsOfPerson
- IS4_ContentOfMessage
- IS5_CreatorOfMessage
- IS6_ForumOfMessage
- IS7_RepliesOfMessage

## Purpose

The goal of this phase is not yet to produce final benchmark numbers. The goal is to validate that each physical candidate:

1. uses the intended materialized MongoDB structure;
2. executes successfully;
3. preserves the same logical result as the reference candidate;
4. produces query-plan evidence;
5. uses indexes and avoids collection scans in the inspected plans.

## Candidate families validated

Across IS1–IS7, the validation includes:

- G0: root_with_references
- G1: single_entity_lookup
- G3: root_with_references_or_summaries
- G4: explicit_edge_collection
- G6: referenced_or_reverse_indexed_edges
- G7: containment_baseline
- G9: hybrid_containment

Not all queries activate all families. The candidate set follows the SchemaLens activated primary, secondary-affected, and control materialization plan.

## Files

- `is1_is7_validation_summary.csv`
- `is1_is7_benchmark_aggregate_results.csv`
- `is1_is7_query_plan_summary_results.csv`
- `is1_is7_semantic_equivalence_results.csv`

## Notes

These are pilot runs with small run counts. They validate physical access paths and semantic correctness before larger p95 benchmark runs.

For summary-based candidates such as G3 and G9, the runner touches the materialized root-summary collection as the candidate-specific physical structure. When needed, indexed base references are used to preserve exact query semantics.
