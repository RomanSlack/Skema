"""
WebSocket support for real-time updates
"""
import json
import logging
from typing import Dict, List, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates
    """
    
    def __init__(self):
        # Store active connections by user ID
        self.active_connections: Dict[UUID, Set[WebSocket]] = {}
        # Store connections by board ID for board-specific updates
        self.board_connections: Dict[UUID, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: UUID):
        """
        Accept a new WebSocket connection for a user
        
        Args:
            websocket: WebSocket connection
            user_id: User ID
        """
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected via WebSocket")
    
    def disconnect(self, websocket: WebSocket, user_id: UUID):
        """
        Remove a WebSocket connection for a user
        
        Args:
            websocket: WebSocket connection
            user_id: User ID
        """
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # Remove user entry if no connections left
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remove from board connections
        for board_id in list(self.board_connections.keys()):
            self.board_connections[board_id].discard(websocket)
            if not self.board_connections[board_id]:
                del self.board_connections[board_id]
        
        logger.info(f"User {user_id} disconnected from WebSocket")
    
    def subscribe_to_board(self, websocket: WebSocket, board_id: UUID):
        """
        Subscribe a WebSocket connection to board updates
        
        Args:
            websocket: WebSocket connection
            board_id: Board ID
        """
        if board_id not in self.board_connections:
            self.board_connections[board_id] = set()
        
        self.board_connections[board_id].add(websocket)
        logger.info(f"WebSocket subscribed to board {board_id}")
    
    def unsubscribe_from_board(self, websocket: WebSocket, board_id: UUID):
        """
        Unsubscribe a WebSocket connection from board updates
        
        Args:
            websocket: WebSocket connection
            board_id: Board ID
        """
        if board_id in self.board_connections:
            self.board_connections[board_id].discard(websocket)
            
            if not self.board_connections[board_id]:
                del self.board_connections[board_id]
        
        logger.info(f"WebSocket unsubscribed from board {board_id}")
    
    async def send_personal_message(self, message: dict, user_id: UUID):
        """
        Send a message to all connections for a specific user
        
        Args:
            message: Message to send
            user_id: User ID
        """
        if user_id not in self.active_connections:
            return
        
        message_text = json.dumps(message)
        connections_to_remove = set()
        
        for websocket in self.active_connections[user_id].copy():
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message_text)
                else:
                    connections_to_remove.add(websocket)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                connections_to_remove.add(websocket)
        
        # Remove failed connections
        for websocket in connections_to_remove:
            self.active_connections[user_id].discard(websocket)
    
    async def send_board_message(self, message: dict, board_id: UUID):
        """
        Send a message to all connections subscribed to a board
        
        Args:
            message: Message to send
            board_id: Board ID
        """
        if board_id not in self.board_connections:
            return
        
        message_text = json.dumps(message)
        connections_to_remove = set()
        
        for websocket in self.board_connections[board_id].copy():
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message_text)
                else:
                    connections_to_remove.add(websocket)
            except Exception as e:
                logger.error(f"Error sending message to board {board_id}: {e}")
                connections_to_remove.add(websocket)
        
        # Remove failed connections
        for websocket in connections_to_remove:
            self.board_connections[board_id].discard(websocket)
    
    async def broadcast(self, message: dict):
        """
        Broadcast a message to all active connections
        
        Args:
            message: Message to broadcast
        """
        message_text = json.dumps(message)
        
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)
    
    def get_user_connection_count(self, user_id: UUID) -> int:
        """
        Get the number of active connections for a user
        
        Args:
            user_id: User ID
            
        Returns:
            int: Number of active connections
        """
        return len(self.active_connections.get(user_id, set()))
    
    def get_board_connection_count(self, board_id: UUID) -> int:
        """
        Get the number of active connections for a board
        
        Args:
            board_id: Board ID
            
        Returns:
            int: Number of active connections
        """
        return len(self.board_connections.get(board_id, set()))


# Global connection manager instance
manager = ConnectionManager()


async def handle_websocket_message(websocket: WebSocket, user_id: UUID, message: dict):
    """
    Handle incoming WebSocket messages
    
    Args:
        websocket: WebSocket connection
        user_id: User ID
        message: Received message
    """
    try:
        message_type = message.get("type")
        
        if message_type == "subscribe_board":
            board_id = message.get("board_id")
            if board_id:
                manager.subscribe_to_board(websocket, UUID(board_id))
                await websocket.send_text(json.dumps({
                    "type": "subscribed",
                    "board_id": board_id
                }))
        
        elif message_type == "unsubscribe_board":
            board_id = message.get("board_id")
            if board_id:
                manager.unsubscribe_from_board(websocket, UUID(board_id))
                await websocket.send_text(json.dumps({
                    "type": "unsubscribed",
                    "board_id": board_id
                }))
        
        elif message_type == "ping":
            await websocket.send_text(json.dumps({
                "type": "pong",
                "timestamp": message.get("timestamp")
            }))
        
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")


# Event types for real-time updates
class WebSocketEvents:
    """WebSocket event types"""
    
    # Board events
    BOARD_CREATED = "board_created"
    BOARD_UPDATED = "board_updated"
    BOARD_DELETED = "board_deleted"
    
    # Card events
    CARD_CREATED = "card_created"
    CARD_UPDATED = "card_updated"
    CARD_MOVED = "card_moved"
    CARD_DELETED = "card_deleted"
    
    # Calendar events
    CALENDAR_EVENT_CREATED = "calendar_event_created"
    CALENDAR_EVENT_UPDATED = "calendar_event_updated"
    CALENDAR_EVENT_DELETED = "calendar_event_deleted"
    
    # Journal events
    JOURNAL_ENTRY_CREATED = "journal_entry_created"
    JOURNAL_ENTRY_UPDATED = "journal_entry_updated"
    JOURNAL_ENTRY_DELETED = "journal_entry_deleted"
    
    # AI events
    AI_COMMAND_EXECUTED = "ai_command_executed"
    
    # User events
    USER_UPDATED = "user_updated"


async def notify_board_update(board_id: UUID, event_type: str, data: dict):
    """
    Notify all subscribers of a board update
    
    Args:
        board_id: Board ID
        event_type: Type of event
        data: Event data
    """
    message = {
        "type": event_type,
        "board_id": str(board_id),
        "data": data,
        "timestamp": json.dumps(json.datetime.now().isoformat())
    }
    
    await manager.send_board_message(message, board_id)


async def notify_user_update(user_id: UUID, event_type: str, data: dict):
    """
    Notify a user of an update
    
    Args:
        user_id: User ID
        event_type: Type of event
        data: Event data
    """
    message = {
        "type": event_type,
        "data": data,
        "timestamp": json.dumps(json.datetime.now().isoformat())
    }
    
    await manager.send_personal_message(message, user_id)


# Fix the datetime import issue
import datetime

async def notify_board_update(board_id: UUID, event_type: str, data: dict):
    """
    Notify all subscribers of a board update
    
    Args:
        board_id: Board ID
        event_type: Type of event
        data: Event data
    """
    message = {
        "type": event_type,
        "board_id": str(board_id),
        "data": data,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    await manager.send_board_message(message, board_id)


async def notify_user_update(user_id: UUID, event_type: str, data: dict):
    """
    Notify a user of an update
    
    Args:
        user_id: User ID
        event_type: Type of event
        data: Event data
    """
    message = {
        "type": event_type,
        "data": data,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    await manager.send_personal_message(message, user_id)