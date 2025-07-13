"""
AI Tools for natural language processing and automation
"""
import json
import logging
import random
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Callable
from uuid import UUID
from pydantic import BaseModel, Field

from app.config import settings
from app.models.user import User
from app.models.board import Board, Card
from app.models.calendar import CalendarEvent
from app.models.journal import JournalEntry
from app.schemas.board import BoardCreate, CardCreate
from app.schemas.calendar import CalendarEventCreate
from app.schemas.journal import JournalEntryCreate

logger = logging.getLogger(__name__)


# Color palettes for random selection
CALENDAR_COLORS = [
    "#3b82f6",  # blue
    "#ef4444",  # red
    "#10b981",  # green
    "#f59e0b",  # yellow
    "#8b5cf6",  # purple
    "#06b6d4",  # cyan
    "#ec4899",  # pink
    "#84cc16",  # lime
    "#f97316",  # orange
    "#6366f1",  # indigo
]

BOARD_COLORS = [
    "#3b82f6",  # blue
    "#ef4444",  # red
    "#10b981",  # green
    "#f59e0b",  # yellow
    "#8b5cf6",  # purple
    "#06b6d4",  # cyan
    "#ec4899",  # pink
    "#84cc16",  # lime
    "#f97316",  # orange
    "#6366f1",  # indigo
    "#10b981",  # emerald
    "#14b8a6",  # teal
    "#8b5cf6",  # violet
    "#f43f5e",  # rose
    "#64748b",  # slate
]


def get_random_calendar_color() -> str:
    """Get a random color for calendar events"""
    return random.choice(CALENDAR_COLORS)


def get_random_board_color() -> str:
    """Get a random color for boards"""
    return random.choice(BOARD_COLORS)


class AITool(BaseModel):
    """Base class for AI tools"""
    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    parameters: Dict[str, Any] = Field(description="Tool parameters schema")
    
    async def execute(self, parameters: Dict[str, Any], user: User, session) -> Dict[str, Any]:
        """Execute the tool with given parameters"""
        raise NotImplementedError


class CreateJournalEntryTool(AITool):
    """Tool for creating journal entries"""
    
    name: str = "create_journal_entry"
    description: str = "Create a new journal entry with title, content, and mood"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The title of the journal entry"
            },
            "content": {
                "type": "string",
                "description": "The content/body of the journal entry"
            },
            "mood": {
                "type": "string",
                "enum": ["great", "good", "okay", "bad", "terrible"],
                "description": "The mood associated with this entry"
            },
            "entry_date": {
                "type": "string",
                "format": "date",
                "description": "The date for this entry (YYYY-MM-DD format), defaults to today"
            }
        },
        "required": ["title", "content"]
    }
    
    async def execute(self, parameters: Dict[str, Any], user: User, session) -> Dict[str, Any]:
        """Execute journal entry creation"""
        try:
            from app.models.journal import JournalEntry
            
            # Parse entry date
            entry_date = parameters.get("entry_date")
            if entry_date:
                entry_date = datetime.fromisoformat(entry_date).date()
            else:
                entry_date = datetime.now(timezone.utc).date()
            
            # Create journal entry directly
            journal_entry = JournalEntry(
                user_id=user.id,
                title=parameters["title"],
                content=parameters["content"],
                mood=parameters.get("mood", "okay"),
                entry_date=entry_date,
                tags=[],
                meta_data={},
                is_private=False,
                is_favorite=False
            )
            
            session.add(journal_entry)
            await session.commit()
            await session.refresh(journal_entry)
            
            return {
                "success": True,
                "result": {
                    "id": str(journal_entry.id),
                    "title": journal_entry.title,
                    "entry_date": journal_entry.entry_date.isoformat() if journal_entry.entry_date else None
                },
                "message": f"Created journal entry: {journal_entry.title}"
            }
            
        except Exception as e:
            logger.error(f"Error creating journal entry: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create journal entry"
            }


class CreateCalendarEventTool(AITool):
    """Tool for creating calendar events"""
    
    name: str = "create_calendar_event"
    description: str = "Create a new calendar event with title, description, and date/time"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The title of the event"
            },
            "description": {
                "type": "string",
                "description": "The description of the event"
            },
            "start_datetime": {
                "type": "string",
                "format": "date-time",
                "description": "Start date and time (ISO format)"
            },
            "end_datetime": {
                "type": "string",
                "format": "date-time",
                "description": "End date and time (ISO format)"
            },
            "is_all_day": {
                "type": "boolean",
                "description": "Whether this is an all-day event"
            },
            "location": {
                "type": "string",
                "description": "Event location"
            }
        },
        "required": ["title", "start_datetime"]
    }
    
    async def execute(self, parameters: Dict[str, Any], user: User, session) -> Dict[str, Any]:
        """Execute calendar event creation"""
        try:
            from app.models.calendar import CalendarEvent
            from app.schemas.calendar import CalendarEventResponse
            
            # Parse dates
            start_datetime = datetime.fromisoformat(parameters["start_datetime"].replace('Z', '+00:00'))
            end_datetime = None
            if parameters.get("end_datetime"):
                end_datetime = datetime.fromisoformat(parameters["end_datetime"].replace('Z', '+00:00'))
            else:
                # Default to 1 hour duration if not specified
                from datetime import timedelta
                end_datetime = start_datetime + timedelta(hours=1)
            
            # Create calendar event directly
            calendar_event = CalendarEvent(
                user_id=user.id,
                title=parameters["title"],
                description=parameters.get("description", ""),
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                location=parameters.get("location"),
                event_type="meeting",
                color=get_random_calendar_color(),
                meta_data={},
                is_all_day=parameters.get("is_all_day", False),
                is_recurring=False
            )
            
            session.add(calendar_event)
            await session.commit()
            await session.refresh(calendar_event)
            
            return {
                "success": True,
                "result": {
                    "id": str(calendar_event.id),
                    "title": calendar_event.title,
                    "start_datetime": calendar_event.start_datetime.isoformat(),
                    "end_datetime": calendar_event.end_datetime.isoformat() if calendar_event.end_datetime else None
                },
                "message": f"Created calendar event: {calendar_event.title} for {start_datetime.strftime('%B %d, %Y at %I:%M %p')}"
            }
            
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create calendar event"
            }


class CreateBoardTool(AITool):
    """Tool for creating boards"""
    
    name: str = "create_board"
    description: str = "Create a new Kanban board with title and description"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The title of the board"
            },
            "description": {
                "type": "string",
                "description": "The description of the board"
            }
        },
        "required": ["title"]
    }
    
    async def execute(self, parameters: Dict[str, Any], user: User, session) -> Dict[str, Any]:
        """Execute board creation"""
        try:
            from app.models.board import Board
            
            # Create board directly
            board = Board(
                user_id=user.id,
                title=parameters["title"],
                description=parameters.get("description", ""),
                color=get_random_board_color(),
                is_archived=False,
                settings={}
            )
            
            session.add(board)
            await session.commit()
            await session.refresh(board)
            
            return {
                "success": True,
                "result": {
                    "id": str(board.id),
                    "title": board.title,
                    "description": board.description
                },
                "message": f"Created board: {board.title}"
            }
            
        except Exception as e:
            logger.error(f"Error creating board: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create board"
            }


class CreateCardTool(AITool):
    """Tool for creating cards on boards"""
    
    name: str = "create_card"
    description: str = "Create a new card on a specific board"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "board_id": {
                "type": "string",
                "description": "The ID of the board to add the card to"
            },
            "title": {
                "type": "string",
                "description": "The title of the card"
            },
            "description": {
                "type": "string",
                "description": "The description of the card"
            },
            "column_id": {
                "type": "string",
                "description": "The ID of the column to add the card to"
            },
            "due_date": {
                "type": "string",
                "format": "date",
                "description": "Due date for the card (YYYY-MM-DD format)"
            }
        },
        "required": ["board_id", "title"]
    }
    
    async def execute(self, parameters: Dict[str, Any], user: User, session) -> Dict[str, Any]:
        """Execute card creation"""
        try:
            from app.models.board import Card
            
            # Parse due date if provided
            due_date = None
            if parameters.get("due_date"):
                due_date = datetime.fromisoformat(parameters["due_date"]).date()
            
            # Create card directly
            card = Card(
                title=parameters["title"],
                description=parameters.get("description", ""),
                position=0,
                status="todo",
                priority="medium",
                board_id=UUID(parameters["board_id"]),
                meta_data={"due_date": due_date.isoformat() if due_date else None}
            )
            
            session.add(card)
            await session.commit()
            await session.refresh(card)
            
            return {
                "success": True,
                "result": {
                    "id": str(card.id),
                    "title": card.title,
                    "board_id": str(card.board_id)
                },
                "message": f"Created card: {card.title}"
            }
            
        except Exception as e:
            logger.error(f"Error creating card: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create card"
            }


class GetBoardsTool(AITool):
    """Tool for getting user boards"""
    
    name: str = "get_boards"
    description: str = "Get list of user's boards"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Maximum number of boards to return",
                "default": 10
            }
        }
    }
    
    async def execute(self, parameters: Dict[str, Any], user: User, session) -> Dict[str, Any]:
        """Execute get boards"""
        try:
            from app.models.board import Board
            from sqlmodel import select
            
            limit = parameters.get("limit", 10)
            
            # Query boards directly
            query = select(Board).where(Board.user_id == user.id).limit(limit)
            result = await session.exec(query)
            boards = result.all()
            
            boards_list = []
            for board in boards:
                boards_list.append({
                    "id": str(board.id),
                    "title": board.title,
                    "description": board.description
                })
            
            return {
                "success": True,
                "result": {
                    "boards": boards_list,
                    "total": len(boards_list)
                },
                "message": f"Found {len(boards_list)} boards"
            }
            
        except Exception as e:
            logger.error(f"Error getting boards: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get boards"
            }


# Registry of available tools
AI_TOOLS_REGISTRY: Dict[str, AITool] = {
    "create_journal_entry": CreateJournalEntryTool(),
    "create_calendar_event": CreateCalendarEventTool(),
    "create_board": CreateBoardTool(),
    "create_card": CreateCardTool(),
    "get_boards": GetBoardsTool()
}


def get_tools_for_openai() -> List[Dict[str, Any]]:
    """Get tools formatted for OpenAI function calling"""
    tools = []
    for tool in AI_TOOLS_REGISTRY.values():
        tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
        })
    return tools


async def execute_ai_tool(tool_name: str, parameters: Dict[str, Any], user: User, session) -> Dict[str, Any]:
    """Execute an AI tool by name"""
    if tool_name not in AI_TOOLS_REGISTRY:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}",
            "message": f"Tool '{tool_name}' is not available"
        }
    
    tool = AI_TOOLS_REGISTRY[tool_name]
    return await tool.execute(parameters, user, session)