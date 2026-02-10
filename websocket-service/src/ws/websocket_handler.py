"""
WebSocket Handler for Real-Time Updates.

Handles WebSocket connections and broadcasts task updates to clients.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Any
from datetime import datetime

import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """Handler for WebSocket connections and message broadcasting."""

    def __init__(self):
        """Initialize WebSocket handler."""
        self.active_connections: Set[websockets.WebSocketServerProtocol] = set()
        self.user_connections: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}

    async def connect(self, websocket: websockets.WebSocketServerProtocol, user_id: str):
        """Connect a new WebSocket client."""
        await websocket.send(json.dumps({
            "type": "connection_established",
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Connected to WebSocket server as user {user_id}"
        }))

        # Add connection to global set
        self.active_connections.add(websocket)

        # Add to user-specific connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)

        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections)}")

        try:
            # Keep connection alive
            await websocket.wait_closed()
        except ConnectionClosed:
            logger.info(f"Connection with user {user_id} closed")
        finally:
            # Clean up on disconnect
            await self.disconnect(websocket, user_id)

    async def disconnect(self, websocket: websockets.WebSocketServerProtocol, user_id: str):
        """Disconnect a WebSocket client."""
        # Remove from global connections
        self.active_connections.discard(websocket)

        # Remove from user-specific connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:  # If no connections left for user
                del self.user_connections[user_id]

        logger.info(f"User {user_id} disconnected. Remaining connections: {len(self.active_connections)}")

    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return

        # Add timestamp to message
        message["timestamp"] = datetime.utcnow().isoformat()

        # Convert message to JSON string
        json_message = json.dumps(message)

        # Track disconnected clients
        disconnected_clients = set()

        for connection in self.active_connections:
            try:
                await connection.send(json_message)
            except ConnectionClosed:
                disconnected_clients.add(connection)
            except Exception as e:
                logger.error(f"Error sending message to client: {e}")
                disconnected_clients.add(connection)

        # Remove disconnected clients
        for client in disconnected_clients:
            self.active_connections.discard(client)

        if disconnected_clients:
            logger.info(f"Removed {len(disconnected_clients)} disconnected clients")

    async def broadcast_to_user(self, user_id: str, message: Dict[str, Any]):
        """Broadcast message to all connections for a specific user."""
        if user_id not in self.user_connections or not self.user_connections[user_id]:
            return

        # Add timestamp to message
        message["timestamp"] = datetime.utcnow().isoformat()

        # Convert message to JSON string
        json_message = json.dumps(message)

        # Track disconnected clients
        disconnected_clients = set()

        for connection in self.user_connections[user_id]:
            try:
                await connection.send(json_message)
            except ConnectionClosed:
                disconnected_clients.add(connection)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                disconnected_clients.add(connection)

        # Remove disconnected clients
        for client in disconnected_clients:
            self.user_connections[user_id].discard(client)
            self.active_connections.discard(client)

            # Clean up user entry if no connections left
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        if disconnected_clients:
            logger.info(f"Removed {disconnected_clients} disconnected clients for user {user_id}")

    async def handle_task_update(self, task_data: Dict[str, Any], user_id: str):
        """Handle task update notification."""
        message = {
            "type": "task_update",
            "data": task_data,
            "user_id": user_id,
            "action": task_data.get("action", "updated")
        }

        await self.broadcast_to_user(user_id, message)
        logger.info(f"Task update broadcast to user {user_id}: {task_data.get('task_id')}")

    async def handle_new_task(self, task_data: Dict[str, Any], user_id: str):
        """Handle new task creation notification."""
        message = {
            "type": "task_created",
            "data": task_data,
            "user_id": user_id
        }

        await self.broadcast_to_user(user_id, message)
        logger.info(f"New task notification broadcast to user {user_id}: {task_data.get('id')}")

    async def handle_task_completion(self, task_data: Dict[str, Any], user_id: str):
        """Handle task completion notification."""
        message = {
            "type": "task_completed",
            "data": task_data,
            "user_id": user_id
        }

        await self.broadcast_to_user(user_id, message)
        logger.info(f"Task completion notification broadcast to user {user_id}: {task_data.get('id')}")

    async def handle_system_message(self, message: str, user_id: str = None):
        """Handle system message broadcast."""
        msg_data = {
            "type": "system_message",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }

        if user_id:
            # Send to specific user
            await self.broadcast_to_user(user_id, msg_data)
        else:
            # Send to all users
            await self.broadcast_to_all(msg_data)

        logger.info(f"System message sent: {message}")


# Global WebSocket handler instance
websocket_handler = WebSocketHandler()