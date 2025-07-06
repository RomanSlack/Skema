"""
Authentication schemas
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, validator
from datetime import datetime
from uuid import UUID


class UserCreate(BaseModel):
    """Schema for user creation"""
    
    email: EmailStr = Field(description="User email address")
    password: str = Field(min_length=8, description="User password")
    username: str = Field(min_length=3, max_length=50, description="Username")
    first_name: str = Field(min_length=1, max_length=100, description="User first name")
    last_name: str = Field(min_length=1, max_length=100, description="User last name")
    avatar_url: Optional[str] = Field(default=None, description="User avatar URL")
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLogin(BaseModel):
    """Schema for user login"""
    
    email: EmailStr = Field(description="User email address")
    password: str = Field(description="User password")


class UserUpdate(BaseModel):
    """Schema for user update"""
    
    full_name: Optional[str] = Field(default=None, max_length=255, description="User full name")
    avatar_url: Optional[str] = Field(default=None, description="User avatar URL")
    preferences: Optional[Dict[str, Any]] = Field(default=None, description="User preferences")


class UserResponse(BaseModel):
    """Schema for user response"""
    
    id: UUID = Field(description="User ID")
    email: str = Field(description="User email address")
    full_name: Optional[str] = Field(description="User full name")
    avatar_url: Optional[str] = Field(description="User avatar URL")
    preferences: Dict[str, Any] = Field(description="User preferences")
    created_at: datetime = Field(description="User creation timestamp")
    updated_at: datetime = Field(description="User last update timestamp")
    is_active: bool = Field(description="User active status")
    email_verified: bool = Field(description="Email verification status")
    last_login_at: Optional[datetime] = Field(description="Last login timestamp")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Token(BaseModel):
    """Schema for authentication token"""
    
    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration time in seconds")


class TokenData(BaseModel):
    """Schema for token data"""
    
    user_id: Optional[UUID] = Field(default=None, description="User ID")
    email: Optional[str] = Field(default=None, description="User email")


class RefreshToken(BaseModel):
    """Schema for refresh token request"""
    
    refresh_token: str = Field(description="JWT refresh token")


class PasswordReset(BaseModel):
    """Schema for password reset request"""
    
    email: EmailStr = Field(description="User email address")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation"""
    
    token: str = Field(description="Password reset token")
    new_password: str = Field(min_length=8, description="New password")
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class PasswordChange(BaseModel):
    """Schema for password change"""
    
    current_password: str = Field(description="Current password")
    new_password: str = Field(min_length=8, description="New password")
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v