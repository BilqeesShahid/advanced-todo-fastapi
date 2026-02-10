"""Task model for SQLModel."""
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, ARRAY, Text
from datetime import datetime
from typing import Optional, List


class Task(SQLModel, table=True):
    """Task entity representing a todo item with advanced features."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(max_length=100)
    title: str = Field(max_length=200, min_length=1)
    description: Optional[str] = Field(default=None, max_length=1000)
    completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Advanced task features for recurring tasks
    priority: str = Field(default="medium", max_length=20)  # high, medium, low
    due_date: Optional[datetime] = Field(default=None)  # timezone-aware datetime
    tags: Optional[List[str]] = Field(sa_column=Column(ARRAY(String)))  # array of tags
    recurrence: Optional[str] = Field(default=None, max_length=50)  # daily, weekly, monthly, custom
    recurrence_rule: Optional[str] = Field(sa_column=Column(Text))  # iCalendar RRULE or simple string
    next_occurrence: Optional[datetime] = Field(default=None)  # next date for recurring tasks