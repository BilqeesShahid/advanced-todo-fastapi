"""
Metrics Collection for Notification Service.

Provides metrics for reminder sent and processing.
"""

import time
from typing import Dict, Any, Callable
from collections import defaultdict
from datetime import datetime, timedelta
import threading

class MetricsCollector:
    """Collects and manages metrics for the notification service."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = defaultdict(int)
        self.timers = defaultdict(float)
        self.lock = threading.Lock()

        # Initialize counters
        self.metrics["reminders_sent_total"] = 0
        self.metrics["notifications_delivered_total"] = 0
        self.metrics["notifications_failed_total"] = 0
        self.metrics["retry_attempts_total"] = 0

    def increment_counter(self, metric_name: str, value: int = 1):
        """Increment a counter metric."""
        with self.lock:
            self.metrics[metric_name] += value

    def record_timer(self, metric_name: str, duration: float):
        """Record a timing metric."""
        with self.lock:
            self.timers[metric_name] += duration

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics values."""
        with self.lock:
            return {
                "counters": dict(self.metrics),
                "timers": dict(self.timers),
                "timestamp": datetime.utcnow().isoformat()
            }

    def reminder_sent(self):
        """Record that a reminder was sent."""
        self.increment_counter("reminders_sent_total")

    def notification_delivered(self):
        """Record that a notification was successfully delivered."""
        self.increment_counter("notifications_delivered_total")

    def notification_failed(self):
        """Record that a notification failed to deliver."""
        self.increment_counter("notifications_failed_total")

    def retry_attempt(self):
        """Record that a retry attempt was made."""
        self.increment_counter("retry_attempts_total")

    def time_operation(self, metric_name: str) -> Callable:
        """Context manager to time an operation."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    self.record_timer(metric_name, duration)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self.record_timer(metric_name, duration)
                    raise e
            return wrapper
        return decorator


# Global metrics instance
metrics_collector = MetricsCollector()


def get_reminders_sent():
    """Get the count of reminders sent."""
    return metrics_collector.metrics["reminders_sent_total"]


def get_notifications_delivered():
    """Get the count of notifications delivered."""
    return metrics_collector.metrics["notifications_delivered_total"]


def get_notifications_failed():
    """Get the count of notifications failed."""
    return metrics_collector.metrics["notifications_failed_total"]


def get_retry_attempts():
    """Get the count of retry attempts."""
    return metrics_collector.metrics["retry_attempts_total"]