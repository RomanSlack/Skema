"""
Board and card management endpoints
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_, desc

from app.core.auth import get_current_user
from app.database import get_session
from app.models.board import Board, Card
from app.models.user import User
from app.schemas.board import (
    BoardCreate, BoardUpdate, BoardResponse, BoardWithCards,
    CardCreate, CardUpdate, CardResponse, CardMove
)
from app.schemas.common import BaseResponse, PaginatedResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=PaginatedResponse[BoardResponse])
async def get_boards(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    include_archived: bool = Query(False, description="Include archived boards"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get user's boards with pagination.
    
    Args:
        page: Page number
        size: Page size
        include_archived: Include archived boards
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        PaginatedResponse[BoardResponse]: Paginated boards
    """
    try:
        # Build query
        query = select(Board).where(Board.user_id == current_user.id)
        
        if not include_archived:
            query = query.where(Board.is_archived == False)
        
        # Get total count
        count_query = select(Board).where(Board.user_id == current_user.id)
        if not include_archived:
            count_query = count_query.where(Board.is_archived == False)
        
        total_result = await session.exec(count_query)
        total = len(total_result.all())
        
        # Get paginated results
        query = query.order_by(desc(Board.updated_at)).offset((page - 1) * size).limit(size)
        result = await session.exec(query)
        boards = result.all()
        
        board_responses = [BoardResponse.from_orm(board) for board in boards]
        
        return PaginatedResponse.create(
            items=board_responses,
            total=total,
            page=page,
            size=size
        )
    
    except Exception as e:
        logger.error(f"Get boards error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve boards"
        )


@router.post("/", response_model=BoardResponse, status_code=status.HTTP_201_CREATED)
async def create_board(
    board_data: BoardCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new board.
    
    Args:
        board_data: Board creation data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        BoardResponse: Created board
    """
    try:
        board = Board(
            user_id=current_user.id,
            title=board_data.title,
            description=board_data.description,
            color=board_data.color,
            settings=board_data.settings or {}
        )
        
        session.add(board)
        await session.commit()
        await session.refresh(board)
        
        logger.info(f"Board created: {board.title} by {current_user.email}")
        
        return BoardResponse.from_orm(board)
    
    except Exception as e:
        logger.error(f"Create board error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create board"
        )


@router.get("/{board_id}", response_model=BoardWithCards)
async def get_board(
    board_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get a specific board with its cards.
    
    Args:
        board_id: Board ID
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        BoardWithCards: Board with cards
    """
    try:
        # Get board
        board = await session.get(Board, board_id)
        if not board or board.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Board not found"
            )
        
        # Get cards
        cards_query = select(Card).where(Card.board_id == board_id).order_by(Card.position)
        cards_result = await session.exec(cards_query)
        cards = cards_result.all()
        
        # Convert to response format
        board_response = BoardResponse.from_orm(board)
        card_responses = [CardResponse.from_orm(card) for card in cards]
        
        return BoardWithCards(
            **board_response.dict(),
            cards=card_responses
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get board error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve board"
        )


@router.put("/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: UUID,
    board_update: BoardUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update a board.
    
    Args:
        board_id: Board ID
        board_update: Board update data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        BoardResponse: Updated board
    """
    try:
        # Get board
        board = await session.get(Board, board_id)
        if not board or board.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Board not found"
            )
        
        # Update board fields
        if board_update.title is not None:
            board.title = board_update.title
        if board_update.description is not None:
            board.description = board_update.description
        if board_update.color is not None:
            board.color = board_update.color
        if board_update.settings is not None:
            board.settings = board_update.settings
        if board_update.is_archived is not None:
            board.is_archived = board_update.is_archived
        
        await session.commit()
        await session.refresh(board)
        
        logger.info(f"Board updated: {board.title} by {current_user.email}")
        
        return BoardResponse.from_orm(board)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update board error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update board"
        )


@router.delete("/{board_id}", response_model=BaseResponse)
async def delete_board(
    board_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a board.
    
    Args:
        board_id: Board ID
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        BaseResponse: Success response
    """
    try:
        # Get board
        board = await session.get(Board, board_id)
        if not board or board.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Board not found"
            )
        
        # Delete board (cards will be deleted by cascade)
        await session.delete(board)
        await session.commit()
        
        logger.info(f"Board deleted: {board.title} by {current_user.email}")
        
        return BaseResponse(message="Board deleted successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete board error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete board"
        )


@router.get("/{board_id}/cards", response_model=List[CardResponse])
async def get_board_cards(
    board_id: UUID,
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get cards for a specific board.
    
    Args:
        board_id: Board ID
        status: Filter by card status
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        List[CardResponse]: List of cards
    """
    try:
        # Verify board ownership
        board = await session.get(Board, board_id)
        if not board or board.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Board not found"
            )
        
        # Build query
        query = select(Card).where(Card.board_id == board_id)
        
        if status:
            query = query.where(Card.status == status)
        
        query = query.order_by(Card.position)
        
        result = await session.exec(query)
        cards = result.all()
        
        return [CardResponse.from_orm(card) for card in cards]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get board cards error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cards"
        )


@router.post("/{board_id}/cards", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
async def create_card(
    board_id: UUID,
    card_data: CardCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new card in a board.
    
    Args:
        board_id: Board ID
        card_data: Card creation data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        CardResponse: Created card
    """
    try:
        # Verify board ownership
        board = await session.get(Board, board_id)
        if not board or board.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Board not found"
            )
        
        # Get next position if not specified
        if card_data.position is None:
            max_position_query = select(Card.position).where(
                and_(Card.board_id == board_id, Card.status == card_data.status)
            ).order_by(desc(Card.position)).limit(1)
            
            max_position_result = await session.exec(max_position_query)
            max_position = max_position_result.first()
            card_data.position = (max_position or 0) + 1
        
        card = Card(
            board_id=board_id,
            title=card_data.title,
            description=card_data.description,
            status=card_data.status,
            priority=card_data.priority,
            card_metadata=card_data.card_metadata or {},
            position=card_data.position
        )
        
        session.add(card)
        await session.commit()
        await session.refresh(card)
        
        logger.info(f"Card created: {card.title} in board {board.title} by {current_user.email}")
        
        return CardResponse.from_orm(card)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create card error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create card"
        )


@router.put("/cards/{card_id}", response_model=CardResponse)
async def update_card(
    card_id: UUID,
    card_update: CardUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update a card.
    
    Args:
        card_id: Card ID
        card_update: Card update data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        CardResponse: Updated card
    """
    try:
        # Get card and verify ownership
        card = await session.get(Card, card_id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Card not found"
            )
        
        # Verify board ownership
        board = await session.get(Board, card.board_id)
        if not board or board.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Card not found"
            )
        
        # Update card fields
        if card_update.title is not None:
            card.title = card_update.title
        if card_update.description is not None:
            card.description = card_update.description
        if card_update.status is not None:
            card.status = card_update.status
        if card_update.priority is not None:
            card.priority = card_update.priority
        if card_update.card_metadata is not None:
            card.card_metadata = card_update.card_metadata
        if card_update.position is not None:
            card.position = card_update.position
        
        # Set completion timestamp if moving to done
        if card_update.status == "done" and card.status != "done":
            from datetime import datetime, timezone
            card.completed_at = datetime.now(timezone.utc)
        elif card_update.status != "done" and card.status == "done":
            card.completed_at = None
        
        await session.commit()
        await session.refresh(card)
        
        logger.info(f"Card updated: {card.title} by {current_user.email}")
        
        return CardResponse.from_orm(card)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update card error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update card"
        )


@router.put("/cards/{card_id}/move", response_model=CardResponse)
async def move_card(
    card_id: UUID,
    move_data: CardMove,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Move a card to a different position or status.
    
    Args:
        card_id: Card ID
        move_data: Card move data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        CardResponse: Updated card
    """
    try:
        # Get card and verify ownership
        card = await session.get(Card, card_id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Card not found"
            )
        
        # Verify board ownership
        board = await session.get(Board, card.board_id)
        if not board or board.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Card not found"
            )
        
        # Update card position and status
        old_status = card.status
        card.board_id = move_data.board_id
        card.status = move_data.status
        card.position = move_data.position
        
        # Set completion timestamp if moving to done
        if move_data.status == "done" and old_status != "done":
            from datetime import datetime, timezone
            card.completed_at = datetime.now(timezone.utc)
        elif move_data.status != "done" and old_status == "done":
            card.completed_at = None
        
        await session.commit()
        await session.refresh(card)
        
        logger.info(f"Card moved: {card.title} by {current_user.email}")
        
        return CardResponse.from_orm(card)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Move card error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to move card"
        )


@router.delete("/cards/{card_id}", response_model=BaseResponse)
async def delete_card(
    card_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a card.
    
    Args:
        card_id: Card ID
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        BaseResponse: Success response
    """
    try:
        # Get card and verify ownership
        card = await session.get(Card, card_id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Card not found"
            )
        
        # Verify board ownership
        board = await session.get(Board, card.board_id)
        if not board or board.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Card not found"
            )
        
        # Delete card
        await session.delete(card)
        await session.commit()
        
        logger.info(f"Card deleted: {card.title} by {current_user.email}")
        
        return BaseResponse(message="Card deleted successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete card error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete card"
        )