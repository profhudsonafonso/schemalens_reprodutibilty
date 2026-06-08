# IC5 physical benchmark validation — SF0.1

This folder contains the validated physical benchmark pilot for LDBC SNB IC5.

## Query

IC5_NewGroups

## Validated candidates

- G0: root_with_references
- G3: root_with_references_or_summaries
- G4: explicit_edge_collection
- G6: referenced_or_reverse_indexed_edges
- G7: containment_baseline
- G9: hybrid_containment

## Physical paths

### G0 and G7

G0 and G7 use the reference-like physical path over base collections:

- `person_knows_person`
- `forum_has_member_person`
- `forum_container_of_post`
- `forums`

The runner first obtains the friend set from `person_knows_person`, checking both directions of the knows relationship. Then it retrieves forums where those friends are members and ranks forums by the number of contained posts.

### G3 and G9

G3 and G9 use their materialized root-summary collections:

- `phys_ldbc_snb_ic5_g3_45734260_root_summary`
- `phys_ldbc_snb_ic5_g9_7a7a63d2_root_summary`

The root summary is touched as the candidate-specific physical materialization. To preserve exact IC5 semantics, the final traversal and ranking use indexed base references over:

- `person_knows_person.person1_id`
- `person_knows_person.person2_id`
- `forum_has_member_person.person_id`
- `forum_container_of_post.forum_id`

### G4

G4 uses explicit edge collections:

- `phys_ldbc_snb_ic5_g4_69144c92_edge_person_knows_person`
- `phys_ldbc_snb_ic5_g4_69144c92_edge_forum_has_member_person`
- `phys_ldbc_snb_ic5_g4_69144c92_edge_forum_container_of_post`

The runner uses `source_id` and `target_id` indexes to traverse friends, forum memberships, and forum-to-post containment.

### G6

G6 uses reverse-index collections:

- `phys_ldbc_snb_ic5_g6_733601c1_rev_person_knows_person`
- `phys_ldbc_snb_ic5_g6_733601c1_rev_forum_has_member_person`
- `phys_ldbc_snb_ic5_g6_733601c1_rev_forum_container_of_post`

The runner uses `lookup_id` and `referenced_id` indexes to preserve the same logical traversal as G0.

## Validation status

The pilot validation confirms:

- failed benchmark runs: 0
- semantic warnings: 0
- all six candidates returned equivalent forum IDs for all tested parameters
- query plans used indexes
- no COLLSCAN was observed

The file `ic5_result_equivalence.csv` verifies that G0, G3, G4, G6, G7, and G9 return the same forum IDs for each tested person parameter.

## Note

These are pilot runs with small run counts. They validate physical access paths and semantic correctness before larger p95 runs.
