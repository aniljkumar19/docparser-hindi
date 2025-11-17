#!/bin/bash
# Test API key after restart

echo "=== Testing API Key ==="
echo ""

# Test 1: Check if API is running
echo "1. Checking if API is running..."
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "   ✅ API is running"
else
    echo "   ❌ API is not running"
    echo "   Start it with: docker-compose up -d api"
    exit 1
fi

# Test 2: Test with Authorization Bearer
echo ""
echo "2. Testing with Authorization Bearer header..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/v1/parse" \
    -H "Authorization: Bearer dev_123" \
    -F "file=@api/samples/sample_invoice.txt" 2>&1)

if echo "$RESPONSE" | grep -q "job_id"; then
    echo "   ✅ SUCCESS! API key is working!"
    echo "   Response: $(echo "$RESPONSE" | head -c 100)..."
elif echo "$RESPONSE" | grep -q "Invalid API key"; then
    echo "   ❌ Invalid API key"
    echo "   Response: $RESPONSE"
    echo ""
    echo "   The API container needs to be restarted to load API_KEYS."
    echo "   Run: docker-compose restart api"
    echo "   Then wait 10 seconds and try again."
elif echo "$RESPONSE" | grep -q "Missing"; then
    echo "   ❌ Missing API key"
    echo "   Response: $RESPONSE"
else
    echo "   ⚠️  Unexpected response: $RESPONSE"
fi

echo ""
echo "=== Done ==="

