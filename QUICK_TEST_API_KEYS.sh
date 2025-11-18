#!/bin/bash
# Quick test script for API Key system
# Usage: ./QUICK_TEST_API_KEYS.sh [railway|local]

BASE_URL="${1:-railway}"

if [ "$BASE_URL" = "railway" ]; then
    API_BASE="https://docparser-production-aa0e.up.railway.app"
    echo "Testing on Railway: $API_BASE"
else
    API_BASE="http://localhost:8000"
    echo "Testing locally: $API_BASE"
fi

echo ""
echo "=========================================="
echo "Step 1: Create a new API key"
echo "=========================================="
echo ""

RESPONSE=$(curl -s -X POST "$API_BASE/v1/api-keys/" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev_123" \
  -d '{
    "name": "Test Key",
    "tenant_id": "tenant_demo",
    "rate_limit_per_minute": 100,
    "rate_limit_per_hour": 5000
  }')

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

# Extract the key (if jq is available, use it; otherwise use grep/sed)
NEW_KEY=$(echo "$RESPONSE" | grep -o '"key": "[^"]*' | cut -d'"' -f4)
KEY_ID=$(echo "$RESPONSE" | grep -o '"id": "[^"]*' | cut -d'"' -f4)

if [ -z "$NEW_KEY" ]; then
    echo ""
    echo "❌ Failed to create API key. Response above."
    exit 1
fi

echo ""
echo "✅ API Key created!"
echo "   Key ID: $KEY_ID"
echo "   Key: $NEW_KEY"
echo ""
echo "⚠️  SAVE THIS KEY - it's only shown once!"
echo ""

read -p "Press Enter to continue to next step..."

echo ""
echo "=========================================="
echo "Step 2: List all API keys"
echo "=========================================="
echo ""

curl -s -X GET "$API_BASE/v1/api-keys/" \
  -H "x-api-key: dev_123" | python3 -m json.tool 2>/dev/null || \
  curl -s -X GET "$API_BASE/v1/api-keys/" \
  -H "x-api-key: dev_123"

echo ""
read -p "Press Enter to continue to next step..."

echo ""
echo "=========================================="
echo "Step 3: Test using the new API key"
echo "=========================================="
echo ""

if [ ! -f "api/samples/GSTR1.pdf" ] && [ ! -f "samples/GSTR1.pdf" ]; then
    echo "⚠️  No sample file found. Testing with a simple request instead..."
    echo ""
    curl -s -X GET "$API_BASE/v1/jobs?limit=5" \
      -H "x-api-key: $NEW_KEY" | python3 -m json.tool 2>/dev/null || \
      curl -s -X GET "$API_BASE/v1/jobs?limit=5" \
      -H "x-api-key: $NEW_KEY"
else
    SAMPLE_FILE=""
    if [ -f "api/samples/GSTR1.pdf" ]; then
        SAMPLE_FILE="api/samples/GSTR1.pdf"
    elif [ -f "samples/GSTR1.pdf" ]; then
        SAMPLE_FILE="samples/GSTR1.pdf"
    fi
    
    echo "Uploading $SAMPLE_FILE with new API key..."
    curl -s -X POST "$API_BASE/v1/parse" \
      -H "x-api-key: $NEW_KEY" \
      -F "file=@$SAMPLE_FILE" | python3 -m json.tool 2>/dev/null || \
      curl -s -X POST "$API_BASE/v1/parse" \
      -H "x-api-key: $NEW_KEY" \
      -F "file=@$SAMPLE_FILE"
fi

echo ""
read -p "Press Enter to continue to next step..."

echo ""
echo "=========================================="
echo "Step 4: Revoke the API key"
echo "=========================================="
echo ""

if [ -z "$KEY_ID" ]; then
    echo "⚠️  No key ID found. Skipping revoke test."
else
    curl -s -X POST "$API_BASE/v1/api-keys/$KEY_ID/revoke" \
      -H "x-api-key: dev_123" | python3 -m json.tool 2>/dev/null || \
      curl -s -X POST "$API_BASE/v1/api-keys/$KEY_ID/revoke" \
      -H "x-api-key: dev_123"
    
    echo ""
    echo "✅ Key revoked!"
fi

echo ""
read -p "Press Enter to continue to next step..."

echo ""
echo "=========================================="
echo "Step 5: Test that revoked key no longer works"
echo "=========================================="
echo ""

curl -s -X GET "$API_BASE/v1/jobs?limit=5" \
  -H "x-api-key: $NEW_KEY" | python3 -m json.tool 2>/dev/null || \
  curl -s -X GET "$API_BASE/v1/jobs?limit=5" \
  -H "x-api-key: $NEW_KEY"

echo ""
echo "Expected: 401 Unauthorized error"
echo ""

read -p "Press Enter to continue to next step..."

echo ""
echo "=========================================="
echo "Step 6: Reactivate the API key"
echo "=========================================="
echo ""

if [ -z "$KEY_ID" ]; then
    echo "⚠️  No key ID found. Skipping reactivate test."
else
    curl -s -X POST "$API_BASE/v1/api-keys/$KEY_ID/reactivate" \
      -H "x-api-key: dev_123" | python3 -m json.tool 2>/dev/null || \
      curl -s -X POST "$API_BASE/v1/api-keys/$KEY_ID/reactivate" \
      -H "x-api-key: dev_123"
    
    echo ""
    echo "✅ Key reactivated!"
fi

echo ""
echo "=========================================="
echo "Test Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Created API key: $NEW_KEY"
echo "  - Key ID: $KEY_ID"
echo "  - Tested key usage"
echo "  - Tested revoke/reactivate"
echo ""

