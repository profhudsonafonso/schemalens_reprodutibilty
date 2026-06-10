# DBSR Implementation for FIBEN Baseline Comparison

This folder contains an independent implementation plan and experimental scaffold for reproducing the DBSR baseline on the FIBEN workload and comparing it with SchemaLens.

DBSR is treated here as a related-work baseline and not as a SchemaLens variant. The goal is to reproduce the DBSR workflow as faithfully as possible from the paper before any comparison with SchemaLens. In particular, DBSR should generate its own document structures, query plans, secondary index recommendations, ranking/utility outputs, and benchmarkable MongoDB materializations.

## Scope

Initial dataset: FIBEN.

Initial workload: FIBEN read queries Q1--Q9.

FIBEN Q10 is an update/insert case and is handled separately as either an extension or a limitation, because the DBSR core method is read-workload oriented.

## Main principles

1. Do not modify existing SchemaLens benchmark results.
2. Do not map DBSR directly to SchemaLens G0--G9 templates during generation.
3. Generate DBSR document structures independently from the DBSR algorithm.
4. Use a separate materialization layer to transform DBSR recommendations into physical MongoDB collections.
5. Use the same experimental environment as SchemaLens whenever possible.
6. Use hot-run p95 latency as the main comparison metric.
7. Document every missing detail from the DBSR paper as an implementation assumption.
8. Keep this folder anonymous and reproducible: no personal names, no local absolute paths, no raw data dumps, no credentials, and no reviewer-sensitive metadata.

## Folder structure

```text
DBSR_implementation/
  README.md
  input/
    fiben/
      manual_relationship_overrides.json
      query_sequence_overrides.json
  src/
    dbsr_core/
      model.py
      workload.py
      document_tree.py
      query_plan.py
      generator.py
      merge_rules.py
      cost_model.py
      pruning.py
      utility.py
    fiben_adapter/
      build_fiben_dbsr_input.py
      build_fiben_workload.py
      extract_fiben_statistics.py
    materialization/
      materialize_dbsr_mongo.py
      execute_dbsr_query_plans.py
    analysis/
      compare_schemalens_vs_dbsr.py
      export_latex_tables.py
  generated/
    fiben/
      dbsr_input_model.json
      dbsr_workload.json
      dbsr_recommended_documents.csv
      dbsr_query_plans.csv
      dbsr_indexes.csv
      dbsr_ranked_schemas.csv
  benchmark/
    fiben/
      run_dbsr_fiben_benchmark.py
      run_dbsr_fiben_query_plan.py
  results/
    fiben/
      dbsr_benchmark_results.csv
      schemalens_vs_dbsr_comparison.csv
      latex/
  docs/
```

## Planned generated files

The first reproducible outputs will be:

```text
DBSR_implementation/generated/fiben/dbsr_input_model.json
DBSR_implementation/generated/fiben/dbsr_workload.json
DBSR_implementation/generated/fiben/dbsr_recommended_documents.csv
DBSR_implementation/generated/fiben/dbsr_query_plans.csv
DBSR_implementation/generated/fiben/dbsr_indexes.csv
DBSR_implementation/generated/fiben/dbsr_ranked_schemas.csv
DBSR_implementation/results/fiben/dbsr_benchmark_results.csv
DBSR_implementation/results/fiben/schemalens_vs_dbsr_comparison.csv
```

## DBSR reproduction steps

| Step                                  | Status  | Output                              | Notes                                                                             |
| ------------------------------------- | ------- | ----------------------------------- | --------------------------------------------------------------------------------- |
| Build FIBEN ER/application model      | Planned | `dbsr_input_model.json`             | Uses FIBEN entities, fields, keys, and relationships.                             |
| Build FIBEN read workload             | Planned | `dbsr_workload.json`                | Queries Q1--Q9 represented as read join sequences.                                |
| Generate initial documents            | Planned | Internal candidates                 | One-level documents from touched entities/fields.                                 |
| Generate initial query plans          | Planned | `dbsr_query_plans.csv`              | Query plans over initial documents.                                               |
| Iterative document merging            | Planned | Candidate document trees            | Merge documents when this removes join steps.                                     |
| Query-plan replacement and compaction | Planned | Optimized query plans               | Rewrites plans using newly generated documents.                                   |
| Secondary index tracking              | Planned | `dbsr_indexes.csv`                  | Indexes required by query plans, including nested fields.                         |
| Cost model and pruning                | Planned | Ranked query plans                  | Uses selected records, result size, secondary-index effects, and query frequency. |
| Document utility matrix               | Planned | `dbsr_ranked_schemas.csv`           | Uses utility/fitness over query-plan ranks.                                       |
| Final DBSR recommendation             | Planned | `dbsr_recommended_documents.csv`    | Produces top recommended document structures.                                     |
| MongoDB materialization layer         | Planned | Physical DBSR databases             | This is not part of DBSR core; it is an experimental adapter.                     |
| MongoDB benchmark                     | Planned | `dbsr_benchmark_results.csv`        | Uses hot-run p95 as the main metric.                                              |
| SchemaLens vs DBSR comparison         | Planned | `schemalens_vs_dbsr_comparison.csv` | Computes regret, top-1, near-best, and winners.                                   |

## Implementation assumptions log

Each assumption must be recorded here before coding.

| ID  | Assumption                                                                    | Reason                                                                                                        | Impact                                                              |
| --- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| A01 | FIBEN Q1--Q9 are treated as DBSR read workload sequences.                     | DBSR is read-workload oriented.                                                                               | Q10 is excluded from the first DBSR run.                            |
| A02 | Query frequencies are uniform unless explicit workload weights are available. | FIBEN benchmark inputs do not currently define DBSR-style query frequencies.                                  | Utility ranking is not frequency-biased in the first version.       |
| A03 | The materialization layer is separate from DBSR core.                         | DBSR recommends document structures and query plans; MongoDB loading is needed only for empirical comparison. | Prevents confusing DBSR algorithm with experimental implementation. |
| A04 | DBSR outputs are not generated from SchemaLens G0--G9.                        | The baseline must be faithful, not SchemaLens-inspired.                                                       | G0--G9 may only be used later for interpretation, not generation.   |

## Comparison metrics

For each query and scale:

```text
regret = (p95_method - p95_best_observed) / p95_best_observed
```

Near-best means:

```text
p95_method <= 1.05 * p95_best_observed
```

Main reported metrics:

* hot-run p95 latency;
* average latency;
* median latency;
* p99 latency;
* documents returned or written, when available;
* regret;
* top-1 preservation;
* near-best preservation with a 5% threshold;
* winner by query and scale.

## Anonymization rules

Do not commit:

* raw FIBEN data files;
* MongoDB dumps;
* local absolute paths;
* machine usernames;
* credentials;
* private repository URLs;
* reviewer comments with identifying metadata;
* paper PDFs containing author-identifying information;
* copied source code from third-party repositories unless license handling is explicitly documented.

Safe to commit:

* implementation source code written for this repository;
* small JSON/CSV metadata files generated from public schema/workload descriptions;
* aggregate benchmark results;
* query-plan summaries;
* LaTeX tables;
* README and reproduction instructions.

## Current status

Scaffold created. No DBSR algorithm code has been implemented yet.

Next step: implement the FIBEN input adapter to generate `dbsr_input_model.json` and `dbsr_workload.json`.


## Progress log

### Phase 0 — DBSR implementation scaffold

Status: completed.

This phase created an isolated `DBSR_implementation/` folder for the DBSR baseline implementation. The goal is to keep DBSR separate from the existing SchemaLens implementation and avoid treating DBSR as a direct mapping to SchemaLens G0--G9 templates.

Created structure:

```text
DBSR_implementation/
  input/fiben/
  src/dbsr_core/
  src/fiben_adapter/
  src/materialization/
  src/analysis/
  generated/fiben/
  benchmark/fiben/
  results/fiben/
  docs/
```

Main decisions:

* DBSR will be implemented as an independent related-work baseline.
* DBSR generation must not use SchemaLens G0--G9 templates, winners, p95 values, or activation scores.
* MongoDB physical loading will be treated as a materialization layer, not as part of the DBSR core algorithm.
* The implementation must record every missing paper detail as an implementation assumption.
* The branch will remain a working branch until the DBSR comparison is complete.

### Phase 1a — FIBEN input adapter

Status: completed.

Created script:

```text
DBSR_implementation/src/fiben_adapter/build_fiben_dbsr_input.py
```

Generated files:

```text
DBSR_implementation/generated/fiben/dbsr_input_model.json
DBSR_implementation/generated/fiben/dbsr_workload.json
```

The adapter builds a first DBSR input model for FIBEN with:

* FIBEN entities;
* source views;
* primary keys;
* relationship hints;
* DBSR run configuration;
* initial read workload draft for Q1--Q9.

The first workload file includes 9 read queries:

```text
Q1_CompanyProfileIBM
Q2_CompanyWithIndustryCountryAndListedSecurities
Q3_SecuritiesHeldInEachFinancialServiceAccount
Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity
Q5_ReportsAndMetricDataOfCompany
Q6_TechUSListedSecuritiesWithHighLastTradedValue
Q7_PersonsWhoBoughtMoreIBMThanSold
Q8_IBMTransactionsBelowAverageSellingPrice
Q9_PersonsWhoBoughtAndSoldSameStock
```

Important methodological note:

The adapter uses the existing FIBEN benchmark plan only to bootstrap query metadata. It does not use SchemaLens winners, p95 values, G0--G9 selection, regret, or benchmark outcomes to generate DBSR inputs.

All generated query sequences are marked as draft and require manual review before DBSR schema generation.

### Phase 1b — Manual DBSR query-sequence review

Status: in progress.

Planned/created files:

```text
DBSR_implementation/input/fiben/query_sequence_overrides.json
DBSR_implementation/src/fiben_adapter/apply_query_sequence_overrides.py
DBSR_implementation/generated/fiben/dbsr_workload_reviewed.json
```

Purpose:

The automatically inferred workload is only a bootstrap artifact. DBSR requires explicit read join sequences. Therefore, the manual override file defines reviewed DBSR sequences for Q1--Q9, such as:

```text
Q2:
Corporation -> Industry
Corporation -> Country
Corporation -> Security -> ListedSecurity
```

The reviewed workload will preserve the automatically inferred sequence for traceability, but DBSR generation should use the manually reviewed `dbsr_sequences`.

### Current next step

Before implementing the DBSR core, validate and commit Phase 1a and Phase 1b artifacts.

Required validation commands:

```bash
python -m py_compile DBSR_implementation/src/fiben_adapter/build_fiben_dbsr_input.py
python -m json.tool DBSR_implementation/generated/fiben/dbsr_input_model.json > /tmp/dbsr_input_model_check.json
python -m json.tool DBSR_implementation/generated/fiben/dbsr_workload.json > /tmp/dbsr_workload_check.json
grep -RInE "personal_name|personal_email|local_username|/home/|/afs/|password|token|secret|credential" DBSR_implementation || true
```

After Phase 1b:

```bash
python -m py_compile DBSR_implementation/src/fiben_adapter/apply_query_sequence_overrides.py
python -m json.tool DBSR_implementation/generated/fiben/dbsr_workload_reviewed.json > /tmp/dbsr_workload_reviewed_check.json
grep -n '"status": "manual_sequence_reviewed_draft"' DBSR_implementation/generated/fiben/dbsr_workload_reviewed.json | wc -l
```

Expected reviewed read queries:

```text
9
```

### Phase 1b — Manual DBSR query-sequence review

Status: completed.

Created files:

```text
DBSR_implementation/input/fiben/query_sequence_overrides.json
DBSR_implementation/src/fiben_adapter/apply_query_sequence_overrides.py
DBSR_implementation/generated/fiben/dbsr_workload_reviewed.json
```

This phase reviewed the automatically inferred FIBEN read workload and replaced the draft single-sequence representation with explicit DBSR-style read join sequences.

The override file defines reviewed draft sequences for Q1--Q9. These sequences are still independent from SchemaLens G0--G9 and are intended to represent DBSR workload inputs.

Validation result:

```text
Overrides applied: 9
Queries without override: 0
Reviewed workload queries marked as manual_sequence_reviewed_draft: 9
```

The reviewed workload keeps the automatically inferred sequence in `dbsr_sequence_inferred` for traceability, but DBSR generation should use the manually reviewed `dbsr_sequences`.

Important limitation:

The sequences are reviewed drafts based on FIBEN query names and known conceptual paths. Before final benchmarking, each sequence should still be checked against the exact FIBEN query implementation.

Current generated workload:

```text
DBSR_implementation/generated/fiben/dbsr_workload_reviewed.json
```

Next phase:

Implement the DBSR core model structures:

```text
DBSR_implementation/src/dbsr_core/model.py
DBSR_implementation/src/dbsr_core/document_tree.py
DBSR_implementation/src/dbsr_core/query_plan.py
DBSR_implementation/src/dbsr_core/merge_rules.py
```

The goal of the next phase is not yet to benchmark MongoDB. The next phase only implements the internal DBSR representation of entities, relationships, document trees, query sequences, and query plans.

## Phase 2a — DBSR core representation and initial query plans

Status: completed.

### Created core files

```text
DBSR_implementation/src/dbsr_core/__init__.py
DBSR_implementation/src/dbsr_core/model.py
DBSR_implementation/src/dbsr_core/document_tree.py
DBSR_implementation/src/dbsr_core/query_plan.py
DBSR_implementation/src/dbsr_core/merge_rules.py
```

### Created FIBEN helper script

```text
DBSR_implementation/src/fiben_adapter/build_initial_dbsr_plans.py
```

### Generated initial DBSR artifacts

```text
DBSR_implementation/generated/fiben/dbsr_initial_documents.csv
DBSR_implementation/generated/fiben/dbsr_initial_query_plans.csv
DBSR_implementation/generated/fiben/dbsr_initial_plan_summary.json
```

### Validation result

```text
Sequences loaded: 15
Initial documents: 12
Initial query plans: 15
Max initial plan steps: 6
```

### Interpretation

The 15 sequences come from the manually reviewed DBSR read workload for FIBEN Q1--Q9. Some queries are decomposed into multiple read join sequences, such as Q2, Q6, Q7, Q8, and Q9.

The 12 initial documents correspond to the unique single-level entities touched by the reviewed workload:

```text
Corporation
Country
FinancialReport
FinancialServiceAccount
Holding
Industry
ListedSecurity
Person
ReportElement
Security
StatementElement
Transaction
```

The largest initial query plan is Q4, with 6 steps:

```text
Person -> FinancialServiceAccount -> Holding -> ListedSecurity -> Security -> Corporation
```

This phase follows the DBSR bottom-up process: it starts from single-level document structures and initial query plans before applying iterative document merges, pruning, and utility ranking.

## Phase 2a correction — Transaction subtype paths

During initial path validation, Q7, Q8, and Q9 failed because the reviewed sequences used `BuyTransaction` and `SellTransaction` as direct nodes between `FinancialServiceAccount` and `ListedSecurity`.

The DBSR input model represents the physical relationship path as:

```text
FinancialServiceAccount -> Transaction -> ListedSecurity
```

Therefore, `BuyTransaction` and `SellTransaction` are represented in the reviewed workload as subtype/filter conditions over `Transaction`, not as separate relationship edges.

Affected queries:

```text
Q7_PersonsWhoBoughtMoreIBMThanSold
Q8_IBMTransactionsBelowAverageSellingPrice
Q9_PersonsWhoBoughtAndSoldSameStock
```

This is recorded as an implementation assumption in:

```text
DBSR_implementation/input/fiben/query_sequence_overrides.json
```

### Next phase

Implement the first iterative DBSR generator loop:

```text
1. Pop QueryPlanStack.
2. Optimize query plan by merging adjacent document structures.
3. Generate new documents.
4. Generate shortened query plans.
5. Notify/rewrite relevant query plans.
6. Stop when stack is empty or max_iterations is reached.
```

## Phase 2b — First iterative DBSR generator loop

Status: completed.

### Created files

```text
DBSR_implementation/src/dbsr_core/generator.py
DBSR_implementation/src/fiben_adapter/run_dbsr_generator.py
```

### Updated files

```text
DBSR_implementation/src/dbsr_core/query_plan.py
DBSR_implementation/src/dbsr_core/merge_rules.py
```

### Generated artifacts

```text
DBSR_implementation/generated/fiben/dbsr_generated_documents.csv
DBSR_implementation/generated/fiben/dbsr_generated_query_plans.csv
DBSR_implementation/generated/fiben/dbsr_generation_summary.json
```

### Purpose

This phase implements the first iterative DBSR generator loop. Starting from the initial single-level query plans, the generator repeatedly tries to merge adjacent document structures, creates larger document trees, and generates shortened query plans.

### Current implementation assumptions

```text
1. This phase implements an iterative per-plan merge loop.
2. It does not yet implement full DBSR global notification of all relevant query plans when a novel document is generated.
3. It does not yet implement cost-based pruning.
4. It does not yet implement document utility ranking.
5. DBSR MaxDim height is interpreted as document-tree height in nodes.
```

### Next phase

Implement cost model, query-plan pruning, and first document utility ranking.

Expected next outputs:

```text
DBSR_implementation/generated/fiben/dbsr_pruned_query_plans.csv
DBSR_implementation/generated/fiben/dbsr_document_utility_matrix.csv
DBSR_implementation/generated/fiben/dbsr_ranked_schemas.csv
```

## Phase 2c — Structural cost, pruning, and first utility ranking

Status: completed.

### Created files

```text
DBSR_implementation/src/dbsr_core/cost_model.py
DBSR_implementation/src/dbsr_core/pruning.py
DBSR_implementation/src/dbsr_core/utility.py
DBSR_implementation/src/fiben_adapter/rank_dbsr_candidates.py
```

### Generated artifacts

```text
DBSR_implementation/generated/fiben/dbsr_scored_query_plans.csv
DBSR_implementation/generated/fiben/dbsr_pruned_query_plans.csv
DBSR_implementation/generated/fiben/dbsr_document_utility_matrix.csv
DBSR_implementation/generated/fiben/dbsr_ranked_schemas.csv
DBSR_implementation/generated/fiben/dbsr_recommended_documents.csv
DBSR_implementation/generated/fiben/dbsr_ranking_summary.json
```

### Validation result

```text
Input query plans: 90
Scored query plans: 90
Pruned query plans: 57
Utility matrix rows: 127
Ranked documents: 35
Recommended documents: 10
Near-best cost ratio: 1.2
Max plans per sequence: 5
Top-k recommended documents: 10
```

### Purpose

This phase adds the first ranking layer after the iterative DBSR generator. The previous phase generated many possible query plans and document trees. This phase assigns a structural proxy cost to each query plan, prunes weaker plans, builds a document utility matrix, and produces a first ranking of recommended document structures.

### Current implementation assumptions

```text
1. This is a structural proxy cost, not the final DBSR cost model.
2. The cost rewards shorter query plans.
3. The cost penalizes larger, deeper, and wider document trees.
4. Cardinality, selectivity, physical object size, and MongoDB execution statistics are not used yet.
5. Document utility is aggregated from pruned query plans.
6. Full schema assembly from ranked documents is deferred to a later phase.
```

### Next phase

Implement statistics-aware costing for FIBEN.

Expected next inputs:

```text
FIBEN collection cardinalities by scale
Average object/document sizes by scale
Estimated selected records per query path
Optional MongoDB executionStats from existing query-plan scripts
```

Expected next outputs:

```text
DBSR_implementation/generated/fiben/dbsr_statistics_sf1.json
DBSR_implementation/generated/fiben/dbsr_statistics_sf10.json
DBSR_implementation/generated/fiben/dbsr_statistics_sf30.json
DBSR_implementation/generated/fiben/dbsr_stats_aware_ranked_schemas.csv
```

## Phase 2d — Offline statistics contract for DBSR costing

Status: completed as an offline contract.

### Created files

```text
DBSR_implementation/input/fiben/statistics_template.json
DBSR_implementation/src/fiben_adapter/validate_fiben_statistics.py
```

### Purpose

The original plan for this phase was to extract MongoDB collection statistics with `collStats`. However, the existing FIBEN benchmark databases are not available in the current repository environment because the previous benchmark workflow created temporary MongoDB databases, measured p95 latency, and dropped those databases after the run.

Therefore, this phase does not report statistics-aware DBSR ranking yet. Instead, it defines the offline statistics contract that future DBSR materialization and benchmark scripts must produce before any temporary database is removed.

### Statistics contract

```text
DBSR_implementation/input/fiben/statistics_template.json
```

The template defines the expected per-entity/per-collection fields:

```text
entity
collection
count
avg_object_size_bytes
size_bytes
storage_size_bytes
total_index_size_bytes
statistics_status
```

The template intentionally contains `null` values for measured quantities because no active benchmark database is available at this point.

### Validation command

```text
python DBSR_implementation/src/fiben_adapter/validate_fiben_statistics.py \
  --statistics DBSR_implementation/input/fiben/statistics_template.json \
  --allow-template
```

Expected validation result:

```text
Statistics validation passed.
Dataset: FIBEN
Scale: sf1
Collections: 12
Status: template_not_measured
```

### Implementation assumption

```text
Statistics-aware DBSR ranking must only be reported after real collection statistics are captured during DBSR materialization or benchmark execution.
```

### Next phase

Implement the DBSR schema assembly step from ranked documents.

The next phase should produce a first recommended DBSR schema manifest, independent from SchemaLens G0--G9:

```text
DBSR_implementation/generated/fiben/dbsr_schema_manifest_structural.json
DBSR_implementation/generated/fiben/dbsr_schema_manifest_structural.csv
```

Later, when DBSR schemas are materialized in MongoDB, the benchmark runner must capture real statistics files such as:

```text
DBSR_implementation/generated/fiben/dbsr_statistics_sf1.json
DBSR_implementation/generated/fiben/dbsr_statistics_sf10.json
DBSR_implementation/generated/fiben/dbsr_statistics_sf30.json
```

before dropping any temporary database.

## Phase 2e — Structural DBSR schema assembly with executable coverage closure

Status: completed.

### Created or updated files

```text
DBSR_implementation/src/dbsr_core/schema_assembly.py
DBSR_implementation/src/fiben_adapter/assemble_dbsr_schema.py
```

### Generated artifacts

```text
DBSR_implementation/generated/fiben/dbsr_schema_manifest_structural.json
DBSR_implementation/generated/fiben/dbsr_schema_manifest_structural.csv
DBSR_implementation/generated/fiben/dbsr_schema_manifest_structural_summary.json
```

### Validation result

```text
Selected documents: 15
Initial top-k documents: 10
Added documents for executable coverage: 5
Partial covered queries: 9
Partial covered sequences: 15
Executable queries: 9
Executable sequences: 15/15
Non-executable sequences: 0
Total selected utility: 1.403427303847
```

### Purpose

This phase assembles the first structural DBSR schema manifest from the ranked document utilities. The manifest starts with the top-k ranked documents and then applies an executable-coverage closure step.

The closure step checks whether each reviewed workload sequence has at least one complete pruned query plan whose documents are all selected. If a sequence is not executable, the missing documents from the best pruned plan for that sequence are added to the manifest.

### Important methodological correction

This phase distinguishes partial document coverage from executable sequence coverage.

Partial coverage means that at least one selected document is useful for a query. Executable coverage means that a full query sequence can be executed using only selected documents. The final manifest reports executable coverage for all 15 reviewed FIBEN read-workload sequences.

### Current implementation assumptions

```text
1. The manifest starts from dbsr_ranked_schemas.csv.
2. The default policy selects the top-k ranked documents.
3. The executable-coverage closure uses dbsr_pruned_query_plans.csv.
4. A sequence is executable when at least one pruned query plan can be expressed using only selected documents.
5. Physical materialization is deferred to a later phase.
6. The schema manifest is generated independently from SchemaLens G0-G9 templates.
```

## Phase 2f — DBSR structural materialization plan

Status: completed.

### Created files

```text
DBSR_implementation/src/materialization/__init__.py
DBSR_implementation/src/materialization/materialization_plan.py
DBSR_implementation/src/fiben_adapter/build_dbsr_materialization_plan.py
```

### Generated artifacts

```text
DBSR_implementation/generated/fiben/dbsr_materialization_plan_structural.json
DBSR_implementation/generated/fiben/dbsr_materialization_plan_structural.csv
DBSR_implementation/generated/fiben/dbsr_materialization_plan_structural_summary.json
```

### Validation result

```text
Target collections: 15
Embedding steps total: 21
Missing relationships total: 0
Source views used: 12
Plan only: True
```

### Purpose

This phase creates a materialization plan for the structural DBSR schema manifest. It defines how each selected DBSR document structure can later be loaded into MongoDB collections.

The plan records the target collection name, root entity, source views, primary keys, embedding steps, relationship identifiers, join columns, and materialization status for each selected document structure.

### Important methodological note

This phase does not load data and does not create MongoDB collections. It only prepares the physical loading plan. This keeps the DBSR algorithmic recommendation separate from the experimental MongoDB materialization layer.

### Current implementation assumptions

```text
1. Each selected DBSR document signature becomes one target collection in the first materialization plan.
2. Overlapping target collections are allowed at this stage.
3. Root scans and nested child lookups will be implemented by a later physical loader.
4. The loader must capture collection statistics before dropping temporary benchmark databases.
5. The materialization plan is generated independently from SchemaLens G0-G9 templates.
```

### Next phase

Implement the first MongoDB loader skeleton for the DBSR materialization plan.

Expected next outputs:

```text
DBSR_implementation/benchmark/fiben/run_dbsr_materialization_smoke_test.py
DBSR_implementation/generated/fiben/dbsr_materialization_smoke_manifest.json
```

The smoke test should load a tiny subset or dry-run the operations before full-scale benchmarking.

## Phase 2g — DBSR materialization loader smoke test

Status: completed.

### Created files

```text
DBSR_implementation/benchmark/fiben/run_dbsr_materialization_smoke_test.py
```

### Generated artifacts

```text
DBSR_implementation/generated/fiben/dbsr_materialization_smoke_manifest.json
DBSR_implementation/generated/fiben/dbsr_materialization_smoke_manifest.csv
DBSR_implementation/generated/fiben/dbsr_materialization_smoke_operations.csv
```

### Validation result

```text
Smoke status: passed
Target collections: 15
Passed collections: 15
Failed collections: 0
Warnings: 0
Dry-run operations: 36
Mongo access: False
Benchmark execution: False
```

### Purpose

This phase validates the DBSR structural materialization plan without connecting to MongoDB. It checks whether each planned target collection has the required root entity, source view, primary key, source collections, embedding steps, and relationship metadata.

### Important methodological note

This is a dry-run smoke test only. It does not load data, does not create MongoDB collections, and does not measure p95 latency.

The official DBSR materialization and benchmark must later be executed on the same server used for the SchemaLens benchmark, after the current query-plan experiments finish, to keep the comparison fair.

### Current implementation assumptions

```text
1. The smoke test reads dbsr_materialization_plan_structural.json.
2. It validates the logical loading plan for each selected DBSR collection.
3. It produces dry-run operations, but no data is loaded.
4. MongoDB access is intentionally disabled in this phase.
5. Benchmark execution is intentionally disabled in this phase.
```

### Next phase

Implement the first real MongoDB materialization loader, but keep it disabled until the benchmark server is available.

Expected next outputs:

```text
DBSR_implementation/benchmark/fiben/run_dbsr_materialization_loader.py
DBSR_implementation/generated/fiben/dbsr_loader_execution_manifest_sf1.json
```

## Phase 2h — DBSR MongoDB materialization loader skeleton

Status: completed in dry-run mode.

### Created files

```text
DBSR_implementation/benchmark/fiben/run_dbsr_materialization_loader.py
```

### Generated artifacts

```text
DBSR_implementation/generated/fiben/dbsr_loader_execution_manifest_sf1_dry_run.json
```

### Validation result

```text
Loader status: dry_run
Mongo access: False
Benchmark execution: False
Target collections: 15
Completed collections: 15
Failed collections: 0
Root limit: 10
Child limit: 20
```

### Purpose

This phase adds the first real MongoDB materialization loader skeleton for the DBSR structural materialization plan. The loader is safe by default: it runs in dry-run mode unless `--execute` is explicitly provided.

### Important methodological note

This phase does not run the official benchmark. The dry-run output confirms that the loader can read the 15-collection DBSR materialization plan and prepare execution metadata without accessing MongoDB.

The real materialization must later run on the same server used for the SchemaLens benchmark. That official execution should capture collection statistics before any temporary database is dropped.

### Safe execution policy

```text
Default mode:
  no MongoDB connection
  no data loading
  no benchmark execution

Execution mode:
  requires --execute
  requires --mongo-db
  may optionally use --drop-target
```

### Next phase

Wait until the benchmark server is available, then run a small executed smoke materialization over FIBEN SF1 before full p95 benchmarking.

## Phase 2i — Executed DBSR loader smoke test with synthetic FIBEN source DB

Status: completed.

### Created files

```text
DBSR_implementation/benchmark/fiben/create_synthetic_fiben_source_db.py
```

### Generated artifacts

```text
DBSR_implementation/generated/fiben/dbsr_synthetic_source_manifest_sf1.json
DBSR_implementation/generated/fiben/dbsr_loader_execution_manifest_sf1_executed.json
```

### Synthetic source validation

```text
Synthetic source status: executed
Mongo access: True
Mongo database: dbsr_fiben_synthetic_smoke
Collections prepared: 12
Documents prepared: 36
Official benchmark: False
```

### Executed loader validation

```text
Loader status: executed
Mongo access: True
Benchmark execution: False
Target collections: 15
Completed collections: 15
Failed collections: 0
Root limit: 100
Child limit: 100
Drop target: True
```

### Purpose

This phase validates the DBSR materialization loader with a synthetic minimal FIBEN source database. Since no real FIBEN MongoDB database was available on the server, the synthetic source database was created only to test the loader execution path.

The test confirms that the loader can connect to MongoDB, read source collections, create DBSR target collections, insert materialized documents, and generate an execution manifest.

### Important methodological note

This is not an official benchmark and must not be used for p95 comparison. The synthetic database is minimal and only supports loader validation.

The official DBSR-vs-SchemaLens comparison must later use the real FIBEN scale-factor data on the same server used for the SchemaLens benchmark.

### Current implementation assumptions

```text
1. The synthetic source database is only for executed smoke testing.
2. It is not a real FIBEN scale-factor database.
3. It must not be used for latency, regret, or p95 comparison.
4. The official benchmark requires real FIBEN data.
5. The official benchmark must capture collection statistics before temporary databases are dropped.
```

### Next phase

Prepare the official DBSR benchmark runner for FIBEN Q1--Q9, but keep execution blocked until the real FIBEN source data is available.

## Phase 2j — Official FIBEN full source load and limited DBSR materialization

Status: completed.

### Created diagnostic and loading files

```text
DBSR_implementation/benchmark/fiben/probe_official_fiben_files.py
DBSR_implementation/benchmark/fiben/load_official_fiben_source_db.py
DBSR_implementation/benchmark/fiben/check_official_fiben_join_coverage.py
DBSR_implementation/benchmark/fiben/find_fiben_report_statement_join.py
DBSR_implementation/benchmark/fiben/find_fiben_element_id_across_files.py
DBSR_implementation/benchmark/fiben/check_report_statement_full_intersection.py
```

### Generated artifacts

```text
DBSR_implementation/generated/fiben/dbsr_official_fiben_source_load_manifest_sf1_dry_run.json
DBSR_implementation/generated/fiben/dbsr_official_fiben_source_load_manifest_sf1_executed.json
DBSR_implementation/generated/fiben/dbsr_loader_execution_manifest_sf1_official_smoke_executed.json
DBSR_implementation/generated/fiben/dbsr_official_fiben_source_load_manifest_sf1_full_source_executed.json
DBSR_implementation/generated/fiben/dbsr_loader_execution_manifest_sf1_full_source_limited_materialization_executed.json
DBSR_implementation/generated/fiben/dbsr_official_fiben_csv_join_coverage.json
DBSR_implementation/generated/fiben/dbsr_report_statement_full_intersection.json
```

### Full source load validation

```text
Source load status: executed
Mongo access: True
Mongo database: dbsr_fiben_sf1_source_full
Entities attempted: 12
Entities loaded: 12
Missing files: 0
Total rows loaded: 9802537
Max rows per file: 0
```

### Source collection counts

```text
fiben_corporations: 2324
fiben_countries: 249
fiben_financial_service_accounts: 97270
fiben_holdings: 534473
fiben_industries: 452
fiben_listed_securities: 2745
fiben_persons: 50100
fiben_report_elements: 8120084
fiben_reports: 48301
fiben_securities: 2745
fiben_statement_elements: 443794
fiben_transactions: 500000
```

### Limited DBSR materialization validation

```text
Loader status: executed
Mongo access: True
Benchmark execution: False
Target collections: 15
Completed collections: 15
Failed collections: 0
Root limit: 100
Child limit: 100
Drop target: True
```

### Embedding validation over full source

```text
dbsr_rank02_transaction_listedsecurity -> listedSecurity=1
dbsr_rank07_financialserviceaccount_holding_listedsecurity -> holding=2
dbsr_rank08_corporation_security_listedsecurity -> security=1
dbsr_rank09_financialserviceaccount_transaction_listedsecurity -> transaction=2
dbsr_rank13_financialreport_reportelement_statementelement -> reportElement=100
```

### Report-statement full intersection

```text
Report elements total: 8120084
Statement distinct ids: 443794
Matched report elements: 443794
Match ratio: 0.054653868112694404
```

### Purpose

This phase validates the official FIBEN source loading path for DBSR. The full source load uses the real headerless FIBEN CSV files and assigns the column names required by the DBSR input model and materialization plan.

It also validates a limited DBSR materialization over the full source database. This confirms that the DBSR loader can materialize root documents and nested documents over real FIBEN data, including the Q5 path from FinancialReport to ReportElement and StatementElement.

### Important methodological note

This is still not the p95 benchmark. The DBSR materialization was limited to 100 root documents and 100 child documents per nesting step. The next phase must run a cardinality and BSON-size preflight before full materialization to avoid MongoDB document-size failures.

### Next phase

Run full-materialization preflight checks, then run full DBSR materialization if the target documents are safe.

## Phase 2k — Full DBSR materialization over official FIBEN source

Status: completed.

### Created files

```text
DBSR_implementation/benchmark/fiben/run_dbsr_full_materialization_preflight.py
```

### Generated artifacts

```text
DBSR_implementation/generated/fiben/dbsr_full_materialization_preflight_sf1_full_source.json
DBSR_implementation/generated/fiben/dbsr_full_materialization_preflight_sf1_full_source.csv
DBSR_implementation/generated/fiben/dbsr_loader_execution_manifest_sf1_full_materialization_executed.json
DBSR_implementation/generated/fiben/dbsr_full_materialization_collection_stats_sf1.json
```

### Preflight validation

```text
Check type: full_materialization_preflight
Mongo database: dbsr_fiben_sf1_source_full
Threshold MB: 16.0
Risk counts: {'low_risk': 15}
High-risk collections: 0
```

### Full materialization validation

```text
Loader status: executed
Mongo access: True
Benchmark execution: False
Target collections: 15
Completed collections: 15
Failed collections: 0
Root limit: 0
Child limit: 0
Drop target: True
```

### Inserted documents by DBSR target collection

```text
dbsr_rank01_listedsecurity: 2745 docs, 0.033594 s
dbsr_rank02_transaction_listedsecurity: 500000 docs, 92.840086 s
dbsr_rank03_corporation: 2324 docs, 0.024924 s
dbsr_rank04_person: 50100 docs, 0.355258 s
dbsr_rank05_corporation_country: 2324 docs, 0.483705 s
dbsr_rank06_corporation_industry: 2324 docs, 0.37986 s
dbsr_rank07_financialserviceaccount_holding_listedsecurity: 97270 docs, 116.657993 s
dbsr_rank08_corporation_security_listedsecurity: 2324 docs, 0.969133 s
dbsr_rank09_financialserviceaccount_transaction_listedsecurity: 97270 docs, 107.732933 s
dbsr_rank10_person_financialserviceaccount_transaction: 50100 docs, 30.807044 s
dbsr_rank11_person_financialserviceaccount_holding: 50100 docs, 29.353388 s
dbsr_rank12_listedsecurity_security_corporation: 2745 docs, 0.890311 s
dbsr_rank13_financialreport_reportelement_statementelement: 48301 docs, 1381.565382 s
dbsr_rank14_security_corporation_industry: 2745 docs, 0.960531 s
dbsr_rank15_security_corporation_country: 2745 docs, 1.07106 s
```

### MongoDB collection statistics after full materialization

```text
dbsr_rank01_listedsecurity: count=2745, avgObjSize=210, size=577172, storageSize=192512
dbsr_rank02_transaction_listedsecurity: count=500000, avgObjSize=519, size=259537010, storageSize=73129984
dbsr_rank03_corporation: count=2324, avgObjSize=176, size=409769, storageSize=147456
dbsr_rank04_person: count=50100, avgObjSize=263, size=13213147, storageSize=4669440
dbsr_rank05_corporation_country: count=2324, avgObjSize=315, size=733796, storageSize=188416
dbsr_rank06_corporation_industry: count=2324, avgObjSize=444, size=1032520, storageSize=282624
dbsr_rank07_financialserviceaccount_holding_listedsecurity: count=97270, avgObjSize=2596, size=252602760, storageSize=70995968
dbsr_rank08_corporation_security_listedsecurity: count=2324, avgObjSize=645, size=1499437, storageSize=397312
dbsr_rank09_financialserviceaccount_transaction_listedsecurity: count=97270, avgObjSize=2921, size=284189801, storageSize=80048128
dbsr_rank10_person_financialserviceaccount_transaction: count=50100, avgObjSize=3634, size=182070748, storageSize=50987008
dbsr_rank11_person_financialserviceaccount_holding: count=50100, avgObjSize=2842, size=142403421, storageSize=39907328
dbsr_rank12_listedsecurity_security_corporation: count=2745, avgObjSize=573, size=1573094, storageSize=405504
dbsr_rank13_financialreport_reportelement_statementelement: count=48301, avgObjSize=29215, size=1411118674, storageSize=267341824
dbsr_rank14_security_corporation_industry: count=2745, avgObjSize=614, size=1685752, storageSize=413696
dbsr_rank15_security_corporation_country: count=2745, avgObjSize=484, size=1329153, storageSize=278528
```

### Purpose

This phase physically materializes the full DBSR-recommended document structures over the official FIBEN source database. Unlike the previous smoke tests, this run uses no root or child limits.

The preflight check estimated document-size risk before execution and found no high-risk collection under the MongoDB 16 MB document limit. The full materialization then completed successfully for all 15 DBSR target collections.

### Important methodological note

This phase is still not the p95 benchmark. It validates that the DBSR baseline can be physically materialized in MongoDB over the official FIBEN source data.

The next phase must implement and run the DBSR query executor for FIBEN Q1--Q9 over the materialized `dbsr_rank*` collections, then calculate hot p95 and compare with the existing SchemaLens results.

### Next phase

Prepare the DBSR FIBEN Q1--Q9 query executor and benchmark runner.

## Phase 2l.1 — DBSR FIBEN query-parameter probe

Status: completed.

### Created files

```text
DBSR_implementation/benchmark/fiben/probe_dbsr_fiben_query_parameters.py
```

### Generated artifacts

```text
DBSR_implementation/generated/fiben/dbsr_fiben_query_parameter_probe_sf1.json
```

### Validation result

```text
Mongo database: dbsr_fiben_sf1_source_full
Collections counted: 15
Missing parameter samples: 0
Q1_CompanyProfileIBM: returned_sample=True
Q2_CompanyWithIndustryCountryAndListedSecurities: returned_sample=True
Q3_SecuritiesHeldInEachFinancialServiceAccount: returned_sample=True
Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity: returned_sample=True
Q5_ReportsAndMetricDataOfCompany: returned_sample=True
Q6_TechUSListedSecuritiesWithHighLastTradedValue: returned_sample=True
Q7_PersonsWhoBoughtMoreIBMThanSold: returned_sample=True
Q8_IBMTransactionsBelowAverageSellingPrice: returned_sample=True
Q9_PersonsWhoBoughtAndSoldSameStock: returned_sample=True
```

### Purpose

This phase selects real query parameters from the fully materialized DBSR FIBEN collections. It prepares the future Q1--Q9 DBSR query executor and avoids benchmark runs with invalid or zero-result parameters.

### Important methodological note

This probe does not execute the benchmark and does not measure p95. It only selects valid parameters from the materialized DBSR collections and does not affect schema selection.

### Next phase

Implement the DBSR FIBEN Q1--Q9 query executor and run a one-repetition smoke benchmark.

## Phase 2l — DBSR FIBEN parameter probe, secondary indexes, and smoke benchmark

Status: completed.

### Created files

```text
DBSR_implementation/benchmark/fiben/probe_dbsr_fiben_query_parameters.py
DBSR_implementation/benchmark/fiben/create_dbsr_fiben_indexes.py
DBSR_implementation/benchmark/fiben/run_dbsr_fiben_query_benchmark.py
```

### Generated artifacts

```text
DBSR_implementation/generated/fiben/dbsr_fiben_query_parameter_probe_sf1.json
DBSR_implementation/generated/fiben/dbsr_fiben_index_manifest_sf1.json
DBSR_implementation/results/fiben/dbsr_fiben_query_benchmark_raw_sf1_smoke.csv
DBSR_implementation/results/fiben/dbsr_fiben_query_benchmark_aggregate_sf1_smoke.csv
DBSR_implementation/results/fiben/dbsr_fiben_query_benchmark_manifest_sf1_smoke.json
DBSR_implementation/results/fiben/dbsr_fiben_query_benchmark_raw_sf1_smoke_indexed.csv
DBSR_implementation/results/fiben/dbsr_fiben_query_benchmark_aggregate_sf1_smoke_indexed.csv
DBSR_implementation/results/fiben/dbsr_fiben_query_benchmark_manifest_sf1_smoke_indexed.json
```

### Query parameter probe validation

```text
Mongo database: dbsr_fiben_sf1_source_full
Missing parameter samples: 0
Q9 matched person: 400000008607
Q9 matched stock: 1004673
Q9 matched tx count: 3
```

### DBSR secondary index validation

```text
Collections indexed: 15
Indexes requested: 44
Indexes created or existing: 44
Indexes failed: 0
```

### Indexed smoke benchmark validation

```text
Mongo database: dbsr_fiben_sf1_source_full
Warmup runs: 1
Hot runs: 1
Failed executions: 0
Official benchmark: False
```

### Indexed smoke hot p95 summary

```text
Q1_CompanyProfileIBM: p95_ms=0.161751, returned=1
Q2_CompanyWithIndustryCountryAndListedSecurities: p95_ms=0.386507, returned=3
Q3_SecuritiesHeldInEachFinancialServiceAccount: p95_ms=0.153466, returned=3
Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity: p95_ms=0.395895, returned=5
Q5_ReportsAndMetricDataOfCompany: p95_ms=0.320933, returned=169
Q6_TechUSListedSecuritiesWithHighLastTradedValue: p95_ms=0.966398, returned=169
Q7_PersonsWhoBoughtMoreIBMThanSold: p95_ms=0.191196, returned=1
Q8_IBMTransactionsBelowAverageSellingPrice: p95_ms=1.244492, returned=101
Q9_PersonsWhoBoughtAndSoldSameStock: p95_ms=0.148754, returned=1
```

### Purpose

This phase prepares the DBSR FIBEN benchmark executor. It selects valid query parameters from the fully materialized DBSR collections, creates DBSR secondary indexes, and validates that Q1--Q9 execute successfully over the `dbsr_rank*` collections.

### Important methodological note

The smoke benchmark is not the official p95 comparison because it uses only one hot run. It only validates executor correctness, nonzero/valid parameters, and indexed execution before the official repeated benchmark.

### Next phase

Run the official DBSR FIBEN hot benchmark with a stable number of repetitions, then compare DBSR p95 against the existing SchemaLens FIBEN results.

## Phase 2m — Official DBSR FIBEN SF1 hot benchmark

Status: completed.

### Generated artifacts

```text
DBSR_implementation/results/fiben/dbsr_fiben_query_benchmark_raw_sf1_official_20hot.csv
DBSR_implementation/results/fiben/dbsr_fiben_query_benchmark_aggregate_sf1_official_20hot.csv
DBSR_implementation/results/fiben/dbsr_fiben_query_benchmark_manifest_sf1_official_20hot.json
```

### Benchmark configuration

```text
Mongo database: dbsr_fiben_sf1_source_full
Warmup runs: 3
Hot runs: 20
Failed executions: 0
Official benchmark: True
```

### Official hot p95 summary

```text
Q1_CompanyProfileIBM: p95_ms=0.261594, avg_ms=0.200904, p50_ms=0.190769, returned=1
Q2_CompanyWithIndustryCountryAndListedSecurities: p95_ms=1.068566, avg_ms=0.804227, p50_ms=0.729346, returned=3
Q3_SecuritiesHeldInEachFinancialServiceAccount: p95_ms=0.195253, avg_ms=0.190328, p50_ms=0.186936, returned=3
Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity: p95_ms=0.434546, avg_ms=0.419942, p50_ms=0.41881, returned=5
Q5_ReportsAndMetricDataOfCompany: p95_ms=0.344668, avg_ms=0.331832, p50_ms=0.329463, returned=169
Q6_TechUSListedSecuritiesWithHighLastTradedValue: p95_ms=1.255224, avg_ms=1.20689, p50_ms=1.174261, returned=169
Q7_PersonsWhoBoughtMoreIBMThanSold: p95_ms=0.244635, avg_ms=0.214408, p50_ms=0.208501, returned=1
Q8_IBMTransactionsBelowAverageSellingPrice: p95_ms=1.219266, avg_ms=1.189969, p50_ms=1.190768, returned=101
Q9_PersonsWhoBoughtAndSoldSameStock: p95_ms=0.25446, avg_ms=0.245584, p50_ms=0.244526, returned=1
```

### Purpose

This phase runs the official DBSR FIBEN SF1 hot benchmark over the fully materialized and indexed `dbsr_rank*` MongoDB collections.

### Important methodological note

This benchmark measures the DBSR baseline after faithful document-structure generation, physical MongoDB materialization, and DBSR secondary-index creation. It uses the materialized DBSR collections only and does not use SchemaLens activation outputs during execution.

### Next phase

Compare DBSR hot p95 against the existing SchemaLens FIBEN hot p95 results and compute per-query regret.
