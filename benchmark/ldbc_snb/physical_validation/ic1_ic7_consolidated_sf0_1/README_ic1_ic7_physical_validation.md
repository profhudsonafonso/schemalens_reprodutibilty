# LDBC SNB IC1–IC7 physical benchmark validation — SF0.1

This folder consolidates the pilot physical benchmark validation for LDBC SNB interactive complex queries IC1–IC7.

## Scope

The validation covers the physical MongoDB materializations generated for the activated SchemaLens candidates at SF0.1.

Validated queries:

- IC1_TransitiveFriendsWithName
- IC2_RecentMessagesByFriends
- IC3_FriendsAndFriendsOfFriendsInCountries
- IC4_NewTopics
- IC5_NewGroups
- IC6_TagCoOccurrence
- IC7_RecentLikers

## Purpose

The goal of this phase is not yet to produce final benchmark numbers. The goal is to validate that each physical candidate:

1. uses the intended materialized MongoDB structure;
2. executes successfully;
3. preserves the same logical result as the reference candidate;
4. produces query-plan evidence;
5. uses indexes and avoids collection scans in the inspected plans.

## Candidate families validated

Across IC1–IC7, the validation includes:

- G0: root_with_references
- G3: root_with_references_or_summaries
- G4: explicit_edge_collection
- G6: referenced_or_reverse_indexed_edges
- G7: containment_baseline
- G9: hybrid_containment

Not all queries activate all families. The candidate set follows the SchemaLens activated primary and secondary-affected materialization plan.

## Files

- `ic1_ic7_validation_summary.csv`  
  One-row-per-query validation summary.

- `ic1_ic7_benchmark_aggregate_results.csv`  
  Consolidated benchmark aggregate results for IC1–IC7.

- `ic1_ic7_query_plan_summary_results.csv`  
  Consolidated query-plan summary results.

- `ic1_ic7_semantic_equivalence_results.csv`  
  Consolidated semantic-equivalence checks for IC1–IC6. IC7 was validated in its dedicated pilot folder and is marked as semantically valid in the validation summary.

## Notes

These are pilot runs with small run counts. They validate physical access paths and semantic correctness before larger p95 benchmark runs.

For G3 and G9, the runner touches the materialized root-summary collection as the candidate-specific physical structure, while indexed base references are used when necessary to preserve exact query semantics. This is required because generic root summaries may not materialize all fields needed for final top-k ordering, aggregation, or bidirectional traversal.
