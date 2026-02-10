"""Task service for Phase V Advanced Task Management."""
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime, date
import json
import os

from app.models.task import Task

# Determine database type for compatibility
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./todo_app.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")


class TaskService:
    """Service class for advanced task CRUD operations with priorities, due dates, tags, and recurrence."""

    def __init__(self, session: Session):
        self.session = session

    def create_advanced(
        self,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        due_date: Optional[str] = None,
        tags: Optional[List[str]] = None,
        recurrence: Optional[str] = None,
        recurrence_rule: Optional[str] = None
    ) -> Task:
        """Create a new task with advanced features."""
        # Validate priority
        if priority not in ["high", "medium", "low"]:
            priority = "medium"

        # Convert due_date string to datetime if provided
        due_datetime = None
        if due_date:
            try:
                due_datetime = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            except ValueError:
                # If parsing fails, ignore the due_date
                due_datetime = None

        task = Task(
            user_id=user_id,
            title=title,
            description=description,
            completed=False,
            priority=priority,
            due_date=due_datetime,
            tags=tags or [],
            recurrence=recurrence,
            recurrence_rule=recurrence_rule,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def get_by_user_advanced(
        self,
        user_id: str,
        filter_type: str = "all",
        priority: Optional[str] = None,
        tag: Optional[str] = None,
        due_from: Optional[str] = None,
        due_to: Optional[str] = None,
        sort_by: str = "created_at",
        search: Optional[str] = None
    ) -> List[Task]:
        """Get all tasks for a user with advanced filtering and sorting."""
        statement = select(Task).where(Task.user_id == user_id)

        # Apply filter by completion status
        if filter_type == "pending":
            statement = statement.where(Task.completed == False)
        elif filter_type == "completed":
            statement = statement.where(Task.completed == True)

        # Apply priority filter
        if priority:
            statement = statement.where(Task.priority == priority)

        # Apply tag filter
        if tag:
            if IS_SQLITE:
                # For SQLite, check if the JSON string contains the tag
                # Using LIKE operator to search for the tag in the JSON array string
                statement = statement.where(Task.tags.like(f'%{tag}%'))
            else:
                # For PostgreSQL, use the @> operator to check if array contains specific value
                statement = statement.where(Task.tags.op('@>')(f'{{{tag}}}'))

        # Apply due date range filters
        if due_from:
            try:
                from_date = datetime.fromisoformat(due_from.replace('Z', '+00:00'))
                statement = statement.where(Task.due_date >= from_date)
            except ValueError:
                pass  # Ignore invalid date format

        if due_to:
            try:
                to_date = datetime.fromisoformat(due_to.replace('Z', '+00:00'))
                statement = statement.where(Task.due_date <= to_date)
            except ValueError:
                pass  # Ignore invalid date format

        # Apply search filter (title and description)
        if search:
            search_pattern = f"%{search}%"
            statement = statement.where(
                Task.title.ilike(search_pattern) |
                (Task.description.is_not(None) & Task.description.ilike(search_pattern))
            )

        # Apply sorting
        if sort_by == "due_date":
            statement = statement.order_by(Task.due_date.asc().nullslast())
        elif sort_by == "priority":
            # Sort by priority: high, medium, low
            from sqlalchemy import case
            statement = statement.order_by(
                case(
                    (Task.priority == 'high', 1),
                    (Task.priority == 'medium', 2),
                    (Task.priority == 'low', 3),
                    else_=4
                ).asc(),
                Task.created_at.desc()
            )
        elif sort_by == "title":
            statement = statement.order_by(Task.title.asc())
        else:  # Default to created_at
            statement = statement.order_by(Task.created_at.desc())

        tasks = list(self.session.exec(statement).all())
        
        # For SQLite, ensure tags are properly formatted for API response
        if IS_SQLITE:
            for task in tasks:
                # Access the tags_serialized property to ensure proper deserialization
                _ = task.tags_serialized
        
        return tasks

    def get_by_id(self, task_id: int, user_id: str) -> Optional[Task]:
        """Get a specific task by ID, ensuring user ownership."""
        statement = (
            select(Task)
            .where(Task.id == task_id)
            .where(Task.user_id == user_id)
        )
        task = self.session.exec(statement).first()
        
        # For SQLite, ensure tags are properly formatted for API response
        if task and IS_SQLITE:
            # Access the tags_serialized property to ensure proper deserialization
            _ = task.tags_serialized
        
        return task

    def update_advanced(
        self,
        task_id: int,
        user_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        due_date: Optional[str] = None,
        tags: Optional[List[str]] = None,
        recurrence: Optional[str] = None,
        recurrence_rule: Optional[str] = None
    ) -> Optional[Task]:
        """Update a task with advanced features, ensuring user ownership."""
        task = self.get_by_id(task_id, user_id)
        if not task:
            return None

        # Update basic fields
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description

        # Update advanced fields
        if priority is not None:
            if priority in ["high", "medium", "low"]:
                task.priority = priority
        if due_date is not None:
            try:
                task.due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            except ValueError:
                # If parsing fails, ignore the due_date update
                pass
        if tags is not None:
            task.tags = tags
        if recurrence is not None:
            task.recurrence = recurrence
        if recurrence_rule is not None:
            task.recurrence_rule = recurrence_rule

        task.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(task)
        
        # For SQLite, ensure tags are properly formatted for API response
        if IS_SQLITE:
            # Access the tags_serialized property to ensure proper deserialization
            _ = task.tags_serialized
        
        return task

    def delete(self, task_id: int, user_id: str) -> bool:
        """Delete a task, ensuring user ownership."""
        task = self.get_by_id(task_id, user_id)
        if not task:
            return False

        self.session.delete(task)
        self.session.commit()
        return True

    def toggle_complete(self, task_id: int, user_id: str) -> Optional[Task]:
        """Toggle task completion status."""
        task = self.get_by_id(task_id, user_id)
        if not task:
            return None

        task.completed = not task.completed
        task.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(task)
        
        # For SQLite, ensure tags are properly formatted for API response
        if IS_SQLITE:
            # Access the tags_serialized property to ensure proper deserialization
            _ = task.tags_serialized
        
        return task

    def get_by_priority(self, user_id: str, priority: str) -> List[Task]:
        """Get tasks filtered by priority."""
        statement = (
            select(Task)
            .where(Task.user_id == user_id)
            .where(Task.priority == priority)
            .where(Task.completed == False)  # Only return pending tasks
            .order_by(Task.created_at.desc())
        )
        tasks = list(self.session.exec(statement).all())
        
        # For SQLite, ensure tags are properly formatted for API response
        if IS_SQLITE:
            for task in tasks:
                # Access the tags_serialized property to ensure proper deserialization
                _ = task.tags_serialized
        
        return tasks

    def get_by_tag(self, user_id: str, tag: str) -> List[Task]:
        """Get tasks filtered by tag."""
        if IS_SQLITE:
            # For SQLite, check if the JSON string contains the tag
            # Using LIKE operator to search for the tag in the JSON array string
            statement = (
                select(Task)
                .where(Task.user_id == user_id)
                .where(Task.tags.like(f'%{tag}%'))
                .order_by(Task.created_at.desc())
            )
        else:
            # For PostgreSQL, use the @> operator to check if array contains specific value
            statement = (
                select(Task)
                .where(Task.user_id == user_id)
                .where(Task.tags.op('@>')(f'{{{tag}}}'))  # PostgreSQL array contains operator for ARRAY type
                .order_by(Task.created_at.desc())
            )
        tasks = list(self.session.exec(statement).all())
        
        # For SQLite, ensure tags are properly formatted for API response
        if IS_SQLITE:
            for task in tasks:
                # Access the tags_serialized property to ensure proper deserialization
                _ = task.tags_serialized
        
        return tasks

    def get_recurring_tasks(self, user_id: str) -> List[Task]:
        """Get all recurring tasks for a user."""
        statement = (
            select(Task)
            .where(Task.user_id == user_id)
            .where(Task.recurrence.is_not(None))
            .order_by(Task.created_at.desc())
        )
        tasks = list(self.session.exec(statement).all())
        
        # For SQLite, ensure tags are properly formatted for API response
        if IS_SQLITE:
            for task in tasks:
                # Access the tags_serialized property to ensure proper deserialization
                _ = task.tags_serialized
        
        return tasks

    def get_tasks_by_due_range(self, user_id: str, start_date: datetime, end_date: datetime) -> List[Task]:
        """Get tasks with due dates in a specific range."""
        statement = (
            select(Task)
            .where(Task.user_id == user_id)
            .where(Task.due_date >= start_date)
            .where(Task.due_date <= end_date)
            .order_by(Task.due_date.asc())
        )
        tasks = list(self.session.exec(statement).all())
        
        # For SQLite, ensure tags are properly formatted for API response
        if IS_SQLITE:
            for task in tasks:
                # Access the tags_serialized property to ensure proper deserialization
                _ = task.tags_serialized
        
        return tasks
