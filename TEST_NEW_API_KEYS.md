# Testing the New API Key System - Step by Step

## Prerequisites

1. **Set ADMIN_TOKEN in Railway** (if not already set)
   - Go to Railway → Variables → Add `ADMIN_TOKEN=your-secret-token`

2. **Get your Railway URL**
   - Example: `https://docparser-production-aa0e.up.railway.app`

---

## Step 1: Create a New API Key (Admin Endpoint)

Use the admin endpoint to create a new database-backed API key:

```bash
# Replace YOUR_ADMIN_TOKEN with the token you set in Railway
# Replace the URL with your Railway URL

curl -X POST "https://docparser-production-aa0e.up.railway.app/admin/api-keys?name=Test+Key" \
  -H "X-Admin-Token: YOUR_ADMIN_TOKEN"
```

**Expected Response:**
```json
{
  "id": "key_abc123...",
  "name": "Test Key",
  "api_key": "dp_a1b2c3d4e5f6...",  ⚠️ SAVE THIS!
  "active": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**⚠️ IMPORTANT:** Copy the `api_key` value - this is the ONLY time it will be shown!

---

## Step 2: Test Using the New API Key

Now use the new key (replace `dp_xxx` with your actual key from Step 1):

### Option A: Using Authorization Bearer Header

```bash
curl -X GET "https://docparser-production-aa0e.up.railway.app/v1/jobs?limit=5" \
  -H "Authorization: Bearer dp_a1b2c3d4e5f6..."
```

### Option B: Using X-API-Key Header

```bash
curl -X GET "https://docparser-production-aa0e.up.railway.app/v1/jobs?limit=5" \
  -H "X-API-Key: dp_a1b2c3d4e5f6..."
```

**Expected:** Should return a list of jobs (same as using `dev_123`)

---

## Step 3: Test Parsing with New Key

```bash
# If you have a sample file
curl -X POST "https://docparser-production-aa0e.up.railway.app/v1/parse" \
  -H "Authorization: Bearer dp_a1b2c3d4e5f6..." \
  -F "file=@path/to/your/file.pdf"

# Or download a sample first
curl -X GET "https://docparser-production-aa0e.up.railway.app/v1/samples/GSTR1.pdf" \
  -H "Authorization: Bearer dp_a1b2c3d4e5f6..." \
  -o GSTR1.pdf

# Then parse it
curl -X POST "https://docparser-production-aa0e.up.railway.app/v1/parse" \
  -H "Authorization: Bearer dp_a1b2c3d4e5f6..." \
  -F "file=@GSTR1.pdf"
```

**Expected:** Returns a `job_id` - same as using `dev_123`

---

## Step 4: List All API Keys (Admin)

```bash
curl -X GET "https://docparser-production-aa0e.up.railway.app/admin/api-keys" \
  -H "X-Admin-Token: YOUR_ADMIN_TOKEN"
```

**Expected Response:**
```json
[
  {
    "id": "key_abc123...",
    "name": "Test Key",
    "tenant_id": "default",
    "active": true,
    "rate_limit_per_minute": 60,
    "rate_limit_per_hour": 1000,
    "last_used_at": "2025-01-15T10:35:00Z",
    "created_at": "2025-01-15T10:30:00Z"
    // Note: api_key is NOT shown for security
  }
]
```

Notice: The `api_key` field is NOT included (for security).

---

## Step 5: Test Revoking a Key

```bash
# Replace key_abc123 with the id from Step 4
curl -X POST "https://docparser-production-aa0e.up.railway.app/admin/api-keys/key_abc123/revoke" \
  -H "X-Admin-Token: YOUR_ADMIN_TOKEN"
```

**Expected Response:**
```json
{
  "ok": true,
  "message": "API key revoked"
}
```

---

## Step 6: Verify Revoked Key Doesn't Work

```bash
# Try using the revoked key
curl -X GET "https://docparser-production-aa0e.up.railway.app/v1/jobs?limit=5" \
  -H "Authorization: Bearer dp_a1b2c3d4e5f6..."
```

**Expected:** `401 Unauthorized` - "Invalid or inactive API key"

---

## Step 7: Reactivate the Key

```bash
curl -X POST "https://docparser-production-aa0e.up.railway.app/admin/api-keys/key_abc123/activate" \
  -H "X-Admin-Token: YOUR_ADMIN_TOKEN"
```

**Expected Response:**
```json
{
  "ok": true,
  "message": "API key activated"
}
```

Now the key should work again!

---

## Quick Test Script

Save this as `test_new_api_keys.sh`:

```bash
#!/bin/bash

# Configuration
API_BASE="https://docparser-production-aa0e.up.railway.app"
ADMIN_TOKEN="YOUR_ADMIN_TOKEN_HERE"

echo "Step 1: Creating new API key..."
RESPONSE=$(curl -s -X POST "${API_BASE}/admin/api-keys?name=Test+Key" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}")

echo "$RESPONSE" | python3 -m json.tool

# Extract the key (requires jq or python)
NEW_KEY=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['api_key'])")
KEY_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo ""
echo "✅ API Key created: $NEW_KEY"
echo "⚠️  SAVE THIS KEY - it's only shown once!"
echo ""

read -p "Press Enter to test using this key..."

echo ""
echo "Step 2: Testing API key..."
curl -s -X GET "${API_BASE}/v1/jobs?limit=5" \
  -H "Authorization: Bearer ${NEW_KEY}" | python3 -m json.tool

echo ""
echo "✅ If you see jobs, the key works!"
echo ""
echo "Step 3: Listing all keys..."
curl -s -X GET "${API_BASE}/admin/api-keys" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -m json.tool
```

Make it executable and run:
```bash
chmod +x test_new_api_keys.sh
./test_new_api_keys.sh
```

---

## Troubleshooting

### Error: "ADMIN_TOKEN not configured"
- Set `ADMIN_TOKEN` in Railway Variables
- Restart the service if needed

### Error: "Invalid admin token"
- Check that `ADMIN_TOKEN` in Railway matches what you're sending
- Make sure header is `X-Admin-Token` (not `X-ADMIN-TOKEN`)

### Error: "Invalid or inactive API key"
- Key might be revoked - check with admin endpoint
- Make sure you're using the full key (starts with `dp_`)

### Error: "API key required"
- Make sure you're sending the header
- Use either `Authorization: Bearer <key>` or `X-API-Key: <key>`

---

## What This Tests

✅ **Database-backed keys** - Keys stored in database (hashed)  
✅ **Admin endpoint** - Create keys via admin endpoint  
✅ **Authentication** - Keys work for API calls  
✅ **Revocation** - Revoked keys don't work  
✅ **Activation** - Reactivated keys work again  
✅ **Security** - Keys not shown in list endpoint  

---

## Comparison: Old vs New

| Feature | Old (`dev_123`) | New (Database Keys) |
|---------|----------------|---------------------|
| Storage | Environment variable | Database (hashed) |
| Creation | Manual env var | Admin endpoint |
| Revocation | Can't revoke | Can revoke/activate |
| Usage tracking | No | `last_used_at` tracked |
| Security | Plain text | SHA256 hashed |

Both work simultaneously - `dev_123` still works for backward compatibility!

