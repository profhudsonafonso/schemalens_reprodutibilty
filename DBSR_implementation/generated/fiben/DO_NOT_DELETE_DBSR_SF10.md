# Do not delete: DBSR FIBEN SF10 MongoDB state

MongoDB database:

- `dbsr_fiben_sf10_source_full`

This database contains the full physical DBSR materialization for FIBEN SF10, including all `dbsr_rank*` collections.

It is required for:

- DBSR p95 benchmark reproducibility
- DBSR query-plan / explain("executionStats") analysis
- future SF10 validation without rematerializing the expensive DBSR structures

Do not drop this database unless a full backup exists.
