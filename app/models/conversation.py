"""
Conversation Model for Phase III AI Chat

Stores conversation metadata for chat sessions between users and the AI assistant.
Each conversation belongs to one user and contains multiple messages.
"""

from datetime import datetime
from uuid import UUID, uuid4
from typing import List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .message import Message
    from .user import User


class Conversation(SQLModel, table=True):
    """
    Conversation metadata for chat sessions.

    Relationships:
    - Belongs to one User
    - Has many Messages

    Constitution Compliance:
    - Stateless backend: All conversation state persisted in database
    - User isolation: user_id foreign key ensures ownership
    """
    __tablename__ = "conversations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships (lazy loaded to avoid circular imports)
    user: "User" = Relationship(back_populates="conversations")
    messages: List["Message"] = Relationship(
        back_populates="conversation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "select"}
    )

    class Config:
        arbitrary_types_allowed = True
