#!/usr/bin/env bash

OUT="$1"
CONTAINER="${2:-ldbc_mongodb_physical}"
MONGO_DATA_DIR="${3:-/home/hudson/mongo_data/ldbc_physical}"

mkdir -p "$(dirname "$OUT")"

echo "timestamp,container,running,status,exit_code,oom_killed,mem_free_mb,mem_used_mb,mem_total_mb,mem_percent,disk_free_gb,disk_used_gb,docker_cpu,docker_mem,docker_mem_percent,docker_block_io,docker_pids" > "$OUT"

while true; do
  TS=$(date -Iseconds)

  INSPECT=$(docker inspect "$CONTAINER" 2>/dev/null || true)

  if [ -n "$INSPECT" ]; then
    RUNNING=$(echo "$INSPECT" | python -c "import sys,json; d=json.load(sys.stdin)[0]; print(d['State'].get('Running'))" 2>/dev/null || echo "")
    STATUS=$(echo "$INSPECT" | python -c "import sys,json; d=json.load(sys.stdin)[0]; print(d['State'].get('Status'))" 2>/dev/null || echo "")
    EXIT_CODE=$(echo "$INSPECT" | python -c "import sys,json; d=json.load(sys.stdin)[0]; print(d['State'].get('ExitCode'))" 2>/dev/null || echo "")
    OOM=$(echo "$INSPECT" | python -c "import sys,json; d=json.load(sys.stdin)[0]; print(d['State'].get('OOMKilled'))" 2>/dev/null || echo "")
  else
    RUNNING=""
    STATUS="missing"
    EXIT_CODE=""
    OOM=""
  fi

  MEM_FREE=$(free -m | awk '/Mem:/ {print $7}')
  MEM_USED=$(free -m | awk '/Mem:/ {print $3}')
  MEM_TOTAL=$(free -m | awk '/Mem:/ {print $2}')
  MEM_PCT=$(free | awk '/Mem:/ {printf "%.2f", ($3/$2)*100}')

  if [ -d "$MONGO_DATA_DIR" ]; then
    DISK_FREE=$(df -BG "$MONGO_DATA_DIR" | awk 'NR==2 {gsub("G","",$4); print $4}')
    DISK_USED=$(df -BG "$MONGO_DATA_DIR" | awk 'NR==2 {gsub("G","",$3); print $3}')
  else
    DISK_FREE=""
    DISK_USED=""
  fi

  STATS=$(docker stats --no-stream --format "{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.BlockIO}},{{.PIDs}}" "$CONTAINER" 2>/dev/null || echo ",,,,")
  DOCKER_CPU=$(echo "$STATS" | cut -d',' -f1)
  DOCKER_MEM=$(echo "$STATS" | cut -d',' -f2)
  DOCKER_MEM_PCT=$(echo "$STATS" | cut -d',' -f3)
  DOCKER_BLOCK_IO=$(echo "$STATS" | cut -d',' -f4)
  DOCKER_PIDS=$(echo "$STATS" | cut -d',' -f5)

  echo "$TS,$CONTAINER,$RUNNING,$STATUS,$EXIT_CODE,$OOM,$MEM_FREE,$MEM_USED,$MEM_TOTAL,$MEM_PCT,$DISK_FREE,$DISK_USED,$DOCKER_CPU,\"$DOCKER_MEM\",$DOCKER_MEM_PCT,\"$DOCKER_BLOCK_IO\",$DOCKER_PIDS" >> "$OUT"

  sleep 3
done
