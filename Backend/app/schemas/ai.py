"""
AI command schemas
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
from uuid import UUID


class AICommandCreate(BaseModel):
    """Schema for AI command creation"""
    
    command: str = Field(description="AI command text")
    context_type: Optional[str] = Field(default=None, description="Context type")
    context_id: Optional[UUID] = Field(default=None, description="Context ID")
    
    @validator('command')
    def validate_command(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Command must be at least 3 characters long')
        if len(v) > 1000:
            raise ValueError('Command must be less than 1000 characters')
        return v.strip()
    
    @validator('context_type')
    def validate_context_type(cls, v):
        allowed_types = ['board', 'card', 'calendar', 'journal', 'general']
        if v and v not in allowed_types:
            raise ValueError(f'Context type must be one of {allowed_types}')
        return v


class AICommandResponse(BaseModel):
    """Schema for AI command response"""
    
    id: UUID = Field(description="Command ID")
    user_id: UUID = Field(description="User ID")
    command: str = Field(description="AI command text")
    response: Optional[str] = Field(description="AI response")
    context_type: Optional[str] = Field(description="Context type")
    context_id: Optional[UUID] = Field(description="Context ID")
    execution_time_ms: Optional[int] = Field(description="Execution time in milliseconds")
    success: bool = Field(description="Command success status")
    error_message: Optional[str] = Field(description="Error message if failed")
    metadata: Dict[str, Any] = Field(description="Command metadata")
    created_at: datetime = Field(description="Command creation timestamp")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AISuggestionResponse(BaseModel):
    """Schema for AI suggestion response"""
    
    suggestions: List[str] = Field(description="List of AI suggestions")
    context_type: Optional[str] = Field(description="Context type")
    context_id: Optional[UUID] = Field(description="Context ID")
    
    class Config:
        from_attributes = True


class AICommandFilter(BaseModel):
    """Schema for AI command filtering"""
    
    context_type: Optional[str] = Field(default=None, description="Filter by context type")
    context_id: Optional[UUID] = Field(default=None, description="Filter by context ID")
    success: Optional[bool] = Field(default=None, description="Filter by success status")
    start_date: Optional[datetime] = Field(default=None, description="Filter start date")
    end_date: Optional[datetime] = Field(default=None, description="Filter end date")
    
    @validator('context_type')
    def validate_context_type(cls, v):
        allowed_types = ['board', 'card', 'calendar', 'journal', 'general']
        if v and v not in allowed_types:
            raise ValueError(f'Context type must be one of {allowed_types}')
        return v


class AICommandStats(BaseModel):
    """Schema for AI command statistics"""
    
    total_commands: int = Field(description="Total number of commands")
    successful_commands: int = Field(description="Number of successful commands")
    failed_commands: int = Field(description="Number of failed commands")
    success_rate: float = Field(description="Success rate percentage")
    average_execution_time: float = Field(description="Average execution time in ms")
    most_common_context: Optional[str] = Field(description="Most common context type")
    commands_today: int = Field(description="Commands executed today")
    commands_this_week: int = Field(description="Commands executed this week")
    
    class Config:
        from_attributes = True