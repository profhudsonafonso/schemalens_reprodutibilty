# Representative Case Analysis

This report explains selected representative cases using measured aggregate benchmark results and normalized SchemaLens methodology variables.

## Scope

- Run phase: `hot`
- Scale mode: `all`
- Near-best threshold: `0.05`
- No MongoDB benchmark is rerun.
- No latency is inferred for unmeasured configurations.
- Root-choice ablation is not included because it would require materializing and benchmarking alternative-root candidates.

## Compact table

| dataset | query_name | scale_label | case_focus | selected_root | Rc | D | Re | DeltaRratio | dominant_semantic_type | global_best_g_class | global_best_benchmark_group | global_best_p95_ms | schema_lens_top1_preserved | schema_lens_near_best_preserved | schema_lens_relative_regret |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| imdb | QG6_EpisodesOfSeries | sf0.25 | containment / low-sharedness traversal | Series | 1.0000 | 1.0000 | 0.0000 | 1.0000 | none | G2 | control | 0.6322 | 0 | 0 | 0.4536 |
| imdb | QG6_EpisodesOfSeries | sf0.5 | containment / low-sharedness traversal | Series | 1.0000 | 1.0000 | 0.0000 | 1.0000 | none | G7 | primary | 1.0162 | 1 | 1 | 0.0000 |
| imdb | QG6_EpisodesOfSeries | sf1 | containment / low-sharedness traversal | Series | 1.0000 | 1.0000 | 0.0000 | 1.0000 | none | G7 | primary | 2.2719 | 1 | 1 | 0.0000 |
| imdb | QG10_AdvancedSearchWatchItems | sf0.25 | association / sharedness / filtered search | WatchItem | 4.0000 | 1.0000 | 0.0000 | 1.0000 | none | G9 | secondary_affected | 115.3121 | 1 | 1 | 0.0000 |
| imdb | QG10_AdvancedSearchWatchItems | sf0.5 | association / sharedness / filtered search | WatchItem | 4.0000 | 1.0000 | 0.0000 | 1.0000 | none | G7 | secondary_affected | 171.6414 | 1 | 1 | 0.0000 |
| imdb | QG10_AdvancedSearchWatchItems | sf1 | association / sharedness / filtered search | WatchItem | 4.0000 | 1.0000 | 0.0000 | 1.0000 | none | G9 | secondary_affected | 299.8020 | 1 | 1 | 0.0000 |
| fiben | Q10_CreateAccountHoldingAndBuyTransaction | sf1 | update + relationship creation | Person | 5.0000 | 3.0000 | 0.0000 | 1.0000 | mixed | G9 | secondary_affected | 0.5756 | 1 | 1 | 0.0000 |
| fiben | Q10_CreateAccountHoldingAndBuyTransaction | sf10 | update + relationship creation | Person | 5.0000 | 3.0000 | 0.0000 | 1.0000 | mixed | G3 | primary | 0.4271 | 1 | 1 | 0.0000 |
| fiben | Q10_CreateAccountHoldingAndBuyTransaction | sf30 | update + relationship creation | Person | 5.0000 | 3.0000 | 0.0000 | 1.0000 | mixed | G7 | secondary_affected | 0.6190 | 1 | 1 | 0.0000 |
| fiben | Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity | sf1 | deep traversal | Person | 4.0000 | 4.0000 | 0.0000 | 1.0000 | mixed | CONTROL | control | 1.0028 | 0 | 0 | 0.1807 |
| fiben | Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity | sf10 | deep traversal | Person | 4.0000 | 4.0000 | 0.0000 | 1.0000 | mixed | G5 | primary | 4.3084 | 1 | 1 | 0.0000 |
| fiben | Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity | sf30 | deep traversal | Person | 4.0000 | 4.0000 | 0.0000 | 1.0000 | mixed | G4 | primary | 17.1424 | 1 | 1 | 0.0000 |
| ldbc_snb | IC1_TransitiveFriendsWithName | sf0.1 | official complex read / transitive association | Person | 7.0000 | 4.0000 | 3.0000 | 0.5714 | association | G3 | primary | 131.3617 | 1 | 1 | 0.0000 |
| ldbc_snb | IC1_TransitiveFriendsWithName | sf1 | official complex read / transitive association | Person | 7.0000 | 4.0000 | 3.0000 | 0.5714 | association | G3 | primary | 227.7275 | 1 | 1 | 0.0000 |
| ldbc_snb | IC1_TransitiveFriendsWithName | sf3 | official complex read / transitive association | Person | 7.0000 | 4.0000 | 3.0000 | 0.5714 | association | G3 | primary | 260.0222 | 1 | 1 | 0.0000 |
| ldbc_snb | IC5_NewGroups | sf0.1 | official complex read / association + containment mix | Person | 5.0000 | 3.0000 | 2.0000 | 0.6000 | association | G7 | secondary_affected | 135.3230 | 1 | 1 | 0.0000 |
| ldbc_snb | IC5_NewGroups | sf1 | official complex read / association + containment mix | Person | 5.0000 | 3.0000 | 2.0000 | 0.6000 | association | G6 | secondary_affected | 176.7536 | 1 | 1 | 0.0000 |
| ldbc_snb | IC5_NewGroups | sf3 | official complex read / association + containment mix | Person | 5.0000 | 3.0000 | 2.0000 | 0.6000 | association | G7 | secondary_affected | 193.8014 | 1 | 1 | 0.0000 |
| ldbc_snb | IC7_RecentLikers | sf0.1 | official complex read / likes and friend check | Person | 5.0000 | 2.0000 | 3.0000 | 0.4000 | association | G4 | secondary_affected | 7.4644 | 1 | 1 | 0.0000 |
| ldbc_snb | IC7_RecentLikers | sf1 | official complex read / likes and friend check | Person | 5.0000 | 2.0000 | 3.0000 | 0.4000 | association | G3 | primary | 7.0093 | 1 | 1 | 0.0000 |
| ldbc_snb | IC7_RecentLikers | sf3 | official complex read / likes and friend check | Person | 5.0000 | 2.0000 | 3.0000 | 0.4000 | association | G4 | secondary_affected | 8.0368 | 1 | 1 | 0.0000 |
| ldbc_snb | IS2_RecentMessagesOfPerson | sf0.1 | official short read / messages of person | Person | 4.0000 | 2.0000 | 2.0000 | 0.5000 | mixed | G6 | secondary_affected | 2.2558 | 1 | 1 | 0.0000 |
| ldbc_snb | IS2_RecentMessagesOfPerson | sf1 | official short read / messages of person | Person | 4.0000 | 2.0000 | 2.0000 | 0.5000 | mixed | G9 | secondary_affected | 3.2309 | 1 | 1 | 0.0000 |
| ldbc_snb | IS2_RecentMessagesOfPerson | sf3 | official short read / messages of person | Person | 4.0000 | 2.0000 | 2.0000 | 0.5000 | mixed | G0 | secondary_affected | 2.7113 | 1 | 1 | 0.0000 |
| ldbc_snb | IS6_ForumOfMessage | sf0.1 | official short read / containment path | Post | 4.0000 | 3.0000 | 1.0000 | 0.7500 | containment | G9 | primary | 1.1708 | 1 | 1 | 0.0000 |
| ldbc_snb | IS6_ForumOfMessage | sf1 | official short read / containment path | Post | 4.0000 | 3.0000 | 1.0000 | 0.7500 | containment | G9 | primary | 2.3013 | 1 | 1 | 0.0000 |
| ldbc_snb | IS6_ForumOfMessage | sf3 | official short read / containment path | Post | 4.0000 | 3.0000 | 1.0000 | 0.7500 | containment | G0 | secondary_affected | 1.3324 | 1 | 1 | 0.0000 |
| ldbc_snb | IS7_RepliesOfMessage | sf0.1 | official short read / replies and author relation | Post | 5.0000 | 2.0000 | 3.0000 | 0.4000 | association | G0 | primary | 7.9440 | 1 | 1 | 0.0000 |
| ldbc_snb | IS7_RepliesOfMessage | sf1 | official short read / replies and author relation | Post | 5.0000 | 2.0000 | 3.0000 | 0.4000 | association | G9 | secondary_affected | 11.0091 | 1 | 1 | 0.0000 |
| ldbc_snb | IS7_RepliesOfMessage | sf3 | official short read / replies and author relation | Post | 5.0000 | 2.0000 | 3.0000 | 0.4000 | association | G7 | secondary_affected | 14.0368 | 1 | 1 | 0.0000 |

## Case-by-case interpretation

### fiben / Q10_CreateAccountHoldingAndBuyTransaction / sf1 / hot

**Focus.** update + relationship creation

**Why selected.** Write-oriented FIBEN case with relationship creation and high update pressure. It helps show that SchemaLens does not blindly prefer embedding for every traversal.

**Analytical variables.** 
Root=Person; Rc=5.00; D=3.00; Re=0.00; DeltaRratio=1.00; semantic=mixed; update=high; sharedness=medium.

**Activated classes.** G2|G3|G4|G5|G7|G9

**Measured classes.** CONTROL|G2|G3|G4|G5|G7|G9 (7 measured candidates in the benchmark-selection table).

**Measured winner.** G9 (Benchmark-required trade-off candidate) from `secondary_affected`; p95=0.5756 ms.

**Best SchemaLens-selected candidate.** G9 (Benchmark-required trade-off candidate); p95=0.5756 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G2|G4; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G2|G3|G5; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G2|G3|G4|G5; no_residual_traversal: top1=0.0, near=0.0, regret=0.1134, removed=G4|G9; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=G5; no_update_volatility: top1=1.0, near=1.0, regret=0.0000, removed=G7

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `mixed` with Rc=5.00, D=3.00, Re=0.00, and DeltaRratio=1.00. The depth signal is important because the workload traverses several conceptual hops; removing depth from the activation logic should therefore make the selected space less reliable. The high DeltaRratio indicates that the selected candidate can absorb most of the conceptual traversal, which supports testing embedded or containment-oriented alternatives. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The sharedness signal warns against interpreting embedding as automatically best, because highly shared entities can create duplication and maintenance pressure. The measured hot-run winner is G9 (Benchmark-required trade-off candidate) from the `secondary_affected` group, with p95=0.5756 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G9 (Benchmark-required trade-off candidate), with p95=0.5756 ms.

### fiben / Q10_CreateAccountHoldingAndBuyTransaction / sf10 / hot

**Focus.** update + relationship creation

**Why selected.** Write-oriented FIBEN case with relationship creation and high update pressure. It helps show that SchemaLens does not blindly prefer embedding for every traversal.

**Analytical variables.** 
Root=Person; Rc=5.00; D=3.00; Re=0.00; DeltaRratio=1.00; semantic=mixed; update=high; sharedness=medium.

**Activated classes.** G2|G3|G4|G5|G7|G9

**Measured classes.** CONTROL|G2|G3|G4|G5|G7|G9 (7 measured candidates in the benchmark-selection table).

**Measured winner.** G3 (Root with associated references) from `primary`; p95=0.4271 ms.

**Best SchemaLens-selected candidate.** G3 (Root with associated references); p95=0.4271 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G2|G4; no_relationship_semantics: top1=0.0, near=0.0, regret=0.1573, removed=G2|G3|G5; no_relationship_semantics_no_depth: top1=0.0, near=0.0, regret=0.8705, removed=G2|G3|G4|G5; no_residual_traversal: top1=1.0, near=1.0, regret=0.0000, removed=G4|G9; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=G5; no_update_volatility: top1=1.0, near=1.0, regret=0.0000, removed=G7

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `mixed` with Rc=5.00, D=3.00, Re=0.00, and DeltaRratio=1.00. The depth signal is important because the workload traverses several conceptual hops; removing depth from the activation logic should therefore make the selected space less reliable. The high DeltaRratio indicates that the selected candidate can absorb most of the conceptual traversal, which supports testing embedded or containment-oriented alternatives. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The sharedness signal warns against interpreting embedding as automatically best, because highly shared entities can create duplication and maintenance pressure. The measured hot-run winner is G3 (Root with associated references) from the `primary` group, with p95=0.4271 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G3 (Root with associated references), with p95=0.4271 ms.

### fiben / Q10_CreateAccountHoldingAndBuyTransaction / sf30 / hot

**Focus.** update + relationship creation

**Why selected.** Write-oriented FIBEN case with relationship creation and high update pressure. It helps show that SchemaLens does not blindly prefer embedding for every traversal.

**Analytical variables.** 
Root=Person; Rc=5.00; D=3.00; Re=0.00; DeltaRratio=1.00; semantic=mixed; update=high; sharedness=medium.

**Activated classes.** G2|G3|G4|G5|G7|G9

**Measured classes.** CONTROL|G2|G3|G4|G5|G7|G9 (7 measured candidates in the benchmark-selection table).

**Measured winner.** G7 (Update-aware document strategy) from `secondary_affected`; p95=0.6190 ms.

**Best SchemaLens-selected candidate.** G7 (Update-aware document strategy); p95=0.6190 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G2|G4; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G2|G3|G5; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G2|G3|G4|G5; no_residual_traversal: top1=1.0, near=1.0, regret=0.0000, removed=G4|G9; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=G5; no_update_volatility: top1=0.0, near=1.0, regret=0.0030, removed=G7

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `mixed` with Rc=5.00, D=3.00, Re=0.00, and DeltaRratio=1.00. The depth signal is important because the workload traverses several conceptual hops; removing depth from the activation logic should therefore make the selected space less reliable. The high DeltaRratio indicates that the selected candidate can absorb most of the conceptual traversal, which supports testing embedded or containment-oriented alternatives. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The sharedness signal warns against interpreting embedding as automatically best, because highly shared entities can create duplication and maintenance pressure. The measured hot-run winner is G7 (Update-aware document strategy) from the `secondary_affected` group, with p95=0.6190 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G7 (Update-aware document strategy), with p95=0.6190 ms.

### fiben / Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity / sf1 / hot

**Focus.** deep traversal

**Why selected.** Deep FIBEN traversal from Person through account, holding, security, and company. It is useful for explaining the role of depth and residual traversal.

**Analytical variables.** 
Root=Person; Rc=4.00; D=4.00; Re=0.00; DeltaRratio=1.00; semantic=mixed; update=high; sharedness=medium.

**Activated classes.** G2|G3|G4|G5|G7|G9

**Measured classes.** CONTROL|G2|G3|G4|G5|G7|G9 (7 measured candidates in the benchmark-selection table).

**Measured winner.** CONTROL () from `control`; p95=1.0028 ms.

**Best SchemaLens-selected candidate.** G4 (Deep nested traversal document); p95=1.1841 ms; Top-1 preserved=0; near-best preserved=0; relative regret=0.1807.

**Ablation signal.** no_depth: top1=0.0, near=0.0, regret=0.2647, removed=G2|G4; no_relationship_semantics: top1=0.0, near=0.0, regret=0.1807, removed=G2|G3|G5; no_relationship_semantics_no_depth: top1=0.0, near=0.0, regret=0.3343, removed=G2|G3|G4|G5; no_residual_traversal: top1=0.0, near=0.0, regret=0.2647, removed=G4|G9; no_sharedness: top1=0.0, near=0.0, regret=0.1807, removed=G5; no_update_volatility: top1=0.0, near=0.0, regret=0.1807, removed=G7

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `mixed` with Rc=4.00, D=4.00, Re=0.00, and DeltaRratio=1.00. The depth signal is important because the workload traverses several conceptual hops; removing depth from the activation logic should therefore make the selected space less reliable. The high DeltaRratio indicates that the selected candidate can absorb most of the conceptual traversal, which supports testing embedded or containment-oriented alternatives. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The sharedness signal warns against interpreting embedding as automatically best, because highly shared entities can create duplication and maintenance pressure. The measured hot-run winner is CONTROL () from the `control` group, with p95=1.0028 ms. SchemaLens missed the Top-1 and the near-best region for this scale/phase; this should be treated as a failure or near-failure case with relative regret 0.1807. The best SchemaLens-selected configuration was G4 (Deep nested traversal document), with p95=1.1841 ms.

### fiben / Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity / sf10 / hot

**Focus.** deep traversal

**Why selected.** Deep FIBEN traversal from Person through account, holding, security, and company. It is useful for explaining the role of depth and residual traversal.

**Analytical variables.** 
Root=Person; Rc=4.00; D=4.00; Re=0.00; DeltaRratio=1.00; semantic=mixed; update=high; sharedness=medium.

**Activated classes.** G2|G3|G4|G5|G7|G9

**Measured classes.** CONTROL|G2|G3|G4|G5|G7|G9 (7 measured candidates in the benchmark-selection table).

**Measured winner.** G5 (Shared target reference strategy) from `primary`; p95=4.3084 ms.

**Best SchemaLens-selected candidate.** G5 (Shared target reference strategy); p95=4.3084 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G2|G4; no_relationship_semantics: top1=0.0, near=1.0, regret=0.0462, removed=G2|G3|G5; no_relationship_semantics_no_depth: top1=0.0, near=0.0, regret=0.2496, removed=G2|G3|G4|G5; no_residual_traversal: top1=1.0, near=1.0, regret=0.0000, removed=G4|G9; no_sharedness: top1=0.0, near=1.0, regret=0.0462, removed=G5; no_update_volatility: top1=1.0, near=1.0, regret=0.0000, removed=G7

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `mixed` with Rc=4.00, D=4.00, Re=0.00, and DeltaRratio=1.00. The depth signal is important because the workload traverses several conceptual hops; removing depth from the activation logic should therefore make the selected space less reliable. The high DeltaRratio indicates that the selected candidate can absorb most of the conceptual traversal, which supports testing embedded or containment-oriented alternatives. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The sharedness signal warns against interpreting embedding as automatically best, because highly shared entities can create duplication and maintenance pressure. The measured hot-run winner is G5 (Shared target reference strategy) from the `primary` group, with p95=4.3084 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G5 (Shared target reference strategy), with p95=4.3084 ms.

### fiben / Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity / sf30 / hot

**Focus.** deep traversal

**Why selected.** Deep FIBEN traversal from Person through account, holding, security, and company. It is useful for explaining the role of depth and residual traversal.

**Analytical variables.** 
Root=Person; Rc=4.00; D=4.00; Re=0.00; DeltaRratio=1.00; semantic=mixed; update=high; sharedness=medium.

**Activated classes.** G2|G3|G4|G5|G7|G9

**Measured classes.** CONTROL|G2|G3|G4|G5|G7|G9 (7 measured candidates in the benchmark-selection table).

**Measured winner.** G4 (Deep nested traversal document) from `primary`; p95=17.1424 ms.

**Best SchemaLens-selected candidate.** G4 (Deep nested traversal document); p95=17.1424 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=0.0, near=1.0, regret=0.0147, removed=G2|G4; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G2|G3|G5; no_relationship_semantics_no_depth: top1=0.0, near=0.0, regret=0.0636, removed=G2|G3|G4|G5; no_residual_traversal: top1=0.0, near=1.0, regret=0.0147, removed=G4|G9; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=G5; no_update_volatility: top1=1.0, near=1.0, regret=0.0000, removed=G7

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `mixed` with Rc=4.00, D=4.00, Re=0.00, and DeltaRratio=1.00. The depth signal is important because the workload traverses several conceptual hops; removing depth from the activation logic should therefore make the selected space less reliable. The high DeltaRratio indicates that the selected candidate can absorb most of the conceptual traversal, which supports testing embedded or containment-oriented alternatives. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The sharedness signal warns against interpreting embedding as automatically best, because highly shared entities can create duplication and maintenance pressure. The measured hot-run winner is G4 (Deep nested traversal document) from the `primary` group, with p95=17.1424 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G4 (Deep nested traversal document), with p95=17.1424 ms.

### imdb / QG10_AdvancedSearchWatchItems / sf0.25 / hot

**Focus.** association / sharedness / filtered search

**Why selected.** IMDb query with high sharedness and filter pressure over WatchItem-related structures. It helps explain why SchemaLens must consider trade-offs beyond simple containment.

**Analytical variables.** 
Root=WatchItem; Rc=4.00; D=1.00; Re=0.00; DeltaRratio=1.00; semantic=none; update=Low volatility exposure; sharedness=High sharedness.

**Activated classes.** G0|G2|G3

**Measured classes.** G0|G2|G3|G4|G5|G6|G7|G8|G9 (9 measured candidates in the benchmark-selection table).

**Measured winner.** G9 (hybrid_containment) from `secondary_affected`; p95=115.3121 ms.

**Best SchemaLens-selected candidate.** G9 (hybrid_containment); p95=115.3121 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G4|G8; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G2|G3|G5|G6|G8; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G2|G3|G4|G5|G6|G8; no_residual_traversal: top1=0.0, near=1.0, regret=0.0227, removed=G4|G8|G9; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=G5|G6; no_update_volatility: top1=1.0, near=1.0, regret=0.0000, removed=G7

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at WatchItem and has semantic profile `none` with Rc=4.00, D=1.00, Re=0.00, and DeltaRratio=1.00. The query is not a pure lookup; it depends on relationship traversal, so relationship semantics are expected to influence which document configurations should be benchmarked. The high DeltaRratio indicates that the selected candidate can absorb most of the conceptual traversal, which supports testing embedded or containment-oriented alternatives. The sharedness signal warns against interpreting embedding as automatically best, because highly shared entities can create duplication and maintenance pressure. The measured hot-run winner is G9 (hybrid_containment) from the `secondary_affected` group, with p95=115.3121 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G9 (hybrid_containment), with p95=115.3121 ms.

### imdb / QG10_AdvancedSearchWatchItems / sf0.5 / hot

**Focus.** association / sharedness / filtered search

**Why selected.** IMDb query with high sharedness and filter pressure over WatchItem-related structures. It helps explain why SchemaLens must consider trade-offs beyond simple containment.

**Analytical variables.** 
Root=WatchItem; Rc=4.00; D=1.00; Re=0.00; DeltaRratio=1.00; semantic=none; update=Low volatility exposure; sharedness=High sharedness.

**Activated classes.** G0|G2|G3

**Measured classes.** G0|G2|G3|G4|G5|G6|G7|G8|G9 (9 measured candidates in the benchmark-selection table).

**Measured winner.** G7 (containment_baseline) from `secondary_affected`; p95=171.6414 ms.

**Best SchemaLens-selected candidate.** G7 (containment_baseline); p95=171.6414 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G4|G8; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G2|G3|G5|G6|G8; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G2|G3|G4|G5|G6|G8; no_residual_traversal: top1=1.0, near=1.0, regret=0.0000, removed=G4|G8|G9; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=G5|G6; no_update_volatility: top1=0.0, near=1.0, regret=0.0003, removed=G7

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at WatchItem and has semantic profile `none` with Rc=4.00, D=1.00, Re=0.00, and DeltaRratio=1.00. The query is not a pure lookup; it depends on relationship traversal, so relationship semantics are expected to influence which document configurations should be benchmarked. The high DeltaRratio indicates that the selected candidate can absorb most of the conceptual traversal, which supports testing embedded or containment-oriented alternatives. The sharedness signal warns against interpreting embedding as automatically best, because highly shared entities can create duplication and maintenance pressure. The measured hot-run winner is G7 (containment_baseline) from the `secondary_affected` group, with p95=171.6414 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G7 (containment_baseline), with p95=171.6414 ms.

### imdb / QG10_AdvancedSearchWatchItems / sf1 / hot

**Focus.** association / sharedness / filtered search

**Why selected.** IMDb query with high sharedness and filter pressure over WatchItem-related structures. It helps explain why SchemaLens must consider trade-offs beyond simple containment.

**Analytical variables.** 
Root=WatchItem; Rc=4.00; D=1.00; Re=0.00; DeltaRratio=1.00; semantic=none; update=Low volatility exposure; sharedness=High sharedness.

**Activated classes.** G0|G2|G3

**Measured classes.** G0|G2|G3|G4|G5|G6|G7|G8|G9 (9 measured candidates in the benchmark-selection table).

**Measured winner.** G9 (hybrid_containment) from `secondary_affected`; p95=299.8020 ms.

**Best SchemaLens-selected candidate.** G9 (hybrid_containment); p95=299.8020 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G4|G8; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G2|G3|G5|G6|G8; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G2|G3|G4|G5|G6|G8; no_residual_traversal: top1=0.0, near=1.0, regret=0.0018, removed=G4|G8|G9; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=G5|G6; no_update_volatility: top1=1.0, near=1.0, regret=0.0000, removed=G7

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at WatchItem and has semantic profile `none` with Rc=4.00, D=1.00, Re=0.00, and DeltaRratio=1.00. The query is not a pure lookup; it depends on relationship traversal, so relationship semantics are expected to influence which document configurations should be benchmarked. The high DeltaRratio indicates that the selected candidate can absorb most of the conceptual traversal, which supports testing embedded or containment-oriented alternatives. The sharedness signal warns against interpreting embedding as automatically best, because highly shared entities can create duplication and maintenance pressure. The measured hot-run winner is G9 (hybrid_containment) from the `secondary_affected` group, with p95=299.8020 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G9 (hybrid_containment), with p95=299.8020 ms.

### imdb / QG6_EpisodesOfSeries / sf0.25 / hot

**Focus.** containment / low-sharedness traversal

**Why selected.** Canonical IMDb containment-like case: a series retrieves its episodes. It is useful to show when embedding/containment-style candidates are semantically justified.

**Analytical variables.** 
Root=Series; Rc=1.00; D=1.00; Re=0.00; DeltaRratio=1.00; semantic=none; update=No volatility exposure; sharedness=Low sharedness.

**Activated classes.** G7|G8|G9

**Measured classes.** G0|G2|G3|G4|G5|G6|G7|G8|G9 (9 measured candidates in the benchmark-selection table).

**Measured winner.** G2 (primary_document_candidate) from `control`; p95=0.6322 ms.

**Best SchemaLens-selected candidate.** G7 (containment_baseline); p95=0.9190 ms; Top-1 preserved=0; near-best preserved=0; relative regret=0.4536.

**Ablation signal.** no_depth: top1=0.0, near=0.0, regret=0.4536, removed=G8; no_relationship_semantics: top1=0.0, near=0.0, regret=0.4536, removed=G3|G8; no_relationship_semantics_no_depth: top1=0.0, near=0.0, regret=0.4536, removed=G3|G8; no_residual_traversal: top1=0.0, near=0.0, regret=0.4536, removed=G8|G9; no_sharedness: top1=0.0, near=0.0, regret=0.4536, removed=; no_update_volatility: top1=0.0, near=0.0, regret=0.4641, removed=G7

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Series and has semantic profile `none` with Rc=1.00, D=1.00, Re=0.00, and DeltaRratio=1.00. This makes the case suitable for testing whether containment-aware or hybrid document candidates reduce traversal without introducing unnecessary cross-document joins. The high DeltaRratio indicates that the selected candidate can absorb most of the conceptual traversal, which supports testing embedded or containment-oriented alternatives. The measured hot-run winner is G2 (primary_document_candidate) from the `control` group, with p95=0.6322 ms. SchemaLens missed the Top-1 and the near-best region for this scale/phase; this should be treated as a failure or near-failure case with relative regret 0.4536. The best SchemaLens-selected configuration was G7 (containment_baseline), with p95=0.9190 ms.

### imdb / QG6_EpisodesOfSeries / sf0.5 / hot

**Focus.** containment / low-sharedness traversal

**Why selected.** Canonical IMDb containment-like case: a series retrieves its episodes. It is useful to show when embedding/containment-style candidates are semantically justified.

**Analytical variables.** 
Root=Series; Rc=1.00; D=1.00; Re=0.00; DeltaRratio=1.00; semantic=none; update=No volatility exposure; sharedness=Low sharedness.

**Activated classes.** G7|G8|G9

**Measured classes.** G0|G2|G3|G4|G5|G6|G7|G8|G9 (9 measured candidates in the benchmark-selection table).

**Measured winner.** G7 (containment_baseline) from `primary`; p95=1.0162 ms.

**Best SchemaLens-selected candidate.** G7 (containment_baseline); p95=1.0162 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G8; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G3|G8; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3|G8; no_residual_traversal: top1=1.0, near=1.0, regret=0.0000, removed=G8|G9; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=; no_update_volatility: top1=0.0, near=0.0, regret=0.4072, removed=G7

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Series and has semantic profile `none` with Rc=1.00, D=1.00, Re=0.00, and DeltaRratio=1.00. This makes the case suitable for testing whether containment-aware or hybrid document candidates reduce traversal without introducing unnecessary cross-document joins. The high DeltaRratio indicates that the selected candidate can absorb most of the conceptual traversal, which supports testing embedded or containment-oriented alternatives. The measured hot-run winner is G7 (containment_baseline) from the `primary` group, with p95=1.0162 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G7 (containment_baseline), with p95=1.0162 ms.

### imdb / QG6_EpisodesOfSeries / sf1 / hot

**Focus.** containment / low-sharedness traversal

**Why selected.** Canonical IMDb containment-like case: a series retrieves its episodes. It is useful to show when embedding/containment-style candidates are semantically justified.

**Analytical variables.** 
Root=Series; Rc=1.00; D=1.00; Re=0.00; DeltaRratio=1.00; semantic=none; update=No volatility exposure; sharedness=Low sharedness.

**Activated classes.** G7|G8|G9

**Measured classes.** G0|G2|G3|G4|G5|G6|G7|G8|G9 (9 measured candidates in the benchmark-selection table).

**Measured winner.** G7 (containment_baseline) from `primary`; p95=2.2719 ms.

**Best SchemaLens-selected candidate.** G7 (containment_baseline); p95=2.2719 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G8; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G3|G8; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3|G8; no_residual_traversal: top1=1.0, near=1.0, regret=0.0000, removed=G8|G9; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=; no_update_volatility: top1=0.0, near=0.0, regret=0.0982, removed=G7

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Series and has semantic profile `none` with Rc=1.00, D=1.00, Re=0.00, and DeltaRratio=1.00. This makes the case suitable for testing whether containment-aware or hybrid document candidates reduce traversal without introducing unnecessary cross-document joins. The high DeltaRratio indicates that the selected candidate can absorb most of the conceptual traversal, which supports testing embedded or containment-oriented alternatives. The measured hot-run winner is G7 (containment_baseline) from the `primary` group, with p95=2.2719 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G7 (containment_baseline), with p95=2.2719 ms.

### ldbc_snb / IC1_TransitiveFriendsWithName / sf0.1 / hot

**Focus.** official complex read / transitive association

**Why selected.** Official LDBC SNB complex query with repeated person-knows-person traversal and profile expansion. It tests whether activated configurations preserve strong candidates under graph-like access.

**Analytical variables.** 
Root=Person; Rc=7.00; D=4.00; Re=3.00; DeltaRratio=0.57; semantic=association; update=high; sharedness=high.

**Activated classes.** G0|G3

**Measured classes.** G0|G3 (2 measured candidates in the benchmark-selection table).

**Measured winner.** G3 (Root document with references or denormalized summaries) from `primary`; p95=131.3617 ms.

**Best SchemaLens-selected candidate.** G3 (Root document with references or denormalized summaries); p95=131.3617 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=0.0, near=0.0, regret=0.1615, removed=G3; no_relationship_semantics: top1=0.0, near=0.0, regret=0.1615, removed=G3; no_relationship_semantics_no_depth: top1=0.0, near=0.0, regret=0.1615, removed=G3; no_residual_traversal: top1=0.0, near=0.0, regret=0.1615, removed=G3; no_sharedness: top1=0.0, near=0.0, regret=0.1615, removed=G3; no_update_volatility: top1=0.0, near=0.0, regret=0.1615, removed=G3

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `association` with Rc=7.00, D=4.00, Re=3.00, and DeltaRratio=0.57. The depth signal is important because the workload traverses several conceptual hops; removing depth from the activation logic should therefore make the selected space less reliable. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The sharedness signal warns against interpreting embedding as automatically best, because highly shared entities can create duplication and maintenance pressure. The measured hot-run winner is G3 (Root document with references or denormalized summaries) from the `primary` group, with p95=131.3617 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G3 (Root document with references or denormalized summaries), with p95=131.3617 ms.

### ldbc_snb / IC1_TransitiveFriendsWithName / sf1 / hot

**Focus.** official complex read / transitive association

**Why selected.** Official LDBC SNB complex query with repeated person-knows-person traversal and profile expansion. It tests whether activated configurations preserve strong candidates under graph-like access.

**Analytical variables.** 
Root=Person; Rc=7.00; D=4.00; Re=3.00; DeltaRratio=0.57; semantic=association; update=high; sharedness=high.

**Activated classes.** G0|G3

**Measured classes.** G0|G3 (2 measured candidates in the benchmark-selection table).

**Measured winner.** G3 (Root document with references or denormalized summaries) from `primary`; p95=227.7275 ms.

**Best SchemaLens-selected candidate.** G3 (Root document with references or denormalized summaries); p95=227.7275 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=0.0, near=0.0, regret=0.1064, removed=G3; no_relationship_semantics: top1=0.0, near=0.0, regret=0.1064, removed=G3; no_relationship_semantics_no_depth: top1=0.0, near=0.0, regret=0.1064, removed=G3; no_residual_traversal: top1=0.0, near=0.0, regret=0.1064, removed=G3; no_sharedness: top1=0.0, near=0.0, regret=0.1064, removed=G3; no_update_volatility: top1=0.0, near=0.0, regret=0.1064, removed=G3

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `association` with Rc=7.00, D=4.00, Re=3.00, and DeltaRratio=0.57. The depth signal is important because the workload traverses several conceptual hops; removing depth from the activation logic should therefore make the selected space less reliable. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The sharedness signal warns against interpreting embedding as automatically best, because highly shared entities can create duplication and maintenance pressure. The measured hot-run winner is G3 (Root document with references or denormalized summaries) from the `primary` group, with p95=227.7275 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G3 (Root document with references or denormalized summaries), with p95=227.7275 ms.

### ldbc_snb / IC1_TransitiveFriendsWithName / sf3 / hot

**Focus.** official complex read / transitive association

**Why selected.** Official LDBC SNB complex query with repeated person-knows-person traversal and profile expansion. It tests whether activated configurations preserve strong candidates under graph-like access.

**Analytical variables.** 
Root=Person; Rc=7.00; D=4.00; Re=3.00; DeltaRratio=0.57; semantic=association; update=high; sharedness=high.

**Activated classes.** G0|G3

**Measured classes.** G0|G3 (2 measured candidates in the benchmark-selection table).

**Measured winner.** G3 (Root document with references or denormalized summaries) from `primary`; p95=260.0222 ms.

**Best SchemaLens-selected candidate.** G3 (Root document with references or denormalized summaries); p95=260.0222 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=0.0, near=0.0, regret=0.0556, removed=G3; no_relationship_semantics: top1=0.0, near=0.0, regret=0.0556, removed=G3; no_relationship_semantics_no_depth: top1=0.0, near=0.0, regret=0.0556, removed=G3; no_residual_traversal: top1=0.0, near=0.0, regret=0.0556, removed=G3; no_sharedness: top1=0.0, near=0.0, regret=0.0556, removed=G3; no_update_volatility: top1=0.0, near=0.0, regret=0.0556, removed=G3

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `association` with Rc=7.00, D=4.00, Re=3.00, and DeltaRratio=0.57. The depth signal is important because the workload traverses several conceptual hops; removing depth from the activation logic should therefore make the selected space less reliable. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The sharedness signal warns against interpreting embedding as automatically best, because highly shared entities can create duplication and maintenance pressure. The measured hot-run winner is G3 (Root document with references or denormalized summaries) from the `primary` group, with p95=260.0222 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G3 (Root document with references or denormalized summaries), with p95=260.0222 ms.

### ldbc_snb / IC5_NewGroups / sf0.1 / hot

**Focus.** official complex read / association + containment mix

**Why selected.** Official LDBC SNB query mixing friendship, forum membership, forum containment, and posts. It is useful for showing why secondary affected families may win.

**Analytical variables.** 
Root=Person; Rc=5.00; D=3.00; Re=2.00; DeltaRratio=0.60; semantic=association; update=high; sharedness=low.

**Activated classes.** G0|G3|G4|G6|G7|G9

**Measured classes.** G0|G3|G4|G6|G7|G9 (6 measured candidates in the benchmark-selection table).

**Measured winner.** G7 (Containment baseline) from `secondary_affected`; p95=135.3230 ms.

**Best SchemaLens-selected candidate.** G7 (Containment baseline); p95=135.3230 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4|G6; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4|G6; no_residual_traversal: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4|G9; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=G3|G6|G9; no_update_volatility: top1=0.0, near=1.0, regret=0.0402, removed=G3|G7|G9

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `association` with Rc=5.00, D=3.00, Re=2.00, and DeltaRratio=0.60. This makes the case suitable for testing whether containment-aware or hybrid document candidates reduce traversal without introducing unnecessary cross-document joins. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The measured hot-run winner is G7 (Containment baseline) from the `secondary_affected` group, with p95=135.3230 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G7 (Containment baseline), with p95=135.3230 ms.

### ldbc_snb / IC5_NewGroups / sf1 / hot

**Focus.** official complex read / association + containment mix

**Why selected.** Official LDBC SNB query mixing friendship, forum membership, forum containment, and posts. It is useful for showing why secondary affected families may win.

**Analytical variables.** 
Root=Person; Rc=5.00; D=3.00; Re=2.00; DeltaRratio=0.60; semantic=association; update=high; sharedness=low.

**Activated classes.** G0|G3|G4|G6|G7|G9

**Measured classes.** G0|G3|G4|G6|G7|G9 (6 measured candidates in the benchmark-selection table).

**Measured winner.** G6 (Referenced or reverse-indexed associative pattern) from `secondary_affected`; p95=176.7536 ms.

**Best SchemaLens-selected candidate.** G6 (Referenced or reverse-indexed associative pattern); p95=176.7536 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4; no_relationship_semantics: top1=0.0, near=1.0, regret=0.0227, removed=G3|G4|G6; no_relationship_semantics_no_depth: top1=0.0, near=1.0, regret=0.0227, removed=G3|G4|G6; no_residual_traversal: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4|G9; no_sharedness: top1=0.0, near=1.0, regret=0.0454, removed=G3|G6|G9; no_update_volatility: top1=1.0, near=1.0, regret=0.0000, removed=G3|G7|G9

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `association` with Rc=5.00, D=3.00, Re=2.00, and DeltaRratio=0.60. This makes the case suitable for testing whether containment-aware or hybrid document candidates reduce traversal without introducing unnecessary cross-document joins. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The measured hot-run winner is G6 (Referenced or reverse-indexed associative pattern) from the `secondary_affected` group, with p95=176.7536 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G6 (Referenced or reverse-indexed associative pattern), with p95=176.7536 ms.

### ldbc_snb / IC5_NewGroups / sf3 / hot

**Focus.** official complex read / association + containment mix

**Why selected.** Official LDBC SNB query mixing friendship, forum membership, forum containment, and posts. It is useful for showing why secondary affected families may win.

**Analytical variables.** 
Root=Person; Rc=5.00; D=3.00; Re=2.00; DeltaRratio=0.60; semantic=association; update=high; sharedness=low.

**Activated classes.** G0|G3|G4|G6|G7|G9

**Measured classes.** G0|G3|G4|G6|G7|G9 (6 measured candidates in the benchmark-selection table).

**Measured winner.** G7 (Containment baseline) from `secondary_affected`; p95=193.8014 ms.

**Best SchemaLens-selected candidate.** G7 (Containment baseline); p95=193.8014 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4|G6; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4|G6; no_residual_traversal: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4|G9; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=G3|G6|G9; no_update_volatility: top1=0.0, near=1.0, regret=0.0215, removed=G3|G7|G9

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `association` with Rc=5.00, D=3.00, Re=2.00, and DeltaRratio=0.60. This makes the case suitable for testing whether containment-aware or hybrid document candidates reduce traversal without introducing unnecessary cross-document joins. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The measured hot-run winner is G7 (Containment baseline) from the `secondary_affected` group, with p95=193.8014 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G7 (Containment baseline), with p95=193.8014 ms.

### ldbc_snb / IC7_RecentLikers / sf0.1 / hot

**Focus.** official complex read / likes and friend check

**Why selected.** Official LDBC SNB query combining recent likes, message ownership, and friendship checks. It exposes association and associative-edge trade-offs.

**Analytical variables.** 
Root=Person; Rc=5.00; D=2.00; Re=3.00; DeltaRratio=0.40; semantic=association; update=high; sharedness=low.

**Activated classes.** G0|G3|G4|G6

**Measured classes.** G0|G3|G4|G6 (4 measured candidates in the benchmark-selection table).

**Measured winner.** G4 (Associative relationship as explicit document) from `secondary_affected`; p95=7.4644 ms.

**Best SchemaLens-selected candidate.** G4 (Associative relationship as explicit document); p95=7.4644 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=0.0, near=0.0, regret=0.3591, removed=G3|G4; no_relationship_semantics: top1=0.0, near=0.0, regret=0.3591, removed=G3|G4|G6; no_relationship_semantics_no_depth: top1=0.0, near=0.0, regret=0.3591, removed=G3|G4|G6; no_residual_traversal: top1=0.0, near=0.0, regret=0.3591, removed=G3|G4; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=G3|G6; no_update_volatility: top1=1.0, near=1.0, regret=0.0000, removed=G3

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `association` with Rc=5.00, D=2.00, Re=3.00, and DeltaRratio=0.40. The query is not a pure lookup; it depends on relationship traversal, so relationship semantics are expected to influence which document configurations should be benchmarked. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The measured hot-run winner is G4 (Associative relationship as explicit document) from the `secondary_affected` group, with p95=7.4644 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G4 (Associative relationship as explicit document), with p95=7.4644 ms.

### ldbc_snb / IC7_RecentLikers / sf1 / hot

**Focus.** official complex read / likes and friend check

**Why selected.** Official LDBC SNB query combining recent likes, message ownership, and friendship checks. It exposes association and associative-edge trade-offs.

**Analytical variables.** 
Root=Person; Rc=5.00; D=2.00; Re=3.00; DeltaRratio=0.40; semantic=association; update=high; sharedness=low.

**Activated classes.** G0|G3|G4|G6

**Measured classes.** G0|G3|G4|G6 (4 measured candidates in the benchmark-selection table).

**Measured winner.** G3 (Root document with references or denormalized summaries) from `primary`; p95=7.0093 ms.

**Best SchemaLens-selected candidate.** G3 (Root document with references or denormalized summaries); p95=7.0093 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=0.0, near=0.0, regret=0.2653, removed=G3|G4; no_relationship_semantics: top1=0.0, near=0.0, regret=2.6478, removed=G3|G4|G6; no_relationship_semantics_no_depth: top1=0.0, near=0.0, regret=2.6478, removed=G3|G4|G6; no_residual_traversal: top1=0.0, near=0.0, regret=0.2653, removed=G3|G4; no_sharedness: top1=0.0, near=0.0, regret=0.7492, removed=G3|G6; no_update_volatility: top1=0.0, near=0.0, regret=0.2653, removed=G3

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `association` with Rc=5.00, D=2.00, Re=3.00, and DeltaRratio=0.40. The query is not a pure lookup; it depends on relationship traversal, so relationship semantics are expected to influence which document configurations should be benchmarked. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The measured hot-run winner is G3 (Root document with references or denormalized summaries) from the `primary` group, with p95=7.0093 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G3 (Root document with references or denormalized summaries), with p95=7.0093 ms.

### ldbc_snb / IC7_RecentLikers / sf3 / hot

**Focus.** official complex read / likes and friend check

**Why selected.** Official LDBC SNB query combining recent likes, message ownership, and friendship checks. It exposes association and associative-edge trade-offs.

**Analytical variables.** 
Root=Person; Rc=5.00; D=2.00; Re=3.00; DeltaRratio=0.40; semantic=association; update=high; sharedness=low.

**Activated classes.** G0|G3|G4|G6

**Measured classes.** G0|G3|G4|G6 (4 measured candidates in the benchmark-selection table).

**Measured winner.** G4 (Associative relationship as explicit document) from `secondary_affected`; p95=8.0368 ms.

**Best SchemaLens-selected candidate.** G4 (Associative relationship as explicit document); p95=8.0368 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=0.0, near=0.0, regret=0.2104, removed=G3|G4; no_relationship_semantics: top1=0.0, near=0.0, regret=0.2104, removed=G3|G4|G6; no_relationship_semantics_no_depth: top1=0.0, near=0.0, regret=0.2104, removed=G3|G4|G6; no_residual_traversal: top1=0.0, near=0.0, regret=0.2104, removed=G3|G4; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=G3|G6; no_update_volatility: top1=1.0, near=1.0, regret=0.0000, removed=G3

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `association` with Rc=5.00, D=2.00, Re=3.00, and DeltaRratio=0.40. The query is not a pure lookup; it depends on relationship traversal, so relationship semantics are expected to influence which document configurations should be benchmarked. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The measured hot-run winner is G4 (Associative relationship as explicit document) from the `secondary_affected` group, with p95=8.0368 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G4 (Associative relationship as explicit document), with p95=8.0368 ms.

### ldbc_snb / IS2_RecentMessagesOfPerson / sf0.1 / hot

**Focus.** official short read / messages of person

**Why selected.** Official LDBC SNB short read with posts/comments and reply context. It is a compact case for residual traversal and mixed message structures.

**Analytical variables.** 
Root=Person; Rc=4.00; D=2.00; Re=2.00; DeltaRratio=0.50; semantic=mixed; update=high; sharedness=low.

**Activated classes.** G0|G3|G4|G6|G7|G9

**Measured classes.** G0|G3|G4|G6|G7|G9 (6 measured candidates in the benchmark-selection table).

**Measured winner.** G6 (Referenced or reverse-indexed associative pattern) from `secondary_affected`; p95=2.2558 ms.

**Best SchemaLens-selected candidate.** G6 (Referenced or reverse-indexed associative pattern); p95=2.2558 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4; no_relationship_semantics: top1=0.0, near=1.0, regret=0.0367, removed=G3|G4|G6; no_relationship_semantics_no_depth: top1=0.0, near=1.0, regret=0.0367, removed=G3|G4|G6; no_residual_traversal: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4|G9; no_sharedness: top1=0.0, near=1.0, regret=0.0367, removed=G3|G6|G9; no_update_volatility: top1=1.0, near=1.0, regret=0.0000, removed=G3|G7|G9

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `mixed` with Rc=4.00, D=2.00, Re=2.00, and DeltaRratio=0.50. The query is not a pure lookup; it depends on relationship traversal, so relationship semantics are expected to influence which document configurations should be benchmarked. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The measured hot-run winner is G6 (Referenced or reverse-indexed associative pattern) from the `secondary_affected` group, with p95=2.2558 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G6 (Referenced or reverse-indexed associative pattern), with p95=2.2558 ms.

### ldbc_snb / IS2_RecentMessagesOfPerson / sf1 / hot

**Focus.** official short read / messages of person

**Why selected.** Official LDBC SNB short read with posts/comments and reply context. It is a compact case for residual traversal and mixed message structures.

**Analytical variables.** 
Root=Person; Rc=4.00; D=2.00; Re=2.00; DeltaRratio=0.50; semantic=mixed; update=high; sharedness=low.

**Activated classes.** G0|G3|G4|G6|G7|G9

**Measured classes.** G0|G3|G4|G6|G7|G9 (6 measured candidates in the benchmark-selection table).

**Measured winner.** G9 (Hybrid containment with references or summaries) from `secondary_affected`; p95=3.2309 ms.

**Best SchemaLens-selected candidate.** G9 (Hybrid containment with references or summaries); p95=3.2309 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4|G6; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4|G6; no_residual_traversal: top1=0.0, near=0.0, regret=0.0793, removed=G3|G4|G9; no_sharedness: top1=0.0, near=0.0, regret=0.0793, removed=G3|G6|G9; no_update_volatility: top1=0.0, near=0.0, regret=0.0863, removed=G3|G7|G9

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `mixed` with Rc=4.00, D=2.00, Re=2.00, and DeltaRratio=0.50. The query is not a pure lookup; it depends on relationship traversal, so relationship semantics are expected to influence which document configurations should be benchmarked. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The measured hot-run winner is G9 (Hybrid containment with references or summaries) from the `secondary_affected` group, with p95=3.2309 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G9 (Hybrid containment with references or summaries), with p95=3.2309 ms.

### ldbc_snb / IS2_RecentMessagesOfPerson / sf3 / hot

**Focus.** official short read / messages of person

**Why selected.** Official LDBC SNB short read with posts/comments and reply context. It is a compact case for residual traversal and mixed message structures.

**Analytical variables.** 
Root=Person; Rc=4.00; D=2.00; Re=2.00; DeltaRratio=0.50; semantic=mixed; update=high; sharedness=low.

**Activated classes.** G0|G3|G4|G6|G7|G9

**Measured classes.** G0|G3|G4|G6|G7|G9 (6 measured candidates in the benchmark-selection table).

**Measured winner.** G0 (Root document with referenced associations) from `secondary_affected`; p95=2.7113 ms.

**Best SchemaLens-selected candidate.** G0 (Root document with referenced associations); p95=2.7113 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4|G6; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4|G6; no_residual_traversal: top1=1.0, near=1.0, regret=0.0000, removed=G3|G4|G9; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=G3|G6|G9; no_update_volatility: top1=1.0, near=1.0, regret=0.0000, removed=G3|G7|G9

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Person and has semantic profile `mixed` with Rc=4.00, D=2.00, Re=2.00, and DeltaRratio=0.50. The query is not a pure lookup; it depends on relationship traversal, so relationship semantics are expected to influence which document configurations should be benchmarked. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The measured hot-run winner is G0 (Root document with referenced associations) from the `secondary_affected` group, with p95=2.7113 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G0 (Root document with referenced associations), with p95=2.7113 ms.

### ldbc_snb / IS6_ForumOfMessage / sf0.1 / hot

**Focus.** official short read / containment path

**Why selected.** Official LDBC SNB short read asking for the forum containing a message and the moderator. It highlights containment-like paths in the social-network workload.

**Analytical variables.** 
Root=Post; Rc=4.00; D=3.00; Re=1.00; DeltaRratio=0.75; semantic=containment; update=high; sharedness=low.

**Activated classes.** G0|G3|G7|G9

**Measured classes.** G0|G3|G7|G9 (4 measured candidates in the benchmark-selection table).

**Measured winner.** G9 (Hybrid containment with references or summaries) from `primary`; p95=1.1708 ms.

**Best SchemaLens-selected candidate.** G9 (Hybrid containment with references or summaries); p95=1.1708 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_residual_traversal: top1=0.0, near=0.0, regret=0.3978, removed=G3|G9; no_sharedness: top1=0.0, near=0.0, regret=0.3978, removed=G3|G9; no_update_volatility: top1=0.0, near=0.0, regret=2.8790, removed=G3|G7|G9

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Post and has semantic profile `containment` with Rc=4.00, D=3.00, Re=1.00, and DeltaRratio=0.75. This makes the case suitable for testing whether containment-aware or hybrid document candidates reduce traversal without introducing unnecessary cross-document joins. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The measured hot-run winner is G9 (Hybrid containment with references or summaries) from the `primary` group, with p95=1.1708 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G9 (Hybrid containment with references or summaries), with p95=1.1708 ms.

### ldbc_snb / IS6_ForumOfMessage / sf1 / hot

**Focus.** official short read / containment path

**Why selected.** Official LDBC SNB short read asking for the forum containing a message and the moderator. It highlights containment-like paths in the social-network workload.

**Analytical variables.** 
Root=Post; Rc=4.00; D=3.00; Re=1.00; DeltaRratio=0.75; semantic=containment; update=high; sharedness=low.

**Activated classes.** G0|G3|G7|G9

**Measured classes.** G0|G3|G7|G9 (4 measured candidates in the benchmark-selection table).

**Measured winner.** G9 (Hybrid containment with references or summaries) from `primary`; p95=2.3013 ms.

**Best SchemaLens-selected candidate.** G9 (Hybrid containment with references or summaries); p95=2.3013 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_residual_traversal: top1=0.0, near=1.0, regret=0.0178, removed=G3|G9; no_sharedness: top1=0.0, near=1.0, regret=0.0178, removed=G3|G9; no_update_volatility: top1=0.0, near=1.0, regret=0.0178, removed=G3|G7|G9

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Post and has semantic profile `containment` with Rc=4.00, D=3.00, Re=1.00, and DeltaRratio=0.75. This makes the case suitable for testing whether containment-aware or hybrid document candidates reduce traversal without introducing unnecessary cross-document joins. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The measured hot-run winner is G9 (Hybrid containment with references or summaries) from the `primary` group, with p95=2.3013 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G9 (Hybrid containment with references or summaries), with p95=2.3013 ms.

### ldbc_snb / IS6_ForumOfMessage / sf3 / hot

**Focus.** official short read / containment path

**Why selected.** Official LDBC SNB short read asking for the forum containing a message and the moderator. It highlights containment-like paths in the social-network workload.

**Analytical variables.** 
Root=Post; Rc=4.00; D=3.00; Re=1.00; DeltaRratio=0.75; semantic=containment; update=high; sharedness=low.

**Activated classes.** G0|G3|G7|G9

**Measured classes.** G0|G3|G7|G9 (4 measured candidates in the benchmark-selection table).

**Measured winner.** G0 (Root document with referenced associations) from `secondary_affected`; p95=1.3324 ms.

**Best SchemaLens-selected candidate.** G0 (Root document with referenced associations); p95=1.3324 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_residual_traversal: top1=1.0, near=1.0, regret=0.0000, removed=G3|G9; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=G3|G9; no_update_volatility: top1=1.0, near=1.0, regret=0.0000, removed=G3|G7|G9

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Post and has semantic profile `containment` with Rc=4.00, D=3.00, Re=1.00, and DeltaRratio=0.75. This makes the case suitable for testing whether containment-aware or hybrid document candidates reduce traversal without introducing unnecessary cross-document joins. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The measured hot-run winner is G0 (Root document with referenced associations) from the `secondary_affected` group, with p95=1.3324 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G0 (Root document with referenced associations), with p95=1.3324 ms.

### ldbc_snb / IS7_RepliesOfMessage / sf0.1 / hot

**Focus.** official short read / replies and author relation

**Why selected.** Official LDBC SNB short read over replies, authors, and whether authors know each other. It is useful for explaining mixed association and containment traversal.

**Analytical variables.** 
Root=Post; Rc=5.00; D=2.00; Re=3.00; DeltaRratio=0.40; semantic=association; update=high; sharedness=low.

**Activated classes.** G0|G3|G7|G9

**Measured classes.** G0|G3|G7|G9 (4 measured candidates in the benchmark-selection table).

**Measured winner.** G0 (Root document with referenced associations) from `primary`; p95=7.9440 ms.

**Best SchemaLens-selected candidate.** G0 (Root document with referenced associations); p95=7.9440 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_residual_traversal: top1=1.0, near=1.0, regret=0.0000, removed=G3|G9; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=G3|G9; no_update_volatility: top1=1.0, near=1.0, regret=0.0000, removed=G3|G7|G9

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Post and has semantic profile `association` with Rc=5.00, D=2.00, Re=3.00, and DeltaRratio=0.40. The query is not a pure lookup; it depends on relationship traversal, so relationship semantics are expected to influence which document configurations should be benchmarked. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The measured hot-run winner is G0 (Root document with referenced associations) from the `primary` group, with p95=7.9440 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G0 (Root document with referenced associations), with p95=7.9440 ms.

### ldbc_snb / IS7_RepliesOfMessage / sf1 / hot

**Focus.** official short read / replies and author relation

**Why selected.** Official LDBC SNB short read over replies, authors, and whether authors know each other. It is useful for explaining mixed association and containment traversal.

**Analytical variables.** 
Root=Post; Rc=5.00; D=2.00; Re=3.00; DeltaRratio=0.40; semantic=association; update=high; sharedness=low.

**Activated classes.** G0|G3|G7|G9

**Measured classes.** G0|G3|G7|G9 (4 measured candidates in the benchmark-selection table).

**Measured winner.** G9 (Hybrid containment with references or summaries) from `secondary_affected`; p95=11.0091 ms.

**Best SchemaLens-selected candidate.** G9 (Hybrid containment with references or summaries); p95=11.0091 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_residual_traversal: top1=0.0, near=1.0, regret=0.0398, removed=G3|G9; no_sharedness: top1=0.0, near=1.0, regret=0.0398, removed=G3|G9; no_update_volatility: top1=0.0, near=1.0, regret=0.0398, removed=G3|G7|G9

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Post and has semantic profile `association` with Rc=5.00, D=2.00, Re=3.00, and DeltaRratio=0.40. The query is not a pure lookup; it depends on relationship traversal, so relationship semantics are expected to influence which document configurations should be benchmarked. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The measured hot-run winner is G9 (Hybrid containment with references or summaries) from the `secondary_affected` group, with p95=11.0091 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G9 (Hybrid containment with references or summaries), with p95=11.0091 ms.

### ldbc_snb / IS7_RepliesOfMessage / sf3 / hot

**Focus.** official short read / replies and author relation

**Why selected.** Official LDBC SNB short read over replies, authors, and whether authors know each other. It is useful for explaining mixed association and containment traversal.

**Analytical variables.** 
Root=Post; Rc=5.00; D=2.00; Re=3.00; DeltaRratio=0.40; semantic=association; update=high; sharedness=low.

**Activated classes.** G0|G3|G7|G9

**Measured classes.** G0|G3|G7|G9 (4 measured candidates in the benchmark-selection table).

**Measured winner.** G7 (Containment baseline) from `secondary_affected`; p95=14.0368 ms.

**Best SchemaLens-selected candidate.** G7 (Containment baseline); p95=14.0368 ms; Top-1 preserved=1; near-best preserved=1; relative regret=0.0000.

**Ablation signal.** no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_relationship_semantics: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_relationship_semantics_no_depth: top1=1.0, near=1.0, regret=0.0000, removed=G3; no_residual_traversal: top1=1.0, near=1.0, regret=0.0000, removed=G3|G9; no_sharedness: top1=1.0, near=1.0, regret=0.0000, removed=G3|G9; no_update_volatility: top1=0.0, near=0.0, regret=1.0827, removed=G3|G7|G9

**Random-k diagnostic.** diagnostic_rows=1

**Interpretation.** The query is rooted at Post and has semantic profile `association` with Rc=5.00, D=2.00, Re=3.00, and DeltaRratio=0.40. The query is not a pure lookup; it depends on relationship traversal, so relationship semantics are expected to influence which document configurations should be benchmarked. Because Re is greater than zero, some traversal remains after the selected document abstraction; this explains why reference, reverse-index, explicit-edge, or hybrid candidates may still be competitive. The update-volatility signal is relevant here; a good result for a reference or hybrid class means that SchemaLens is capturing the maintenance cost of overly embedded designs, not only read locality. The measured hot-run winner is G7 (Containment baseline) from the `secondary_affected` group, with p95=14.0368 ms. SchemaLens preserved the measured Top-1 configuration, so this case supports the claim that the activation matrix keeps the relevant winner inside the reduced benchmark space. The best SchemaLens-selected configuration was G7 (Containment baseline), with p95=14.0368 ms.

## Suggested text for the advisor response

I added a representative-case analysis that connects the analytical variables used by SchemaLens with the measured benchmark winners. For each selected IMDb, FIBEN, and LDBC SNB case, the analysis reports the selected root, traversal count, embedding depth, residual traversal, semantic type, sharedness, update pressure, activated G classes, measured benchmark candidates, the hot-run p95 winner, and whether the reduced SchemaLens space preserved the Top-1 or a near-best configuration. This complements the baseline and ablation studies by explaining why specific configurations win under specific workload and data characteristics, instead of only reporting aggregate preservation metrics.
