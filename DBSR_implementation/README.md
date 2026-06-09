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
