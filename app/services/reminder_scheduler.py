"""Reminder Scheduler Service."""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlmodel import Session, select
from app.models.task import Task
from app.dapr.client import dapr_publisher


class ReminderScheduler:
    """Service for scheduling task reminders."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def schedule_reminders_for_task(self, task: Task) -> bool:
        """
        Schedule reminders for a task based on due date.

        Args:
            task: Task object with due date

        Returns:
            True if reminder scheduled, False otherwise
        """
        if not task.due_date:
            return False

        # Create reminder event
        reminder_data = {
            "task_id": task.id,
            "user_id": task.user_id,
            "due_date": task.due_date.isoformat(),
            "title": task.title,
            "priority": task.priority
        }

        # Publish reminder event
        try:
            dapr_publisher.publish_reminder_scheduled(reminder_data)
            return True
        except Exception as e:
            print(f"Failed to schedule reminder for task {task.id}: {str(e)}")
            return False

    def get_upcoming_reminders(self, minutes_ahead: int = 5) -> List[Dict[str, Any]]:
        """
        Get tasks with due dates coming up in the next specified minutes.

        Args:
            minutes_ahead: Number of minutes ahead to check for due tasks

        Returns:
            List of task dictionaries with upcoming due dates
        """
        now = datetime.utcnow()
        target_time = now + timedelta(minutes=minutes_ahead)

        # Query for tasks with due dates in the specified range
        statement = select(Task).where(
            Task.due_date <= target_time,
            Task.due_date >= now,
            Task.completed == False
        )
        tasks = self.db.exec(statement).all()

        reminder_tasks = []
        for task in tasks:
            reminder_tasks.append({
                "task_id": task.id,
                "user_id": task.user_id,
                "title": task.title,
                "due_date": task.due_date,
                "priority": task.priority,
                "description": task.description
            })

        return reminder_tasks

    def schedule_periodic_reminders(self, hours_before_due: int = 24) -> int:
        """
        Schedule periodic reminders for tasks (e.g., 24 hours before due date).

        Args:
            hours_before_due: Number of hours before due date to send reminder

        Returns:
            Number of reminders scheduled
        """
        now = datetime.utcnow()
        target_time = now + timedelta(hours=hours_before_due)

        # Query for tasks with due dates at the target time
        statement = select(Task).where(
            Task.due_date <= target_time,
            Task.due_date >= now,
            Task.completed == False
        )
        tasks = self.db.exec(statement).all()

        scheduled_count = 0
        for task in tasks:
            if self.schedule_reminders_for_task(task):
                scheduled_count += 1

        return scheduled_count

    def validate_reminder_request(self, task_id: int, user_id: str, due_date: str) -> Dict[str, Any]:
        """
        Validate a reminder scheduling request.

        Args:
            task_id: ID of task to remind about
            user_id: User ID
            due_date: Due date string

        Returns:
            Dict with validation result
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Check if task exists and belongs to user
        statement = select(Task).where(Task.id == task_id, Task.user_id == user_id)
        task = self.db.exec(statement).first()

        if not task:
            result["valid"] = False
            result["errors"].append(f"Task {task_id} not found for user {user_id}")
            return result

        # Check if task is already completed
        if task.completed:
            result["warnings"].append(f"Task {task_id} is already completed")

        # Validate due date format
        try:
            datetime.fromisoformat(due_date.replace('Z', '+00:00'))
        except ValueError:
            result["valid"] = False
            result["errors"].append(f"Invalid due date format: {due_date}")

        return result