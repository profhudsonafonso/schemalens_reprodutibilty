\# SchemaLens Analysis Outputs



This folder contains the analysis files used to verify and extend the experimental results of the SchemaLens paper.



The goal of this folder is to support lightweight reproducibility from aggregate benchmark outputs, without requiring reviewers to rerun the full MongoDB benchmark.



The analyses in this folder are used to support:



\- normalized aggregate benchmark outputs;

\- baseline comparisons;

\- ablation studies;

\- near-best and regret analysis;

\- failure and near-failure analysis;

\- paper-ready tables.



These analyses use the aggregate benchmark result files already included in the repository.



\---



\## Folder structure



&#x20;   analysis/

&#x20;     README.md



&#x20;     imdb/

&#x20;       benchmark\_aggregate\_results\_imdb\_all\_sfs.csv

&#x20;       benchmark\_aggregate\_results\_sf025.csv

&#x20;       benchmark\_aggregate\_results\_sf050.csv

&#x20;       benchmark\_aggregate\_results\_sf1.csv



&#x20;     fiben/

&#x20;       benchmark\_aggregate\_results\_fiben\_sf1.csv

&#x20;       benchmark\_aggregate\_results\_fiben\_sf10.csv

&#x20;       benchmark\_aggregate\_results\_fiben\_sf30.csv

&#x20;       benchmark\_execution\_plan.csv



&#x20;     ldbc\_snb/

&#x20;       benchmark\_aggregate\_results\_ldbc\_snb\_sf0\_1.csv

&#x20;       benchmark\_aggregate\_results\_ldbc\_snb\_sf1.csv

&#x20;       benchmark\_aggregate\_results\_ldbc\_snb\_sf3.csv



&#x20;     scripts/

&#x20;       normalize\_aggregate\_outputs.py



&#x20;     generated/

&#x20;       aggregate\_results\_all\_datasets.csv

&#x20;       normalization\_report.txt



\---



\## Purpose of the normalization step



The original aggregate benchmark files have similar information, but their column names are not identical across datasets.



For IMDb, the aggregate file uses columns such as:



&#x20;   config\_name

&#x20;   activated\_class

&#x20;   benchmark\_family

&#x20;   query\_group



For FIBEN and LDBC SNB, the aggregate files use columns such as:



&#x20;   candidate\_id

&#x20;   g\_class

&#x20;   design\_pattern

&#x20;   final\_benchmark\_group



The normalization script converts these dataset-specific formats into one common schema.



This makes it possible to run the same downstream analyses over IMDb, FIBEN, and LDBC SNB.



\---



\## Input files



\### IMDb



&#x20;   analysis/imdb/benchmark\_aggregate\_results\_imdb\_all\_sfs.csv



The following scale-specific files are also provided for easier inspection:



&#x20;   analysis/imdb/benchmark\_aggregate\_results\_sf025.csv

&#x20;   analysis/imdb/benchmark\_aggregate\_results\_sf050.csv

&#x20;   analysis/imdb/benchmark\_aggregate\_results\_sf1.csv



The normalization script uses the consolidated IMDb file:



&#x20;   analysis/imdb/benchmark\_aggregate\_results\_imdb\_all\_sfs.csv



\---



\### FIBEN



&#x20;   analysis/fiben/benchmark\_aggregate\_results\_fiben\_sf1.csv

&#x20;   analysis/fiben/benchmark\_aggregate\_results\_fiben\_sf10.csv

&#x20;   analysis/fiben/benchmark\_aggregate\_results\_fiben\_sf30.csv



\---



\### LDBC SNB



&#x20;   analysis/ldbc\_snb/benchmark\_aggregate\_results\_ldbc\_snb\_sf0\_1.csv

&#x20;   analysis/ldbc\_snb/benchmark\_aggregate\_results\_ldbc\_snb\_sf1.csv

&#x20;   analysis/ldbc\_snb/benchmark\_aggregate\_results\_ldbc\_snb\_sf3.csv



\---



\## Output files



The normalization script generates:



&#x20;   analysis/generated/aggregate\_results\_all\_datasets.csv

&#x20;   analysis/generated/normalization\_report.txt



The file `aggregate\_results\_all\_datasets.csv` is the common input for the next analysis scripts.



The file `normalization\_report.txt` summarizes the generated output and checks whether the normalization was successful.



\---



\## Normalized columns



The generated CSV uses the following common columns:



&#x20;   dataset

&#x20;   scale\_label

&#x20;   query\_name

&#x20;   query\_scale\_phase\_id

&#x20;   config\_id

&#x20;   g\_class

&#x20;   design\_family

&#x20;   benchmark\_group

&#x20;   run\_phase

&#x20;   n\_runs

&#x20;   n\_success\_runs

&#x20;   avg\_latency\_ms

&#x20;   median\_latency\_ms

&#x20;   p95\_latency\_ms

&#x20;   p99\_latency\_ms

&#x20;   min\_latency\_ms

&#x20;   max\_latency\_ms

&#x20;   std\_latency\_ms

&#x20;   avg\_documents\_returned

&#x20;   avg\_documents\_written

&#x20;   source\_experiment\_id

&#x20;   source\_file



\---



\## Meaning of the main normalized columns



\### dataset



Identifies the dataset:



&#x20;   imdb

&#x20;   fiben

&#x20;   ldbc\_snb



\### scale\_label



Identifies the scale factor used in the benchmark.



Examples:



&#x20;   sf0.25

&#x20;   sf0.5

&#x20;   sf1

&#x20;   sf10

&#x20;   sf30

&#x20;   sf0\_1

&#x20;   sf3



\### query\_name



Identifies the workload query.



Examples:



&#x20;   QG6\_EpisodesOfSeries

&#x20;   Q5\_ReportsAndMetricDataOfCompany

&#x20;   IC5\_NewGroups

&#x20;   IS4\_ContentOfMessage



\### config\_id



Identifies the concrete benchmarked MongoDB configuration.



For IMDb, this comes from `config\_name`.



For FIBEN and LDBC SNB, this comes from `candidate\_id`.



\### g\_class



Identifies the SchemaLens configuration class.



Examples:



&#x20;   G0

&#x20;   G1

&#x20;   G2

&#x20;   G3

&#x20;   G4

&#x20;   G5

&#x20;   G6

&#x20;   G7

&#x20;   G8

&#x20;   G9

&#x20;   CONTROL



\### design\_family



Identifies the design family or pattern.



For IMDb, this comes from `benchmark\_family`.



For FIBEN and LDBC SNB, this comes from `design\_pattern`.



\### benchmark\_group



Identifies how the configuration is used in the evaluation.



Expected values:



&#x20;   primary

&#x20;   secondary\_affected

&#x20;   control



\### run\_phase



Identifies whether the result comes from cold or hot benchmark runs.



Expected values:



&#x20;   cold

&#x20;   hot



\### p95\_latency\_ms



The 95th percentile latency in milliseconds.



This is the main latency metric used in the paper.



\---



\## Run command



From the repository root, run:



&#x20;   python analysis/scripts/normalize\_aggregate\_outputs.py



On Windows PowerShell, run:



&#x20;   python analysis\\scripts\\normalize\_aggregate\_outputs.py



\---



\## Expected result



The script should read the aggregate CSV files from IMDb, FIBEN, and LDBC SNB and generate:



&#x20;   analysis/generated/aggregate\_results\_all\_datasets.csv

&#x20;   analysis/generated/normalization\_report.txt



Expected row counts:



&#x20;   IMDb: 540 rows

&#x20;   FIBEN: 360 rows

&#x20;   LDBC SNB: 384 rows

&#x20;   Total: 1284 rows



Expected datasets:



&#x20;   imdb

&#x20;   fiben

&#x20;   ldbc\_snb



Expected run phases:



&#x20;   cold

&#x20;   hot



\---



\## Validation report



The generated file:



&#x20;   analysis/generated/normalization\_report.txt



reports:



\- total rows;

\- rows by dataset;

\- rows by dataset and scale;

\- rows by dataset and run phase;

\- benchmark groups;

\- unique queries by dataset;

\- G classes by dataset;

\- rows with missing p95 latency;

\- duplicated rows;

\- source files used.



A successful normalization should report:



&#x20;   Rows with missing p95\_latency\_ms: 0



The duplicate-row check should also be reviewed. If duplicates are reported, they must be inspected before running baseline or ablation analyses.



\---



\## What this step does not do



This step does not simulate baselines.



This step does not run ablation analysis.



This step does not rerun MongoDB benchmarks.



This step only creates a common, clean input file for the next analyses.



\---



\## Next planned scripts



The next analysis scripts will use:



&#x20;   analysis/generated/aggregate\_results\_all\_datasets.csv



Planned scripts:



&#x20;   analysis/scripts/check\_baseline\_coverage.py

&#x20;   analysis/scripts/simulate\_baselines.py

&#x20;   analysis/scripts/run\_ablation\_analysis.py

&#x20;   analysis/scripts/analyze\_failure\_cases.py



\---



\## Reproducibility note



These analyses are based on aggregate benchmark outputs already included in the repository.



They are intended for lightweight verification of the paper results. Full benchmark reproduction is still possible, but it requires loading the datasets, materializing MongoDB candidate configurations, and rerunning repeated cold/hot benchmark executions.



The lightweight path is recommended for quickly verifying:



\- p95 latency;

\- Top-1 preservation;

\- Top-3 preservation;

\- near-best preservation within the 5% threshold;

\- relative regret;

\- control-winner cases;

\- cross-scale behavior.

