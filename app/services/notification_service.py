"""
Notification Service

Consumes reminder events from Kafka and sends notifications to users.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pytz

# Import dapr if available, otherwise provide fallback
try:
    import dapr.clients
    from dapr.clients import DaprClient
    DAPR_AVAILABLE = True
except ImportError:
    DAPR_AVAILABLE = False
    DaprClient = None

from sqlmodel import create_engine, Session, select
from app.models.task import Task

logger = logging.getLogger(__name__)

class NotificationService:
    """Service to handle task reminder notifications."""

    def __init__(self, database_url: str):
        """Initialize the notification service."""
        self.engine = create_engine(database_url)
        self.dapr_available = DAPR_AVAILABLE

        if not self.dapr_available:
            logger.warning("Dapr not available. Running in development mode without Dapr integration.")

    def send_notification(self, user_id: str, task_id: int, title: str, due_date: str, message: str):
        """Send a notification to the user."""
        # In a real implementation, this would send an actual notification
        # (email, push notification, SMS, etc.)
        # For now, we'll just log it
        logger.info(f"NOTIFICATION for user {user_id}: Task {task_id} '{title}' is due at {due_date}")
        logger.info(f"Message: {message}")

    def process_reminder_event(self, event_data: Dict[str, Any]) -> bool:
        """Process a reminder event and send notification."""
        try:
            task_id = event_data.get("task_id")
            user_id = event_data.get("user_id")
            due_date = event_data.get("due_date")
            title = event_data.get("title")

            if not all([task_id, user_id, title]):
                logger.error("Missing required fields in reminder event data")
                return False

            # Verify task exists
            with Session(self.engine) as session:
                statement = select(Task).where(Task.id == task_id, Task.user_id == user_id)
                task = session.exec(statement).first()

                if not task:
                    logger.error(f"Task {task_id} not found for user {user_id}")
                    return False

                # Check if task is not already completed
                if task.completed:
                    logger.info(f"Task {task_id} is already completed, skipping notification")
                    return True

            # Send notification
            message = f"Reminder: Task '{title}' is due soon!"
            if due_date:
                message = f"Reminder: Task '{title}' is due at {due_date}"

            self.send_notification(user_id, task_id, title, due_date, message)

            # In production, publish an event for the notification sent
            if self.dapr_available:
                try:
                    with DaprClient() as client:
                        notification_event = {
                            "task_id": task_id,
                            "user_id": user_id,
                            "timestamp": datetime.utcnow().isoformat(),
                            "status": "sent"
                        }

                        client.publish_event(
                            pubsub_name="task-pubsub",
                            topic_name="notifications",
                            data={"event_id": f"notification_{task_id}", "type": "notification.sent", "data": notification_event},
                            data_content_type="application/json"
                        )
                except Exception as e:
                    logger.error(f"Failed to publish notification.sent event: {str(e)}")

            return True

        except Exception as e:
            logger.error(f"Error processing reminder event: {str(e)}")
            return False

    async def start_consumer(self):
        """Start consuming reminder events from Kafka via Dapr."""
        if not self.dapr_available:
            logger.info("Dapr not available - running in development mode without Kafka consumption")
            return

        logger.info("Starting notification service consumer...")

        while True:
            try:
                # In a real implementation, this would connect to Kafka via Dapr
                # For now, we'll simulate event consumption
                with DaprClient() as client:
                    # Subscribe to reminders topic and listen for reminder events
                    # This is a simplified version - in reality you'd need to implement
                    # proper event subscription and processing
                    pass

            except Exception as e:
                logger.error(f"Error in notification consumer: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying

    def run_dev_mode(self):
        """Run in development mode without Dapr/Kafka."""
        logger.info("Running notification service in development mode...")
        # In development mode, you might have a different mechanism to trigger
        # the sending of notifications, like a periodic check or manual triggers
        pass