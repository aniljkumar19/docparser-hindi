#!/bin/bash
# Verify bulk-parse endpoint and provide fix instructions

echo "=== Checking Bulk-Parse Endpoint ==="
echo ""

# Check if endpoint exists in code
if grep -q '@app.post("/v1/bulk-parse")' api/app/main.py; then
    echo "✅ Endpoint exists in code (line 118)"
else
    echo "❌ Endpoint NOT found in code"
    exit 1
fi

# Check if endpoint is registered in running API
echo ""
echo "Checking running API..."
ENDPOINTS=$(curl -s "http://localhost:8000/openapi.json" 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    posts = [p for p in d.get('paths', {}).keys() if d['paths'][p].get('post')]
    print(' '.join(posts))
except:
    print('')
" 2>/dev/null)

if echo "$ENDPOINTS" | grep -q "bulk-parse"; then
    echo "✅ Endpoint is registered in running API"
    echo ""
    echo "The endpoint should work! Try uploading again."
else
    echo "❌ Endpoint is NOT registered in running API"
    echo ""
    echo "Registered POST endpoints:"
    echo "$ENDPOINTS" | tr ' ' '\n' | sed 's/^/  /'
    echo ""
    echo "=== FIX REQUIRED ==="
    echo ""
    echo "The endpoint exists in code but isn't loaded. Restart the API:"
    echo ""
    echo "  sudo docker-compose restart api"
    echo ""
    echo "Or restart all services:"
    echo ""
    echo "  sudo docker-compose restart"
    echo ""
    echo "After restart, wait 10 seconds and try again."
fi

