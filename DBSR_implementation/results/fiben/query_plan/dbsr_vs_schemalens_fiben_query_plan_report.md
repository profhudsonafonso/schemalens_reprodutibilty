# DBSR vs SchemaLens FIBEN Query-Plan Evidence

## Scope

This report compares MongoDB `explain("executionStats")` evidence for the faithful DBSR FIBEN materialization against the best SchemaLens query-plan candidate selected by estimated examined bytes.

The comparison covers FIBEN SF1, SF10, and SF30 for read queries Q1--Q9. Q10 is skipped because it is an insert/update workload and is not explainable through read-style MongoDB execution statistics in this runner.

## Summary

| Scale | Queries | DBSR lower estimated bytes | SchemaLens lower estimated bytes | DBSR lower docs | SchemaLens lower docs | Avg docs ratio DBSR/SchemaLens | Avg keys ratio DBSR/SchemaLens | Avg estimated-bytes ratio DBSR/SchemaLens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SF1 | 9 | 6 | 3 | 6 | 1 | 0.607 | 29.802 | 0.915 |
| SF10 | 9 | 7 | 2 | 6 | 2 | 4.954 | 72.289 | 17.353 |
| SF30 | 9 | 7 | 2 | 6 | 2 | 5.238 | 78.231 | 19.034 |

These query-plan metrics complement, rather than replace, the p95 benchmark comparison. The benchmark remains the primary performance result, while query-plan evidence explains why each method wins or loses.

## Focus cases

### Q3: Securities held in each financial service account

Q3 shows that DBSR suffers from a much larger index traversal, especially at larger scales.

| Scale | SchemaLens best class | SchemaLens docs | DBSR docs | Docs ratio | SchemaLens keys | DBSR keys | Keys ratio | SchemaLens bytes | DBSR bytes | Bytes ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SF1 | G3 | 7 | 5.8 | 0.829 | 11 | 2,746 | 249.636 | 1,798 | 3,604 | 2.004 |
| SF10 | G2 | 41 | 49 | 1.195 | 45 | 27,452 | 610.044 | 10,298 | 14,066 | 1.366 |
| SF30 | G2 | 121 | 145 | 1.198 | 125 | 82,352 | 658.816 | 29,098 | 39,649 | 1.363 |

Although the number of examined documents is close, DBSR examines hundreds of times more keys. This supports the benchmark result: Q3 is not a semantic mismatch, but a less efficient physical access path under the DBSR materialization.

### Q4: Companies reached from person through account, holding, listed security

Q4 is the strongest query-plan explanation for the SchemaLens advantage.

| Scale | SchemaLens best class | SchemaLens docs | DBSR docs | Docs ratio | SchemaLens keys | DBSR keys | Keys ratio | SchemaLens bytes | DBSR bytes | Bytes ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SF1 | G4 | 2,446 | 2,746 | 1.123 | 182 | 2,746 | 15.088 | 1,025,218 | 1,575,727 | 1.537 |
| SF10 | G4 | 672 | 27,451 | 40.850 | 722 | 27,451 | 38.021 | 123,099 | 18,696,798 | 151.884 |
| SF30 | G4 | 1,892 | 82,351 | 43.526 | 1,922 | 82,351 | 42.847 | 339,109 | 56,742,493 | 167.328 |

At SF30, DBSR examines about 43.5 times more documents and 167.3 times more estimated bytes than SchemaLens. This explains why SchemaLens is much faster for Q4: it selects a deep nested document configuration that better matches the traversal pattern.

### Q5: Reports and metric data of company

Q5 is a DBSR-favorable case.

| Scale | SchemaLens best class | SchemaLens docs | DBSR docs | Docs ratio | SchemaLens bytes | DBSR bytes | Bytes ratio |
|---|---|---:|---:|---:|---:|---:|---:|
| SF1 | G4 | 6,718 | 24 | 0.004 | 1,065,417 | 701,160 | 0.658 |
| SF10 | G9 | 6,742 | 24 | 0.004 | 1,067,848 | 806,664 | 0.755 |
| SF30 | G9 | 6,742 | 24 | 0.004 | 1,072,171 | 27,960 | 0.026 |

DBSR uses a direct materialized report path and examines only 24 documents. This explains why DBSR is faster than SchemaLens for Q5 in the benchmark.

### Q6: Tech US listed securities with high last traded value

Q6 is the strongest DBSR-favorable query-plan case.

| Scale | SchemaLens best class | SchemaLens docs | DBSR docs | Docs ratio | SchemaLens bytes | DBSR bytes | Bytes ratio |
|---|---|---:|---:|---:|---:|---:|---:|
| SF1 | G3 | 5,514 | 100 | 0.018 | 1,057,424 | 21,000 | 0.020 |
| SF10 | G3 | 50,073 | 100 | 0.002 | 10,867,290 | 25,100 | 0.002 |
| SF30 | G3 | 149,093 | 100 | 0.001 | 32,616,752 | 25,400 | 0.001 |

DBSR answers the effective benchmark semantics through a capped scan over the listed-security root collection. This produces very low examined-document and estimated-byte counts, explaining the strong DBSR p95 advantage for Q6.

## Interpretation

The query-plan evidence supports a nuanced comparison. DBSR is not uniformly worse: it provides efficient access paths for selected materialized-root cases such as Q5 and Q6. However, SchemaLens is more robust across the workload because it benchmarks multiple activated alternatives and can choose better physical structures for traversal-heavy queries.

The clearest SchemaLens advantage appears in Q4, where the DBSR materialization examines tens of thousands of documents and keys at SF10 and SF30, while SchemaLens uses a deep nested configuration with much lower examined work. Q3 shows a related pattern: returned cardinalities remain aligned, but DBSR pays a much higher key-examination cost.

Overall, query-plan evidence reinforces the benchmark conclusion: DBSR is a faithful and meaningful baseline, but SchemaLens provides stronger workload-aware physical design selection across heterogeneous query patterns and scale factors.
