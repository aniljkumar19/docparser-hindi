#!/bin/bash
# Stop Docker API container to free port 8000

set -e

echo "=== Stopping Docker API Container ==="
echo ""

cd "$(dirname "$0")"

# Check if we need sudo
if docker ps > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="sudo docker-compose"
fi

echo "Stopping API container..."
$DOCKER_COMPOSE stop api 2>&1 || echo "Container already stopped or not running"

echo ""
echo "Checking if port 8000 is free..."
sleep 2
if netstat -tlnp 2>/dev/null | grep -q ":8000" || ss -tlnp 2>/dev/null | grep -q ":8000"; then
    echo "   ⚠️  Port 8000 is still in use"
    echo "   Killing process on port 8000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || fuser -k 8000/tcp 2>/dev/null || echo "Could not kill process - you may need to do it manually"
else
    echo "   ✅ Port 8000 is now free"
fi

echo ""
echo "=== Done ==="
echo ""
echo "Now you can start the API directly with:"
echo "  ./start_api_direct.sh"

