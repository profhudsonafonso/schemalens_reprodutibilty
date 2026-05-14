# IMDb Scale-Factor Generation

This folder documents the scale-factor preparation workflow used for the IMDb part of the SchemaLens evaluation.

IMDb is used in the paper as the detailed running example because it contains association, associative, and containment-like structures. The scale factors used in the experiments are:


sf0.25
sf0.5
sf1
Recommended reviewer path

Reviewers do not need to regenerate the IMDb scale factors from scratch.

The prepared scale-factor package used in the paper is available on OSF:

https://osf.io/532rn/overview?view_only=0a93fbed1db745d0978aa2e9f6cd7c78

After downloading and extracting the package, organize the IMDb data locally as:

data/
  imdb/
    sf_025/
    sf_050/
    sf_1/

These folders should contain the IMDb TSV files required by the benchmark runner:

name.basics.tsv
title.akas.tsv
title.basics.tsv
title.crew.tsv
title.episode.tsv
title.principals.tsv
title.ratings.tsv

Then follow the benchmark and analysis instructions in:

README_IMDB.md
Two reproduction options
Option A — Use the prepared OSF scale-factor package

This is the recommended path for reviewers.

Download the prepared IMDb scale-factor package from OSF.
Extract it locally using the folder structure shown above.
Run the SchemaLens methodology notebook.
Run the MongoDB benchmark script using the extracted scale-factor folders.
Run the IMDb analysis notebooks to verify the reported results.

This option avoids the time-consuming scale-factor generation step.

Option B — Regenerate the scale factors

Use this option only if you want to reproduce the IMDb scale-factor generation process.

Run the IMDb scale-generation notebook in this folder. For example:

scale_generator/imdb/IMDB_sf_commented_english.ipynb

If the notebook name differs in your local copy, use the IMDb scale-generation notebook provided in this folder.

The notebook documents how the IMDb scale factors were prepared from the IMDb source TSV files. The preparation starts from the IMDb source data and creates the scale-factor folders used by the benchmark:

sf_025
sf_050
sf_1
Outputs

The expected generated folders are:

data/
  imdb/
    sf_025/
    sf_050/
    sf_1/

These folders are used as input by the MongoDB benchmark runner:

benchmark/imdb/run_mongo_benchmark_option_b_incremental.py

The benchmark runner expects these paths by default:

sf0.25 -> /path/to/imdb/data/sf_025
sf0.5  -> /path/to/imdb/data/sf_050
sf1    -> /path/to/imdb/data/sf_1

If your local paths are different, update the IMDB_SF_PATHS dictionary in:

benchmark/imdb/run_mongo_benchmark_option_b_incremental.py
Notes

The scale-factor data are large and are therefore distributed through OSF rather than stored directly in this Git repository. The Git repository contains the notebook and instructions needed to reproduce the generation process.
