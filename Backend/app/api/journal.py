"""
Journal entry endpoints
"""
import logging
from datetime import date, datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_, desc, func, or_

from app.core.auth import get_current_user
from app.database import get_session
from app.models.journal import JournalEntry
from app.models.user import User
from app.schemas.journal import (
    JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse,
    JournalEntryFilter, JournalStats
)
from app.schemas.common import BaseResponse, PaginatedResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/entries", response_model=PaginatedResponse[JournalEntryResponse])
async def get_journal_entries(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    start_date: Optional[date] = Query(None, description="Filter start date"),
    end_date: Optional[date] = Query(None, description="Filter end date"),
    mood: Optional[str] = Query(None, description="Filter by mood"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    is_favorite: Optional[bool] = Query(None, description="Filter by favorite status"),
    search: Optional[str] = Query(None, description="Search in title and content"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get user's journal entries with filtering and pagination.
    
    Args:
        page: Page number
        size: Page size
        start_date: Filter entries after this date
        end_date: Filter entries before this date
        mood: Filter by mood
        tags: Comma-separated list of tags to filter by
        is_favorite: Filter by favorite status
        search: Search text in title and content
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        PaginatedResponse[JournalEntryResponse]: Paginated journal entries
    """
    try:
        # Build query
        query = select(JournalEntry).where(JournalEntry.user_id == current_user.id)
        
        # Apply filters
        if start_date:
            query = query.where(JournalEntry.entry_date >= start_date)
        if end_date:
            query = query.where(JournalEntry.entry_date <= end_date)
        if mood:
            query = query.where(JournalEntry.mood == mood)
        if is_favorite is not None:
            query = query.where(JournalEntry.is_favorite == is_favorite)
        
        # Filter by tags
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            for tag in tag_list:
                query = query.where(JournalEntry.tags.contains([tag]))
        
        # Search in title and content
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    JournalEntry.title.ilike(search_term),
                    JournalEntry.content.ilike(search_term)
                )
            )
        
        # Get total count
        count_query = select(JournalEntry).where(JournalEntry.user_id == current_user.id)
        if start_date:
            count_query = count_query.where(JournalEntry.entry_date >= start_date)
        if end_date:
            count_query = count_query.where(JournalEntry.entry_date <= end_date)
        if mood:
            count_query = count_query.where(JournalEntry.mood == mood)
        if is_favorite is not None:
            count_query = count_query.where(JournalEntry.is_favorite == is_favorite)
        if tags:
            for tag in tag_list:
                count_query = count_query.where(JournalEntry.tags.contains([tag]))
        if search:
            count_query = count_query.where(
                or_(
                    JournalEntry.title.ilike(search_term),
                    JournalEntry.content.ilike(search_term)
                )
            )
        
        total_result = await session.exec(count_query)
        total = len(total_result.all())
        
        # Get paginated results
        query = query.order_by(desc(JournalEntry.entry_date)).offset((page - 1) * size).limit(size)
        result = await session.exec(query)
        entries = result.all()
        
        entry_responses = [JournalEntryResponse.from_orm(entry) for entry in entries]
        
        return PaginatedResponse.create(
            items=entry_responses,
            total=total,
            page=page,
            size=size
        )
    
    except Exception as e:
        logger.error(f"Get journal entries error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve journal entries"
        )


@router.post("/entries", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_journal_entry(
    entry_data: JournalEntryCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new journal entry.
    
    Args:
        entry_data: Journal entry creation data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        JournalEntryResponse: Created journal entry
    """
    try:
        # Set entry date to today if not provided
        entry_date = entry_data.entry_date or date.today()
        
        entry = JournalEntry(
            user_id=current_user.id,
            title=entry_data.title,
            content=entry_data.content,
            mood=entry_data.mood,
            tags=entry_data.tags or [],
            metadata=entry_data.metadata or {},
            entry_date=entry_date,
            is_private=entry_data.is_private,
            is_favorite=entry_data.is_favorite
        )
        
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        
        logger.info(f"Journal entry created by {current_user.email}")
        
        return JournalEntryResponse.from_orm(entry)
    
    except Exception as e:
        logger.error(f"Create journal entry error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create journal entry"
        )


@router.get("/entries/{entry_id}", response_model=JournalEntryResponse)
async def get_journal_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get a specific journal entry.
    
    Args:
        entry_id: Journal entry ID
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        JournalEntryResponse: Journal entry
    """
    try:
        entry = await session.get(JournalEntry, entry_id)
        if not entry or entry.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found"
            )
        
        return JournalEntryResponse.from_orm(entry)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get journal entry error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve journal entry"
        )


@router.put("/entries/{entry_id}", response_model=JournalEntryResponse)
async def update_journal_entry(
    entry_id: UUID,
    entry_update: JournalEntryUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update a journal entry.
    
    Args:
        entry_id: Journal entry ID
        entry_update: Journal entry update data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        JournalEntryResponse: Updated journal entry
    """
    try:
        entry = await session.get(JournalEntry, entry_id)
        if not entry or entry.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found"
            )
        
        # Update entry fields
        if entry_update.title is not None:
            entry.title = entry_update.title
        if entry_update.content is not None:
            entry.content = entry_update.content
        if entry_update.mood is not None:
            entry.mood = entry_update.mood
        if entry_update.tags is not None:
            entry.tags = entry_update.tags
        if entry_update.metadata is not None:
            entry.metadata = entry_update.metadata
        if entry_update.entry_date is not None:
            entry.entry_date = entry_update.entry_date
        if entry_update.is_private is not None:
            entry.is_private = entry_update.is_private
        if entry_update.is_favorite is not None:
            entry.is_favorite = entry_update.is_favorite
        
        await session.commit()
        await session.refresh(entry)
        
        logger.info(f"Journal entry updated by {current_user.email}")
        
        return JournalEntryResponse.from_orm(entry)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update journal entry error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update journal entry"
        )


@router.delete("/entries/{entry_id}", response_model=BaseResponse)
async def delete_journal_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a journal entry.
    
    Args:
        entry_id: Journal entry ID
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        BaseResponse: Success response
    """
    try:
        entry = await session.get(JournalEntry, entry_id)
        if not entry or entry.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found"
            )
        
        await session.delete(entry)
        await session.commit()
        
        logger.info(f"Journal entry deleted by {current_user.email}")
        
        return BaseResponse(message="Journal entry deleted successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete journal entry error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete journal entry"
        )


@router.get("/entries/date/{entry_date}", response_model=List[JournalEntryResponse])
async def get_entries_by_date(
    entry_date: date,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get journal entries for a specific date.
    
    Args:
        entry_date: Date to get entries for
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        List[JournalEntryResponse]: List of journal entries for the date
    """
    try:
        query = select(JournalEntry).where(
            and_(
                JournalEntry.user_id == current_user.id,
                JournalEntry.entry_date == entry_date
            )
        ).order_by(desc(JournalEntry.created_at))
        
        result = await session.exec(query)
        entries = result.all()
        
        return [JournalEntryResponse.from_orm(entry) for entry in entries]
    
    except Exception as e:
        logger.error(f"Get entries by date error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve entries for date"
        )


@router.get("/stats", response_model=JournalStats)
async def get_journal_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get journal statistics for the current user.
    
    Args:
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        JournalStats: Journal statistics
    """
    try:
        now = datetime.now(timezone.utc)
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_week_start = now - timedelta(days=now.weekday())
        current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Total entries
        total_query = select(func.count(JournalEntry.id)).where(JournalEntry.user_id == current_user.id)
        total_result = await session.exec(total_query)
        total_entries = total_result.first() or 0
        
        # Entries this month
        month_query = select(func.count(JournalEntry.id)).where(
            and_(
                JournalEntry.user_id == current_user.id,
                JournalEntry.created_at >= current_month_start
            )
        )
        month_result = await session.exec(month_query)
        entries_this_month = month_result.first() or 0
        
        # Entries this week
        week_query = select(func.count(JournalEntry.id)).where(
            and_(
                JournalEntry.user_id == current_user.id,
                JournalEntry.created_at >= current_week_start
            )
        )
        week_result = await session.exec(week_query)
        entries_this_week = week_result.first() or 0
        
        # Total words and average
        entries_query = select(JournalEntry).where(JournalEntry.user_id == current_user.id)
        entries_result = await session.exec(entries_query)
        entries = entries_result.all()
        
        total_words = 0
        mood_counts = {}
        all_tags = set()
        
        for entry in entries:
            # Count words in content
            words = len(entry.content.split()) if entry.content else 0
            total_words += words
            
            # Count moods
            if entry.mood:
                mood_counts[entry.mood] = mood_counts.get(entry.mood, 0) + 1
            
            # Collect tags
            if entry.tags:
                all_tags.update(entry.tags)
        
        average_words_per_entry = total_words / total_entries if total_entries > 0 else 0
        most_common_mood = max(mood_counts, key=mood_counts.get) if mood_counts else None
        
        # Favorite count
        favorite_query = select(func.count(JournalEntry.id)).where(
            and_(
                JournalEntry.user_id == current_user.id,
                JournalEntry.is_favorite == True
            )
        )
        favorite_result = await session.exec(favorite_query)
        favorite_count = favorite_result.first() or 0
        
        # Calculate streak (simplified - consecutive days with entries)
        streak_days = 0
        check_date = date.today()
        
        while True:
            day_query = select(func.count(JournalEntry.id)).where(
                and_(
                    JournalEntry.user_id == current_user.id,
                    JournalEntry.entry_date == check_date
                )
            )
            day_result = await session.exec(day_query)
            day_count = day_result.first() or 0
            
            if day_count > 0:
                streak_days += 1
                check_date -= timedelta(days=1)
            else:
                break
            
            # Prevent infinite loop
            if streak_days > 365:
                break
        
        return JournalStats(
            total_entries=total_entries,
            entries_this_month=entries_this_month,
            entries_this_week=entries_this_week,
            total_words=total_words,
            average_words_per_entry=round(average_words_per_entry, 2),
            most_common_mood=most_common_mood,
            streak_days=streak_days,
            favorite_count=favorite_count,
            tags_used=sorted(list(all_tags))
        )
    
    except Exception as e:
        logger.error(f"Get journal stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve journal statistics"
        )