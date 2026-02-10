"""
Conversation Memory Subagent

Loads and manages conversation history, provides context to other agents.

Reusability: Long sessions, multi-agent orchestration, voice & multilingual chat

Constitution Compliance:
- Stateless backend: Loads from database (§2.5)
- Reusable intelligence (§2.6)
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
import logging
from app.agents.skills.conversation_summarization import conversation_summarization_skill, ConversationMessage

logger = logging.getLogger(__name__)


class ConversationMemorySubagent:
    """
    Subagent for conversation memory management

    Responsibilities:
    - Load conversation history from database
    - Summarize long conversations
    - Build context for other agents
    - Track conversation state
    """

    def __init__(self):
        self.summarizer = conversation_summarization_skill

    async def load_history(
        self,
        conversation_id: UUID,
        db_session: Any,  # SQLModel Session
        max_messages: int = 50
    ) -> List[Dict[str, str]]:
        """
        Load conversation history from database

        Args:
            conversation_id: Conversation UUID
            db_session: Database session
            max_messages: Maximum messages to load

        Returns:
            List of messages formatted for agent
        """
        from app.models.message import Message
        from sqlmodel import select

        # Query messages
        statement = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).limit(max_messages)

        messages = db_session.exec(statement).all()

        # Convert to agent format
        history = [
            {
                "role": msg.role,  # Already a string (user/assistant)
                "content": msg.content,
                "timestamp": msg.created_at.isoformat()
            }
            for msg in messages
        ]

        logger.info(f"Loaded {len(history)} messages for conversation {conversation_id}")
        return history

    async def get_compressed_context(
        self,
        history: List[Dict[str, str]],
        max_context_size: int = 20
    ) -> List[Dict[str, str]]:
        """
        Get compressed conversation context

        Args:
            history: Full conversation history
            max_context_size: Maximum messages in context

        Returns:
            Compressed context suitable for AI agent
        """
        if len(history) <= max_context_size:
            return history

        # Convert to ConversationMessage format
        messages = [
            ConversationMessage(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"]
            )
            for msg in history
        ]

        # Compress using summarization skill
        compressed = self.summarizer.get_compressed_context(messages, max_context_size)

        # Convert back to dict format
        return [
            {"role": msg.role, "content": msg.content}
            for msg in compressed
        ]

    def extract_task_references(self, history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Extract task references from conversation (for context-aware commands)

        Args:
            history: Conversation history

        Returns:
            Dictionary of extracted task references
        """
        # Track last listed tasks for "the first one" style references
        last_task_list = None

        for msg in reversed(history):
            if msg["role"] == "assistant" and "task" in msg["content"].lower():
                # Simple heuristic: if message lists tasks, remember it
                if any(word in msg["content"].lower() for word in ["1.", "2.", "•", "-"]):
                    last_task_list = msg["content"]
                    break

        return {
            "last_task_list": last_task_list
        }


# Singleton instance
conversation_memory_subagent = ConversationMemorySubagent()
