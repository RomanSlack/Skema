"""
Logging middleware
"""
import json
import logging
import time
from typing import Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all requests and responses
    """
    
    def __init__(self, app, log_body: bool = False):
        super().__init__(app)
        self.log_body = log_body
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid4())
        
        # Log request start
        start_time = time.time()
        
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        user_agent = request.headers.get("User-Agent", "")
        
        # Log request
        request_log = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "client_ip": client_ip,
            "user_agent": user_agent,
            "headers": dict(request.headers),
        }
        
        # Log request body if enabled (be careful with sensitive data)
        if self.log_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # Try to parse as JSON for better logging
                    try:
                        request_log["body"] = json.loads(body.decode())
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        request_log["body"] = body.decode("utf-8", errors="ignore")[:1000]
                
                # Re-create request with body for downstream processing
                from starlette.requests import Request as StarletteRequest
                
                async def receive():
                    return {"type": "http.request", "body": body}
                
                request = StarletteRequest(request.scope, receive)
            except Exception as e:
                logger.error(f"Error reading request body: {e}")
        
        logger.info(f"Request started: {json.dumps(request_log, default=str)}")
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            response_log = {
                "request_id": request_id,
                "status_code": response.status_code,
                "process_time": round(process_time, 4),
                "response_headers": dict(response.headers),
            }
            
            # Add process time header
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            
            if response.status_code >= 400:
                logger.warning(f"Request failed: {json.dumps(response_log, default=str)}")
            else:
                logger.info(f"Request completed: {json.dumps(response_log, default=str)}")
            
            return response
        
        except Exception as e:
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log exception
            error_log = {
                "request_id": request_id,
                "error": str(e),
                "process_time": round(process_time, 4),
            }
            
            logger.error(f"Request error: {json.dumps(error_log, default=str)}")
            raise


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log performance metrics
    """
    
    def __init__(self, app, slow_request_threshold: float = 1.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Log slow requests
        if process_time > self.slow_request_threshold:
            slow_log = {
                "method": request.method,
                "url": str(request.url),
                "process_time": round(process_time, 4),
                "status_code": response.status_code,
            }
            
            logger.warning(f"Slow request detected: {json.dumps(slow_log, default=str)}")
        
        return response


def add_logging_middleware(app) -> None:
    """
    Add logging middleware to the FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    # Add request logging (be careful with body logging in production)
    app.add_middleware(
        RequestLoggingMiddleware,
        log_body=False  # Set to True only in development
    )
    
    # Add performance logging
    app.add_middleware(
        PerformanceLoggingMiddleware,
        slow_request_threshold=1.0  # Log requests taking more than 1 second
    )