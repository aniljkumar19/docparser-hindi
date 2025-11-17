#!/bin/bash
# Fix API key issue - change override=True to override=False

set -e

echo "=== Fixing API Key Issue ==="
echo ""

cd "$(dirname "$0")"

# Check if we need sudo
if docker ps > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="sudo docker-compose"
fi

echo "Step 1: Fixed code (override=False so docker-compose env vars take precedence)"
echo "   ✅ Updated api/app/main.py"

echo ""
echo "Step 2: Restarting API container..."
$DOCKER_COMPOSE restart api

echo "   Waiting 8 seconds for API to start..."
sleep 8

echo ""
echo "Step 3: Testing API key..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/v1/parse" \
    -H "Authorization: Bearer dev_123" \
    -F "file=@api/samples/sample_invoice.txt" 2>&1)

if echo "$RESPONSE" | grep -q "job_id"; then
    echo "   ✅ SUCCESS! API key is working!"
    echo "   Response: $(echo "$RESPONSE" | head -c 100)..."
elif echo "$RESPONSE" | grep -q "Invalid API key"; then
    echo "   ❌ Still getting 'Invalid API key'"
    echo "   Response: $RESPONSE"
    echo ""
    echo "   Debugging..."
    echo "   Checking if API_KEYS is in docker-compose.yml..."
    if grep -q "API_KEYS: dev_123:tenant_demo" docker-compose.yml; then
        echo "   ✅ API_KEYS found in docker-compose.yml"
    else
        echo "   ❌ API_KEYS missing in docker-compose.yml"
    fi
else
    echo "   ⚠️  Unexpected response: $RESPONSE"
fi

echo ""
echo "=== Done ==="

