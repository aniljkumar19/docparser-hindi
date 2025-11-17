# API Key Configuration

## Current Setup

**API Key:** `dev_123`  
**Tenant:** `tenant_demo`

## Where It's Configured

1. **docker-compose.yml** (line 11):
   ```yaml
   environment:
     API_KEYS: dev_123:tenant_demo
   ```

2. **api/.env** file:
   ```
   API_KEYS=dev_123:tenant_demo
   ```

## How to Use

### In Frontend (Current)
```javascript
headers: { "Authorization": "Bearer dev_123" }
```

### Alternative (Also Works)
```javascript
headers: { "X-API-Key": "dev_123" }
```

## Why "Invalid API key" Error?

The API container might not be loading the environment variables correctly. 

**Fix:** Restart the API container:
```bash
sudo docker-compose restart api
```

This will reload the environment variables and API keys.

## Test It

After restart:
```bash
curl -X POST "http://localhost:8000/v1/parse" \
  -H "Authorization: Bearer dev_123" \
  -F "file=@api/samples/sample_invoice.txt"
```

Should return a job_id, not "Invalid API key".

