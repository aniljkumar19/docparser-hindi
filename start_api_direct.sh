#!/bin/bash
# Start API directly without Docker (much simpler!)

set -e

echo "=== Starting API Directly (No Docker) ==="
echo ""

cd "$(dirname "$0")/api"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies if needed
if [ ! -f ".venv/.installed" ]; then
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    touch .venv/.installed
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Set API_KEYS if not set
export API_KEYS=${API_KEYS:-"dev_123:tenant_demo"}

echo ""
echo "Starting API on http://localhost:8000"
echo "API_KEYS: $API_KEYS"
echo "Press Ctrl+C to stop"
echo ""

# Start uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

