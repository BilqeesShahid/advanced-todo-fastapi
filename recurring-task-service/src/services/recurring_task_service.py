"""
Recurring Task Service.

Handles the logic for creating next occurrences of recurring tasks.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import calendar
from sqlmodel import create_engine, Session, select

from ..models.task import Task

logger = logging.getLogger(__name__)

class RecurringTaskService:
    """Service to handle recurring task logic."""

    def __init__(self, database_url: str):
        """Initialize the recurring task service."""
        self.engine = create_engine(database_url)

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

    def prevent_duplicate_creation(self, task_id: int, recurrence: str, next_occurrence: datetime) -> bool:
        """
        Prevent duplicate task creation for the same recurrence pattern on the same day.

        Args:
            task_id: Original task ID
            recurrence: Recurrence pattern
            next_occurrence: Expected next occurrence date

        Returns:
            True if no duplicate exists, False if duplicate would be created
        """
        # Check if a task with the same title and user already exists for the same date
        with Session(self.engine) as session:
            from sqlalchemy import func
            # Look for tasks with the same user_id, title, and approximate due_date (within a day)
            stmt = select(Task).where(
                Task.user_id == task_id,
                func.date(Task.due_date) == func.date(next_occurrence)
            )

            existing_tasks = session.exec(stmt).all()

            # If there are existing tasks with similar characteristics, prevent duplicate
            for task in existing_tasks:
                if task.title == task_id and task.recurrence == recurrence:
                    logger.info(f"Duplicate prevention: Task with similar characteristics already exists for {next_occurrence}")
                    return False

        return True