\# IMDb QG9 Query-Plan Validation



This folder contains the MongoDB query-plan validation results for IMDb `QG9\_TopRatedSeriesByGenre`.



The goal is to complement the benchmark p95 results with MongoDB `explain("executionStats")` evidence and physical collection statistics.



\## Query



`QG9\_TopRatedSeriesByGenre` retrieves top-rated series for a given genre.



The representative parameter used in this validation is:



```text

Comedy

```



\## Compared configurations



The validation compares the main configurations involved in the QG9 interpretation:



\- `watchitem\_g0` / `G0`: generic WatchItem-rooted baseline.

\- `watchitem\_g2` / `G2`: WatchItem-rooted shared-descriptor variant.

\- `series\_g7` / `G7`: Series-rooted containment baseline.

\- `series\_g8` / `G8`: Series-rooted containment with embedded episodes.



\## Main evidence



The query-plan results show that `G7` and `G8` query the specialized `series` collection, while `G0` and `G2` query the generic `watchitems` collection.



For `sf1`, `G0` and `G2` examine more than 24,000 documents, while `G7` and `G8` examine only 91 documents.



The physical collection statistics also distinguish `G7` from `G8`. Both use the same `series` root, but `G8` has substantially larger documents because it embeds episodes that QG9 does not use.



Therefore, QG9 supports the interpretation that the winning configuration is not explained only by index usage. It is explained by the match between query root, collection specialization, and physical document size.



\## Files



\### Consolidated files



\- `query\_plan\_summary\_qg9\_all\_sfs.csv`: consolidated summary across all validated scale factors.

\- `query\_plan\_components\_qg9\_all\_sfs.csv`: consolidated component-level query-plan details.

\- `query\_plan\_status\_summary\_qg9\_all\_sfs.csv`: consolidated status summary.



\### Source files



\- `query\_plan\_summary\_results\_qg9\_sf025\_sf050.csv`: summary for `sf0.25` and `sf0.5`.

\- `query\_plan\_summary\_results\_qg9\_sf1.csv`: summary for `sf1`.

\- `query\_plan\_component\_results\_qg9\_sf025\_sf050.csv`: component-level results for `sf0.25` and `sf0.5`.

\- `query\_plan\_component\_results\_qg9\_sf1.csv`: component-level results for `sf1`.

\- `query\_plan\_status\_summary\_qg9\_sf025\_sf050.csv`: status summary for `sf0.25` and `sf0.5`.

\- `query\_plan\_status\_summary\_qg9\_sf1.csv`: status summary for `sf1`.

\- `benchmark\_run\_manifest\_qg9\_sf025\_sf050.json`: execution metadata for `sf0.25` and `sf0.5`.

\- `benchmark\_run\_manifest\_qg9\_sf1.json`: execution metadata for `sf1`.

\- `execution\_qg9\_sf025\_sf050.log`: execution log for `sf0.25` and `sf0.5`.

\- `execution\_qg9\_sf1.log`: execution log for `sf1`.

\- `selected\_experiments\_summary\_qg9\_\*.csv`: selected experiment summaries.

\- `scale\_db\_initialization\_summary\_qg9\_\*.csv`: MongoDB initialization summaries.

\- `collection\_swap\_summary\_qg9\_\*.csv`: collection replacement summaries.



Raw `explain` JSON files are not committed by default because they can become large in full query-plan runs.



\## Interpretation



The QG9 validation supports three observations:



1\. `G7` is aligned with the query root because QG9 asks for top-rated series by genre.

2\. `G0` and `G2` operate over the more generic `watchitems` collection and require a more complex indexed plan.

3\. `G8` uses the same `series` root as `G7`, but its documents are larger because it embeds episodes that QG9 does not use.



Therefore, QG9 helps explain why the benchmark selected `G7`: it combines the correct query root with smaller physical documents.



\## Reproducing the merge step



The consolidated CSV files are generated with:



```bash

python analysis/scripts/merge\_qg9\_query\_plan\_results.py

```



This script merges the split outputs from:



\- `sf0.25` and `sf0.5`

\- `sf1`



into consolidated all-scale files.

