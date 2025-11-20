#!/bin/bash
# Quick test script for rate limiting
# Make sure API server is restarted after setting .env variables

echo "Testing Rate Limiting..."
echo "API Key: test-key-123"
echo "Limit: 10 requests/minute"
echo ""
echo "Sending 15 requests (should get 429 after 10)..."
echo ""

for i in {1..15}; do
    status=$(curl -s -o /dev/null -w "%{http_code}" -H "x-api-key: test-key-123" http://localhost:8000/v1/jobs)
    if [ "$status" = "429" ]; then
        echo "✅ Request $i: HTTP $status (Rate limited - as expected!)"
        break
    elif [ "$status" = "401" ]; then
        echo "⚠️  Request $i: HTTP $status (Auth failed - check API key)"
    elif [ "$status" = "200" ]; then
        echo "Request $i: HTTP $status"
    else
        echo "Request $i: HTTP $status"
    fi
    sleep 0.2
done

echo ""
echo "Test complete!"
