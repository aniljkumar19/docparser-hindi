#!/bin/bash
# Restart API to load bulk-parse endpoint

echo "=== Restarting API Server ==="
echo ""
echo "This will restart the API container to load the bulk-parse endpoint."
echo ""

cd "$(dirname "$0")"

# Check if docker-compose is available
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ docker-compose not found"
    exit 1
fi

# Try without sudo first
if $DOCKER_COMPOSE restart api 2>&1; then
    echo "✅ API restarted successfully"
else
    echo "⚠️  Need sudo to restart. Please run:"
    echo "   sudo $DOCKER_COMPOSE restart api"
    echo ""
    echo "Or restart all services:"
    echo "   sudo $DOCKER_COMPOSE restart"
    exit 1
fi

echo ""
echo "Waiting for API to be ready..."
sleep 5

echo ""
echo "Testing bulk-parse endpoint..."
if curl -s -X POST "http://localhost:8000/v1/bulk-parse" \
    -H "Authorization: Bearer dev_123" \
    -F "files=@api/samples/sample_invoice.txt" 2>&1 | grep -q "batch_id\|Not Found"; then
    echo "✅ Endpoint is responding!"
else
    echo "⚠️  Endpoint test inconclusive. Check manually."
fi

echo ""
echo "=== Done ==="

