"""
Security middleware
"""
import logging
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # HSTS (only in production with HTTPS)
        if not settings.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """
    Limit request body size to prevent DoS attacks
    """
    
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check Content-Length header
        content_length = request.headers.get("content-length")
        
        if content_length:
            try:
                content_length = int(content_length)
                if content_length > self.max_size:
                    return JSONResponse(
                        status_code=413,
                        content={"error": "Request body too large"}
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid Content-Length header"}
                )
        
        return await call_next(request)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Whitelist specific IP addresses (optional, for admin endpoints)
    """
    
    def __init__(self, app, whitelist: list = None, paths: list = None):
        super().__init__(app)
        self.whitelist = whitelist or []
        self.paths = paths or []
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip if no whitelist or paths configured
        if not self.whitelist or not self.paths:
            return await call_next(request)
        
        # Check if request path matches protected paths
        if not any(request.url.path.startswith(path) for path in self.paths):
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else None
        forwarded_for = request.headers.get("X-Forwarded-For")
        
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        # Check whitelist
        if client_ip not in self.whitelist:
            logger.warning(f"IP {client_ip} not in whitelist for path {request.url.path}")
            return JSONResponse(
                status_code=403,
                content={"error": "Access denied"}
            )
        
        return await call_next(request)


def add_security_middleware(app: FastAPI) -> None:
    """
    Add security middleware to the FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    # Add security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Limit request size
    app.add_middleware(RequestSizeMiddleware, max_size=10 * 1024 * 1024)  # 10MB
    
    # IP whitelist for admin endpoints (if configured)
    admin_whitelist = getattr(settings, 'admin_ip_whitelist', [])
    admin_paths = getattr(settings, 'admin_paths', ['/admin'])
    
    if admin_whitelist:
        app.add_middleware(
            IPWhitelistMiddleware,
            whitelist=admin_whitelist,
            paths=admin_paths
        )