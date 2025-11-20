import os
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class ApiKeyAndRateLimitMiddleware(BaseHTTPMiddleware):
    """
    API-key auth + rate limiting middleware.
    - Checks X-API-Key header or ?api_key= against DOCPARSER_API_KEY
    - Limits total requests/min per client key/IP
    - Limits upload requests/min separately (for /parse, /bulk-parse, /upload endpoints)
    - Uses Redis for distributed rate limiting if available, otherwise in-memory
    """

    def __init__(self, app, redis_client=None):
        import logging
        logging.info("🔧 ApiKeyAndRateLimitMiddleware.__init__ called")
        try:
            super().__init__(app)
            self.api_key_required = os.getenv("DOCPARSER_API_KEY")
            self.req_limit_per_min = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))
            self.upload_limit_per_min = int(os.getenv("RATE_LIMIT_UPLOADS_PER_MINUTE", "5"))
            
            # Redis client for distributed rate limiting (optional)
            self.redis = redis_client
            self.use_redis = redis_client is not None
            
            # Fallback: in-memory rate limiting (for single-instance or when Redis unavailable)
            if not self.use_redis:
                self._request_buckets: dict[str, deque[float]] = defaultdict(deque)
                self._upload_buckets: dict[str, deque[float]] = defaultdict(deque)
            
            logging.info(f"✅ ApiKeyAndRateLimitMiddleware initialized successfully")
            logging.info(f"   api_key_required: {bool(self.api_key_required)} (length: {len(self.api_key_required) if self.api_key_required else 0})")
            logging.info(f"   use_redis: {self.use_redis}")
        except Exception as e:
            logging.error(f"❌ Failed to initialize ApiKeyAndRateLimitMiddleware: {e}", exc_info=True)
            raise

    async def dispatch(self, request: Request, call_next):
        import logging
        path = request.url.path
        
        # Log that middleware is running (even for public paths)
        logging.info(f"🔐 Middleware dispatch called: {path}")

        # Skip auth/rate limiting for public paths
        PUBLIC_PATHS = ["/", "/health", "/docs", "/openapi.json", "/redoc", "/dashboard", "/_next"]
        if any(path.startswith(public) for public in PUBLIC_PATHS):
            logging.debug(f"   → Public path, skipping auth/rate limit")
            return await call_next(request)

        # Debug logging
        logging.info(f"🔐 Middleware intercepting: {path} (api_key_required={bool(self.api_key_required)})")

        # 1) API key check
        client_key = self._get_client_key(request)
        presented_key = None
        if self.api_key_required:
            presented_key = (
                request.headers.get("x-api-key")
                or request.query_params.get("api_key")
            )
            if not presented_key:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "unauthorized",
                        "message": "Missing API key. Please provide 'x-api-key' header or '?api_key=' query parameter.",
                    },
                )
            if presented_key != self.api_key_required:
                # Log for debugging (but don't expose the actual key)
                import logging
                logging.warning(f"🔐 Middleware: API key mismatch!")
                logging.warning(f"   Provided key length: {len(presented_key) if presented_key else 0}")
                logging.warning(f"   Required key length: {len(self.api_key_required) if self.api_key_required else 0}")
                logging.warning(f"   Provided starts with: {presented_key[:10] if presented_key and len(presented_key) >= 10 else 'N/A'}")
                logging.warning(f"   Required starts with: {self.api_key_required[:10] if self.api_key_required and len(self.api_key_required) >= 10 else 'N/A'}")
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "unauthorized",
                        "message": "Invalid API key.",
                    },
                )

        # 2) Rate limiting
        now = time.time()
        id_for_limit = client_key

        # global request limit
        if not self._check_rate_limit(id_for_limit, "requests", self.req_limit_per_min, now):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limited",
                    "message": "Too many requests. Please try again later.",
                },
            )

        # upload-specific limit (check for POST to /v1/parse or /v1/bulk-parse or any path with 'upload')
        path_lower = path.lower()
        method = request.method.upper()
        is_upload = (
            method == "POST" and (
                "/parse" in path_lower or 
                "upload" in path_lower or
                "bulk" in path_lower
            )
        )
        if is_upload:
            if not self._check_rate_limit(id_for_limit, "uploads", self.upload_limit_per_min, now):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limited_uploads",
                        "message": "Too many uploads. Please slow down.",
                    },
                )

        # Set authentication info in request.state so endpoints can skip verify_api_key()
        request.state.middleware_authenticated = True
        request.state.api_key = presented_key if (self.api_key_required and presented_key) else (
            request.headers.get("x-api-key") or request.query_params.get("api_key") or None
        )
        request.state.tenant_id = None  # Middleware doesn't track tenant_id, use None
        
        # OK → pass through
        response = await call_next(request)
        return response

    def _get_client_key(self, request: Request) -> str:
        ip = request.client.host if request.client else "unknown"
        api_key = (
            request.headers.get("x-api-key")
            or request.query_params.get("api_key")
            or "anonymous"
        )
        return f"{ip}:{api_key}"

    def _check_rate_limit(
        self,
        key: str,
        limit_type: str,
        limit_per_minute: int,
        now: float,
    ) -> bool:
        """
        Check rate limit using Redis (if available) or in-memory fallback.
        
        Args:
            key: Client identifier (IP:API_KEY)
            limit_type: "requests" or "uploads"
            limit_per_minute: Maximum requests per minute
            now: Current timestamp
            
        Returns:
            True if under limit, False if limit exceeded
        """
        if self.use_redis:
            return self._check_rate_limit_redis(key, limit_type, limit_per_minute, now)
        else:
            return self._check_rate_limit_memory(key, limit_type, limit_per_minute, now)
    
    def _check_rate_limit_redis(
        self,
        key: str,
        limit_type: str,
        limit_per_minute: int,
        now: float,
    ) -> bool:
        """Check rate limit using Redis (distributed, works across instances)."""
        try:
            redis_key = f"rate_limit:{limit_type}:{key}"
            current = self.redis.get(redis_key)
            
            if current is None:
                # First request in this window
                self.redis.setex(redis_key, 60, 1)  # Expire in 60 seconds
                return True
            
            count = int(current)
            if count >= limit_per_minute:
                return False
            
            # Increment counter
            self.redis.incr(redis_key)
            return True
        except Exception as e:
            # If Redis fails, fall back to in-memory (log error but don't block)
            import logging
            logging.warning(f"Redis rate limit check failed, falling back to in-memory: {e}")
            return self._check_rate_limit_memory(key, limit_type, limit_per_minute, now)
    
    def _check_rate_limit_memory(
        self,
        key: str,
        limit_type: str,
        limit_per_minute: int,
        now: float,
    ) -> bool:
        """Check rate limit using in-memory storage (single instance only)."""
        window = 60.0
        
        # Select appropriate bucket
        if limit_type == "requests":
            buckets = self._request_buckets
        else:
            buckets = self._upload_buckets
        
        dq = buckets[key]
        
        # Drop entries older than 60s
        while dq and now - dq[0] > window:
            dq.popleft()
        
        current_count = len(dq)
        if current_count >= limit_per_minute:
            # Log for debugging
            import logging
            logging.debug(f"Rate limit exceeded: {limit_type} for {key[:20]}... (count: {current_count}, limit: {limit_per_minute})")
            return False
        
        dq.append(now)
        # Log for debugging (only first few to avoid spam)
        if current_count < 3:
            import logging
            logging.debug(f"Rate limit check: {limit_type} for {key[:20]}... (count: {current_count + 1}/{limit_per_minute})")
        return True

