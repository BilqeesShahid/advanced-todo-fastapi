"""Task router for Phase V Advanced Task Management."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.services.task_service import TaskService
from app.middleware.auth import get_current_user, CurrentUser
from app.db.config import get_session
from sqlmodel import Session

router = APIRouter(tags=["Tasks"])  # No prefix since main.py adds /api prefix


def get_task_service(session: Session = Depends(get_session)) -> TaskService:
    """Dependency for getting TaskService instance."""
    return TaskService(session)


@router.get("/{user_id}/tasks", response_model=Dict[str, Any])
async def list_tasks(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
    filter_type: str = Query("all", description="Filter by status: all, pending, completed"),
    priority: Optional[str] = Query(None, description="Filter by priority: high, medium, low"),
    tag: Optional[str] = Query(None, description="Filter by specific tag"),
    due_from: Optional[str] = Query(None, description="Filter tasks with due date >= this date (ISO format)"),
    due_to: Optional[str] = Query(None, description="Filter tasks with due date <= this date (ISO format)"),
    sort_by: str = Query("created_at", description="Sort by field: created_at, due_date, priority, title"),
    search: Optional[str] = Query(None, description="Search keyword for title/description"),
):
    """List tasks for the authenticated user with advanced filtering and sorting."""

    # Verify that the user_id in the path matches the authenticated user
    if user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's resources"
        )

    tasks = service.get_by_user_advanced(
        user_id=user_id,
        filter_type=filter_type,
        priority=priority,
        tag=tag,
        due_from=due_from,
        due_to=due_to,
        sort_by=sort_by,
        search=search
    )

    return {
        "tasks": tasks,
        "count": len(tasks)
    }


@router.post("/{user_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    user_id: str,
    task_data: TaskCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    """Create a new task with advanced features (priority, due date, tags, recurrence)."""
    # Verify that the user_id in the path matches the authenticated user
    if user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create tasks for this user"
        )

    return service.create_advanced(
        user_id=user_id,
        title=task_data.title,
        description=task_data.description,
        priority=getattr(task_data, 'priority', 'medium'),
        due_date=getattr(task_data, 'due_date', None),
        tags=getattr(task_data, 'tags', []),
        recurrence=getattr(task_data, 'recurrence', None),
        recurrence_rule=getattr(task_data, 'recurrence_rule', None)
    )


@router.get("/{user_id}/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    user_id: str,
    task_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    """Get a specific task by ID."""
    # Verify that the user_id in the path matches the authenticated user
    if user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's resources"
        )

    task = service.get_by_id(task_id, user_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


@router.put("/{user_id}/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    user_id: str,
    task_id: int,
    task_data: TaskUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    """Update a task with advanced features (title, description, priority, due date, tags, recurrence)."""
    # Verify that the user_id in the path matches the authenticated user
    if user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update tasks for this user"
        )

    task = service.update_advanced(
        task_id=task_id,
        user_id=user_id,
        title=getattr(task_data, 'title', None),
        description=getattr(task_data, 'description', None),
        priority=getattr(task_data, 'priority', None),
        due_date=getattr(task_data, 'due_date', None),
        tags=getattr(task_data, 'tags', None),
        recurrence=getattr(task_data, 'recurrence', None),
        recurrence_rule=getattr(task_data, 'recurrence_rule', None)
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


@router.delete("/{user_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    user_id: str,
    task_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    """Delete a task."""
    # Verify that the user_id in the path matches the authenticated user
    if user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete tasks for this user"
        )

    success = service.delete(task_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )


@router.patch("/{user_id}/tasks/{task_id}/complete", response_model=TaskResponse)
async def toggle_complete(
    user_id: str,
    task_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    """Toggle task completion status."""
    # Verify that the user_id in the path matches the authenticated user
    if user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to complete tasks for this user"
        )

    task = service.toggle_complete(task_id, user_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


@router.get("/{user_id}/tasks/priority/{priority_level}", response_model=List[TaskResponse])
async def get_tasks_by_priority(
    user_id: str,
    priority_level: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    """Get tasks filtered by priority level."""
    # Verify that the user_id in the path matches the authenticated user
    if user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's resources"
        )

    if priority_level not in ["high", "medium", "low"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Priority must be one of: high, medium, low"
        )

    return service.get_by_priority(user_id, priority_level)


@router.get("/{user_id}/tasks/tag/{tag_name}", response_model=List[TaskResponse])
async def get_tasks_by_tag(
    user_id: str,
    tag_name: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    """Get tasks filtered by tag."""
    # Verify that the user_id in the path matches the authenticated user
    if user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's resources"
        )

    return service.get_by_tag(user_id, tag_name)


@router.get("/{user_id}/recurring-tasks", response_model=List[TaskResponse])
async def get_recurring_tasks(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    """Get all recurring tasks for the user."""
    # Verify that the user_id in the path matches the authenticated user
    if user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's resources"
        )

    return service.get_recurring_tasks(user_id)


@router.get("/{user_id}/tasks/due-range", response_model=List[TaskResponse])
async def get_tasks_by_due_range(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
    due_from: str = Query(..., description="Start date in ISO format (e.g., 2026-02-01)"),
    due_to: str = Query(..., description="End date in ISO format (e.g., 2026-02-28)")
):
    """Get tasks with due dates in a specific range."""
    # Verify that the user_id in the path matches the authenticated user
    if user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's resources"
        )

    try:
        start_date = datetime.fromisoformat(due_from)
        end_date = datetime.fromisoformat(due_to)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD)"
        )

    return service.get_tasks_by_due_range(user_id, start_date, end_date)
