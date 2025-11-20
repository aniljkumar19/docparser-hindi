# Testing Rate Limiting Locally

## Steps to Test

1. **Restart your API server** to load the new .env variables:
   ```bash
   # Stop the current server (Ctrl+C)
   # Then restart it
   cd api
   uvicorn app.main:app --reload --port 8000
   ```

2. **Verify .env is loaded:**
   The API should log on startup if middleware is enabled.

3. **Test rate limiting:**
   ```bash
   # Quick test
   ./test_rate_limiting.sh
   
   # Or manual test
   for i in {1..15}; do
     curl -H "x-api-key: test-key-123" http://localhost:8000/v1/jobs
     sleep 0.2
   done
   ```

## Expected Results

- **First 10 requests:** HTTP 200 (success)
- **Request 11+:** HTTP 429 (rate limited)
- **Error message:** `{"error": "rate_limited", "message": "Too many requests. Please try again later."}`

## Configuration in .env

```bash
USE_API_KEY_MIDDLEWARE=true
DOCPARSER_API_KEY=test-key-123
RATE_LIMIT_REQUESTS_PER_MINUTE=10
RATE_LIMIT_UPLOADS_PER_MINUTE=3
```

## Notes

- The API key must match `DOCPARSER_API_KEY` in .env
- Rate limits reset after 60 seconds
- Public paths (`/health`, `/docs`) don't require API key
- If you see 401 errors, the middleware is working but API key doesn't match

