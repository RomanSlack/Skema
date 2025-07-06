"""
Pydantic schemas for request/response validation
"""
from .auth import (
    UserCreate, UserLogin, UserUpdate, UserResponse, 
    Token, TokenData, RefreshToken
)
from .board import (
    BoardCreate, BoardUpdate, BoardResponse,
    CardCreate, CardUpdate, CardResponse, CardMove
)
from .calendar import (
    CalendarEventCreate, CalendarEventUpdate, CalendarEventResponse
)
from .journal import (
    JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse
)
from .ai import (
    AICommandCreate, AICommandResponse, AISuggestionResponse
)
from .common import (
    BaseResponse, PaginatedResponse, ErrorResponse
)

__all__ = [
    # Auth schemas
    "UserCreate", "UserLogin", "UserUpdate", "UserResponse",
    "Token", "TokenData", "RefreshToken",
    
    # Board schemas
    "BoardCreate", "BoardUpdate", "BoardResponse",
    "CardCreate", "CardUpdate", "CardResponse", "CardMove",
    
    # Calendar schemas
    "CalendarEventCreate", "CalendarEventUpdate", "CalendarEventResponse",
    
    # Journal schemas
    "JournalEntryCreate", "JournalEntryUpdate", "JournalEntryResponse",
    
    # AI schemas
    "AICommandCreate", "AICommandResponse", "AISuggestionResponse",
    
    # Common schemas
    "BaseResponse", "PaginatedResponse", "ErrorResponse"
]