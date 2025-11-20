import os
import time
from collections import defaultdict, deque
from typing import Callable, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiKeyAndRateLimitMiddleware:
    """
    Simple API-key auth + in-memory rate limiting.
    - Checks X-API-Key header or ?api_key=
    - Limits total requests/min per client key/IP
    - Limits upload requests/min separately (path contains 'upload')
    """

    def __init__(self, app: Callable, redis_client=None):
        self.app = app
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

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        path = scope.get("path", "")

        # Skip auth/rate limiting for public paths
        PUBLIC_PATHS = ["/", "/health", "/docs", "/openapi.json", "/redoc", "/dashboard", "/_next"]
        if any(path.startswith(public) for public in PUBLIC_PATHS):
            await self.app(scope, receive, send)
            return

        # 1) API key check
        client_key = self._get_client_key(request)
        presented_key = None
        if self.api_key_required:
            presented_key = (
                request.headers.get("x-api-key")
                or request.query_params.get("api_key")
            )
            if not presented_key:
                resp = JSONResponse(
                    status_code=401,
                    content={
                        "error": "unauthorized",
                        "message": "Missing API key. Please provide 'x-api-key' header or '?api_key=' query parameter.",
                    },
                )
                await resp(scope, receive, send)
                return
            if presented_key != self.api_key_required:
                # Log for debugging (but don't expose the actual key)
                import logging
                logging.debug(f"API key mismatch: provided key length={len(presented_key)}, required key length={len(self.api_key_required) if self.api_key_required else 0}")
                resp = JSONResponse(
                    status_code=401,
                    content={
                        "error": "unauthorized",
                        "message": "Invalid API key.",
                    },
                )
                await resp(scope, receive, send)
                return

        # 2) Rate limiting
        now = time.time()
        id_for_limit = client_key

        # global request limit
        if not self._check_rate_limit(id_for_limit, "requests", self.req_limit_per_min, now):
            resp = JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limited",
                    "message": "Too many requests. Please try again later.",
                },
            )
            await resp(scope, receive, send)
            return

        # upload-specific limit (check for POST to /v1/parse or /v1/bulk-parse or any path with 'upload')
        path_lower = scope.get("path", "").lower()
        method = scope.get("method", "").upper()
        is_upload = (
            method == "POST" and (
                "/parse" in path_lower or 
                "upload" in path_lower or
                "bulk" in path_lower
            )
        )
        if is_upload:
            if not self._check_rate_limit(id_for_limit, "uploads", self.upload_limit_per_min, now):
                resp = JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limited_uploads",
                        "message": "Too many uploads. Please slow down.",
                    },
                )
                await resp(scope, receive, send)
                return

        # Set authentication info in request.state so endpoints can skip verify_api_key()
        # This allows middleware to handle auth when enabled
        # Note: We need to set this in scope['state'] for ASGI, but Request.state will access it
        if 'state' not in scope:
            scope['state'] = {}
        scope['state']['middleware_authenticated'] = True
        # Get the presented key (already validated above)
        final_key = presented_key if (self.api_key_required and presented_key) else (
            request.headers.get("x-api-key") or request.query_params.get("api_key") or None
        )
        scope['state']['api_key'] = final_key
        scope['state']['tenant_id'] = None  # Middleware doesn't track tenant_id, use None
        
        # OK → pass through
        await self.app(scope, receive, send)

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

