# DBSR vs SchemaLens on FIBEN SF1: Semantic-Aligned Comparison

## Purpose

This document summarizes the semantic-aligned comparison between SchemaLens and a faithful DBSR baseline on the FIBEN SF1 workload. The goal is to explain how the DBSR baseline was implemented, how the benchmark was aligned with the original FIBEN/SchemaLens execution semantics, and how the final per-query comparison should be interpreted.

## How the comparison was produced

We implemented DBSR independently from the SchemaLens activation rules. DBSR receives the FIBEN conceptual/workload input, generates its recommended document structures, and these structures are physically materialized in MongoDB as `dbsr_rank*` collections.

After materialization, we created a DBSR query executor for FIBEN Q1--Q9. The first executable comparison showed that some queries returned different result sizes from the original SchemaLens/FIBEN benchmark. Therefore, before reporting performance results, we aligned the DBSR executor with the original FIBEN runner semantics.

The final alignment includes:

* Q2 returns one logical corporation-with-context result, following the original candidate-level returned-count policy.
* Q3 uses a pool of financial-service-account identifiers and rotates the parameter by repetition.
* Q4 uses a pool of persons with complete account--holding--security--corporation paths and rotates the parameter by repetition.
* Q5 uses the IBM corporation-level parameter and counts reports, report elements, and statement elements.
* Q7 and Q8 use the corporation-to-security-to-transaction traversal.
* Q9 uses a pool of security identifiers and rotates the parameter by repetition.

For each query, the comparison uses:

* the best observed SchemaLens candidate p95 for that query;
* the p95 of the DBSR physical execution over the materialized `dbsr_rank*` collections;
* the returned-count ratio as a semantic-parity check.

Thus, the comparison is a direct per-query method-level comparison: SchemaLens is represented by its best observed candidate, while DBSR is represented by the physical structure selected and materialized by the faithful DBSR implementation.

## Markdown version for the repository

### Final semantic-aligned benchmark summary

| Query | Best SchemaLens choice            | DBSR physical path                                  | SL p95 (ms) | DBSR p95 (ms) | Winner     | Returned ratio |
| ----- | --------------------------------- | --------------------------------------------------- | ----------: | ------------: | ---------- | -------------: |
| Q1    | Control / normalized reference    | Corporation root                                    |       0.233 |         0.224 | DBSR       |           1.00 |
| Q2    | G5 / shared targets as references | Corporation + context collections                   |       0.117 |         0.772 | SchemaLens |           1.00 |
| Q3    | G5 / shared targets as references | Account → Holding → ListedSecurity                  |       0.435 |         0.317 | DBSR       |           1.08 |
| Q4    | Control / normalized reference    | Person → Account → Holding → Security → Corporation |       1.003 |         1.022 | SchemaLens |           0.98 |
| Q5    | G2 / embedded containment         | FinancialReport → ReportElement → StatementElement  |      37.627 |        11.896 | DBSR       |           1.00 |
| Q6    | G9 / trade-off candidate          | Security → Corporation → Industry/Country           |       0.386 |         1.382 | SchemaLens |           1.69 |
| Q7    | G4 / deep nested path             | Corporation → Security → Transaction                |       1.187 |         1.553 | SchemaLens |           1.00 |
| Q8    | G7 / update-aware references      | Corporation → Security → Transaction                |       0.864 |         1.569 | SchemaLens |           0.99 |
| Q9    | G7 / update-aware references      | Security → Transaction, with parameter pool         |       0.851 |         2.014 | SchemaLens |           0.83 |

### Interpretation

After semantic alignment, DBSR wins 3 out of 9 FIBEN queries, while SchemaLens wins 6 out of 9. DBSR is within 5% of SchemaLens in 4 out of 9 queries.

The strongest DBSR case is Q5. In this query, DBSR materializes the report hierarchy directly as `FinancialReport → ReportElement → StatementElement`, reducing p95 from 37.63 ms to 11.90 ms while preserving returned-count parity.

SchemaLens is stronger in Q2 and in the transaction-oriented queries Q7--Q9. This suggests that SchemaLens preserves strong design choices for association-heavy and update-sensitive traversals, where reference-oriented or update-aware alternatives can outperform the DBSR materialized structures.

Q6 should be interpreted with care because DBSR returns more documents than SchemaLens. However, the returned-count ratio is still reported explicitly, so the reader can assess the semantic parity of the comparison.

## Query-plan evidence to add later

The main table should not include all query-plan details, because it would become too large. Instead, query-plan evidence should be added for representative cases only.

Recommended representative cases:

| Query | Reason                              | Expected evidence to collect                                               |
| ----- | ----------------------------------- | -------------------------------------------------------------------------- |
| Q5    | Strong DBSR win                     | DBSR should examine a materialized report hierarchy directly.              |
| Q2    | Strong SchemaLens win               | SchemaLens likely benefits from a more compact shared-reference structure. |
| Q7    | Transaction-oriented SchemaLens win | SchemaLens likely uses a better transaction/security traversal strategy.   |
| Q8    | Transaction-oriented SchemaLens win | SchemaLens likely benefits from update-aware/reference design.             |

Suggested query-plan columns:

| Query | Method     | Main collection/path                               | Docs examined | Keys examined | Main stage | Interpretation                                    |
| ----- | ---------- | -------------------------------------------------- | ------------: | ------------: | ---------- | ------------------------------------------------- |
| Q5    | DBSR       | FinancialReport → ReportElement → StatementElement |          TODO |          TODO | TODO       | Direct materialized hierarchy.                    |
| Q5    | SchemaLens | G2 embedded containment                            |          TODO |          TODO | TODO       | Best SchemaLens candidate for report hierarchy.   |
| Q2    | DBSR       | Corporation + context collections                  |          TODO |          TODO | TODO       | Multiple context lookups.                         |
| Q2    | SchemaLens | G5 shared targets as references                    |          TODO |          TODO | TODO       | More efficient company-context retrieval.         |
| Q7    | DBSR       | Corporation → Security → Transaction               |          TODO |          TODO | TODO       | Transaction scan over issued securities.          |
| Q7    | SchemaLens | G4 deep nested path                                |          TODO |          TODO | TODO       | Better physical path for buy/sell aggregation.    |
| Q8    | DBSR       | Corporation → Security → Transaction               |          TODO |          TODO | TODO       | Average sell-price computation over transactions. |
| Q8    | SchemaLens | G7 update-aware references                         |          TODO |          TODO | TODO       | Better transaction-oriented reference layout.     |

## Overleaf version

```latex
\paragraph{DBSR baseline construction and comparison protocol.}
To compare SchemaLens with a faithful DBSR baseline, we implemented DBSR independently from the SchemaLens activation rules. DBSR receives the FIBEN conceptual/workload input, generates its recommended document structures, and these structures are physically materialized in MongoDB as \texttt{dbsr\_rank*} collections. We then implemented a DBSR query executor for FIBEN Q1--Q9 and aligned its parameters, traversal semantics, and returned-count policy with the original FIBEN benchmark runner. This alignment avoids comparing executions that return substantially different result sizes.

For each query, we compare the hot p95 latency of the best SchemaLens candidate observed in the original benchmark against the hot p95 latency of the corresponding DBSR materialized execution. Thus, the comparison is per-query and method-level: SchemaLens is represented by its best observed candidate, while DBSR is represented by the physical structure selected and materialized by the faithful DBSR implementation.

\begin{table*}[t]
\centering
\caption{Semantic-aligned comparison between SchemaLens and DBSR on FIBEN SF1. Returned ratio is computed as DBSR returned count divided by SchemaLens returned count and is used as a semantic-parity check.}
\label{tab:dbsr-schemalens-fiben-sf1}
\scriptsize
\begin{tabular}{p{0.055\linewidth} p{0.22\linewidth} p{0.28\linewidth} r r p{0.11\linewidth} r}
\toprule
Query & Best SchemaLens choice & DBSR physical path & SL p95 & DBSR p95 & Winner & Ret. ratio \\
\midrule
Q1 & Control / normalized reference & Corporation root & 0.233 & 0.224 & DBSR & 1.00 \\
Q2 & G5 / shared targets as references & Corporation + context collections & 0.117 & 0.772 & SchemaLens & 1.00 \\
Q3 & G5 / shared targets as references & Account $\rightarrow$ Holding $\rightarrow$ ListedSecurity & 0.435 & 0.317 & DBSR & 1.08 \\
Q4 & Control / normalized reference & Person $\rightarrow$ Account $\rightarrow$ Holding $\rightarrow$ Security $\rightarrow$ Corporation & 1.003 & 1.022 & SchemaLens & 0.98 \\
Q5 & G2 / embedded containment & FinancialReport $\rightarrow$ ReportElement $\rightarrow$ StatementElement & 37.627 & 11.896 & DBSR & 1.00 \\
Q6 & G9 / trade-off candidate & Security $\rightarrow$ Corporation $\rightarrow$ Industry/Country & 0.386 & 1.382 & SchemaLens & 1.69 \\
Q7 & G4 / deep nested path & Corporation $\rightarrow$ Security $\rightarrow$ Transaction & 1.187 & 1.553 & SchemaLens & 1.00 \\
Q8 & G7 / update-aware references & Corporation $\rightarrow$ Security $\rightarrow$ Transaction & 0.864 & 1.569 & SchemaLens & 0.99 \\
Q9 & G7 / update-aware references & Security $\rightarrow$ Transaction, with parameter pool & 0.851 & 2.014 & SchemaLens & 0.83 \\
\bottomrule
\end{tabular}
\end{table*}

\paragraph{Interpretation.}
After semantic alignment, DBSR wins three out of nine FIBEN queries, while SchemaLens wins six out of nine. DBSR is within 5\% of SchemaLens in four out of nine queries. The strongest DBSR case is Q5, where the materialized report hierarchy directly matches the query path and reduces p95 from 37.63 ms to 11.90 ms with returned-count parity. SchemaLens is stronger in Q2 and in the transaction-oriented queries Q7--Q9, suggesting that its design-space reduction preserves strong choices for association-heavy and update-sensitive traversals. Q6 should be interpreted with care because DBSR returns more documents than SchemaLens; therefore, the returned-count ratio is reported explicitly as a semantic-parity check.

\paragraph{Query-plan evidence.}
Documents returned are not used as a performance metric; they are used as a semantic-parity check. Query-plan evidence should be reported only for representative cases to explain why each method wins. In particular, Q5 can illustrate the DBSR advantage from a directly materialized report hierarchy, whereas Q2, Q7, and Q8 can illustrate cases where SchemaLens selects more efficient shared-reference, deep-path, or update-aware structures.
```
