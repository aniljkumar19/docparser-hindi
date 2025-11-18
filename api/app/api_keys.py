"""API Key management endpoints"""
import secrets
import hashlib
from fastapi import APIRouter, HTTPException, status, Header, Depends, Request
from typing import Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel
from .db import SessionLocal, ApiKey
from .security import hash_api_key

router = APIRouter(prefix="/v1/api-keys", tags=["API Keys"])

class CreateApiKeyRequest(BaseModel):
    name: Optional[str] = None
    tenant_id: str
    rate_limit_per_minute: Optional[int] = 60
    rate_limit_per_hour: Optional[int] = 1000

class ApiKeyResponse(BaseModel):
    id: str
    key: str  # Only shown once on creation
    name: Optional[str]
    tenant_id: str
    is_active: str
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    last_used_at: Optional[str]
    created_at: str

class ApiKeyListResponse(BaseModel):
    id: str
    name: Optional[str]
    tenant_id: str
    is_active: str
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    last_used_at: Optional[str]
    created_at: str
    # Note: 'key' is NOT included in list for security

def generate_api_key() -> str:
    """Generate a secure API key"""
    # Format: dp_<32 random hex chars>
    random_part = secrets.token_hex(16)
    return f"dp_{random_part}"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_tenant(request: Request, authorization: str | None = Header(None), x_api_key: str | None = Header(None, alias="x-api-key")) -> str:
    """Get tenant_id from request state (if middleware is enabled) or from API key verification"""
    # Try to get from request state (set by middleware if enabled)
    if hasattr(request.state, "tenant_id"):
        return request.state.tenant_id
    
    # Fallback: verify API key and extract tenant_id
    from .security import verify_api_key
    try:
        _, tenant_id = verify_api_key(authorization, x_api_key)
        return tenant_id
    except HTTPException:
        raise HTTPException(status_code=401, detail="Not authenticated")

@router.post("/", response_model=ApiKeyResponse)
def create_api_key(
    req: CreateApiKeyRequest,
    request: Request,
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="x-api-key"),
    db: Session = Depends(get_db)
):
    """Create a new API key. The key is only shown once - save it immediately!"""
    # Generate API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    
    # Check for hash collision (very unlikely)
    existing = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
    if existing:
        raise HTTPException(status_code=500, detail="Key collision (retry)")
    
    # Verify that the requester has permission to create keys for this tenant
    # (In production, you might want stricter checks here)
    requester_tenant = get_current_tenant(request, authorization, x_api_key)
    if req.tenant_id != requester_tenant:
        raise HTTPException(status_code=403, detail="Cannot create keys for different tenant")
    
    # Create database record
    db_key = ApiKey(
        key_hash=key_hash,
        tenant_id=req.tenant_id,
        name=req.name,
        is_active="active",
        rate_limit_per_minute=req.rate_limit_per_minute or 60,
        rate_limit_per_hour=req.rate_limit_per_hour or 1000,
        created_by=requester_tenant
    )
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    
    return ApiKeyResponse(
        id=db_key.id,
        key=api_key,  # Only time the key is returned
        name=db_key.name,
        tenant_id=db_key.tenant_id,
        is_active=db_key.is_active,
        rate_limit_per_minute=db_key.rate_limit_per_minute,
        rate_limit_per_hour=db_key.rate_limit_per_hour,
        last_used_at=db_key.last_used_at.isoformat() if db_key.last_used_at else None,
        created_at=db_key.created_at.isoformat() if db_key.created_at else None
    )

@router.get("/", response_model=list[ApiKeyListResponse])
def list_api_keys(
    request: Request,
    tenant_id: Optional[str] = None,
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="x-api-key"),
    db: Session = Depends(get_db)
):
    """List all API keys for a tenant"""
    # Use tenant_id from request state if not provided
    filter_tenant = tenant_id or get_current_tenant(request, authorization, x_api_key)
    
    keys = db.query(ApiKey).filter(ApiKey.tenant_id == filter_tenant).all()
    
    return [
        ApiKeyListResponse(
            id=k.id,
            name=k.name,
            tenant_id=k.tenant_id,
            is_active=k.is_active,
            rate_limit_per_minute=k.rate_limit_per_minute,
            rate_limit_per_hour=k.rate_limit_per_hour,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            created_at=k.created_at.isoformat() if k.created_at else None
        )
        for k in keys
    ]

@router.post("/{key_id}/revoke")
def revoke_api_key(
    key_id: str,
    request: Request,
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="x-api-key"),
    db: Session = Depends(get_db)
):
    """Revoke an API key"""
    tenant_id = get_current_tenant(request, authorization, x_api_key)
    
    key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.tenant_id == tenant_id
    ).first()
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    key.is_active = "revoked"
    db.commit()
    
    return {"ok": True, "message": "API key revoked"}

@router.post("/{key_id}/reactivate")
def reactivate_api_key(
    key_id: str,
    request: Request,
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="x-api-key"),
    db: Session = Depends(get_db)
):
    """Reactivate a revoked API key"""
    tenant_id = get_current_tenant(request, authorization, x_api_key)
    
    key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.tenant_id == tenant_id
    ).first()
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    key.is_active = "active"
    db.commit()
    
    return {"ok": True, "message": "API key reactivated"}

@router.delete("/{key_id}")
def delete_api_key(
    key_id: str,
    request: Request,
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="x-api-key"),
    db: Session = Depends(get_db)
):
    """Permanently delete an API key"""
    tenant_id = get_current_tenant(request, authorization, x_api_key)
    
    key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.tenant_id == tenant_id
    ).first()
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    db.delete(key)
    db.commit()
    
    return {"ok": True, "message": "API key deleted"}

