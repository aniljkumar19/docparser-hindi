#!/bin/bash
set -e

# Start script for Railway - runs both API server and RQ worker (if Redis available)

echo "🚀 Starting DocParser API..."

# Check if Redis is available
REDIS_URL="${REDIS_URL:-}"
if [ -n "$REDIS_URL" ] && [[ ! "$REDIS_URL" =~ ^redis://(localhost|127\.0\.0\.1) ]]; then
    echo "✅ Redis detected: $REDIS_URL"
    echo "🔄 Starting RQ worker in background..."
    
    # Start RQ worker in background
    rq worker -u "$REDIS_URL" --worker-ttl 600 docparser-queue &
    WORKER_PID=$!
    echo "   Worker PID: $WORKER_PID"
    
    # Function to kill worker on exit
    cleanup() {
        echo "🛑 Shutting down worker (PID: $WORKER_PID)..."
        kill $WORKER_PID 2>/dev/null || true
        wait $WORKER_PID 2>/dev/null || true
    }
    trap cleanup EXIT INT TERM
else
    echo "ℹ️  Redis not configured. Jobs will process synchronously."
fi

# Start API server (foreground - this is the main process)
echo "🌐 Starting FastAPI server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

