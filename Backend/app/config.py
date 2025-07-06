"""
Configuration management for the Skema API
"""
import os
from typing import List, Optional, Any
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    app_name: str = Field(default="Skema API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_description: str = Field(default="Production-ready FastAPI backend for Skema productivity app", env="APP_DESCRIPTION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database
    database_url: str = Field(env="DATABASE_URL")
    database_test_url: Optional[str] = Field(default=None, env="DATABASE_TEST_URL")
    
    # JWT Configuration
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=30, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # CORS
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"], 
        env="ALLOWED_ORIGINS"
    )
    allowed_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        env="ALLOWED_METHODS"
    )
    allowed_headers: List[str] = Field(default=["*"], env="ALLOWED_HEADERS")
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_burst: int = Field(default=10, env="RATE_LIMIT_BURST")
    
    # Email (optional)
    smtp_host: Optional[str] = Field(default=None, env="SMTP_HOST")
    smtp_port: Optional[int] = Field(default=587, env="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, env="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    from_email: Optional[str] = Field(default=None, env="FROM_EMAIL")
    
    # AI Configuration (optional)
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ai_model: str = Field(default="gpt-4-turbo-preview", env="AI_MODEL")
    ai_max_tokens: int = Field(default=4000, env="AI_MAX_TOKENS")
    
    # Security
    bcrypt_rounds: int = Field(default=12, env="BCRYPT_ROUNDS")
    session_cookie_secure: bool = Field(default=False, env="SESSION_COOKIE_SECURE")
    session_cookie_httponly: bool = Field(default=True, env="SESSION_COOKIE_HTTPONLY")
    session_cookie_samesite: str = Field(default="lax", env="SESSION_COOKIE_SAMESITE")
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    
    @validator('allowed_origins', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @validator('allowed_methods', pre=True)
    def parse_cors_methods(cls, v):
        if isinstance(v, str):
            return [method.strip() for method in v.split(',')]
        return v
    
    @validator('allowed_headers', pre=True)
    def parse_cors_headers(cls, v):
        if isinstance(v, str):
            return [header.strip() for header in v.split(',')]
        return v
    
    @validator('jwt_secret_key')
    def validate_jwt_secret_key(cls, v):
        if not v or len(v) < 32:
            raise ValueError('JWT secret key must be at least 32 characters long')
        return v
    
    @validator('database_url')
    def validate_database_url(cls, v):
        if not v:
            raise ValueError('Database URL is required')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()