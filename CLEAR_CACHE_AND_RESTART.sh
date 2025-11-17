#!/bin/bash
# Clear Python cache and restart API

set -e

echo "=== Clearing Python Cache and Restarting API ==="
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
echo "Step 2: Clearing Python cache in mounted volume..."
find api -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find api -name "*.pyc" -delete 2>/dev/null || true
find api -name "*.pyo" -delete 2>/dev/null || true
echo "   ✅ Cache cleared"

echo ""
echo "Step 3: Verifying security.py doesn't have 'Missing Bearer token'..."
if grep -q "Missing Bearer token" api/app/security.py; then
    echo "   ❌ ERROR: security.py still has 'Missing Bearer token'!"
    exit 1
else
    echo "   ✅ security.py is correct"
fi

echo ""
echo "Step 4: Starting API..."
$DOCKER_COMPOSE up -d api

echo ""
echo "Step 5: Waiting 15 seconds for API to start..."
sleep 15

echo ""
echo "Step 6: Testing with x-api-key header..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/v1/parse" \
    -H "x-api-key: dev_123" \
    -F "file=@api/samples/sample_invoice.txt" 2>&1)

echo "Response: $RESPONSE"

if echo "$RESPONSE" | grep -q "job_id"; then
    echo ""
    echo "   ✅✅✅ SUCCESS! API key is working! ✅✅✅"
elif echo "$RESPONSE" | grep -q "Missing Bearer token"; then
    echo ""
    echo "   ❌ Still getting 'Missing Bearer token'"
    echo "   This means Python is importing from wrong location or cache"
    echo ""
    echo "   Try: docker-compose down api && docker-compose up -d --build api"
elif echo "$RESPONSE" | grep -q "Missing API key"; then
    echo ""
    echo "   ⚠️  Got 'Missing API key' - new code is running but header not received"
    echo "   Check if header is being sent correctly"
else
    echo ""
    echo "   ⚠️  Unexpected response"
fi

echo ""
echo "=== Done ==="

