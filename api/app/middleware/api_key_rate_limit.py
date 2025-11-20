import os
import time
from collections import defaultdict, deque
from typing import Callable, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiKeyAndRateLimitMiddleware:
    """
    API-key auth + rate limiting middleware (ASGI-style).
    - Checks X-API-Key header or ?api_key= against DOCPARSER_API_KEY
    - Limits total requests/min per client key/IP
    - Limits upload requests/min separately (for /parse, /bulk-parse, /upload endpoints)
    - Uses Redis for distributed rate limiting if available, otherwise in-memory
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
        
        api_key_status = "yes" if self.api_key_required else "no"
        print(
            f"[RateLimitMiddleware] enabled=True, req_limit_per_min={self.req_limit_per_min}, "
            f"upload_limit_per_min={self.upload_limit_per_min}, api_key_required={api_key_status}"
        )
        import logging
        logging.info(f"✅ ApiKeyAndRateLimitMiddleware initialized successfully")
        logging.info(f"   api_key_required: {bool(self.api_key_required)} (length: {len(self.api_key_required) if self.api_key_required else 0})")
        logging.info(f"   use_redis: {self.use_redis}")

    async def __call__(self, scope, receive, send):
        """ASGI middleware entry point - handles request body cloning properly."""
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        # Clone request body (important for multipart/form-data uploads)
        # We need to read the body to check it, but also preserve it for FastAPI
        body_chunks = []
        more_body = True
        receive_ = receive

        async def inner_receive():
            nonlocal body_chunks, more_body, receive_
            message = await receive_()
            if message["type"] == "http.request":
                body_chunks.append(message.get("body", b""))
                more_body = message.get("more_body", False)
            return message
        
        # Actually read the body by creating a temporary Request (this will trigger inner_receive)
        # But we'll recreate it properly for FastAPI
        try:
            # Create Request to trigger body reading, but we'll recreate the stream
            temp_request = Request(scope, receive=inner_receive)
            # Force body read by accessing it (but we'll use body_chunks instead)
            await temp_request.body()  # This triggers inner_receive to read all chunks
        except Exception:
            # If body reading fails, continue anyway (might be GET request)
            pass
        
        # Combine all body chunks
        body = b"".join(body_chunks)

        path = scope["path"]
        path_lower = path.lower()

        # Skip auth/rate limiting for public paths
        PUBLIC_PATHS_EXACT = ["/", "/health", "/docs", "/openapi.json", "/redoc"]
        PUBLIC_PATHS_PREFIX = ["/dashboard", "/_next"]
        
        # Check exact matches
        if path in PUBLIC_PATHS_EXACT:
            return await self.app(scope, receive, send)
        
        # Check prefix matches
        if any(path.startswith(prefix) for prefix in PUBLIC_PATHS_PREFIX):
            return await self.app(scope, receive, send)

        # Read headers directly from scope (don't consume body yet)
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        
        # Extract API key from headers or query string
        presented_key = headers.get("x-api-key") or headers.get("x-api-key".lower())
        
        # Also check query string (need to parse it from scope)
        query_string = scope.get("query_string", b"").decode()
        if not presented_key and query_string:
            from urllib.parse import parse_qs
            query_params = parse_qs(query_string)
            if "api_key" in query_params:
                presented_key = query_params["api_key"][0]
        
        # Get client IP from scope
        client_info = scope.get("client")
        client_ip = client_info[0] if client_info else "unknown"
        bucket_key = f"{client_ip}:{presented_key or 'anonymous'}"

        # Debug logging
        import logging
        print(f"[RateLimitMiddleware] Intercepting: {path} (api_key_required={bool(self.api_key_required)})")
        logging.info(f"🔐 Middleware intercepting: {path} (api_key_required={bool(self.api_key_required)})")

        # API key check
        if self.api_key_required:
            if not presented_key:
                print(f"[RateLimitMiddleware] ❌ No API key provided for {path}")
                response = JSONResponse(
                    status_code=401,
                    content={
                        "error": "unauthorized",
                        "message": "Missing API key. Please provide 'x-api-key' header or '?api_key=' query parameter.",
                    },
                )
                return await response(scope, receive, send)
            
            if presented_key != self.api_key_required:
                print(f"[RateLimitMiddleware] ❌ API key mismatch for {path}")
                logging.warning(f"🔐 Middleware: API key mismatch!")
                response = JSONResponse(
                    status_code=401,
                    content={
                        "error": "unauthorized",
                        "message": "Invalid API key.",
                    },
                )
                return await response(scope, receive, send)

        # Determine if it's an upload (check content-type and path)
        content_type = headers.get("content-type", "").lower()
        method = scope.get("method", "").upper()
        is_upload = (
            method == "POST" and (
                "multipart/form-data" in content_type
                or "/v1/parse" in path_lower
                or "/v1/bulk-parse" in path_lower
                or "upload" in path_lower
            )
        )

        now = time.time()

        # Global rate limit
        if not self._check_rate_limit(bucket_key, "requests", self.req_limit_per_min, now):
            print(f"[RateLimitMiddleware] ❌ Rate limit exceeded (general) for {path}")
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limited",
                    "message": "Too many requests. Please try again later.",
                },
            )
            return await response(scope, receive, send)

        # Upload-specific limit
        if is_upload:
            if not self._check_rate_limit(bucket_key, "uploads", self.upload_limit_per_min, now):
                print(f"[RateLimitMiddleware] ❌ Rate limit exceeded (uploads) for {path}")
                response = JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limited_uploads",
                        "message": "Too many uploads. Please slow down.",
                    },
                )
                return await response(scope, receive, send)

        # Recreate receive stream for downstream FastAPI (preserve body)
        body_sent = False
        async def new_receive():
            nonlocal body, body_sent
            if not body_sent and body:
                body_sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        # Set authentication info in request.state (need to pass through scope)
        # Note: We can't modify scope directly, but FastAPI will handle request.state
        # We'll set it in a way that downstream can access
        
        # Pass to downstream FastAPI
        return await self.app(scope, new_receive, send)

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
