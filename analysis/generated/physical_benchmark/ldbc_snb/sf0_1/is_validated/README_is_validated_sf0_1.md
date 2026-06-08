# LDBC SNB SF0.1 physical benchmark — validated IS group

This folder consolidates the validated physical benchmark and query-plan outputs for LDBC SNB short-read queries IS1--IS7.

## Source folders

- IS1--IS3: `is_pilot_sf0_1`
- IS4: `is4_debug_sf0_1_v2`
- IS5: `is5_pilot_sf0_1_v3`
- IS6: `is6_pilot_sf0_1_v3`
- IS7: `is7_pilot_sf0_1_v4`

## Validation status

- All IS queries returned documents.
- No aggregate semantic warnings remain.
- All selected runs completed without failed benchmark executions.
- IS7 was patched to use the real materialized reply field `parent_comment_id` instead of the non-existing `comment1_id`, removing the previous COLLSCAN.

## Summary

- Aggregate rows: 22
- Raw rows: 220
- Query-plan summary rows: 22
- Query-plan component rows: 58
- Failed runs total: 0
- Semantic-warning rows: 0
- Query-plan rows with COLLSCAN: 0

## Notes

These are pilot validation runs. They use small benchmark-run counts and are intended to validate semantic correctness, physical access paths, query-plan capture, and resource monitoring before the final larger run.
