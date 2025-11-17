#!/bin/bash
# Start the Next.js frontend

set -e

echo "=== Starting Frontend ==="
echo ""

cd "$(dirname "$0")/dashboard"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

echo ""
echo "Starting Next.js dev server on http://localhost:3000"
echo "Press Ctrl+C to stop"
echo ""

npm run dev
