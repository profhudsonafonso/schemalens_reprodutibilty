# IC1 physical benchmark validation — SF0.1

This folder contains the validated physical benchmark pilot for LDBC SNB IC1.

## Query

IC1_TransitiveFriendsWithName

## Validated candidates

- G0: root_with_references
- G3: root_with_references_or_summaries

## Physical paths

### G0

G0 uses the normalized/reference physical path:

- `persons`
- `person_knows_person`

The traversal checks both directions of `person_knows_person`, because the knows relationship is treated as an undirected social relationship for the transitive traversal.

### G3

G3 uses the materialized root-summary collection:

- `phys_ldbc_snb_ic1_g3_89a97e97_root_summary`

This summary stores `relationship_summaries.person_knows_person` for the root person. Because the generic root summary may only contain the root-as-source direction, the runner also uses the indexed reverse side of the base relationship collection:

- `person_knows_person.person2_id`

This preserves the IC1 traversal semantics while still using the G3 physical summary as the primary access path.

## Validation status

The pilot validation confirms:

- failed benchmark runs: 0
- semantic warnings: 0
- G0 and G3 returned equivalent result IDs for all tested parameters
- query plans used indexes
- no COLLSCAN was observed

The file `ic1_g0_g3_result_equivalence.csv` verifies that G0 and G3 return the same result IDs for each tested `person_id|first_name` parameter.

## Note

These are pilot runs with small run counts. They validate physical access paths and semantic correctness before larger p95 runs.
