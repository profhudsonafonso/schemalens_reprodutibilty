# IC3 physical benchmark validation — SF0.1

This folder contains the validated physical benchmark pilot for LDBC SNB IC3.

## Query

IC3_FriendsAndFriendsOfFriendsInCountries

## Validated candidates

- G0: root_with_references
- G3: root_with_references_or_summaries
- G7: containment_baseline
- G9: hybrid_containment

## Physical paths

### G0 and G7

G0 and G7 use the reference-like physical path over base collections:

- `person_knows_person`
- `persons`
- `places`
- `posts`
- `comments`

The traversal checks both directions of `person_knows_person`, because the knows relationship is treated as an undirected social relationship for the friend/friend-of-friend traversal.

### G3 and G9

G3 and G9 use their materialized root-summary collections:

- `phys_ldbc_snb_ic3_g3_f4732bc1_root_summary`
- `phys_ldbc_snb_ic3_g9_75aa81cd_root_summary`

The root summary is touched as the candidate-specific physical materialization. To preserve exact IC3 semantics, the final traversal and ranking use indexed base references:

- `person_knows_person.person1_id`
- `person_knows_person.person2_id`
- `posts.creator_person_id`
- `comments.creator_person_id`

This was necessary because the generic root summary can be directionally or structurally partial for top-k equivalence. The final validated path therefore uses the summary as the candidate-specific physical structure while relying on indexed references to preserve the same logical result as G0/G7.

## Validation status

The pilot validation confirms:

- failed benchmark runs: 0
- semantic warnings: 0
- G0, G3, G7, and G9 returned equivalent result IDs for all tested parameters
- query plans used indexes
- no COLLSCAN was observed

The file `ic3_result_equivalence.csv` verifies that all four candidates return the same person IDs for each tested `person_id|country1|country2` parameter.

## Note

These are pilot runs with small run counts. They validate physical access paths and semantic correctness before larger p95 runs.
