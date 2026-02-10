"""
Conversation Summarization Skill

Compresses long conversation histories while preserving semantic meaning.

Reusability: Can be used in any long-running conversation (voice, multilingual, etc.)

Constitution Compliance:
- Generic and composable (§5.3)
- Supports stateless backend by reducing context size (§2.5)
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """Simplified message representation"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str


@dataclass
class ConversationSummary:
    """Summarized conversation"""
    summary: str
    message_count: int
    key_points: List[str]
    recent_messages: List[ConversationMessage]


class ConversationSummarizationSkill:
    """
    Skill for summarizing long conversation histories

    Strategies:
    1. Keep recent messages (last N)
    2. Summarize older messages into key points
    3. Preserve context for task references
    """

    def __init__(self, recent_message_threshold: int = 10):
        """
        Initialize summarization skill

        Args:
            recent_message_threshold: Number of recent messages to keep in full
        """
        self.recent_message_threshold = recent_message_threshold

    def should_summarize(self, message_count: int) -> bool:
        """
        Determine if conversation should be summarized

        Args:
            message_count: Total number of messages in conversation

        Returns:
            True if summarization is needed
        """
        # Summarize if more than 50 messages
        return message_count > 50

    def summarize(
        self,
        messages: List[ConversationMessage],
        force: bool = False
    ) -> ConversationSummary:
        """
        Summarize a conversation

        Args:
            messages: List of conversation messages
            force: Force summarization even if below threshold

        Returns:
            ConversationSummary with compressed history
        """
        message_count = len(messages)

        # If below threshold and not forced, return as-is
        if not force and not self.should_summarize(message_count):
            return ConversationSummary(
                summary="",
                message_count=message_count,
                key_points=[],
                recent_messages=messages
            )

        # Split into old and recent messages
        recent_messages = messages[-self.recent_message_threshold:]
        old_messages = messages[:-self.recent_message_threshold]

        # Extract key points from old messages
        key_points = self._extract_key_points(old_messages)

        # Generate summary
        summary = self._generate_summary(old_messages, key_points)

        logger.info(
            f"Summarized conversation: {message_count} messages → "
            f"{len(recent_messages)} recent + {len(key_points)} key points"
        )

        return ConversationSummary(
            summary=summary,
            message_count=message_count,
            key_points=key_points,
            recent_messages=recent_messages
        )

    def _extract_key_points(self, messages: List[ConversationMessage]) -> List[str]:
        """
        Extract key points from messages

        This is a simple extraction based on keywords.
        In production, you might use:
        - OpenAI summarization API
        - Extractive summarization model
        - Custom fine-tuned model

        Args:
            messages: Messages to extract key points from

        Returns:
            List of key points
        """
        key_points = []

        # Track actions mentioned
        actions = {
            "added": [],
            "completed": [],
            "deleted": [],
            "updated": []
        }

        for msg in messages:
            content_lower = msg.content.lower()

            # Extract task additions
            if "task" in content_lower and "added" in content_lower:
                # Try to extract task name
                if "'" in msg.content or '"' in msg.content:
                    # Extract text between quotes
                    import re
                    match = re.search(r'["\']([^"\']+)["\']', msg.content)
                    if match:
                        actions["added"].append(match.group(1))

            # Extract completions
            if "complete" in content_lower or "marked as complete" in content_lower:
                if "task" in content_lower:
                    actions["completed"].append("task")

            # Extract deletions
            if "deleted" in content_lower:
                actions["deleted"].append("task")

            # Extract updates
            if "updated" in content_lower:
                actions["updated"].append("task")

        # Convert actions to key points
        if actions["added"]:
            key_points.append(f"Added tasks: {', '.join(actions['added'][:3])}")
        if actions["completed"]:
            key_points.append(f"Completed {len(actions['completed'])} task(s)")
        if actions["deleted"]:
            key_points.append(f"Deleted {len(actions['deleted'])} task(s)")
        if actions["updated"]:
            key_points.append(f"Updated {len(actions['updated'])} task(s)")

        return key_points

    def _generate_summary(
        self,
        messages: List[ConversationMessage],
        key_points: List[str]
    ) -> str:
        """
        Generate a natural language summary

        Args:
            messages: Messages to summarize
            key_points: Extracted key points

        Returns:
            Summary text
        """
        if not key_points:
            return f"Previous conversation with {len(messages)} messages."

        summary = f"In the previous conversation ({len(messages)} messages), you:\n"
        summary += "\n".join(f"- {point}" for point in key_points)

        return summary

    def get_compressed_context(
        self,
        messages: List[ConversationMessage],
        max_messages: int = 20
    ) -> List[ConversationMessage]:
        """
        Get compressed context suitable for AI agent

        Args:
            messages: Full conversation history
            max_messages: Maximum messages to include

        Returns:
            Compressed message list
        """
        if len(messages) <= max_messages:
            return messages

        # Summarize and return recent messages
        summary = self.summarize(messages)

        # Create a synthetic "summary message"
        summary_msg = ConversationMessage(
            role="assistant",
            content=f"[Context Summary] {summary.summary}",
            timestamp="summarized"
        )

        # Return summary + recent messages
        return [summary_msg] + summary.recent_messages


# Singleton instance for easy import
conversation_summarization_skill = ConversationSummarizationSkill()
