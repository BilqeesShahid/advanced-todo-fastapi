"""
Reminder Consumer for Notification Service.

Consumes reminder events from Kafka and sends notifications to users.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pytz
from sqlmodel import create_engine, Session, select

# Import dapr if available, otherwise provide fallback
try:
    import dapr.clients
    from dapr.clients import DaprClient
    DAPR_AVAILABLE = True
except ImportError:
    DAPR_AVAILABLE = False
    DaprClient = None

from ..models.notification import Notification

logger = logging.getLogger(__name__)

class ReminderConsumer:
    """Consumer to handle reminder events and send notifications."""

    def __init__(self, database_url: str):
        """Initialize the reminder consumer."""
        self.engine = create_engine(database_url)
        self.dapr_available = DAPR_AVAILABLE

        if not self.dapr_available:
            logger.warning("Dapr not available. Running in development mode without Dapr integration.")

    def send_notification(self, user_id: str, task_id: int, title: str, due_date: str, message: str, channel: str = "push"):
        """Send a notification to the user."""
        # In a real implementation, this would send an actual notification
        # (email, push notification, SMS, etc.)
        # For now, we'll just log it
        logger.info(f"NOTIFICATION for user {user_id}: Task {task_id} '{title}' is due at {due_date}")
        logger.info(f"Channel: {channel}, Message: {message}")

        # Save notification record
        notification = Notification(
            task_id=task_id,
            user_id=user_id,
            scheduled_time=datetime.fromisoformat(due_date.replace('Z', '+00:00')) if due_date else datetime.utcnow(),
            sent_time=datetime.utcnow(),
            status="sent",
            delivery_attempts=1,
            channel=channel,
            message_content=message
        )

        with Session(self.engine) as session:
            session.add(notification)
            session.commit()

    def process_reminder_event(self, event_data: Dict[str, Any]) -> bool:
        """Process a reminder event and send notification."""
        try:
            task_id = event_data.get("task_id")
            user_id = event_data.get("user_id")
            due_date = event_data.get("due_date")
            title = event_data.get("title")
            priority = event_data.get("priority", "medium")
            channel = event_data.get("channel", "push")  # Default to push notification

            if not all([task_id, user_id, title]):
                logger.error("Missing required fields in reminder event data")
                return False

            # Send notification based on priority
            if priority == "high":
                message = f"🚨 HIGH PRIORITY: Task '{title}' is due soon!"
            elif priority == "low":
                message = f"↘️ Low priority reminder: Task '{title}' is due soon."
            else:
                message = f"⏰ Reminder: Task '{title}' is due soon!"

            if due_date:
                message = f"⏰ URGENT REMINDER: Task '{title}' is due at {due_date}"

            self.send_notification(user_id, task_id, title, due_date, message, channel)

            # In production, publish an event for the notification sent
            if self.dapr_available:
                try:
                    with DaprClient() as client:
                        notification_event = {
                            "task_id": task_id,
                            "user_id": user_id,
                            "timestamp": datetime.utcnow().isoformat(),
                            "status": "sent",
                            "channel": channel
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

    def handle_failed_notification(self, notification_id: int, error_details: str):
        """Handle failed notification and implement retry logic."""
        logger.error(f"Notification {notification_id} failed: {error_details}")

        # Update notification record with failure status
        with Session(self.engine) as session:
            # Get the notification
            notification = session.get(Notification, notification_id)
            if notification:
                notification.delivery_attempts += 1
                notification.status = "failed"
                session.add(notification)
                session.commit()

                # Check if we should retry
                if notification.delivery_attempts < 3:  # Retry up to 3 times
                    logger.info(f"Scheduling retry for notification {notification_id}")
                    # In a real implementation, you would schedule a retry
                else:
                    logger.warning(f"Max retries reached for notification {notification_id}")
                    # Move to dead letter queue or mark as permanently failed
                    self.move_to_dead_letter_queue(notification)

    def move_to_dead_letter_queue(self, notification: Notification):
        """Move failed notification to dead letter queue for manual processing."""
        logger.warning(f"Moving notification {notification.id} to dead letter queue")
        # In a real implementation, this would move the notification to a separate table
        # or queue for manual processing by an admin
        pass

    async def start_consumer(self):
        """Start consuming reminder events from Kafka via Dapr."""
        if not self.dapr_available:
            logger.info("Dapr not available - running in development mode without Kafka consumption")
            return

        logger.info("Starting reminder consumer...")

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
                logger.error(f"Error in reminder consumer: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying

    def run_dev_mode(self):
        """Run in development mode without Dapr/Kafka."""
        logger.info("Running reminder consumer in development mode...")
        # In development mode, you might have a different mechanism to trigger
        # the sending of notifications, like a periodic check or manual triggers
        pass