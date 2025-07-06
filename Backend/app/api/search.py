"""
Global search endpoints
"""
import logging
import time
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_, or_, desc, func, text

from app.core.auth import get_current_user
from app.database import get_session
from app.models.board import Board, Card
from app.models.calendar import CalendarEvent
from app.models.journal import JournalEntry
from app.models.user import User
from app.schemas.search import (
    SearchQuery, SearchResult, SearchResponse, 
    SearchSuggestion, SearchSuggestionsResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=SearchResponse)
async def search_content(
    q: str = Query(description="Search query"),
    type: str = Query(default="all", description="Content type filter"),
    limit: int = Query(default=50, ge=1, le=100, description="Results limit"),
    offset: int = Query(default=0, ge=0, description="Results offset"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Global search across all user content.
    
    Args:
        q: Search query
        type: Content type filter (all, boards, cards, calendar, journal)
        limit: Maximum results to return
        offset: Results offset for pagination
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        SearchResponse: Search results with metadata
    """
    start_time = time.time()
    
    try:
        if not q or len(q.strip()) < 2:
            return SearchResponse(
                query=q,
                results=[],
                total=0,
                limit=limit,
                offset=offset,
                took_ms=0,
                filters={"type": type}
            )
        
        search_term = q.strip()
        results = []
        
        # Search boards
        if type in ['all', 'boards']:
            board_results = await _search_boards(session, current_user.id, search_term, limit, offset)
            results.extend(board_results)
        
        # Search cards
        if type in ['all', 'cards']:
            card_results = await _search_cards(session, current_user.id, search_term, limit, offset)
            results.extend(card_results)
        
        # Search calendar events
        if type in ['all', 'calendar']:
            calendar_results = await _search_calendar_events(session, current_user.id, search_term, limit, offset)
            results.extend(calendar_results)
        
        # Search journal entries
        if type in ['all', 'journal']:
            journal_results = await _search_journal_entries(session, current_user.id, search_term, limit, offset)
            results.extend(journal_results)
        
        # Sort by relevance score (descending) and then by update time
        results.sort(key=lambda x: (x.relevance_score, x.updated_at.timestamp()), reverse=True)
        
        # Apply pagination
        total = len(results)
        paginated_results = results[offset:offset + limit]
        
        took_ms = int((time.time() - start_time) * 1000)
        
        return SearchResponse(
            query=search_term,
            results=paginated_results,
            total=total,
            limit=limit,
            offset=offset,
            took_ms=took_ms,
            filters={"type": type}
        )
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )


@router.get("/suggestions", response_model=SearchSuggestionsResponse)
async def get_search_suggestions(
    q: str = Query(description="Partial search query"),
    limit: int = Query(default=10, ge=1, le=20, description="Suggestions limit"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get search suggestions/autocomplete.
    
    Args:
        q: Partial search query
        limit: Maximum suggestions to return
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        SearchSuggestionsResponse: Search suggestions
    """
    try:
        if not q or len(q.strip()) < 1:
            return SearchSuggestionsResponse(query=q, suggestions=[])
        
        search_term = q.strip().lower()
        suggestions = []
        
        # Get board titles
        board_query = select(Board.title).where(
            and_(
                Board.user_id == current_user.id,
                func.lower(Board.title).like(f"%{search_term}%")
            )
        ).limit(5)
        board_result = await session.exec(board_query)
        board_titles = board_result.all()
        
        for title in board_titles:
            suggestions.append(SearchSuggestion(
                text=title,
                type="board",
                count=1
            ))
        
        # Get journal tags
        journal_query = select(JournalEntry.tags).where(
            JournalEntry.user_id == current_user.id
        )
        journal_result = await session.exec(journal_query)
        all_tags = set()
        
        for entry in journal_result.all():
            if entry.tags:
                for tag in entry.tags:
                    if search_term in tag.lower():
                        all_tags.add(tag)
        
        for tag in list(all_tags)[:5]:
            suggestions.append(SearchSuggestion(
                text=f"#{tag}",
                type="tag",
                count=1
            ))
        
        return SearchSuggestionsResponse(
            query=search_term,
            suggestions=suggestions[:limit]
        )
    
    except Exception as e:
        logger.error(f"Search suggestions error: {e}")
        return SearchSuggestionsResponse(query=q, suggestions=[])


async def _search_boards(session: AsyncSession, user_id: UUID, query: str, limit: int, offset: int) -> List[SearchResult]:
    """Search boards by title and description."""
    try:
        search_query = select(Board).where(
            and_(
                Board.user_id == user_id,
                or_(
                    func.lower(Board.title).like(f"%{query.lower()}%"),
                    func.lower(Board.description).like(f"%{query.lower()}%") if Board.description else False
                )
            )
        ).order_by(desc(Board.updated_at))
        
        result = await session.exec(search_query)
        boards = result.all()
        
        search_results = []
        for board in boards:
            # Calculate relevance score
            relevance = 0.0
            if query.lower() in (board.title or "").lower():
                relevance += 2.0
            if board.description and query.lower() in board.description.lower():
                relevance += 1.0
            
            search_results.append(SearchResult(
                id=board.id,
                type="board",
                title=board.title,
                description=board.description,
                url=f"/boards/{board.id}",
                created_at=board.created_at,
                updated_at=board.updated_at,
                metadata={
                    "color": board.color,
                    "is_archived": board.is_archived
                },
                relevance_score=relevance
            ))
        
        return search_results
    
    except Exception as e:
        logger.error(f"Board search error: {e}")
        return []


async def _search_cards(session: AsyncSession, user_id: UUID, query: str, limit: int, offset: int) -> List[SearchResult]:
    """Search cards by title and description."""
    try:
        search_query = select(Card, Board.title.label("board_title")).join(
            Board, Card.board_id == Board.id
        ).where(
            and_(
                Board.user_id == user_id,
                or_(
                    func.lower(Card.title).like(f"%{query.lower()}%"),
                    func.lower(Card.description).like(f"%{query.lower()}%") if Card.description else False
                )
            )
        ).order_by(desc(Card.updated_at))
        
        result = await session.exec(search_query)
        cards = result.all()
        
        search_results = []
        for card, board_title in cards:
            # Calculate relevance score
            relevance = 0.0
            if query.lower() in card.title.lower():
                relevance += 2.0
            if card.description and query.lower() in card.description.lower():
                relevance += 1.0
            
            search_results.append(SearchResult(
                id=card.id,
                type="card",
                title=card.title,
                description=card.description,
                url=f"/boards/{card.board_id}?card={card.id}",
                created_at=card.created_at,
                updated_at=card.updated_at,
                metadata={
                    "board_title": board_title,
                    "status": card.status,
                    "priority": card.priority
                },
                relevance_score=relevance
            ))
        
        return search_results
    
    except Exception as e:
        logger.error(f"Card search error: {e}")
        return []


async def _search_calendar_events(session: AsyncSession, user_id: UUID, query: str, limit: int, offset: int) -> List[SearchResult]:
    """Search calendar events by title and description."""
    try:
        search_query = select(CalendarEvent).where(
            and_(
                CalendarEvent.user_id == user_id,
                or_(
                    func.lower(CalendarEvent.title).like(f"%{query.lower()}%"),
                    func.lower(CalendarEvent.description).like(f"%{query.lower()}%") if CalendarEvent.description else False,
                    func.lower(CalendarEvent.location).like(f"%{query.lower()}%") if CalendarEvent.location else False
                )
            )
        ).order_by(desc(CalendarEvent.start_datetime))
        
        result = await session.exec(search_query)
        events = result.all()
        
        search_results = []
        for event in events:
            # Calculate relevance score
            relevance = 0.0
            if query.lower() in event.title.lower():
                relevance += 2.0
            if event.description and query.lower() in event.description.lower():
                relevance += 1.0
            if event.location and query.lower() in event.location.lower():
                relevance += 0.5
            
            search_results.append(SearchResult(
                id=event.id,
                type="calendar_event",
                title=event.title,
                description=event.description,
                url=f"/calendar?event={event.id}",
                created_at=event.created_at,
                updated_at=event.updated_at,
                metadata={
                    "start_datetime": event.start_datetime.isoformat(),
                    "end_datetime": event.end_datetime.isoformat(),
                    "location": event.location,
                    "event_type": event.event_type,
                    "color": event.color
                },
                relevance_score=relevance
            ))
        
        return search_results
    
    except Exception as e:
        logger.error(f"Calendar search error: {e}")
        return []


async def _search_journal_entries(session: AsyncSession, user_id: UUID, query: str, limit: int, offset: int) -> List[SearchResult]:
    """Search journal entries by title, content, and tags."""
    try:
        search_query = select(JournalEntry).where(
            and_(
                JournalEntry.user_id == user_id,
                or_(
                    func.lower(JournalEntry.title).like(f"%{query.lower()}%") if JournalEntry.title else False,
                    func.lower(JournalEntry.content).like(f"%{query.lower()}%"),
                    JournalEntry.tags.contains([query.lower()]) if JournalEntry.tags else False
                )
            )
        ).order_by(desc(JournalEntry.entry_date))
        
        result = await session.exec(search_query)
        entries = result.all()
        
        search_results = []
        for entry in entries:
            # Calculate relevance score
            relevance = 0.0
            if entry.title and query.lower() in entry.title.lower():
                relevance += 2.0
            if query.lower() in entry.content.lower():
                relevance += 1.5
            if entry.tags and any(query.lower() in tag.lower() for tag in entry.tags):
                relevance += 1.0
            
            # Create description from content (first 150 chars)
            description = entry.content[:150] + "..." if len(entry.content) > 150 else entry.content
            
            search_results.append(SearchResult(
                id=entry.id,
                type="journal_entry",
                title=entry.title or "Untitled Entry",
                description=description,
                url=f"/journal?entry={entry.id}",
                created_at=entry.created_at,
                updated_at=entry.updated_at,
                metadata={
                    "entry_date": entry.entry_date.isoformat(),
                    "mood": entry.mood,
                    "tags": entry.tags or [],
                    "is_private": entry.is_private,
                    "is_favorite": entry.is_favorite
                },
                relevance_score=relevance
            ))
        
        return search_results
    
    except Exception as e:
        logger.error(f"Journal search error: {e}")
        return []