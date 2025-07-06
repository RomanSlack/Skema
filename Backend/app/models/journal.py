"""
Journal entry models
"""
from datetime import datetime, timezone, date
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import TIMESTAMP, text, ARRAY, String, ForeignKey


class JournalEntry(SQLModel, table=True):
    """Journal entry model for journaling functionality"""
    
    __tablename__ = "journal_entries"
    
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"server_default": text("uuid_generate_v4()")}
    )
    user_id: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), index=True))
    title: Optional[str] = Field(max_length=255, default=None)
    content: str = Field()
    mood: Optional[str] = Field(max_length=50, default=None)
    tags: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String))
    )
    meta_data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "weather": None,
            "location": None,
            "custom_fields": {},
            "attachments": [],
            "word_count": 0,
            "reading_time": 0
        },
        sa_column=Column(JSON)
    )
    entry_date: date = Field()
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    )
    is_private: bool = Field(default=True)
    is_favorite: bool = Field(default=False)