#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$HOME/Documents/framework_test/ldbc_snb_benchmark"
cd "$BASE_DIR"

MANIFEST="results/physical_materialization/sf3_full_comparison_consolidated/materialization/physical_materialization_manifest.csv"
OUT_BASE="results/physical_benchmark/ldbc_snb_sf3_full_10cold_10hot"

mkdir -p "$OUT_BASE"

GLOBAL_LOG="$OUT_BASE/full_run.log"
exec > >(tee -a "$GLOBAL_LOG") 2>&1

echo "============================================================"
echo "LDBC SNB SF3 full physical benchmark"
echo "Protocol: 10 cold + 10 hot, warmup 0"
echo "Started at: $(date)"
echo "Output base: $OUT_BASE"
echo "Global log: $GLOBAL_LOG"
echo "============================================================"

get_ids() {
  local Q="$1"

  python - "$Q" <<'PY'
import sys
import pandas as pd
from pathlib import Path

q = sys.argv[1]
base = Path("results/physical_benchmark")

if q == "IC1":
    path = base / "sf3_parameter_pools/ic1_parameter_pairs.csv"
elif q == "IC3":
    path = base / "sf3_parameter_pools/ic3_parameter_triples.csv"
elif q == "IC4":
    path = base / "sf3_parameter_pools/ic4_parameter_ids.csv"
elif q == "IC6":
    path = base / "sf3_parameter_pools/ic6_parameter_pairs.csv"
elif q == "IC7":
    path = base / "sf3_parameter_pools/ic7_parameter_ids.csv"
elif q.startswith("IC"):
    path = base / "sf3_parameter_pools/ic_parameter_pools.csv"
elif q.startswith("IS"):
    path = base / "sf3_parameter_pools/is_parameter_pools.csv"
elif q.startswith("INS"):
    path = base / "sf3_parameter_pools/ins_parameter_pools.csv"
else:
    raise SystemExit(f"Unknown query: {q}")

if not path.exists():
    raise SystemExit(f"Missing parameter file for {q}: {path}")

df = pd.read_csv(path)

if "official_id" in df.columns:
    df = df[df["official_id"].astype(str) == q]

vals = df["parameter_id"].astype(str).tolist()

if not vals:
    raise SystemExit(f"No parameters found for {q} in {path}")

for v in vals:
    print(v)
PY
}

run_one() {
  local Q="$1"
  local PHASE="$2"
  local WARMUP="$3"
  local RUNS="$4"

  mapfile -t IDS < <(get_ids "$Q")

  if [ "${#IDS[@]}" -eq 0 ]; then
    echo "ERROR: empty parameter list for $Q"
    exit 1
  fi

  local RESULTS="$OUT_BASE/${Q,,}_${PHASE}"

  rm -rf "$RESULTS"
  mkdir -p "$RESULTS"

  echo ""
  echo "============================================================"
  echo "Running $Q / $PHASE"
  echo "Warmup: $WARMUP"
  echo "Runs: $RUNS"
  echo "Parameters: ${IDS[*]}"
  echo "Results: $RESULTS"
  echo "============================================================"

  python run_ldbc_snb_physical_benchmark.py \
    --manifest "$MANIFEST" \
    --results-dir "$RESULTS" \
    --official-id "$Q" \
    --scale-label sf3 \
    --mongo-host 127.0.0.1 \
    --mongo-port 27018 \
    --mongo-username mongo \
    --mongo-password mongo \
    --mongo-auth-source admin \
    --owner-ids "${IDS[@]}" \
    --sample-size "${#IDS[@]}" \
    --warmup-runs "$WARMUP" \
    --benchmark-runs "$RUNS" \
    --run-phase "$PHASE" \
    --resource-monitor \
    --resource-monitor-interval-sec 5 \
    --docker-container-name ldbc_mongodb_physical \
    --mongo-data-dir /home/hudson/mongo_data/ldbc_physical \
    --save-raw-explain \
    2>&1 | tee "$RESULTS/run_${PHASE}.log"
}

QUERIES=(
  IC1 IC2 IC3 IC4 IC5 IC6 IC7
  IS1 IS2 IS3 IS4 IS5 IS6 IS7
  INS1 INS2 INS3 INS4 INS5 INS6 INS7 INS8
)

for Q in "${QUERIES[@]}"; do
  run_one "$Q" cold 0 10
  run_one "$Q" hot 0 10
done

echo ""
echo "All SF3 10 cold + 10 hot runs completed."
echo "Finished at: $(date)"
echo "Results in: $OUT_BASE"
echo "Global log: $GLOBAL_LOG"
