#!/bin/bash
# Debug and fix API key issue

set -e

echo "=== Debugging API Key Issue ==="
echo ""

cd "$(dirname "$0")"

# Check if we need sudo
if docker ps > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="sudo docker-compose"
fi

echo "Step 1: Stopping API..."
$DOCKER_COMPOSE stop api

echo ""
echo "Step 2: Removing API container..."
$DOCKER_COMPOSE rm -f api

echo ""
echo "Step 3: Rebuilding API (no cache)..."
$DOCKER_COMPOSE build --no-cache api

echo ""
echo "Step 4: Starting API..."
$DOCKER_COMPOSE up -d api

echo ""
echo "Step 5: Waiting 20 seconds for API to start..."
sleep 20

echo ""
echo "Step 6: Testing with x-api-key header..."
curl -v -X POST "http://localhost:8000/v1/parse" \
    -H "x-api-key: dev_123" \
    -F "file=@api/samples/sample_invoice.txt" 2>&1 | grep -E "(< HTTP|detail|AUTH|SECURITY)" | head -10

echo ""
echo "Step 7: Checking API logs for debug output..."
$DOCKER_COMPOSE logs api 2>&1 | tail -30 | grep -E "(AUTH|SECURITY|DEBUG|error|Error)" | head -15

echo ""
echo "=== Done ==="
echo ""
echo "If you see 'AUTH DEBUG' or 'SECURITY DEBUG' in logs, the new code is running."
echo "If you see 'Missing Bearer token', old code is still running."

