"""
Authentication endpoints
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.core.auth import (
    authenticate_user, create_access_token, create_refresh_token,
    get_current_user, get_password_hash, get_user_by_email,
    get_user_session, invalidate_all_user_sessions, invalidate_refresh_token,
    save_refresh_token, verify_token
)
from app.database import get_session
from app.models.user import User
from app.schemas.auth import (
    UserCreate, UserLogin, UserResponse, Token, RefreshToken,
    PasswordChange, UserUpdate
)
from app.schemas.common import BaseResponse, ErrorResponse

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """
    Register a new user.
    
    Args:
        user_data: User registration data
        request: HTTP request object
        session: Database session
        
    Returns:
        UserResponse: Created user data
        
    Raises:
        HTTPException: If email already exists
    """
    try:
        # Check if user already exists
        existing_user = await get_user_by_email(session, user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            avatar_url=user_data.avatar_url,
            is_active=True,
            email_verified=False
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        logger.info(f"User registered: {user.email}")
        return UserResponse.from_orm(user)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """
    Authenticate user and return access and refresh tokens.
    
    Args:
        user_data: User login credentials
        request: HTTP request object
        session: Database session
        
    Returns:
        Token: Access and refresh tokens
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Authenticate user
        user = await authenticate_user(session, user_data.email, user_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Create tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        # Save refresh token to database
        user_agent = request.headers.get("user-agent")
        client_ip = request.client.host if request.client else None
        
        await save_refresh_token(
            session, user.id, refresh_token, user_agent, client_ip
        )
        
        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await session.commit()
        
        logger.info(f"User logged in: {user.email}")
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: RefreshToken,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """
    Refresh access token using refresh token.
    
    Args:
        token_data: Refresh token data
        request: HTTP request object
        session: Database session
        
    Returns:
        Token: New access and refresh tokens
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        # Verify refresh token
        payload = verify_token(token_data.refresh_token, "refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if refresh token exists in database
        user_session = await get_user_session(session, token_data.refresh_token)
        if not user_session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user
        user = await session.get(User, UUID(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        # Invalidate old refresh token
        await invalidate_refresh_token(session, token_data.refresh_token)
        
        # Save new refresh token
        user_agent = request.headers.get("user-agent")
        client_ip = request.client.host if request.client else None
        
        await save_refresh_token(
            session, user.id, new_refresh_token, user_agent, client_ip
        )
        
        logger.info(f"Token refreshed for user: {user.email}")
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout", response_model=BaseResponse)
async def logout(
    token_data: RefreshToken,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Logout user by invalidating refresh token.
    
    Args:
        token_data: Refresh token data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        BaseResponse: Success response
    """
    try:
        # Invalidate refresh token
        await invalidate_refresh_token(session, token_data.refresh_token)
        
        logger.info(f"User logged out: {current_user.email}")
        
        return BaseResponse(message="Logged out successfully")
    
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/logout-all", response_model=BaseResponse)
async def logout_all(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Logout user from all devices by invalidating all refresh tokens.
    
    Args:
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        BaseResponse: Success response
    """
    try:
        # Invalidate all user sessions
        await invalidate_all_user_sessions(session, current_user.id)
        
        logger.info(f"User logged out from all devices: {current_user.email}")
        
        return BaseResponse(message="Logged out from all devices successfully")
    
    except Exception as e:
        logger.error(f"Logout all error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout all failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserResponse: Current user data
    """
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update current user information.
    
    Args:
        user_update: User update data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        UserResponse: Updated user data
    """
    try:
        # Update user fields
        if user_update.full_name is not None:
            current_user.full_name = user_update.full_name
        if user_update.avatar_url is not None:
            current_user.avatar_url = user_update.avatar_url
        if user_update.preferences is not None:
            current_user.preferences = user_update.preferences
        
        await session.commit()
        await session.refresh(current_user)
        
        logger.info(f"User updated: {current_user.email}")
        
        return UserResponse.from_orm(current_user)
    
    except Exception as e:
        logger.error(f"User update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User update failed"
        )


@router.post("/change-password", response_model=BaseResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Change user password.
    
    Args:
        password_data: Password change data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        BaseResponse: Success response
    """
    try:
        from app.core.auth import verify_password
        
        # Verify current password
        if not verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        current_user.hashed_password = get_password_hash(password_data.new_password)
        await session.commit()
        
        # Invalidate all user sessions (force re-login)
        await invalidate_all_user_sessions(session, current_user.id)
        
        logger.info(f"Password changed for user: {current_user.email}")
        
        return BaseResponse(message="Password changed successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )