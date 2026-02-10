"""
Conversation Service

CRUD operations for conversations and messages.

Constitution Compliance:
- Stateless backend: All operations on database (§2.5)
- User isolation: Enforces ownership (§7.3)
"""

from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import Session, select

from app.models.conversation import Conversation
from app.models.message import Message, MessageRole


class ConversationService:
    """Service for managing conversations and messages"""

    def __init__(self, db: Session):
        self.db = db

    def create_conversation(self, user_id: str) -> Conversation:
        """Create new conversation"""
        conversation = Conversation(
            id=uuid4(),
            user_id=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_conversation(self, conversation_id: UUID, user_id: str) -> Optional[Conversation]:
        """Get conversation ensuring ownership"""
        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
        return self.db.exec(statement).first()

    def add_message(
        self,
        conversation_id: UUID,
        role: MessageRole,
        content: str
    ) -> Message:
        """Add message to conversation"""
        message = Message(
            id=uuid4(),
            conversation_id=conversation_id,
            role=role.value,  # Use enum value (lowercase string)
            content=content,
            created_at=datetime.utcnow()
        )
        self.db.add(message)

        # Update conversation timestamp
        conversation = self.db.get(Conversation, conversation_id)
        if conversation:
            conversation.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(message)
        return message

    def get_messages(
        self,
        conversation_id: UUID,
        limit: int = 50
    ) -> List[Message]:
        """Get messages for conversation"""
        statement = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).limit(limit)

        return list(self.db.exec(statement).all())

    def get_user_conversations(self, user_id: str) -> List[Conversation]:
        """Get all conversations for a user, ordered by most recent"""
        statement = select(Conversation).where(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc())

        return list(self.db.exec(statement).all())
