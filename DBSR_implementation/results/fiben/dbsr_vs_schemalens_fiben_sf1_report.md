# DBSR vs SchemaLens on FIBEN SF1

## Protocol

This experiment compares a faithful DBSR physical materialization against the best observed SchemaLens MongoDB candidate for FIBEN at SF1.

The final DBSR SF1 protocol is:

- source database: `dbsr_fiben_sf1_source_full`
- physical DBSR materialization: full `dbsr_rank*` collections
- query set: FIBEN Q1–Q9
- Q10: excluded from read-query comparison because it is an insert/update workload
- parameter protocol: original-pool alignment
- corporation parameter: IBM-compatible corporation id `2860`
- Q6: effective-runner alignment over capped listed-security retrieval
- benchmark protocol: hot p95, 10 hot runs
- failed executions: 0

## Summary

| Metric | Value |
|---|---:|
| Queries compared | 9 |
| DBSR wins | 2 |
| SchemaLens wins | 7 |
| DBSR near SchemaLens within 5% | 2 |
| Average DBSR regret vs SchemaLens | 7.531969 |

## Per-query results

| Query | SchemaLens p95 ms | DBSR p95 ms | Winner | Returned-count ratio |
|---|---:|---:|---|---:|
| Q1 | 0.233373 | 0.215286 | DBSR | 1.000 |
| Q2 | 0.117117 | 0.791630 | SchemaLens | 1.000 |
| Q3 | 0.434946 | 8.885722 | SchemaLens | 1.000 |
| Q4 | 1.002833 | 42.196069 | SchemaLens | 1.000 |
| Q5 | 37.626791 | 12.358580 | DBSR | 1.003 |
| Q6 | 0.385924 | 0.425665 | SchemaLens | 1.000 |
| Q7 | 1.186999 | 1.546273 | SchemaLens | 1.000 |
| Q8 | 0.863551 | 1.567427 | SchemaLens | 0.989 |
| Q9 | 0.851476 | 1.745873 | SchemaLens | 1.000 |

## Interpretation

The SF1 result confirms that DBSR can produce competitive physical structures for selected access patterns, especially Q1 and Q5. However, SchemaLens wins seven of nine queries and remains stronger across the complete workload.

The strongest SchemaLens advantages appear in Q3 and Q4. After semantic alignment, both queries have exact returned-count parity, so the performance difference is not caused by parameter mismatch. Instead, it reflects the physical access path: DBSR must traverse nested/generated document structures, while SchemaLens selects benchmarked alternatives better matched to MongoDB execution.

Q5 is the strongest DBSR-favorable case at SF1. DBSR returns a comparable number of documents and substantially outperforms SchemaLens, showing that DBSR can be a meaningful baseline for document-tree-oriented workloads.

Overall, SF1 supports the same conclusion observed at SF10: DBSR is useful and sometimes faster, but SchemaLens is more robust across heterogeneous query patterns because it evaluates multiple activated design alternatives rather than relying on one generated structure.
