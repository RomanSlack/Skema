"""
Search schemas
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime, date
from uuid import UUID


class SearchQuery(BaseModel):
    """Schema for search query parameters"""
    
    q: str = Field(description="Search query")
    type: Optional[Literal['all', 'boards', 'cards', 'calendar', 'journal', 'quests']] = Field(
        default='all', 
        description="Type of content to search"
    )
    limit: Optional[int] = Field(default=50, ge=1, le=100, description="Maximum results")
    offset: Optional[int] = Field(default=0, ge=0, description="Results offset")


class SearchResult(BaseModel):
    """Schema for individual search result"""
    
    id: UUID = Field(description="Item ID")
    type: Literal['board', 'card', 'calendar_event', 'journal_entry', 'quest'] = Field(description="Result type")
    title: str = Field(description="Item title")
    description: Optional[str] = Field(description="Item description/content")
    url: str = Field(description="URL to navigate to this item")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    metadata: Dict[str, Any] = Field(description="Additional metadata")
    relevance_score: float = Field(description="Search relevance score")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


class SearchResponse(BaseModel):
    """Schema for search response"""
    
    query: str = Field(description="Original search query")
    results: List[SearchResult] = Field(description="Search results")
    total: int = Field(description="Total number of results")
    limit: int = Field(description="Results limit")
    offset: int = Field(description="Results offset")
    took_ms: int = Field(description="Query execution time in milliseconds")
    filters: Dict[str, Any] = Field(description="Applied filters")
    
    class Config:
        from_attributes = True


class SearchSuggestion(BaseModel):
    """Schema for search suggestions/autocomplete"""
    
    text: str = Field(description="Suggestion text")
    type: str = Field(description="Suggestion type")
    count: int = Field(description="Number of matching items")
    
    class Config:
        from_attributes = True


class SearchSuggestionsResponse(BaseModel):
    """Schema for search suggestions response"""
    
    query: str = Field(description="Original query")
    suggestions: List[SearchSuggestion] = Field(description="Search suggestions")
    
    class Config:
        from_attributes = True