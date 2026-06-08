# IC6 physical benchmark validation — SF0.1

This folder contains the validated physical benchmark pilot for LDBC SNB IC6.

## Query

IC6_TagCoOccurrence

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

The runner obtains people reachable from the root person through the knows relationship, retrieves posts from those reachable people, and computes tag co-occurrence using `post_has_tag`.

### G3

G3 uses the materialized root-summary collection:

- `phys_ldbc_snb_ic6_g3_9a00a0b5_root_summary`

The root summary is touched as the candidate-specific physical materialization. To preserve exact IC6 tag co-occurrence semantics, final traversal and co-occurrence computation use indexed base references:

- `person_knows_person.person1_id`
- `person_knows_person.person2_id`
- `posts.creator_person_id`
- `post_has_tag.post_id`
- `tags.tag_id`

This preserves the same logical result as G0 while still validating the G3 materialized physical structure.

## Validation status

The pilot validation confirms:

- failed benchmark runs: 0
- semantic warnings: 0
- G0 and G3 returned equivalent tag IDs for all tested parameters
- query plans used indexes
- no COLLSCAN was observed

The file `ic6_result_equivalence.csv` verifies that G0 and G3 return the same tag IDs for each tested `person_id|tag_id` parameter.

## Note

These are pilot runs with small run counts. They validate physical access paths and semantic correctness before larger p95 runs.
