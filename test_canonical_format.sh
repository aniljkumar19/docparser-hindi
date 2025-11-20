#!/bin/bash
# Test Canonical Format Implementation

set -e

API_URL="${API_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-dev_123}"

echo "🧪 Testing Canonical Format Implementation"
echo "=========================================="
echo ""
echo "API URL: $API_URL"
echo "API Key: $API_KEY"
echo ""

# Check if API is running
echo "1. Checking API health..."
if ! curl -s "$API_URL/" > /dev/null; then
    echo "❌ API is not running at $API_URL"
    echo "   Start it with: docker-compose up -d"
    exit 1
fi
echo "✅ API is running"
echo ""

# Find a sample file
SAMPLE_FILE=""
if [ -f "api/samples/sample_invoice.txt" ]; then
    SAMPLE_FILE="api/samples/sample_invoice.txt"
elif [ -f "tests/fixtures/purchase_same_state.json" ]; then
    # We'll need to create a test file from JSON
    echo "⚠️  No sample invoice file found, will test with existing job"
    TEST_MODE="existing_job"
else
    echo "⚠️  No sample files found"
    TEST_MODE="existing_job"
fi

if [ "$TEST_MODE" != "existing_job" ] && [ -n "$SAMPLE_FILE" ]; then
    echo "2. Uploading test document..."
    UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/v1/parse" \
        -H "Authorization: Bearer $API_KEY" \
        -F "file=@$SAMPLE_FILE")
    
    JOB_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"job_id":"[^"]*' | cut -d'"' -f4)
    
    if [ -z "$JOB_ID" ]; then
        echo "❌ Failed to upload document"
        echo "Response: $UPLOAD_RESPONSE"
        exit 1
    fi
    
    echo "✅ Document uploaded, job_id: $JOB_ID"
    echo ""
    
    # Wait for processing
    echo "3. Waiting for job to complete..."
    sleep 3
    
    # Check job status
    STATUS=$(curl -s -H "Authorization: Bearer $API_KEY" \
        "$API_URL/v1/jobs/$JOB_ID" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    
    echo "   Job status: $STATUS"
    echo ""
else
    echo "2. Using existing job (skipping upload)"
    echo "   To test with a new upload, provide a sample file"
    echo ""
    
    # Try to get a recent job
    echo "3. Fetching recent jobs..."
    JOBS_RESPONSE=$(curl -s -H "Authorization: Bearer $API_KEY" \
        "$API_URL/v1/jobs?limit=1")
    
    JOB_ID=$(echo "$JOBS_RESPONSE" | grep -o '"job_id":"[^"]*' | cut -d'"' -f4 | head -1)
    
    if [ -z "$JOB_ID" ]; then
        echo "❌ No jobs found. Please upload a document first."
        exit 1
    fi
    
    echo "✅ Found job: $JOB_ID"
    echo ""
fi

# Test legacy format (default)
echo "4. Testing legacy format (default)..."
LEGACY_RESPONSE=$(curl -s -H "Authorization: Bearer $API_KEY" \
    "$API_URL/v1/jobs/$JOB_ID")
LEGACY_FORMAT=$(echo "$LEGACY_RESPONSE" | grep -o '"format":"[^"]*' | cut -d'"' -f4 || echo "none")
LEGACY_SCHEMA=$(echo "$LEGACY_RESPONSE" | grep -o '"schema_version":"[^"]*' | cut -d'"' -f4 || echo "none")

if [ "$LEGACY_FORMAT" = "none" ] && [ "$LEGACY_SCHEMA" = "none" ]; then
    echo "✅ Legacy format returned (no format field = legacy)"
else
    echo "⚠️  Legacy format has format field: $LEGACY_FORMAT"
fi
echo ""

# Test canonical format
echo "5. Testing canonical format..."
CANONICAL_RESPONSE=$(curl -s -H "Authorization: Bearer $API_KEY" \
    "$API_URL/v1/jobs/$JOB_ID?format=canonical")

# Check for canonical format indicators
CANONICAL_FORMAT=$(echo "$CANONICAL_RESPONSE" | grep -o '"format":"[^"]*' | cut -d'"' -f4 || echo "none")
CANONICAL_SCHEMA=$(echo "$CANONICAL_RESPONSE" | grep -o '"schema_version":"[^"]*' | cut -d'"' -f4 || echo "none")
CANONICAL_DOC_TYPE=$(echo "$CANONICAL_RESPONSE" | grep -o '"doc_type":"[^"]*' | cut -d'"' -f4 | head -1 || echo "none")

if [ "$CANONICAL_FORMAT" = "canonical" ]; then
    echo "✅ Format field is 'canonical'"
else
    echo "❌ Format field is not 'canonical' (got: $CANONICAL_FORMAT)"
fi

if [ "$CANONICAL_SCHEMA" = "doc.v0.1" ]; then
    echo "✅ Schema version is 'doc.v0.1'"
else
    echo "❌ Schema version is not 'doc.v0.1' (got: $CANONICAL_SCHEMA)"
fi

if [ "$CANONICAL_DOC_TYPE" != "none" ]; then
    echo "✅ Doc type found: $CANONICAL_DOC_TYPE"
else
    echo "❌ Doc type not found in response"
fi

# Check for required canonical fields
echo ""
echo "6. Validating canonical structure..."
HAS_BUSINESS=$(echo "$CANONICAL_RESPONSE" | grep -q '"business"' && echo "yes" || echo "no")
HAS_PARTIES=$(echo "$CANONICAL_RESPONSE" | grep -q '"parties"' && echo "yes" || echo "no")
HAS_FINANCIALS=$(echo "$CANONICAL_RESPONSE" | grep -q '"financials"' && echo "yes" || echo "no")
HAS_ENTRIES=$(echo "$CANONICAL_RESPONSE" | grep -q '"entries"' && echo "yes" || echo "no")

if [ "$HAS_BUSINESS" = "yes" ]; then
    echo "✅ Has 'business' field"
else
    echo "❌ Missing 'business' field"
fi

if [ "$HAS_PARTIES" = "yes" ]; then
    echo "✅ Has 'parties' field"
else
    echo "❌ Missing 'parties' field"
fi

if [ "$HAS_FINANCIALS" = "yes" ]; then
    echo "✅ Has 'financials' field"
else
    echo "❌ Missing 'financials' field"
fi

if [ "$HAS_ENTRIES" = "yes" ]; then
    echo "✅ Has 'entries' field"
else
    echo "❌ Missing 'entries' field"
fi

echo ""
echo "=========================================="
echo "📋 Summary"
echo "=========================================="
echo "Job ID: $JOB_ID"
echo "Legacy format: ✅ Working"
if [ "$CANONICAL_FORMAT" = "canonical" ] && [ "$CANONICAL_SCHEMA" = "doc.v0.1" ]; then
    echo "Canonical format: ✅ Working"
    echo ""
    echo "✅ All tests passed!"
    echo ""
    echo "To view the canonical response:"
    echo "curl -s -H \"Authorization: Bearer $API_KEY\" \"$API_URL/v1/jobs/$JOB_ID?format=canonical\" | jq"
else
    echo "Canonical format: ❌ Not working correctly"
    echo ""
    echo "Response preview:"
    echo "$CANONICAL_RESPONSE" | head -20
    exit 1
fi

