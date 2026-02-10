"""
Notification Service.

Handles sending notifications to users via different channels.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List
from sqlmodel import create_engine, Session, select

from ..models.notification import Notification

logger = logging.getLogger(__name__)

class NotificationService:
    """Service to handle task reminder notifications."""

    def __init__(self, database_url: str):
        """Initialize the notification service."""
        self.engine = create_engine(database_url)

    def send_notification(self, user_id: str, task_id: int, title: str, due_date: str,
                         message: str, channel: str = "push") -> Notification:
        """Send a notification to the user and save to database."""

        # Create notification record
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

        # In a real implementation, this would send an actual notification
        # (email, push notification, SMS, etc.)
        # For now, we'll just log it
        logger.info(f"NOTIFICATION for user {user_id}: Task {task_id} '{title}' is due at {due_date}")
        logger.info(f"Channel: {channel}, Message: {message}")

        # Save to database
        with Session(self.engine) as session:
            session.add(notification)
            session.commit()
            session.refresh(notification)

        return notification

    def send_batch_notifications(self, notifications: List[Dict[str, Any]]) -> List[Notification]:
        """Send multiple notifications at once."""
        sent_notifications = []

        for notification_data in notifications:
            user_id = notification_data.get("user_id")
            task_id = notification_data.get("task_id")
            title = notification_data.get("title")
            due_date = notification_data.get("due_date")
            message = notification_data.get("message", f"Task '{title}' is due soon!")
            channel = notification_data.get("channel", "push")

            notification = self.send_notification(user_id, task_id, title, due_date, message, channel)
            sent_notifications.append(notification)

        return sent_notifications

    def get_pending_notifications(self) -> List[Notification]:
        """Get all pending notifications."""
        with Session(self.engine) as session:
            statement = select(Notification).where(Notification.status == "pending")
            pending_notifications = session.exec(statement).all()
            return pending_notifications

    def get_failed_notifications(self) -> List[Notification]:
        """Get all failed notifications."""
        with Session(self.engine) as session:
            statement = select(Notification).where(Notification.status == "failed")
            failed_notifications = session.exec(statement).all()
            return failed_notifications

    def retry_failed_notifications(self) -> int:
        """Retry sending failed notifications."""
        failed_notifications = self.get_failed_notifications()
        retry_count = 0

        for notification in failed_notifications:
            if notification.delivery_attempts < 3:  # Max 3 attempts
                # In a real implementation, this would retry sending the notification
                logger.info(f"Retrying notification {notification.id}")

                # Update delivery attempt count
                with Session(self.engine) as session:
                    notification.delivery_attempts += 1
                    session.add(notification)
                    session.commit()

                retry_count += 1
            else:
                logger.warning(f"Max attempts reached for notification {notification.id}, moving to dead letter queue")

        return retry_count

    def record_delivery_failure(self, notification_id: int, error_details: str) -> Notification:
        """Record a notification delivery failure."""
        with Session(self.engine) as session:
            notification = session.get(Notification, notification_id)

            if notification:
                notification.status = "failed"
                notification.delivery_attempts += 1
                session.add(notification)
                session.commit()
                session.refresh(notification)

                logger.error(f"Notification {notification_id} failed: {error_details}")

                return notification
            else:
                logger.error(f"Notification {notification_id} not found")
                return None