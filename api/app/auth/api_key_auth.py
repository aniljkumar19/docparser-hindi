"""API Key authentication dependency for FastAPI routes"""
from fastapi import Depends, Header, HTTPException, status, Request
from sqlalchemy.orm import Session
from ..db import SessionLocal, ApiKey
from ..security import hash_api_key, _extract_key

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_api_key_from_headers(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
) -> str | None:
    """Extract API key from headers. Supports both Authorization: Bearer and X-API-Key"""
    return _extract_key(authorization, x_api_key)

def require_api_key(
    request: Request,
    db: Session = Depends(get_db),
    raw_key: str | None = Depends(get_api_key_from_headers),
) -> ApiKey:
    """
    Dependency that requires a valid API key.
    Use this in router dependencies or individual route dependencies.
    
    Example:
        router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])
    
    NOTE: If USE_API_KEY_MIDDLEWARE is enabled, this will check request.state.middleware_authenticated
    first and skip verification if middleware already authenticated the request.
    """
    # Check if middleware already authenticated this request
    if request and hasattr(request.state, 'middleware_authenticated') and request.state.middleware_authenticated:
        # Middleware already verified, return a mock ApiKey object
        api_key = getattr(request.state, 'api_key', None) or raw_key
        tenant_id = getattr(request.state, 'tenant_id', None) or ""
        
        class MiddlewareAuthenticatedApiKey:
            def __init__(self, key, tenant_id):
                self.id = f"middleware_{key[:10] if key else 'unknown'}"
                self.key_hash = ""
                self.tenant_id = tenant_id
                self.name = "Middleware Authenticated"
                self.is_active = "active"
                self.rate_limit_per_minute = 60
                self.rate_limit_per_hour = 1000
                self.last_used_at = None
                self.created_at = None
        
        return MiddlewareAuthenticatedApiKey(api_key, tenant_id)
    
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Use Authorization: Bearer <key> or X-API-Key: <key>",
        )
    
    # 1) Master key from env (DOCPARSER_API_KEY) - used by dashboard + test script
    import os
    master_key = os.getenv("DOCPARSER_API_KEY")
    if master_key and raw_key == master_key:
        # Return a mock ApiKey object for master key
        class MasterApiKey:
            def __init__(self, key):
                self.id = f"master_{key[:10] if key else 'unknown'}"
                self.key_hash = ""
                self.tenant_id = "master"
                self.name = "Master API Key"
                self.is_active = "active"
                self.rate_limit_per_minute = 60
                self.rate_limit_per_hour = 1000
                self.last_used_at = None
                self.created_at = None
        
        return MasterApiKey(raw_key)
    
    # 2) Database lookup (hashed keys)
    key_hash = hash_api_key(raw_key)
    api_key = (
        db.query(ApiKey)
        .filter(ApiKey.key_hash == key_hash, ApiKey.is_active == "active")
        .first()
    )
    
    if api_key:
        # Update last_used_at
        from datetime import datetime, timezone
        api_key.last_used_at = datetime.now(timezone.utc)
        db.commit()
        return api_key
    
    # Fallback to legacy env var keys (for backward compatibility)
    from ..security import API_KEY_TENANTS
    tenant_id = API_KEY_TENANTS.get(raw_key)
    if tenant_id:
        # Return a mock ApiKey object for legacy keys
        # This allows backward compatibility
        class LegacyApiKey:
            def __init__(self, key, tenant_id):
                self.id = f"legacy_{raw_key}"
                self.key_hash = key_hash
                self.tenant_id = tenant_id
                self.name = "Legacy Key"
                self.is_active = "active"
                self.rate_limit_per_minute = 60
                self.rate_limit_per_hour = 1000
                self.last_used_at = None
                self.created_at = None
        
        return LegacyApiKey(raw_key, tenant_id)
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or inactive API key.",
    )

