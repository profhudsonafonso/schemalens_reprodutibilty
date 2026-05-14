\# SchemaLens Artifact — IMDb Case Study



This README describes how to reproduce the IMDb part of the SchemaLens evaluation.



IMDb is used in the paper as the detailed running example because it contains the three semantic patterns handled by SchemaLens:



\- association

\- associative structures

\- containment-like structures



The IMDb case study supports reproduction of:



1\. scale-factor preparation;

2\. methodology execution;

3\. MongoDB candidate benchmarking;

4\. result analysis;

5\. paper-support outputs for the IMDb rows in the cross-dataset summary.



\## Repository files



Main files for the IMDb case study:



methodology/imdb\_methodology.ipynb



benchmark/imdb/run\_mongo\_benchmark\_option\_b\_incremental.py

benchmark/imdb/mongo\_experiment\_catalog.csv

benchmark/imdb/benchmark\_execution\_template.csv



analysis/imdb/analyze\_results\_using\_catalog.ipynb

analysis/imdb/compare\_scale\_factors\_imdb.ipynb

analysis/imdb/benchmark\_aggregate\_results\_imdb\_all\_sfs.csv

Dataset



The raw IMDb TSV files are not stored in this repository because of size and licensing constraints.



The experiments use the IMDb non-commercial dataset files:



name.basics.tsv

title.akas.tsv

title.basics.tsv

title.crew.tsv

title.episode.tsv

title.principals.tsv

title.ratings.tsv



The scale-factor folders used in the experiments are:



sf0.25

sf0.5

sf1



In the benchmark script, these are expected by default at:



sf0.25 -> /home/hudson/Documents/framework\_test/imdb/data/sf\_025

sf0.5  -> /home/hudson/Documents/framework\_test/imdb/data/sf\_050

sf1    -> /home/hudson/Documents/framework\_test/imdb/data/sf\_1



If your local paths are different, update the IMDB\_SF\_PATHS dictionary in:



benchmark/imdb/run\_mongo\_benchmark\_option\_b\_incremental.py

Methodology reproduction



Run the notebook:



methodology/imdb\_methodology.ipynb



This notebook generates or documents the IMDb SchemaLens methodology outputs, including:



conceptual/semantic view preparation;

analytical matrix generation;

query classification;

activated MongoDB configuration families.



The key methodology artifact used by the benchmark is the MongoDB experiment catalog:



benchmark/imdb/mongo\_experiment\_catalog.csv

Benchmark reproduction



The benchmark runner is:



benchmark/imdb/run\_mongo\_benchmark\_option\_b\_incremental.py



The runner requires:



benchmark/imdb/mongo\_experiment\_catalog.csv

benchmark/imdb/benchmark\_execution\_template.csv



Example command:



python benchmark/imdb/run\_mongo\_benchmark\_option\_b\_incremental.py \\

&#x20; --catalog-csv benchmark/imdb/mongo\_experiment\_catalog.csv \\

&#x20; --template-csv benchmark/imdb/benchmark\_execution\_template.csv \\

&#x20; --results-dir results/imdb/sf0\_25 \\

&#x20; --scale-label sf0.25 \\

&#x20; --run-phase cold hot \\

&#x20; --batch-size 10000 \\

&#x20; --force-rebuild-scale-db



The benchmark uses 10 cold-run and 10 hot-run repetitions per candidate/query pair.



MongoDB can be started from the repository root with:



docker compose up -d



The default MongoDB port is:



27018

Result analysis



The main IMDb analysis notebooks are:



analysis/imdb/analyze\_results\_using\_catalog.ipynb

analysis/imdb/compare\_scale\_factors\_imdb.ipynb



The aggregate all-scale result file is:



analysis/imdb/benchmark\_aggregate\_results\_imdb\_all\_sfs.csv



These files support the IMDb results reported in the paper, including:



QG6 containment case;

hot-run results across scale factors;

primary, secondary-affected, and control query comparison;

IMDb representative rows in the cross-dataset summary.

Paper connection



The IMDb artifact supports:



the end-to-end SchemaLens walkthrough;

the QG6 containment example;

the IMDb association, associative, and containment rows in the cross-dataset table.



The main representative IMDb queries are:



QG3\_RecommendationByGenreAndSubtype

QG4\_AllPersonsOfTypeForWatchItem

QG6\_EpisodesOfSeries

Lightweight verification



To verify the paper results without rerunning the full benchmark, use:



analysis/imdb/benchmark\_aggregate\_results\_imdb\_all\_sfs.csv

analysis/imdb/analyze\_results\_using\_catalog.ipynb

analysis/imdb/compare\_scale\_factors\_imdb.ipynb



Full benchmark reproduction is supported, but it is more time-consuming because it requires materializing MongoDB candidate configurations and executing repeated cold/hot benchmark runs.

