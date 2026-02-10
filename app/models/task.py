"""Task model for SQLModel."""
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, ForeignKey, Text
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import os
import json

if TYPE_CHECKING:
    from app.models.user import User

# Determine database type for compatibility
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./todo_app.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

if not IS_SQLITE:
    # Use PostgreSQL ARRAY type for PostgreSQL
    from sqlalchemy import ARRAY
    TAGS_COLUMN_TYPE = Column(ARRAY(String))
else:
    # Use Text column with JSON serialization for SQLite
    TAGS_COLUMN_TYPE = Column(Text)


class Task(SQLModel, table=True):
    """Task entity representing a todo item with advanced features."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(
        sa_column=Column(String, ForeignKey("user.id", ondelete="CASCADE"), index=True)
    )
    title: str = Field(max_length=200, min_length=1)
    description: str | None = Field(default=None, max_length=1000)
    completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Phase V: Advanced task features
    priority: str = Field(default="medium", max_length=20)  # high, medium, low
    due_date: Optional[datetime] = Field(default=None)  # timezone-aware datetime
    tags: Optional[List[str]] = Field(sa_column=TAGS_COLUMN_TYPE)  # array of tags (PostgreSQL) or JSON (SQLite)
    recurrence: Optional[str] = Field(default=None, max_length=50)  # daily, weekly, monthly, custom
    recurrence_rule: Optional[str] = Field(sa_column=Column(Text))  # iCalendar RRULE or simple string
    next_occurrence: Optional[datetime] = Field(default=None)  # next date for recurring tasks

    # Relationships
    user: "User" = Relationship(back_populates="tasks")

    def __setattr__(self, name, value):
        """Override to handle tags serialization for SQLite."""
        if name == "tags" and IS_SQLITE and isinstance(value, list):
            # Serialize tags to JSON string for SQLite
            super().__setattr__(name, json.dumps(value) if value else None)
        else:
            super().__setattr__(name, value)

    @property
    def tags_serialized(self) -> Optional[List[str]]:
        """Property to get properly deserialized tags for API responses."""
        if self.tags is None:
            return []
        
        if IS_SQLITE:
            # Deserialize from JSON string for SQLite
            try:
                return json.loads(self.tags) if self.tags else []
            except (json.JSONDecodeError, TypeError):
                return []
        else:
            # For PostgreSQL, tags is already a list
            return self.tags or []

    @property
    def tags_list(self) -> Optional[List[str]]:
        """Property to get tags as a list, handling both PostgreSQL and SQLite."""
        return self.tags_serialized

    def dict(self, **kwargs):
        """Custom dict method to properly serialize tags for API responses."""
        data = super().dict(**kwargs)
        
        # Ensure tags are properly formatted for API responses when using SQLite
        if IS_SQLITE:
            data['tags'] = self.tags_serialized
        
        return data

    class Config:
        """Pydantic configuration for proper serialization."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }