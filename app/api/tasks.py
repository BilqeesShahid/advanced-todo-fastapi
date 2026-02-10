"""Task API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from sqlmodel import Session, select
from app.database.connection import get_session
from app.models.task import Task
from app.services.task_service import TaskService
from app.services.recurrence_validator import RecurrenceValidator
from app.services.reminder_scheduler import ReminderScheduler
from app.dapr.client import dapr_publisher


router = APIRouter()


@router.post("/tasks", response_model=Task)
async def create_task(
    task_data: dict,
    db: Session = Depends(get_session)
):
    """Create a new task with advanced features."""
    user_id = task_data.get("user_id")
    title = task_data.get("title")

    if not user_id or not title:
        raise HTTPException(status_code=400, detail="user_id and title are required")

    # Validate advanced features
    priority = task_data.get("priority", "medium")
    tags = task_data.get("tags", [])
    recurrence = task_data.get("recurrence")
    recurrence_rule = task_data.get("recurrence_rule")

    # Validate priority
    priority_validation = RecurrenceValidator.validate_priority(priority)
    if not priority_validation["valid"]:
        raise HTTPException(status_code=400, detail=", ".join(priority_validation["errors"]))

    # Validate tags
    tag_validation = RecurrenceValidator.validate_tag_limits(tags)
    if not tag_validation["valid"]:
        raise HTTPException(status_code=400, detail=", ".join(tag_validation["errors"]))

    # Validate recurrence if present
    if recurrence:
        recurrence_validation = RecurrenceValidator.validate_recurrence_pattern(recurrence, recurrence_rule)
        if not recurrence_validation["valid"]:
            raise HTTPException(status_code=400, detail=", ".join(recurrence_validation["errors"]))

        # Validate task with recurrence
        task_with_recurrence_validation = RecurrenceValidator.validate_task_with_recurrence(task_data)
        if not task_with_recurrence_validation["valid"]:
            raise HTTPException(status_code=400, detail=", ".join(task_with_recurrence_validation["errors"]))

    # Create task service and create task
    task_service = TaskService(db)

    try:
        task = task_service.create_task(
            user_id=user_id,
            title=title,
            description=task_data.get("description"),
            priority=priority,
            due_date=task_data.get("due_date"),
            tags=tags,
            recurrence=recurrence,
            recurrence_rule=recurrence_rule
        )

        # Schedule reminder if due date is set
        if task_data.get("due_date"):
            reminder_scheduler = ReminderScheduler(db)
            reminder_scheduler.schedule_reminders_for_task(task)

        # Publish event for task creation
        dapr_publisher.publish_event(
            topic="task-updates",
            event_type="task.created.api",
            data={"task_id": task.id, "user_id": user_id},
            source="todo-chat-api"
        )

        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.get("/tasks", response_model=List[Task])
async def list_tasks(
    user_id: str = Query(..., description="User ID"),
    filter_type: str = Query("all", description="Filter by status: all, pending, completed"),
    priority: str = Query(None, description="Filter by priority: high, medium, low"),
    tag: str = Query(None, description="Filter by specific tag"),
    due_from: str = Query(None, description="Filter tasks with due date >= this date (ISO format)"),
    due_to: str = Query(None, description="Filter tasks with due date <= this date (ISO format)"),
    sort_by: str = Query("created_at", description="Sort by field: created_at, due_date, priority, title"),
    search: str = Query(None, description="Search keyword for title/description"),
    db: Session = Depends(get_session)
):
    """List tasks with advanced filtering and sorting."""
    # Validate priority filter
    if priority:
        priority_validation = RecurrenceValidator.validate_priority(priority)
        if not priority_validation["valid"]:
            raise HTTPException(status_code=400, detail=", ".join(priority_validation["errors"]))

    # Validate tag format
    if tag:
        tag_validation = RecurrenceValidator.validate_tag_limits([tag])
        if not tag_validation["valid"]:
            raise HTTPException(status_code=400, detail=", ".join(tag_validation["errors"]))

    # Create task service and get tasks
    task_service = TaskService(db)

    try:
        tasks = task_service.get_tasks(
            user_id=user_id,
            filter_type=filter_type,
            priority=priority,
            tag=tag,
            due_from=due_from,
            due_to=due_to,
            sort_by=sort_by,
            search=search
        )

        # Publish event for task listing
        dapr_publisher.publish_event(
            topic="task-updates",
            event_type="task.listed.api",
            data={"user_id": user_id, "count": len(tasks)},
            source="todo-chat-api"
        )

        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@router.get("/tasks/{task_id}", response_model=Task)
async def get_task(
    task_id: int,
    user_id: str,
    db: Session = Depends(get_session)
):
    """Get a specific task."""
    statement = select(Task).where(Task.id == task_id, Task.user_id == user_id)
    task = db.exec(statement).first()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found for user {user_id}")

    # Publish event for task viewing
    dapr_publisher.publish_event(
        topic="task-updates",
        event_type="task.viewed.api",
        data={"task_id": task_id, "user_id": user_id},
        source="todo-chat-api"
    )

    return task


@router.put("/tasks/{task_id}", response_model=Task)
async def update_task(
    task_id: int,
    task_data: dict,
    user_id: str,
    db: Session = Depends(get_session)
):
    """Update an existing task."""
    # Validate advanced features
    updates = {}

    # Check for priority update
    if "priority" in task_data:
        priority = task_data["priority"]
        priority_validation = RecurrenceValidator.validate_priority(priority)
        if not priority_validation["valid"]:
            raise HTTPException(status_code=400, detail=", ".join(priority_validation["errors"]))
        updates["priority"] = priority

    # Check for tags update
    if "tags" in task_data:
        tags = task_data["tags"]
        tag_validation = RecurrenceValidator.validate_tag_limits(tags)
        if not tag_validation["valid"]:
            raise HTTPException(status_code=400, detail=", ".join(tag_validation["errors"]))
        updates["tags"] = tags

    # Check for recurrence update
    if "recurrence" in task_data:
        recurrence = task_data["recurrence"]
        recurrence_rule = task_data.get("recurrence_rule")
        recurrence_validation = RecurrenceValidator.validate_recurrence_pattern(recurrence, recurrence_rule)
        if not recurrence_validation["valid"]:
            raise HTTPException(status_code=400, detail=", ".join(recurrence_validation["errors"]))
        updates["recurrence"] = recurrence

        if recurrence_rule:
            updates["recurrence_rule"] = recurrence_rule

    # Add other update fields
    for field in ["title", "description", "due_date"]:
        if field in task_data:
            updates[field] = task_data[field]

    # Create task service and update task
    task_service = TaskService(db)

    try:
        task = task_service.update_task(
            task_id=task_id,
            user_id=user_id,
            **updates
        )

        # Publish event for task update
        dapr_publisher.publish_event(
            topic="task-updates",
            event_type="task.updated.api",
            data={"task_id": task_id, "user_id": user_id},
            source="todo-chat-api"
        )

        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")


@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: int,
    user_id: str,
    db: Session = Depends(get_session)
):
    """Mark a task as complete."""
    task_service = TaskService(db)

    try:
        task = task_service.complete_task(
            task_id=task_id,
            user_id=user_id
        )

        # Publish event for task completion
        dapr_publisher.publish_event(
            topic="task-updates",
            event_type="task.completed.api",
            data={"task_id": task_id, "user_id": user_id, "title": task.title},
            source="todo-chat-api"
        )

        return {"message": f"Task {task_id} marked as complete", "task_id": task_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete task: {str(e)}")


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    user_id: str,
    db: Session = Depends(get_session)
):
    """Delete a task."""
    statement = select(Task).where(Task.id == task_id, Task.user_id == user_id)
    task = db.exec(statement).first()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found for user {user_id}")

    # Actually delete the task
    db.delete(task)
    db.commit()

    # Publish event for task deletion
    dapr_publisher.publish_event(
        topic="task-updates",
        event_type="task.deleted.api",
        data={"task_id": task_id, "user_id": user_id, "title": task.title},
        source="todo-chat-api"
    )

    return {"message": f"Task {task_id} deleted", "task_id": task_id}