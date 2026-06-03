PYTHON ?= python
PIP ?= pip

.PHONY: help docker-up docker-down install-analysis reproduce-paper analysis-pipeline check-artifact clean-generated

help:
	@echo "SchemaLens reproducibility commands"
	@echo ""
	@echo "Lightweight verification:"
	@echo "  make install-analysis      Install pinned analysis dependencies"
	@echo "  make reproduce-paper       Reproduce short-paper Table 1 and Table 2 CSVs"
	@echo "  make analysis-pipeline     Regenerate normalized, baseline, ablation, and paper outputs"
	@echo "  make check-artifact        Run basic artifact consistency checks"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up             Start MongoDB with Docker Compose"
	@echo "  make docker-down           Stop MongoDB with Docker Compose"
	@echo ""
	@echo "Full benchmark targets will be added with dataset-path variables."

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
	$(PYTHON) -c "from pathlib import Path; broken=[]; [broken.append(str(p)) for p in Path('.').rglob('*.md') if '.git' not in p.parts and p.read_text(errors='ignore').count('```') % 2 != 0]; print('Broken markdown fences:' if broken else 'Markdown fences OK.'); [print(' -', p) for p in broken]; raise SystemExit(1 if broken else 0)"

clean-generated:
	@echo "No destructive clean is defined. Generated CSV outputs are part of the artifact."
