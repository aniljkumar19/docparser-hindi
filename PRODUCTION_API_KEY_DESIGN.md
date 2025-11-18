# Production API Key System - Design & Implementation Plan

## Current State (Testing/Development)

### ❌ What's Missing for Production

1. **No Admin/User Roles**
   - Currently: Anyone with an API key can create more keys
   - Problem: No way to restrict who can create keys

2. **No Document Quota System**
   - Currently: No limit on documents per API key
   - Problem: Can't enforce subscription limits

3. **No User Management**
   - Currently: Only `tenant_id` exists
   - Problem: Can't track individual users or control access

4. **No Subscription/Plan Management**
   - Currently: No way to assign plans (Free, Pro, Enterprise)
   - Problem: Can't enforce different limits per plan

---

## Production Design

### 1. Who Creates API Keys?

**Option A: Admin-Only (Recommended for B2B SaaS)**
```
Admin Dashboard → Create API Key → Assign to Tenant/User
```

**Option B: Self-Service (For Developer-Focused SaaS)**
```
User Dashboard → Create API Key → Auto-assigned to their account
```

**Option C: Hybrid**
```
- Admins can create keys for any tenant
- Users can create keys for their own tenant (with limits)
```

**Recommended: Option C (Hybrid)**

---

### 2. How to Control Number of Users/Keys?

**Database Schema:**
```sql
-- Tenant/Organization table
CREATE TABLE tenants (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    plan VARCHAR DEFAULT 'free',  -- free, pro, enterprise
    max_api_keys INTEGER DEFAULT 1,  -- Plan-based limit
    max_users INTEGER DEFAULT 1,     -- Plan-based limit
    created_at TIMESTAMP
);

-- User table
CREATE TABLE users (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    role VARCHAR DEFAULT 'user',  -- admin, user, viewer
    created_at TIMESTAMP
);

-- API Key table (enhanced)
CREATE TABLE api_keys (
    id VARCHAR PRIMARY KEY,
    key_hash VARCHAR UNIQUE NOT NULL,
    tenant_id VARCHAR NOT NULL,
    user_id VARCHAR,  -- Who created it (optional)
    name VARCHAR,
    is_active VARCHAR DEFAULT 'active',
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_hour INTEGER DEFAULT 1000,
    document_quota INTEGER,  -- NEW: Max documents allowed
    documents_used INTEGER DEFAULT 0,  -- NEW: Documents parsed so far
    quota_reset_date DATE,  -- NEW: When quota resets (monthly/yearly)
    created_at TIMESTAMP
);
```

**Enforcement Logic:**
```python
def can_create_api_key(tenant_id: str, db: Session) -> bool:
    """Check if tenant can create more API keys"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        return False
    
    current_keys = db.query(ApiKey).filter(
        ApiKey.tenant_id == tenant_id,
        ApiKey.is_active == "active"
    ).count()
    
    return current_keys < tenant.max_api_keys
```

---

### 3. Document Quota System

**Database Schema (already have `Job` table):**
```sql
-- Track usage per API key
SELECT COUNT(*) FROM jobs 
WHERE api_key = 'key_hash' 
AND created_at >= quota_reset_date;
```

**Enhance ApiKey Model:**
```python
class ApiKey(Base):
    # ... existing fields ...
    document_quota = Column(Integer, nullable=True)  # NULL = unlimited
    documents_used = Column(Integer, default=0)
    quota_reset_date = Column(Date, nullable=True)  # Monthly/yearly reset
    quota_period = Column(String, default="monthly")  # monthly, yearly, lifetime
```

**Enforcement in Parse Endpoint:**
```python
@app.post("/v1/parse")
async def parse_endpoint(
    file: UploadFile = File(...),
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="x-api-key"),
):
    api_key, tenant_id = verify_api_key(authorization, x_api_key)
    
    # Check document quota
    with SessionLocal() as db:
        key_obj = db.query(ApiKey).filter(
            ApiKey.key_hash == hash_api_key(api_key)
        ).first()
        
        if key_obj and key_obj.document_quota:
            # Check if quota reset is needed
            if key_obj.quota_reset_date and datetime.now().date() >= key_obj.quota_reset_date:
                key_obj.documents_used = 0
                # Set next reset date
                if key_obj.quota_period == "monthly":
                    key_obj.quota_reset_date = (datetime.now() + timedelta(days=30)).date()
                elif key_obj.quota_period == "yearly":
                    key_obj.quota_reset_date = (datetime.now() + timedelta(days=365)).date()
                db.commit()
            
            if key_obj.documents_used >= key_obj.document_quota:
                raise HTTPException(
                    status_code=402,  # Payment Required
                    detail=f"Document quota exceeded ({key_obj.document_quota} documents). Upgrade your plan or wait for quota reset."
                )
        
        # ... rest of parsing logic ...
        
        # Increment usage after successful parse
        if key_obj:
            key_obj.documents_used += 1
            db.commit()
```

---

## Implementation Plan

### Phase 1: Admin Panel & User Management

**1. Create Admin User System**
```python
# api/app/models.py
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String)  # For admin login
    role = Column(String, default="user")  # admin, user, viewer
    created_at = Column(TIMESTAMP)
```

**2. Admin Dashboard Endpoints**
```python
# POST /v1/admin/api-keys/create
# - Requires admin role
# - Can create keys for any tenant
# - Can set quotas, rate limits

# GET /v1/admin/tenants
# - List all tenants
# - View usage stats

# POST /v1/admin/tenants/{id}/upgrade
# - Change plan
# - Update max_keys, max_users, quotas
```

**3. Self-Service Key Creation (for users)**
```python
# POST /v1/api-keys/create
# - User can create keys for their own tenant
# - Check tenant.max_api_keys limit
# - Auto-assign quotas based on plan
```

---

### Phase 2: Subscription/Plan Management

**1. Plan Definitions**
```python
PLANS = {
    "free": {
        "max_api_keys": 1,
        "max_users": 1,
        "document_quota": 100,  # per month
        "rate_limit_per_minute": 10,
        "rate_limit_per_hour": 100
    },
    "pro": {
        "max_api_keys": 5,
        "max_users": 10,
        "document_quota": 10000,  # per month
        "rate_limit_per_minute": 100,
        "rate_limit_per_hour": 5000
    },
    "enterprise": {
        "max_api_keys": -1,  # unlimited
        "max_users": -1,  # unlimited
        "document_quota": -1,  # unlimited
        "rate_limit_per_minute": 1000,
        "rate_limit_per_hour": 50000
    }
}
```

**2. Tenant Model**
```python
class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    plan = Column(String, default="free")
    max_api_keys = Column(Integer, default=1)
    max_users = Column(Integer, default=1)
    stripe_customer_id = Column(String, nullable=True)  # For billing
    created_at = Column(TIMESTAMP)
```

**3. Auto-Assign Quotas on Key Creation**
```python
def create_api_key_with_plan_defaults(tenant_id: str, db: Session):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    plan_config = PLANS.get(tenant.plan, PLANS["free"])
    
    api_key = ApiKey(
        tenant_id=tenant_id,
        document_quota=plan_config["document_quota"],
        rate_limit_per_minute=plan_config["rate_limit_per_minute"],
        rate_limit_per_hour=plan_config["rate_limit_per_hour"],
        quota_period="monthly",
        quota_reset_date=(datetime.now() + timedelta(days=30)).date()
    )
    # ... save to db
```

---

### Phase 3: Usage Tracking & Quota Enforcement

**1. Track Usage in Job Creation**
```python
# In parse_endpoint, after job is created:
with SessionLocal() as db:
    key_obj = db.query(ApiKey).filter(
        ApiKey.key_hash == hash_api_key(api_key)
    ).first()
    
    if key_obj:
        key_obj.documents_used += 1
        db.commit()
```

**2. Quota Reset Job (Cron)**
```python
# Run daily to reset quotas
def reset_monthly_quotas():
    with SessionLocal() as db:
        keys = db.query(ApiKey).filter(
            ApiKey.quota_reset_date <= datetime.now().date()
        ).all()
        
        for key in keys:
            key.documents_used = 0
            if key.quota_period == "monthly":
                key.quota_reset_date = (datetime.now() + timedelta(days=30)).date()
            # ... update reset date
        
        db.commit()
```

**3. Usage Dashboard**
```python
# GET /v1/api-keys/{id}/usage
{
    "documents_used": 45,
    "document_quota": 100,
    "quota_reset_date": "2025-02-15",
    "rate_limit_per_minute": 60,
    "rate_limit_per_hour": 1000
}
```

---

## Recommended Production Flow

### For B2B SaaS (CA Firms):

1. **Admin creates tenant** (via admin panel or signup)
2. **Admin assigns plan** (Free/Pro/Enterprise)
3. **Admin creates API keys** for the tenant
4. **System auto-assigns quotas** based on plan
5. **Users use API keys** (tracked per key)
6. **Quota enforced** on each parse request
7. **Monthly reset** via cron job

### For Self-Service:

1. **User signs up** → Creates tenant automatically
2. **User selects plan** (Free/Pro/Enterprise)
3. **User creates API keys** (up to plan limit)
4. **System auto-assigns quotas** based on plan
5. **Usage tracked** and displayed in dashboard
6. **Upgrade prompts** when quota exceeded

---

## Database Migration Needed

```sql
-- Add to existing api_keys table
ALTER TABLE docparser.api_keys 
ADD COLUMN document_quota INTEGER,
ADD COLUMN documents_used INTEGER DEFAULT 0,
ADD COLUMN quota_reset_date DATE,
ADD COLUMN quota_period VARCHAR DEFAULT 'monthly',
ADD COLUMN user_id VARCHAR;

-- Create tenants table
CREATE TABLE docparser.tenants (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    plan VARCHAR DEFAULT 'free',
    max_api_keys INTEGER DEFAULT 1,
    max_users INTEGER DEFAULT 1,
    stripe_customer_id VARCHAR,
    created_at TIMESTAMP
);

-- Create users table
CREATE TABLE docparser.users (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR,
    role VARCHAR DEFAULT 'user',
    created_at TIMESTAMP
);
```

---

## Summary

**Current State:**
- ✅ API keys work
- ✅ Rate limiting works
- ❌ No admin/user roles
- ❌ No document quotas
- ❌ No plan management

**Production Needs:**
1. **Admin panel** to create/manage keys
2. **User/tenant management** system
3. **Subscription/plan** system
4. **Document quota** tracking & enforcement
5. **Usage dashboard** for users

**Next Steps:**
1. Build tenant/user models
2. Add document quota fields to ApiKey
3. Implement quota checking in parse endpoint
4. Build admin endpoints
5. Create usage dashboard

