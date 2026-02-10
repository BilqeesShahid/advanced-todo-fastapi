"""Task schemas for Phase V Advanced Task Management."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class TaskCreate(BaseModel):
    """Schema for creating a task with advanced features."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: Optional[str] = Field(default="medium", pattern=r"^(high|medium|low)$")  # Priority level
    due_date: Optional[str] = Field(None)  # ISO date string
    tags: Optional[List[str]] = Field(None, max_items=10)  # Array of tags (max 10)
    recurrence: Optional[str] = Field(None, pattern=r"^(daily|weekly|monthly|custom|)$")  # Recurrence pattern
    recurrence_rule: Optional[str] = Field(None)  # iCal RRULE or custom rule


class TaskUpdate(BaseModel):
    """Schema for updating a task with advanced features."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: Optional[str] = Field(None, pattern=r"^(high|medium|low)$")  # Priority level
    due_date: Optional[str] = Field(None)  # ISO date string
    tags: Optional[List[str]] = Field(None, max_items=10)  # Array of tags (max 10)
    recurrence: Optional[str] = Field(None, pattern=r"^(daily|weekly|monthly|custom|)$")  # Recurrence pattern
    recurrence_rule: Optional[str] = Field(None)  # iCal RRULE or custom rule


class TaskResponse(BaseModel):
    """Schema for task API responses with advanced features."""
    id: int
    user_id: str
    title: str
    description: Optional[str]
    completed: bool
    created_at: datetime
    updated_at: datetime
    priority: Optional[str] = "medium"  # Priority level (high, medium, low)
    due_date: Optional[datetime] = None  # Due date and time
    tags: Optional[List[str]] = []  # Array of tags
    recurrence: Optional[str] = None  # Recurrence pattern (daily, weekly, monthly, custom)
    recurrence_rule: Optional[str] = None  # iCal RRULE or custom rule
    next_occurrence: Optional[datetime] = None  # Next occurrence date for recurring tasks

    class Config:
        from_attributes = True


class TaskToggleComplete(BaseModel):
    """Schema for toggling task completion (empty body, just an action)."""
    completed: bool
