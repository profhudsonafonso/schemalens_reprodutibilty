# LDBC SNB INS1–INS8 physical benchmark validation — SF0.1

This folder consolidates the pilot physical benchmark validation for LDBC SNB insert/update queries INS1–INS8.

## Scope

The validation covers the physical MongoDB materializations generated for the activated SchemaLens candidates at SF0.1.

Validated queries:

- INS1_AddPerson
- INS2_AddLikeToPost
- INS3_AddLikeToComment
- INS4_AddForum
- INS5_AddForumMembership
- INS6_AddPost
- INS7_AddComment
- INS8_AddFriendship

## Purpose

The goal of this phase is not yet to produce final benchmark numbers. The goal is to validate that each physical candidate:

1. executes the write workload successfully;
2. writes at least one document per run;
3. maintains the expected base and derived physical structures;
4. records write-path evidence separately from read-style query plans;
5. avoids treating write workloads as read explain plans.

## Candidate families validated

Across INS1–INS8, the validation includes:

- G0: root_with_references
- G3: root_with_references_or_summaries
- G4: explicit_edge_collection
- G6: referenced_or_reverse_indexed_edges
- G7: containment_baseline
- G9: hybrid_containment

Not all queries activate all families. The candidate set follows the SchemaLens activated primary and secondary-affected materialization plan.

## Files

- `ins1_ins8_validation_summary.csv`
- `ins1_ins8_benchmark_aggregate_results.csv`
- `ins1_ins8_write_plan_summary_results.csv`
- `ins1_ins8_physical_maintenance_summary.csv`
- `ins1_ins8_physical_maintenance_checks.csv`

## Write validation strategy

Unlike IC and IS read queries, INS workloads are write-oriented. Therefore, this validation uses two forms of evidence:

1. benchmark evidence, based on successful runs, p95 latency, and `documents_written`;
2. physical-maintenance evidence, based on checking that the expected base collections and derived candidate-specific structures were updated.

For write workloads, the query-plan summary records a synthetic `WRITE` stage rather than MongoDB read-style `executionStats`.
