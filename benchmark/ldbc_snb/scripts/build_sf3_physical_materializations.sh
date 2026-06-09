#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$HOME/Documents/framework_test/ldbc_snb_benchmark"
cd "$BASE_DIR"

DATA_DIR="data/sf3"
ARTIFACTS_DIR="ldbc_snb_sf0_1_mongo_benchmark_bundle"
EXECUTION_PLAN="benchmark_execution_plan.csv"
RESULTS_DIR="results/physical_materialization/sf3_full_comparison_consolidated"

mkdir -p "$RESULTS_DIR"

LOG_FILE="$RESULTS_DIR/build_sf1_physical_materializations.log"

echo "============================================================" | tee "$LOG_FILE"
echo "Building LDBC SNB SF3 physical MongoDB materializations" | tee -a "$LOG_FILE"
echo "Started at: $(date)" | tee -a "$LOG_FILE"
echo "DATA_DIR: $DATA_DIR" | tee -a "$LOG_FILE"
echo "ARTIFACTS_DIR: $ARTIFACTS_DIR" | tee -a "$LOG_FILE"
echo "EXECUTION_PLAN: $EXECUTION_PLAN" | tee -a "$LOG_FILE"
echo "RESULTS_DIR: $RESULTS_DIR" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"

python build_ldbc_snb_physical_materializations.py \
  --data-dir "$DATA_DIR" \
  --artifacts-dir "$ARTIFACTS_DIR" \
  --execution-plan "$EXECUTION_PLAN" \
  --results-dir "$RESULTS_DIR" \
  --scale-label sf3 \
  --mongo-host 127.0.0.1 \
  --mongo-port 27018 \
  --mongo-username mongo \
  --mongo-password mongo \
  --mongo-auth-source admin \
  --db-prefix ldbc_snb_phys_sf3 \
  --batch-size 50000 \
  --max-summary-items 5000 \
  --force-rebuild-db \
  --verbose \
  2>&1 | tee -a "$LOG_FILE"

echo "============================================================" | tee -a "$LOG_FILE"
echo "Finished at: $(date)" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"
