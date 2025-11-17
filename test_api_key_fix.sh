#!/bin/bash
# Test and fix API key issue

echo "=== Testing API Key Configuration ==="
echo ""

cd "$(dirname "$0")"

# Check .env file
echo "1. Checking .env file..."
if grep -q "API_KEYS=dev_123:tenant_demo" api/.env; then
    echo "   ✅ API_KEYS found in .env"
else
    echo "   ❌ API_KEYS missing in .env"
    echo "   Adding it..."
    echo "API_KEYS=dev_123:tenant_demo" >> api/.env
fi

# Check docker-compose
echo ""
echo "2. Checking docker-compose.yml..."
if grep -q "API_KEYS: dev_123:tenant_demo" docker-compose.yml; then
    echo "   ✅ API_KEYS found in docker-compose.yml"
else
    echo "   ❌ API_KEYS missing in docker-compose.yml"
fi

echo ""
echo "3. Testing API..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/v1/parse" \
    -H "Authorization: Bearer dev_123" \
    -F "file=@api/samples/sample_invoice.txt" 2>&1)

if echo "$RESPONSE" | grep -q "job_id"; then
    echo "   ✅ API key is working!"
    echo "   Response: $RESPONSE"
elif echo "$RESPONSE" | grep -q "Invalid API key"; then
    echo "   ❌ Still getting 'Invalid API key'"
    echo ""
    echo "   The API container needs to be restarted to load the keys."
    echo "   Run: sudo docker-compose restart api"
else
    echo "   ⚠️  Unexpected response: $RESPONSE"
fi

echo ""
echo "=== Summary ==="
echo "If API key still doesn't work after restart, the issue is:"
echo "  - Container not reading environment variables correctly"
echo "  - Or .env file path mismatch (/app/.env vs actual location)"

