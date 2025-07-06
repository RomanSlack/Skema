"""
Board and card models for Kanban functionality
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import TIMESTAMP, text


class Board(SQLModel, table=True):
    """Board model for Kanban boards"""
    
    __tablename__ = "boards"
    
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"server_default": text("uuid_generate_v4()")}
    )
    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None)
    color: str = Field(max_length=7, default="#6366f1")
    settings: Dict[str, Any] = Field(
        default_factory=lambda: {
            "columns": [
                {"id": "todo", "title": "To Do", "color": "#ef4444"},
                {"id": "in_progress", "title": "In Progress", "color": "#f59e0b"},
                {"id": "done", "title": "Done", "color": "#10b981"}
            ],
            "automation": {
                "auto_archive": False,
                "move_completed_cards": False
            },
            "permissions": {
                "public": False,
                "collaborators": []
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
    is_archived: bool = Field(default=False, index=True)


class Card(SQLModel, table=True):
    """Card model for Kanban cards"""
    
    __tablename__ = "cards"
    
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"server_default": text("uuid_generate_v4()")}
    )
    board_id: UUID = Field(foreign_key="boards.id", ondelete="CASCADE", index=True)
    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None)
    status: str = Field(max_length=50, default="todo", index=True)
    priority: str = Field(max_length=20, default="medium", index=True)
    metadata: Dict[str, Any] = Field(
        default_factory=lambda: {
            "tags": [],
            "due_date": None,
            "checklist": [],
            "attachments": [],
            "assigned_to": None,
            "estimated_hours": None,
            "actual_hours": None
        },
        sa_column=Column(JSON)
    )
    position: int = Field(default=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True))
    )