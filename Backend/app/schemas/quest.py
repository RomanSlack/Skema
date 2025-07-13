"""
Quest schemas for request/response validation
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, date
from uuid import UUID


class QuestCreate(BaseModel):
    """Schema for creating a quest"""
    content: str = Field(min_length=1, max_length=1000, description="Quest task content")
    date_created: Optional[date] = Field(default=None, description="Date for the quest (defaults to today)")
    date_due: Optional[date] = Field(default=None, description="Due date for the quest")
    time_due: Optional[str] = Field(default=None, pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?$', description="Due time in HH:MM or HH:MM:SS format")
    order_index: Optional[int] = Field(default=0, description="Order index for sorting")


class QuestUpdate(BaseModel):
    """Schema for updating a quest"""
    content: Optional[str] = Field(default=None, min_length=1, max_length=1000, description="Quest task content")
    is_complete: Optional[bool] = Field(default=None, description="Quest completion status")
    date_due: Optional[date] = Field(default=None, description="Due date for the quest")
    time_due: Optional[str] = Field(default=None, pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?$', description="Due time in HH:MM or HH:MM:SS format")
    order_index: Optional[int] = Field(default=None, description="Order index for sorting")


class QuestReorder(BaseModel):
    """Schema for reordering quests"""
    quest_id: UUID = Field(description="Quest ID to reorder")
    new_order_index: int = Field(description="New order index")


class QuestBatchReorder(BaseModel):
    """Schema for batch reordering quests"""
    quest_orders: List[QuestReorder] = Field(description="List of quest reorder operations")


class QuestResponse(BaseModel):
    """Schema for quest response"""
    id: UUID = Field(description="Quest ID")
    user_id: UUID = Field(description="User ID")
    content: str = Field(description="Quest task content")
    is_complete: bool = Field(description="Quest completion status")
    date_created: date = Field(description="Date the quest was created for")
    date_due: Optional[date] = Field(description="Due date for the quest")
    time_due: Optional[str] = Field(description="Due time for the quest")
    order_index: int = Field(description="Order index for sorting")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    completed_at: Optional[datetime] = Field(description="Completion timestamp")
    
    model_config = {"from_attributes": True}


# Use simple dict types to avoid recursion
QuestDayResponse = Dict[str, Any]
QuestArchiveResponse = Dict[str, Any]


class QuestRolloverRequest(BaseModel):
    """Schema for rolling over incomplete quests"""
    from_date: date = Field(description="Date to roll over from")
    to_date: Optional[date] = Field(default=None, description="Date to roll over to (defaults to today)")


class QuestRolloverResponse(BaseModel):
    """Schema for rollover operation response"""
    success: bool = Field(description="Whether the rollover was successful")
    rolled_count: int = Field(description="Number of quests rolled over")
    from_date: date = Field(description="Date rolled over from")
    to_date: date = Field(description="Date rolled over to")
    timestamp: datetime = Field(description="When the rollover occurred")