"""
Main FastAPI application
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.auth import get_current_user, verify_token
from app.core.exceptions import add_exception_handlers
from app.core.logging import setup_logging
from app.database import init_db, close_db
from app.middleware.cors import add_cors_middleware
from app.middleware.security import add_security_middleware
from app.middleware.rate_limiting import add_rate_limiting_middleware
from app.middleware.logging import add_logging_middleware
from app.models.user import User
from app.schemas.common import HealthResponse
from app.websocket import manager, handle_websocket_message

# API routers
from app.api import auth, boards, calendar, journal, ai

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    """
    # Startup
    logger.info("Starting up Skema API...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        yield
    
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Skema API...")
        
        try:
            # Close database connections
            await close_db()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Shutdown error: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# Add middleware (order matters!)
add_logging_middleware(app)
add_security_middleware(app)
add_rate_limiting_middleware(app)
add_cors_middleware(app)

# Add exception handlers
add_exception_handlers(app)

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(boards.router, prefix="/api/boards", tags=["Boards"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])
app.include_router(journal.router, prefix="/api/journal", tags=["Journal"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    
    Returns:
        HealthResponse: Service health status
    """
    try:
        # Test database connection
        from app.database import engine
        
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        
        database_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        database_status = "unhealthy"
    
    # Test Redis connection (if configured)
    redis_status = None
    try:
        if hasattr(settings, 'redis_url') and settings.redis_url:
            # Simple Redis check would go here
            redis_status = "healthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "unhealthy"
    
    # Determine overall status
    overall_status = "healthy" if database_status == "healthy" else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        database=database_status,
        redis=redis_status
    )


@app.get("/")
async def root():
    """
    Root endpoint
    
    Returns:
        dict: Welcome message
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "Documentation disabled",
        "health": "/health"
    }


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = None
):
    """
    WebSocket endpoint for real-time updates
    
    Args:
        websocket: WebSocket connection
        token: JWT token for authentication
    """
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return
    
    try:
        # Verify JWT token
        payload = verify_token(token, "access")
        user_id = payload.get("sub")
        
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        from uuid import UUID
        user_id = UUID(user_id)
        
        # Accept connection
        await manager.connect(websocket, user_id)
        
        try:
            while True:
                # Receive message
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    await handle_websocket_message(websocket, user_id, message)
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Internal error"
                    }))
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user_id}")
        
        finally:
            manager.disconnect(websocket, user_id)
    
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        await websocket.close(code=4003, reason="Authentication failed")


@app.get("/api/stats")
async def get_api_stats(current_user: User = Depends(get_current_user)):
    """
    Get API statistics (protected endpoint)
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        dict: API statistics
    """
    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "websocket_connections": manager.get_user_connection_count(current_user.id),
        "environment": settings.environment,
        "version": settings.app_version
    }


# Add startup message
@app.on_event("startup")
async def startup_message():
    """Log startup message"""
    logger.info(f"{settings.app_name} v{settings.app_version} started successfully")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")


# Error handling for uncaught exceptions
@app.exception_handler(500)
async def internal_server_error(request, exc):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )