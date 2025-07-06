"""
Audit log models
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import TIMESTAMP, text


class AuditLog(SQLModel, table=True):
    """Audit log model for security and compliance tracking"""
    
    __tablename__ = "audit_logs"
    
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"server_default": text("uuid_generate_v4()")}
    )
    user_id: Optional[UUID] = Field(foreign_key="users.id", ondelete="SET NULL", default=None)
    action: str = Field(max_length=100)
    resource_type: str = Field(max_length=50)
    resource_id: Optional[UUID] = Field(default=None)
    old_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    new_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    ip_address: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    )