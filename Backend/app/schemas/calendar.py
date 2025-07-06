"""
Calendar event schemas
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from uuid import UUID


class CalendarEventCreate(BaseModel):
    """Schema for calendar event creation"""
    
    title: str = Field(max_length=255, description="Event title")
    description: Optional[str] = Field(default=None, description="Event description")
    start_datetime: datetime = Field(description="Event start datetime")
    end_datetime: datetime = Field(description="Event end datetime")
    location: Optional[str] = Field(default=None, max_length=255, description="Event location")
    event_type: Optional[str] = Field(default="personal", description="Event type")
    color: Optional[str] = Field(default="#3b82f6", description="Event color")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Event metadata")
    is_all_day: Optional[bool] = Field(default=False, description="All-day event flag")
    is_recurring: Optional[bool] = Field(default=False, description="Recurring event flag")
    
    @validator('end_datetime')
    def validate_end_datetime(cls, v, values):
        if 'start_datetime' in values and v <= values['start_datetime']:
            raise ValueError('End datetime must be after start datetime')
        return v
    
    @validator('color')
    def validate_color(cls, v):
        if v and not v.startswith('#'):
            raise ValueError('Color must be a valid hex color code')
        if v and len(v) != 7:
            raise ValueError('Color must be a 7-character hex code')
        return v
    
    @validator('event_type')
    def validate_event_type(cls, v):
        allowed_types = ['personal', 'work', 'meeting', 'appointment', 'reminder', 'other']
        if v and v not in allowed_types:
            raise ValueError(f'Event type must be one of {allowed_types}')
        return v


class CalendarEventUpdate(BaseModel):
    """Schema for calendar event update"""
    
    title: Optional[str] = Field(default=None, max_length=255, description="Event title")
    description: Optional[str] = Field(default=None, description="Event description")
    start_datetime: Optional[datetime] = Field(default=None, description="Event start datetime")
    end_datetime: Optional[datetime] = Field(default=None, description="Event end datetime")
    location: Optional[str] = Field(default=None, max_length=255, description="Event location")
    event_type: Optional[str] = Field(default=None, description="Event type")
    color: Optional[str] = Field(default=None, description="Event color")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Event metadata")
    is_all_day: Optional[bool] = Field(default=None, description="All-day event flag")
    is_recurring: Optional[bool] = Field(default=None, description="Recurring event flag")
    
    @validator('color')
    def validate_color(cls, v):
        if v and not v.startswith('#'):
            raise ValueError('Color must be a valid hex color code')
        if v and len(v) != 7:
            raise ValueError('Color must be a 7-character hex code')
        return v
    
    @validator('event_type')
    def validate_event_type(cls, v):
        allowed_types = ['personal', 'work', 'meeting', 'appointment', 'reminder', 'other']
        if v and v not in allowed_types:
            raise ValueError(f'Event type must be one of {allowed_types}')
        return v


class CalendarEventResponse(BaseModel):
    """Schema for calendar event response"""
    
    id: UUID = Field(description="Event ID")
    user_id: UUID = Field(description="User ID")
    title: str = Field(description="Event title")
    description: Optional[str] = Field(description="Event description")
    start_datetime: datetime = Field(description="Event start datetime")
    end_datetime: datetime = Field(description="Event end datetime")
    location: Optional[str] = Field(description="Event location")
    event_type: str = Field(description="Event type")
    color: str = Field(description="Event color")
    metadata: Dict[str, Any] = Field(description="Event metadata")
    created_at: datetime = Field(description="Event creation timestamp")
    updated_at: datetime = Field(description="Event last update timestamp")
    is_all_day: bool = Field(description="All-day event flag")
    is_recurring: bool = Field(description="Recurring event flag")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CalendarEventFilter(BaseModel):
    """Schema for calendar event filtering"""
    
    start_date: Optional[datetime] = Field(default=None, description="Filter start date")
    end_date: Optional[datetime] = Field(default=None, description="Filter end date")
    event_type: Optional[str] = Field(default=None, description="Filter by event type")
    
    @validator('event_type')
    def validate_event_type(cls, v):
        allowed_types = ['personal', 'work', 'meeting', 'appointment', 'reminder', 'other']
        if v and v not in allowed_types:
            raise ValueError(f'Event type must be one of {allowed_types}')
        return v