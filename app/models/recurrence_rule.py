"""Recurrence Rule model for SQLModel."""
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import ARRAY


class RecurrenceRule(SQLModel, table=True):
    """Recurrence Rule entity defining patterns for recurring tasks."""

    id: Optional[int] = Field(default=None, primary_key=True)
    frequency: str = Field(sa_column=Column(String, max_length=20))  # daily, weekly, monthly, yearly
    interval: int = Field(sa_column=Column(Integer, default=1))  # How often to repeat (every X units)
    days_of_week: Optional[list] = Field(sa_column=Column(ARRAY(Integer)))  # 0-6 for Sunday-Saturday
    days_of_month: Optional[list] = Field(sa_column=Column(ARRAY(Integer)))  # 1-31
    months: Optional[list] = Field(sa_column=Column(ARRAY(Integer)))  # 1-12
    end_date: Optional[datetime] = Field(sa_column=Column(DateTime, nullable=True))  # When to stop recurring
    occurrence_count: Optional[int] = Field(sa_column=Column(Integer, nullable=True))  # Max occurrences
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))