# Quick Test Checklist

After restarting your API server, run these tests:

## ✅ Test 1: Public Paths (No Auth)
```bash
curl http://localhost:8000/health
```
**Expected:** HTTP 200 with JSON response

## ✅ Test 2: API Key Required
```bash
# Without API key
curl http://localhost:8000/v1/jobs
```
**Expected:** HTTP 401 with error message

## ✅ Test 3: File Type Validation
```bash
# Invalid file (.exe)
echo "test" > /tmp/test.exe
curl -X POST http://localhost:8000/v1/parse \
  -H "x-api-key: test-key-123" \
  -F "file=@/tmp/test.exe"
```
**Expected:** HTTP 400 with `{"error": "invalid_file_type", "message": "..."}`

```bash
# Valid file (.pdf)
echo "test" > /tmp/test.pdf
curl -X POST http://localhost:8000/v1/parse \
  -H "x-api-key: test-key-123" \
  -F "file=@/tmp/test.pdf"
```
**Expected:** HTTP 200 (job created) or 401 (if auth fails, but file validation passed)

## ✅ Test 4: Rate Limiting
```bash
# Send 12 requests rapidly (limit is 10/min)
for i in {1..12}; do
  curl -H "x-api-key: test-key-123" http://localhost:8000/v1/jobs?limit=1
  sleep 0.1
done
```
**Expected:** 
- First 10 requests: HTTP 200
- Request 11+: HTTP 429 with `{"error": "rate_limited", "message": "Too many requests..."}`

## ✅ Test 5: Error Messages
```bash
# 404 error
curl -H "x-api-key: test-key-123" http://localhost:8000/v1/jobs/nonexistent-id
```
**Expected:** HTTP 404 with structured JSON:
```json
{
  "error": "job_not_found",
  "message": "Job nonexistent-id not found..."
}
```

## 🚀 Quick Test Script

Or just run:
```bash
./quick_test.sh
```

This will test all features automatically!

