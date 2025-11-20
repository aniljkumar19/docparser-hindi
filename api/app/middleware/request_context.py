"""
Middleware to add request context (request_id, etc.) for structured logging.
"""

import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Add request context (request_id, etc.) to request state for logging."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        # Try to extract tenant_id from API key if available
        # (This will be set by auth middleware if present)
        tenant_id = getattr(request.state, "tenant_id", None)
        request.state.tenant_id = tenant_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers for tracing
        response.headers["X-Request-ID"] = request_id
        
        return response

