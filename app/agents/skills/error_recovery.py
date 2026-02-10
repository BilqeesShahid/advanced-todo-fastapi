"""
Error Recovery Skill

Handles errors gracefully and generates clarifying questions.

Reusability: Can be used in any error scenario across all features

Constitution Compliance:
- Generic and composable (§5.3)
- Graceful error handling (§15)
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RecoveryStrategy:
    """Strategy for recovering from an error"""
    strategy_type: str  # "clarify", "suggest", "retry", "abort"
    message: str  # Human-friendly message
    suggested_action: Optional[str] = None  # Suggested next step
    context: Optional[Dict[str, Any]] = None  # Additional context


class ErrorRecoverySkill:
    """
    Skill for handling errors and generating recovery strategies

    Handles:
    - Missing parameters → Ask clarifying questions
    - Invalid input → Suggest corrections
    - Resource not found → Offer alternatives
    - System errors → Graceful failure messages
    """

    def handle_missing_parameter(self, parameter_name: str, context: str = "") -> RecoveryStrategy:
        """
        Generate clarifying question for missing parameter

        Args:
            parameter_name: Name of the missing parameter
            context: Additional context about what was being attempted

        Returns:
            Recovery strategy with clarifying question
        """
        questions = {
            "task_id": "Which task would you like to work with? Please provide the task number.",
            "title": "What should the task title be?",
            "new_title": "What would you like to change the task to?",
            "filter": "Would you like to see all tasks, only pending, or only completed tasks?",
        }

        question = questions.get(
            parameter_name,
            f"I need more information about {parameter_name}. Can you provide it?"
        )

        if context:
            question = f"{context} {question}"

        return RecoveryStrategy(
            strategy_type="clarify",
            message=question,
            suggested_action=None,
            context={"missing_parameter": parameter_name}
        )

    def handle_ambiguous_input(self, intent: str, raw_input: str) -> RecoveryStrategy:
        """
        Handle ambiguous user input

        Args:
            intent: The attempted intent
            raw_input: Original user input

        Returns:
            Recovery strategy with clarification request
        """
        messages = {
            "update": "Which task would you like to update? Please provide the task number or description.",
            "complete": "Which task did you complete? Please provide the task number.",
            "delete": "Which task would you like to delete? Please provide the task number.",
        }

        message = messages.get(
            intent,
            "I'm not sure which task you're referring to. Could you provide more details?"
        )

        return RecoveryStrategy(
            strategy_type="clarify",
            message=message,
            suggested_action="You can say 'show my tasks' to see all your tasks first.",
            context={"original_input": raw_input, "intent": intent}
        )

    def handle_resource_not_found(self, resource_type: str, identifier: Any) -> RecoveryStrategy:
        """
        Handle resource not found error

        Args:
            resource_type: Type of resource (e.g., "task")
            identifier: The identifier that wasn't found

        Returns:
            Recovery strategy with helpful suggestion
        """
        message = f"I couldn't find {resource_type}"

        if identifier:
            message += f" {identifier}"

        message += ". Would you like to see your current tasks?"

        return RecoveryStrategy(
            strategy_type="suggest",
            message=message,
            suggested_action="list_tasks",
            context={"resource_type": resource_type, "identifier": identifier}
        )

    def handle_validation_error(self, field: str, issue: str) -> RecoveryStrategy:
        """
        Handle input validation error

        Args:
            field: The field that failed validation
            issue: Description of the validation issue

        Returns:
            Recovery strategy with correction suggestion
        """
        message = f"There's an issue with the {field}: {issue}. Could you try again?"

        return RecoveryStrategy(
            strategy_type="suggest",
            message=message,
            suggested_action=None,
            context={"field": field, "issue": issue}
        )

    def handle_system_error(self, error_message: str = "") -> RecoveryStrategy:
        """
        Handle unexpected system error

        Args:
            error_message: Optional error details (will be logged, not shown to user)

        Returns:
            Recovery strategy with user-friendly error message
        """
        if error_message:
            logger.error(f"System error: {error_message}")

        return RecoveryStrategy(
            strategy_type="abort",
            message="I'm sorry, something went wrong. Please try again in a moment.",
            suggested_action=None,
            context={}
        )

    def suggest_retry(self, action: str, reason: str = "") -> RecoveryStrategy:
        """
        Suggest retrying an action

        Args:
            action: The action to retry
            reason: Optional reason for retry

        Returns:
            Recovery strategy suggesting retry
        """
        message = f"Let's try to {action} again"

        if reason:
            message += f". {reason}"
        else:
            message += "."

        return RecoveryStrategy(
            strategy_type="retry",
            message=message,
            suggested_action=action,
            context={"action": action}
        )

    def format_recovery_message(self, strategy: RecoveryStrategy) -> str:
        """
        Format recovery strategy into user-friendly message

        Args:
            strategy: The recovery strategy

        Returns:
            Formatted message for user
        """
        message = strategy.message

        if strategy.suggested_action and strategy.strategy_type == "suggest":
            message += f"\n\nSuggestion: {strategy.suggested_action}"

        return message


# Singleton instance for easy import
error_recovery_skill = ErrorRecoverySkill()
