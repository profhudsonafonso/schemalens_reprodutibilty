# SchemaLens FIBEN Artifacts Reused by the Lima & Mello Baseline

This file documents which artifacts from the SchemaLens FIBEN methodology notebook should be reused by the de Lima & Mello 2015 implementation.

Notebook source:

    methodology/fiben_methodology.ipynb

Possible output directories used by the notebook:

    output/framework
    methodology/output/framework

## Core artifacts for Lima & Mello

### BLOCK V6C — Manual FIBEN Relationship Join Hints

Expected files:

    variables/block_v06c/fiben_relationship_join_hints.csv
    variables/block_v06c/invalid_relationship_join_hints.csv
    variables/block_v06c/fiben_relationship_join_hints_metadata.json

Role in the Lima & Mello implementation:

- preserve the same relationship-to-column mappings used by SchemaLens;
- avoid defining new joins for FIBEN;
- keep the comparison fair by using the same conceptual relationship evidence.

### BLOCK V6 — Observed Cardinality with Manual FIBEN Join Hints

Expected files:

    variables/block_v06/observed_cardinality_by_relationship.csv
    variables/block_v06/relationship_cardinality.csv
    variables/block_v06/cardinality_observed.csv
    variables/block_v06/observed_cardinality_summary.csv
    variables/block_v06/uncomputed_cardinality_relationships.csv
    variables/block_v06/low_confidence_cardinality_relationships.csv
    variables/block_v06/no_match_cardinality_relationships.csv
    variables/block_v06/observed_cardinality_metadata.json

Role in the Lima & Mello implementation:

- provide observed relationship cardinalities;
- derive Avg(A, r, B);
- support the choice between Rule 4, Rule 5, and Rule 6;
- reduce the risk of using different cardinalities from SchemaLens.

## Supporting artifacts for interpretation only

These artifacts are useful for explaining the comparison with SchemaLens, but they should not directly drive the faithful Lima & Mello algorithm.

### BLOCK V7 — Semantic Classification of Relationships

    variables/block_v07/relationship_semantics.csv
    variables/block_v07/semantic_relationships.csv
    variables/block_v07/relationship_semantic_profile.csv
    variables/block_v07/semantic_type_summary.csv
    variables/block_v07/semantic_cardinality_summary.csv

### BLOCK V15 — Update Volatility by Entity

    variables/block_v15/update_volatility_by_entity.csv
    variables/block_v15/entity_update_volatility.csv
    variables/block_v15/update_volatility_events.csv
    variables/block_v15/update_volatility_summary.csv

### BLOCK V16 — Update Volatility by Query

    variables/block_v16/update_volatility_by_query.csv
    variables/block_v16/query_update_volatility.csv
    variables/block_v16/update_volatility_query_summary.csv

### BLOCK V18 — Observed Sharedness

    variables/block_v18/observed_sharedness_by_relationship.csv
    variables/block_v18/relationship_sharedness.csv
    variables/block_v18/sharedness_observed.csv
    variables/block_v18/query_edge_sharedness.csv
    variables/block_v18/query_sharedness_profile.csv

### BLOCK V20 — Final Document Variable Matrix

    variables/block_v20/final_document_variable_matrix.csv
    variables/block_v20/document_variable_matrix.csv
    variables/block_v20/activation_input_matrix.csv

## Methodological rule

For the Lima & Mello baseline, use SchemaLens artifacts only to reuse:

- conceptual schema;
- relationship joins;
- observed cardinalities;
- entity volumes;
- workload access paths.

Do not use SchemaLens activation variables to decide the Lima & Mello schema.

The Lima & Mello schema must be decided by:

- GAF;
- MAF;
- cardinality;
- participation;
- hierarchy conversion rules;
- relationship conversion rules.
