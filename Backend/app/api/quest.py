"""
Quest API endpoints for daily productivity tracking
"""
import logging
from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_, func

from app.config import settings
from app.core.auth import get_current_user
from app.database import get_session
from app.models.user import User
from app.models.quest import Quest
from app.schemas.quest import (
    QuestCreate, QuestUpdate, QuestResponse, QuestDayResponse,
    QuestArchiveResponse, QuestBatchReorder, QuestRolloverRequest,
    QuestRolloverResponse
)
from app.schemas.common import BaseResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/day/{quest_date}", response_model=QuestDayResponse)
async def get_quest_day(
    quest_date: date,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get all quests for a specific day
    
    Args:
        quest_date: Date to get quests for
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        QuestDayResponse: Quests for the specified day
    """
    try:
        # Get quests for the specified date
        statement = select(Quest).where(
            and_(
                Quest.user_id == current_user.id,
                Quest.date_created == quest_date
            )
        ).order_by(Quest.is_complete.asc(), Quest.created_at.desc())
        
        result = await session.execute(statement)
        quests = result.scalars().all()
        
        # Calculate counts
        total_count = len(quests)
        completed_count = sum(1 for q in quests if q.is_complete)
        pending_count = total_count - completed_count
        
        return {
            "date": quest_date,
            "quests": [QuestResponse.model_validate(quest).model_dump() for quest in quests],
            "total_count": total_count,
            "completed_count": completed_count,
            "pending_count": pending_count
        }
    
    except Exception as e:
        logger.error(f"Error fetching quest day {quest_date} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch quest day"
        )


@router.get("/today", response_model=QuestDayResponse)
async def get_today_quests(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get all quests for today
    
    Args:
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        QuestDayResponse: Today's quests
    """
    today = date.today()
    return await get_quest_day(today, current_user, session)


@router.get("/archive", response_model=QuestArchiveResponse)
async def get_quest_archive(
    start_date: Optional[date] = Query(None, description="Start date for archive"),
    end_date: Optional[date] = Query(None, description="End date for archive"),
    limit: int = Query(30, ge=1, le=365, description="Maximum number of days to return"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get quest archive for a date range
    
    Args:
        start_date: Start date (defaults to 30 days ago)
        end_date: End date (defaults to today)
        limit: Maximum number of days
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        QuestArchiveResponse: Archive of quest days
    """
    try:
        # Set default date range
        if not end_date:
            end_date = date.today()
        if not start_date:
            from datetime import timedelta
            start_date = end_date - timedelta(days=limit-1)
        
        # Get distinct dates with quests
        statement = select(Quest.date_created).where(
            and_(
                Quest.user_id == current_user.id,
                Quest.date_created >= start_date,
                Quest.date_created <= end_date
            )
        ).distinct().order_by(Quest.date_created.desc())
        
        result = await session.execute(statement)
        quest_dates = result.scalars().all()
        
        # Get quests for each date
        days = []
        for quest_date in quest_dates:
            day_response = await get_quest_day(quest_date, current_user, session)
            days.append(day_response)
        
        return {
            "days": days,
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_days": len(days)
            }
        }
    
    except Exception as e:
        logger.error(f"Error fetching quest archive for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch quest archive"
        )


@router.post("/", response_model=QuestResponse, status_code=status.HTTP_201_CREATED)
async def create_quest(
    quest_data: QuestCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new quest
    
    Args:
        quest_data: Quest creation data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        QuestResponse: Created quest
    """
    try:
        # Use today if no date provided
        quest_date = quest_data.date_created or date.today()
        
        # Get the next order index for this date
        if quest_data.order_index == 0:
            max_order_stmt = select(func.coalesce(func.max(Quest.order_index), 0)).where(
                and_(
                    Quest.user_id == current_user.id,
                    Quest.date_created == quest_date
                )
            )
            result = await session.execute(max_order_stmt)
            max_order = result.scalar() or 0
            order_index = max_order + 1
        else:
            order_index = quest_data.order_index
        
        # Create quest
        quest = Quest(
            user_id=current_user.id,
            content=quest_data.content,
            date_created=quest_date,
            date_due=quest_data.date_due,
            time_due=quest_data.time_due,
            order_index=order_index
        )
        
        session.add(quest)
        await session.commit()
        await session.refresh(quest)
        
        logger.info(f"Quest created for user {current_user.id}: {quest.id}")
        
        return QuestResponse.model_validate(quest)
    
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating quest for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create quest"
        )


@router.patch("/{quest_id}", response_model=QuestResponse)
async def update_quest(
    quest_id: UUID,
    quest_data: QuestUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update a quest
    
    Args:
        quest_id: Quest ID to update
        quest_data: Quest update data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        QuestResponse: Updated quest
    """
    try:
        # Get quest
        statement = select(Quest).where(
            and_(Quest.id == quest_id, Quest.user_id == current_user.id)
        )
        result = await session.execute(statement)
        quest = result.scalar_one_or_none()
        
        if not quest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quest not found"
            )
        
        # Update fields
        update_data = quest_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(quest, field, value)
        
        # Handle completion status change
        if quest_data.is_complete is not None:
            if quest_data.is_complete:
                quest.mark_complete()
            else:
                quest.mark_incomplete()
        
        quest.updated_at = datetime.now(timezone.utc)
        
        await session.commit()
        await session.refresh(quest)
        
        logger.info(f"Quest updated for user {current_user.id}: {quest.id}")
        
        return QuestResponse.model_validate(quest)
    
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating quest {quest_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update quest"
        )


@router.delete("/{quest_id}")
async def delete_quest(
    quest_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a quest
    
    Args:
        quest_id: Quest ID to delete
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        BaseResponse: Deletion confirmation
    """
    try:
        # Get quest
        statement = select(Quest).where(
            and_(Quest.id == quest_id, Quest.user_id == current_user.id)
        )
        result = await session.execute(statement)
        quest = result.scalar_one_or_none()
        
        if not quest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quest not found"
            )
        
        await session.delete(quest)
        await session.commit()
        
        logger.info(f"Quest deleted for user {current_user.id}: {quest.id}")
        
        return BaseResponse(message="Quest deleted successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting quest {quest_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete quest"
        )


@router.post("/reorder", response_model=BaseResponse)
async def reorder_quests(
    reorder_data: QuestBatchReorder,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Batch reorder quests
    
    Args:
        reorder_data: Batch reorder data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        BaseResponse: Reorder confirmation
    """
    try:
        # Update each quest's order
        for quest_order in reorder_data.quest_orders:
            statement = select(Quest).where(
                and_(
                    Quest.id == quest_order.quest_id,
                    Quest.user_id == current_user.id
                )
            )
            result = await session.execute(statement)
            quest = result.scalar_one_or_none()
            
            if quest:
                quest.order_index = quest_order.new_order_index
                quest.updated_at = datetime.now(timezone.utc)
        
        await session.commit()
        
        logger.info(f"Quests reordered for user {current_user.id}: {len(reorder_data.quest_orders)} items")
        
        return BaseResponse(message="Quests reordered successfully")
    
    except Exception as e:
        await session.rollback()
        logger.error(f"Error reordering quests for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder quests"
        )


@router.post("/rollover", response_model=QuestRolloverResponse)
async def rollover_incomplete_quests(
    rollover_data: QuestRolloverRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Roll over incomplete quests from one day to another
    
    Args:
        rollover_data: Rollover request data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        QuestRolloverResponse: Rollover result
    """
    try:
        to_date = rollover_data.to_date or date.today()
        
        # Get incomplete quests from the source date
        statement = select(Quest).where(
            and_(
                Quest.user_id == current_user.id,
                Quest.date_created == rollover_data.from_date,
                Quest.is_complete == False
            )
        ).order_by(Quest.order_index)
        
        result = await session.execute(statement)
        incomplete_quests = result.scalars().all()
        
        if not incomplete_quests:
            return QuestRolloverResponse(
                success=True,
                rolled_count=0,
                from_date=rollover_data.from_date,
                to_date=to_date,
                timestamp=datetime.now(timezone.utc)
            )
        
        # Get the next order index for the target date
        max_order_stmt = select(func.coalesce(func.max(Quest.order_index), 0)).where(
            and_(
                Quest.user_id == current_user.id,
                Quest.date_created == to_date
            )
        )
        result = await session.execute(max_order_stmt)
        max_order = result.scalar() or 0
        
        # Create new quests for the target date
        rolled_count = 0
        for i, quest in enumerate(incomplete_quests):
            new_quest = Quest(
                user_id=current_user.id,
                content=quest.content,
                date_created=to_date,
                date_due=quest.date_due,
                time_due=quest.time_due,
                order_index=max_order + i + 1
            )
            session.add(new_quest)
            rolled_count += 1
        
        await session.commit()
        
        logger.info(f"Rolled over {rolled_count} quests for user {current_user.id} from {rollover_data.from_date} to {to_date}")
        
        return QuestRolloverResponse(
            success=True,
            rolled_count=rolled_count,
            from_date=rollover_data.from_date,
            to_date=to_date,
            timestamp=datetime.now(timezone.utc)
        )
    
    except Exception as e:
        await session.rollback()
        logger.error(f"Error rolling over quests for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rollover quests"
        )