#!/bin/bash
# Restart the API server running directly (not Docker)

echo "=== Restarting API Server ==="
echo ""

cd "$(dirname "$0")/api"

# Find the uvicorn process
PID=$(ps aux | grep "uvicorn app.main" | grep -v grep | awk '{print $2}' | head -1)

if [ -z "$PID" ]; then
    echo "❌ API server process not found"
    echo "   Starting new server..."
    cd api
    nohup bash run.sh > /tmp/api.log 2>&1 &
    echo "✅ API server started"
    echo "   Logs: /tmp/api.log"
else
    echo "Found API process: $PID"
    echo "Restarting..."
    kill $PID
    sleep 2
    
    # Start it again
    cd api
    nohup bash run.sh > /tmp/api.log 2>&1 &
    echo "✅ API server restarted"
    echo "   Logs: /tmp/api.log"
fi

echo ""
echo "Waiting for API to be ready..."
sleep 5

echo ""
echo "Testing endpoints..."
curl -s http://localhost:8000/ | head -1
echo ""

# Check if bulk-parse is now available
if curl -s "http://localhost:8000/openapi.json" 2>&1 | grep -q "bulk-parse"; then
    echo "✅ bulk-parse endpoint is now available!"
else
    echo "⚠️  bulk-parse endpoint still not found. Check logs: /tmp/api.log"
fi

