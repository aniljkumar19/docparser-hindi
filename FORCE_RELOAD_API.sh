#!/bin/bash
# Force reload API with cleared Python cache

set -e

echo "=== Force Reloading API ==="
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
echo "Step 2: Clearing Python cache in container..."
$DOCKER_COMPOSE run --rm api find /app -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
$DOCKER_COMPOSE run --rm api find /app -name "*.pyc" -delete 2>/dev/null || true

echo ""
echo "Step 3: Starting API..."
$DOCKER_COMPOSE up -d api

echo ""
echo "Step 4: Waiting for API to start..."
sleep 12

echo ""
echo "Step 5: Testing API key with x-api-key header..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/v1/parse" \
    -H "x-api-key: dev_123" \
    -F "file=@api/samples/sample_invoice.txt" 2>&1)

if echo "$RESPONSE" | grep -q "job_id"; then
    echo "   ✅ SUCCESS! API key is working!"
    echo "   Response: $(echo "$RESPONSE" | head -c 150)..."
elif echo "$RESPONSE" | grep -q "Invalid API key"; then
    echo "   ❌ Still getting 'Invalid API key'"
    echo "   Response: $RESPONSE"
elif echo "$RESPONSE" | grep -q "Missing"; then
    echo "   ❌ Still getting error: $RESPONSE"
    echo ""
    echo "   The container might be using cached Python modules."
    echo "   Try: docker-compose down api && docker-compose up -d api"
else
    echo "   ⚠️  Response: $RESPONSE"
fi

echo ""
echo "=== Done ==="

