"""Notification model for SQLModel."""
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY


class Notification(SQLModel, table=True):
    """Notification entity representing task reminders."""

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(sa_column=Column(Integer, ForeignKey("task.id")))
    user_id: str = Field(sa_column=Column(String, max_length=100))
    scheduled_time: datetime = Field(sa_column=Column(DateTime, nullable=False))
    sent_time: Optional[datetime] = Field(sa_column=Column(DateTime, nullable=True))
    status: str = Field(sa_column=Column(String, max_length=20, default="pending"))  # pending, sent, failed, delivered
    delivery_attempts: int = Field(sa_column=Column(Integer, default=0))
    channel: str = Field(sa_column=Column(String, max_length=20))  # email, push, sms
    message_content: str = Field(sa_column=Column(String, nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))