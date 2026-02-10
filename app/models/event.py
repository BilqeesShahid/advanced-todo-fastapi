"""Event model for SQLModel."""
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
import uuid
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB


class Event(SQLModel, table=True):
    """Event entity representing system events."""

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), max_length=36)  # Unique event identifier
    type: str = Field(max_length=50)  # task.created, task.updated, task.completed, etc.
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(max_length=100)  # Service that generated event
    data: dict = Field(sa_column=Column(JSONB))  # Event payload as JSONB
    processed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)