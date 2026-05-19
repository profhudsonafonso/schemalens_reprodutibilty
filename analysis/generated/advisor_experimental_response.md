# Advisor Experimental Response - Baselines and Ablation

This document summarizes the additional experimental analyses added in response to the advisor comments.

The goal is to move the evaluation from a descriptive workflow demonstration to a deeper analysis of:

1. whether SchemaLens performs better than simple reduction baselines;
2. whether the analytical variables used by SchemaLens actually matter;
3. how to interpret random-k;
4. what evidence should be included later in the paper.

## 1. What was added

| Advisor concern | Action taken |
| --- | --- |
| Evaluation was too descriptive. | Added baseline comparison and ablation study over all datasets. |
| Need simple baselines. | Added random-k, always-reference, always-embed, depth-only, and relationship-type-only. |
| Need to show which analytical variables matter. | Added ablations removing relationship semantics, depth, residual traversal, sharedness, and update volatility. |
| Repository had aggregate outputs only for one dataset. | Added aggregate outputs for IMDb, FIBEN, and LDBC SNB. |
| Need reproducible analysis. | Added scripts under analysis/scripts and generated outputs under analysis/generated. |

## 2. Normalized analysis scope

| Normalized file | Rows | Meaning |
| --- | --- | --- |
| query_analytical_metadata_all_datasets.csv | 42 | One row per query with real methodology variables. |
| query_class_activation_all_datasets.csv | 191 | Normalized G-class activation output. |
| benchmark_configuration_selection_all_datasets.csv | 214 | Links query, configuration, G-class, and benchmark group. |

Query coverage by dataset:

| Dataset | Number of queries |
| --- | --- |
| fiben | 10 |
| imdb | 10 |
| ldbc_snb | 22 |

## 3. Baseline comparison - all runs

| Method | Available cases | Top-1 | Top-3 | Near-best | Mean regret | Median regret | Interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| schema_lens | 252/252 | 0.8730 | 0.9881 | 0.9206 | 0.0394 | 0.0000 | Explainable semantic/workload-aware reduction. |
| random_k | 252/252 | 0.8888 | 0.9956 | 0.9360 | 0.0317 | 0.0000 | Statistical sanity check; not explainable. |
| always_reference | 252/252 | 0.5992 | 0.9167 | 0.7262 | 0.1590 | 0.0000 | Reference-only strategy; misses embedding/hybrid cases. |
| always_embed | 180/252 | 0.5278 | 0.9278 | 0.7278 | 0.1089 | 0.0000 | Embedding-only strategy; misses reference-sensitive cases. |
| depth_only | 180/252 | 0.5444 | 0.8444 | 0.7333 | 0.1277 | 0.0000 | Uses depth only; ignores semantic/update/sharedness signals. |
| relationship_type_only | 234/252 | 0.4829 | 0.7906 | 0.6410 | 0.7463 | 0.0031 | Uses relationship type only; ignores other analytical signals. |

Interpretation:

SchemaLens clearly outperforms the deterministic heuristic baselines. The deterministic baselines lose Top-1 and near-best preservation because they use only one simple rule, such as always referencing, always embedding, using only depth, or using only relationship type.

Random-k is competitive in the aggregate because it samples the same number of measured configuration classes as SchemaLens. Therefore, when the measured space is small or SchemaLens selects several classes, random-k has a high probability of including the global best by chance.

## 4. Baseline comparison - hot runs

| Method | Available hot cases | Top-1 | Near-best | Mean regret | Interpretation |
| --- | --- | --- | --- | --- | --- |
| schema_lens | 126/126 | 0.8651 | 0.9206 | 0.0324 | Explainable semantic/workload-aware reduction. |
| random_k | 126/126 | 0.8884 | 0.9328 | 0.0276 | Statistical sanity check; not explainable. |
| always_reference | 126/126 | 0.6270 | 0.7778 | 0.1075 | Reference-only strategy; misses embedding/hybrid cases. |
| depth_only | 90/126 | 0.5889 | 0.7222 | 0.1106 | Uses depth only; ignores semantic/update/sharedness signals. |
| relationship_type_only | 117/126 | 0.5299 | 0.6667 | 0.8959 | Uses relationship type only; ignores other analytical signals. |
| always_embed | 90/126 | 0.4889 | 0.6444 | 0.1237 | Embedding-only strategy; misses reference-sensitive cases. |

The hot-run table is the best candidate for the paper because the paper mainly interprets hot p95 latency.

## 5. Random-k diagnostic

- Overall, SchemaLens Top-1 = 0.8730, random-k Top-1 = 0.8888.
- Overall, SchemaLens mean regret = 0.0394, random-k expected regret = 0.0317.
- Case-level Top-1 comparison: SchemaLens higher in 70 cases, random-k higher in 32 cases, ties in 150 cases.
- On LDBC SNB, SchemaLens Top-1 = 0.9848, random-k Top-1 = 0.9777; SchemaLens mean regret = 0.0043, random-k expected regret = 0.0070.
- On LDBC SNB hot runs, SchemaLens Top-1 = 0.9848, random-k Top-1 = 0.9775; SchemaLens mean regret = 0.0078, random-k expected regret = 0.0128.

The correct interpretation is not that random selection is a better design method. Random-k is a statistical sanity check: it asks what happens if we select the same number of measured classes without using any semantic explanation.

SchemaLens remains different because it provides an explainable and reproducible reduction based on EER/workload evidence. On the official LDBC SNB workload, SchemaLens also slightly outperforms random-k in Top-1 preservation and regret.

## 6. Ablation study - all runs

| Variant | Available cases | Top-1 | Top-3 | Near-best | Mean regret | Median regret | Interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| full_schema_lens | 252/252 | 0.8730 | 0.9881 | 0.9206 | 0.0394 | 0.0000 | Complete analytical matrix. |
| no_depth | 252/252 | 0.5516 | 0.9841 | 0.7063 | 0.9666 | 0.0000 | Removes depth-sensitive activation evidence. |
| no_relationship_semantics | 234/252 | 0.4615 | 0.8590 | 0.6581 | 1.1203 | 0.0059 | Removes relationship-semantics evidence. |
| no_relationship_semantics_no_depth | 234/252 | 0.4145 | 0.7821 | 0.5940 | 1.1803 | 0.0173 | Removes both semantic and depth evidence. |
| no_residual_traversal | 252/252 | 0.4802 | 0.9802 | 0.6746 | 1.0118 | 0.0042 | Removes Re, DeltaR, and residual traversal evidence. |
| no_sharedness | 252/252 | 0.5675 | 0.9722 | 0.7421 | 0.9647 | 0.0000 | Removes observed sharedness evidence. |
| no_update_volatility | 252/252 | 0.5714 | 0.9484 | 0.7540 | 0.9563 | 0.0000 | Removes update/write-pressure evidence. |

The all-run ablation shows that removing any major analytical component reduces preservation quality and increases regret.

## 7. Ablation study - hot runs

| Variant | Available hot cases | Top-1 | Near-best | Mean regret | Interpretation |
| --- | --- | --- | --- | --- | --- |
| full_schema_lens | 126/126 | 0.8651 | 0.9206 | 0.0324 | Complete analytical matrix. |
| no_depth | 126/126 | 0.5794 | 0.6825 | 0.1435 | Removes depth-sensitive activation evidence. |
| no_relationship_semantics | 117/126 | 0.4786 | 0.6325 | 0.1580 | Removes relationship-semantics evidence. |
| no_relationship_semantics_no_depth | 117/126 | 0.4274 | 0.5641 | 0.1986 | Removes both semantic and depth evidence. |
| no_residual_traversal | 126/126 | 0.4921 | 0.6508 | 0.1573 | Removes Re, DeltaR, and residual traversal evidence. |
| no_sharedness | 126/126 | 0.5317 | 0.6905 | 0.1232 | Removes observed sharedness evidence. |
| no_update_volatility | 126/126 | 0.5397 | 0.6905 | 0.1286 | Removes update/write-pressure evidence. |

The hot-run ablation is especially useful for the paper. The full SchemaLens variant preserves near-best configurations in more than 92% of hot cases, while all ablated variants show lower Top-1 and near-best preservation.

## 8. Dataset-level ablation - hot runs

| Dataset | Variant | Top-1 | Near-best | Mean regret |
| --- | --- | --- | --- | --- |
| fiben | full_schema_lens | 0.8333 | 0.8667 | 0.0801 |
| fiben | no_relationship_semantics | 0.4000 | 0.6667 | 0.1273 |
| fiben | no_relationship_semantics_no_depth | 0.3000 | 0.5000 | 0.1789 |
| fiben | no_residual_traversal | 0.6000 | 0.7333 | 0.1192 |
| imdb | full_schema_lens | 0.6333 | 0.8333 | 0.0387 |
| imdb | no_relationship_semantics | 0.4000 | 0.5667 | 0.1940 |
| imdb | no_relationship_semantics_no_depth | 0.3000 | 0.4667 | 0.3006 |
| imdb | no_residual_traversal | 0.3667 | 0.7000 | 0.0785 |
| ldbc_snb | full_schema_lens | 0.9848 | 0.9848 | 0.0078 |
| ldbc_snb | no_relationship_semantics | 0.5614 | 0.6491 | 0.1552 |
| ldbc_snb | no_relationship_semantics_no_depth | 0.5614 | 0.6491 | 0.1552 |
| ldbc_snb | no_residual_traversal | 0.5000 | 0.5909 | 0.2104 |

The LDBC SNB results are particularly important because this is the official workload. There, the complete SchemaLens variant almost always preserves the best or near-best configuration, while removing analytical components causes a large drop.

## 9. Main conclusions for the advisor

1. SchemaLens is stronger than deterministic heuristic baselines.

The deterministic baselines are weaker because each one uses only a single signal. SchemaLens combines relationship semantics, traversal structure, residual traversal, sharedness, and update volatility.

2. Random-k should be kept, but interpreted carefully.

Random-k is useful as a sanity check, but it is not an explainable design method. It can perform well because it samples the same number of classes as SchemaLens.

3. The ablation study supports the analytical matrix.

Removing relationship semantics, depth, residual traversal, sharedness, or update volatility consistently reduces Top-1 and near-best preservation. The strongest degradation occurs when relationship semantics and depth are removed together.

4. Root-choice ablation should be reported as not executed in this simulation.

The current benchmark artifacts do not include alternative-root MongoDB configurations for all queries. A fair root-choice ablation would require generating and benchmarking additional candidates rooted at non-selected entities.

## 10. Suggested text for the advisor response

> I added two new experimental analyses to address the concern that the evaluation was too descriptive.
>
> First, I added a baseline comparison over the normalized aggregate benchmark outputs. The baselines include random-k, always-reference, always-embed, depth-only, and relationship-type-only strategies. This analysis does not rerun MongoDB benchmarks; it uses the measured p95 values already available in the aggregate outputs. SchemaLens clearly outperforms the deterministic heuristic baselines. Random-k is competitive in the aggregate because it samples the same number of measured configuration classes as SchemaLens, so it has a high probability of including the global best when the measured space is small. However, random-k has no semantic explanation. On the official LDBC SNB workload, SchemaLens slightly outperforms random-k in Top-1 preservation and regret.
>
> Second, I added an ablation study using real methodology variables extracted from the IMDb, FIBEN, and LDBC SNB artifacts. The ablation removes relationship semantics, depth, residual traversal, sharedness, and update volatility from the measured SchemaLens-selected space. The full SchemaLens variant achieves high Top-1 and near-best preservation on hot runs with low mean regret. All ablated variants perform substantially worse. The strongest degradation occurs when relationship semantics and depth are removed together. This supports the claim that the analytical matrix materially contributes to preserving best or near-best configurations.

## 11. Recommended next steps

1. Select which baseline table should go into the paper.
2. Select which ablation table should go into the paper.
3. Add a short paragraph explaining random-k as a statistical sanity check.
4. Add a short paragraph explaining why root-choice ablation requires additional benchmark candidates.
5. Add representative query-level explanations showing why specific configurations win.
6. Decide what stays in the paper and what remains as supplementary repository material.
