"""
Logging Utility for Services.

Provides structured logging with appropriate levels and formats.
"""

import logging
import sys
from typing import Optional
from datetime import datetime
import json


class StructuredLogger:
    """Structured logger for services."""

    def __init__(self, name: str, level: int = logging.INFO):
        """
        Initialize structured logger.

        Args:
            name: Logger name
            level: Logging level
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Prevent adding handlers multiple times
        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """Set up logging handlers."""
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)

        self.logger.addHandler(console_handler)

    def _log_structured(self, level: int, message: str, **kwargs):
        """
        Log a structured message.

        Args:
            level: Logging level
            message: Log message
            **kwargs: Additional structured data
        """
        if self.logger.isEnabledFor(level):
            # Add timestamp and service info
            log_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": logging.getLevelName(level),
                "message": message,
                "service": self.logger.name
            }
            log_data.update(kwargs)

            # Log as JSON string
            self.logger.log(level, json.dumps(log_data))

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log_structured(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log_structured(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log_structured(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log_structured(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log_structured(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        if self.logger.isEnabledFor(logging.ERROR):
            log_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "ERROR",
                "message": message,
                "service": self.logger.name,
                "exception": True
            }
            log_data.update(kwargs)

            self.logger.exception(json.dumps(log_data))


# Create loggers for different services
recurring_task_logger = StructuredLogger("recurring-task-service")
notification_logger = StructuredLogger("notification-service")
websocket_logger = StructuredLogger("websocket-service")


def get_logger(service_name: str) -> StructuredLogger:
    """
    Get a logger for the specified service.

    Args:
        service_name: Name of the service

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(service_name)