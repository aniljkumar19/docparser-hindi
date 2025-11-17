#!/bin/bash
# Final fix for API key - adds fallback and restarts

set -e

echo "=== Final API Key Fix ==="
echo ""

cd "$(dirname "$0")"

# Check if we need sudo
if docker ps > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="sudo docker-compose"
fi

echo "Step 1: Updated security.py with fallback API key"
echo "   ✅ Code updated"

echo ""
echo "Step 2: Restarting API..."
$DOCKER_COMPOSE restart api
echo "   Waiting 10 seconds for full restart..."
sleep 10

echo ""
echo "Step 3: Testing API key..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/v1/parse" \
    -H "Authorization: Bearer dev_123" \
    -F "file=@api/samples/sample_invoice.txt" 2>&1)

if echo "$RESPONSE" | grep -q "job_id"; then
    echo "   ✅ SUCCESS! API key is working!"
    echo "   Response: $(echo "$RESPONSE" | head -c 150)..."
elif echo "$RESPONSE" | grep -q "Invalid API key"; then
    echo "   ❌ Still getting 'Invalid API key'"
    echo "   Full response: $RESPONSE"
    echo ""
    echo "   Let's check what the API sees..."
    echo "   (Debug endpoint should be available after restart)"
else
    echo "   ⚠️  Response: $RESPONSE"
fi

echo ""
echo "=== Done ==="
echo ""
echo "If it still doesn't work, check:"
echo "  1. docker-compose logs api | tail -20"
echo "  2. curl http://localhost:8000/debug/api-keys"

