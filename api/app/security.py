# api/app/security.py
import os
import hashlib
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from .db import SessionLocal, ApiKey

# Legacy: Environment variable-based API keys (for backward compatibility)
def _load_key_map() -> dict[str, str]:
    # Try multiple sources for API_KEYS
    raw = os.getenv("API_KEYS", "").strip()
    
    # If empty, try default fallback
    if not raw:
        raw = "dev_123:tenant_demo"
    
    mapping: dict[str, str] = {}
    for token in [s.strip() for s in raw.split(",") if s.strip()]:
        if ":" in token:
            k, t = token.split(":", 1)
        else:
            k, t = token, "default"
        mapping[k.strip()] = t.strip()
    return mapping

API_KEY_TENANTS = _load_key_map()

def reload_api_keys() -> None:
    global API_KEY_TENANTS
    API_KEY_TENANTS = _load_key_map()

def hash_api_key(key: str) -> str:
    """Hash an API key using SHA256"""
    return hashlib.sha256(key.encode()).hexdigest()

def _extract_key(authorization: str | None, x_api_key: str | None) -> str:
    # IMPORTANT: Check x-api-key header FIRST (this is the preferred method)
    # FastAPI converts x-api-key header to x_api_key parameter automatically
    if x_api_key and isinstance(x_api_key, str) and x_api_key.strip():
        return x_api_key.strip()
    # Fallback to Authorization Bearer header
    if authorization and isinstance(authorization, str) and authorization.lower().startswith("bearer "):
        return authorization.split(None, 1)[1].strip()
    # If neither is provided, raise error with helpful message
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, 
        detail="Missing API key. Please provide either 'x-api-key' header or 'Authorization: Bearer <token>' header"
    )

def verify_api_key(authorization: str | None, x_api_key: str | None) -> tuple[str, str]:
    """
    Verify API key - supports both database-backed keys and legacy env var keys.
    This is the backward-compatible function used by existing endpoints.
    For new code, use the middleware which provides request.state.tenant_id.
    """
    key = _extract_key(authorization, x_api_key)
    
    # First, try database lookup (new method)
    key_hash = hash_api_key(key)
    with SessionLocal() as db:
        api_key_obj = db.query(ApiKey).filter(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active == "active"
        ).first()
        if api_key_obj:
            # Update last_used_at
            from datetime import datetime, timezone
            api_key_obj.last_used_at = datetime.now(timezone.utc)
            db.commit()
            return key, api_key_obj.tenant_id
    
    # Fallback to legacy env var method (for backward compatibility)
    tenant_id = API_KEY_TENANTS.get(key)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return key, tenant_id
