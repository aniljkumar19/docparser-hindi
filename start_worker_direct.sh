#!/bin/bash
# Start worker directly (no Docker) to process queued jobs

set -e

echo "=== Starting Worker Directly (No Docker) ==="
echo ""

cd "$(dirname "$0")/api"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found. Run ./start_api_direct.sh first."
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

echo "Starting RQ worker to process jobs..."
echo "Press Ctrl+C to stop"
echo ""

# Start RQ worker
rq worker docparser-queue --url "$REDIS_URL"

