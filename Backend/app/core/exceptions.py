"""
Custom exceptions and error handling
"""
import logging
from typing import Any, Dict, Optional, Union
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError

from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


class BaseAPIException(HTTPException):
    """Base exception for API-specific errors"""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code
        self.details = details or {}


class ValidationException(BaseAPIException):
    """Raised when request validation fails"""
    
    def __init__(self, detail: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            code="VALIDATION_ERROR",
            details=details
        )


class AuthenticationException(BaseAPIException):
    """Raised when authentication fails"""
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            code="AUTHENTICATION_ERROR"
        )


class AuthorizationException(BaseAPIException):
    """Raised when authorization fails"""
    
    def __init__(self, detail: str = "Authorization failed"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            code="AUTHORIZATION_ERROR"
        )


class ResourceNotFoundException(BaseAPIException):
    """Raised when a resource is not found"""
    
    def __init__(self, resource: str, identifier: Union[str, int]):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found",
            code="RESOURCE_NOT_FOUND",
            details={"resource": resource, "identifier": str(identifier)}
        )


class DuplicateResourceException(BaseAPIException):
    """Raised when trying to create a duplicate resource"""
    
    def __init__(self, resource: str, field: str, value: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{resource} with {field} '{value}' already exists",
            code="DUPLICATE_RESOURCE",
            details={"resource": resource, "field": field, "value": value}
        )


class BusinessLogicException(BaseAPIException):
    """Raised when business logic validation fails"""
    
    def __init__(self, detail: str, code: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            code=code,
            details=details
        )


class ExternalServiceException(BaseAPIException):
    """Raised when external service call fails"""
    
    def __init__(self, service: str, detail: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"External service error: {detail}",
            code="EXTERNAL_SERVICE_ERROR",
            details={"service": service}
        )


class RateLimitException(BaseAPIException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            code="RATE_LIMIT_EXCEEDED"
        )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors
    
    Args:
        request: HTTP request
        exc: Validation exception
        
    Returns:
        JSONResponse: Error response
    """
    errors = []
    
    for error in exc.errors():
        field = " -> ".join(str(x) for x in error["loc"])
        message = error["msg"]
        error_type = error["type"]
        
        errors.append({
            "field": field,
            "message": message,
            "type": error_type,
            "input": error.get("input")
        })
    
    logger.warning(f"Validation error for {request.method} {request.url}: {errors}")
    
    error_response = ErrorResponse(
        error="Validation failed",
        code="VALIDATION_ERROR",
        details={"errors": errors}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(error_response.dict())
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions
    
    Args:
        request: HTTP request
        exc: HTTP exception
        
    Returns:
        JSONResponse: Error response
    """
    if isinstance(exc, BaseAPIException):
        error_response = ErrorResponse(
            error=exc.detail,
            code=exc.code,
            details=exc.details
        )
    else:
        error_response = ErrorResponse(
            error=exc.detail,
            code="HTTP_ERROR"
        )
    
    logger.warning(f"HTTP error {exc.status_code} for {request.method} {request.url}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error_response.dict())
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handle database exceptions
    
    Args:
        request: HTTP request
        exc: Database exception
        
    Returns:
        JSONResponse: Error response
    """
    if isinstance(exc, IntegrityError):
        # Handle integrity constraint violations
        error_response = ErrorResponse(
            error="Data integrity violation",
            code="INTEGRITY_ERROR",
            details={"constraint": str(exc.orig)}
        )
        status_code = status.HTTP_409_CONFLICT
        logger.warning(f"Database integrity error for {request.method} {request.url}: {exc}")
    else:
        # Handle other database errors
        error_response = ErrorResponse(
            error="Database error occurred",
            code="DATABASE_ERROR"
        )
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        logger.error(f"Database error for {request.method} {request.url}: {exc}")
    
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(error_response.dict())
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions
    
    Args:
        request: HTTP request
        exc: Exception
        
    Returns:
        JSONResponse: Error response
    """
    logger.error(f"Unexpected error for {request.method} {request.url}: {exc}", exc_info=True)
    
    error_response = ErrorResponse(
        error="Internal server error",
        code="INTERNAL_ERROR"
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(error_response.dict())
    )


def add_exception_handlers(app) -> None:
    """
    Add exception handlers to the FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)