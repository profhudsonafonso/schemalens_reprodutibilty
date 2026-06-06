# LDBC SNB SF0.1 full physical comparison manifest

This folder contains the Phase 1C consolidated physical materialization manifest
for the LDBC SNB SF0.1 faithful MongoDB materialization workflow.

## Summary

- Total candidates: 64
- Unique candidates: 64
- Primary candidates: 41
- Secondary-affected candidates: 22
- Control candidates: 1
- Activated candidates for DSR: 63
- Ready for benchmark: 64
- Not ready: 0

## Methodological rule

The activated SchemaLens family is:

A(Q) = primary + secondary_affected

Control candidates are part of the broader benchmarked comparison space, but they
are not counted as activated configurations for DSR.

Therefore:

- DSR uses: primary + secondary_affected
- best_activated uses: primary + secondary_affected
- best_primary uses: primary only
- best_overall uses: primary + secondary_affected + control
- Top-1 / near-best / regret compare against: primary + secondary_affected + control

## Phase 1B result

The Phase 1B control-expansion check found that the original candidate JSON already
contained one control candidate and that this control candidate was already physically
materialized in Phase 1A. Therefore, no additional control materialization was required
for SF0.1.

## Next phase

The next phase is the physical benchmark runner. It must read this manifest and
execute each candidate using its candidate-specific physical MongoDB access path.
