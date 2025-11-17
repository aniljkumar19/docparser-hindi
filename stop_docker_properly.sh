#!/bin/bash
# Properly stop Docker API container

set -e

echo "=== Stopping Docker API Container Properly ==="
echo ""

cd "$(dirname "$0")"

echo "Stopping API container (this requires sudo)..."
sudo docker-compose stop api

echo ""
echo "Waiting 3 seconds..."
sleep 3

echo ""
echo "Checking if port 8000 is free..."
if netstat -tlnp 2>/dev/null | grep -q ":8000" || ss -tlnp 2>/dev/null | grep -q ":8000"; then
    echo "   ⚠️  Port 8000 is still in use"
    echo "   Listing processes on port 8000:"
    sudo lsof -i:8000 2>&1 | head -5 || sudo netstat -tlnp | grep :8000
    echo ""
    echo "   You may need to kill docker-proxy processes:"
    echo "   sudo pkill docker-proxy"
else
    echo "   ✅ Port 8000 is now free"
fi

echo ""
echo "=== Done ==="
echo ""
echo "Now you can start the API directly with:"
echo "  ./start_api_direct.sh"

