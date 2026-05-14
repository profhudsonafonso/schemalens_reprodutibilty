\# SchemaLens Artifact — LDBC SNB Case Study



This README describes how to reproduce the LDBC Social Network Benchmark (LDBC SNB) part of the SchemaLens evaluation.



LDBC SNB is used in the paper as an official benchmark workload. Unlike IMDb and FIBEN, which use representative workloads designed to cover generic access classes, LDBC SNB keeps the official benchmark queries unchanged. SchemaLens maps these official queries to analytical features after extracting touched entities, relationship paths, traversal depth, access type, and write operations.



The LDBC SNB case study supports reproduction of:



1\. methodology execution over the LDBC SNB conceptual structure;

2\. mapping of official IC, IS, and INS queries to SchemaLens analytical features;

3\. MongoDB candidate generation and benchmark execution;

4\. cross-scale result analysis;

5\. aggregate official-workload validation used in the paper.



\## Repository files



Main files for the LDBC SNB case study:





methodology/ldbc\_snb\_methodology.ipynb



benchmark/ldbc\_snb/run\_ldbc\_snb\_mongo\_benchmark.py



analysis/ldbc\_snb/analyze\_results\_sf0\_1.ipynb

analysis/ldbc\_snb/analyze\_results\_sf1.ipynb

analysis/ldbc\_snb/analyze\_results\_sf3.ipynb

analysis/ldbc\_snb/compare\_scale\_factors.ipynb

Dataset



The raw LDBC SNB data files are not stored directly in this repository because of size constraints.



The experiments use the official LDBC SNB data layout, including static, dynamic, and substitution-parameter files.



The scale factors used in the paper are:



sf0.1

sf1

sf3



The official workload queries evaluated in the paper are:



IC1--IC7

IS1--IS7

INS1--INS8



These queries are kept unchanged and mapped to SchemaLens analytical features before activation.



Methodology reproduction



Run the notebook:



methodology/ldbc\_snb\_methodology.ipynb



This notebook documents the SchemaLens methodology execution for LDBC SNB, including:



conceptual view preparation;

official query mapping;

touched-entity extraction;

relationship-path extraction;

analytical matrix generation;

activation of MongoDB configuration families;

benchmark-planning artifacts.

Benchmark reproduction



The benchmark runner is:



benchmark/ldbc\_snb/run\_ldbc\_snb\_mongo\_benchmark.py



Example command:



python benchmark/ldbc\_snb/run\_ldbc\_snb\_mongo\_benchmark.py \\

&#x20; --data-dir /path/to/ldbc\_snb/data/sf0.1 \\

&#x20; --artifacts-dir /path/to/ldbc\_snb/benchmark\_artifacts/ldbc\_snb\_mongo\_configurations \\

&#x20; --results-dir results/ldbc\_snb/sf0\_1 \\

&#x20; --scale-label sf0.1 \\

&#x20; --mongo-host 127.0.0.1 \\

&#x20; --mongo-port 27018 \\

&#x20; --batch-size 5000 \\

&#x20; --force-rebuild-db



Repeat the execution for:



sf0.1

sf1

sf3



MongoDB can be started from the repository root with:



docker compose up -d



The default MongoDB port is:



27018

Result analysis



The main LDBC SNB analysis notebooks are:



analysis/ldbc\_snb/analyze\_results\_sf0\_1.ipynb

analysis/ldbc\_snb/analyze\_results\_sf1.ipynb

analysis/ldbc\_snb/analyze\_results\_sf3.ipynb

analysis/ldbc\_snb/compare\_scale\_factors.ipynb



These files support the LDBC SNB results reported in the paper, including:



design-space reduction;

Top-1 preservation;

near-best preservation;

activated-family regret;

primary, secondary, and control winners;

cross-scale comparison across sf0.1, sf1, and sf3.

Paper connection



The LDBC SNB artifact supports the official-workload validation in the cross-dataset evaluation.



In the paper, LDBC SNB is reported as an aggregate official-workload result rather than as one representative semantic-family case. This is because the official benchmark workload contains multiple query types and is kept unchanged.



The aggregate paper result summarizes:



22 official queries per scale

3 scale factors

66 query-scale cases

65/66 Top-1 preservation

71.4% average design-space reduction

0.008 mean activated regret

Lightweight verification



To verify the LDBC SNB part of the paper without rerunning the full benchmark, use:



analysis/ldbc\_snb/analyze\_results\_sf0\_1.ipynb

analysis/ldbc\_snb/analyze\_results\_sf1.ipynb

analysis/ldbc\_snb/analyze\_results\_sf3.ipynb

analysis/ldbc\_snb/compare\_scale\_factors.ipynb



Full benchmark reproduction is supported, but it is more time-consuming because it requires loading LDBC SNB scale-factor data, materializing MongoDB candidate configurations, and executing repeated benchmark runs over the official workload.

