#!/bin/bash

# Configuration - UPDATE THESE
API_BASE="https://docparser-production-aa0e.up.railway.app"
ADMIN_TOKEN="${ADMIN_TOKEN:-YOUR_ADMIN_TOKEN_HERE}"

if [ "$ADMIN_TOKEN" = "YOUR_ADMIN_TOKEN_HERE" ]; then
    echo "❌ Error: Set ADMIN_TOKEN environment variable"
    echo "   export ADMIN_TOKEN=your-token-here"
    exit 1
fi

echo "=========================================="
echo "Testing New API Key System"
echo "=========================================="
echo ""

echo "Step 1: Creating new API key..."
RESPONSE=$(curl -s -X POST "${API_BASE}/admin/api-keys?name=Test+Key+$(date +%s)" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}")

if echo "$RESPONSE" | grep -q "api_key"; then
    echo "✅ API Key created successfully!"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    
    # Extract the key
    NEW_KEY=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('api_key', ''))" 2>/dev/null)
    KEY_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('id', ''))" 2>/dev/null)
    
    if [ -z "$NEW_KEY" ]; then
        echo "⚠️  Could not extract key. Please copy it manually from above."
        exit 1
    fi
    
    echo ""
    echo "⚠️  SAVE THIS KEY: $NEW_KEY"
    echo "   (This is the ONLY time it will be shown)"
    echo ""
    
    read -p "Press Enter to test using this key..."
    
    echo ""
    echo "Step 2: Testing API key with /v1/jobs..."
    curl -s -X GET "${API_BASE}/v1/jobs?limit=5" \
      -H "Authorization: Bearer ${NEW_KEY}" | python3 -m json.tool 2>/dev/null || \
      curl -s -X GET "${API_BASE}/v1/jobs?limit=5" \
      -H "Authorization: Bearer ${NEW_KEY}"
    
    echo ""
    echo ""
    echo "Step 3: Listing all API keys (admin)..."
    curl -s -X GET "${API_BASE}/admin/api-keys" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -m json.tool 2>/dev/null || \
      curl -s -X GET "${API_BASE}/admin/api-keys" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}"
    
    echo ""
    echo "✅ Test complete!"
    echo ""
    echo "To test revocation:"
    echo "  curl -X POST \"${API_BASE}/admin/api-keys/${KEY_ID}/revoke\" \\"
    echo "    -H \"X-Admin-Token: ${ADMIN_TOKEN}\""
else
    echo "❌ Failed to create API key"
    echo "$RESPONSE"
    exit 1
fi
