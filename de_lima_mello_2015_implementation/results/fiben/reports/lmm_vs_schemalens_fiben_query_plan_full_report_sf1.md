# Lima & Mello 2015 vs SchemaLens FIBEN query-plan comparison

Scale: `sf1`

## Method summary

| method        |   n_queries |   total_docs_examined |   total_keys_examined |   n_ixscan |   n_collscan |   n_lookup |   n_group |   n_unwind |
|:--------------|------------:|----------------------:|----------------------:|-----------:|-------------:|-----------:|----------:|-----------:|
| LimaMello2015 |           9 |                 22410 |                  1889 |          8 |            1 |          3 |         3 |          6 |
| SchemaLens    |           9 |                 15866 |                 14938 |          9 |            2 |          0 |         3 |          0 |

## Query interpretation

- **Q1**: both examine the same number of documents; both avoid COLLSCAN.
- **Q2**: both examine the same number of documents; both avoid COLLSCAN; Lima & Mello uses LOOKUP while SchemaLens avoids it.
- **Q3**: Lima & Mello examines fewer documents; both avoid COLLSCAN.
- **Q4**: Lima & Mello examines fewer documents; SchemaLens uses COLLSCAN while Lima & Mello avoids it; Lima & Mello uses LOOKUP while SchemaLens avoids it.
- **Q5**: Lima & Mello examines fewer documents; both avoid COLLSCAN.
- **Q6**: SchemaLens examines fewer documents; both use COLLSCAN; Lima & Mello uses LOOKUP while SchemaLens avoids it.
- **Q7**: Lima & Mello examines fewer documents; both avoid COLLSCAN.
- **Q8**: SchemaLens examines fewer documents; both avoid COLLSCAN.
- **Q9**: Lima & Mello examines fewer documents; both avoid COLLSCAN.