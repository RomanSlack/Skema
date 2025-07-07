"""
AI command models
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import TIMESTAMP, text, ForeignKey


class AICommand(SQLModel, table=True):
    """AI command model for AI command bar functionality"""
    
    __tablename__ = "ai_commands"
    
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"server_default": text("uuid_generate_v4()")}
    )
    user_id: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), index=True))
    command: str = Field()
    response: Optional[str] = Field(default=None)
    context_type: Optional[str] = Field(max_length=50, default=None)
    context_id: Optional[UUID] = Field(default=None)
    execution_time_ms: Optional[int] = Field(default=None)
    success: bool = Field(default=True)
    error_message: Optional[str] = Field(default=None)
    meta_data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "model": "gpt-4",
            "tokens_used": 0,
            "intent": None,
            "confidence": 0.0,
            "source": "command_bar"
        },
        sa_column=Column(JSON),
        alias="metadata"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    )