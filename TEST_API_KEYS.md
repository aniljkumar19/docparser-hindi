# Testing the Production API Key System

## Quick Test Guide

### 1. Test Creating an API Key

```bash
# Using curl
curl -X POST http://localhost:8000/v1/api-keys/ \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev_123" \
  -d '{
    "name": "Test Key",
    "tenant_id": "tenant_demo",
    "rate_limit_per_minute": 100,
    "rate_limit_per_hour": 5000
  }'
```

**Expected Response:**
```json
{
  "id": "key_abc123...",
  "key": "dp_a1b2c3d4e5f6...",  // ⚠️ SAVE THIS - only shown once!
  "name": "Test Key",
  "tenant_id": "tenant_demo",
  "is_active": "active",
  "rate_limit_per_minute": 100,
  "rate_limit_per_hour": 5000,
  "last_used_at": null,
  "created_at": "2025-01-15T10:30:00Z"
}
```

### 2. Test Listing API Keys

```bash
curl -X GET http://localhost:8000/v1/api-keys/ \
  -H "x-api-key: dev_123"
```

**Expected Response:**
```json
[
  {
    "id": "key_abc123...",
    "name": "Test Key",
    "tenant_id": "tenant_demo",
    "is_active": "active",
    "rate_limit_per_minute": 100,
    "rate_limit_per_hour": 5000,
    "last_used_at": null,
    "created_at": "2025-01-15T10:30:00Z"
    // Note: 'key' field is NOT included for security
  }
]
```

### 3. Test Using the New API Key

```bash
# Use the key you just created (replace dp_xxx with your actual key)
curl -X POST http://localhost:8000/v1/parse \
  -H "x-api-key: dp_a1b2c3d4e5f6..." \
  -F "file=@GSTR1.pdf"
```

**Expected:** Should work just like `dev_123` - creates a job and returns job_id.

### 4. Test Revoking a Key

```bash
curl -X POST http://localhost:8000/v1/api-keys/{key_id}/revoke \
  -H "x-api-key: dev_123"
```

**Expected Response:**
```json
{
  "ok": true,
  "message": "API key revoked"
}
```

### 5. Test Using Revoked Key (Should Fail)

```bash
curl -X POST http://localhost:8000/v1/parse \
  -H "x-api-key: dp_a1b2c3d4e5f6..." \
  -F "file=@GSTR1.pdf"
```

**Expected:** `401 Unauthorized` - "Invalid or revoked API key"

### 6. Test Reactivating a Key

```bash
curl -X POST http://localhost:8000/v1/api-keys/{key_id}/reactivate \
  -H "x-api-key: dev_123"
```

**Expected Response:**
```json
{
  "ok": true,
  "message": "API key reactivated"
}
```

### 7. Test Rate Limiting (Optional - if middleware enabled)

If `USE_API_KEY_MIDDLEWARE=true`, rate limiting is enforced:

```bash
# Make 100 requests in quick succession
for i in {1..100}; do
  curl -X GET http://localhost:8000/v1/jobs \
    -H "x-api-key: dp_xxx"
done
```

**Expected:** After exceeding `rate_limit_per_minute`, you'll get:
```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```
Status: `429 Too Many Requests`

## Testing Checklist

- [ ] Create API key via POST `/v1/api-keys/`
- [ ] List API keys via GET `/v1/api-keys/`
- [ ] Use new API key to parse a document
- [ ] Revoke API key
- [ ] Verify revoked key no longer works
- [ ] Reactivate API key
- [ ] Verify reactivated key works again
- [ ] Delete API key permanently
- [ ] Verify deleted key no longer exists in list

## Notes

1. **Backward Compatibility:** The old `dev_123` key (from env vars) still works
2. **Database Keys:** New keys are stored in the `api_keys` table
3. **Key Format:** New keys start with `dp_` followed by 32 hex characters
4. **Security:** Keys are hashed (SHA256) before storage - original key is never stored
5. **One-Time Display:** The plaintext key is only shown once on creation - save it!

## Troubleshooting

**Error: "Not authenticated"**
- Make sure you're sending the API key in the header
- Use either `x-api-key: <key>` or `Authorization: Bearer <key>`

**Error: "Cannot create keys for different tenant"**
- The `tenant_id` in the request must match your API key's tenant
- Use `tenant_demo` if testing with `dev_123`

**Error: "Invalid API key"**
- Check that the key hasn't been revoked
- Verify the key format: `dp_` followed by 32 hex chars

