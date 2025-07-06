"""
Board and card schemas
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
from uuid import UUID


class BoardCreate(BaseModel):
    """Schema for board creation"""
    
    title: str = Field(max_length=255, description="Board title")
    description: Optional[str] = Field(default=None, description="Board description")
    color: Optional[str] = Field(default="#6366f1", description="Board color")
    settings: Optional[Dict[str, Any]] = Field(default=None, description="Board settings")
    
    @validator('color')
    def validate_color(cls, v):
        if v and not v.startswith('#'):
            raise ValueError('Color must be a valid hex color code')
        if v and len(v) != 7:
            raise ValueError('Color must be a 7-character hex code')
        return v


class BoardUpdate(BaseModel):
    """Schema for board update"""
    
    title: Optional[str] = Field(default=None, max_length=255, description="Board title")
    description: Optional[str] = Field(default=None, description="Board description")
    color: Optional[str] = Field(default=None, description="Board color")
    settings: Optional[Dict[str, Any]] = Field(default=None, description="Board settings")
    is_archived: Optional[bool] = Field(default=None, description="Board archived status")
    
    @validator('color')
    def validate_color(cls, v):
        if v and not v.startswith('#'):
            raise ValueError('Color must be a valid hex color code')
        if v and len(v) != 7:
            raise ValueError('Color must be a 7-character hex code')
        return v


class BoardResponse(BaseModel):
    """Schema for board response"""
    
    id: UUID = Field(description="Board ID")
    user_id: UUID = Field(description="User ID")
    title: str = Field(description="Board title")
    description: Optional[str] = Field(description="Board description")
    color: str = Field(description="Board color")
    settings: Dict[str, Any] = Field(description="Board settings")
    created_at: datetime = Field(description="Board creation timestamp")
    updated_at: datetime = Field(description="Board last update timestamp")
    is_archived: bool = Field(description="Board archived status")
    is_starred: bool = Field(description="Board starred status")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CardCreate(BaseModel):
    """Schema for card creation"""
    
    title: str = Field(max_length=255, description="Card title")
    description: Optional[str] = Field(default=None, description="Card description")
    status: Optional[str] = Field(default="todo", description="Card status")
    priority: Optional[str] = Field(default="medium", description="Card priority")
    card_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Card metadata", alias="metadata")
    position: Optional[int] = Field(default=0, description="Card position")
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['todo', 'in_progress', 'done', 'blocked']
        if v and v not in allowed_statuses:
            raise ValueError(f'Status must be one of {allowed_statuses}')
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        allowed_priorities = ['low', 'medium', 'high', 'urgent']
        if v and v not in allowed_priorities:
            raise ValueError(f'Priority must be one of {allowed_priorities}')
        return v


class CardUpdate(BaseModel):
    """Schema for card update"""
    
    title: Optional[str] = Field(default=None, max_length=255, description="Card title")
    description: Optional[str] = Field(default=None, description="Card description")
    status: Optional[str] = Field(default=None, description="Card status")
    priority: Optional[str] = Field(default=None, description="Card priority")
    card_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Card metadata", alias="metadata")
    position: Optional[int] = Field(default=None, description="Card position")
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['todo', 'in_progress', 'done', 'blocked']
        if v and v not in allowed_statuses:
            raise ValueError(f'Status must be one of {allowed_statuses}')
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        allowed_priorities = ['low', 'medium', 'high', 'urgent']
        if v and v not in allowed_priorities:
            raise ValueError(f'Priority must be one of {allowed_priorities}')
        return v


class CardMove(BaseModel):
    """Schema for card move operation"""
    
    board_id: UUID = Field(description="Target board ID")
    status: str = Field(description="New card status")
    position: int = Field(description="New card position")
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['todo', 'in_progress', 'done', 'blocked']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of {allowed_statuses}')
        return v


class CardResponse(BaseModel):
    """Schema for card response"""
    
    id: UUID = Field(description="Card ID")
    board_id: UUID = Field(description="Board ID")
    title: str = Field(description="Card title")
    description: Optional[str] = Field(description="Card description")
    status: str = Field(description="Card status")
    priority: str = Field(description="Card priority")
    metadata: Dict[str, Any] = Field(description="Card metadata")
    position: int = Field(description="Card position")
    created_at: datetime = Field(description="Card creation timestamp")
    updated_at: datetime = Field(description="Card last update timestamp")
    completed_at: Optional[datetime] = Field(description="Card completion timestamp")
    
    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        
    @classmethod
    def from_orm(cls, obj):
        # Map the SQLAlchemy field to the response field
        data = {
            'id': obj.id,
            'board_id': obj.board_id,
            'title': obj.title,
            'description': obj.description,
            'status': obj.status,
            'priority': obj.priority,
            'metadata': obj.card_metadata,  # Map card_metadata to metadata
            'position': obj.position,
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
            'completed_at': obj.completed_at
        }
        return cls(**data)


class BoardWithCards(BaseModel):
    """Schema for board with cards"""
    
    id: UUID = Field(description="Board ID")
    user_id: UUID = Field(description="User ID")
    title: str = Field(description="Board title")
    description: Optional[str] = Field(description="Board description")
    color: str = Field(description="Board color")
    settings: Dict[str, Any] = Field(description="Board settings")
    created_at: datetime = Field(description="Board creation timestamp")
    updated_at: datetime = Field(description="Board last update timestamp")
    is_archived: bool = Field(description="Board archived status")
    is_starred: bool = Field(description="Board starred status")
    cards: List[CardResponse] = Field(description="Board cards")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }