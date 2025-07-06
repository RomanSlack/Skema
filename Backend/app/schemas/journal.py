"""
Journal entry schemas
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
from uuid import UUID


class JournalEntryCreate(BaseModel):
    """Schema for journal entry creation"""
    
    title: Optional[str] = Field(default=None, max_length=255, description="Entry title")
    content: str = Field(description="Entry content")
    mood: Optional[str] = Field(default=None, description="Entry mood")
    tags: Optional[List[str]] = Field(default=None, description="Entry tags")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Entry metadata")
    entry_date: Optional[date] = Field(default=None, description="Entry date")
    is_private: Optional[bool] = Field(default=True, description="Private entry flag")
    is_favorite: Optional[bool] = Field(default=False, description="Favorite entry flag")
    
    @validator('mood')
    def validate_mood(cls, v):
        allowed_moods = [
            'happy', 'sad', 'excited', 'calm', 'anxious', 'angry', 
            'grateful', 'hopeful', 'frustrated', 'content', 'stressed', 'other'
        ]
        if v and v not in allowed_moods:
            raise ValueError(f'Mood must be one of {allowed_moods}')
        return v
    
    @validator('tags')
    def validate_tags(cls, v):
        if v:
            # Remove duplicates and ensure all tags are strings
            unique_tags = list(set(str(tag).strip() for tag in v if tag))
            if len(unique_tags) > 20:
                raise ValueError('Maximum 20 tags allowed')
            return unique_tags
        return v
    
    @validator('entry_date', pre=True)
    def validate_entry_date(cls, v):
        if v is None:
            return date.today()
        return v


class JournalEntryUpdate(BaseModel):
    """Schema for journal entry update"""
    
    title: Optional[str] = Field(default=None, max_length=255, description="Entry title")
    content: Optional[str] = Field(default=None, description="Entry content")
    mood: Optional[str] = Field(default=None, description="Entry mood")
    tags: Optional[List[str]] = Field(default=None, description="Entry tags")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Entry metadata")
    entry_date: Optional[date] = Field(default=None, description="Entry date")
    is_private: Optional[bool] = Field(default=None, description="Private entry flag")
    is_favorite: Optional[bool] = Field(default=None, description="Favorite entry flag")
    
    @validator('mood')
    def validate_mood(cls, v):
        allowed_moods = [
            'happy', 'sad', 'excited', 'calm', 'anxious', 'angry', 
            'grateful', 'hopeful', 'frustrated', 'content', 'stressed', 'other'
        ]
        if v and v not in allowed_moods:
            raise ValueError(f'Mood must be one of {allowed_moods}')
        return v
    
    @validator('tags')
    def validate_tags(cls, v):
        if v:
            # Remove duplicates and ensure all tags are strings
            unique_tags = list(set(str(tag).strip() for tag in v if tag))
            if len(unique_tags) > 20:
                raise ValueError('Maximum 20 tags allowed')
            return unique_tags
        return v


class JournalEntryResponse(BaseModel):
    """Schema for journal entry response"""
    
    id: UUID = Field(description="Entry ID")
    user_id: UUID = Field(description="User ID")
    title: Optional[str] = Field(description="Entry title")
    content: str = Field(description="Entry content")
    mood: Optional[str] = Field(description="Entry mood")
    tags: List[str] = Field(description="Entry tags")
    metadata: Dict[str, Any] = Field(description="Entry metadata")
    entry_date: date = Field(description="Entry date")
    created_at: datetime = Field(description="Entry creation timestamp")
    updated_at: datetime = Field(description="Entry last update timestamp")
    is_private: bool = Field(description="Private entry flag")
    is_favorite: bool = Field(description="Favorite entry flag")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


class JournalEntryFilter(BaseModel):
    """Schema for journal entry filtering"""
    
    start_date: Optional[date] = Field(default=None, description="Filter start date")
    end_date: Optional[date] = Field(default=None, description="Filter end date")
    mood: Optional[str] = Field(default=None, description="Filter by mood")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    is_favorite: Optional[bool] = Field(default=None, description="Filter by favorite status")
    search: Optional[str] = Field(default=None, description="Search in title and content")
    
    @validator('mood')
    def validate_mood(cls, v):
        allowed_moods = [
            'happy', 'sad', 'excited', 'calm', 'anxious', 'angry', 
            'grateful', 'hopeful', 'frustrated', 'content', 'stressed', 'other'
        ]
        if v and v not in allowed_moods:
            raise ValueError(f'Mood must be one of {allowed_moods}')
        return v


class JournalStats(BaseModel):
    """Schema for journal statistics"""
    
    total_entries: int = Field(description="Total number of entries")
    entries_this_month: int = Field(description="Entries this month")
    entries_this_week: int = Field(description="Entries this week")
    total_words: int = Field(description="Total word count")
    average_words_per_entry: float = Field(description="Average words per entry")
    most_common_mood: Optional[str] = Field(description="Most common mood")
    streak_days: int = Field(description="Current writing streak in days")
    favorite_count: int = Field(description="Number of favorite entries")
    tags_used: List[str] = Field(description="All tags used")
    
    class Config:
        from_attributes = True