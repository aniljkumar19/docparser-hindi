#!/bin/bash
# Start API and worker together without Docker

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT_DIR/logs"
API_LOG="$LOG_DIR/api.log"
WORKER_LOG="$LOG_DIR/worker.log"
API_PID_FILE="$ROOT_DIR/api.pid"
WORKER_PID_FILE="$ROOT_DIR/worker.pid"

mkdir -p "$LOG_DIR"

cd "$ROOT_DIR"

check_redis() {
  if command -v redis-cli >/dev/null 2>&1; then
    if redis-cli -h localhost -p 6379 ping >/dev/null 2>&1; then
      echo "✅ Redis reachable at redis://localhost:6379"
    else
      echo "⚠️  Warning: Unable to reach Redis at localhost:6379. Jobs will process synchronously."
    fi
  else
    echo "ℹ️  redis-cli not installed; skipping Redis connectivity check."
  fi
}

start_api() {
  if lsof -i:8000 >/dev/null 2>&1; then
    echo "⚠️  API already running on port 8000"
    return
  fi

  echo "🚀 Starting API (logs: $API_LOG)"
  nohup "$ROOT_DIR/start_api_direct.sh" >> "$API_LOG" 2>&1 &
  API_PID=$!
  echo $API_PID > "$API_PID_FILE"
  sleep 2
  echo "  ↳ PID $API_PID"
  tail -n 5 "$API_LOG" || true
}

start_worker() {
  if pgrep -f "rq worker docparser-queue" >/dev/null 2>&1; then
    echo "⚠️  Worker already running"
    return
  fi

  echo "🚀 Starting worker (logs: $WORKER_LOG)"
  nohup "$ROOT_DIR/start_worker_direct.sh" >> "$WORKER_LOG" 2>&1 &
  WORKER_PID=$!
  echo $WORKER_PID > "$WORKER_PID_FILE"
  sleep 2
  echo "  ↳ PID $WORKER_PID"
  tail -n 5 "$WORKER_LOG" || true
}

check_redis
start_api
start_worker

echo ""
echo "✅ All services started."
echo "   API log:    $API_LOG"
echo "   Worker log: $WORKER_LOG"
echo ""
echo "To stop them:"
echo "  pkill -f 'uvicorn app.main:app'"
echo "  pkill -f 'rq worker docparser-queue'"
