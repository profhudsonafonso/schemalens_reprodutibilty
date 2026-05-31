\# IMDb Group D Query-Plan Results: QG8 Add Person Role to WatchItem



This folder contains the MongoDB query-plan results for IMDb Group D.



Group D focuses on the insert/update-oriented query:



\* `QG8\_AddPersonRoleToWatchItem`



The goal is to record which parts of the insertion/update workflow can be explained using MongoDB `explain("executionStats")` and which parts are not explainable as query plans.



\## Execution status



The Group D run completed successfully for all IMDb scale factors:



\* `sf0.25`

\* `sf0.5`

\* `sf1`



The status summary reports `execution\_status = completed` for all selected query groups and scale factors:



\* `control`

\* `primary`

\* `secondary\_affected`



No failed query-plan rows were detected.



\## Important note about insert operations



MongoDB does not expose a useful query plan for pure `insert\_one` operations. Therefore, insert-only components are recorded as `not\_explainable`.



This is expected behavior and should not be interpreted as a failure.



For configurations where the insertion also requires locating or updating an existing `watchitems` document, the script captures the explainable part of the operation. In the associative configurations `G4`, `G5`, and `G6`, the results show plans with:



\* `UPDATE`

\* `FETCH`

\* `IXSCAN`



using the index:



\* `watchitem\_id\_1`



\## Main physical pattern



The results show that QG8 is not only an insertion task. In associative configurations, adding a role/person relation may also require maintaining embedded or partially embedded structures inside the `watchitems` document.



The relevant configurations are:



\* `G4 / watchitem\_g4`: associative partial embedding with `Role`.

\* `G5 / watchitem\_g5`: associative snapshot with `Role` embedded and `Person` referenced/snapshotted.

\* `G6 / watchitem\_g6`: associative full embedding with `Role` and `Person`.



These configurations expose the maintenance cost of write-oriented schema decisions. As the embedding becomes richer from G4 to G6, the average document size increases, which helps explain why insert/update workloads must be considered in SchemaLens.



\## Files



Main files in this folder:



\* `query\_plan\_summary\_results\_group\_D.csv`

\* `query\_plan\_component\_results\_group\_D.csv`

\* `query\_plan\_status\_summary\_group\_D.csv`

\* `benchmark\_run\_manifest\_group\_D.json`

\* `execution\_group\_D.log`

\* `selected\_experiments\_summary\_group\_D.csv`

\* `scale\_db\_initialization\_summary\_group\_D.csv`

\* `collection\_swap\_summary\_group\_D.csv`



Raw MongoDB `explain` JSON files are not committed by default because they can become large in full query-plan runs.



\## Interpretation



Group D is valid and complete.



The results should be interpreted differently from read-only query groups. Pure inserts are marked as `not\_explainable`, while update or lookup components around the insert are captured when MongoDB exposes a useful plan.



This group supports the SchemaLens argument that document-schema design must consider write-sensitive trade-offs. Embedding can improve locality for some reads, but it may increase maintenance cost when new associative relationships are inserted.



