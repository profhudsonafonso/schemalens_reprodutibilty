# IMDb Group C Query-Plan Results: QG4 and QG5

This document summarizes the MongoDB query-plan results for IMDb Group C.

Group C focuses on the associative and deep-traversal IMDb queries:

* `QG4_AllPersonsOfTypeForWatchItem`
* `QG5_AllPersonsForEpisodesOfSeries`

These queries are important because they involve the `WatchItem`, `Role`, `Person`, `Series`, and `Episode` structures. They are used to explain the associative family in SchemaLens, especially the behavior of `G4`, `G5`, and `G6`.

## Folder structure

The Group C results are stored in four folders:

* `group_C_roles_sf025/`
* `group_C_roles_sf050/`
* `group_C_roles_sf1_assoc_only/`
* `group_C_qg5_sf1_assoc_only_with_episodes/`

The first two folders contain full Group C runs for `sf0.25` and `sf0.5`.

The last two folders contain targeted `sf1` runs. They were necessary because the full `sf1` Group C run was repeatedly interrupted during the materialization of the external `roles` collection.

## Execution summary

### Full runs

The full Group C runs were completed for:

* `sf0.25`
* `sf0.5`

These runs include the selected configurations for QG4 and QG5 across the relevant query groups.

### Targeted sf1 runs

The full `sf1` Group C run was not completed because the process repeatedly stopped during materialization of the external `roles` collection. This happened before query-plan extraction, so it was a data-loading limitation rather than a query-plan failure.

To preserve the main associative evidence at `sf1`, we executed targeted runs for the main associative configurations:

* `watchitem_g4`
* `watchitem_g5`
* `watchitem_g6`

These configurations correspond to the associative family used to explain QG4 and QG5.

## sf1 QG4 run

The folder:

* `group_C_roles_sf1_assoc_only/`

contains the targeted `sf1` run for QG4 and QG5 with:

* `watchitem_g4`
* `watchitem_g5`
* `watchitem_g6`

In this run, the auxiliary collections `persons`, `roles`, and `episodes` were skipped.

This run is valid for QG4 because QG4 is an associative query over `WatchItem`, `Role`, and `Person`, and the relevant associative structures are materialized inside the `watchitems` candidate documents for `G4`, `G5`, and `G6`.

However, this first targeted run is not sufficient for QG5. The zero-returned diagnostics showed `EOF` over the `episodes` collection for QG5, because QG5 starts from the `Series`--`Episode` traversal and therefore requires the `episodes` collection to be loaded.

## sf1 QG5 run with episodes

The folder:

* `group_C_qg5_sf1_assoc_only_with_episodes/`

contains an additional targeted `sf1` run for QG5 with:

* `watchitem_g4`
* `watchitem_g5`
* `watchitem_g6`

In this run, the `episodes` collection was loaded, while `persons` and `roles` remained skipped.

This run completed successfully and did not produce failed or zero-returned rows. It validates QG5 for the main associative configurations at `sf1` without requiring the expensive external `roles` collection to be materialized.

## Reproducibility note

For `sf1`, the full external-reference run would require a more advanced execution mode, such as reusing an already materialized execution database or resuming a partially loaded base database. This engineering extension was not required for the current analysis because the main objective of Group C is to explain the associative configurations `G4`, `G5`, and `G6`.

The current results therefore provide:

* full Group C coverage for `sf0.25`;
* full Group C coverage for `sf0.5`;
* targeted associative coverage for QG4 at `sf1`;
* targeted associative coverage for QG5 at `sf1` with `episodes` loaded.

## Files

Each folder contains the corresponding query-plan outputs, renamed with a group/scale suffix.

Typical files include:

* `query_plan_summary_results_*.csv`
* `query_plan_component_results_*.csv`
* `query_plan_status_summary_*.csv`
* `benchmark_run_manifest_*.json`
* `execution_*.log`
* `selected_experiments_summary_*.csv`
* `scale_db_initialization_summary_*.csv`
* `collection_swap_summary_*.csv`

The folder `group_C_roles_sf1_assoc_only/` also includes a zero-returned diagnostic file documenting why QG5 required an additional run with `episodes` loaded.

Raw MongoDB `explain` JSON files are not committed by default because they can become large in full query-plan runs.

## Interpretation

Group C complements the previous IMDb query-plan groups.

* Group A explains local, search, ranking, and update-oriented queries.
* Group B explains the containment-oriented QG6 case.
* Group D explains insert/update behavior for QG8.
* Group C explains associative and deep-traversal behavior for QG4 and QG5.

Together, these results support the SchemaLens argument that the best document-schema candidates depend on the interaction between query root, relationship semantics, traversal depth, residual traversal, sharedness, update sensitivity, and physical document size.
