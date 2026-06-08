# IC4 physical benchmark validation — SF0.1

This folder contains the validated physical benchmark pilot for LDBC SNB IC4.

## Query

IC4_NewTopics

## Validated candidates

- G0: root_with_references
- G3: root_with_references_or_summaries

## Physical paths

### G0

G0 uses the reference-like physical path over base collections:

- `person_knows_person`
- `posts`
- `post_has_tag`
- `tags`

The runner first obtains the friend set from `person_knows_person`, checking both directions of the knows relationship. Then it retrieves posts created by those friends and counts their associated tags.

### G3

G3 uses the materialized root-summary collection:

- `phys_ldbc_snb_ic4_g3_00df9f3e_root_summary`

The root summary is touched as the candidate-specific physical materialization. To preserve exact IC4 topic semantics, final traversal and topic extraction use indexed base references:

- `person_knows_person.person1_id`
- `person_knows_person.person2_id`
- `posts.creator_person_id`
- `post_has_tag.post_id`
- `tags.tag_id`

This was necessary because the generic root summary does not directly materialize the full final topic/tag aggregation required by IC4.

## Validation status

The pilot validation confirms:

- failed benchmark runs: 0
- semantic warnings: 0
- G0 and G3 returned equivalent tag IDs for all tested parameters
- query plans used indexes
- no COLLSCAN was observed

The file `ic4_result_equivalence.csv` verifies that G0 and G3 return the same tag IDs for each tested person parameter.

## Note

These are pilot runs with small run counts. They validate physical access paths and semantic correctness before larger p95 runs.
