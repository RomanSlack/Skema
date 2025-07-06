"""
User and session models
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import TIMESTAMP, text, ForeignKey


class User(SQLModel, table=True):
    """User model for authentication and profile management"""
    
    __tablename__ = "users"
    
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"server_default": text("uuid_generate_v4()")}
    )
    email: str = Field(max_length=255, unique=True, index=True)
    hashed_password: str = Field(max_length=255)
    full_name: Optional[str] = Field(max_length=255, default=None)
    avatar_url: Optional[str] = Field(max_length=255, default=None)
    preferences: Dict[str, Any] = Field(
        default_factory=lambda: {
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
        },
        sa_column=Column(JSON)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    )
    is_active: bool = Field(default=True)
    email_verified: bool = Field(default=False)
    last_login_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True))
    )


class UserSession(SQLModel, table=True):
    """User session model for JWT refresh token management"""
    
    __tablename__ = "user_sessions"
    
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"server_default": text("uuid_generate_v4()")}
    )
    user_id: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE")))
    refresh_token: str = Field(max_length=255, index=True)
    user_agent: Optional[str] = Field(default=None)
    ip_address: Optional[str] = Field(default=None)
    expires_at: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    )
    is_active: bool = Field(default=True)