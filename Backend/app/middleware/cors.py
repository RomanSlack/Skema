"""
CORS middleware configuration
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


def add_cors_middleware(app: FastAPI) -> None:
    """
    Add CORS middleware to the FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=settings.allowed_methods,
        allow_headers=settings.allowed_headers,
        expose_headers=["X-Total-Count", "X-Page-Count"],
        max_age=600,  # Cache preflight response for 10 minutes
    )