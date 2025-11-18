# api/app/security.py
import os
import hashlib
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from .db import SessionLocal, ApiKey

# Legacy: Environment variable-based API keys (for backward compatibility)
def _load_key_map() -> dict[str, str]:
    # Try multiple sources for API_KEYS
    # Important: Check if API_KEYS is explicitly set vs not set at all
    # If explicitly set to empty string, we still use default
    raw = os.getenv("API_KEYS", "").strip()
    
    # If empty or not set, use default fallback
    # This ensures dev_123 always works for development/testing
    if not raw:
        raw = "dev_123:tenant_demo"
        import logging
        logging.info("API_KEYS not set, using default: dev_123:tenant_demo")
    else:
        import logging
        logging.info(f"API_KEYS loaded from environment: {raw[:20]}...")
    
    mapping: dict[str, str] = {}
    for token in [s.strip() for s in raw.split(",") if s.strip()]:
        if ":" in token:
            k, t = token.split(":", 1)
        else:
            k, t = token, "default"
        mapping[k.strip()] = t.strip()
    
    import logging
    logging.info(f"Loaded {len(mapping)} API keys from env vars: {list(mapping.keys())}")
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
    import logging
    key = _extract_key(authorization, x_api_key)
    
    # Log the key being verified (first 12 chars + last 4 for debugging)
    key_preview = key[:12] + "..." + key[-4:] if len(key) > 16 else key
    logging.info(f"Verifying API key: {key_preview} (length: {len(key)}, starts with: {key[:3] if len(key) >= 3 else key})")
    
    # Check for common issues
    if key.startswith(" ") or key.endswith(" "):
        logging.warning(f"⚠️  API key has leading/trailing whitespace! Original length: {len(key)}")
        key = key.strip()
        logging.info(f"   Trimmed key: {key[:12]}...{key[-4:]} (length: {len(key)})")
    
    # First, try database lookup (new method)
    key_hash = hash_api_key(key)
    logging.info(f"Key hash (first 16 chars): {key_hash[:16]}...")
    
    with SessionLocal() as db:
        # Check ALL keys (not just active) to see what's in the database
        all_keys = db.query(ApiKey).all()
        all_active_keys = db.query(ApiKey).filter(ApiKey.is_active == "active").all()
        logging.info(f"Found {len(all_keys)} total API keys in database ({len(all_active_keys)} active)")
        
        # If no keys at all, log database connection info
        if len(all_keys) == 0:
            from .db import DB_URL
            logging.warning(f"⚠️  No API keys found in database at all!")
            logging.warning(f"   Database URL: {DB_URL[:50]}..." if len(DB_URL) > 50 else f"   Database URL: {DB_URL}")
            logging.warning(f"   This might mean:")
            logging.warning(f"   1. Keys were created in a different database")
            logging.warning(f"   2. Database connection is pointing to wrong database")
            logging.warning(f"   3. Keys were never saved (transaction issue)")
        
        # Try exact hash match (check both active and inactive)
        api_key_obj = db.query(ApiKey).filter(
            ApiKey.key_hash == key_hash
        ).first()
        
        if api_key_obj:
            # Check if it's active
            if api_key_obj.is_active != "active":
                logging.warning(f"⚠️  API key found but is INACTIVE (status: {api_key_obj.is_active})")
                logging.warning(f"   Key ID: {api_key_obj.id}, Name: {api_key_obj.name}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"API key is inactive (status: {api_key_obj.is_active})"
                )
            
            # Update last_used_at
            from datetime import datetime, timezone
            api_key_obj.last_used_at = datetime.now(timezone.utc)
            db.commit()
            logging.info(f"✅ API key verified from database (tenant: {api_key_obj.tenant_id}, name: {api_key_obj.name})")
            return key, api_key_obj.tenant_id
        else:
            # Log what we found for debugging
            logging.warning(f"❌ No matching API key found in database")
            logging.warning(f"   Searched hash: {key_hash[:16]}...")
            logging.warning(f"   Key being verified: {key_preview} (length: {len(key)})")
            logging.warning(f"   Total keys in DB: {len(all_keys)}, Active: {len(all_active_keys)}")
            if all_keys:
                for k in all_keys[:5]:  # Show first 5 for debugging
                    logging.warning(f"   - Key ID: {k.id}, Name: {k.name}, Hash: {k.key_hash[:16]}..., Active: {k.is_active}")
                    # Try to help user - show what the key should start with
                    if k.name:
                        logging.warning(f"     (This key was created with name: '{k.name}')")
            
            # Additional help: check if key format is wrong
            if not key.startswith("dp_"):
                logging.warning(f"   ⚠️  Key doesn't start with 'dp_' - database keys should start with 'dp_'")
                logging.warning(f"   Are you using the correct key? Database keys look like: dp_xxxxxxxxxxxx")
    
    # Fallback to legacy env var method (for backward compatibility)
    logging.info(f"Database lookup failed, checking env vars. Available keys: {list(API_KEY_TENANTS.keys())}")
    tenant_id = API_KEY_TENANTS.get(key)
    if not tenant_id:
        logging.warning(f"❌ API key not found in database or env vars: {key_preview}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    logging.info(f"✅ API key verified from env vars (tenant: {tenant_id})")
    return key, tenant_id
