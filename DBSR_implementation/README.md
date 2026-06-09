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
