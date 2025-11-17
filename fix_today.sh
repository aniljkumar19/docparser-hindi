#!/bin/bash
# Fix the issues from yesterday: Start worker and restart API

set -e

echo "=== Fixing DocParser Issues ==="
echo ""

cd "$(dirname "$0")"

# Check if we need sudo
if docker ps > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
    DOCKER="docker"
else
    DOCKER_COMPOSE="sudo docker-compose"
    DOCKER="sudo docker"
fi

echo "1. Starting worker (to process queued jobs)..."
$DOCKER_COMPOSE up -d worker
sleep 3

echo ""
echo "2. Restarting API (to register bulk-parse endpoint)..."
$DOCKER_COMPOSE restart api
sleep 5

echo ""
echo "3. Checking status..."
echo ""

# Check worker
if $DOCKER_COMPOSE ps worker 2>&1 | grep -q "Up"; then
    echo "✅ Worker is running"
else
    echo "❌ Worker is not running"
fi

# Check API
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ API is running"
else
    echo "❌ API is not responding"
fi

# Check bulk endpoint
echo ""
echo "4. Verifying bulk-parse endpoint..."
if curl -s "http://localhost:8000/openapi.json" 2>&1 | grep -q "bulk-parse"; then
    echo "✅ bulk-parse endpoint is registered!"
else
    echo "❌ bulk-parse endpoint still not found"
    echo "   You may need to rebuild: sudo docker-compose up -d --build api"
fi

# Check queued jobs
echo ""
echo "5. Checking queued jobs..."
export PGPASSWORD=docpass
QUEUED=$(psql -h localhost -p 55432 -U docuser -d docdb -t -c "SELECT COUNT(*) FROM jobs WHERE status = 'queued';" 2>&1 | tr -d ' ')
if [ "$QUEUED" -gt 0 ]; then
    echo "⚠️  $QUEUED jobs still queued (worker should process them soon)"
else
    echo "✅ No queued jobs"
fi
unset PGPASSWORD

echo ""
echo "=== Done ==="
echo ""
echo "Try bulk upload now: http://localhost:3000/bulk-upload"

