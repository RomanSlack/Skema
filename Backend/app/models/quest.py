"""
Quest task models for daily productivity tracking
"""
from datetime import datetime, timezone, date
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import TIMESTAMP, text, ForeignKey, Date


class Quest(SQLModel, table=True):
    """Quest task model for daily rolling to-do system"""
    
    __tablename__ = "quests"
    
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"server_default": text("uuid_generate_v4()")}
    )
    user_id: UUID = Field(foreign_key="users.id", index=True)
    content: str = Field(max_length=1000)
    is_complete: bool = Field(default=False)
    date_created: date = Field(sa_column=Column(Date, index=True))
    date_due: Optional[date] = Field(default=None, sa_column=Column(Date))
    time_due: Optional[str] = Field(default=None, max_length=8)
    order_index: int = Field(default=0)
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
    
    def mark_complete(self) -> None:
        """Mark quest as complete"""
        self.is_complete = True
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_incomplete(self) -> None:
        """Mark quest as incomplete"""
        self.is_complete = False
        self.completed_at = None
        self.updated_at = datetime.now(timezone.utc)