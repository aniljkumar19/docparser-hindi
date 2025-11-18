# Production API Key System

## Overview

The production API key system replaces the simple environment variable-based authentication with a full database-backed system that includes:

- ✅ Database storage (hashed keys)
- ✅ Rate limiting (per minute/hour)
- ✅ Key management (create, revoke, reactivate)
- ✅ Usage tracking (last_used_at)
- ✅ Middleware-based authentication
- ✅ Backward compatibility with env var keys

## Architecture

### Database Schema

```sql
CREATE TABLE docparser.api_keys (
    id VARCHAR PRIMARY KEY,
    key_hash VARCHAR UNIQUE NOT NULL,  -- SHA256 hash of the key
    tenant_id VARCHAR NOT NULL,
    name VARCHAR,  -- User-friendly name
    is_active VARCHAR DEFAULT 'active',  -- 'active' or 'revoked'
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_hour INTEGER DEFAULT 1000,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP,
    created_by VARCHAR
);
```

### Components

1. **Middleware** (`api/app/middleware/auth.py`)
   - Authenticates API keys on every request
   - Enforces rate limits
   - Updates `last_used_at` timestamp
   - Attaches `tenant_id` to `request.state`

2. **Security Module** (`api/app/security.py`)
   - Backward-compatible `verify_api_key()` function
   - Checks database first, falls back to env vars
   - Supports both old and new systems

3. **API Key Management** (`api/app/api_keys.py`)
   - CRUD endpoints for API keys
   - Key generation (format: `dp_<32 hex chars>`)
   - Revoke/reactivate functionality

## Usage

### Enable Middleware (Optional)

The middleware is **opt-in** via environment variable:

```bash
USE_API_KEY_MIDDLEWARE=true
```

When enabled:
- All `/v1/*` endpoints require authentication
- Rate limiting is enforced automatically
- Endpoints can use `request.state.tenant_id` instead of calling `verify_api_key()`

When disabled (default):
- Endpoints use the legacy `verify_api_key()` function
- Backward compatible with existing code

### Creating API Keys

**Via API:**
```bash
POST /v1/api-keys/
{
  "name": "Production Key",
  "tenant_id": "tenant_demo",
  "rate_limit_per_minute": 100,
  "rate_limit_per_hour": 5000
}

Response:
{
  "id": "key_abc123",
  "key": "dp_a1b2c3d4e5f6...",  # ⚠️ Only shown once!
  "name": "Production Key",
  "tenant_id": "tenant_demo",
  ...
}
```

**⚠️ IMPORTANT:** The `key` field is only returned once on creation. Save it immediately!

### Listing Keys

```bash
GET /v1/api-keys/?tenant_id=tenant_demo

Response:
[
  {
    "id": "key_abc123",
    "name": "Production Key",
    "tenant_id": "tenant_demo",
    "is_active": "active",
    "rate_limit_per_minute": 100,
    "rate_limit_per_hour": 5000,
    "last_used_at": "2025-01-15T10:30:00Z",
    "created_at": "2025-01-10T08:00:00Z"
    # Note: 'key' is NOT included for security
  }
]
```

### Revoking Keys

```bash
POST /v1/api-keys/{key_id}/revoke
```

### Using API Keys

**Header format:**
```bash
x-api-key: dp_a1b2c3d4e5f6...
# OR
Authorization: Bearer dp_a1b2c3d4e5f6...
```

## Migration from Environment Variables

### Step 1: Run Migration Script

```bash
cd api
python -m app.migrate_api_keys
```

This creates database records for existing env var keys (but note: the original keys can't be stored, so users need to create new keys).

### Step 2: Create New Keys

For each tenant, create a new key via the API:

```bash
POST /v1/api-keys/
{
  "name": "Production Key",
  "tenant_id": "tenant_demo",
  "rate_limit_per_minute": 100,
  "rate_limit_per_hour": 5000
}
```

### Step 3: Update Applications

Update all applications to use the new keys.

### Step 4: Enable Middleware (Optional)

Once all applications are migrated:

```bash
USE_API_KEY_MIDDLEWARE=true
```

### Step 5: Remove Environment Variables

After migration is complete, you can remove `API_KEYS` from environment variables.

## Rate Limiting

Rate limits are enforced per API key:

- **Per minute:** Default 60 requests (configurable)
- **Per hour:** Default 1000 requests (configurable)

When exceeded, API returns:
```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```
Status: `429 Too Many Requests`

## Security

1. **Key Hashing:** All keys are stored as SHA256 hashes
2. **Never Logged:** Original keys are never logged or stored in plaintext
3. **One-Time Display:** Keys are only shown once on creation
4. **Revocation:** Keys can be revoked instantly without deletion
5. **Rate Limiting:** Prevents abuse and DoS attacks

## Backward Compatibility

The system maintains backward compatibility:

- Legacy `verify_api_key()` function checks database first, then env vars
- Existing endpoints continue to work without changes
- Middleware is opt-in (disabled by default)

## Future Enhancements

- [ ] Usage metering dashboard (requests per key, per day/month)
- [ ] Redis-based rate limiting (for distributed systems)
- [ ] Key rotation policies
- [ ] Webhook notifications for key events
- [ ] Frontend UI for key management

