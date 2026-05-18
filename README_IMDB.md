# SchemaLens Artifact — IMDb Case Study

This README describes how to reproduce the IMDb part of the SchemaLens evaluation.

IMDb is used in the paper as the detailed running example because it contains the three semantic patterns handled by SchemaLens:

* association
* associative structures
* containment-like structures

The IMDb case study supports reproduction of:

1. scale-factor preparation or reuse;
2. methodology execution;
3. MongoDB candidate benchmarking;
4. result analysis;
5. paper-support outputs for the IMDb rows in the cross-dataset summary.

## Repository files

Main files for the IMDb case study:



methodology/imdb\_methodology.ipynb

scale\_generator/imdb/README.md
scale\_generator/imdb/IMDB\_sf\_commented\_english.ipynb

benchmark/imdb/run\_mongo\_benchmark\_option\_b\_incremental.py
benchmark/imdb/mongo\_experiment\_catalog.csv
benchmark/imdb/benchmark\_execution\_template.csv

analysis/imdb/analyze\_results\_using\_catalog.ipynb
analysis/imdb/compare\_scale\_factors\_imdb.ipynb
analysis/imdb/benchmark\_aggregate\_results\_imdb\_all\_sfs.csv
Data availability

The raw IMDb TSV files and prepared IMDb scale-factor folders are not stored directly in this Git repository because of size and licensing constraints.

The prepared scale-factor package used in the paper is available on OSF:

https://osf.io/532rn/overview?view\_only=0a93fbed1db745d0978aa2e9f6cd7c78

Reviewers can either use the prepared OSF package or regenerate the scale factors using the notebook in:

scale\_generator/imdb/

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

After downloading or generating the data, organize them locally as:

data/
imdb/
sf\_025/
sf\_050/
sf\_1/

Each scale-factor folder should contain the required IMDb TSV files.

If your local paths are different, update the IMDB\_SF\_PATHS dictionary in:

benchmark/imdb/run\_mongo\_benchmark\_option\_b\_incremental.py

### Two reproduction options

#### Option A — Use the prepared OSF scale-factor package

This is the recommended path for reviewers.

Download the prepared IMDb scale-factor package from OSF.
Extract it locally using the folder structure shown above.
Run the SchemaLens methodology notebook.
Run the MongoDB benchmark script using the extracted scale-factor folders.
Run the IMDb analysis notebooks to verify the reported results.

This option avoids the time-consuming scale-factor generation step.

#### Option B — Regenerate the scale factors

Use this option only if you want to reproduce the IMDb scale-factor generation process.

Run the IMDb scale-generation notebook:

scale\_generator/imdb/IMDB\_sf\_commented\_english.ipynb

The notebook documents how the IMDb scale factors were prepared from the IMDb source TSV files. The preparation creates the scale-factor folders used by the benchmark:

sf\_025
sf\_050
sf\_1

Additional scale-generation instructions are provided in:

scale\_generator/imdb/README.md
Methodology reproduction

## Run the notebook:

methodology/imdb\_methodology.ipynb

This notebook generates or documents the IMDb SchemaLens methodology outputs, including:

conceptual/semantic view preparation;
analytical matrix generation;
query classification;
activated MongoDB configuration families.

The key methodology artifact used by the benchmark is the MongoDB experiment catalog:

benchmark/imdb/mongo\_experiment\_catalog.csv

## Benchmark reproduction

The benchmark runner is:

benchmark/imdb/run\_mongo\_benchmark\_option\_b\_incremental.py

The runner requires:

benchmark/imdb/mongo\_experiment\_catalog.csv
benchmark/imdb/benchmark\_execution\_template.csv

Example command:

python benchmark/imdb/run\_mongo\_benchmark\_option\_b\_incremental.py   
--catalog-csv benchmark/imdb/mongo\_experiment\_catalog.csv   
--template-csv benchmark/imdb/benchmark\_execution\_template.csv   
--results-dir results/imdb/sf0\_25   
--scale-label sf0.25   
--run-phase cold hot   
--batch-size 10000   
--force-rebuild-scale-db

Repeat the benchmark for the other scale factors by changing:

\--results-dir
--scale-label

The benchmark uses 10 cold-run and 10 hot-run repetitions per candidate/query pair.

MongoDB can be started from the repository root with:

docker compose up -d

The default MongoDB port is:

27018

## Result analysis

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

## Paper connection

The IMDb artifact supports:

the end-to-end SchemaLens walkthrough;
the QG6 containment example;
the IMDb association, associative, and containment rows in the cross-dataset table.

The main representative IMDb queries are:

QG3\_RecommendationByGenreAndSubtype
QG4\_AllPersonsOfTypeForWatchItem
QG6\_EpisodesOfSeries


## Lightweight verification



To verify the IMDb part of the paper without rerunning the full benchmark, use the provided aggregate benchmark outputs.



Consolidated all-scale file:



```text

analysis/imdb/benchmark\_aggregate\_results\_imdb\_all\_sfs.csv



Scale-specific files:



analysis/imdb/benchmark\_aggregate\_results\_sf025.csv

analysis/imdb/benchmark\_aggregate\_results\_sf050.csv

analysis/imdb/benchmark\_aggregate\_results\_sf1.csv

````

The consolidated file is used for cross-scale analysis. The scale-specific files are provided for easier inspection of each IMDb scale factor.



These files support verification of the IMDb containment case study, the G7/G8/G9 comparison for QG6\_EpisodesOfSeries, p95 latency, near-best preservation within the 5% threshold, and workload-level trade-offs across primary, secondary-affected, and control queries.



Full benchmark reproduction is supported, but it is more time-consuming because it requires materializing MongoDB candidate configurations and executing repeated cold/hot benchmark runs.

## Notes

The scale-factor data are large and are therefore distributed through OSF rather than stored directly in this Git repository. The Git repository contains the methodology notebook, scale-generation notebook, benchmark script, benchmark input files, and analysis notebooks needed to reproduce or verify the IMDb part of the paper.

