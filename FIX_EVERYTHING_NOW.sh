#!/bin/bash
# Fix all DocParser issues in one go

set -e

echo "=== Fixing All DocParser Issues ==="
echo ""

cd "$(dirname "$0")"

# Check if we need sudo
if docker ps > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="sudo docker-compose"
fi

echo "Step 1: Restarting API (fixes bulk endpoint + API keys)..."
$DOCKER_COMPOSE restart api
echo "   Waiting 8 seconds for API to start..."
sleep 8

echo ""
echo "Step 2: Starting worker (processes queued jobs)..."
$DOCKER_COMPOSE up -d worker
echo "   Waiting 3 seconds..."
sleep 3

echo ""
echo "Step 3: Verifying fixes..."
echo ""

# Check API
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ API is running"
else
    echo "❌ API not responding"
fi

# Check bulk endpoint
if curl -s "http://localhost:8000/openapi.json" 2>&1 | grep -q "bulk-parse"; then
    echo "✅ Bulk-parse endpoint registered!"
else
    echo "❌ Bulk-parse endpoint still missing"
fi

# Check API key
if curl -s -X POST "http://localhost:8000/v1/parse" -H "Authorization: Bearer dev_123" -F "file=@api/samples/sample_invoice.txt" 2>&1 | grep -q "job_id"; then
    echo "✅ API key working!"
else
    echo "❌ API key still not working"
fi

# Check worker
if $DOCKER_COMPOSE ps worker 2>&1 | grep -q "Up"; then
    echo "✅ Worker is running"
else
    echo "❌ Worker not running"
fi

# Check queued jobs
export PGPASSWORD=docpass
QUEUED=$(psql -h localhost -p 55432 -U docuser -d docdb -t -c "SELECT COUNT(*) FROM jobs WHERE status = 'queued';" 2>&1 | tr -d ' ')
unset PGPASSWORD

if [ "$QUEUED" -gt 0 ]; then
    echo "⚠️  $QUEUED jobs still queued (worker should process them soon)"
else
    echo "✅ No queued jobs"
fi

echo ""
echo "=== Done ==="
echo ""
echo "Test your app:"
echo "  - Single upload: http://localhost:3000"
echo "  - Bulk upload: http://localhost:3000/bulk-upload"
echo ""

