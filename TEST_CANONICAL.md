# Testing Canonical Format

## Option 1: Test Locally (Recommended First)

### Step 1: Start Services
```bash
# Start all services (API, DB, Redis, MinIO)
docker-compose up -d

# Wait for services to be ready
sleep 5

# Check if API is running
curl http://localhost:8000/
```

### Step 2: Run Test Script
```bash
# Run the automated test
./test_canonical_format.sh

# Or test manually:
# 1. Upload a document
curl -X POST "http://localhost:8000/v1/parse" \
  -H "Authorization: Bearer dev_123" \
  -F "file=@api/samples/sample_invoice.txt"

# 2. Get job_id from response, then test canonical format
curl -H "Authorization: Bearer dev_123" \
  "http://localhost:8000/v1/jobs/{job_id}?format=canonical" | jq
```

### Step 3: Verify Results
The test script will check:
- ✅ API health
- ✅ Legacy format (default)
- ✅ Canonical format (`format=canonical`)
- ✅ Required fields (business, parties, financials, entries)
- ✅ Schema version (`doc.v0.1`)

## Option 2: Test on Railway

### Step 1: Deploy to Railway
```bash
# Push to GitHub (Railway auto-deploys)
git add .
git commit -m "Add canonical JSON format v0.1"
git push origin main
```

### Step 2: Test on Railway
```bash
# Replace with your Railway URL
RAILWAY_URL="https://your-app.railway.app"

# Test canonical format
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "$RAILWAY_URL/v1/jobs/{job_id}?format=canonical" | jq
```

## Manual Testing Examples

### Test Invoice → Canonical
```bash
# 1. Upload invoice
JOB_RESPONSE=$(curl -s -X POST "http://localhost:8000/v1/parse" \
  -H "Authorization: Bearer dev_123" \
  -F "file=@api/samples/sample_invoice.txt")

JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')

# 2. Wait for processing
sleep 3

# 3. Get canonical format
curl -s -H "Authorization: Bearer dev_123" \
  "http://localhost:8000/v1/jobs/$JOB_ID?format=canonical" | jq
```

### Test Purchase Register → Canonical
```bash
# 1. Upload purchase register
JOB_RESPONSE=$(curl -s -X POST "http://localhost:8000/v1/parse" \
  -H "Authorization: Bearer dev_123" \
  -H "doc_type: purchase_register" \
  -F "file=@samples/purchase_register_complex.csv")

JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')

# 2. Get canonical format
curl -s -H "Authorization: Bearer dev_123" \
  "http://localhost:8000/v1/jobs/$JOB_ID?format=canonical" | jq '.result | {schema_version, doc_type, business, parties, financials, entries: .entries | length}'
```

### Test GSTR-3B → Canonical
```bash
# 1. Upload GSTR-3B
JOB_RESPONSE=$(curl -s -X POST "http://localhost:8000/v1/parse" \
  -H "Authorization: Bearer dev_123" \
  -H "doc_type: gstr3b" \
  -F "file=@samples/GSTR-3B.pdf")

JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')

# 2. Get canonical format
curl -s -H "Authorization: Bearer dev_123" \
  "http://localhost:8000/v1/jobs/$JOB_ID?format=canonical" | jq
```

## Expected Results

### Legacy Format (Default)
```json
{
  "job_id": "...",
  "status": "succeeded",
  "doc_type": "invoice",
  "result": {
    "invoice_number": "INV-001",
    "date": "2025-01-15",
    "seller": {...},
    "buyer": {...},
    ...
  }
}
```

### Canonical Format
```json
{
  "job_id": "...",
  "status": "succeeded",
  "doc_type": "invoice",
  "result": {
    "schema_version": "doc.v0.1",
    "doc_type": "invoice",
    "doc_id": "invoice-INV-001",
    "doc_date": "2025-01-15",
    "business": {...},
    "parties": {
      "primary": {...},
      "counterparty": {...}
    },
    "financials": {
      "currency": "INR",
      "subtotal": 100000.00,
      "tax_breakup": {...},
      "grand_total": 118000.00
    },
    "entries": [...],
    "doc_specific": {...}
  },
  "meta": {
    "format": "canonical",
    "schema_version": "doc.v0.1"
  }
}
```

## Troubleshooting

### API Not Running
```bash
# Check docker containers
docker ps

# Start services
docker-compose up -d

# Check logs
docker-compose logs api
```

### Import Errors
```bash
# Check if canonical module is imported correctly
docker-compose exec api python -c "from app.parsers.canonical import normalize_to_canonical; print('OK')"
```

### Format Not Working
- Check API logs: `docker-compose logs api | grep canonical`
- Verify endpoint: `curl "http://localhost:8000/openapi.json" | jq '.paths["/v1/jobs/{job_id}"].get.parameters'`
- Test with existing job: Use a job_id from `/v1/jobs` endpoint

