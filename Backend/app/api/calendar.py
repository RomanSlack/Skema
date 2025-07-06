"""
Calendar event endpoints
"""
import logging
from datetime import datetime, timezone, date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_, desc, or_

from app.core.auth import get_current_user
from app.database import get_session
from app.models.calendar import CalendarEvent
from app.models.user import User
from app.schemas.calendar import (
    CalendarEventCreate, CalendarEventUpdate, CalendarEventResponse,
    CalendarEventFilter
)
from app.schemas.common import BaseResponse, PaginatedResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/events", response_model=PaginatedResponse[CalendarEventResponse])
async def get_calendar_events(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    start_date: Optional[datetime] = Query(None, description="Filter start date"),
    end_date: Optional[datetime] = Query(None, description="Filter end date"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get user's calendar events with filtering and pagination.
    
    Args:
        page: Page number
        size: Page size
        start_date: Filter events after this date
        end_date: Filter events before this date
        event_type: Filter by event type
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        PaginatedResponse[CalendarEventResponse]: Paginated calendar events
    """
    try:
        # Build query
        query = select(CalendarEvent).where(CalendarEvent.user_id == current_user.id)
        
        # Apply filters
        if start_date:
            query = query.where(CalendarEvent.start_datetime >= start_date)
        if end_date:
            query = query.where(CalendarEvent.end_datetime <= end_date)
        if event_type:
            query = query.where(CalendarEvent.event_type == event_type)
        
        # Get total count
        count_query = select(CalendarEvent).where(CalendarEvent.user_id == current_user.id)
        if start_date:
            count_query = count_query.where(CalendarEvent.start_datetime >= start_date)
        if end_date:
            count_query = count_query.where(CalendarEvent.end_datetime <= end_date)
        if event_type:
            count_query = count_query.where(CalendarEvent.event_type == event_type)
        
        total_result = await session.exec(count_query)
        total = len(total_result.all())
        
        # Get paginated results
        query = query.order_by(CalendarEvent.start_datetime).offset((page - 1) * size).limit(size)
        result = await session.exec(query)
        events = result.all()
        
        event_responses = [CalendarEventResponse.from_orm(event) for event in events]
        
        return PaginatedResponse.create(
            items=event_responses,
            total=total,
            page=page,
            size=size
        )
    
    except Exception as e:
        logger.error(f"Get calendar events error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve calendar events"
        )


@router.post("/events", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar_event(
    event_data: CalendarEventCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new calendar event.
    
    Args:
        event_data: Calendar event creation data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        CalendarEventResponse: Created calendar event
    """
    try:
        event = CalendarEvent(
            user_id=current_user.id,
            title=event_data.title,
            description=event_data.description,
            start_datetime=event_data.start_datetime,
            end_datetime=event_data.end_datetime,
            location=event_data.location,
            event_type=event_data.event_type,
            color=event_data.color,
            metadata=event_data.metadata or {},
            is_all_day=event_data.is_all_day,
            is_recurring=event_data.is_recurring
        )
        
        session.add(event)
        await session.commit()
        await session.refresh(event)
        
        logger.info(f"Calendar event created: {event.title} by {current_user.email}")
        
        return CalendarEventResponse.from_orm(event)
    
    except Exception as e:
        logger.error(f"Create calendar event error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create calendar event"
        )


@router.get("/events/{event_id}", response_model=CalendarEventResponse)
async def get_calendar_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get a specific calendar event.
    
    Args:
        event_id: Calendar event ID
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        CalendarEventResponse: Calendar event
    """
    try:
        event = await session.get(CalendarEvent, event_id)
        if not event or event.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Calendar event not found"
            )
        
        return CalendarEventResponse.from_orm(event)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get calendar event error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve calendar event"
        )


@router.put("/events/{event_id}", response_model=CalendarEventResponse)
async def update_calendar_event(
    event_id: UUID,
    event_update: CalendarEventUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update a calendar event.
    
    Args:
        event_id: Calendar event ID
        event_update: Calendar event update data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        CalendarEventResponse: Updated calendar event
    """
    try:
        event = await session.get(CalendarEvent, event_id)
        if not event or event.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Calendar event not found"
            )
        
        # Update event fields
        if event_update.title is not None:
            event.title = event_update.title
        if event_update.description is not None:
            event.description = event_update.description
        if event_update.start_datetime is not None:
            event.start_datetime = event_update.start_datetime
        if event_update.end_datetime is not None:
            event.end_datetime = event_update.end_datetime
        if event_update.location is not None:
            event.location = event_update.location
        if event_update.event_type is not None:
            event.event_type = event_update.event_type
        if event_update.color is not None:
            event.color = event_update.color
        if event_update.metadata is not None:
            event.metadata = event_update.metadata
        if event_update.is_all_day is not None:
            event.is_all_day = event_update.is_all_day
        if event_update.is_recurring is not None:
            event.is_recurring = event_update.is_recurring
        
        # Validate end datetime is after start datetime
        if event.end_datetime <= event.start_datetime:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End datetime must be after start datetime"
            )
        
        await session.commit()
        await session.refresh(event)
        
        logger.info(f"Calendar event updated: {event.title} by {current_user.email}")
        
        return CalendarEventResponse.from_orm(event)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update calendar event error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update calendar event"
        )


@router.delete("/events/{event_id}", response_model=BaseResponse)
async def delete_calendar_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a calendar event.
    
    Args:
        event_id: Calendar event ID
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        BaseResponse: Success response
    """
    try:
        event = await session.get(CalendarEvent, event_id)
        if not event or event.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Calendar event not found"
            )
        
        await session.delete(event)
        await session.commit()
        
        logger.info(f"Calendar event deleted: {event.title} by {current_user.email}")
        
        return BaseResponse(message="Calendar event deleted successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete calendar event error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete calendar event"
        )


@router.get("/events/date/{date}", response_model=List[CalendarEventResponse])
async def get_events_by_date(
    date: date,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get calendar events for a specific date.
    
    Args:
        date: Date to get events for
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        List[CalendarEventResponse]: List of calendar events for the date
    """
    try:
        # Convert date to datetime range
        start_of_day = datetime.combine(date, datetime.min.time())
        end_of_day = datetime.combine(date, datetime.max.time())
        
        # Make timezone-aware
        start_of_day = start_of_day.replace(tzinfo=timezone.utc)
        end_of_day = end_of_day.replace(tzinfo=timezone.utc)
        
        # Query events that overlap with the date
        query = select(CalendarEvent).where(
            and_(
                CalendarEvent.user_id == current_user.id,
                or_(
                    # Event starts on this date
                    and_(
                        CalendarEvent.start_datetime >= start_of_day,
                        CalendarEvent.start_datetime <= end_of_day
                    ),
                    # Event ends on this date
                    and_(
                        CalendarEvent.end_datetime >= start_of_day,
                        CalendarEvent.end_datetime <= end_of_day
                    ),
                    # Event spans this date
                    and_(
                        CalendarEvent.start_datetime <= start_of_day,
                        CalendarEvent.end_datetime >= end_of_day
                    )
                )
            )
        ).order_by(CalendarEvent.start_datetime)
        
        result = await session.exec(query)
        events = result.all()
        
        return [CalendarEventResponse.from_orm(event) for event in events]
    
    except Exception as e:
        logger.error(f"Get events by date error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve events for date"
        )


@router.get("/events/upcoming", response_model=List[CalendarEventResponse])
async def get_upcoming_events(
    limit: int = Query(10, ge=1, le=50, description="Number of upcoming events"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get upcoming calendar events.
    
    Args:
        limit: Maximum number of events to return
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        List[CalendarEventResponse]: List of upcoming calendar events
    """
    try:
        now = datetime.now(timezone.utc)
        
        query = select(CalendarEvent).where(
            and_(
                CalendarEvent.user_id == current_user.id,
                CalendarEvent.start_datetime >= now
            )
        ).order_by(CalendarEvent.start_datetime).limit(limit)
        
        result = await session.exec(query)
        events = result.all()
        
        return [CalendarEventResponse.from_orm(event) for event in events]
    
    except Exception as e:
        logger.error(f"Get upcoming events error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve upcoming events"
        )