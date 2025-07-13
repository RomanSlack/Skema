"""
AI command endpoints
"""
import logging
import time
import tempfile
import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_, desc, func
import openai

from app.config import settings
from app.core.auth import get_current_user
from app.database import get_session
from app.models.ai import AICommand
from app.models.user import User
from app.schemas.ai import (
    AICommandCreate, AICommandResponse, AISuggestionResponse,
    AICommandFilter, AICommandStats, AIConversationRequest, AIConversationResponse
)
from app.schemas.common import BaseResponse, PaginatedResponse
from app.core.ai_conversation import ai_conversation_handler

router = APIRouter()
logger = logging.getLogger(__name__)


async def process_ai_command(command: str, context_type: Optional[str] = None, context_id: Optional[UUID] = None) -> tuple[str, dict]:
    """
    Process an AI command and return response.
    
    This is a simplified implementation. In a real application, you would:
    1. Integrate with OpenAI or another AI service
    2. Implement intent recognition
    3. Execute context-aware actions
    4. Return structured responses
    
    Args:
        command: The AI command text
        context_type: Context type (board, card, calendar, journal, general)
        context_id: Context ID
        
    Returns:
        tuple[str, dict]: Response text and metadata
    """
    try:
        # Simulate AI processing time
        await asyncio.sleep(0.1)
        
        # Simple command processing (replace with actual AI integration)
        command_lower = command.lower()
        
        if "create" in command_lower:
            if context_type == "board":
                response = "I can help you create a new board. What would you like to name it?"
            elif context_type == "card":
                response = "I can help you create a new card. What should the card title be?"
            elif context_type == "calendar":
                response = "I can help you create a calendar event. When would you like to schedule it?"
            elif context_type == "journal":
                response = "I can help you create a journal entry. What would you like to write about?"
            else:
                response = "I can help you create something. What would you like to create?"
        
        elif "list" in command_lower or "show" in command_lower:
            if context_type == "board":
                response = "Here are your boards. Would you like me to show details for a specific board?"
            elif context_type == "calendar":
                response = "Here are your upcoming events. Would you like me to show events for a specific date?"
            else:
                response = "I can show you various items. What would you like to see?"
        
        elif "summary" in command_lower or "summarize" in command_lower:
            response = "I can provide a summary of your data. What would you like me to summarize?"
        
        elif "help" in command_lower:
            response = """I can help you with:
            - Creating boards, cards, calendar events, and journal entries
            - Listing and organizing your content
            - Providing summaries and insights
            - Searching through your data
            
            Just tell me what you'd like to do!"""
        
        else:
            response = f"I understand you want to: {command}. I'm processing this request and will help you accomplish this task."
        
        metadata = {
            "model": settings.ai_model,
            "tokens_used": len(command.split()) + len(response.split()),
            "intent": "create" if "create" in command_lower else "query",
            "confidence": 0.85,
            "source": "command_bar"
        }
        
        return response, metadata
    
    except Exception as e:
        logger.error(f"AI command processing error: {e}")
        raise


@router.post("/command", response_model=AICommandResponse)
async def execute_ai_command(
    command_data: AICommandCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Execute an AI command.
    
    Args:
        command_data: AI command data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        AICommandResponse: AI command result
    """
    try:
        start_time = time.time()
        
        # Process the AI command
        try:
            response_text, metadata = await process_ai_command(
                command_data.command,
                command_data.context_type,
                command_data.context_id
            )
            success = True
            error_message = None
        except Exception as e:
            response_text = None
            metadata = {
                "model": settings.ai_model,
                "tokens_used": 0,
                "intent": None,
                "confidence": 0.0,
                "source": "command_bar"
            }
            success = False
            error_message = str(e)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Save command to database
        ai_command = AICommand(
            user_id=current_user.id,
            command=command_data.command,
            response=response_text,
            context_type=command_data.context_type,
            context_id=command_data.context_id,
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message,
            meta_data=metadata
        )
        
        session.add(ai_command)
        await session.commit()
        await session.refresh(ai_command)
        
        logger.info(f"AI command executed by {current_user.email}: {command_data.command[:50]}...")
        
        return AICommandResponse.from_orm(ai_command)
    
    except Exception as e:
        logger.error(f"Execute AI command error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute AI command"
        )


@router.get("/history", response_model=PaginatedResponse[AICommandResponse])
async def get_ai_command_history(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    context_type: Optional[str] = Query(None, description="Filter by context type"),
    context_id: Optional[UUID] = Query(None, description="Filter by context ID"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    start_date: Optional[datetime] = Query(None, description="Filter start date"),
    end_date: Optional[datetime] = Query(None, description="Filter end date"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get AI command history with filtering and pagination.
    
    Args:
        page: Page number
        size: Page size
        context_type: Filter by context type
        context_id: Filter by context ID
        success: Filter by success status
        start_date: Filter commands after this date
        end_date: Filter commands before this date
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        PaginatedResponse[AICommandResponse]: Paginated AI command history
    """
    try:
        # Build query
        query = select(AICommand).where(AICommand.user_id == current_user.id)
        
        # Apply filters
        if context_type:
            query = query.where(AICommand.context_type == context_type)
        if context_id:
            query = query.where(AICommand.context_id == context_id)
        if success is not None:
            query = query.where(AICommand.success == success)
        if start_date:
            query = query.where(AICommand.created_at >= start_date)
        if end_date:
            query = query.where(AICommand.created_at <= end_date)
        
        # Get total count
        count_query = select(AICommand).where(AICommand.user_id == current_user.id)
        if context_type:
            count_query = count_query.where(AICommand.context_type == context_type)
        if context_id:
            count_query = count_query.where(AICommand.context_id == context_id)
        if success is not None:
            count_query = count_query.where(AICommand.success == success)
        if start_date:
            count_query = count_query.where(AICommand.created_at >= start_date)
        if end_date:
            count_query = count_query.where(AICommand.created_at <= end_date)
        
        total_result = await session.exec(count_query)
        total = len(total_result.all())
        
        # Get paginated results
        query = query.order_by(desc(AICommand.created_at)).offset((page - 1) * size).limit(size)
        result = await session.exec(query)
        commands = result.all()
        
        command_responses = [AICommandResponse.from_orm(command) for command in commands]
        
        return PaginatedResponse.create(
            items=command_responses,
            total=total,
            page=page,
            size=size
        )
    
    except Exception as e:
        logger.error(f"Get AI command history error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve AI command history"
        )


@router.get("/suggestions", response_model=AISuggestionResponse)
async def get_ai_suggestions(
    context_type: Optional[str] = Query(None, description="Context type for suggestions"),
    context_id: Optional[UUID] = Query(None, description="Context ID for suggestions"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get AI suggestions based on context.
    
    Args:
        context_type: Context type
        context_id: Context ID
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        AISuggestionResponse: AI suggestions
    """
    try:
        # Generate context-aware suggestions
        suggestions = []
        
        if context_type == "board":
            suggestions = [
                "Create a new card for this board",
                "Archive completed cards",
                "Add priority labels to cards",
                "Set up board automation rules",
                "Export board to CSV"
            ]
        elif context_type == "card":
            suggestions = [
                "Add a due date to this card",
                "Break this card into subtasks",
                "Assign this card to someone",
                "Add time tracking",
                "Move to different status"
            ]
        elif context_type == "calendar":
            suggestions = [
                "Schedule a recurring meeting",
                "Set up event reminders",
                "Block time for focused work",
                "Create a daily standup",
                "Plan weekly review session"
            ]
        elif context_type == "journal":
            suggestions = [
                "Start a gratitude entry",
                "Write about today's achievements",
                "Reflect on challenges faced",
                "Set goals for tomorrow",
                "Track mood patterns"
            ]
        else:
            # General suggestions
            suggestions = [
                "Show me my recent activity",
                "What tasks are due soon?",
                "Create a new project board",
                "Schedule a break in my calendar",
                "Write a quick journal entry"
            ]
        
        return AISuggestionResponse(
            suggestions=suggestions,
            context_type=context_type,
            context_id=context_id
        )
    
    except Exception as e:
        logger.error(f"Get AI suggestions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve AI suggestions"
        )


@router.get("/stats", response_model=AICommandStats)
async def get_ai_command_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get AI command statistics for the current user.
    
    Args:
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        AICommandStats: AI command statistics
    """
    try:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Total commands
        total_query = select(func.count(AICommand.id)).where(AICommand.user_id == current_user.id)
        total_result = await session.exec(total_query)
        total_commands = total_result.first() or 0
        
        # Successful commands
        success_query = select(func.count(AICommand.id)).where(
            and_(
                AICommand.user_id == current_user.id,
                AICommand.success == True
            )
        )
        success_result = await session.exec(success_query)
        successful_commands = success_result.first() or 0
        
        # Failed commands
        failed_commands = total_commands - successful_commands
        
        # Success rate
        success_rate = (successful_commands / total_commands * 100) if total_commands > 0 else 0
        
        # Average execution time
        exec_time_query = select(func.avg(AICommand.execution_time_ms)).where(
            and_(
                AICommand.user_id == current_user.id,
                AICommand.success == True
            )
        )
        exec_time_result = await session.exec(exec_time_query)
        average_execution_time = exec_time_result.first() or 0
        
        # Most common context
        context_query = select(AICommand.context_type, func.count(AICommand.id).label('count')).where(
            AICommand.user_id == current_user.id
        ).group_by(AICommand.context_type).order_by(desc('count')).limit(1)
        
        context_result = await session.exec(context_query)
        most_common_context_row = context_result.first()
        most_common_context = most_common_context_row[0] if most_common_context_row else None
        
        # Commands today
        today_query = select(func.count(AICommand.id)).where(
            and_(
                AICommand.user_id == current_user.id,
                AICommand.created_at >= today_start
            )
        )
        today_result = await session.exec(today_query)
        commands_today = today_result.first() or 0
        
        # Commands this week
        week_query = select(func.count(AICommand.id)).where(
            and_(
                AICommand.user_id == current_user.id,
                AICommand.created_at >= week_start
            )
        )
        week_result = await session.exec(week_query)
        commands_this_week = week_result.first() or 0
        
        return AICommandStats(
            total_commands=total_commands,
            successful_commands=successful_commands,
            failed_commands=failed_commands,
            success_rate=round(success_rate, 2),
            average_execution_time=round(average_execution_time or 0, 2),
            most_common_context=most_common_context,
            commands_today=commands_today,
            commands_this_week=commands_this_week
        )
    
    except Exception as e:
        logger.error(f"Get AI command stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve AI command statistics"
        )


# We need to import asyncio for the sleep function
import asyncio


@router.post("/conversation", response_model=AIConversationResponse)
async def ai_conversation(
    request: AIConversationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Process AI conversation with natural language understanding and tool calling.
    
    Args:
        request: AI conversation request
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        AIConversationResponse: AI conversation response
    """
    try:
        start_time = time.time()
        
        # Process the conversation
        result = await ai_conversation_handler.process_message(
            request.message,
            current_user,
            session,
            request.conversation_history
        )
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Save conversation to database
        ai_command = AICommand(
            user_id=current_user.id,
            command=request.message,
            response=result.get("response"),
            context_type="conversation",
            context_id=None,
            execution_time_ms=execution_time_ms,
            success=result.get("success", False),
            error_message=result.get("error"),
            meta_data=result.get("metadata", {})
        )
        
        session.add(ai_command)
        await session.commit()
        await session.refresh(ai_command)
        
        logger.info(f"AI conversation processed for {current_user.email}: {request.message[:50]}...")
        
        return AIConversationResponse(
            response=result.get("response", ""),
            tool_calls=result.get("tool_calls", []),
            success=result.get("success", False),
            error=result.get("error"),
            metadata=result.get("metadata", {}),
            execution_time_ms=execution_time_ms
        )
        
    except Exception as e:
        logger.error(f"AI conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process AI conversation"
        )


@router.get("/suggestions/quick", response_model=List[str])
async def get_quick_suggestions(
    current_user: User = Depends(get_current_user)
):
    """
    Get quick suggestion prompts for the AI conversation.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        List[str]: Quick suggestion prompts
    """
    try:
        suggestions = await ai_conversation_handler.get_quick_suggestions(current_user)
        return suggestions
        
    except Exception as e:
        logger.error(f"Get quick suggestions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get quick suggestions"
        )


@router.post("/transcribe", response_model=dict)
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Transcribe audio file using OpenAI Whisper API.
    
    Args:
        audio_file: Audio file to transcribe
        current_user: Current authenticated user
        
    Returns:
        dict: Transcription result with text
    """
    try:
        start_time = time.time()
        
        # Validate file type
        if not audio_file.content_type or not audio_file.content_type.startswith('audio/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an audio file"
            )
        
        # Create temporary file to store audio
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_file:
            # Read and write audio content
            content = await audio_file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=settings.openai_api_key)
            
            # Transcribe using Whisper
            with open(temp_file_path, 'rb') as audio_file_handle:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file_handle,
                    response_format="text"
                )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(f"Audio transcribed for {current_user.email} in {execution_time_ms}ms")
            
            return {
                "transcript": transcript.strip(),
                "execution_time_ms": execution_time_ms,
                "success": True
            }
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio transcription error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to transcribe audio"
        )