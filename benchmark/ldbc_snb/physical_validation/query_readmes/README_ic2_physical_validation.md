# IC2 physical benchmark validation — SF0.1

This folder contains the validated physical benchmark pilot for LDBC SNB IC2.

## Query

IC2_RecentMessagesByFriends

## Validated candidates

- G0: root_with_references
- G3: root_with_references_or_summaries

## Physical paths

### G0

G0 uses the normalized/reference physical path:

- `person_knows_person`
- `posts`
- `comments`

The runner first obtains the friend set from `person_knows_person`, checking both directions of the knows relationship. Then it retrieves recent posts and comments from those friends using indexed `creator_person_id` fields and sorts by `creation_date`.

### G3

G3 uses the materialized root-summary collection:

- `phys_ldbc_snb_ic2_g3_8f05f032_root_summary`

The root summary is used to obtain the friend set through `relationship_summaries.person_knows_person`. Because the summary may only contain the root-as-source direction, the runner also uses the indexed reverse side of the base relationship collection:

- `person_knows_person.person2_id`

For final message retrieval, G3 uses indexed references over:

- `posts.creator_person_id`
- `comments.creator_person_id`

This preserves the exact IC2 top-k recent-message semantics. Earlier, using only message IDs stored inside the generic summary produced non-equivalent top-20 results, so the final validated path uses the summary for the friend set and indexed references for recent-message retrieval.

## Validation status

The pilot validation confirms:

- failed benchmark runs: 0
- semantic warnings: 0
- G0 and G3 returned equivalent message IDs for all tested parameters
- query plans used indexes
- no COLLSCAN was observed

The file `ic2_g0_g3_result_equivalence.csv` verifies that G0 and G3 return the same message IDs for each tested person parameter.

## Note

These are pilot runs with small run counts. They validate physical access paths and semantic correctness before larger p95 runs.
