"""Admin-only endpoints for API key management"""
import os
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from ..db import SessionLocal, ApiKey
from ..security import hash_api_key
import secrets

router = APIRouter(prefix="/admin/api-keys", tags=["admin-api-keys"])

def get_admin_token() -> str | None:
    """Get ADMIN_TOKEN from environment (reloads on each call)"""
    return os.getenv("ADMIN_TOKEN")

def require_admin_token(x_admin_token: str | None = Header(None, alias="x-admin-token")):
    """Dependency to require admin token for admin endpoints"""
    admin_token = get_admin_token()
    
    if not admin_token:
        import logging
        logging.error("ADMIN_TOKEN not found in environment variables")
        logging.error(f"Available env vars with 'ADMIN': {[k for k in os.environ.keys() if 'ADMIN' in k.upper()]}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ADMIN_TOKEN not configured. Please set ADMIN_TOKEN environment variable in Railway and restart the service.",
        )
    
    if not x_admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing admin token. Provide X-Admin-Token header.",
        )
    
    if x_admin_token != admin_token:
        import logging
        logging.warning(f"Admin token mismatch. Expected length: {len(admin_token)}, Received length: {len(x_admin_token) if x_admin_token else 0}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_api_key() -> str:
    """Generate a secure API key"""
    # Format: dp_<32 random hex chars>
    random_part = secrets.token_hex(16)
    return f"dp_{random_part}"

class CreateApiKeyResponse(BaseModel):
    id: str
    name: str
    api_key: str  # Only shown once!
    active: bool
    created_at: str

@router.post("", summary="Create a new API key (admin only)", response_model=CreateApiKeyResponse)
def create_new_api_key(
    name: str,  # Query param or form field
    tenant_id: Optional[str] = None,  # Optional tenant assignment
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_token),
):
    """
    Admin-only endpoint to create API keys.
    
    Usage:
        curl -X POST "https://your-api.com/admin/api-keys?name=CA+Firm+A" \
          -H "X-Admin-Token: YOUR_ADMIN_TOKEN"
    
    The api_key in the response is the ONLY time it will be shown.
    Save it immediately!
    """
    import logging
    try:
        # Generate API key
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        
        # Check for hash collision (very unlikely)
        existing = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
        if existing:
            raise HTTPException(status_code=500, detail="Key collision (retry)")
        
        # Create database record
        api_key = ApiKey(
            key_hash=key_hash,
            tenant_id=tenant_id or "default",
            name=name,
            is_active="active",
            rate_limit_per_minute=60,
            rate_limit_per_hour=1000,
            created_by="admin"
        )
        db.add(api_key)
        
        # Log database info before commit
        from ..db import DB_URL, TABLE_SCHEMA
        db_preview = DB_URL[:50] + "..." if len(DB_URL) > 50 else DB_URL
        logging.info(f"Saving API key to database: {db_preview}")
        logging.info(f"Using schema: {TABLE_SCHEMA if TABLE_SCHEMA else 'None (no schema)'}")
        
        # Commit and verify it was saved
        try:
            db.commit()
            db.refresh(api_key)
            
            # Verify the key was actually saved (use a fresh query to ensure we're reading from DB)
            # Close current session and create new one to avoid cache issues
            db.close()
            with SessionLocal() as verify_db:
                verify_key = verify_db.query(ApiKey).filter(ApiKey.id == api_key.id).first()
                if not verify_key:
                    logging.error(f"❌ CRITICAL: API key {api_key.id} was not saved to database after commit!")
                    logging.error(f"   Database: {db_preview}")
                    logging.error(f"   Schema: {TABLE_SCHEMA if TABLE_SCHEMA else 'None'}")
                    raise HTTPException(status_code=500, detail="Failed to save API key to database")
                
                logging.info(f"✅ Verified API key {api_key.id} was saved to database")
                logging.info(f"   Key name: {api_key.name}, Tenant: {api_key.tenant_id}")
                logging.info(f"   Schema: {TABLE_SCHEMA if TABLE_SCHEMA else 'None'}")
            
            # Re-open session for response formatting
            db = SessionLocal()
            api_key = db.query(ApiKey).filter(ApiKey.id == api_key.id).first()
        except Exception as commit_error:
            db.rollback()
            logging.error(f"❌ Failed to commit API key: {commit_error}")
            import traceback
            logging.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Database error: {str(commit_error)}")
        
        # Format created_at safely
        created_at_str = ""
        if api_key.created_at:
            try:
                if hasattr(api_key.created_at, 'isoformat'):
                    created_at_str = api_key.created_at.isoformat()
                else:
                    created_at_str = str(api_key.created_at)
            except Exception as e:
                logging.warning(f"Error formatting created_at: {e}")
                created_at_str = ""
        
        response = CreateApiKeyResponse(
            id=api_key.id,
            name=api_key.name or name,
            api_key=raw_key,  # Only time this is returned!
            active=api_key.is_active == "active",
            created_at=created_at_str,
        )
        
        logging.info(f"Created API key: {api_key.id} for tenant: {api_key.tenant_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error creating API key: {e}\n{traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create API key: {str(e)}"
        )

@router.get("", summary="List all API keys (admin only)")
def list_all_api_keys(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_token),
):
    """List all API keys (admin only). Keys are NOT shown for security."""
    import logging
    from ..db import DB_URL, TABLE_SCHEMA
    
    # Log database connection info
    db_preview = DB_URL[:50] + "..." if len(DB_URL) > 50 else DB_URL
    logging.info(f"Admin listing API keys from database: {db_preview}")
    logging.info(f"Using schema: {TABLE_SCHEMA if TABLE_SCHEMA else 'None (no schema)'}")
    
    # Get all keys (including inactive)
    all_keys = db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()
    active_keys = db.query(ApiKey).filter(ApiKey.is_active == "active").all()
    
    logging.info(f"Admin listing API keys: {len(all_keys)} total, {len(active_keys)} active")
    
    # Debug: Log what we found
    if all_keys:
        logging.info(f"Found {len(all_keys)} keys: {[k.id for k in all_keys]}")
    else:
        logging.warning("⚠️  Query returned 0 keys, but debug endpoint shows keys exist!")
        # Try a raw query to see if keys exist
        try:
            from sqlalchemy import text
            # Try with schema prefix if using PostgreSQL
            if TABLE_SCHEMA:
                table_name = f"{TABLE_SCHEMA}.api_keys"
            else:
                table_name = "api_keys"
            
            raw_count = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            logging.warning(f"Raw SQL COUNT query shows {raw_count} keys in {table_name} table")
            if raw_count > 0:
                # Try querying with schema
                raw_keys = db.execute(text(f"SELECT id, name FROM {table_name} LIMIT 5")).fetchall()
                logging.warning(f"Raw SQL query found keys: {raw_keys}")
                # If raw query finds keys but ORM doesn't, there's a schema mismatch
                logging.error("❌ SCHEMA MISMATCH: Raw SQL found keys but ORM query returned 0!")
                logging.error(f"   Table name: {table_name}")
                logging.error(f"   TABLE_SCHEMA: {TABLE_SCHEMA}")
                logging.error(f"   ApiKey model schema: {ApiKey.__table_args__}")
        except Exception as e:
            logging.error(f"Error with raw query: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    # If no keys, check if table exists
    if len(all_keys) == 0:
        logging.warning("⚠️  No API keys found in database at all!")
        # Check if we can query the table at all (to verify it exists)
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.bind)
            tables = inspector.get_table_names(schema=TABLE_SCHEMA if TABLE_SCHEMA else None)
            logging.warning(f"Available tables in schema: {tables}")
            if "api_keys" not in tables:
                logging.error("❌ api_keys table does NOT exist in database!")
            else:
                logging.warning("⚠️  api_keys table exists but is empty")
        except Exception as e:
            logging.error(f"Could not inspect database: {e}")
        # Return empty array
        return []
    
    result = [
        {
            "id": k.id,
            "name": k.name,
            "tenant_id": k.tenant_id,
            "active": k.is_active == "active",
            "rate_limit_per_minute": k.rate_limit_per_minute,
            "rate_limit_per_hour": k.rate_limit_per_hour,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            # Note: api_key is NOT included for security
        }
        for k in all_keys
    ]
    
    logging.info(f"Returning {len(result)} keys to admin")
    return result

@router.post("/{key_id}/revoke", summary="Revoke an API key (admin only)")
def revoke_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_token),
):
    """Revoke an API key (admin only)"""
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_key.is_active = "revoked"
    db.commit()
    
    return {"ok": True, "message": "API key revoked"}

@router.post("/{key_id}/activate", summary="Activate a revoked API key (admin only)")
def activate_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_token),
):
    """Activate a revoked API key (admin only)"""
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_key.is_active = "active"
    db.commit()
    
    return {"ok": True, "message": "API key activated"}

