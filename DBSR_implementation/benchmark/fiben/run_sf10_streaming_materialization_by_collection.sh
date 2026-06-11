#!/usr/bin/env bash
set -euo pipefail

mkdir -p DBSR_implementation/generated/fiben/logs

DB="dbsr_fiben_sf10_source_full"
PLAN="DBSR_implementation/generated/fiben/dbsr_materialization_plan_structural.json"
SCRIPT="DBSR_implementation/benchmark/fiben/run_dbsr_materialization_loader.py"

TARGETS=(
  dbsr_rank01_listedsecurity
  dbsr_rank02_transaction_listedsecurity
  dbsr_rank03_corporation
  dbsr_rank04_person
  dbsr_rank05_corporation_country
  dbsr_rank06_corporation_industry
  dbsr_rank07_financialserviceaccount_holding_listedsecurity
  dbsr_rank08_corporation_security_listedsecurity
  dbsr_rank09_financialserviceaccount_transaction_listedsecurity
  dbsr_rank10_person_financialserviceaccount_transaction
  dbsr_rank11_person_financialserviceaccount_holding
  dbsr_rank12_listedsecurity_security_corporation
  dbsr_rank13_financialreport_reportelement_statementelement
  dbsr_rank14_security_corporation_industry
  dbsr_rank15_security_corporation_country
)

for TARGET in "${TARGETS[@]}"; do
  echo
  echo "=== Materializing ${TARGET} ==="
  echo

  LOG="DBSR_implementation/generated/fiben/logs/materialize_sf10_full_${TARGET}_$(date +%Y%m%d_%H%M%S).log"

  CMD=(
    env
    PYTHONUNBUFFERED=1
    PYTHONPATH=DBSR_implementation/src
    python
    "${SCRIPT}"
    --materialization-plan "${PLAN}"
    --scale-label "sf10_full_materialization_streaming_${TARGET}"
    --mongo-host 127.0.0.1
    --mongo-port 27018
    --mongo-username mongo
    --mongo-password mongo
    --mongo-auth-source admin
    --mongo-db "${DB}"
    --root-limit 0
    --child-limit 0
    --batch-size 100000
    --progress-interval 100000
    --target-collection "${TARGET}"
    --drop-target
    --execute
  )

  time "${CMD[@]}" 2>&1 | tee "${LOG}"
done
