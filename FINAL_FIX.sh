#!/bin/bash
# Final fix - rebuild container and test

set -e

echo "=== FINAL FIX: Rebuilding API Container ==="
echo ""

cd "$(dirname "$0")"

# Check if we need sudo
if docker ps > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="sudo docker-compose"
fi

echo "Step 1: Stopping and removing API container..."
$DOCKER_COMPOSE stop api
$DOCKER_COMPOSE rm -f api

echo ""
echo "Step 2: Rebuilding API image..."
$DOCKER_COMPOSE build --no-cache api

echo ""
echo "Step 3: Starting API..."
$DOCKER_COMPOSE up -d api

echo ""
echo "Step 4: Waiting 20 seconds for API to fully start..."
sleep 20

echo ""
echo "Step 5: Testing with x-api-key header..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/v1/parse" \
    -H "x-api-key: dev_123" \
    -F "file=@api/samples/sample_invoice.txt" 2>&1)

echo "Full response: $RESPONSE"

if echo "$RESPONSE" | grep -q "job_id"; then
    echo ""
    echo "   ✅✅✅ SUCCESS! API key is working! ✅✅✅"
elif echo "$RESPONSE" | grep -q "Invalid API key"; then
    echo ""
    echo "   ⚠️  Got 'Invalid API key' - API is running but key not recognized"
    echo "   Checking API keys..."
    curl -s http://localhost:8000/debug/api-keys 2>&1 || echo "Debug endpoint not available"
elif echo "$RESPONSE" | grep -q "Missing Bearer token"; then
    echo ""
    echo "   ❌ Still getting 'Missing Bearer token'"
    echo "   The container is importing wrong security.py file"
    echo "   Check: docker-compose logs api | grep -i security"
else
    echo ""
    echo "   ⚠️  Unexpected response"
fi

echo ""
echo "=== Done ==="
echo ""
echo "If it still doesn't work, the issue is Python importing wrong security.py"
echo "Check: docker-compose exec api python3 -c 'import app.security; print(app.security.__file__)'"

