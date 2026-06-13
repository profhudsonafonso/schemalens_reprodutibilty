#!/usr/bin/env bash

INTERVAL="${1:-10}"
LOG_DIR="de_lima_mello_2015_implementation/results/fiben/materialization/sf10/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/resource_monitor_$(date +%Y%m%d_%H%M%S).log"

echo "Monitoring every ${INTERVAL}s"
echo "Log file: $LOG_FILE"
echo "Press Ctrl+C to stop."

while true; do
  {
    echo
    echo "============================================================"
    echo "TIME: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "============================================================"

    echo
    echo "### LOAD / CPU"
    uptime
    top -bn1 | head -5

    echo
    echo "### MEMORY"
    free -h

    echo
    echo "### DISK SPACE"
    df -h / /home /var/lib/docker 2>/dev/null || df -h

    echo
    echo "### DISK I/O"
    if command -v iostat >/dev/null 2>&1; then
      iostat -xz 1 1
    else
      vmstat 1 2 | tail -n 3
    fi

    echo
    echo "### TOP MEMORY PROCESSES"
    ps -eo pid,ppid,pcpu,pmem,rss,vsz,etime,cmd --sort=-%mem | head -15

    echo
    echo "### TOP CPU PROCESSES"
    ps -eo pid,ppid,pcpu,pmem,rss,vsz,etime,cmd --sort=-%cpu | head -15

    echo
    echo "### MONGODB / PYTHON RELATED PROCESSES"
    ps -eo pid,ppid,pcpu,pmem,rss,vsz,etime,cmd --sort=-%mem | grep -E 'mongod|python|run_lmm|mongo' | grep -v grep | head -20 || true

    echo
    echo "### DOCKER STATS"
    if command -v docker >/dev/null 2>&1; then
      docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.BlockIO}}\t{{.NetIO}}" 2>/dev/null || true
    else
      echo "docker command not found"
    fi
  } | tee -a "$LOG_FILE"

  sleep "$INTERVAL"
done
