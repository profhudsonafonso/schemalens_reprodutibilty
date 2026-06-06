# LDBC SNB SF0.1 Phase 1B control expansion plan

This plan was generated from `mongodb_candidate_specs_by_candidate_id.json`, because the candidate JSON stores `activation_strength` values for `primary`, `secondary`, and `control` candidates.

Phase 1A materialized the activated SchemaLens space, i.e., `primary + secondary_affected` candidates. Phase 1B identifies the `control` candidates that are part of the broader benchmarked comparison space and are not yet physically materialized.

Methodological rule:

- `primary + secondary_affected` form the activated family A(Q).
- `control` candidates are not counted in DSR.
- Top-1 preservation, near-best preservation, activated regret, and primary regret compare against `primary + secondary_affected + control`.
