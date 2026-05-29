\# IMDb Group B Query-Plan Results: QG6 Episodes of Series



This folder contains the MongoDB query-plan results for IMDb Group B.



Group B focuses on the containment-oriented query:



\* `QG6\_EpisodesOfSeries`



The goal is to explain the physical behavior of the containment family and its alternatives using MongoDB `explain("executionStats")` and collection-level statistics.



\## Execution status



The Group B run completed successfully for all IMDb scale factors:



\* `sf0.25`

\* `sf0.5`

\* `sf1`



The status summary reports `execution\_status = completed` for all selected query groups and scale factors.



No failed query-plan rows were detected.



\## Important note about zero-returned rows



The run produced a `query\_plan\_zero\_returned\_rows\_group\_B.csv` file.



These rows are not treated as execution failures. They correspond to MongoDB `COUNT` / `COUNT\_SCAN` plans over the `episodes` collection.



For count-style plans, MongoDB may report `nReturned = 0` even when the query uses an index and examines index keys. In this case, the relevant signal is not the returned-document count, but the use of `COUNT\_SCAN`, the index name, and the number of examined keys.



Therefore, the zero-returned rows are expected for this group and should be interpreted as count-plan diagnostics rather than query failures.



\## Main physical pattern



The query-plan results show two different physical strategies for QG6.



For `G7` and the WatchItem-rooted alternatives, the query uses external episode documents and accesses the `episodes` collection through the `series\_watchitem\_id\_1` index. This appears as a `COUNT` / `COUNT\_SCAN` pattern.



For `G8` and `G9`, the query accesses the `series` collection directly and uses embedded episode information. These plans use the `series` root, but the physical document size increases because episode data is embedded inside the series document.



This confirms the trade-off described in the paper:



\* `G7 / series\_g7` keeps episodes external and uses indexed access over the episode collection.

\* `G8 / series\_g8` embeds a reduced episode representation in the series document.

\* `G9 / series\_g9` embeds a richer episode representation, increasing document size further.



\## Files



Main files in this folder:



\* `query\_plan\_summary\_results\_group\_B.csv`

\* `query\_plan\_component\_results\_group\_B.csv`

\* `query\_plan\_status\_summary\_group\_B.csv`

\* `query\_plan\_zero\_returned\_rows\_group\_B.csv`

\* `benchmark\_run\_manifest\_group\_B.json`

\* `execution\_group\_B.log`

\* `selected\_experiments\_summary\_group\_B.csv`

\* `scale\_db\_initialization\_summary\_group\_B.csv`

\* `collection\_swap\_summary\_group\_B.csv`



Raw MongoDB `explain` JSON files are not committed by default because they can become large in full query-plan runs.



\## Interpretation



Group B is valid and complete, with one expected warning: the zero-returned rows are caused by MongoDB count-plan behavior. They do not indicate failed query execution.



The results are useful for explaining why the containment family must compare both reference-based and embedded containment alternatives. `G7` represents the reference-based containment baseline, while `G8` and `G9` represent increasingly embedded alternatives with larger series documents.



