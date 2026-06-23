# DBSR vs SchemaLens on FIBEN SF10

## Protocol

This experiment compares a faithful DBSR physical materialization against the best SchemaLens observed MongoDB candidate for FIBEN at SF10.

The final DBSR protocol is:

- source database: `dbsr_fiben_sf10_source_full`
- physical DBSR materialization: full `dbsr_rank*` collections
- benchmark protocol: hot p95
- parameter protocol: original SchemaLens parameter-pool alignment
- Q9 adjustment: raw returned-count alignment for the low-cardinality buy/sell query
- failed executions: 0

The final comparison file is:

- `DBSR_implementation/results/fiben/dbsr_vs_schemalens_sf10_semantic_aligned_v8_original_pool_q9_raw_comparison.csv`

## Summary

| Metric | Value |
|---|---:|
| Queries compared | 9 |
| DBSR wins | 3 |
| SchemaLens wins | 6 |
| DBSR near SchemaLens within 5% | 3 |
| Average DBSR regret vs SchemaLens | 31.033760 |

## Per-query results

| Query | SchemaLens p95 ms | DBSR p95 ms | Winner | Returned-count ratio |
|---|---:|---:|---|---:|
| Q1 | 0.295784 | 0.217370 | DBSR | 1.000 |
| Q2 | 0.155368 | 0.812346 | SchemaLens | 1.000 |
| Q3 | 0.899143 | 113.679687 | SchemaLens | 1.000 |
| Q4 | 4.308413 | 578.854638 | SchemaLens | 1.119 |
| Q5 | 28.432783 | 12.834964 | DBSR | 1.003 |
| Q6 | 91.474332 | 5.481802 | DBSR | 1.000 |
| Q7 | 0.857698 | 1.568635 | SchemaLens | 1.000 |
| Q8 | 0.921652 | 1.555086 | SchemaLens | 0.989 |
| Q9 | 1.056870 | 18.524093 | SchemaLens | 1.000 |

## Interpretation

DBSR is competitive when its generated document trees match the dominant access pattern, especially for compact lookups and selected filtered cases. This appears in Q1, Q5, and Q6, where DBSR outperforms the best observed SchemaLens candidate.

SchemaLens is stronger across the full workload, winning six of nine read queries. The largest differences occur in Q3 and Q4. After parameter-pool alignment, Q3 has exact returned-count parity and Q4 has comparable returned-count scale, so the observed slowdown is not explained by a parameter mismatch. Instead, it indicates that the DBSR physical materialization requires expensive suffix-based traversal over nested structures, while SchemaLens selected candidates that better exploit the benchmarked MongoDB access paths.

Q6 is the main DBSR-favorable case. Its physical structure gives a compact path for the selected filtered retrieval, producing a substantially lower p95 than SchemaLens. This is useful evidence that DBSR can produce strong candidates for some query shapes, but it does not dominate the full workload.

Overall, the SF10 result supports the paper's main claim: a workload-aware, benchmark-based design-space reduction can preserve high-performing alternatives more robustly than a single baseline design generator. DBSR provides a meaningful baseline, but SchemaLens is more stable across heterogeneous FIBEN query patterns.
