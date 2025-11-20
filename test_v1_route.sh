#!/bin/bash
# Test if middleware intercepts /v1/ routes

BASE="${1:-https://docparser-production-aa0e.up.railway.app}"

echo "=== Testing /v1/ route interception ==="
echo "BASE: $BASE"
echo ""
echo "Making request to /v1/jobs WITHOUT API key:"
echo "Expected: Middleware should intercept and return 401 with 'unauthorized' error"
echo ""
curl -s -i "$BASE/v1/jobs" | head -15
echo ""
echo ""
echo "Check Railway logs for:"
echo "  [RateLimitMiddleware] dispatch called for: /v1/jobs"
echo "  [RateLimitMiddleware] Intercepting: /v1/jobs"
echo "  [RateLimitMiddleware] ❌ No API key provided"
