# LDBC SNB faithful MongoDB physical materialization

This document describes the first reproducibility phase for the faithful MongoDB physical materialization of the LDBC SNB SchemaLens candidates.

The goal of this phase is to preserve the original SchemaLens evaluation logic while replacing the previous simplified candidate-execution layer with explicit MongoDB physical structures. The analytical matrix, activation rules, candidate identifiers, and benchmark groups are not changed.

## Methodological rule

SchemaLens uses three benchmark roles:

- `primary`: candidates directly activated by the dominant EER/workload pattern.
- `secondary_affected`: candidates retained because the query touches related structures, side effects, sharedness, volatility, or secondary access paths.
- `control`: comparison or baseline candidates used to evaluate whether the reduced space excluded a competitive alternative.

For metric computation:

- `A(Q) = primary + secondary_affected`.
- `control` candidates are benchmarked but are not counted as activated configurations for DSR.
- `best_overall` is computed over `primary + secondary_affected + control`.
- `best_activated` is computed over `primary + secondary_affected`.
- `best_primary` is computed over `primary` only.
- Top-1 preservation, near-best preservation, activated regret, and primary regret are computed against the broader benchmarked comparison space.

## Phase 1A: activated physical materialization

Phase 1A materialized the LDBC SNB SF0.1 candidates produced by the SchemaLens candidate-generation artifacts.

Output folder:

    analysis/generated/physical_materialization/ldbc_snb/sf0_1/phase1A_activated/

Main files:

    physical_materialization_manifest.csv
    physical_support_matrix.csv
    materialization_validation_summary.csv
    materialization_consolidated_summary.csv
    README_materialization_consolidated.md
    README_physical_materializations_by_query.md

Phase 1A result:

    total_candidates = 64
    ready_for_benchmark_true = 64
    not_ready = 0

Two warning cases were manually validated and treated as manifest/validation-summary recording issues rather than materialization failures:

    IS7 / G0
    IC5 / G0

The grouped INS run had one transient connection failure for `INS6 / G7`. This candidate was rerun in isolation and validated successfully.

## Phase 1B: control-expansion check

Phase 1B checked whether additional `control` candidates from the original candidate JSON were missing from the physical materialization.

Output folder:

    analysis/generated/physical_materialization/ldbc_snb/sf0_1/phase1B_control_plan_json/

Main files:

    candidate_inventory_from_json.csv
    sf0_1_control_expansion_plan.csv
    sf0_1_controls_to_materialize.csv
    sf0_1_activated_missing_unexpected.csv
    sf0_1_control_expansion_summary.csv
    README_control_expansion_plan.md

Phase 1B result:

    json_total_candidates = 64
    primary_candidates = 41
    secondary_affected_candidates = 22
    control_candidates = 1
    control_already_materialized = 1
    control_needs_materialization = 0
    activated_missing_unexpected = 0

Therefore, no extra control materialization was required for SF0.1. The single control candidate was already included in the 64 physically materialized candidates.

## Phase 1C: full comparison manifest

Phase 1C consolidated the final manifest used by the physical benchmark phase.

Output folder:

    analysis/generated/physical_materialization/ldbc_snb/sf0_1/phase1C_full_comparison/

Main files:

    physical_materialization_manifest.csv
    physical_support_matrix.csv
    full_comparison_manifest_summary.csv
    materialization_validation_summary.csv
    README_full_comparison_manifest.md
    README_physical_materializations_by_query.md

Phase 1C result:

    total_candidates = 64
    unique_candidates = 64
    primary = 41
    secondary_affected = 22
    control = 1
    activated_primary_plus_secondary = 63
    ready_for_benchmark_true = 64
    not_ready = 0

This final manifest is the input for the faithful physical benchmark runner.

## Reproduction scripts

The scripts used in this phase are stored in:

    benchmark/ldbc_snb/

Scripts:

    build_ldbc_snb_physical_materializations.py
    build_ldbc_snb_control_expansion_plan.py
    build_ldbc_snb_control_plan_from_json.py
    monitor_ldbc_mongo_resources.sh

The resource monitor is optional and does not modify MongoDB data or benchmark results. It records Docker/container state, memory usage, CPU usage, and disk usage to help diagnose infrastructure failures during materialization.

## Next phase

The next phase is to execute the physical benchmark and query-plan analysis using:

    analysis/generated/physical_materialization/ldbc_snb/sf0_1/phase1C_full_comparison/physical_materialization_manifest.csv

The benchmark runner must execute each candidate through its own candidate-specific physical MongoDB access path. For example, for IC7:

    G0 -> base referenced collections
    G3 -> ic7_g3_person_recent_liker_summary
    G4 -> ic7_g4_explicit_like_edges
    G6 -> ic7_g6_owner_liker_reverse_index

This ensures that the new experiment preserves the original SchemaLens evaluation logic while using faithful physical MongoDB materializations.
