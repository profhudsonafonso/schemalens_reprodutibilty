# FIBEN Scale-Factor Generation

This folder documents the scale-factor generation workflow used for the FIBEN part of the SchemaLens evaluation.

The notebook in this folder is:


Fiben_generate_scale_factor.ipynb
Recommended reviewer path

Reviewers do not need to regenerate the FIBEN scale factors from scratch.

The prepared FIBEN scale-factor package used in the paper is available on OSF:

https://osf.io/532rn/overview?view_only=0a93fbed1db745d0978aa2e9f6cd7c78

After downloading and extracting the package, organize it locally as:

data/
  fiben/
    sf1/
    sf10/
    sf30/

Then follow the benchmark and analysis instructions in:

README_FIBEN.md
Full scale-factor reproduction

Use this path only if you want to reproduce the FIBEN scale-factor generation process.

Run:

scale_generator/fiben/Fiben_generate_scale_factor.ipynb

The notebook documents the preparation of:

sf1
sf10
sf30

The scale-generation workflow starts from the FIBEN source data, derives a workload-induced baseline subset, and then generates larger scale factors while preserving the workload-relevant relationship structure.

Outputs

The expected generated folders are:

data/
  fiben/
    sf1/
    sf10/
    sf30/

These folders are used as input by the MongoDB benchmark runner:

benchmark/fiben/run_fiben_mongo_benchmark.py
Notes

The scale-factor data are large and are therefore distributed through OSF rather than stored directly in this Git repository. The Git repository contains the notebook and instructions needed to reproduce the generation process.
