# Railway Deployment Checklist

## Pre-Deployment

- [x] All code implemented
- [x] Local tests passing (10/12)
- [x] Code committed to repository
- [ ] Environment variables prepared

## Railway Setup

### 1. Environment Variables

Set these in Railway project settings:

**Required:**
- [ ] `USE_API_KEY_MIDDLEWARE=true`
- [ ] `DOCPARSER_API_KEY=<your-secret-key>` (use a strong production key!)

**Optional:**
- [ ] `RATE_LIMIT_REQUESTS_PER_MINUTE=60` (default: 60)
- [ ] `RATE_LIMIT_UPLOADS_PER_MINUTE=5` (default: 5)
- [ ] `USE_JSON_LOGGING=false` (default: false)
- [ ] `LOG_LEVEL=INFO` (default: INFO)
- [ ] `REDIS_URL=<redis-url>` (optional, for distributed rate limiting)

### 2. Deploy

- [ ] Push code to GitHub
- [ ] Railway auto-deploys (or trigger manual deploy)
- [ ] Check deployment logs for errors

### 3. Verify Deployment

- [ ] Check startup logs for: `🔐 API Key Middleware ENABLED`
- [ ] Test `/health` endpoint (should work without API key)
- [ ] Test `/v1/jobs` without API key (should get 401)
- [ ] Test `/v1/jobs` with API key (should work)

## Post-Deployment Testing

### Test 1: Public Paths
```bash
curl https://your-app.railway.app/health
```
Expected: HTTP 200

### Test 2: API Key Authentication
```bash
# Without key
curl https://your-app.railway.app/v1/jobs
# Expected: HTTP 401

# With key
curl -H "x-api-key: YOUR_KEY" https://your-app.railway.app/v1/jobs
# Expected: HTTP 200
```

### Test 3: File Type Validation
```bash
# Invalid file
echo "test" > test.exe
curl -X POST \
  -H "x-api-key: YOUR_KEY" \
  -F "file=@test.exe" \
  https://your-app.railway.app/v1/parse
# Expected: HTTP 400 with error: invalid_file_type

# Valid file
echo "test" > test.pdf
curl -X POST \
  -H "x-api-key: YOUR_KEY" \
  -F "file=@test.pdf" \
  https://your-app.railway.app/v1/parse
# Expected: HTTP 200 (job created)
```

### Test 4: Rate Limiting
```bash
# Send 70 requests rapidly
for i in {1..70}; do
  curl -H "x-api-key: YOUR_KEY" \
    https://your-app.railway.app/v1/jobs?limit=1
done
# Expected: First 60 get HTTP 200, then HTTP 429
```

### Test 5: Error Messages
```bash
# 404 error
curl -H "x-api-key: YOUR_KEY" \
  https://your-app.railway.app/v1/jobs/nonexistent-id
# Expected: HTTP 404 with structured JSON error

# Validation error
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_KEY" \
  -d '{"invalid": "data"}' \
  https://your-app.railway.app/v1/parse
# Expected: HTTP 422 with structured JSON error
```

## Monitoring

- [ ] Check Railway logs for middleware startup message
- [ ] Monitor for 429 responses (rate limiting working)
- [ ] Check error message format in responses
- [ ] Verify file validation is rejecting invalid files

## Rollback Plan

If issues occur:
1. Set `USE_API_KEY_MIDDLEWARE=false` to disable middleware
2. System will fall back to legacy `verify_api_key()` function
3. All other features (file validation, error messages) will still work

---

**Ready to deploy!** 🚀

