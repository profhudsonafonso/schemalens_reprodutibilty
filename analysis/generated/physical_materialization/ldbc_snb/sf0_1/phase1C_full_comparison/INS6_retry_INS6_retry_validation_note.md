# Retry validation note: INS6 / AddPost

During the grouped INS materialization run, `INS6_AddPost / G7`
failed with a transient MongoDB `AutoReconnect: connection closed` error.

Resource monitoring did not indicate memory exhaustion, disk exhaustion, or an
OOM event:

- container remained running;
- exit_code was 0;
- oom_killed was False;
- system memory usage stayed below approximately 10%;
- Docker memory usage stayed around 1--2 GiB out of 62 GiB;
- disk free space remained stable.

The query was re-executed in isolation with a smaller batch size. The retry
successfully materialized all INS6 candidates:

- G0: ready
- G3: ready_generic
- G7: ready
- G9: ready_generic

Therefore, the previous failure is interpreted as a transient connection issue,
not as a physical-materialization failure.
