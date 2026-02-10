"""Notification model for SQLModel."""
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class Notification(SQLModel, table=True):
    """Notification entity representing task reminders."""

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id")
    user_id: str = Field(max_length=100)
    scheduled_time: datetime
    sent_time: Optional[datetime] = None
    status: str = Field(default="pending", max_length=20)  # pending, sent, failed, delivered
    delivery_attempts: int = Field(default=0)
    channel: str = Field(max_length=20)  # email, push, sms
    message_content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)