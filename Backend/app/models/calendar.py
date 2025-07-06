"""
Calendar event models
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import TIMESTAMP, text


class CalendarEvent(SQLModel, table=True):
    """Calendar event model for scheduling functionality"""
    
    __tablename__ = "calendar_events"
    
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"server_default": text("uuid_generate_v4()")}
    )
    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None)
    start_datetime: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    end_datetime: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    location: Optional[str] = Field(max_length=255, default=None)
    event_type: str = Field(max_length=50, default="personal", index=True)
    color: str = Field(max_length=7, default="#3b82f6")
    metadata: Dict[str, Any] = Field(
        default_factory=lambda: {
            "recurrence": None,
            "attendees": [],
            "reminders": [
                {"type": "notification", "minutes": 15},
                {"type": "email", "minutes": 60}
            ],
            "meeting_link": None,
            "timezone": "UTC"
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
    is_all_day: bool = Field(default=False)
    is_recurring: bool = Field(default=False)