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
            logger.info(f"AI Calendar Tool - Raw start_datetime parameter: {parameters.get('start_datetime')}")
            start_datetime = datetime.fromisoformat(parameters["start_datetime"].replace('Z', '+00:00'))
            logger.info(f"AI Calendar Tool - Parsed start_datetime: {start_datetime}")
            
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


class EditCalendarEventTool(AITool):
    """Tool for editing existing calendar events"""
    
    name: str = "edit_calendar_event"
    description: str = "Edit an existing calendar event by changing title, time, description, or location"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "event_title": {
                "type": "string",
                "description": "Current title of the event to find and edit"
            },
            "new_title": {
                "type": "string",
                "description": "New title for the event"
            },
            "new_start_datetime": {
                "type": "string",
                "format": "date-time",
                "description": "New start date and time (ISO format)"
            },
            "new_end_datetime": {
                "type": "string",
                "format": "date-time",
                "description": "New end date and time (ISO format)"
            },
            "new_description": {
                "type": "string",
                "description": "New description for the event"
            },
            "new_location": {
                "type": "string",
                "description": "New location for the event"
            }
        },
        "required": ["event_title"]
    }
    
    async def execute(self, parameters: Dict[str, Any], user: User, session) -> Dict[str, Any]:
        """Execute calendar event editing"""
        try:
            from app.models.calendar import CalendarEvent
            from sqlmodel import select, and_
            
            event_title = parameters.get("event_title")
            
            # Find the event by title
            statement = select(CalendarEvent).where(
                and_(
                    CalendarEvent.user_id == user.id,
                    CalendarEvent.title.ilike(f"%{event_title}%")
                )
            ).order_by(CalendarEvent.start_datetime.desc())
            
            result = await session.execute(statement)
            events = result.scalars().all()
            
            if not events:
                return {
                    "success": False,
                    "error": f"No calendar event found matching '{event_title}'",
                    "message": f"Could not find event '{event_title}'"
                }
            
            # Use the first (most recent) match
            event = events[0]
            
            # Update fields if provided
            if parameters.get("new_title"):
                event.title = parameters["new_title"]
            
            if parameters.get("new_start_datetime"):
                event.start_datetime = datetime.fromisoformat(parameters["new_start_datetime"].replace('Z', '+00:00'))
            
            if parameters.get("new_end_datetime"):
                event.end_datetime = datetime.fromisoformat(parameters["new_end_datetime"].replace('Z', '+00:00'))
            elif parameters.get("new_start_datetime"):
                # If only start time changed, maintain 1-hour duration
                from datetime import timedelta
                event.end_datetime = event.start_datetime + timedelta(hours=1)
            
            if parameters.get("new_description") is not None:
                event.description = parameters["new_description"]
            
            if parameters.get("new_location") is not None:
                event.location = parameters["new_location"]
            
            await session.commit()
            await session.refresh(event)
            
            return {
                "success": True,
                "result": {
                    "id": str(event.id),
                    "title": event.title,
                    "start_datetime": event.start_datetime.isoformat(),
                    "end_datetime": event.end_datetime.isoformat() if event.end_datetime else None
                },
                "message": f"Updated calendar event: {event.title}"
            }
            
        except Exception as e:
            logger.error(f"Error editing calendar event: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to edit calendar event"
            }


class DeleteCalendarEventTool(AITool):
    """Tool for deleting calendar events"""
    
    name: str = "delete_calendar_event"
    description: str = "Delete a calendar event by title"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "event_title": {
                "type": "string",
                "description": "Title of the event to delete"
            }
        },
        "required": ["event_title"]
    }
    
    async def execute(self, parameters: Dict[str, Any], user: User, session) -> Dict[str, Any]:
        """Execute calendar event deletion"""
        try:
            from app.models.calendar import CalendarEvent
            from sqlmodel import select, and_
            
            event_title = parameters.get("event_title")
            
            # Find the event by title
            statement = select(CalendarEvent).where(
                and_(
                    CalendarEvent.user_id == user.id,
                    CalendarEvent.title.ilike(f"%{event_title}%")
                )
            ).order_by(CalendarEvent.start_datetime.desc())
            
            result = await session.execute(statement)
            events = result.scalars().all()
            
            if not events:
                return {
                    "success": False,
                    "error": f"No calendar event found matching '{event_title}'",
                    "message": f"Could not find event '{event_title}'"
                }
            
            # Delete the first (most recent) match
            event = events[0]
            event_title_deleted = event.title
            
            await session.delete(event)
            await session.commit()
            
            return {
                "success": True,
                "result": {
                    "deleted_event": event_title_deleted
                },
                "message": f"Deleted calendar event: {event_title_deleted}"
            }
            
        except Exception as e:
            logger.error(f"Error deleting calendar event: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to delete calendar event"
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


class CreateQuestTool(AITool):
    """Tool for creating quest tasks"""
    
    name: str = "create_quest"
    description: str = "Create a new quest (daily task) with content and optional due date/time"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The quest task content or description"
            },
            "date_created": {
                "type": "string",
                "format": "date",
                "description": "Date for the quest (YYYY-MM-DD format), defaults to today"
            },
            "date_due": {
                "type": "string",
                "format": "date", 
                "description": "Due date for the quest (YYYY-MM-DD format)"
            },
            "time_due": {
                "type": "string",
                "pattern": "^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
                "description": "Due time in HH:MM format"
            }
        },
        "required": ["content"]
    }
    
    async def execute(self, parameters: Dict[str, Any], user: User, session) -> Dict[str, Any]:
        try:
            from app.models.quest import Quest
            from datetime import date, datetime, timezone
            from sqlmodel import select, func, and_
            
            content = parameters.get("content")
            date_created = parameters.get("date_created")
            date_due = parameters.get("date_due")
            time_due = parameters.get("time_due")
            
            # Parse dates
            if date_created:
                quest_date = datetime.strptime(date_created, "%Y-%m-%d").date()
            else:
                quest_date = date.today()
                
            due_date = None
            if date_due:
                due_date = datetime.strptime(date_due, "%Y-%m-%d").date()
            
            # Get next order index
            max_order_stmt = select(func.coalesce(func.max(Quest.order_index), 0)).where(
                and_(Quest.user_id == user.id, Quest.date_created == quest_date)
            )
            result = await session.execute(max_order_stmt)
            max_order = result.scalar() or 0
            
            # Create quest
            quest = Quest(
                user_id=user.id,
                content=content,
                date_created=quest_date,
                date_due=due_date,
                time_due=time_due,
                order_index=max_order + 1
            )
            
            session.add(quest)
            await session.commit()
            await session.refresh(quest)
            
            logger.info(f"Quest created via AI: {quest.id} for user {user.id}")
            
            return {
                "success": True,
                "quest": {
                    "id": str(quest.id),
                    "content": quest.content,
                    "date_created": quest.date_created.isoformat(),
                    "date_due": quest.date_due.isoformat() if quest.date_due else None,
                    "time_due": quest.time_due,
                    "is_complete": quest.is_complete
                },
                "message": f"Quest created for {quest_date}: {content}"
            }
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating quest via AI: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create quest"
            }


class CompleteQuestTool(AITool):
    """Tool for completing/marking quest tasks as done"""
    
    name: str = "complete_quest"
    description: str = "Mark a quest task as complete or incomplete"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "quest_content": {
                "type": "string", 
                "description": "Content of the quest to mark as complete (partial match)"
            },
            "quest_date": {
                "type": "string",
                "format": "date",
                "description": "Date of the quest (YYYY-MM-DD format), defaults to today"
            },
            "is_complete": {
                "type": "boolean",
                "description": "Whether to mark as complete (true) or incomplete (false)"
            }
        },
        "required": ["quest_content"]
    }
    
    async def execute(self, parameters: Dict[str, Any], user: User, session) -> Dict[str, Any]:
        try:
            from app.models.quest import Quest
            from datetime import date, datetime, timezone
            from sqlmodel import select, and_
            
            quest_content = parameters.get("quest_content")
            quest_date_str = parameters.get("quest_date")
            is_complete = parameters.get("is_complete", True)
            
            # Parse date
            if quest_date_str:
                quest_date = datetime.strptime(quest_date_str, "%Y-%m-%d").date()
            else:
                quest_date = date.today()
            
            # Find quest by content (fuzzy match)
            statement = select(Quest).where(
                and_(
                    Quest.user_id == user.id,
                    Quest.date_created == quest_date,
                    Quest.content.ilike(f"%{quest_content}%")
                )
            ).order_by(Quest.order_index)
            
            result = await session.execute(statement)
            quests = result.scalars().all()
            
            if not quests:
                return {
                    "success": False,
                    "message": f"No quest found matching '{quest_content}' for {quest_date}"
                }
            
            # Use the first match
            quest = quests[0]
            
            if is_complete:
                quest.mark_complete()
            else:
                quest.mark_incomplete()
            
            await session.commit()
            
            status = "completed" if is_complete else "marked as incomplete"
            logger.info(f"Quest {status} via AI: {quest.id} for user {user.id}")
            
            return {
                "success": True,
                "quest": {
                    "id": str(quest.id),
                    "content": quest.content,
                    "is_complete": quest.is_complete,
                    "completed_at": quest.completed_at.isoformat() if quest.completed_at else None
                },
                "message": f"Quest '{quest.content}' {status}"
            }
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error completing quest via AI: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update quest"
            }


class GetQuestsTool(AITool):
    """Tool for getting quest tasks for a specific date"""
    
    name: str = "get_quests"
    description: str = "Get quest tasks for a specific date or today"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "quest_date": {
                "type": "string",
                "format": "date",
                "description": "Date to get quests for (YYYY-MM-DD format), defaults to today"
            },
            "include_completed": {
                "type": "boolean",
                "description": "Whether to include completed quests (default: true)"
            }
        },
        "required": []
    }
    
    async def execute(self, parameters: Dict[str, Any], user: User, session) -> Dict[str, Any]:
        try:
            from app.models.quest import Quest
            from datetime import date, datetime
            from sqlmodel import select, and_
            
            quest_date_str = parameters.get("quest_date")
            include_completed = parameters.get("include_completed", True)
            
            # Parse date
            if quest_date_str:
                quest_date = datetime.strptime(quest_date_str, "%Y-%m-%d").date()
            else:
                quest_date = date.today()
            
            # Build query
            conditions = [
                Quest.user_id == user.id,
                Quest.date_created == quest_date
            ]
            
            if not include_completed:
                conditions.append(Quest.is_complete == False)
            
            statement = select(Quest).where(and_(*conditions)).order_by(Quest.order_index)
            result = await session.execute(statement)
            quests = result.scalars().all()
            
            # Format quests
            quests_list = []
            completed_count = 0
            for quest in quests:
                if quest.is_complete:
                    completed_count += 1
                    
                quests_list.append({
                    "id": str(quest.id),
                    "content": quest.content,
                    "is_complete": quest.is_complete,
                    "date_due": quest.date_due.isoformat() if quest.date_due else None,
                    "time_due": quest.time_due,
                    "order_index": quest.order_index
                })
            
            logger.info(f"Retrieved {len(quests)} quests for {quest_date} via AI for user {user.id}")
            
            return {
                "success": True,
                "quests": quests_list,
                "summary": {
                    "date": quest_date.isoformat(),
                    "total": len(quests_list),
                    "completed": completed_count,
                    "pending": len(quests_list) - completed_count
                },
                "message": f"Found {len(quests_list)} quests for {quest_date}"
            }
            
        except Exception as e:
            logger.error(f"Error getting quests via AI: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get quests"
            }


class EditQuestTool(AITool):
    """Tool for editing existing quest tasks"""
    
    name: str = "edit_quest"
    description: str = "Edit an existing quest task by changing content, due date, or time"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "quest_content": {
                "type": "string",
                "description": "Current content of the quest to find and edit (partial match)"
            },
            "new_content": {
                "type": "string",
                "description": "New content for the quest"
            },
            "new_date_due": {
                "type": "string",
                "format": "date",
                "description": "New due date for the quest (YYYY-MM-DD format)"
            },
            "new_time_due": {
                "type": "string",
                "pattern": "^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
                "description": "New due time in HH:MM format"
            },
            "quest_date": {
                "type": "string",
                "format": "date",
                "description": "Date of the quest (YYYY-MM-DD format), defaults to today"
            }
        },
        "required": ["quest_content"]
    }
    
    async def execute(self, parameters: Dict[str, Any], user: User, session) -> Dict[str, Any]:
        try:
            from app.models.quest import Quest
            from datetime import date, datetime
            from sqlmodel import select, and_
            
            quest_content = parameters.get("quest_content")
            quest_date_str = parameters.get("quest_date")
            
            # Parse date
            if quest_date_str:
                quest_date = datetime.strptime(quest_date_str, "%Y-%m-%d").date()
            else:
                quest_date = date.today()
            
            # Find quest by content
            statement = select(Quest).where(
                and_(
                    Quest.user_id == user.id,
                    Quest.date_created == quest_date,
                    Quest.content.ilike(f"%{quest_content}%")
                )
            ).order_by(Quest.order_index)
            
            result = await session.execute(statement)
            quests = result.scalars().all()
            
            if not quests:
                return {
                    "success": False,
                    "error": f"No quest found matching '{quest_content}' for {quest_date}",
                    "message": f"Could not find quest matching '{quest_content}'"
                }
            
            # Use the first match
            quest = quests[0]
            
            # Update fields if provided
            if parameters.get("new_content"):
                quest.content = parameters["new_content"]
            
            if parameters.get("new_date_due"):
                quest.date_due = datetime.strptime(parameters["new_date_due"], "%Y-%m-%d").date()
            
            if parameters.get("new_time_due"):
                quest.time_due = parameters["new_time_due"]
            
            await session.commit()
            await session.refresh(quest)
            
            return {
                "success": True,
                "quest": {
                    "id": str(quest.id),
                    "content": quest.content,
                    "date_due": quest.date_due.isoformat() if quest.date_due else None,
                    "time_due": quest.time_due,
                    "is_complete": quest.is_complete
                },
                "message": f"Updated quest: {quest.content}"
            }
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error editing quest via AI: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to edit quest"
            }


class DeleteQuestTool(AITool):
    """Tool for deleting quest tasks"""
    
    name: str = "delete_quest"
    description: str = "Delete a quest task by content"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "quest_content": {
                "type": "string",
                "description": "Content of the quest to delete (partial match)"
            },
            "quest_date": {
                "type": "string",
                "format": "date",
                "description": "Date of the quest (YYYY-MM-DD format), defaults to today"
            }
        },
        "required": ["quest_content"]
    }
    
    async def execute(self, parameters: Dict[str, Any], user: User, session) -> Dict[str, Any]:
        try:
            from app.models.quest import Quest
            from datetime import date, datetime
            from sqlmodel import select, and_
            
            quest_content = parameters.get("quest_content")
            quest_date_str = parameters.get("quest_date")
            
            # Parse date
            if quest_date_str:
                quest_date = datetime.strptime(quest_date_str, "%Y-%m-%d").date()
            else:
                quest_date = date.today()
            
            # Find quest by content
            statement = select(Quest).where(
                and_(
                    Quest.user_id == user.id,
                    Quest.date_created == quest_date,
                    Quest.content.ilike(f"%{quest_content}%")
                )
            ).order_by(Quest.order_index)
            
            result = await session.execute(statement)
            quests = result.scalars().all()
            
            if not quests:
                return {
                    "success": False,
                    "error": f"No quest found matching '{quest_content}' for {quest_date}",
                    "message": f"Could not find quest matching '{quest_content}'"
                }
            
            # Delete the first match
            quest = quests[0]
            quest_content_deleted = quest.content
            
            await session.delete(quest)
            await session.commit()
            
            return {
                "success": True,
                "result": {
                    "deleted_quest": quest_content_deleted
                },
                "message": f"Deleted quest: {quest_content_deleted}"
            }
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error deleting quest via AI: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to delete quest"
            }


class InternetSearchTool(AITool):
    """Tool for searching the internet using Serper API"""
    
    name: str = "search_internet"
    description: str = "Search the internet for current information, news, facts, or answers to questions"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to find information on the internet"
            },
            "num_results": {
                "type": "integer",
                "description": "Number of search results to return (default: 5, max: 10)",
                "default": 5,
                "minimum": 1,
                "maximum": 10
            }
        },
        "required": ["query"]
    }
    
    async def execute(self, parameters: Dict[str, Any], user: User, session) -> Dict[str, Any]:
        """Execute internet search using Serper API"""
        try:
            if not settings.serper_api_key:
                return {
                    "success": False,
                    "error": "Internet search not available - Serper API key not configured",
                    "message": "Internet search functionality is not configured"
                }
            
            import httpx
            
            query = parameters.get("query")
            num_results = min(parameters.get("num_results", 5), 10)
            
            # Prepare Serper API request
            url = "https://google.serper.dev/search"
            headers = {
                'X-API-KEY': settings.serper_api_key,
                'Content-Type': 'application/json'
            }
            payload = {
                "q": query,
                "num": num_results
            }
            
            # Make the API request
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                results = response.json()
            
            # Extract organic search results
            organic_results = results.get("organic", [])
            
            # Format results for the AI
            search_results = []
            for result in organic_results[:num_results]:
                search_results.append({
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "position": result.get("position", 0)
                })
            
            # Also include answer box and knowledge graph if available
            answer_box = results.get("answerBox")
            knowledge_graph = results.get("knowledgeGraph")
            
            return {
                "success": True,
                "result": {
                    "query": query,
                    "search_results": search_results,
                    "answer_box": answer_box,
                    "knowledge_graph": knowledge_graph,
                    "results_count": len(search_results),
                    "search_time": results.get("searchInformation", {}).get("searchTime")
                },
                "message": f"Found {len(search_results)} search results for '{query}'"
            }
            
        except httpx.RequestError as e:
            logger.error(f"Network error in internet search: {e}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}",
                "message": "Failed to connect to search service"
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in internet search: {e}")
            return {
                "success": False,
                "error": f"Search API error: {e.response.status_code}",
                "message": "Search service returned an error"
            }
        except Exception as e:
            logger.error(f"Error in internet search: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to perform internet search"
            }


# Registry of available tools
AI_TOOLS_REGISTRY: Dict[str, AITool] = {
    "create_journal_entry": CreateJournalEntryTool(),
    "create_calendar_event": CreateCalendarEventTool(),
    "edit_calendar_event": EditCalendarEventTool(),
    "delete_calendar_event": DeleteCalendarEventTool(),
    "create_board": CreateBoardTool(),
    "create_card": CreateCardTool(),
    "get_boards": GetBoardsTool(),
    "create_quest": CreateQuestTool(),
    "complete_quest": CompleteQuestTool(),
    "edit_quest": EditQuestTool(),
    "delete_quest": DeleteQuestTool(),
    "get_quests": GetQuestsTool(),
    "search_internet": InternetSearchTool()
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