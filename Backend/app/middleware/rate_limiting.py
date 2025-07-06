"""
Rate limiting middleware
"""
import logging
import time
from typing import Callable, Dict, Optional
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter using sliding window
    """
    
    def __init__(self):
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """
        Check if request is allowed within rate limit
        
        Args:
            key: Unique identifier (e.g., IP address)
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            bool: True if allowed, False if rate limited
        """
        now = time.time()
        
        # Initialize key if not exists
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests outside the window
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if now - req_time < window
        ]
        
        # Check if limit exceeded
        if len(self.requests[key]) >= limit:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True
    
    def get_remaining(self, key: str, limit: int, window: int) -> int:
        """
        Get remaining requests in current window
        
        Args:
            key: Unique identifier
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            int: Remaining requests
        """
        now = time.time()
        
        if key not in self.requests:
            return limit
        
        # Remove old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if now - req_time < window
        ]
        
        return max(0, limit - len(self.requests[key]))
    
    def get_reset_time(self, key: str, window: int) -> Optional[float]:
        """
        Get time until rate limit resets
        
        Args:
            key: Unique identifier
            window: Time window in seconds
            
        Returns:
            Optional[float]: Time until reset, None if no requests
        """
        if key not in self.requests or not self.requests[key]:
            return None
        
        oldest_request = min(self.requests[key])
        return oldest_request + window


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_requests: int = 10,
        burst_window: int = 60
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_requests = burst_requests
        self.burst_window = burst_window
        self.limiter = InMemoryRateLimiter()
    
    def get_client_id(self, request: Request) -> str:
        """
        Get unique client identifier for rate limiting
        
        Args:
            request: HTTP request
            
        Returns:
            str: Client identifier
        """
        # Try to get real IP from headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Include user agent for additional uniqueness
        user_agent = request.headers.get("User-Agent", "")
        
        return f"{client_ip}:{hash(user_agent) % 10000}"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_id = self.get_client_id(request)
        
        # Check burst limit (short window)
        if not self.limiter.is_allowed(
            f"burst:{client_id}",
            self.burst_requests,
            self.burst_window
        ):
            remaining = self.limiter.get_remaining(
                f"burst:{client_id}",
                self.burst_requests,
                self.burst_window
            )
            reset_time = self.limiter.get_reset_time(
                f"burst:{client_id}",
                self.burst_window
            )
            
            logger.warning(f"Burst rate limit exceeded for {client_id}")
            
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests in short period"
                }
            )
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(self.burst_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            if reset_time:
                response.headers["X-RateLimit-Reset"] = str(int(reset_time))
            response.headers["Retry-After"] = str(self.burst_window)
            
            return response
        
        # Check per-minute limit
        if not self.limiter.is_allowed(
            f"minute:{client_id}",
            self.requests_per_minute,
            60
        ):
            remaining = self.limiter.get_remaining(
                f"minute:{client_id}",
                self.requests_per_minute,
                60
            )
            reset_time = self.limiter.get_reset_time(
                f"minute:{client_id}",
                60
            )
            
            logger.warning(f"Per-minute rate limit exceeded for {client_id}")
            
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests per minute"
                }
            )
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            if reset_time:
                response.headers["X-RateLimit-Reset"] = str(int(reset_time))
            response.headers["Retry-After"] = "60"
            
            return response
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to successful responses
        remaining = self.limiter.get_remaining(
            f"minute:{client_id}",
            self.requests_per_minute,
            60
        )
        
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response


class APIKeyRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for API key based access
    """
    
    def __init__(
        self,
        app,
        api_key_limits: Dict[str, int] = None,
        default_limit: int = 1000
    ):
        super().__init__(app)
        self.api_key_limits = api_key_limits or {}
        self.default_limit = default_limit
        self.limiter = InMemoryRateLimiter()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check for API key
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            return await call_next(request)
        
        # Get limit for this API key
        limit = self.api_key_limits.get(api_key, self.default_limit)
        
        # Check rate limit
        if not self.limiter.is_allowed(f"api_key:{api_key}", limit, 3600):  # 1 hour window
            remaining = self.limiter.get_remaining(f"api_key:{api_key}", limit, 3600)
            reset_time = self.limiter.get_reset_time(f"api_key:{api_key}", 3600)
            
            logger.warning(f"API key rate limit exceeded: {api_key}")
            
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "API key rate limit exceeded",
                    "message": f"Maximum {limit} requests per hour"
                }
            )
            
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            if reset_time:
                response.headers["X-RateLimit-Reset"] = str(int(reset_time))
            response.headers["Retry-After"] = "3600"
            
            return response
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.limiter.get_remaining(f"api_key:{api_key}", limit, 3600)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response


def add_rate_limiting_middleware(app: FastAPI) -> None:
    """
    Add rate limiting middleware to the FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    # Only add rate limiting if enabled
    if settings.enable_rate_limiting:
        # Add general rate limiting
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=settings.rate_limit_requests_per_minute,
            burst_requests=settings.rate_limit_burst,
            burst_window=60
        )
        
        # Add API key based rate limiting (if configured)
        api_key_limits = getattr(settings, 'api_key_limits', {})
        if api_key_limits:
            app.add_middleware(
                APIKeyRateLimitMiddleware,
                api_key_limits=api_key_limits,
                default_limit=1000
            )