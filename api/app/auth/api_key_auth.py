"""API Key authentication dependency for FastAPI routes"""
from fastapi import Depends, Header, HTTPException, status
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
    db: Session = Depends(get_db),
    raw_key: str | None = Depends(get_api_key_from_headers),
) -> ApiKey:
    """
    Dependency that requires a valid API key.
    Use this in router dependencies or individual route dependencies.
    
    Example:
        router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])
    """
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Use Authorization: Bearer <key> or X-API-Key: <key>",
        )
    
    # First try database lookup (hashed keys)
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

