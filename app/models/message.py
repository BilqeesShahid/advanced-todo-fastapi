"""
Message Model for Phase III AI Chat

Stores individual chat messages (user or assistant) within conversations.
Messages are immutable once created.
"""

from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Text, String

if TYPE_CHECKING:
    from .conversation import Conversation


class MessageRole(str, Enum):
    """Message sender role"""
    USER = "user"
    ASSISTANT = "assistant"


class Message(SQLModel, table=True):
    """
    Individual chat message (user or assistant).

    Relationships:
    - Belongs to one Conversation

    Constitution Compliance:
    - Stateless backend: All messages persisted in database
    - Immutable: Messages are never updated after creation
    - User isolation: Enforced via conversation foreign key
    """
    __tablename__ = "messages"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    conversation_id: UUID = Field(foreign_key="conversations.id", index=True)
    role: str = Field(sa_column=Column(String))  # Store enum value as string
    content: str = Field(sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Relationships (lazy loaded to avoid circular imports)
    conversation: "Conversation" = Relationship(
        back_populates="messages",
        sa_relationship_kwargs={"lazy": "select"}
    )

    class Config:
        arbitrary_types_allowed = True
