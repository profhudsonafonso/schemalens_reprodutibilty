# Lima & Mello 2015 vs SchemaLens: FIBEN query-plan comparison

Scale: `sf1`

## Method-level summary

| method        |   n_queries |   n_completed |   total_docs_examined |   total_keys_examined |   n_collscan |   n_ixscan |   n_lookup |   n_group |   n_unwind |
|:--------------|------------:|--------------:|----------------------:|----------------------:|-------------:|-----------:|-----------:|----------:|-----------:|
| LimaMello2015 |           9 |             9 |                 22410 |                  1889 |            1 |          8 |          3 |         3 |          6 |
| SchemaLens    |           9 |             9 |                 15866 |                 14938 |            2 |          0 |          0 |         3 |          0 |

## Query-level interpretation

- **Q1**: Q1: both examine the same number of documents.
- **Q2**: Q2: both examine the same number of documents; Lima & Mello requires lookup.
- **Q3**: Q3: Lima & Mello examines fewer documents.
- **Q4**: Q4: Lima & Mello examines fewer documents; SchemaLens uses COLLSCAN while Lima & Mello avoids it; Lima & Mello requires lookup.
- **Q5**: Q5: Lima & Mello examines fewer documents.
- **Q6**: Q6: SchemaLens examines fewer documents; both use COLLSCAN; Lima & Mello requires lookup.
- **Q7**: Q7: Lima & Mello examines fewer documents.
- **Q8**: Q8: SchemaLens examines fewer documents.
- **Q9**: Q9: Lima & Mello examines fewer documents.