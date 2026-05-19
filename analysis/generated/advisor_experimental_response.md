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

## 10. Resume

> I added two new experimental analyses to address the concern that the evaluation was too descriptive.
>
> First, I added a baseline comparison over the normalized aggregate benchmark outputs. The baselines include random-k, always-reference, always-embed, depth-only, and relationship-type-only strategies. This analysis does not rerun MongoDB benchmarks; it uses the measured p95 values already available in the aggregate outputs. SchemaLens clearly outperforms the deterministic heuristic baselines. Random-k is competitive in the aggregate because it samples the same number of measured configuration classes as SchemaLens, so it has a high probability of including the global best when the measured space is small. However, random-k has no semantic explanation. On the official LDBC SNB workload, SchemaLens slightly outperforms random-k in Top-1 preservation and regret.
>
> Second, I added an ablation study using real methodology variables extracted from the IMDb, FIBEN, and LDBC SNB artifacts. The ablation removes relationship semantics, depth, residual traversal, sharedness, and update volatility from the measured SchemaLens-selected space. The full SchemaLens variant achieves high Top-1 and near-best preservation on hot runs with low mean regret. All ablated variants perform substantially worse. The strongest degradation occurs when relationship semantics and depth are removed together. This supports the claim that the analytical matrix materially contributes to preserving best or near-best configurations.

## 11. Next steps

1. Select which baseline table should go into the paper.
2. Select which ablation table should go into the paper.
3. Add a short paragraph explaining random-k as a statistical sanity check.
4. Add a short paragraph explaining why root-choice ablation requires additional benchmark candidates.
5. Add representative query-level explanations showing why specific configurations win.
6. Decide what stays in the paper and what remains as supplementary repository material.






## Representative-case analysis

I added a representative-case analysis to connect the analytical variables used by SchemaLens with the measured benchmark winners. The goal is to move the experimental section beyond aggregate preservation metrics and explain why particular configuration families win under specific workload and data characteristics.

The analysis uses only measured hot-run p95 results. No MongoDB benchmark is rerun, no latency is inferred for unmeasured configurations, and root-choice ablation is not included because it would require materializing and benchmarking alternative-root candidates.

### Representative cases and interpretation

| Dataset | Query | Pattern / key signal | Hot-run winner(s) across scales | Preservation | Interpretation |
|---|---|---|---|---|---|
| imdb | `QG6_EpisodesOfSeries` | containment / low-sharedness traversal; root=Series; Rc=1.0; D=1.0; Re=0.0; DeltaRratio=1.0; semantic=none | sf0.25: G2 (control, 0.6322 ms); sf0.5: G7 (primary, 1.016 ms); sf1: G7 (primary, 2.272 ms) | Top-1 2/3; near-best 2/3 | This is the canonical IMDb containment case. It fails at sf0.25, where a simple control candidate wins, but the expected containment family wins at sf0.5 and sf1. |
| imdb | `QG10_AdvancedSearchWatchItems` | association / sharedness / filtered search; root=WatchItem; Rc=4.0; D=1.0; Re=0.0; DeltaRratio=1.0; semantic=none | sf0.25: G9 (secondary_affected, 115.3 ms); sf0.5: G7 (secondary_affected, 171.6 ms); sf1: G9 (secondary_affected, 299.8 ms) | Top-1 3/3; near-best 3/3 | This is the IMDb sharedness/filtering case. Use it after checking the activation-vs-selection distinction, because the winners are secondary/hybrid candidates that may be selected beyond the raw activation-matrix classes. |
| fiben | `Q10_CreateAccountHoldingAndBuyTransaction` | update + relationship creation; root=Person; Rc=5.0; D=3.0; Re=0.0; DeltaRratio=1.0; semantic=mixed | sf1: G9 (secondary_affected, 0.5756 ms); sf10: G3 (primary, 0.4271 ms); sf30: G7 (secondary_affected, 0.619 ms) | Top-1 3/3; near-best 3/3 | This is the best FIBEN case for update volatility. The query creates relationships under high update pressure, so the winner changes across scales rather than always favoring embedding. |
| fiben | `Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity` | deep traversal; root=Person; Rc=4.0; D=4.0; Re=0.0; DeltaRratio=1.0; semantic=mixed | sf1: CONTROL (control, 1.003 ms); sf10: G5 (primary, 4.308 ms); sf30: G4 (primary, 17.14 ms) | Top-1 2/3; near-best 2/3 | This is the main scale-sensitive FIBEN case. CONTROL wins at sf1, but activated designs win at larger scales, suggesting that the benefit of the activated space becomes clearer as traversal cost grows. |
| ldbc_snb | `IC1_TransitiveFriendsWithName` | official complex read / transitive association; root=Person; Rc=7.0; D=4.0; Re=3.0; DeltaRratio=0.5714285714; semantic=association | sf0.1: G3 (primary, 131.4 ms); sf1: G3 (primary, 227.7 ms); sf3: G3 (primary, 260 ms) | Top-1 3/3; near-best 3/3 | This is a strong official workload case. High traversal depth and residual traversal over associative relationships explain why a reference/summary-oriented Person-rooted configuration remains competitive instead of full embedding. |
| ldbc_snb | `IC5_NewGroups` | official complex read / association + containment mix; root=Person; Rc=5.0; D=3.0; Re=2.0; DeltaRratio=0.6000000000000001; semantic=association | sf0.1: G7 (secondary_affected, 135.3 ms); sf1: G6 (secondary_affected, 176.8 ms); sf3: G7 (secondary_affected, 193.8 ms) | Top-1 3/3; near-best 3/3 | This case is useful to justify secondary_affected candidates. The winners are secondary families across scales, showing that mixed association/containment workloads require more than only the primary family. |
| ldbc_snb | `IC7_RecentLikers` | official complex read / likes and friend check; root=Person; Rc=5.0; D=2.0; Re=3.0; DeltaRratio=0.4; semantic=association | sf0.1: G4 (secondary_affected, 7.464 ms); sf1: G3 (primary, 7.009 ms); sf3: G4 (secondary_affected, 8.037 ms) | Top-1 3/3; near-best 3/3 | This query combines likes, message ownership, and friendship checks. The alternation between G4 and G3 shows that explicit associative-edge and reference-aware designs are both relevant under graph-like access. |
| ldbc_snb | `IS2_RecentMessagesOfPerson` | official short read / messages of person; root=Person; Rc=4.0; D=2.0; Re=2.0; DeltaRratio=0.5; semantic=mixed | sf0.1: G6 (secondary_affected, 2.256 ms); sf1: G9 (secondary_affected, 3.231 ms); sf3: G0 (secondary_affected, 2.711 ms) | Top-1 3/3; near-best 3/3 | This short-read case is compact but still has mixed message structures and residual traversal. It supports the need to preserve several secondary alternatives instead of choosing a single fixed document pattern. |
| ldbc_snb | `IS6_ForumOfMessage` | official short read / containment path; root=Post; Rc=4.0; D=3.0; Re=1.0; DeltaRratio=0.75; semantic=containment | sf0.1: G9 (primary, 1.171 ms); sf1: G9 (primary, 2.301 ms); sf3: G0 (secondary_affected, 1.332 ms) | Top-1 3/3; near-best 3/3 | This is a good containment/hybrid example. Even though the path is containment-like, residual traversal remains, explaining why hybrid or reference-aware candidates can win. |
| ldbc_snb | `IS7_RepliesOfMessage` | official short read / replies and author relation; root=Post; Rc=5.0; D=2.0; Re=3.0; DeltaRratio=0.4; semantic=association | sf0.1: G0 (primary, 7.944 ms); sf1: G9 (secondary_affected, 11.01 ms); sf3: G7 (secondary_affected, 14.04 ms) | Top-1 3/3; near-best 3/3 | This short-read case mixes replies, authors, and author relationships. It is useful for showing that update-aware and hybrid candidates can matter even in compact access patterns. |

### Failure and near-failure cases

| Dataset | Query | Scale | Winner | Best SchemaLens candidate / regret | Interpretation |
|---|---|---|---|---|---|
| imdb | `QG6_EpisodesOfSeries` | sf0.25 | G2 (control, p95=0.6322362009086646) | G7; regret=0.4536 | Small-scale containment failure: a simple control/primary-style candidate wins at sf0.25, but the containment family wins at larger scales. |
| fiben | `Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity` | sf1 | CONTROL (control, p95=1.0028332064393908) | G4; regret=0.1807 | Scale-sensitive deep-traversal failure: CONTROL wins at sf1, while activated configurations win at sf10 and sf30. |

### Main takeaways

1. The representative cases show that SchemaLens does not simply choose embedding or references by default. Different workload/data characteristics lead to different winning families.
2. LDBC SNB provides the strongest evidence because it is an official workload and the selected cases consistently preserve Top-1 or near-best configurations.
3. Secondary_affected candidates are important: several winners come from this group, especially in mixed association/containment cases.
4. The failure cases are informative rather than fatal: IMDb QG6 at sf0.25 and FIBEN Q4 at sf1 are small-scale or scale-sensitive misses, while larger scales preserve the activated winners.
5. For the final paper text, activation-matrix classes and final SchemaLens benchmark-selected classes should be reported separately to avoid ambiguity.
