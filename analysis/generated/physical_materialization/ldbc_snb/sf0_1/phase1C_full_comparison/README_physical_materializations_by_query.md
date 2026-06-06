# LDBC SNB SF0.1 — Physical MongoDB Materializations

Generated at: `2026-06-06T04:40:58`

This README documents how each activated SchemaLens candidate was physically materialized in MongoDB for the LDBC SNB SF0.1 workload.

The materializations were generated from the existing SchemaLens MongoDB candidate artifacts. The framework was **not rerun** to change root selection, sharedness, volatility, activation rules, or the G0--G9 candidate set. This phase only compiles the already generated MongoDB candidates into concrete physical MongoDB structures.

## Methodological rule

A candidate can be used by the physical benchmark only if it appears in `physical_materialization_manifest.csv` with `ready_for_benchmark = True`.

For SF0.1, the consolidated manifest contains:

- Total candidates: 64
- Ready for benchmark: 64
- Not ready: 0

## Status meaning

- `ready`: query-specific materialization, usually with a query-specific physical structure.
- `ready_generic`: generic materialization derived from the activated MongoDB template.
- `ready_with_warnings`: materialization is considered ready, but a manual validation note explains a manifest/validation-summary warning.

## Materialization pattern summary

- `G0`: reference-based baseline over separate entity and relationship collections.
- `G1`: single-entity lookup over the required entity collection.
- `G3`: root-with-references-or-summaries, usually adding a root summary collection.
- `G4`: explicit edge collections derived from relationship collections.
- `G6`: reverse-indexed or endpoint-indexed edge collections.
- `G7`: containment-reference baseline.
- `G9`: hybrid containment, usually represented by reference access plus a derived summary/root structure in generic cases.

## IS1 — `IS1_ProfileOfPerson`

- Number of candidates: 2
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (primary, ready)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (primary, ready_generic)

### IS1 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_is1_g0_edd90ee3`
- Benchmark group: `primary`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is1_g0_edd90ee3`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `7.742038947995752` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_is_located_in_place`: 1528 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`persons`; documents=`1528`; role=`normalized_reference_baseline`; relationships_available=`['forum_has_member_person', 'comment_has_tag', 'forum_has_moderator_person', 'comment_reply_of_post', 'person_likes_comment', 'person_has_interest_tag', 'person_study_at_organisation', 'comment_reply_of_comment', 'person_work_at_organisation', 'forum_container_of_post', 'post_has_tag', 'person_knows_person', 'person_likes_post', 'person_is_located_in_place', 'forum_has_tag']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IS1 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_is1_g3_6c817501`
- Benchmark group: `primary`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is1_g3_6c817501`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `7.436358415987343` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_is_located_in_place`: 1528 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_is1_g3_6c817501_root_summary`; documents=`1528`; role=`generic_root_summary`; root_collection=`persons`; root_pk=`person_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_is1_g3_6c817501_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in comment_reply_of_comment; skipped for root summary.
- No ID fields found in person_knows_person; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in forum_container_of_post; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in comment_reply_of_post; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.

## IS2 — `IS2_RecentMessagesOfPerson`

- Number of candidates: 6
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (secondary_affected, ready)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (secondary_affected, ready_generic)
  - `G4` — `explicit_edge_collection` / `edge_document` (secondary_affected, ready_generic)
  - `G6` — `referenced_or_reverse_indexed_edges` / `edge_reference_reverse_index` (secondary_affected, ready_generic)
  - `G7` — `containment_baseline` / `containment_reference` (secondary_affected, ready)
  - `G9` — `hybrid_containment` / `hybrid_embed_reference_summary` (secondary_affected, ready_generic)

### IS2 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_is2_g0_1d094f1c`
- Benchmark group: `secondary_affected`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is2_g0_1d094f1c`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `12.03648523800075` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`persons`; documents=`1528`; role=`normalized_reference_baseline`; relationships_available=`['person_likes_comment', 'forum_container_of_post', 'forum_has_moderator_person', 'person_study_at_organisation', 'person_likes_post', 'comment_has_creator_person', 'forum_has_member_person', 'person_has_interest_tag', 'post_has_creator_person', 'person_knows_person', 'comment_reply_of_post', 'post_has_tag', 'forum_has_tag', 'comment_reply_of_comment', 'person_work_at_organisation', 'comment_has_tag']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IS2 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_is2_g3_b993236d`
- Benchmark group: `secondary_affected`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is2_g3_b993236d`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `12.98155186092481` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_is2_g3_b993236d_root_summary`; documents=`1461`; role=`generic_root_summary`; root_collection=`persons`; root_pk=`person_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_is2_g3_b993236d_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in person_knows_person; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- Relationship comment_reply_of_comment does not expose root field person_id; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in forum_container_of_post; skipped for root summary.
- Relationship comment_reply_of_post does not expose root field person_id; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.

### IS2 / G4 — `explicit_edge_collection`

- Candidate ID: `ldbc_snb_is2_g4_9622e695`
- Benchmark group: `secondary_affected`
- Document strategy: `edge_document`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is2_g4_9622e695`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `18.90028130123392` seconds

**Physical interpretation.**

Explicit edge-collection pattern. The candidate keeps the base collections and adds explicit MongoDB edge collections derived from the activated relationship collections. These edge documents expose source/target or query-specific endpoint fields and are indexed for traversal.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_is2_g4_9622e695_edge_comment_reply_of_comment`; documents=`76787`; role=`generic_explicit_edge_collection`; relationship=`comment_reply_of_comment`; endpoint_inference=`relationship_priority`
- collection=`phys_ldbc_snb_is2_g4_9622e695_edge_post_has_creator_person`; documents=`135701`; role=`generic_explicit_edge_collection`; relationship=`post_has_creator_person`; endpoint_inference=`root_pk_priority`
- collection=`phys_ldbc_snb_is2_g4_9622e695_edge_comment_reply_of_post`; documents=`74256`; role=`generic_explicit_edge_collection`; relationship=`comment_reply_of_post`; endpoint_inference=`relationship_priority`
- collection=`phys_ldbc_snb_is2_g4_9622e695_edge_comment_has_creator_person`; documents=`151043`; role=`generic_explicit_edge_collection`; relationship=`comment_has_creator_person`; endpoint_inference=`root_pk_priority`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_is2_g4_9622e695_edge_comment_reply_of_comment`; index=`source_id_1`
- collection=`phys_ldbc_snb_is2_g4_9622e695_edge_comment_reply_of_comment`; index=`target_id_1`
- collection=`phys_ldbc_snb_is2_g4_9622e695_edge_comment_reply_of_comment`; index=`source_id_1_creation_date_-1`
- collection=`phys_ldbc_snb_is2_g4_9622e695_edge_post_has_creator_person`; index=`source_id_1`
- collection=`phys_ldbc_snb_is2_g4_9622e695_edge_post_has_creator_person`; index=`target_id_1`
- collection=`phys_ldbc_snb_is2_g4_9622e695_edge_post_has_creator_person`; index=`source_id_1_creation_date_-1`
- collection=`phys_ldbc_snb_is2_g4_9622e695_edge_comment_reply_of_post`; index=`source_id_1`
- collection=`phys_ldbc_snb_is2_g4_9622e695_edge_comment_reply_of_post`; index=`target_id_1`
- collection=`phys_ldbc_snb_is2_g4_9622e695_edge_comment_reply_of_post`; index=`source_id_1_creation_date_-1`
- collection=`phys_ldbc_snb_is2_g4_9622e695_edge_comment_has_creator_person`; index=`source_id_1`
- collection=`phys_ldbc_snb_is2_g4_9622e695_edge_comment_has_creator_person`; index=`target_id_1`
- collection=`phys_ldbc_snb_is2_g4_9622e695_edge_comment_has_creator_person`; index=`source_id_1_creation_date_-1`

**Warnings / notes from materializer.**

- Could not infer endpoint fields for relationship collection forum_has_tag.
- Could not infer endpoint fields for relationship collection person_likes_post.
- Could not infer endpoint fields for relationship collection post_has_tag.
- Could not infer endpoint fields for relationship collection comment_has_tag.
- Could not infer endpoint fields for relationship collection forum_container_of_post.
- Could not infer endpoint fields for relationship collection person_study_at_organisation.
- Could not infer endpoint fields for relationship collection forum_has_member_person.
- Could not infer endpoint fields for relationship collection person_likes_comment.
- Could not infer endpoint fields for relationship collection person_knows_person.
- Could not infer endpoint fields for relationship collection forum_has_moderator_person.
- Could not infer endpoint fields for relationship collection person_has_interest_tag.
- Could not infer endpoint fields for relationship collection person_work_at_organisation.

### IS2 / G6 — `referenced_or_reverse_indexed_edges`

- Candidate ID: `ldbc_snb_is2_g6_7253ed90`
- Benchmark group: `secondary_affected`
- Document strategy: `edge_reference_reverse_index`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is2_g6_7253ed90`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `19.245916707906872` seconds

**Physical interpretation.**

Referenced or reverse-indexed edge pattern. The candidate keeps the base collections and adds reverse-index or endpoint-indexed collections. These collections are designed to support lookup from the query-side endpoint to the referenced/related endpoint.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_is2_g6_7253ed90_rev_comment_has_creator_person`; documents=`151043`; role=`generic_reverse_index`; relationship=`comment_has_creator_person`; endpoint_inference=`root_pk_priority`
- collection=`phys_ldbc_snb_is2_g6_7253ed90_rev_post_has_creator_person`; documents=`135701`; role=`generic_reverse_index`; relationship=`post_has_creator_person`; endpoint_inference=`root_pk_priority`
- collection=`phys_ldbc_snb_is2_g6_7253ed90_rev_comment_reply_of_comment`; documents=`76787`; role=`generic_reverse_index`; relationship=`comment_reply_of_comment`; endpoint_inference=`relationship_priority`
- collection=`phys_ldbc_snb_is2_g6_7253ed90_rev_comment_reply_of_post`; documents=`74256`; role=`generic_reverse_index`; relationship=`comment_reply_of_post`; endpoint_inference=`relationship_priority`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_is2_g6_7253ed90_rev_comment_has_creator_person`; index=`lookup_id_1`
- collection=`phys_ldbc_snb_is2_g6_7253ed90_rev_comment_has_creator_person`; index=`referenced_id_1`
- collection=`phys_ldbc_snb_is2_g6_7253ed90_rev_comment_has_creator_person`; index=`lookup_id_1_creation_date_-1`
- collection=`phys_ldbc_snb_is2_g6_7253ed90_rev_post_has_creator_person`; index=`lookup_id_1`
- collection=`phys_ldbc_snb_is2_g6_7253ed90_rev_post_has_creator_person`; index=`referenced_id_1`
- collection=`phys_ldbc_snb_is2_g6_7253ed90_rev_post_has_creator_person`; index=`lookup_id_1_creation_date_-1`
- collection=`phys_ldbc_snb_is2_g6_7253ed90_rev_comment_reply_of_comment`; index=`lookup_id_1`
- collection=`phys_ldbc_snb_is2_g6_7253ed90_rev_comment_reply_of_comment`; index=`referenced_id_1`
- collection=`phys_ldbc_snb_is2_g6_7253ed90_rev_comment_reply_of_comment`; index=`lookup_id_1_creation_date_-1`
- collection=`phys_ldbc_snb_is2_g6_7253ed90_rev_comment_reply_of_post`; index=`lookup_id_1`
- collection=`phys_ldbc_snb_is2_g6_7253ed90_rev_comment_reply_of_post`; index=`referenced_id_1`
- collection=`phys_ldbc_snb_is2_g6_7253ed90_rev_comment_reply_of_post`; index=`lookup_id_1_creation_date_-1`

**Warnings / notes from materializer.**

- Could not infer endpoint fields for reverse index from comment_has_tag.
- Could not infer endpoint fields for reverse index from person_knows_person.
- Could not infer endpoint fields for reverse index from person_study_at_organisation.
- Could not infer endpoint fields for reverse index from person_work_at_organisation.
- Could not infer endpoint fields for reverse index from person_likes_comment.
- Could not infer endpoint fields for reverse index from forum_container_of_post.
- Could not infer endpoint fields for reverse index from person_likes_post.
- Could not infer endpoint fields for reverse index from forum_has_tag.
- Could not infer endpoint fields for reverse index from post_has_tag.
- Could not infer endpoint fields for reverse index from forum_has_moderator_person.
- Could not infer endpoint fields for reverse index from person_has_interest_tag.
- Could not infer endpoint fields for reverse index from forum_has_member_person.

### IS2 / G7 — `containment_baseline`

- Candidate ID: `ldbc_snb_is2_g7_26e684aa`
- Benchmark group: `secondary_affected`
- Document strategy: `containment_reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is2_g7_26e684aa`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `12.365069400984794` seconds

**Physical interpretation.**

Containment-reference baseline. The candidate represents the activated containment family while preserving reference-based access to the required base collections. In this materialization manifest, query-specific G7 candidates may be represented by the loaded root/contained collections and relationship references rather than by a new derived collection.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`persons`; documents=`1528`; role=`containment_reference_baseline`; relationships_available=`['forum_has_tag', 'forum_has_moderator_person', 'person_work_at_organisation', 'forum_container_of_post', 'person_knows_person', 'person_likes_post', 'person_study_at_organisation', 'post_has_creator_person', 'comment_has_creator_person', 'person_likes_comment', 'comment_reply_of_comment', 'post_has_tag', 'forum_has_member_person', 'person_has_interest_tag', 'comment_has_tag', 'comment_reply_of_post']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IS2 / G9 — `hybrid_containment`

- Candidate ID: `ldbc_snb_is2_g9_b1df45f6`
- Benchmark group: `secondary_affected`
- Document strategy: `hybrid_embed_reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is2_g9_b1df45f6`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `12.960059479810296` seconds

**Physical interpretation.**

Hybrid containment pattern. The candidate combines reference-based access with derived summary/containment structures. In generic cases, the manifest records a root summary collection derived from the activated template.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_is2_g9_b1df45f6_root_summary`; documents=`1461`; role=`generic_root_summary`; root_collection=`persons`; root_pk=`person_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_is2_g9_b1df45f6_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in person_knows_person; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- Relationship comment_reply_of_post does not expose root field person_id; skipped for root summary.
- No ID fields found in forum_container_of_post; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- Relationship comment_reply_of_comment does not expose root field person_id; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.

## IS3 — `IS3_FriendsOfPerson`

- Number of candidates: 2
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (primary, ready)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (primary, ready_generic)

### IS3 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_is3_g0_fc24df68`
- Benchmark group: `primary`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is3_g0_fc24df68`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `7.565974536817521` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`persons`; documents=`1528`; role=`normalized_reference_baseline`; relationships_available=`['person_likes_post', 'person_likes_comment', 'forum_has_moderator_person', 'forum_has_tag', 'comment_has_tag', 'person_has_interest_tag', 'forum_has_member_person', 'person_knows_person', 'person_work_at_organisation', 'comment_reply_of_comment', 'post_has_tag', 'forum_container_of_post', 'person_study_at_organisation', 'comment_reply_of_post']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IS3 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_is3_g3_ebc00ba6`
- Benchmark group: `primary`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is3_g3_ebc00ba6`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `14.22229788126424` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_is3_g3_ebc00ba6_root_summary`; documents=`1199`; role=`generic_root_summary`; root_collection=`persons`; root_pk=`person_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_is3_g3_ebc00ba6_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in forum_container_of_post; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in comment_reply_of_post; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in comment_reply_of_comment; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.

## IS4 — `IS4_ContentOfMessage`

- Number of candidates: 2
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (control, ready)
  - `G1` — `single_entity_lookup` / `single_collection` (primary, ready)

### IS4 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_is4_g0_103e0c60`
- Benchmark group: `control`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is4_g0_103e0c60`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `7.843239843845367` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`posts`; documents=`135701`; role=`normalized_reference_baseline`; relationships_available=`['person_likes_comment', 'person_has_interest_tag', 'comment_reply_of_comment', 'post_has_tag', 'person_study_at_organisation', 'forum_has_member_person', 'person_likes_post', 'comment_has_tag', 'forum_has_moderator_person', 'forum_container_of_post', 'person_work_at_organisation', 'person_knows_person', 'comment_reply_of_post', 'forum_has_tag']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IS4 / G1 — `single_entity_lookup`

- Candidate ID: `ldbc_snb_is4_g1_c923c633`
- Benchmark group: `primary`
- Document strategy: `single_collection`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is4_g1_c923c633`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `7.68040348123759` seconds

**Physical interpretation.**

Single-entity lookup pattern. The candidate materializes the main entity collection needed by the query and indexes it for direct lookup.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`posts`; documents=`135701`; role=`root_centered_reference_lookup`; relationships_available=`['forum_has_tag', 'forum_container_of_post', 'forum_has_member_person', 'comment_reply_of_post', 'forum_has_moderator_person', 'post_has_tag', 'person_likes_comment', 'person_knows_person', 'person_likes_post', 'person_work_at_organisation', 'comment_has_tag', 'person_study_at_organisation', 'comment_reply_of_comment', 'person_has_interest_tag']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

## IS5 — `IS5_CreatorOfMessage`

- Number of candidates: 2
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (primary, ready)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (primary, ready_generic)

### IS5 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_is5_g0_0e8582ef`
- Benchmark group: `primary`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is5_g0_0e8582ef`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `10.154569381847978` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`posts`; documents=`135701`; role=`normalized_reference_baseline`; relationships_available=`['forum_has_tag', 'comment_reply_of_comment', 'comment_has_creator_person', 'forum_has_moderator_person', 'person_work_at_organisation', 'forum_container_of_post', 'person_knows_person', 'comment_has_tag', 'post_has_creator_person', 'comment_reply_of_post', 'forum_has_member_person', 'person_likes_comment', 'post_has_tag', 'person_study_at_organisation', 'person_likes_post', 'person_has_interest_tag']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IS5 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_is5_g3_f332352f`
- Benchmark group: `primary`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is5_g3_f332352f`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `12.80810529878363` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_is5_g3_f332352f_root_summary`; documents=`135701`; role=`generic_root_summary`; root_collection=`posts`; root_pk=`post_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_is5_g3_f332352f_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in person_knows_person; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- Relationship comment_has_creator_person does not expose root field post_id; skipped for root summary.
- No ID fields found in comment_reply_of_comment; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in comment_reply_of_post; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in forum_container_of_post; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.

## IS6 — `IS6_ForumOfMessage`

- Number of candidates: 4
- Activated candidates:
  - `G7` — `containment_baseline` / `containment_reference` (primary, ready)
  - `G9` — `hybrid_containment` / `hybrid_embed_reference_summary` (primary, ready_generic)
  - `G0` — `root_with_references` / `reference` (secondary_affected, ready)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (secondary_affected, ready_generic)

### IS6 / G7 — `containment_baseline`

- Candidate ID: `ldbc_snb_is6_g7_0aecbe5c`
- Benchmark group: `primary`
- Document strategy: `containment_reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is6_g7_0aecbe5c`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `11.15738879190758` seconds

**Physical interpretation.**

Containment-reference baseline. The candidate represents the activated containment family while preserving reference-based access to the required base collections. In this materialization manifest, query-specific G7 candidates may be represented by the loaded root/contained collections and relationship references rather than by a new derived collection.

**Base collections loaded.**

- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forum_container_of_post`: 135701 documents
- `forum_has_moderator_person`: 13750 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`posts`; documents=`135701`; role=`containment_reference_baseline`; relationships_available=`['comment_reply_of_post', 'post_has_tag', 'person_work_at_organisation', 'comment_has_tag', 'forum_has_tag', 'person_has_interest_tag', 'comment_reply_of_comment', 'forum_container_of_post', 'person_likes_post', 'person_study_at_organisation', 'forum_has_member_person', 'person_knows_person', 'forum_has_moderator_person', 'person_likes_comment']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IS6 / G9 — `hybrid_containment`

- Candidate ID: `ldbc_snb_is6_g9_c7584187`
- Benchmark group: `primary`
- Document strategy: `hybrid_embed_reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is6_g9_c7584187`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `14.161060424055904` seconds

**Physical interpretation.**

Hybrid containment pattern. The candidate combines reference-based access with derived summary/containment structures. In generic cases, the manifest records a root summary collection derived from the activated template.

**Base collections loaded.**

- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forum_container_of_post`: 135701 documents
- `forum_has_moderator_person`: 13750 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_is6_g9_c7584187_root_summary`; documents=`135701`; role=`generic_root_summary`; root_collection=`posts`; root_pk=`post_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_is6_g9_c7584187_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in post_has_tag; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in person_knows_person; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- Relationship comment_reply_of_comment does not expose root field post_id; skipped for root summary.
- Relationship forum_has_moderator_person does not expose root field post_id; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.

### IS6 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_is6_g0_768bbe02`
- Benchmark group: `secondary_affected`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is6_g0_768bbe02`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `11.368392962962387` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forum_container_of_post`: 135701 documents
- `forum_has_moderator_person`: 13750 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`posts`; documents=`135701`; role=`normalized_reference_baseline`; relationships_available=`['person_likes_comment', 'person_likes_post', 'forum_has_moderator_person', 'person_study_at_organisation', 'forum_has_tag', 'person_work_at_organisation', 'post_has_tag', 'comment_reply_of_comment', 'comment_reply_of_post', 'forum_container_of_post', 'person_knows_person', 'comment_has_tag', 'forum_has_member_person', 'person_has_interest_tag']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IS6 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_is6_g3_f811f02c`
- Benchmark group: `secondary_affected`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is6_g3_f811f02c`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `14.75160703388974` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forum_container_of_post`: 135701 documents
- `forum_has_moderator_person`: 13750 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_is6_g3_f811f02c_root_summary`; documents=`135701`; role=`generic_root_summary`; root_collection=`posts`; root_pk=`post_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_is6_g3_f811f02c_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- Relationship forum_has_moderator_person does not expose root field post_id; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.
- Relationship comment_reply_of_comment does not expose root field post_id; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in person_knows_person; skipped for root summary.

## IS7 — `IS7_RepliesOfMessage`

- Number of candidates: 4
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (primary, ready_with_warnings)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (primary, ready_generic)
  - `G7` — `containment_baseline` / `containment_reference` (secondary_affected, ready)
  - `G9` — `hybrid_containment` / `hybrid_embed_reference_summary` (secondary_affected, ready_generic)

### IS7 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_is7_g0_7dff7761`
- Benchmark group: `primary`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is7_g0_7dff7761`
- Status: `ready_with_warnings / query_specific / ready_for_benchmark=True`
- Materialization time: `19.28463105671108` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`posts`; documents=`0`; role=`normalized_reference_baseline`; relationships_available=`['forum_container_of_post', 'person_knows_person', 'person_work_at_organisation', 'comment_reply_of_comment', 'person_study_at_organisation', 'comment_reply_of_post', 'forum_has_tag', 'comment_has_creator_person', 'person_has_interest_tag', 'comment_has_tag', 'person_likes_comment', 'forum_has_member_person', 'post_has_tag', 'forum_has_moderator_person', 'post_has_creator_person', 'person_likes_post']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IS7 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_is7_g3_6298fb5e`
- Benchmark group: `primary`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is7_g3_6298fb5e`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `15.673222318757324` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_is7_g3_6298fb5e_root_summary`; documents=`135701`; role=`generic_root_summary`; root_collection=`posts`; root_pk=`post_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_is7_g3_6298fb5e_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- Relationship comment_has_creator_person does not expose root field post_id; skipped for root summary.
- No ID fields found in forum_container_of_post; skipped for root summary.
- Relationship person_knows_person does not expose root field post_id; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- Relationship comment_reply_of_comment does not expose root field post_id; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.

### IS7 / G7 — `containment_baseline`

- Candidate ID: `ldbc_snb_is7_g7_4e6a7bf8`
- Benchmark group: `secondary_affected`
- Document strategy: `containment_reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is7_g7_4e6a7bf8`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `12.42154573276639` seconds

**Physical interpretation.**

Containment-reference baseline. The candidate represents the activated containment family while preserving reference-based access to the required base collections. In this materialization manifest, query-specific G7 candidates may be represented by the loaded root/contained collections and relationship references rather than by a new derived collection.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`posts`; documents=`135701`; role=`containment_reference_baseline`; relationships_available=`['post_has_tag', 'post_has_creator_person', 'person_knows_person', 'forum_has_tag', 'person_has_interest_tag', 'comment_has_tag', 'person_study_at_organisation', 'comment_has_creator_person', 'forum_has_member_person', 'person_likes_comment', 'person_likes_post', 'comment_reply_of_comment', 'forum_has_moderator_person', 'forum_container_of_post', 'person_work_at_organisation', 'comment_reply_of_post']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IS7 / G9 — `hybrid_containment`

- Candidate ID: `ldbc_snb_is7_g9_392f7469`
- Benchmark group: `secondary_affected`
- Document strategy: `hybrid_embed_reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_is7_g9_392f7469`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `15.64127279073` seconds

**Physical interpretation.**

Hybrid containment pattern. The candidate combines reference-based access with derived summary/containment structures. In generic cases, the manifest records a root summary collection derived from the activated template.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_is7_g9_392f7469_root_summary`; documents=`135701`; role=`generic_root_summary`; root_collection=`posts`; root_pk=`post_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_is7_g9_392f7469_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in forum_container_of_post; skipped for root summary.
- Relationship comment_reply_of_comment does not expose root field post_id; skipped for root summary.
- Relationship comment_has_creator_person does not expose root field post_id; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- Relationship person_knows_person does not expose root field post_id; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.

## IC1 — `IC1_TransitiveFriendsWithName`

- Number of candidates: 2
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (primary, ready)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (primary, ready_generic)

### IC1 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_ic1_g0_6aac8974`
- Benchmark group: `primary`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic1_g0_6aac8974`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `7.929630228783935` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `organisation_is_located_in_place`: 7955 documents
- `organisations`: 7955 documents
- `person_is_located_in_place`: 1528 documents
- `person_knows_person`: 14073 documents
- `person_study_at_organisation`: 1209 documents
- `person_work_at_organisation`: 3313 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`persons`; documents=`1528`; role=`normalized_reference_baseline`; relationships_available=`['organisation_is_located_in_place', 'comment_has_tag', 'forum_has_moderator_person', 'forum_container_of_post', 'post_has_tag', 'person_is_located_in_place', 'comment_reply_of_comment', 'forum_has_member_person', 'person_has_interest_tag', 'person_knows_person', 'person_likes_comment', 'person_likes_post', 'forum_has_tag', 'comment_reply_of_post', 'person_work_at_organisation', 'person_study_at_organisation']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IC1 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_ic1_g3_89a97e97`
- Benchmark group: `primary`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic1_g3_89a97e97`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `8.219919370952994` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `organisation_is_located_in_place`: 7955 documents
- `organisations`: 7955 documents
- `person_is_located_in_place`: 1528 documents
- `person_knows_person`: 14073 documents
- `person_study_at_organisation`: 1209 documents
- `person_work_at_organisation`: 3313 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ic1_g3_89a97e97_root_summary`; documents=`1528`; role=`generic_root_summary`; root_collection=`persons`; root_pk=`person_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ic1_g3_89a97e97_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in comment_reply_of_post; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- Relationship organisation_is_located_in_place does not expose root field person_id; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in comment_reply_of_comment; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in forum_container_of_post; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.

## IC2 — `IC2_RecentMessagesByFriends`

- Number of candidates: 2
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (primary, ready)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (primary, ready_generic)

### IC2 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_ic2_g0_bcc20fff`
- Benchmark group: `primary`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic2_g0_bcc20fff`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `10.482633243780583` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`persons`; documents=`1528`; role=`normalized_reference_baseline`; relationships_available=`['person_work_at_organisation', 'post_has_tag', 'person_knows_person', 'person_likes_comment', 'forum_has_tag', 'comment_has_tag', 'person_likes_post', 'comment_reply_of_comment', 'comment_reply_of_post', 'person_has_interest_tag', 'comment_has_creator_person', 'forum_container_of_post', 'forum_has_moderator_person', 'post_has_creator_person', 'forum_has_member_person', 'person_study_at_organisation']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IC2 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_ic2_g3_8f05f032`
- Benchmark group: `primary`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic2_g3_8f05f032`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `11.167640089057386` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ic2_g3_8f05f032_root_summary`; documents=`1472`; role=`generic_root_summary`; root_collection=`persons`; root_pk=`person_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ic2_g3_8f05f032_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in forum_container_of_post; skipped for root summary.
- No ID fields found in comment_reply_of_comment; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in comment_reply_of_post; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.

## IC3 — `IC3_FriendsAndFriendsOfFriendsInCountries`

- Number of candidates: 4
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (primary, ready)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (primary, ready_generic)
  - `G7` — `containment_baseline` / `containment_reference` (secondary_affected, ready)
  - `G9` — `hybrid_containment` / `hybrid_embed_reference_summary` (secondary_affected, ready_generic)

### IC3 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_ic3_g0_f7817cbe`
- Benchmark group: `primary`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic3_g0_f7817cbe`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `12.643276390153916` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_is_located_in_place`: 151043 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_is_located_in_place`: 1528 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `place_is_part_of_place`: 1454 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `post_is_located_in_place`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`persons`; documents=`1528`; role=`normalized_reference_baseline`; relationships_available=`['person_study_at_organisation', 'post_is_located_in_place', 'forum_has_member_person', 'comment_reply_of_comment', 'person_likes_comment', 'comment_reply_of_post', 'comment_is_located_in_place', 'post_has_creator_person', 'comment_has_tag', 'person_is_located_in_place', 'comment_has_creator_person', 'person_work_at_organisation', 'forum_container_of_post', 'person_likes_post', 'person_has_interest_tag', 'forum_has_moderator_person', 'place_is_part_of_place', 'person_knows_person', 'post_has_tag', 'forum_has_tag']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IC3 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_ic3_g3_f4732bc1`
- Benchmark group: `primary`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic3_g3_f4732bc1`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `14.084755782969296` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_is_located_in_place`: 151043 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_is_located_in_place`: 1528 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `place_is_part_of_place`: 1454 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `post_is_located_in_place`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ic3_g3_f4732bc1_root_summary`; documents=`1528`; role=`generic_root_summary`; root_collection=`persons`; root_pk=`person_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ic3_g3_f4732bc1_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- Relationship post_is_located_in_place does not expose root field person_id; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- Relationship place_is_part_of_place does not expose root field person_id; skipped for root summary.
- No ID fields found in comment_reply_of_post; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in comment_reply_of_comment; skipped for root summary.
- No ID fields found in forum_container_of_post; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- Relationship comment_is_located_in_place does not expose root field person_id; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.

### IC3 / G7 — `containment_baseline`

- Candidate ID: `ldbc_snb_ic3_g7_a1750f34`
- Benchmark group: `secondary_affected`
- Document strategy: `containment_reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic3_g7_a1750f34`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `13.084576515946535` seconds

**Physical interpretation.**

Containment-reference baseline. The candidate represents the activated containment family while preserving reference-based access to the required base collections. In this materialization manifest, query-specific G7 candidates may be represented by the loaded root/contained collections and relationship references rather than by a new derived collection.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_is_located_in_place`: 151043 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_is_located_in_place`: 1528 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `place_is_part_of_place`: 1454 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `post_is_located_in_place`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`persons`; documents=`1528`; role=`containment_reference_baseline`; relationships_available=`['comment_has_tag', 'comment_reply_of_post', 'place_is_part_of_place', 'person_is_located_in_place', 'person_work_at_organisation', 'forum_has_member_person', 'forum_has_tag', 'person_study_at_organisation', 'forum_has_moderator_person', 'post_has_creator_person', 'forum_container_of_post', 'comment_is_located_in_place', 'comment_has_creator_person', 'person_has_interest_tag', 'person_likes_post', 'comment_reply_of_comment', 'post_is_located_in_place', 'person_knows_person', 'post_has_tag', 'person_likes_comment']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IC3 / G9 — `hybrid_containment`

- Candidate ID: `ldbc_snb_ic3_g9_75aa81cd`
- Benchmark group: `secondary_affected`
- Document strategy: `hybrid_embed_reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic3_g9_75aa81cd`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `13.571756056975572` seconds

**Physical interpretation.**

Hybrid containment pattern. The candidate combines reference-based access with derived summary/containment structures. In generic cases, the manifest records a root summary collection derived from the activated template.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_is_located_in_place`: 151043 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_is_located_in_place`: 1528 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `place_is_part_of_place`: 1454 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `post_is_located_in_place`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ic3_g9_75aa81cd_root_summary`; documents=`1528`; role=`generic_root_summary`; root_collection=`persons`; root_pk=`person_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ic3_g9_75aa81cd_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in person_likes_post; skipped for root summary.
- Relationship comment_is_located_in_place does not expose root field person_id; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.
- No ID fields found in comment_reply_of_comment; skipped for root summary.
- Relationship place_is_part_of_place does not expose root field person_id; skipped for root summary.
- No ID fields found in comment_reply_of_post; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in forum_container_of_post; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- Relationship post_is_located_in_place does not expose root field person_id; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.

## IC4 — `IC4_NewTopics`

- Number of candidates: 2
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (primary, ready)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (primary, ready_generic)

### IC4 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_ic4_g0_54d8940c`
- Benchmark group: `primary`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic4_g0_54d8940c`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `9.733431142754853` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `post_has_tag`: 51118 documents
- `posts`: 135701 documents
- `tags`: 16080 documents

**Derived physical collections created.**

- collection=`persons`; documents=`1528`; role=`normalized_reference_baseline`; relationships_available=`['forum_has_moderator_person', 'person_likes_comment', 'forum_has_member_person', 'person_study_at_organisation', 'person_work_at_organisation', 'post_has_creator_person', 'comment_has_tag', 'post_has_tag', 'person_likes_post', 'forum_container_of_post', 'comment_reply_of_post', 'person_knows_person', 'person_has_interest_tag', 'comment_reply_of_comment', 'forum_has_tag']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IC4 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_ic4_g3_00df9f3e`
- Benchmark group: `primary`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic4_g3_00df9f3e`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `10.7964323698543` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `post_has_tag`: 51118 documents
- `posts`: 135701 documents
- `tags`: 16080 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ic4_g3_00df9f3e_root_summary`; documents=`1421`; role=`generic_root_summary`; root_collection=`persons`; root_pk=`person_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ic4_g3_00df9f3e_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in forum_container_of_post; skipped for root summary.
- No ID fields found in comment_reply_of_post; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- Relationship post_has_tag does not expose root field person_id; skipped for root summary.
- No ID fields found in comment_reply_of_comment; skipped for root summary.

## IC5 — `IC5_NewGroups`

- Number of candidates: 6
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (primary, ready_with_warnings)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (primary, ready_generic)
  - `G4` — `explicit_edge_collection` / `edge_document` (secondary_affected, ready_generic)
  - `G6` — `referenced_or_reverse_indexed_edges` / `edge_reference_reverse_index` (secondary_affected, ready_generic)
  - `G7` — `containment_baseline` / `containment_reference` (secondary_affected, ready)
  - `G9` — `hybrid_containment` / `hybrid_embed_reference_summary` (secondary_affected, ready_generic)

### IC5 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_ic5_g0_f44bd6f8`
- Benchmark group: `primary`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic5_g0_f44bd6f8`
- Status: `ready_with_warnings / query_specific / ready_for_benchmark=True`
- Materialization time: `19.37199142994359` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comments`: 151043 documents
- `forum_container_of_post`: 135701 documents
- `forum_has_member_person`: 123268 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`persons`; documents=`0`; role=`normalized_reference_baseline`; relationships_available=`['comment_reply_of_post', 'forum_has_moderator_person', 'person_likes_comment', 'post_has_creator_person', 'forum_has_tag', 'comment_has_tag', 'person_has_interest_tag', 'person_work_at_organisation', 'forum_has_member_person', 'person_likes_post', 'post_has_tag', 'comment_reply_of_comment', 'forum_container_of_post', 'person_knows_person', 'person_study_at_organisation']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IC5 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_ic5_g3_45734260`
- Benchmark group: `primary`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic5_g3_45734260`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `13.0936294561252` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comments`: 151043 documents
- `forum_container_of_post`: 135701 documents
- `forum_has_member_person`: 123268 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ic5_g3_45734260_root_summary`; documents=`1501`; role=`generic_root_summary`; root_collection=`persons`; root_pk=`person_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ic5_g3_45734260_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- Relationship forum_container_of_post does not expose root field person_id; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in comment_reply_of_post; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in comment_reply_of_comment; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.

### IC5 / G4 — `explicit_edge_collection`

- Candidate ID: `ldbc_snb_ic5_g4_69144c92`
- Benchmark group: `secondary_affected`
- Document strategy: `edge_document`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic5_g4_69144c92`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `17.85385619616136` seconds

**Physical interpretation.**

Explicit edge-collection pattern. The candidate keeps the base collections and adds explicit MongoDB edge collections derived from the activated relationship collections. These edge documents expose source/target or query-specific endpoint fields and are indexed for traversal.

**Base collections loaded.**

- `comments`: 151043 documents
- `forum_container_of_post`: 135701 documents
- `forum_has_member_person`: 123268 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ic5_g4_69144c92_edge_forum_container_of_post`; documents=`135701`; role=`generic_explicit_edge_collection`; relationship=`forum_container_of_post`; endpoint_inference=`relationship_priority`
- collection=`phys_ldbc_snb_ic5_g4_69144c92_edge_person_knows_person`; documents=`14073`; role=`generic_explicit_edge_collection`; relationship=`person_knows_person`; endpoint_inference=`relationship_priority`
- collection=`phys_ldbc_snb_ic5_g4_69144c92_edge_forum_has_member_person`; documents=`123268`; role=`generic_explicit_edge_collection`; relationship=`forum_has_member_person`; endpoint_inference=`root_pk_priority`
- collection=`phys_ldbc_snb_ic5_g4_69144c92_edge_post_has_creator_person`; documents=`135701`; role=`generic_explicit_edge_collection`; relationship=`post_has_creator_person`; endpoint_inference=`root_pk_priority`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ic5_g4_69144c92_edge_forum_container_of_post`; index=`source_id_1`
- collection=`phys_ldbc_snb_ic5_g4_69144c92_edge_forum_container_of_post`; index=`target_id_1`
- collection=`phys_ldbc_snb_ic5_g4_69144c92_edge_forum_container_of_post`; index=`source_id_1_creation_date_-1`
- collection=`phys_ldbc_snb_ic5_g4_69144c92_edge_person_knows_person`; index=`source_id_1`
- collection=`phys_ldbc_snb_ic5_g4_69144c92_edge_person_knows_person`; index=`target_id_1`
- collection=`phys_ldbc_snb_ic5_g4_69144c92_edge_person_knows_person`; index=`source_id_1_creation_date_-1`
- collection=`phys_ldbc_snb_ic5_g4_69144c92_edge_forum_has_member_person`; index=`source_id_1`
- collection=`phys_ldbc_snb_ic5_g4_69144c92_edge_forum_has_member_person`; index=`target_id_1`
- collection=`phys_ldbc_snb_ic5_g4_69144c92_edge_forum_has_member_person`; index=`source_id_1_creation_date_-1`
- collection=`phys_ldbc_snb_ic5_g4_69144c92_edge_post_has_creator_person`; index=`source_id_1`
- collection=`phys_ldbc_snb_ic5_g4_69144c92_edge_post_has_creator_person`; index=`target_id_1`
- collection=`phys_ldbc_snb_ic5_g4_69144c92_edge_post_has_creator_person`; index=`source_id_1_creation_date_-1`

**Warnings / notes from materializer.**

- Could not infer endpoint fields for relationship collection post_has_tag.
- Could not infer endpoint fields for relationship collection person_study_at_organisation.
- Could not infer endpoint fields for relationship collection person_likes_post.
- Could not infer endpoint fields for relationship collection person_has_interest_tag.
- Could not infer endpoint fields for relationship collection forum_has_moderator_person.
- Could not infer endpoint fields for relationship collection person_work_at_organisation.
- Could not infer endpoint fields for relationship collection comment_reply_of_comment.
- Could not infer endpoint fields for relationship collection forum_has_tag.
- Could not infer endpoint fields for relationship collection comment_has_tag.
- Could not infer endpoint fields for relationship collection person_likes_comment.
- Could not infer endpoint fields for relationship collection comment_reply_of_post.

### IC5 / G6 — `referenced_or_reverse_indexed_edges`

- Candidate ID: `ldbc_snb_ic5_g6_733601c1`
- Benchmark group: `secondary_affected`
- Document strategy: `edge_reference_reverse_index`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic5_g6_733601c1`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `17.53430201066658` seconds

**Physical interpretation.**

Referenced or reverse-indexed edge pattern. The candidate keeps the base collections and adds reverse-index or endpoint-indexed collections. These collections are designed to support lookup from the query-side endpoint to the referenced/related endpoint.

**Base collections loaded.**

- `comments`: 151043 documents
- `forum_container_of_post`: 135701 documents
- `forum_has_member_person`: 123268 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ic5_g6_733601c1_rev_forum_has_member_person`; documents=`123268`; role=`generic_reverse_index`; relationship=`forum_has_member_person`; endpoint_inference=`root_pk_priority`
- collection=`phys_ldbc_snb_ic5_g6_733601c1_rev_person_knows_person`; documents=`14073`; role=`generic_reverse_index`; relationship=`person_knows_person`; endpoint_inference=`relationship_priority`
- collection=`phys_ldbc_snb_ic5_g6_733601c1_rev_forum_container_of_post`; documents=`135701`; role=`generic_reverse_index`; relationship=`forum_container_of_post`; endpoint_inference=`relationship_priority`
- collection=`phys_ldbc_snb_ic5_g6_733601c1_rev_post_has_creator_person`; documents=`135701`; role=`generic_reverse_index`; relationship=`post_has_creator_person`; endpoint_inference=`root_pk_priority`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ic5_g6_733601c1_rev_forum_has_member_person`; index=`lookup_id_1`
- collection=`phys_ldbc_snb_ic5_g6_733601c1_rev_forum_has_member_person`; index=`referenced_id_1`
- collection=`phys_ldbc_snb_ic5_g6_733601c1_rev_forum_has_member_person`; index=`lookup_id_1_creation_date_-1`
- collection=`phys_ldbc_snb_ic5_g6_733601c1_rev_person_knows_person`; index=`lookup_id_1`
- collection=`phys_ldbc_snb_ic5_g6_733601c1_rev_person_knows_person`; index=`referenced_id_1`
- collection=`phys_ldbc_snb_ic5_g6_733601c1_rev_person_knows_person`; index=`lookup_id_1_creation_date_-1`
- collection=`phys_ldbc_snb_ic5_g6_733601c1_rev_forum_container_of_post`; index=`lookup_id_1`
- collection=`phys_ldbc_snb_ic5_g6_733601c1_rev_forum_container_of_post`; index=`referenced_id_1`
- collection=`phys_ldbc_snb_ic5_g6_733601c1_rev_forum_container_of_post`; index=`lookup_id_1_creation_date_-1`
- collection=`phys_ldbc_snb_ic5_g6_733601c1_rev_post_has_creator_person`; index=`lookup_id_1`
- collection=`phys_ldbc_snb_ic5_g6_733601c1_rev_post_has_creator_person`; index=`referenced_id_1`
- collection=`phys_ldbc_snb_ic5_g6_733601c1_rev_post_has_creator_person`; index=`lookup_id_1_creation_date_-1`

**Warnings / notes from materializer.**

- Could not infer endpoint fields for reverse index from person_work_at_organisation.
- Could not infer endpoint fields for reverse index from person_likes_post.
- Could not infer endpoint fields for reverse index from person_study_at_organisation.
- Could not infer endpoint fields for reverse index from comment_has_tag.
- Could not infer endpoint fields for reverse index from person_has_interest_tag.
- Could not infer endpoint fields for reverse index from forum_has_moderator_person.
- Could not infer endpoint fields for reverse index from post_has_tag.
- Could not infer endpoint fields for reverse index from comment_reply_of_comment.
- Could not infer endpoint fields for reverse index from comment_reply_of_post.
- Could not infer endpoint fields for reverse index from person_likes_comment.
- Could not infer endpoint fields for reverse index from forum_has_tag.

### IC5 / G7 — `containment_baseline`

- Candidate ID: `ldbc_snb_ic5_g7_a2002d4c`
- Benchmark group: `secondary_affected`
- Document strategy: `containment_reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic5_g7_a2002d4c`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `11.527502283919604` seconds

**Physical interpretation.**

Containment-reference baseline. The candidate represents the activated containment family while preserving reference-based access to the required base collections. In this materialization manifest, query-specific G7 candidates may be represented by the loaded root/contained collections and relationship references rather than by a new derived collection.

**Base collections loaded.**

- `comments`: 151043 documents
- `forum_container_of_post`: 135701 documents
- `forum_has_member_person`: 123268 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`persons`; documents=`1528`; role=`containment_reference_baseline`; relationships_available=`['forum_has_member_person', 'comment_reply_of_comment', 'comment_reply_of_post', 'forum_has_moderator_person', 'post_has_creator_person', 'person_work_at_organisation', 'person_has_interest_tag', 'forum_container_of_post', 'comment_has_tag', 'post_has_tag', 'person_study_at_organisation', 'person_likes_post', 'person_likes_comment', 'person_knows_person', 'forum_has_tag']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IC5 / G9 — `hybrid_containment`

- Candidate ID: `ldbc_snb_ic5_g9_7a7a63d2`
- Benchmark group: `secondary_affected`
- Document strategy: `hybrid_embed_reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic5_g9_7a7a63d2`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `12.750286252703518` seconds

**Physical interpretation.**

Hybrid containment pattern. The candidate combines reference-based access with derived summary/containment structures. In generic cases, the manifest records a root summary collection derived from the activated template.

**Base collections loaded.**

- `comments`: 151043 documents
- `forum_container_of_post`: 135701 documents
- `forum_has_member_person`: 123268 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ic5_g9_7a7a63d2_root_summary`; documents=`1501`; role=`generic_root_summary`; root_collection=`persons`; root_pk=`person_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ic5_g9_7a7a63d2_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in comment_reply_of_post; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in comment_reply_of_comment; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- Relationship forum_container_of_post does not expose root field person_id; skipped for root summary.

## IC6 — `IC6_TagCoOccurrence`

- Number of candidates: 2
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (primary, ready)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (primary, ready_generic)

### IC6 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_ic6_g0_f6a698ed`
- Benchmark group: `primary`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic6_g0_f6a698ed`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `9.56373698823154` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `post_has_tag`: 51118 documents
- `posts`: 135701 documents
- `tags`: 16080 documents

**Derived physical collections created.**

- collection=`persons`; documents=`1528`; role=`normalized_reference_baseline`; relationships_available=`['forum_container_of_post', 'comment_reply_of_comment', 'person_likes_post', 'forum_has_moderator_person', 'post_has_tag', 'forum_has_member_person', 'person_knows_person', 'comment_has_tag', 'person_likes_comment', 'person_work_at_organisation', 'person_has_interest_tag', 'forum_has_tag', 'comment_reply_of_post', 'person_study_at_organisation', 'post_has_creator_person']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IC6 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_ic6_g3_9a00a0b5`
- Benchmark group: `primary`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic6_g3_9a00a0b5`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `10.522905461024491` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `post_has_tag`: 51118 documents
- `posts`: 135701 documents
- `tags`: 16080 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ic6_g3_9a00a0b5_root_summary`; documents=`1421`; role=`generic_root_summary`; root_collection=`persons`; root_pk=`person_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ic6_g3_9a00a0b5_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in forum_container_of_post; skipped for root summary.
- Relationship post_has_tag does not expose root field person_id; skipped for root summary.
- No ID fields found in comment_reply_of_comment; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in comment_reply_of_post; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.

## IC7 — `IC7_RecentLikers`

- Number of candidates: 4
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (primary, ready)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (primary, ready)
  - `G4` — `explicit_edge_collection` / `edge_document` (secondary_affected, ready)
  - `G6` — `referenced_or_reverse_indexed_edges` / `edge_reference_reverse_index` (secondary_affected, ready)

### IC7 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_ic7_g0_39cfc8f6`
- Benchmark group: `primary`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic7_g0_39cfc8f6`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `12.058021403849123` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `person_likes_comment`: 62225 documents
- `person_likes_post`: 47215 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`persons`; documents=`1528`; role=`normalized_reference_baseline`; relationships_available=`['person_has_interest_tag', 'comment_reply_of_comment', 'post_has_creator_person', 'comment_reply_of_post', 'comment_has_creator_person', 'comment_has_tag', 'forum_has_moderator_person', 'person_likes_post', 'person_study_at_organisation', 'forum_has_tag', 'forum_has_member_person', 'forum_container_of_post', 'person_knows_person', 'person_work_at_organisation', 'post_has_tag', 'person_likes_comment']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### IC7 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_ic7_g3_d6d26f02`
- Benchmark group: `primary`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic7_g3_d6d26f02`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `23.75629931502044` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `person_likes_comment`: 62225 documents
- `person_likes_post`: 47215 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`ic7_g3_person_recent_liker_summary`; documents=`1143`; role=`owner_recent_liker_summary`

**Indexes created on derived physical collections.**

- collection=`ic7_g3_person_recent_liker_summary`; index=`owner_person_id_1`

**Warnings / notes from materializer.**

_None._

### IC7 / G4 — `explicit_edge_collection`

- Candidate ID: `ldbc_snb_ic7_g4_5de4a081`
- Benchmark group: `secondary_affected`
- Document strategy: `edge_document`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic7_g4_5de4a081`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `13.648650551214814` seconds

**Physical interpretation.**

Explicit edge-collection pattern. The candidate keeps the base collections and adds explicit MongoDB edge collections derived from the activated relationship collections. These edge documents expose source/target or query-specific endpoint fields and are indexed for traversal.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `person_likes_comment`: 62225 documents
- `person_likes_post`: 47215 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`ic7_g4_explicit_like_edges`; documents=`109440`; role=`explicit_like_edge_collection`

**Indexes created on derived physical collections.**

- collection=`ic7_g4_explicit_like_edges`; index=`owner_person_id_1`
- collection=`ic7_g4_explicit_like_edges`; index=`liker_person_id_1`
- collection=`ic7_g4_explicit_like_edges`; index=`owner_person_id_1_creation_date_-1`

**Warnings / notes from materializer.**

_None._

### IC7 / G6 — `referenced_or_reverse_indexed_edges`

- Candidate ID: `ldbc_snb_ic7_g6_084f8a43`
- Benchmark group: `secondary_affected`
- Document strategy: `edge_reference_reverse_index`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ic7_g6_084f8a43`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `14.389820433221756` seconds

**Physical interpretation.**

Referenced or reverse-indexed edge pattern. The candidate keeps the base collections and adds reverse-index or endpoint-indexed collections. These collections are designed to support lookup from the query-side endpoint to the referenced/related endpoint.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `person_likes_comment`: 62225 documents
- `person_likes_post`: 47215 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`ic7_g6_owner_liker_reverse_index`; documents=`67297`; role=`owner_liker_reverse_index`

**Indexes created on derived physical collections.**

- collection=`ic7_g6_owner_liker_reverse_index`; index=`owner_person_id_1`
- collection=`ic7_g6_owner_liker_reverse_index`; index=`liker_person_id_1`
- collection=`ic7_g6_owner_liker_reverse_index`; index=`owner_person_id_1_latest_creation_date_-1`

**Warnings / notes from materializer.**

_None._

## INS1 — `INS1_AddPerson`

- Number of candidates: 2
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (primary, ready)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (primary, ready_generic)

### INS1 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_ins1_g0_ffbfd07e`
- Benchmark group: `primary`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins1_g0_ffbfd07e`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `8.079300520941615` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `organisations`: 7955 documents
- `person_has_interest_tag`: 35475 documents
- `person_is_located_in_place`: 1528 documents
- `person_study_at_organisation`: 1209 documents
- `person_work_at_organisation`: 3313 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents
- `tags`: 16080 documents

**Derived physical collections created.**

- collection=`persons`; documents=`1528`; role=`normalized_reference_baseline`; relationships_available=`['post_has_tag', 'comment_reply_of_post', 'person_knows_person', 'forum_has_member_person', 'person_likes_comment', 'person_study_at_organisation', 'person_is_located_in_place', 'person_work_at_organisation', 'forum_container_of_post', 'forum_has_tag', 'person_likes_post', 'comment_has_tag', 'person_has_interest_tag', 'comment_reply_of_comment', 'forum_has_moderator_person']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### INS1 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_ins1_g3_10a467d5`
- Benchmark group: `primary`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins1_g3_10a467d5`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `8.18262399174273` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `organisations`: 7955 documents
- `person_has_interest_tag`: 35475 documents
- `person_is_located_in_place`: 1528 documents
- `person_study_at_organisation`: 1209 documents
- `person_work_at_organisation`: 3313 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents
- `tags`: 16080 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ins1_g3_10a467d5_root_summary`; documents=`1528`; role=`generic_root_summary`; root_collection=`persons`; root_pk=`person_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ins1_g3_10a467d5_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in comment_reply_of_post; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in person_knows_person; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in forum_container_of_post; skipped for root summary.
- No ID fields found in comment_reply_of_comment; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.

## INS2 — `INS2_AddLikeToPost`

- Number of candidates: 2
- Activated candidates:
  - `G4` — `explicit_edge_collection` / `edge_document` (primary, ready_generic)
  - `G6` — `referenced_or_reverse_indexed_edges` / `edge_reference_reverse_index` (primary, ready_generic)

### INS2 / G4 — `explicit_edge_collection`

- Candidate ID: `ldbc_snb_ins2_g4_9fb1f96c`
- Benchmark group: `primary`
- Document strategy: `edge_document`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins2_g4_9fb1f96c`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `8.721640078816563` seconds

**Physical interpretation.**

Explicit edge-collection pattern. The candidate keeps the base collections and adds explicit MongoDB edge collections derived from the activated relationship collections. These edge documents expose source/target or query-specific endpoint fields and are indexed for traversal.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_likes_post`: 47215 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ins2_g4_9fb1f96c_edge_person_likes_post`; documents=`47215`; role=`generic_explicit_edge_collection`; relationship=`person_likes_post`; endpoint_inference=`root_pk_priority`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ins2_g4_9fb1f96c_edge_person_likes_post`; index=`source_id_1`
- collection=`phys_ldbc_snb_ins2_g4_9fb1f96c_edge_person_likes_post`; index=`target_id_1`
- collection=`phys_ldbc_snb_ins2_g4_9fb1f96c_edge_person_likes_post`; index=`source_id_1_creation_date_-1`

**Warnings / notes from materializer.**

- Could not infer endpoint fields for relationship collection person_likes_comment.
- Could not infer endpoint fields for relationship collection comment_reply_of_post.
- Could not infer endpoint fields for relationship collection post_has_tag.
- Could not infer endpoint fields for relationship collection forum_has_tag.
- Could not infer endpoint fields for relationship collection comment_reply_of_comment.
- Could not infer endpoint fields for relationship collection forum_has_member_person.
- Could not infer endpoint fields for relationship collection person_study_at_organisation.
- Could not infer endpoint fields for relationship collection forum_container_of_post.
- Could not infer endpoint fields for relationship collection forum_has_moderator_person.
- Could not infer endpoint fields for relationship collection person_work_at_organisation.
- Could not infer endpoint fields for relationship collection person_has_interest_tag.
- Could not infer endpoint fields for relationship collection person_knows_person.
- Could not infer endpoint fields for relationship collection comment_has_tag.

### INS2 / G6 — `referenced_or_reverse_indexed_edges`

- Candidate ID: `ldbc_snb_ins2_g6_f226f1c0`
- Benchmark group: `primary`
- Document strategy: `edge_reference_reverse_index`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins2_g6_f226f1c0`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `16.181758848018944` seconds

**Physical interpretation.**

Referenced or reverse-indexed edge pattern. The candidate keeps the base collections and adds reverse-index or endpoint-indexed collections. These collections are designed to support lookup from the query-side endpoint to the referenced/related endpoint.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_likes_post`: 47215 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ins2_g6_f226f1c0_rev_person_likes_post`; documents=`47215`; role=`generic_reverse_index`; relationship=`person_likes_post`; endpoint_inference=`root_pk_priority`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ins2_g6_f226f1c0_rev_person_likes_post`; index=`lookup_id_1`
- collection=`phys_ldbc_snb_ins2_g6_f226f1c0_rev_person_likes_post`; index=`referenced_id_1`
- collection=`phys_ldbc_snb_ins2_g6_f226f1c0_rev_person_likes_post`; index=`lookup_id_1_creation_date_-1`

**Warnings / notes from materializer.**

- Could not infer endpoint fields for reverse index from comment_has_tag.
- Could not infer endpoint fields for reverse index from comment_reply_of_comment.
- Could not infer endpoint fields for reverse index from person_study_at_organisation.
- Could not infer endpoint fields for reverse index from person_knows_person.
- Could not infer endpoint fields for reverse index from comment_reply_of_post.
- Could not infer endpoint fields for reverse index from forum_has_moderator_person.
- Could not infer endpoint fields for reverse index from person_likes_comment.
- Could not infer endpoint fields for reverse index from forum_container_of_post.
- Could not infer endpoint fields for reverse index from person_work_at_organisation.
- Could not infer endpoint fields for reverse index from forum_has_member_person.
- Could not infer endpoint fields for reverse index from person_has_interest_tag.
- Could not infer endpoint fields for reverse index from post_has_tag.
- Could not infer endpoint fields for reverse index from forum_has_tag.

## INS3 — `INS3_AddLikeToComment`

- Number of candidates: 2
- Activated candidates:
  - `G4` — `explicit_edge_collection` / `edge_document` (primary, ready_generic)
  - `G6` — `referenced_or_reverse_indexed_edges` / `edge_reference_reverse_index` (primary, ready_generic)

### INS3 / G4 — `explicit_edge_collection`

- Candidate ID: `ldbc_snb_ins3_g4_9ec9f8f6`
- Benchmark group: `primary`
- Document strategy: `edge_document`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins3_g4_9ec9f8f6`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `8.720434186980128` seconds

**Physical interpretation.**

Explicit edge-collection pattern. The candidate keeps the base collections and adds explicit MongoDB edge collections derived from the activated relationship collections. These edge documents expose source/target or query-specific endpoint fields and are indexed for traversal.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_likes_comment`: 62225 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ins3_g4_9ec9f8f6_edge_person_likes_comment`; documents=`62225`; role=`generic_explicit_edge_collection`; relationship=`person_likes_comment`; endpoint_inference=`root_pk_priority`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ins3_g4_9ec9f8f6_edge_person_likes_comment`; index=`source_id_1`
- collection=`phys_ldbc_snb_ins3_g4_9ec9f8f6_edge_person_likes_comment`; index=`target_id_1`
- collection=`phys_ldbc_snb_ins3_g4_9ec9f8f6_edge_person_likes_comment`; index=`source_id_1_creation_date_-1`

**Warnings / notes from materializer.**

- Could not infer endpoint fields for relationship collection comment_reply_of_post.
- Could not infer endpoint fields for relationship collection person_has_interest_tag.
- Could not infer endpoint fields for relationship collection post_has_tag.
- Could not infer endpoint fields for relationship collection person_study_at_organisation.
- Could not infer endpoint fields for relationship collection forum_has_moderator_person.
- Could not infer endpoint fields for relationship collection forum_has_tag.
- Could not infer endpoint fields for relationship collection forum_has_member_person.
- Could not infer endpoint fields for relationship collection person_knows_person.
- Could not infer endpoint fields for relationship collection person_work_at_organisation.
- Could not infer endpoint fields for relationship collection comment_has_tag.
- Could not infer endpoint fields for relationship collection forum_container_of_post.
- Could not infer endpoint fields for relationship collection person_likes_post.
- Could not infer endpoint fields for relationship collection comment_reply_of_comment.

### INS3 / G6 — `referenced_or_reverse_indexed_edges`

- Candidate ID: `ldbc_snb_ins3_g6_c1c01729`
- Benchmark group: `primary`
- Document strategy: `edge_reference_reverse_index`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins3_g6_c1c01729`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `9.03698360780254` seconds

**Physical interpretation.**

Referenced or reverse-indexed edge pattern. The candidate keeps the base collections and adds reverse-index or endpoint-indexed collections. These collections are designed to support lookup from the query-side endpoint to the referenced/related endpoint.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_likes_comment`: 62225 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ins3_g6_c1c01729_rev_person_likes_comment`; documents=`62225`; role=`generic_reverse_index`; relationship=`person_likes_comment`; endpoint_inference=`root_pk_priority`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ins3_g6_c1c01729_rev_person_likes_comment`; index=`lookup_id_1`
- collection=`phys_ldbc_snb_ins3_g6_c1c01729_rev_person_likes_comment`; index=`referenced_id_1`
- collection=`phys_ldbc_snb_ins3_g6_c1c01729_rev_person_likes_comment`; index=`lookup_id_1_creation_date_-1`

**Warnings / notes from materializer.**

- Could not infer endpoint fields for reverse index from forum_container_of_post.
- Could not infer endpoint fields for reverse index from person_knows_person.
- Could not infer endpoint fields for reverse index from post_has_tag.
- Could not infer endpoint fields for reverse index from forum_has_tag.
- Could not infer endpoint fields for reverse index from person_likes_post.
- Could not infer endpoint fields for reverse index from person_study_at_organisation.
- Could not infer endpoint fields for reverse index from comment_has_tag.
- Could not infer endpoint fields for reverse index from comment_reply_of_post.
- Could not infer endpoint fields for reverse index from comment_reply_of_comment.
- Could not infer endpoint fields for reverse index from person_has_interest_tag.
- Could not infer endpoint fields for reverse index from forum_has_moderator_person.
- Could not infer endpoint fields for reverse index from forum_has_member_person.
- Could not infer endpoint fields for reverse index from person_work_at_organisation.

## INS4 — `INS4_AddForum`

- Number of candidates: 2
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (primary, ready)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (primary, ready_generic)

### INS4 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_ins4_g0_63b0def3`
- Benchmark group: `primary`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins4_g0_63b0def3`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `8.613942873198539` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comments`: 151043 documents
- `forum_has_moderator_person`: 13750 documents
- `forum_has_tag`: 47697 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents
- `tags`: 16080 documents

**Derived physical collections created.**

- collection=`forums`; documents=`13750`; role=`normalized_reference_baseline`; relationships_available=`['comment_reply_of_comment', 'forum_container_of_post', 'post_has_tag', 'comment_reply_of_post', 'forum_has_member_person', 'person_work_at_organisation', 'person_has_interest_tag', 'forum_has_moderator_person', 'person_study_at_organisation', 'comment_has_tag', 'person_likes_comment', 'forum_has_tag', 'person_likes_post', 'person_knows_person']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### INS4 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_ins4_g3_b5f0ac72`
- Benchmark group: `primary`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins4_g3_b5f0ac72`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `8.688494877889752` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comments`: 151043 documents
- `forum_has_moderator_person`: 13750 documents
- `forum_has_tag`: 47697 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents
- `tags`: 16080 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ins4_g3_b5f0ac72_root_summary`; documents=`13750`; role=`generic_root_summary`; root_collection=`forums`; root_pk=`forum_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ins4_g3_b5f0ac72_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in comment_reply_of_post; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in person_knows_person; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in forum_container_of_post; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in comment_reply_of_comment; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.

## INS5 — `INS5_AddForumMembership`

- Number of candidates: 2
- Activated candidates:
  - `G4` — `explicit_edge_collection` / `edge_document` (primary, ready_generic)
  - `G6` — `referenced_or_reverse_indexed_edges` / `edge_reference_reverse_index` (primary, ready_generic)

### INS5 / G4 — `explicit_edge_collection`

- Candidate ID: `ldbc_snb_ins5_g4_79a744a2`
- Benchmark group: `primary`
- Document strategy: `edge_document`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins5_g4_79a744a2`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `11.316177351865916` seconds

**Physical interpretation.**

Explicit edge-collection pattern. The candidate keeps the base collections and adds explicit MongoDB edge collections derived from the activated relationship collections. These edge documents expose source/target or query-specific endpoint fields and are indexed for traversal.

**Base collections loaded.**

- `comments`: 151043 documents
- `forum_has_member_person`: 123268 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ins5_g4_79a744a2_edge_forum_has_member_person`; documents=`123268`; role=`generic_explicit_edge_collection`; relationship=`forum_has_member_person`; endpoint_inference=`root_pk_priority`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ins5_g4_79a744a2_edge_forum_has_member_person`; index=`source_id_1`
- collection=`phys_ldbc_snb_ins5_g4_79a744a2_edge_forum_has_member_person`; index=`target_id_1`
- collection=`phys_ldbc_snb_ins5_g4_79a744a2_edge_forum_has_member_person`; index=`source_id_1_creation_date_-1`

**Warnings / notes from materializer.**

- Could not infer endpoint fields for relationship collection comment_reply_of_comment.
- Could not infer endpoint fields for relationship collection person_knows_person.
- Could not infer endpoint fields for relationship collection person_likes_comment.
- Could not infer endpoint fields for relationship collection person_study_at_organisation.
- Could not infer endpoint fields for relationship collection comment_has_tag.
- Could not infer endpoint fields for relationship collection comment_reply_of_post.
- Could not infer endpoint fields for relationship collection person_likes_post.
- Could not infer endpoint fields for relationship collection post_has_tag.
- Could not infer endpoint fields for relationship collection person_work_at_organisation.
- Could not infer endpoint fields for relationship collection forum_has_moderator_person.
- Could not infer endpoint fields for relationship collection forum_container_of_post.
- Could not infer endpoint fields for relationship collection person_has_interest_tag.
- Could not infer endpoint fields for relationship collection forum_has_tag.

### INS5 / G6 — `referenced_or_reverse_indexed_edges`

- Candidate ID: `ldbc_snb_ins5_g6_9496cfdb`
- Benchmark group: `primary`
- Document strategy: `edge_reference_reverse_index`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins5_g6_9496cfdb`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `10.827062242198735` seconds

**Physical interpretation.**

Referenced or reverse-indexed edge pattern. The candidate keeps the base collections and adds reverse-index or endpoint-indexed collections. These collections are designed to support lookup from the query-side endpoint to the referenced/related endpoint.

**Base collections loaded.**

- `comments`: 151043 documents
- `forum_has_member_person`: 123268 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ins5_g6_9496cfdb_rev_forum_has_member_person`; documents=`123268`; role=`generic_reverse_index`; relationship=`forum_has_member_person`; endpoint_inference=`root_pk_priority`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ins5_g6_9496cfdb_rev_forum_has_member_person`; index=`lookup_id_1`
- collection=`phys_ldbc_snb_ins5_g6_9496cfdb_rev_forum_has_member_person`; index=`referenced_id_1`
- collection=`phys_ldbc_snb_ins5_g6_9496cfdb_rev_forum_has_member_person`; index=`lookup_id_1_creation_date_-1`

**Warnings / notes from materializer.**

- Could not infer endpoint fields for reverse index from forum_container_of_post.
- Could not infer endpoint fields for reverse index from forum_has_moderator_person.
- Could not infer endpoint fields for reverse index from person_has_interest_tag.
- Could not infer endpoint fields for reverse index from person_knows_person.
- Could not infer endpoint fields for reverse index from person_study_at_organisation.
- Could not infer endpoint fields for reverse index from comment_reply_of_post.
- Could not infer endpoint fields for reverse index from person_likes_post.
- Could not infer endpoint fields for reverse index from post_has_tag.
- Could not infer endpoint fields for reverse index from person_likes_comment.
- Could not infer endpoint fields for reverse index from comment_reply_of_comment.
- Could not infer endpoint fields for reverse index from comment_has_tag.
- Could not infer endpoint fields for reverse index from person_work_at_organisation.
- Could not infer endpoint fields for reverse index from forum_has_tag.

## INS6 — `INS6_AddPost`

- Number of candidates: 4
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (primary, ready)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (primary, ready_generic)
  - `G7` — `containment_baseline` / `containment_reference` (secondary_affected, ready)
  - `G9` — `hybrid_containment` / `hybrid_embed_reference_summary` (secondary_affected, ready_generic)

### INS6 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_ins6_g0_50983b9d`
- Benchmark group: `primary`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins6_g0_50983b9d`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `12.270624464843422` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comments`: 151043 documents
- `forum_container_of_post`: 135701 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `post_has_tag`: 51118 documents
- `post_is_located_in_place`: 135701 documents
- `posts`: 135701 documents
- `tags`: 16080 documents

**Derived physical collections created.**

- collection=`posts`; documents=`135701`; role=`normalized_reference_baseline`; relationships_available=`['person_knows_person', 'forum_has_member_person', 'comment_reply_of_comment', 'person_study_at_organisation', 'post_has_creator_person', 'person_likes_comment', 'forum_has_tag', 'post_is_located_in_place', 'comment_has_tag', 'person_work_at_organisation', 'forum_has_moderator_person', 'comment_reply_of_post', 'person_likes_post', 'forum_container_of_post', 'post_has_tag', 'person_has_interest_tag']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### INS6 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_ins6_g3_d110d93b`
- Benchmark group: `primary`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins6_g3_d110d93b`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `15.376771206967533` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comments`: 151043 documents
- `forum_container_of_post`: 135701 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `post_has_tag`: 51118 documents
- `post_is_located_in_place`: 135701 documents
- `posts`: 135701 documents
- `tags`: 16080 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ins6_g3_d110d93b_root_summary`; documents=`135701`; role=`generic_root_summary`; root_collection=`posts`; root_pk=`post_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ins6_g3_d110d93b_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in person_knows_person; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in comment_reply_of_comment; skipped for root summary.
- No ID fields found in comment_reply_of_post; skipped for root summary.

### INS6 / G7 — `containment_baseline`

- Candidate ID: `ldbc_snb_ins6_g7_2ba4aefb`
- Benchmark group: `secondary_affected`
- Document strategy: `containment_reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins6_g7_2ba4aefb`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `17.661091790068895` seconds

**Physical interpretation.**

Containment-reference baseline. The candidate represents the activated containment family while preserving reference-based access to the required base collections. In this materialization manifest, query-specific G7 candidates may be represented by the loaded root/contained collections and relationship references rather than by a new derived collection.

**Base collections loaded.**

- `comments`: 151043 documents
- `forum_container_of_post`: 135701 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `post_has_tag`: 51118 documents
- `post_is_located_in_place`: 135701 documents
- `posts`: 135701 documents
- `tags`: 16080 documents

**Derived physical collections created.**

- collection=`posts`; documents=`135701`; role=`containment_reference_baseline`; relationships_available=`['person_study_at_organisation', 'post_has_tag', 'forum_has_tag', 'post_has_creator_person', 'comment_reply_of_post', 'person_has_interest_tag', 'person_likes_post', 'post_is_located_in_place', 'comment_reply_of_comment', 'person_likes_comment', 'forum_has_moderator_person', 'person_knows_person', 'forum_container_of_post', 'comment_has_tag', 'person_work_at_organisation', 'forum_has_member_person']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### INS6 / G9 — `hybrid_containment`

- Candidate ID: `ldbc_snb_ins6_g9_0dad4d32`
- Benchmark group: `secondary_affected`
- Document strategy: `hybrid_embed_reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins6_g9_0dad4d32`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `15.58380798669532` seconds

**Physical interpretation.**

Hybrid containment pattern. The candidate combines reference-based access with derived summary/containment structures. In generic cases, the manifest records a root summary collection derived from the activated template.

**Base collections loaded.**

- `comments`: 151043 documents
- `forum_container_of_post`: 135701 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `post_has_creator_person`: 135701 documents
- `post_has_tag`: 51118 documents
- `post_is_located_in_place`: 135701 documents
- `posts`: 135701 documents
- `tags`: 16080 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ins6_g9_0dad4d32_root_summary`; documents=`135701`; role=`generic_root_summary`; root_collection=`posts`; root_pk=`post_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ins6_g9_0dad4d32_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in comment_reply_of_post; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in comment_reply_of_comment; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in person_knows_person; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.

## INS7 — `INS7_AddComment`

- Number of candidates: 4
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (primary, ready)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (primary, ready_generic)
  - `G7` — `containment_baseline` / `containment_reference` (secondary_affected, ready)
  - `G9` — `hybrid_containment` / `hybrid_embed_reference_summary` (secondary_affected, ready_generic)

### INS7 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_ins7_g0_1f628fad`
- Benchmark group: `primary`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins7_g0_1f628fad`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `13.226967494003476` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_has_tag`: 191303 documents
- `comment_is_located_in_place`: 151043 documents
- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents
- `tags`: 16080 documents

**Derived physical collections created.**

- collection=`comments`; documents=`151043`; role=`normalized_reference_baseline`; relationships_available=`['person_knows_person', 'comment_reply_of_comment', 'person_study_at_organisation', 'person_likes_comment', 'forum_has_member_person', 'comment_is_located_in_place', 'forum_has_moderator_person', 'person_work_at_organisation', 'comment_has_creator_person', 'forum_container_of_post', 'person_has_interest_tag', 'forum_has_tag', 'comment_reply_of_post', 'person_likes_post', 'post_has_tag', 'comment_has_tag']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### INS7 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_ins7_g3_e7300dd8`
- Benchmark group: `primary`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins7_g3_e7300dd8`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `20.11621505208313` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_has_tag`: 191303 documents
- `comment_is_located_in_place`: 151043 documents
- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents
- `tags`: 16080 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ins7_g3_e7300dd8_root_summary`; documents=`151043`; role=`generic_root_summary`; root_collection=`comments`; root_pk=`comment_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ins7_g3_e7300dd8_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in forum_container_of_post; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.
- No ID fields found in person_knows_person; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.

### INS7 / G7 — `containment_baseline`

- Candidate ID: `ldbc_snb_ins7_g7_c86de251`
- Benchmark group: `secondary_affected`
- Document strategy: `containment_reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins7_g7_c86de251`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `14.03646067297086` seconds

**Physical interpretation.**

Containment-reference baseline. The candidate represents the activated containment family while preserving reference-based access to the required base collections. In this materialization manifest, query-specific G7 candidates may be represented by the loaded root/contained collections and relationship references rather than by a new derived collection.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_has_tag`: 191303 documents
- `comment_is_located_in_place`: 151043 documents
- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents
- `tags`: 16080 documents

**Derived physical collections created.**

- collection=`comments`; documents=`151043`; role=`containment_reference_baseline`; relationships_available=`['person_likes_post', 'comment_has_creator_person', 'comment_reply_of_comment', 'person_study_at_organisation', 'person_knows_person', 'forum_has_member_person', 'forum_container_of_post', 'comment_is_located_in_place', 'person_has_interest_tag', 'comment_has_tag', 'person_work_at_organisation', 'forum_has_tag', 'person_likes_comment', 'comment_reply_of_post', 'forum_has_moderator_person', 'post_has_tag']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### INS7 / G9 — `hybrid_containment`

- Candidate ID: `ldbc_snb_ins7_g9_bcd2ce9b`
- Benchmark group: `secondary_affected`
- Document strategy: `hybrid_embed_reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins7_g9_bcd2ce9b`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `20.8454949031584` seconds

**Physical interpretation.**

Hybrid containment pattern. The candidate combines reference-based access with derived summary/containment structures. In generic cases, the manifest records a root summary collection derived from the activated template.

**Base collections loaded.**

- `comment_has_creator_person`: 151043 documents
- `comment_has_tag`: 191303 documents
- `comment_is_located_in_place`: 151043 documents
- `comment_reply_of_comment`: 76787 documents
- `comment_reply_of_post`: 74256 documents
- `comments`: 151043 documents
- `forums`: 13750 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents
- `tags`: 16080 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ins7_g9_bcd2ce9b_root_summary`; documents=`151043`; role=`generic_root_summary`; root_collection=`comments`; root_pk=`comment_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ins7_g9_bcd2ce9b_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in forum_container_of_post; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in post_has_tag; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in person_knows_person; skipped for root summary.

## INS8 — `INS8_AddFriendship`

- Number of candidates: 2
- Activated candidates:
  - `G0` — `root_with_references` / `reference` (primary, ready)
  - `G3` — `root_with_references_or_summaries` / `reference_summary` (primary, ready_generic)

### INS8 / G0 — `root_with_references`

- Candidate ID: `ldbc_snb_ins8_g0_2acc6939`
- Benchmark group: `primary`
- Document strategy: `reference`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins8_g0_2acc6939`
- Status: `ready / query_specific / ready_for_benchmark=True`
- Materialization time: `7.565369478892535` seconds

**Physical interpretation.**

Reference-based baseline. The candidate keeps the required LDBC SNB entities and relationship collections as separate MongoDB collections, using indexes/references for traversal. No additional derived summary, edge, or reverse-index collection is required for this baseline unless explicitly recorded.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`persons`; documents=`1528`; role=`normalized_reference_baseline`; relationships_available=`['forum_has_moderator_person', 'forum_container_of_post', 'person_study_at_organisation', 'comment_reply_of_comment', 'forum_has_tag', 'person_likes_post', 'post_has_tag', 'comment_has_tag', 'comment_reply_of_post', 'person_work_at_organisation', 'person_has_interest_tag', 'forum_has_member_person', 'person_knows_person', 'person_likes_comment']`

**Indexes created on derived physical collections.**

_None recorded._

**Warnings / notes from materializer.**

_None._

### INS8 / G3 — `root_with_references_or_summaries`

- Candidate ID: `ldbc_snb_ins8_g3_8e5c5f42`
- Benchmark group: `primary`
- Document strategy: `reference_summary`
- MongoDB database: `ldbc_snb_phys_sf0_1_ldbc_snb_ins8_g3_8e5c5f42`
- Status: `ready_generic / generic_template / ready_for_benchmark=True`
- Materialization time: `7.878544764127582` seconds

**Physical interpretation.**

Root-with-references-or-summaries pattern. The candidate keeps the base collections and adds a summary/root-summary collection derived from the activated root and relationships. The benchmark executor must use this summary when evaluating this candidate.

**Base collections loaded.**

- `comments`: 151043 documents
- `forums`: 13750 documents
- `person_knows_person`: 14073 documents
- `persons`: 1528 documents
- `places`: 1460 documents
- `posts`: 135701 documents

**Derived physical collections created.**

- collection=`phys_ldbc_snb_ins8_g3_8e5c5f42_root_summary`; documents=`1199`; role=`generic_root_summary`; root_collection=`persons`; root_pk=`person_id`; root_inference=`artifact`

**Indexes created on derived physical collections.**

- collection=`phys_ldbc_snb_ins8_g3_8e5c5f42_root_summary`; index=`root_id_1`

**Warnings / notes from materializer.**

- No ID fields found in post_has_tag; skipped for root summary.
- No ID fields found in comment_reply_of_post; skipped for root summary.
- No ID fields found in forum_has_member_person; skipped for root summary.
- No ID fields found in forum_container_of_post; skipped for root summary.
- No ID fields found in comment_has_tag; skipped for root summary.
- No ID fields found in person_work_at_organisation; skipped for root summary.
- No ID fields found in forum_has_moderator_person; skipped for root summary.
- No ID fields found in comment_reply_of_comment; skipped for root summary.
- No ID fields found in person_likes_post; skipped for root summary.
- No ID fields found in person_study_at_organisation; skipped for root summary.
- No ID fields found in person_likes_comment; skipped for root summary.
- No ID fields found in forum_has_tag; skipped for root summary.
- No ID fields found in person_has_interest_tag; skipped for root summary.

## Manual validation notes

- `IC_IC5_G0_warning_validation_note.md`
- `INS6_retry_INS6_retry_validation_note.md`
- `IS_IS7_G0_warning_validation_note.md`

## Next phase

The next phase is to run the physical benchmark and query-plan analysis using this consolidated manifest. The benchmark script must read `physical_materialization_manifest.csv` and execute only candidates with `ready_for_benchmark = True`.
