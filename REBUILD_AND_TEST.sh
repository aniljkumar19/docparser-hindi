#!/bin/bash
# Rebuild API container to ensure latest code is loaded

set -e

echo "=== Rebuilding API Container ==="
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
echo "Step 2: Rebuilding API image (this may take a minute)..."
$DOCKER_COMPOSE build api

echo ""
echo "Step 3: Starting API..."
$DOCKER_COMPOSE up -d api

echo ""
echo "Step 4: Waiting for API to start..."
sleep 15

echo ""
echo "Step 5: Testing API with x-api-key header..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/v1/parse" \
    -H "x-api-key: dev_123" \
    -F "file=@api/samples/sample_invoice.txt" 2>&1)

echo "Response: $RESPONSE"

if echo "$RESPONSE" | grep -q "job_id"; then
    echo ""
    echo "   ✅ SUCCESS! API key is working!"
elif echo "$RESPONSE" | grep -q "Invalid API key"; then
    echo ""
    echo "   ⚠️  Got 'Invalid API key' - API is running but key not recognized"
    echo "   Check: docker-compose logs api | tail -20"
elif echo "$RESPONSE" | grep -q "Missing Bearer token"; then
    echo ""
    echo "   ❌ Still getting 'Missing Bearer token'"
    echo "   The container is still running old code."
    echo "   Try: docker-compose down api && docker-compose up -d --build api"
else
    echo ""
    echo "   ⚠️  Unexpected response"
fi

echo ""
echo "=== Done ==="

