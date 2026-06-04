PYTHON ?= python
PIP ?= pip

.PHONY: help docker-up docker-down install-analysis install-benchmark reproduce-paper analysis-pipeline check-artifact imdb-benchmark fiben-benchmark ldbc-benchmark clean-generated

help:
	@echo "SchemaLens reproducibility commands"
	@echo ""
	@echo "Lightweight verification:"
	@echo "  make install-analysis      Install pinned analysis dependencies"
	@echo "  make install-benchmark     Install pinned benchmark dependencies"
	@echo "  make reproduce-paper       Reproduce short-paper Table 1 and Table 2 CSVs"
	@echo "  make analysis-pipeline     Regenerate normalized, baseline, ablation, and paper outputs"
	@echo "  make check-artifact        Run basic artifact consistency checks"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up             Start MongoDB with Docker Compose"
	@echo "  make docker-down           Stop MongoDB with Docker Compose"
	@echo ""
	@echo "Benchmarks:"
	@echo "  make imdb-benchmark        Run IMDb MongoDB benchmark for one scale"
	@echo "  make fiben-benchmark       Run FIBEN MongoDB benchmark for one scale"
	@echo "  make ldbc-benchmark        Run LDBC SNB MongoDB benchmark for one scale"
	@echo ""
	@echo "Examples:"
	@echo "  make imdb-benchmark IMDB_SCALE=sf0.25 IMDB_RESULTS_DIR=results/imdb/sf0_25"
	@echo "  make fiben-benchmark FIBEN_DATA_DIR=/path/to/fiben/sf1 FIBEN_SCALE=sf1 FIBEN_RESULTS_DIR=results/fiben/sf1"
	@echo "  make ldbc-benchmark LDBC_DATA_DIR=/path/to/ldbc_snb/sf0_1 LDBC_ARTIFACTS_DIR=/path/to/artifacts LDBC_SCALE=sf0.1 LDBC_RESULTS_DIR=results/ldbc_snb/sf0_1"

install-analysis:
	$(PIP) install -r requirements.txt

docker-up:
	docker compose up -d

docker-down:
	docker compose down

reproduce-paper:
	$(PYTHON) analysis/scripts/reproduce_short_paper_tables.py

analysis-pipeline:
	$(PYTHON) analysis/scripts/normalize_aggregate_outputs.py
	$(PYTHON) analysis/scripts/check_baseline_coverage.py
	$(PYTHON) analysis/scripts/simulate_baselines.py
	$(PYTHON) analysis/scripts/analyze_baseline_diagnostics.py
	$(PYTHON) analysis/scripts/normalize_ablation_variables.py
	$(PYTHON) analysis/scripts/run_ablation_analysis.py
	$(PYTHON) analysis/scripts/analyze_representative_cases.py
	$(PYTHON) analysis/scripts/find_joint_explanatory_cases.py
	$(PYTHON) analysis/scripts/reproduce_short_paper_tables.py

check-artifact:
	$(PYTHON) -c "from pathlib import Path; required=['README.md','docker-compose.yml','requirements.txt','requirements-analysis.txt','requirements-benchmark.txt','analysis/scripts/reproduce_short_paper_tables.py','analysis/generated/aggregate_results_all_datasets.csv','analysis/generated/baseline_performance_by_case.csv','analysis/generated/ablation_performance_by_case.csv']; missing=[p for p in required if not Path(p).exists()]; print('Missing files:' if missing else 'All required files found.'); [print(' -', p) for p in missing]; raise SystemExit(1 if missing else 0)"
	$(PYTHON) -c "from pathlib import Path; broken=[]; [broken.append(str(p)) for p in Path('.').rglob('*.md') if '.git' not in p.parts and p.read_text(errors='ignore').count(chr(96)*3) % 2 != 0]; print('Broken markdown fences:' if broken else 'Markdown fences OK.'); [print(' -', p) for p in broken]; raise SystemExit(1 if broken else 0)"


install-benchmark:
	$(PIP) install -r requirements-benchmark.txt

# Shared MongoDB benchmark defaults.
MONGO_HOST ?= 127.0.0.1
MONGO_PORT ?= 27018
MONGO_USERNAME ?= mongo
MONGO_PASSWORD ?= mongo
MONGO_AUTH_SOURCE ?= admin
RUN_PHASE ?= cold hot
BATCH_SIZE ?= 10000
SAMPLE_SIZE ?= 20
REPETITIONS ?= 10

# IMDb benchmark defaults.
IMDB_CATALOG_CSV ?= benchmark/imdb/mongo_experiment_catalog.csv
IMDB_TEMPLATE_CSV ?= benchmark/imdb/benchmark_execution_template.csv
IMDB_RESULTS_DIR ?= results/imdb/$(IMDB_SCALE)
IMDB_BATCH_SIZE ?= $(BATCH_SIZE)
IMDB_SAMPLE_SIZE ?= $(SAMPLE_SIZE)

imdb-benchmark:
	@[ -n "$(IMDB_SCALE)" ] || (echo "Missing IMDB_SCALE. Example: make imdb-benchmark IMDB_SCALE=sf0.25 IMDB_RESULTS_DIR=results/imdb/sf0_25"; exit 1)
	$(PYTHON) benchmark/imdb/run_mongo_benchmark_option_b_incremental.py \
		--catalog-csv $(IMDB_CATALOG_CSV) \
		--template-csv $(IMDB_TEMPLATE_CSV) \
		--results-dir $(IMDB_RESULTS_DIR) \
		--scale-label $(IMDB_SCALE) \
		--run-phase $(RUN_PHASE) \
		--batch-size $(IMDB_BATCH_SIZE) \
		--sample-size $(IMDB_SAMPLE_SIZE) \
		--force-rebuild-scale-db

# FIBEN benchmark defaults.
FIBEN_ARTIFACTS_DIR ?= analysis/fiben
FIBEN_RESULTS_DIR ?= results/fiben/$(FIBEN_SCALE)
FIBEN_BATCH_SIZE ?= 100000
FIBEN_SAMPLE_SIZE ?= $(SAMPLE_SIZE)
FIBEN_REPETITIONS ?= $(REPETITIONS)

fiben-benchmark:
	@[ -n "$(FIBEN_DATA_DIR)" ] || (echo "Missing FIBEN_DATA_DIR. Example: make fiben-benchmark FIBEN_DATA_DIR=/path/to/fiben/sf1 FIBEN_SCALE=sf1 FIBEN_RESULTS_DIR=results/fiben/sf1"; exit 1)
	@[ -n "$(FIBEN_SCALE)" ] || (echo "Missing FIBEN_SCALE. Example: FIBEN_SCALE=sf1"; exit 1)
	$(PYTHON) benchmark/fiben/run_fiben_mongo_benchmark.py \
		--data-dir $(FIBEN_DATA_DIR) \
		--artifacts-dir $(FIBEN_ARTIFACTS_DIR) \
		--results-dir $(FIBEN_RESULTS_DIR) \
		--scale-label $(FIBEN_SCALE) \
		--mongo-host $(MONGO_HOST) \
		--mongo-port $(MONGO_PORT) \
		--mongo-username $(MONGO_USERNAME) \
		--mongo-password $(MONGO_PASSWORD) \
		--mongo-auth-source $(MONGO_AUTH_SOURCE) \
		--run-phase $(RUN_PHASE) \
		--repetitions $(FIBEN_REPETITIONS) \
		--batch-size $(FIBEN_BATCH_SIZE) \
		--sample-size $(FIBEN_SAMPLE_SIZE) \
		--force-rebuild-db

# LDBC SNB benchmark defaults.
LDBC_RESULTS_DIR ?= results/ldbc_snb/$(LDBC_SCALE)
LDBC_BATCH_SIZE ?= 5000
LDBC_SAMPLE_SIZE ?= $(SAMPLE_SIZE)

ldbc-benchmark:
	@[ -n "$(LDBC_DATA_DIR)" ] || (echo "Missing LDBC_DATA_DIR. Example: make ldbc-benchmark LDBC_DATA_DIR=/path/to/ldbc_snb/sf0_1 LDBC_ARTIFACTS_DIR=/path/to/artifacts LDBC_SCALE=sf0.1 LDBC_RESULTS_DIR=results/ldbc_snb/sf0_1"; exit 1)
	@[ -n "$(LDBC_ARTIFACTS_DIR)" ] || (echo "Missing LDBC_ARTIFACTS_DIR. Example: LDBC_ARTIFACTS_DIR=/path/to/ldbc_snb_mongo_configurations"; exit 1)
	@[ -n "$(LDBC_SCALE)" ] || (echo "Missing LDBC_SCALE. Example: LDBC_SCALE=sf0.1"; exit 1)
	$(PYTHON) benchmark/ldbc_snb/run_ldbc_snb_mongo_benchmark.py \
		--data-dir $(LDBC_DATA_DIR) \
		--artifacts-dir $(LDBC_ARTIFACTS_DIR) \
		--results-dir $(LDBC_RESULTS_DIR) \
		--scale-label $(LDBC_SCALE) \
		--mongo-host $(MONGO_HOST) \
		--mongo-port $(MONGO_PORT) \
		--mongo-username $(MONGO_USERNAME) \
		--mongo-password $(MONGO_PASSWORD) \
		--mongo-auth-source $(MONGO_AUTH_SOURCE) \
		--run-phase $(RUN_PHASE) \
		--batch-size $(LDBC_BATCH_SIZE) \
		--sample-size $(LDBC_SAMPLE_SIZE) \
		--force-rebuild-db

clean-generated:
	@echo "No destructive clean is defined. Generated CSV outputs are part of the artifact."
