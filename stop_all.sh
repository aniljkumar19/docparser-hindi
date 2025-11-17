#!/bin/bash
# Stop API and worker processes started without Docker

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
API_PID_FILE="$ROOT_DIR/api.pid"
WORKER_PID_FILE="$ROOT_DIR/worker.pid"

stop_process() {
  local name="$1"
  local pid_file="$2"
  local pattern="$3"

  if [ -f "$pid_file" ]; then
    local pid
    pid=$(cat "$pid_file")
    if ps -p "$pid" >/dev/null 2>&1; then
      echo "🔻 Stopping $name (PID $pid)"
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
  fi

  if pgrep -f "$pattern" >/dev/null 2>&1; then
    echo "🔻 Stopping extra $name processes"
    pkill -f "$pattern" || true
  fi
}

stop_process "API" "$API_PID_FILE" "uvicorn app.main:app"
stop_process "worker" "$WORKER_PID_FILE" "rq worker docparser-queue"

echo "✅ All processes stopped."
