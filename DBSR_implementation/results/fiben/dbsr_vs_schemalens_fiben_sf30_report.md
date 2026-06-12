# DBSR vs SchemaLens on FIBEN SF30

## Protocol

This experiment compares a faithful DBSR physical materialization against the best observed SchemaLens MongoDB candidate for FIBEN at SF30.

The final DBSR SF30 protocol is:

- source database: `dbsr_fiben_sf30_source_full`
- physical DBSR materialization: full `dbsr_rank*` collections
- query set: FIBEN Q1–Q9
- Q10: excluded from read-query comparison because it is an insert/update workload
- parameter protocol: original-pool alignment
- corporation parameter: IBM-compatible corporation id `2860`
- Q4: raw-sequence-aligned person pool
- Q9: raw-count-aligned security pool
- Q6: effective-runner alignment over capped listed-security retrieval
- benchmark protocol: hot p95, 10 hot runs
- failed executions: 0

## Summary

| Metric | Value |
|---|---:|
| Queries compared | 9 |
| DBSR wins | 3 |
| SchemaLens wins | 6 |
| DBSR near SchemaLens within 5% | 3 |
| Average DBSR regret vs SchemaLens | 33.179445 |

## Per-query results

| Query | SchemaLens p95 ms | DBSR p95 ms | Winner | Returned-count ratio |
|---|---:|---:|---|---:|
| Q1 | 0.224772 | 0.196788 | DBSR | 1.000 |
| Q2 | 0.250701 | 1.314892 | SchemaLens | 1.000 |
| Q3 | 1.652037 | 329.543310 | SchemaLens | 1.000 |
| Q4 | 17.142359 | 1677.835470 | SchemaLens | 1.000 |
| Q5 | 45.217182 | 12.415111 | DBSR | 1.003 |
| Q6 | 418.834830 | 0.502494 | DBSR | 1.000 |
| Q7 | 1.322278 | 1.587218 | SchemaLens | 1.000 |
| Q8 | 1.292882 | 1.571194 | SchemaLens | 0.989 |
| Q9 | 1.223861 | 1.774232 | SchemaLens | 1.000 |

## Interpretation

The SF30 result confirms the cross-scale pattern observed at SF1 and SF10. DBSR is competitive and sometimes faster for selected access patterns, especially Q1, Q5, and Q6. However, SchemaLens remains stronger across the full workload, winning six of nine read queries.

The largest SchemaLens advantages occur in Q3 and Q4. Both queries have exact returned-count parity after alignment, so the performance gap is not caused by semantic mismatch. Instead, it reflects the physical access path: DBSR follows one generated document-tree materialization, while SchemaLens selects among benchmarked activated alternatives.

Q6 is the strongest DBSR-favorable case at SF30. Under the effective benchmark semantics, DBSR answers the capped listed-security retrieval much faster than the best SchemaLens candidate.

Overall, SF30 reinforces the main conclusion: DBSR is a meaningful faithful baseline, but SchemaLens provides more robust workload-aware model selection across heterogeneous query patterns and scale factors.
