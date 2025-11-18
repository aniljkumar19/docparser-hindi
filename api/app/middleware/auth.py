"""Authentication and rate limiting middleware for API keys"""
import hashlib
import time
from typing import Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy.orm import Session
from ..db import SessionLocal, ApiKey
from collections import defaultdict
from datetime import datetime, timedelta, timezone

# In-memory rate limit tracking (for production, use Redis)
_rate_limit_cache: dict[str, list[float]] = defaultdict(list)

def hash_api_key(key: str) -> str:
    """Hash an API key using SHA256"""
    return hashlib.sha256(key.encode()).hexdigest()

def get_api_key_from_request(request: Request) -> Optional[str]:
    """Extract API key from request headers"""
    # Check x-api-key header first
    api_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    if api_key:
        return api_key.strip()
    
    # Check Authorization Bearer header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    
    return None

def verify_api_key_from_db(api_key: str) -> Optional[ApiKey]:
    """Verify API key against database"""
    key_hash = hash_api_key(api_key)
    with SessionLocal() as db:
        api_key_obj = db.query(ApiKey).filter(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active == "active"
        ).first()
        return api_key_obj

def check_rate_limit(api_key_obj: ApiKey) -> bool:
    """Check if API key has exceeded rate limits"""
    key_id = api_key_obj.id
    now = time.time()
    
    # Clean old entries (older than 1 hour)
    cutoff = now - 3600
    _rate_limit_cache[key_id] = [t for t in _rate_limit_cache[key_id] if t > cutoff]
    
    # Check per-minute limit
    minute_ago = now - 60
    recent_minute = [t for t in _rate_limit_cache[key_id] if t > minute_ago]
    if len(recent_minute) >= api_key_obj.rate_limit_per_minute:
        return False
    
    # Check per-hour limit
    hour_ago = now - 3600
    recent_hour = [t for t in _rate_limit_cache[key_id] if t > hour_ago]
    if len(recent_hour) >= api_key_obj.rate_limit_per_hour:
        return False
    
    # Record this request
    _rate_limit_cache[key_id].append(now)
    return True

def update_api_key_last_used(api_key_obj: ApiKey):
    """Update last_used_at timestamp for API key"""
    with SessionLocal() as db:
        db_key = db.query(ApiKey).filter(ApiKey.id == api_key_obj.id).first()
        if db_key:
            db_key.last_used_at = datetime.now(timezone.utc)
            db.commit()

class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to authenticate API keys and enforce rate limits"""
    
    # Paths that don't require authentication
    PUBLIC_PATHS = [
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/dashboard",
        "/_next",
    ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for public paths
        path = request.url.path
        if any(path.startswith(public) for public in self.PUBLIC_PATHS):
            return await call_next(request)
        
        # Skip auth for non-API paths (static files, etc.)
        if not path.startswith("/v1/"):
            return await call_next(request)
        
        # Extract API key
        api_key = get_api_key_from_request(request)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key. Provide 'x-api-key' header or 'Authorization: Bearer <token>'"
            )
        
        # Verify API key
        api_key_obj = verify_api_key_from_db(api_key)
        if not api_key_obj:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API key"
            )
        
        # Check rate limits
        if not check_rate_limit(api_key_obj):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Update last used timestamp (async, don't block)
        update_api_key_last_used(api_key_obj)
        
        # Attach API key info to request state for use in endpoints
        request.state.api_key = api_key
        request.state.api_key_obj = api_key_obj
        request.state.tenant_id = api_key_obj.tenant_id
        
        response = await call_next(request)
        return response

