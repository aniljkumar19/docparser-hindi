#!/bin/bash
# Test middleware with correct route paths

BASE="${1:-https://docparser-production-aa0e.up.railway.app}"
KEY="${2:-docparser_prod_ala2q7yv2pzu7wohv82qyrpu}"

echo "=== Testing Middleware ==="
echo "BASE: $BASE"
echo "KEY: ${KEY:0:20}..."
echo ""

echo "1. Testing /health (should be public, 200):"
curl -s -o /dev/null -w "Status: %{http_code}\n" "$BASE/health"
echo ""

echo "2. Testing /v1/validate/sales-register/fake-id WITHOUT key (should be 401 from middleware):"
curl -s -w "\nStatus: %{http_code}\n" "$BASE/v1/validate/sales-register/fake-id" | head -5
echo ""

echo "3. Testing /v1/validate/sales-register/fake-id WITH key (should be 404 job_not_found, not 401):"
curl -s -H "X-API-Key: $KEY" -w "\nStatus: %{http_code}\n" "$BASE/v1/validate/sales-register/fake-id" | head -5
echo ""

echo "4. Testing /v1/jobs (should be 401 without key):"
curl -s -w "\nStatus: %{http_code}\n" "$BASE/v1/jobs" | head -5
echo ""

echo "5. Testing /v1/jobs WITH key (should work or return proper error, not 401):"
curl -s -H "X-API-Key: $KEY" -w "\nStatus: %{http_code}\n" "$BASE/v1/jobs" | head -5
echo ""

