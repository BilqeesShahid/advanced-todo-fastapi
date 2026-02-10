"""
Base Notification Provider.

Abstract base class for different notification channels.
"""

import abc
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class NotificationProvider(abc.ABC):
    """Abstract base class for notification providers."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize notification provider.

        Args:
            config: Configuration for the provider
        """
        self.config = config
        self.is_initialized = False

    @abc.abstractmethod
    async def send(self, recipient: str, message: str, **kwargs) -> Dict[str, Any]:
        """
        Send a notification.

        Args:
            recipient: Recipient identifier (email, phone number, device token)
            message: Message content
            **kwargs: Additional provider-specific parameters

        Returns:
            Dict with send result (success, message_id, etc.)
        """
        pass

    @abc.abstractmethod
    def validate_recipient(self, recipient: str) -> bool:
        """
        Validate recipient format.

        Args:
            recipient: Recipient identifier

        Returns:
            True if valid, False otherwise
        """
        pass

    async def initialize(self):
        """Initialize the provider (e.g., establish connections)."""
        self.is_initialized = True
        logger.info(f"{self.__class__.__name__} initialized")

    async def cleanup(self):
        """Clean up resources (e.g., close connections)."""
        self.is_initialized = False
        logger.info(f"{self.__class__.__name__} cleaned up")


class EmailProvider(NotificationProvider):
    """Email notification provider."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_host = config.get("smtp_host", "localhost")
        self.smtp_port = config.get("smtp_port", 587)
        self.sender_email = config.get("sender_email", "noreply@example.com")

    async def send(self, recipient: str, message: str, subject: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Send email notification."""
        if not self.validate_recipient(recipient):
            return {"success": False, "error": "Invalid email address"}

        if not subject:
            subject = "Task Reminder"

        # In a real implementation, this would send an actual email
        logger.info(f"Sending email to {recipient}: {subject}")
        logger.info(f"Message: {message}")

        # Simulate email sending
        return {
            "success": True,
            "message_id": f"email_{hash(recipient + message)}",
            "provider": "email"
        }

    def validate_recipient(self, recipient: str) -> bool:
        """Validate email address format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, recipient))


class PushProvider(NotificationProvider):
    """Push notification provider."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service_endpoint = config.get("service_endpoint", "https://push.example.com")

    async def send(self, recipient: str, message: str, title: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Send push notification."""
        if not self.validate_recipient(recipient):
            return {"success": False, "error": "Invalid device token"}

        if not title:
            title = "Task Reminder"

        # In a real implementation, this would send an actual push notification
        logger.info(f"Sending push notification to {recipient}: {title}")
        logger.info(f"Message: {message}")

        # Simulate push notification sending
        return {
            "success": True,
            "message_id": f"push_{hash(recipient + message)}",
            "provider": "push"
        }

    def validate_recipient(self, recipient: str) -> bool:
        """Validate device token format."""
        # Basic validation - in practice, this would depend on the push service
        return len(recipient) >= 10  # Assume device tokens are at least 10 chars


class SMSProvider(NotificationProvider):
    """SMS notification provider."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service_endpoint = config.get("service_endpoint", "https://sms.example.com")

    async def send(self, recipient: str, message: str, **kwargs) -> Dict[str, Any]:
        """Send SMS notification."""
        if not self.validate_recipient(recipient):
            return {"success": False, "error": "Invalid phone number"}

        # In a real implementation, this would send an actual SMS
        logger.info(f"Sending SMS to {recipient}")
        logger.info(f"Message: {message}")

        # Simulate SMS sending
        return {
            "success": True,
            "message_id": f"sms_{hash(recipient + message)}",
            "provider": "sms"
        }

    def validate_recipient(self, recipient: str) -> bool:
        """Validate phone number format."""
        import re
        # Basic phone number validation (allows +, digits, parentheses, hyphens, spaces)
        pattern = r'^[\+]?[1-9][\d\s\-\(\)]{7,15}$'
        return bool(re.match(pattern, recipient.strip()))