# API Key Production - Direct Answers

## Your 3 Questions Answered

### 1. Who Creates API Keys?

**Current State (Testing):**
- ❌ **Anyone** with an API key can create more keys
- Not suitable for production

**Production Solution:**
- ✅ **Admin Panel** - Only admins can create keys
- ✅ **Self-Service** - Users can create keys for their own account (with limits)
- ✅ **Hybrid** - Admins for all tenants, users for their own tenant

**Implementation:**
```
Admin Dashboard → Create Key → Assign to Tenant → Set Quotas
OR
User Dashboard → Create Key → Auto-assigned to my account
```

---

### 2. How to Control Number of People/Keys?

**Current State:**
- ❌ No limit on number of API keys
- ❌ No user management

**Production Solution:**

**A. Plan-Based Limits:**
```python
Free Plan:    1 API key,  1 user
Pro Plan:     5 API keys, 10 users  
Enterprise:   Unlimited API keys, unlimited users
```

**B. Database Schema:**
```sql
tenants table:
  - plan: VARCHAR (free/pro/enterprise)
  - max_api_keys: INTEGER (from plan)
  - max_users: INTEGER (from plan)

api_keys table:
  - tenant_id: VARCHAR (links to tenant)
  - user_id: VARCHAR (who created it)
```

**C. Enforcement:**
```python
# Before creating a key, check:
def can_create_key(tenant_id):
    tenant = get_tenant(tenant_id)
    current_keys = count_api_keys(tenant_id)
    return current_keys < tenant.max_api_keys
```

**Where to Set:**
- **Admin Dashboard** → Tenant Settings → Change Plan → Auto-updates limits
- **Database** → `tenants.plan` → `tenants.max_api_keys` (from plan config)

---

### 3. How to Limit Documents Per API Key?

**Current State:**
- ❌ No document quota system
- ❌ Unlimited documents

**Production Solution:**

**A. Add Quota Fields to ApiKey:**
```sql
ALTER TABLE api_keys ADD COLUMN document_quota INTEGER;
ALTER TABLE api_keys ADD COLUMN documents_used INTEGER DEFAULT 0;
ALTER TABLE api_keys ADD COLUMN quota_reset_date DATE;
```

**B. Plan-Based Quotas:**
```python
Free Plan:     100 documents/month
Pro Plan:      10,000 documents/month
Enterprise:    Unlimited
```

**C. Enforcement in Parse Endpoint:**
```python
@app.post("/v1/parse")
async def parse_endpoint(...):
    # Check quota BEFORE parsing
    if api_key.documents_used >= api_key.document_quota:
        raise HTTPException(402, "Quota exceeded")
    
    # Parse document...
    
    # Increment usage AFTER success
    api_key.documents_used += 1
```

**D. Monthly Reset:**
```python
# Cron job runs daily
def reset_quotas():
    keys = get_keys_where_reset_date_passed()
    for key in keys:
        key.documents_used = 0
        key.quota_reset_date = next_month()
```

**Where to Set:**
- **Admin Dashboard** → Create/Edit API Key → Set `document_quota`
- **Plan Assignment** → Auto-assigns quota based on plan
- **Database** → `api_keys.document_quota` (NULL = unlimited)

---

## Quick Implementation Checklist

### Phase 1: Basic Quota System (1-2 days)
- [ ] Add `document_quota`, `documents_used`, `quota_reset_date` to ApiKey model
- [ ] Add quota check in `/v1/parse` endpoint
- [ ] Increment `documents_used` after successful parse
- [ ] Create cron job to reset monthly quotas

### Phase 2: Plan Management (2-3 days)
- [ ] Create `Tenant` model with `plan` field
- [ ] Create plan config (Free/Pro/Enterprise)
- [ ] Auto-assign quotas when creating keys based on plan
- [ ] Add `max_api_keys` limit per tenant

### Phase 3: Admin Panel (3-5 days)
- [ ] Create admin user system
- [ ] Build admin endpoints:
  - `POST /v1/admin/api-keys/create` (create for any tenant)
  - `GET /v1/admin/tenants` (list all)
  - `POST /v1/admin/tenants/{id}/upgrade` (change plan)
- [ ] Build admin dashboard UI

### Phase 4: Self-Service (2-3 days)
- [ ] User can create keys for their own tenant
- [ ] Check `max_api_keys` limit before creation
- [ ] User dashboard to view usage/quota

---

## Example: Production Flow

### Scenario: CA Firm Signs Up

1. **Admin creates tenant:**
   ```
   POST /v1/admin/tenants
   {
     "name": "ABC CA Firm",
     "plan": "pro"
   }
   ```

2. **System auto-assigns limits:**
   - `max_api_keys`: 5
   - `max_users`: 10
   - Default quota per key: 10,000 docs/month

3. **Admin creates API key:**
   ```
   POST /v1/admin/api-keys/create
   {
     "tenant_id": "tenant_abc",
     "name": "Production Key",
     "document_quota": 10000  // From plan
   }
   ```

4. **User uses key:**
   - Each parse increments `documents_used`
   - If `documents_used >= document_quota` → Error 402
   - Monthly reset via cron

5. **Usage tracking:**
   ```
   GET /v1/api-keys/{id}/usage
   {
     "documents_used": 1234,
     "document_quota": 10000,
     "quota_reset_date": "2025-02-15"
   }
   ```

---

## Summary Table

| Question | Current | Production Solution |
|---------|---------|---------------------|
| **Who creates keys?** | Anyone | Admin panel OR self-service with limits |
| **Control # of keys?** | No limit | Plan-based: `tenants.max_api_keys` |
| **Document limits?** | Unlimited | `api_keys.document_quota` + enforcement |

**Key Files to Modify:**
1. `api/app/db.py` - Add quota fields to ApiKey, create Tenant model
2. `api/app/main.py` - Add quota check in parse endpoint
3. `api/app/api_keys.py` - Add quota fields to create endpoint
4. New: `api/app/admin.py` - Admin endpoints
5. New: `api/app/plans.py` - Plan configuration

**Database Changes:**
- Add columns to `api_keys` table
- Create `tenants` table
- Create `users` table (optional, for user management)

