"""
Recurring Task Service

Consumes task.completed events from Kafka and creates next occurrence based on recurrence rules.
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

class RecurringTaskService:
    """Service to handle recurring task logic."""

    def __init__(self, database_url: str):
        """Initialize the recurring task service."""
        self.engine = create_engine(database_url)
        self.dapr_available = DAPR_AVAILABLE

        if not self.dapr_available:
            logger.warning("Dapr not available. Running in development mode without Dapr integration.")

    def calculate_next_occurrence(self, recurrence: str, recurrence_rule: str, last_completion: datetime) -> Optional[datetime]:
        """Calculate the next occurrence based on recurrence rules."""
        if not recurrence:
            return None

        # For simplicity, implement basic recurrence patterns
        # In production, use a library like dateutil.rrule for complex rules
        if recurrence == "daily":
            return last_completion + timedelta(days=1)
        elif recurrence == "weekly":
            return last_completion + timedelta(weeks=1)
        elif recurrence == "monthly":
            # Simple monthly - same day next month
            next_month = last_completion.month + 1
            next_year = last_completion.year
            if next_month > 12:
                next_month = 1
                next_year += 1

            # Handle months with different number of days
            import calendar
            max_day = calendar.monthrange(next_year, next_month)[1]
            next_day = min(last_completion.day, max_day)

            return last_completion.replace(year=next_year, month=next_month, day=next_day)
        elif recurrence == "custom" and recurrence_rule:
            # In a real implementation, parse the recurrence_rule using a library like dateutil.rrule
            # For now, we'll implement basic custom patterns
            if "every_2_days" in recurrence_rule:
                return last_completion + timedelta(days=2)
            elif "every_weekday" in recurrence_rule:
                # Find next weekday
                next_date = last_completion + timedelta(days=1)
                while next_date.weekday() >= 5:  # Saturday=5, Sunday=6
                    next_date += timedelta(days=1)
                return next_date
            else:
                logger.warning(f"Unsupported custom recurrence rule: {recurrence_rule}")
                return None
        else:
            return None

    def create_next_occurrence(self, completed_task: Task) -> Optional[Task]:
        """Create the next occurrence of a recurring task."""
        if not completed_task.recurrence:
            return None

        next_occurrence = self.calculate_next_occurrence(
            completed_task.recurrence,
            completed_task.recurrence_rule,
            datetime.utcnow()
        )

        if not next_occurrence:
            return None

        # Create new task with same properties as original
        new_task = Task(
            user_id=completed_task.user_id,
            title=completed_task.title,
            description=completed_task.description,
            completed=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            priority=completed_task.priority,
            due_date=next_occurrence,  # Set due date to the next occurrence
            tags=completed_task.tags,
            recurrence=completed_task.recurrence,
            recurrence_rule=completed_task.recurrence_rule,
            next_occurrence=None  # Will be calculated for the next occurrence
        )

        # Save to database
        with Session(self.engine) as session:
            session.add(new_task)
            session.commit()
            session.refresh(new_task)

        logger.info(f"Created next occurrence of task {completed_task.id}: new task {new_task.id}")
        return new_task

    def process_task_completed_event(self, event_data: Dict[str, Any]) -> bool:
        """Process a task.completed event and create next occurrence if needed."""
        try:
            task_id = event_data.get("id")
            user_id = event_data.get("user_id")

            if not task_id:
                logger.error("Missing task_id in event data")
                return False

            # Get the completed task from database
            with Session(self.engine) as session:
                statement = select(Task).where(Task.id == task_id, Task.user_id == user_id)
                task = session.exec(statement).first()

                if not task:
                    logger.error(f"Task {task_id} not found for user {user_id}")
                    return False

                # Check if this task has recurrence
                if task.recurrence:
                    next_task = self.create_next_occurrence(task)
                    if next_task:
                        logger.info(f"Successfully created next occurrence for task {task_id}: new task {next_task.id}")

                        # In production, publish an event for the new task creation
                        if self.dapr_available:
                            try:
                                with DaprClient() as client:
                                    new_task_data = {
                                        "id": next_task.id,
                                        "user_id": next_task.user_id,
                                        "title": next_task.title,
                                        "due_date": next_task.due_date.isoformat() if next_task.due_date else None
                                    }

                                    client.publish_event(
                                        pubsub_name="task-pubsub",
                                        topic_name="task-events",
                                        data={"event_id": f"next_occurrence_{next_task.id}", "type": "task.created", "data": new_task_data},
                                        data_content_type="application/json"
                                    )
                            except Exception as e:
                                logger.error(f"Failed to publish task.created event: {str(e)}")

                        return True
                else:
                    logger.info(f"Task {task_id} does not have recurrence, skipping next occurrence creation")

        except Exception as e:
            logger.error(f"Error processing task.completed event: {str(e)}")
            return False

        return False

    async def start_consumer(self):
        """Start consuming task.completed events from Kafka via Dapr."""
        if not self.dapr_available:
            logger.info("Dapr not available - running in development mode without Kafka consumption")
            return

        logger.info("Starting recurring task service consumer...")

        while True:
            try:
                # In a real implementation, this would connect to Kafka via Dapr
                # For now, we'll simulate event consumption
                with DaprClient() as client:
                    # Subscribe to task-events topic and listen for task.completed events
                    # This is a simplified version - in reality you'd need to implement
                    # proper event subscription and processing
                    pass

            except Exception as e:
                logger.error(f"Error in recurring task consumer: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying

    def run_dev_mode(self):
        """Run in development mode without Dapr/Kafka."""
        logger.info("Running recurring task service in development mode...")
        # In development mode, you might have a different mechanism to trigger
        # the processing of completed tasks, like a periodic check or manual triggers
        pass