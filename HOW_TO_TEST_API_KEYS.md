# How to Test API Keys - Quick Guide

## Option 1: Automated Test Script (Easiest)

Run the automated test script:

```bash
# Test on Railway (production)
./QUICK_TEST_API_KEYS.sh railway

# OR test locally
./QUICK_TEST_API_KEYS.sh local
```

This script will:
1. ✅ Create a new API key
2. ✅ List all API keys
3. ✅ Test using the new key
4. ✅ Revoke the key
5. ✅ Verify revoked key doesn't work
6. ✅ Reactivate the key

---

## Option 2: Manual Testing with curl

### Step 1: Create a New API Key

**On Railway:**
```bash
curl -X POST https://docparser-production-aa0e.up.railway.app/v1/api-keys/ \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev_123" \
  -d '{
    "name": "My Test Key",
    "tenant_id": "tenant_demo",
    "rate_limit_per_minute": 100,
    "rate_limit_per_hour": 5000
  }'
```

**Locally:**
```bash
curl -X POST http://localhost:8000/v1/api-keys/ \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev_123" \
  -d '{
    "name": "My Test Key",
    "tenant_id": "tenant_demo",
    "rate_limit_per_minute": 100,
    "rate_limit_per_hour": 5000
  }'
```

**Response:**
```json
{
  "id": "key_abc123...",
  "key": "dp_a1b2c3d4e5f6...",  ⚠️ SAVE THIS!
  "name": "My Test Key",
  "tenant_id": "tenant_demo",
  "is_active": "active",
  "rate_limit_per_minute": 100,
  "rate_limit_per_hour": 5000,
  "last_used_at": null,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**⚠️ IMPORTANT:** Copy the `key` value - it's only shown once!

---

### Step 2: List All API Keys

**On Railway:**
```bash
curl -X GET https://docparser-production-aa0e.up.railway.app/v1/api-keys/ \
  -H "x-api-key: dev_123"
```

**Locally:**
```bash
curl -X GET http://localhost:8000/v1/api-keys/ \
  -H "x-api-key: dev_123"
```

**Response:**
```json
[
  {
    "id": "key_abc123...",
    "name": "My Test Key",
    "tenant_id": "tenant_demo",
    "is_active": "active",
    "rate_limit_per_minute": 100,
    "rate_limit_per_hour": 5000,
    "last_used_at": null,
    "created_at": "2025-01-15T10:30:00Z"
  }
]
```

Note: The `key` field is NOT included for security.

---

### Step 3: Use the New API Key

Replace `dp_xxx` with your actual key from Step 1.

**On Railway:**
```bash
curl -X GET https://docparser-production-aa0e.up.railway.app/v1/jobs?limit=5 \
  -H "x-api-key: dp_a1b2c3d4e5f6..."
```

**Locally:**
```bash
curl -X GET http://localhost:8000/v1/jobs?limit=5 \
  -H "x-api-key: dp_a1b2c3d4e5f6..."
```

**Expected:** Should return a list of jobs (same as using `dev_123`)

---

### Step 4: Test Parsing with New Key

**On Railway:**
```bash
curl -X POST https://docparser-production-aa0e.up.railway.app/v1/parse \
  -H "x-api-key: dp_a1b2c3d4e5f6..." \
  -F "file=@path/to/your/file.pdf"
```

**Locally:**
```bash
curl -X POST http://localhost:8000/v1/parse \
  -H "x-api-key: dp_a1b2c3d4e5f6..." \
  -F "file=@api/samples/GSTR1.pdf"
```

**Expected:** Returns a `job_id` - same as using `dev_123`

---

### Step 5: Revoke the API Key

Replace `key_xxx` with the `id` from Step 1.

**On Railway:**
```bash
curl -X POST https://docparser-production-aa0e.up.railway.app/v1/api-keys/key_abc123/revoke \
  -H "x-api-key: dev_123"
```

**Locally:**
```bash
curl -X POST http://localhost:8000/v1/api-keys/key_abc123/revoke \
  -H "x-api-key: dev_123"
```

**Response:**
```json
{
  "ok": true,
  "message": "API key revoked"
}
```

---

### Step 6: Verify Revoked Key Doesn't Work

**On Railway:**
```bash
curl -X GET https://docparser-production-aa0e.up.railway.app/v1/jobs?limit=5 \
  -H "x-api-key: dp_a1b2c3d4e5f6..."
```

**Locally:**
```bash
curl -X GET http://localhost:8000/v1/jobs?limit=5 \
  -H "x-api-key: dp_a1b2c3d4e5f6..."
```

**Expected:** `401 Unauthorized` - "Invalid or revoked API key"

---

### Step 7: Reactivate the Key

**On Railway:**
```bash
curl -X POST https://docparser-production-aa0e.up.railway.app/v1/api-keys/key_abc123/reactivate \
  -H "x-api-key: dev_123"
```

**Locally:**
```bash
curl -X POST http://localhost:8000/v1/api-keys/key_abc123/reactivate \
  -H "x-api-key: dev_123"
```

**Response:**
```json
{
  "ok": true,
  "message": "API key reactivated"
}
```

Now the key should work again!

---

## Option 3: Using the Dashboard

The dashboard at `/dashboard` already uses API keys. You can:

1. Log in with `dev_123` (or any API key)
2. The dashboard stores it in `localStorage`
3. All API calls use the stored key

To test the new system:
1. Create a new key via API (Step 1 above)
2. Log out of dashboard (clear API key)
3. Log back in with the new `dp_xxx` key
4. Everything should work the same!

---

## Quick Reference

| Action | Endpoint | Method | Auth Header |
|--------|----------|--------|-------------|
| Create key | `/v1/api-keys/` | POST | `dev_123` |
| List keys | `/v1/api-keys/` | GET | `dev_123` |
| Revoke key | `/v1/api-keys/{id}/revoke` | POST | `dev_123` |
| Reactivate | `/v1/api-keys/{id}/reactivate` | POST | `dev_123` |
| Delete key | `/v1/api-keys/{id}` | DELETE | `dev_123` |
| Use key | `/v1/parse`, `/v1/jobs`, etc. | Any | `dp_xxx...` |

---

## Troubleshooting

**Error: "Not authenticated"**
- Make sure you're using the correct API key
- Check the header format: `x-api-key: <key>` or `Authorization: Bearer <key>`

**Error: "Cannot create keys for different tenant"**
- Use `tenant_id: "tenant_demo"` when creating keys with `dev_123`

**Error: "Invalid API key"**
- The key might be revoked - check the list endpoint
- Make sure you copied the full key (starts with `dp_`)

**Key not working after creation**
- Make sure you saved the key from the creation response
- Keys are only shown once - if lost, you need to create a new one

