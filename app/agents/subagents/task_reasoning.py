"""
Task Reasoning Subagent

Understands user intent and decides which MCP tool(s) to invoke.

Reusability: Can be used in event-driven flows, automation pipelines, microservices

Constitution Compliance:
- Agent-first design: Business logic in agents (§2.3)
- Reusable intelligence (§2.6)
"""

from typing import Dict, Any, Optional
import logging
from app.agents.skills.intent_parsing import intent_parsing_skill, IntentType, ParsedIntent
from app.agents.skills.error_recovery import error_recovery_skill, RecoveryStrategy

logger = logging.getLogger(__name__)


class TaskDecision:
    """Decision about which MCP tool to invoke"""

    def __init__(
        self,
        tool_name: Optional[str],
        parameters: Dict[str, Any],
        confidence: float,
        needs_clarification: bool = False,
        clarification_message: Optional[str] = None
    ):
        self.tool_name = tool_name
        self.parameters = parameters
        self.confidence = confidence
        self.needs_clarification = needs_clarification
        self.clarification_message = clarification_message


class TaskReasoningSubagent:
    """
    Subagent for task-related reasoning

    Responsibilities:
    - Parse user intent from natural language
    - Determine which MCP tool(s) to invoke
    - Extract and validate parameters
    - Handle ambiguous input
    """

    def __init__(self):
        self.intent_parser = intent_parsing_skill
        self.error_recovery = error_recovery_skill

    async def reason(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> TaskDecision:
        """
        Reason about user input and decide action

        Args:
            user_input: Natural language input from user
            context: Optional conversation context (e.g., previous task list)

        Returns:
            TaskDecision with tool name and parameters
        """
        # Parse intent
        parsed = self.intent_parser.parse(user_input)

        logger.info(
            f"Parsed intent: {parsed.intent} "
            f"(confidence: {parsed.confidence:.2f}) "
            f"params: {parsed.parameters}"
        )

        # Map intent to MCP tool
        return self._intent_to_decision(parsed, context)

    def _intent_to_decision(
        self,
        parsed: ParsedIntent,
        context: Optional[Dict[str, Any]]
    ) -> TaskDecision:
        """
        Convert parsed intent to task decision

        Args:
            parsed: Parsed intent with parameters
            context: Conversation context

        Returns:
            TaskDecision with tool and parameters
        """
        # Handle unknown intent
        if parsed.intent == IntentType.UNKNOWN:
            recovery = self.error_recovery.handle_system_error("Could not understand intent")
            return TaskDecision(
                tool_name=None,
                parameters={},
                confidence=0.0,
                needs_clarification=True,
                clarification_message="""🤔 I'm not quite sure what you'd like me to do.

I can help you with:
📝 Adding tasks - "Add buy milk"
📋 Viewing tasks - "Show my tasks"
✏️ Updating tasks - "Update task 3 to new title"
✅ Completing tasks - "Complete task 1"
🗑️ Deleting tasks - "Delete task 2"

Type 'help' for more examples, or just tell me what you need!"""
            )

        # Handle help intent
        if parsed.intent == IntentType.HELP:
            return TaskDecision(
                tool_name=None,
                parameters={},
                confidence=1.0,
                needs_clarification=False,
                clarification_message=self._get_help_message()
            )

        # Handle greeting intent
        if parsed.intent == IntentType.GREETING:
            return TaskDecision(
                tool_name=None,
                parameters={},
                confidence=1.0,
                needs_clarification=False,
                clarification_message=self._get_greeting_message()
            )

        # Map intent to tool
        tool_mapping = {
            IntentType.ADD: "add_task",
            IntentType.LIST: "list_tasks",
            IntentType.VIEW: "view_task",
            IntentType.UPDATE: "update_task",
            IntentType.COMPLETE: "complete_task",
            IntentType.DELETE: "delete_task",
        }

        tool_name = tool_mapping.get(parsed.intent)
        if not tool_name:
            return TaskDecision(
                tool_name=None,
                parameters={},
                confidence=0.0,
                needs_clarification=True,
                clarification_message="I couldn't determine what action to take."
            )

        # Validate parameters and check for missing requirements
        validation_result = self._validate_parameters(parsed.intent, parsed.parameters, context)

        if validation_result["needs_clarification"]:
            return TaskDecision(
                tool_name=None,
                parameters=parsed.parameters,
                confidence=parsed.confidence,
                needs_clarification=True,
                clarification_message=validation_result["message"]
            )

        # All good, return decision
        return TaskDecision(
            tool_name=tool_name,
            parameters=validation_result["parameters"],
            confidence=parsed.confidence,
            needs_clarification=False
        )

    def _validate_parameters(
        self,
        intent: IntentType,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate parameters for intent and check for missing data

        Args:
            intent: User intent
            parameters: Extracted parameters
            context: Conversation context

        Returns:
            Dict with validation result
        """
        # Check required parameters per intent
        if intent == IntentType.ADD:
            if not parameters.get("title"):
                recovery = self.error_recovery.handle_missing_parameter("title", "To add a task,")
                return {
                    "needs_clarification": True,
                    "message": recovery.message,
                    "parameters": parameters
                }

            # Validate priority if provided
            priority = parameters.get("priority")
            if priority and priority not in ["high", "medium", "low"]:
                return {
                    "needs_clarification": True,
                    "message": "Priority must be one of: high, medium, or low",
                    "parameters": parameters
                }

            # Validate tags if provided
            tags = parameters.get("tags")
            if tags and isinstance(tags, list) and len(tags) > 10:
                return {
                    "needs_clarification": True,
                    "message": "Maximum 10 tags allowed per task",
                    "parameters": parameters
                }

            # Validate recurrence if provided
            recurrence = parameters.get("recurrence")
            if recurrence and recurrence not in ["daily", "weekly", "monthly", "custom"]:
                return {
                    "needs_clarification": True,
                    "message": "Recurrence must be one of: daily, weekly, monthly, or custom",
                    "parameters": parameters
                }

        elif intent == IntentType.LIST:
            # Map "filter" to "filter_type" for list_tasks tool
            if "filter" in parameters:
                parameters["filter_type"] = parameters.pop("filter")
            else:
                parameters["filter_type"] = "all"

            # Validate priority filter if provided
            priority = parameters.get("priority")
            if priority and priority not in ["high", "medium", "low"]:
                return {
                    "needs_clarification": True,
                    "message": "Priority filter must be one of: high, medium, or low",
                    "parameters": parameters
                }

        elif intent in [IntentType.VIEW, IntentType.UPDATE, IntentType.COMPLETE, IntentType.DELETE]:
            if not parameters.get("task_id"):
                action_names = {
                    IntentType.VIEW: "view",
                    IntentType.UPDATE: "update",
                    IntentType.COMPLETE: "complete",
                    IntentType.DELETE: "delete"
                }
                action = action_names.get(intent, "work with")
                return {
                    "needs_clarification": True,
                    "message": f"Which task would you like to {action}? Please provide the task number.\n\nTry: 'Show my tasks' to see all task numbers.",
                    "parameters": parameters
                }

            # For update, also need new title
            if intent == IntentType.UPDATE and not parameters.get("title"):
                return {
                    "needs_clarification": True,
                    "message": "What would you like to change the task to?",
                    "parameters": parameters
                }

            # For update, validate advanced parameters
            if intent == IntentType.UPDATE:
                # Validate priority if provided
                priority = parameters.get("priority")
                if priority and priority not in ["high", "medium", "low"]:
                    return {
                        "needs_clarification": True,
                        "message": "Priority must be one of: high, medium, or low",
                        "parameters": parameters
                    }

                # Validate tags if provided
                tags = parameters.get("tags")
                if tags and isinstance(tags, list) and len(tags) > 10:
                    return {
                        "needs_clarification": True,
                        "message": "Maximum 10 tags allowed per task",
                        "parameters": parameters
                    }

                # Validate recurrence if provided
                recurrence = parameters.get("recurrence")
                if recurrence and recurrence not in ["daily", "weekly", "monthly", "custom"]:
                    return {
                        "needs_clarification": True,
                        "message": "Recurrence must be one of: daily, weekly, monthly, or custom",
                        "parameters": parameters
                    }

        # All validations passed
        return {
            "needs_clarification": False,
            "message": None,
            "parameters": parameters
        }

    def _get_help_message(self) -> str:
        """Get help message describing available commands"""
        return """I can help you manage your tasks! Here's what I can do:

📝 **Add a task**: "Add buy groceries" or "Create task: call dentist"
📋 **List tasks**: "Show my tasks" or "What tasks do I have?"
✏️ **Update a task**: "Change task 3 to buy organic groceries"
✅ **Complete a task**: "Mark task 2 as done" or "Complete task 1"
🗑️ **Delete a task**: "Delete task 4" or "Remove task 2"

Just tell me what you'd like to do in natural language!"""

    def _get_greeting_message(self) -> str:
        """Get greeting message"""
        return """👋 Hello! I'm your AI Task Manager!

I'm here to help you stay organized and productive. You can chat with me naturally to manage your tasks!

**Try these:**
• "Add buy groceries - eggs, milk, and bread"
• "Show my pending tasks"
• "Complete task 1"
• "Update task 3 to something new"

What would you like to do today? 😊"""


# Singleton instance for easy import
task_reasoning_subagent = TaskReasoningSubagent()
