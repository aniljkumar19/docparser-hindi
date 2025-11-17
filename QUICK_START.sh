#!/bin/bash
# Quick start: Stop Docker API and start direct API

set -e

echo "=== Quick Start: Direct API (No Docker) ==="
echo ""

cd "$(dirname "$0")"

echo "Step 1: Stopping Docker API (if running)..."
sudo docker-compose stop api 2>&1 || echo "Docker API not running or already stopped"

echo ""
echo "Step 2: Waiting 3 seconds..."
sleep 3

echo ""
echo "Step 3: Checking port 8000..."
if netstat -tlnp 2>/dev/null | grep -q ":8000" || ss -tlnp 2>/dev/null | grep -q ":8000"; then
    echo "   ⚠️  Port 8000 is still in use"
    echo "   Killing process..."
    sudo fuser -k 8000/tcp 2>&1 || sudo kill -9 $(sudo lsof -ti:8000) 2>&1 || echo "   Please manually stop the process on port 8000"
    sleep 2
fi

echo ""
echo "Step 4: Starting API directly..."
cd api
./../start_api_direct.sh

