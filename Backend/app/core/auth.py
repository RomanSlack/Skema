"""
Authentication and authorization utilities
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Dict, Any
from uuid import UUID

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.database import get_session
from app.models.user import User, UserSession

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token scheme
security = HTTPBearer()


class AuthenticationError(HTTPException):
    """Custom authentication error"""
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Custom authorization error"""
    
    def __init__(self, detail: str = "Authorization failed"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: The plain text password
        hashed_password: The hashed password
        
    Returns:
        bool: True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.
    
    Args:
        password: The plain text password
        
    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: The data to encode in the token
        expires_delta: Token expiration time delta
        
    Returns:
        str: The encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: The data to encode in the token
        expires_delta: Token expiration time delta
        
    Returns:
        str: The encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    
    # Add some randomness to refresh tokens
    to_encode.update({"jti": secrets.token_urlsafe(16)})
    
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: The JWT token to verify
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        Dict[str, Any]: The decoded token data
        
    Raises:
        AuthenticationError: If token is invalid
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        
        if payload.get("type") != token_type:
            raise AuthenticationError("Invalid token type")
        
        return payload
    except JWTError:
        raise AuthenticationError("Invalid token")


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    """
    Get a user by email address.
    
    Args:
        session: Database session
        email: User email address
        
    Returns:
        Optional[User]: User object if found, None otherwise
    """
    statement = select(User).where(User.email == email)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> Optional[User]:
    """
    Get a user by ID.
    
    Args:
        session: Database session
        user_id: User ID
        
    Returns:
        Optional[User]: User object if found, None otherwise
    """
    statement = select(User).where(User.id == user_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def authenticate_user(session: AsyncSession, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user with email and password.
    
    Args:
        session: Database session
        email: User email address
        password: User password
        
    Returns:
        Optional[User]: User object if authenticated, None otherwise
    """
    user = await get_user_by_email(session, email)
    
    if not user:
        return None
    
    if not user.is_active:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        session: Database session
        
    Returns:
        User: The authenticated user
        
    Raises:
        AuthenticationError: If authentication fails
    """
    try:
        payload = verify_token(credentials.credentials, "access")
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise AuthenticationError("Invalid token")
        
        user = await get_user_by_id(session, UUID(user_id))
        
        if user is None:
            raise AuthenticationError("User not found")
        
        if not user.is_active:
            raise AuthenticationError("User account is disabled")
        
        return user
    
    except ValueError:
        raise AuthenticationError("Invalid token")


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current active user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: The active user
        
    Raises:
        AuthenticationError: If user is not active
    """
    if not current_user.is_active:
        raise AuthenticationError("User account is disabled")
    
    return current_user


async def save_refresh_token(
    session: AsyncSession,
    user_id: UUID,
    refresh_token: str,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None
) -> UserSession:
    """
    Save a refresh token to the database.
    
    Args:
        session: Database session
        user_id: User ID
        refresh_token: Refresh token
        user_agent: User agent string
        ip_address: IP address
        
    Returns:
        UserSession: The created session
    """
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    
    user_session = UserSession(
        user_id=user_id,
        refresh_token=refresh_token,
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=expires_at
    )
    
    session.add(user_session)
    await session.commit()
    await session.refresh(user_session)
    
    return user_session


async def get_user_session(session: AsyncSession, refresh_token: str) -> Optional[UserSession]:
    """
    Get a user session by refresh token.
    
    Args:
        session: Database session
        refresh_token: Refresh token
        
    Returns:
        Optional[UserSession]: User session if found, None otherwise
    """
    statement = select(UserSession).where(
        UserSession.refresh_token == refresh_token,
        UserSession.is_active == True,
        UserSession.expires_at > datetime.now(timezone.utc)
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def invalidate_refresh_token(session: AsyncSession, refresh_token: str) -> bool:
    """
    Invalidate a refresh token.
    
    Args:
        session: Database session
        refresh_token: Refresh token to invalidate
        
    Returns:
        bool: True if token was invalidated, False otherwise
    """
    user_session = await get_user_session(session, refresh_token)
    
    if user_session:
        user_session.is_active = False
        await session.commit()
        return True
    
    return False


async def invalidate_all_user_sessions(session: AsyncSession, user_id: UUID) -> None:
    """
    Invalidate all user sessions for a user.
    
    Args:
        session: Database session
        user_id: User ID
    """
    statement = select(UserSession).where(
        UserSession.user_id == user_id,
        UserSession.is_active == True
    )
    result = await session.execute(statement)
    
    for user_session in result.scalars().all():
        user_session.is_active = False
    
    await session.commit()


async def clear_user_account_data(session: AsyncSession, user_id: UUID) -> Dict[str, int]:
    """
    Clear all user account data while preserving the user account itself.
    
    This function deletes:
    - All boards and their cards
    - All calendar events  
    - All journal entries
    - All AI command history
    - All user sessions (logout all devices)
    
    Args:
        session: Database session
        user_id: User ID whose data should be cleared
        
    Returns:
        Dict[str, int]: Count of deleted items per category
    """
    from app.models.board import Board, Card
    from app.models.calendar import CalendarEvent  
    from app.models.journal import JournalEntry
    from app.models.ai import AICommand
    
    counts = {
        "boards": 0,
        "cards": 0, 
        "calendar_events": 0,
        "journal_entries": 0,
        "ai_commands": 0,
        "user_sessions": 0
    }
    
    try:
        # Delete all user sessions (logout from all devices)
        sessions_stmt = select(UserSession).where(UserSession.user_id == user_id)
        sessions_result = await session.execute(sessions_stmt)
        user_sessions = sessions_result.scalars().all()
        counts["user_sessions"] = len(user_sessions)
        
        for user_session in user_sessions:
            await session.delete(user_session)
        
        # Delete all AI commands
        ai_stmt = select(AICommand).where(AICommand.user_id == user_id)
        ai_result = await session.execute(ai_stmt)
        ai_commands = ai_result.scalars().all()
        counts["ai_commands"] = len(ai_commands)
        
        for ai_command in ai_commands:
            await session.delete(ai_command)
        
        # Delete all journal entries
        journal_stmt = select(JournalEntry).where(JournalEntry.user_id == user_id)
        journal_result = await session.execute(journal_stmt)
        journal_entries = journal_result.scalars().all()
        counts["journal_entries"] = len(journal_entries)
        
        for journal_entry in journal_entries:
            await session.delete(journal_entry)
        
        # Delete all calendar events
        calendar_stmt = select(CalendarEvent).where(CalendarEvent.user_id == user_id)
        calendar_result = await session.execute(calendar_stmt)
        calendar_events = calendar_result.scalars().all()
        counts["calendar_events"] = len(calendar_events)
        
        for calendar_event in calendar_events:
            await session.delete(calendar_event)
        
        # Delete all cards first (foreign key constraint)
        cards_stmt = select(Card).join(Board).where(Board.user_id == user_id)
        cards_result = await session.execute(cards_stmt)
        cards = cards_result.scalars().all()
        counts["cards"] = len(cards)
        
        for card in cards:
            await session.delete(card)
        
        # Delete all boards
        boards_stmt = select(Board).where(Board.user_id == user_id)
        boards_result = await session.execute(boards_stmt)
        boards = boards_result.scalars().all()
        counts["boards"] = len(boards)
        
        for board in boards:
            await session.delete(board)
        
        # Reset user preferences to default
        user = await get_user_by_id(session, user_id)
        if user:
            user.preferences = {
                "theme": "light",
                "notifications": {
                    "email": True,
                    "push": True,
                    "board_updates": True,
                    "calendar_reminders": True
                },
                "dashboard": {
                    "layout": "default",
                    "widgets": ["boards", "calendar", "journal", "recent_activity"]
                }
            }
            user.updated_at = datetime.now(timezone.utc)
            session.add(user)
        
        await session.commit()
        
        return counts
        
    except Exception as e:
        await session.rollback()
        raise e