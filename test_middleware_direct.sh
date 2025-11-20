#!/bin/bash
# Test if middleware dispatch is being called at all

BASE="${1:-https://docparser-production-aa0e.up.railway.app}"

echo "=== Testing if middleware dispatch is called ==="
echo "BASE: $BASE"
echo ""

echo "Making a request to /health (should trigger middleware dispatch):"
curl -s -i "$BASE/health" | head -10
echo ""

echo "Making a request to /v1/jobs (should trigger middleware dispatch):"
curl -s -i "$BASE/v1/jobs" | head -10
echo ""

echo "Check Railway logs for:"
echo "  [RateLimitMiddleware] dispatch called for: /health"
echo "  [RateLimitMiddleware] dispatch called for: /v1/jobs"
