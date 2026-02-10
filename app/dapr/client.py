"""Dapr client for interacting with Dapr sidecar."""
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import logging

# Import dapr if available, otherwise provide fallback
try:
    import dapr.clients
    from dapr.clients import DaprClient
    DAPR_AVAILABLE = True
except ImportError:
    DAPR_AVAILABLE = False
    DaprClient = None

logger = logging.getLogger(__name__)


class DaprEventPublisher:
    """Publishes events to Kafka via Dapr pub/sub."""

    def __init__(self):
        """Initialize Dapr event publisher."""
        self.dapr_available = DAPR_AVAILABLE
        if not self.dapr_available:
            logger.warning("Dapr not available. Running in development mode without Dapr integration.")

    def publish_event(self, topic: str, event_type: str, data: Dict[str, Any], source: str = "todo-chat-api"):
        """Publish an event to a Kafka topic via Dapr pub/sub."""
        if not self.dapr_available:
            # Development mode: log the event instead of publishing
            logger.info(f"[DEV MODE] Would publish to topic '{topic}': {event_type} from {source} with data {data}")
            return {"success": True, "message": "Event logged in dev mode"}

        try:
            # Create event envelope
            event_envelope = {
                "event_id": str(uuid.uuid4()),
                "type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "source": source,
                "data": data
            }

            # Publish via Dapr
            import json
            with DaprClient() as client:
                client.publish_event(
                    pubsub_name="task-pubsub",  # Defined in Dapr component
                    topic_name=topic,
                    data=json.dumps(event_envelope),  # Serialize the data to JSON string
                    data_content_type="application/json"
                )

            logger.info(f"Published event {event_type} to topic {topic}")
            return {"success": True, "event_id": event_envelope["event_id"]}

        except Exception as e:
            logger.error(f"Failed to publish event to topic {topic}: {str(e)}")
            raise

    def publish_task_created(self, task_data: Dict[str, Any]):
        """Publish task.created event."""
        return self.publish_event(
            topic="task-events",
            event_type="task.created",
            data=task_data
        )

    def publish_task_updated(self, task_data: Dict[str, Any]):
        """Publish task.updated event."""
        return self.publish_event(
            topic="task-events",
            event_type="task.updated",
            data=task_data
        )

    def publish_task_completed(self, task_data: Dict[str, Any]):
        """Publish task.completed event."""
        return self.publish_event(
            topic="task-events",
            event_type="task.completed",
            data=task_data
        )

    def publish_task_deleted(self, task_data: Dict[str, Any]):
        """Publish task.deleted event."""
        return self.publish_event(
            topic="task-events",
            event_type="task.deleted",
            data=task_data
        )

    def publish_reminder_scheduled(self, reminder_data: Dict[str, Any]):
        """Publish task.due_scheduled event."""
        return self.publish_event(
            topic="reminders",
            event_type="task.due_scheduled",
            data=reminder_data
        )


# Global instance
dapr_publisher = DaprEventPublisher()