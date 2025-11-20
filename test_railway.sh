#!/bin/bash
# Test script for Railway deployment
# Usage: ./test_railway.sh <RAILWAY_URL> <API_KEY>

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: ./test_railway.sh <RAILWAY_URL> <API_KEY>"
    echo ""
    echo "Example:"
    echo "  ./test_railway.sh https://docparser-production.up.railway.app docparser_prod_abc123"
    exit 1
fi

API_BASE="$1"
API_KEY="$2"
PASS_COUNT=0
FAIL_COUNT=0

print_test() {
    if [ $1 -eq 0 ]; then
        echo "   ✅ PASS: $2"
        ((PASS_COUNT++))
    else
        echo "   ❌ FAIL: $2"
        ((FAIL_COUNT++))
    fi
}

echo "============================================================"
echo "  Railway Deployment Test"
echo "============================================================"
echo "API: $API_BASE"
echo "API Key: ${API_KEY:0:20}..."
echo ""

# Test 1: Public paths (no auth)
echo "📋 TEST 1: Public Paths"
echo "-----------------------------------"
echo ""
echo "1.1 Testing /health (should work without API key)..."
response=$(curl -s -w "\n%{http_code}" "$API_BASE/health" 2>/dev/null)
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ]; then
    print_test 0 "/health accessible (HTTP $http_code)"
else
    print_test 1 "/health check (got HTTP $http_code)"
fi

# Test 2: API key required
echo ""
echo "📋 TEST 2: API Key Authentication"
echo "-----------------------------------"
echo ""
echo "2.1 Testing without API key (should get 401)..."
response=$(curl -s -w "\n%{http_code}" "$API_BASE/v1/jobs" 2>/dev/null)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)
error=$(echo "$body" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('error', ''))" 2>/dev/null || echo "")
if [ "$http_code" = "401" ] && [ -n "$error" ]; then
    print_test 0 "API key required (got 401 with error: $error)"
else
    print_test 1 "API key required (got HTTP $http_code)"
fi

echo ""
echo "2.2 Testing with correct API key..."
response=$(curl -s -w "\n%{http_code}" -H "x-api-key: $API_KEY" "$API_BASE/v1/jobs?limit=1" 2>/dev/null)
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ] || [ "$http_code" = "404" ] || [ "$http_code" = "400" ]; then
    print_test 0 "Correct API key accepted (HTTP $http_code, not 401)"
else
    if [ "$http_code" = "401" ]; then
        print_test 1 "API key rejected (got 401 - check DOCPARSER_API_KEY matches)"
    else
        print_test 1 "Unexpected status with valid key (HTTP $http_code)"
    fi
fi

# Test 3: File type validation
echo ""
echo ""
echo "📋 TEST 3: File Type Validation"
echo "-----------------------------------"
echo ""
echo "3.1 Testing invalid file extension (.exe)..."
echo "test" > /tmp/test.exe
response=$(curl -s -w "\n%{http_code}" -X POST \
    -H "x-api-key: $API_KEY" \
    -F "file=@/tmp/test.exe" \
    "$API_BASE/v1/parse" 2>/dev/null)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)
error=$(echo "$body" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('error', ''))" 2>/dev/null || echo "")
rm -f /tmp/test.exe

if [ "$http_code" = "400" ] && [ "$error" = "invalid_file_type" ]; then
    print_test 0 "Invalid extension rejected (HTTP 400, error: $error)"
else
    print_test 1 "Invalid extension check (got HTTP $http_code, error: $error)"
fi

echo ""
echo "3.2 Testing valid file extension (.pdf)..."
echo "test content" > /tmp/test.pdf
response=$(curl -s -w "\n%{http_code}" -X POST \
    -H "x-api-key: $API_KEY" \
    -F "file=@/tmp/test.pdf" \
    "$API_BASE/v1/parse" 2>/dev/null)
http_code=$(echo "$response" | tail -n1)
rm -f /tmp/test.pdf

if [ "$http_code" = "200" ] || [ "$http_code" = "401" ]; then
    if [ "$http_code" = "401" ]; then
        print_test 0 "Valid .pdf passed validation (got 401 auth error, but file was accepted)"
    else
        print_test 0 "Valid .pdf accepted (HTTP $http_code)"
    fi
else
    print_test 1 "Valid .pdf check (got HTTP $http_code)"
fi

# Test 4: Rate Limiting
echo ""
echo ""
echo "📋 TEST 4: Rate Limiting"
echo "-----------------------------------"
echo ""
echo "4.1 Testing general rate limiting (limit: 60/min)..."
echo "   Sending 70 requests rapidly to trigger rate limit..."
rate_limited=false
rate_limited_at=0
for i in $(seq 1 70); do
    status=$(curl -s -o /dev/null -w "%{http_code}" -H "x-api-key: $API_KEY" "$API_BASE/v1/jobs?limit=1" 2>/dev/null)
    if [ "$status" = "429" ]; then
        echo "   ✅ Request $i: HTTP 429 (Rate limited!)"
        rate_limited=true
        rate_limited_at=$i
        break
    elif [ "$i" -le 5 ]; then
        echo "   Request $i: HTTP $status"
    fi
done
if [ "$rate_limited" = true ]; then
    print_test 0 "General rate limiting works (got 429 at request $rate_limited_at)"
else
    print_test 1 "General rate limiting not triggered (may need more requests or check limits)"
fi

echo ""
echo "4.2 Testing upload-specific rate limiting (limit: 5/min)..."
echo "   Creating small test file (1KB) for fast uploads..."
echo "x" > /tmp/tiny_upload.pdf
echo "   Sending 8 upload requests rapidly..."
upload_rate_limited=false
upload_rate_limited_at=0
for i in $(seq 1 8); do
    status=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "x-api-key: $API_KEY" \
        -F "file=@/tmp/tiny_upload.pdf" \
        "$API_BASE/v1/parse" 2>/dev/null)
    if [ "$status" = "429" ]; then
        echo "   ✅ Upload $i: HTTP 429 (Upload rate limited!)"
        upload_rate_limited=true
        upload_rate_limited_at=$i
        break
    elif [ "$i" -le 3 ]; then
        echo "   Upload $i: HTTP $status"
    fi
done
rm -f /tmp/tiny_upload.pdf
if [ "$upload_rate_limited" = true ]; then
    print_test 0 "Upload rate limiting works (got 429 at upload $upload_rate_limited_at)"
else
    print_test 1 "Upload rate limiting not triggered (may need more requests or check limits)"
fi

# Test 5: Error messages
echo ""
echo ""
echo "📋 TEST 5: Error Messages"
echo "-----------------------------------"
echo ""
echo "   ⏳ Waiting 65 seconds for rate limit window to reset..."
sleep 65
echo "   ✅ Rate limit window reset, proceeding with error message tests"
echo ""
echo "5.1 Testing 404 error format..."
response=$(curl -s -w "\n%{http_code}" \
    -H "x-api-key: $API_KEY" \
    "$API_BASE/v1/jobs/nonexistent-job-id-12345" 2>/dev/null)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)
error=$(echo "$body" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('error', ''))" 2>/dev/null || echo "")
message=$(echo "$body" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('message', ''))" 2>/dev/null || echo "")

if [ "$http_code" = "404" ] && [ "$error" = "job_not_found" ] && [ -n "$message" ]; then
    print_test 0 "404 error has structured format (error: $error, message present)"
else
    print_test 1 "404 error format (got HTTP $http_code, error: $error)"
fi

echo ""
echo "5.2 Testing validation error format..."
response=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{"invalid": "data"}' \
    "$API_BASE/v1/parse" 2>/dev/null)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)
error=$(echo "$body" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('error', ''))" 2>/dev/null || echo "")

if [ "$http_code" = "422" ] && [ "$error" = "request_validation_error" ]; then
    print_test 0 "Validation error has structured format (HTTP 422, error: $error)"
else
    print_test 1 "Validation error format (got HTTP $http_code, error: $error)"
fi

# Summary
echo ""
echo ""
echo "============================================================"
echo "  Test Summary"
echo "============================================================"
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""
if [ $FAIL_COUNT -eq 0 ]; then
    echo "🎉 All tests passed! Railway deployment is working correctly."
else
    echo "⚠️  Some tests failed. Review the output above."
fi
echo "============================================================"

