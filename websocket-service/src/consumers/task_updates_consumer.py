"""
Task Updates Consumer for WebSocket Service.

Consumes task update events from Kafka and broadcasts them to WebSocket clients.
"""

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

# Import dapr if available, otherwise provide fallback
try:
    import dapr.clients
    from dapr.clients import DaprClient
    DAPR_AVAILABLE = True
except ImportError:
    DAPR_AVAILABLE = False
    DaprClient = None

from ..ws.websocket_handler import websocket_handler

logger = logging.getLogger(__name__)


class TaskUpdatesConsumer:
    """Consumer to handle task update events and broadcast to WebSocket clients."""

    def __init__(self):
        """Initialize the task updates consumer."""
        self.dapr_available = DAPR_AVAILABLE

        if not self.dapr_available:
            logger.warning("Dapr not available. Running in development mode without Dapr integration.")

    async def process_task_event(self, event_data: Dict[str, Any]) -> bool:
        """Process a task event and broadcast to WebSocket clients."""
        try:
            event_type = event_data.get("type", "")
            user_id = event_data.get("data", {}).get("user_id") or event_data.get("user_id")
            task_data = event_data.get("data", {})

            if not user_id:
                logger.error("Missing user_id in event data")
                return False

            # Route to appropriate handler based on event type
            if event_type.endswith(".created"):
                await websocket_handler.handle_new_task(task_data, user_id)
            elif event_type.endswith(".updated"):
                await websocket_handler.handle_task_update(task_data, user_id)
            elif event_type.endswith(".completed"):
                await websocket_handler.handle_task_completion(task_data, user_id)
            elif event_type == "task.created.api":
                # Special handling for API-created tasks
                await websocket_handler.handle_new_task(task_data, user_id)
            elif event_type == "task.updated.api":
                # Special handling for API-updated tasks
                await websocket_handler.handle_task_update(task_data, user_id)
            elif event_type == "task.completed.api":
                # Special handling for API-completed tasks
                await websocket_handler.handle_task_completion(task_data, user_id)
            elif event_type == "task.listed.api":
                # Broadcast that tasks were listed (could be used for UI updates)
                message = {
                    "type": "tasks_listed",
                    "data": task_data,
                    "user_id": user_id
                }
                await websocket_handler.broadcast_to_user(user_id, message)
            else:
                logger.info(f"Unknown event type: {event_type}, broadcasting as general update")
                message = {
                    "type": "task_general_update",
                    "data": task_data,
                    "user_id": user_id,
                    "event_type": event_type
                }
                await websocket_handler.broadcast_to_user(user_id, message)

            logger.info(f"Processed task event {event_type} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error processing task event: {str(e)}")
            return False

    async def start_consumer(self):
        """Start consuming task update events from Kafka via Dapr."""
        if not self.dapr_available:
            logger.info("Dapr not available - running in development mode without Kafka consumption")
            return

        logger.info("Starting task updates consumer...")

        while True:
            try:
                # In a real implementation, this would connect to Kafka via Dapr
                # For now, we'll simulate event consumption
                with DaprClient() as client:
                    # Subscribe to task-updates topic and listen for task events
                    # This is a simplified version - in reality you'd need to implement
                    # proper event subscription and processing
                    pass

            except Exception as e:
                logger.error(f"Error in task updates consumer: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying

    def run_dev_mode(self):
        """Run in development mode without Dapr/Kafka."""
        logger.info("Running task updates consumer in development mode...")
        # In development mode, you might have a different mechanism to trigger
        # the broadcasting of updates, like a mock event source or manual triggers
        pass


# Global instance
task_updates_consumer = TaskUpdatesConsumer()