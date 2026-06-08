# IC7 physical benchmark validation — SF0.1

This folder documents the validated physical benchmark pilot for LDBC SNB IC7.

## Query

IC7_RecentLikers

## Validated candidates

- G0: root_with_references
- G3: root_with_references_or_summaries
- G4: explicit_edge_collection
- G6: referenced_or_reverse_indexed_edges

## Physical paths

IC7 validates recent-liker retrieval across four physical candidate families.

- G0 uses the normalized/reference path over base message, like, creator, person, and knows collections.
- G3 uses the materialized summary collection for recent-liker access.
- G4 uses the explicit edge collection `ic7_g4_explicit_like_edges`.
- G6 uses the reverse-index collection `ic7_g6_owner_liker_reverse_index`.

## Validation status

The pilot validation confirms:

- failed benchmark runs: 0
- semantic warnings: 0
- query plans used indexes
- no COLLSCAN was observed

IC7 is marked as semantically valid in the consolidated IC1–IC7 validation summary.
