# SchemaLens Artifact — LDBC SNB Case Study

Check that the execution plan exists in the folder passed to --artifacts-dir.

For example:

analysis/ldbc_snb/benchmark_execution_plan.csv

Then use:

--artifacts-dir analysis/ldbc_snb
IC1–IC5 return zero documents

Check the person_knows_person collection.

The document must contain:

person1_id
person2_id
creation_date

If it contains:

Person.id.1

instead of:

person2_id

the runner must normalize the duplicate LDBC column name.

Insert queries return zero documents

This is expected for:

INS1–INS8

Check:

documents_written

The expected value is:

documents_written = 1
MongoDB connection closes during loading

Use a smaller batch size:

--batch-size 5000

Avoid very large values such as:

--batch-size 300000
Results from different scale factors look identical

Check that these three arguments point to the intended scale:

--data-dir
--results-dir
--scale-label

Each scale factor must use a separate result directory.

What should be stored in Git

Store:

methodology/ldbc_methodology.ipynb
benchmark/ldbc_snb/run_ldbc_snb_mongo_benchmark.py
analysis/ldbc_snb/results_analise_sf0_1ipynb
analysis/ldbc_snb/results_analise_sf1.ipynb
analysis/ldbc_snb/results_analise_sf3.ipynb
analysis/ldbc_snb/comparison_sfs.ipynb
README_LDBC_SNB.md

Also store small benchmark artifacts if they are not too large:

benchmark_execution_plan.csv
benchmark_execution_plan_smoke.csv
benchmark_manifest.json
mongodb_candidate_specs_by_candidate_id.json
mongodb_candidate_specs_overview.csv

These can be placed in:

analysis/ldbc_snb/

Do not store:

datasets/
data/
downloads/
*.tar.zst
*.tar.zst.*
*.duckdb
.venv/
mongo_data/
Docker volumes
large raw benchmark files
MongoDB database files
Suggested .gitignore
# Large datasets
data/
datasets/
downloads/
*.tar.zst
*.tar.zst.*

# Local environments
.venv/
venv/
__pycache__/
.ipynb_checkpoints/

# Local DB files
*.duckdb
*.sqlite
mongo_data/

# Large benchmark outputs
results/
*.log
execution.log
Paper connection

The LDBC SNB outputs support the cross-dataset comparison in the SchemaLens paper.

The final paper table uses the corrected per-query, per-scale, per-phase analysis based on:

p95 latency
DSR
Top-1 preservation
near-best preservation within 5%
activated regret
primary regret
