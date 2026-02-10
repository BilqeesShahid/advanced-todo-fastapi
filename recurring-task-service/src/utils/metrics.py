"""
Metrics Collection for Recurring Task Service.

Provides metrics for recurring task creation and processing.
"""

import time
from typing import Dict, Any, Callable
from collections import defaultdict
from datetime import datetime, timedelta
import threading

class MetricsCollector:
    """Collects and manages metrics for the recurring task service."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = defaultdict(int)
        self.timers = defaultdict(float)
        self.lock = threading.Lock()

        # Initialize counters
        self.metrics["recurring_tasks_created_total"] = 0
        self.metrics["recurring_tasks_processed_total"] = 0
        self.metrics["recurring_tasks_errors_total"] = 0

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

    def recurring_task_created(self):
        """Record that a recurring task was created."""
        self.increment_counter("recurring_tasks_created_total")

    def recurring_task_processed(self):
        """Record that a recurring task was processed."""
        self.increment_counter("recurring_tasks_processed_total")

    def recurring_task_error(self):
        """Record that an error occurred processing a recurring task."""
        self.increment_counter("recurring_tasks_errors_total")

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


def get_recurring_tasks_created():
    """Get the count of recurring tasks created."""
    return metrics_collector.metrics["recurring_tasks_created_total"]


def get_recurring_tasks_processed():
    """Get the count of recurring tasks processed."""
    return metrics_collector.metrics["recurring_tasks_processed_total"]


def get_recurring_tasks_errors():
    """Get the count of recurring task errors."""
    return metrics_collector.metrics["recurring_tasks_errors_total"]