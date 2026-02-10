"""
Main Orchestrator Agent

Coordinates all subagents and skills to process user messages.

Constitution Compliance:
- Agent-first design: Business logic in agents (§2.3)
- Coordinates subagents + skills (§5.2, §5.3)
- Uses MCP as only system interface (§2.4)
"""

from typing import Dict, Any, Optional
from uuid import UUID
import logging
from sqlmodel import Session

from app.mcp.server import MCPServer
from app.agents.subagents.task_reasoning import task_reasoning_subagent, TaskDecision
from app.agents.subagents.conversation_memory import conversation_memory_subagent
from app.agents.subagents.tool_orchestration import create_tool_orchestration_subagent
from app.agents.subagents.response_formatting import response_formatting_subagent
from app.agents.subagents.cohere_ai_subagent import cohere_ai_subagent, CohereParsedIntent, CohereIntentType

logger = logging.getLogger(__name__)


class TodoChatAgent:
    """
    Main orchestrator agent for todo chatbot

    Responsibilities:
    - Coordinate all subagents
    - Process user messages
    - Execute tool calls via MCP
    - Format responses

    Constitution Compliance:
    - Never accesses database directly (§2.4)
    - All operations through MCP (§2.4)
    - Stateless (§2.5)
    """

    def __init__(self, mcp_server: MCPServer, db_session: Session):
        """
        Initialize main agent

        Args:
            mcp_server: MCP server instance
            db_session: Database session for loading conversation history
        """
        self.mcp_server = mcp_server
        self.db_session = db_session

        # Initialize subagents
        self.task_reasoner = task_reasoning_subagent
        self.memory = conversation_memory_subagent
        self.orchestrator = create_tool_orchestration_subagent(mcp_server)
        self.formatter = response_formatting_subagent

        logger.info("TodoChatAgent initialized")

    async def process_message(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[UUID] = None
    ) -> str:
        """
        Process a user message and generate response

        Args:
            user_id: User ID (from JWT)
            message: User's natural language input
            conversation_id: Optional conversation ID for context

        Returns:
            AI assistant's response
        """
        logger.info(f"Processing message for user {user_id}: {message[:50]}...")

        try:
            # Load conversation context if available
            context = await self._load_context(conversation_id) if conversation_id else {}

            # Step 1: Use Cohere AI for intent parsing if available, otherwise use rule-based
            if cohere_ai_subagent.enabled:
                cohere_result = await cohere_ai_subagent.parse_intent(message, context)

                # If Cohere provides a direct response, return it
                if cohere_result.ai_response and cohere_result.intent in [CohereIntentType.HELP, CohereIntentType.GREETING, CohereIntentType.UNKNOWN]:
                    return cohere_result.ai_response

                # Otherwise, map Cohere intent to task decision
                decision = await self._cohere_intent_to_task_decision(cohere_result, context)
            else:
                # Fall back to rule-based reasoning
                decision: TaskDecision = await self.task_reasoner.reason(message, context)

            # Step 2: Handle clarification needs
            if decision.needs_clarification:
                logger.info("User input needs clarification")
                return decision.clarification_message or "I'm not sure what you'd like to do. Can you provide more details?"

            # Step 3: If no tool needed (e.g., help), return formatted message
            if not decision.tool_name:
                return decision.clarification_message or self.formatter.format_help()

            # Step 4: Validate parameters before executing MCP tool
            if decision.tool_name == "add_task":
                title = decision.parameters.get('title', '')
                if not title or not isinstance(title, str) or not title.strip():
                    # Need clarification for add_task without a title
                    return "I'd be happy to help you add a task, but I need a title for the task. What would you like to name your task?"

                # Check if the title is generic or placeholder-like
                stripped_title = title.strip().lower()
                if stripped_title in ['any task', 'any new task', 'something', 'anything', 'a task', 'new task', 'some task', 'an item', 'something new', 'anything new', 'any']:
                    # Need clarification for add_task with generic title
                    return "I'd be happy to add a task for you, but I need a specific title. '" + title.strip() + "' is too generic. What specific task would you like to add?"

            logger.info(f"Executing tool: {decision.tool_name}")
            tool_result = await self.orchestrator.execute_tool(
                tool_name=decision.tool_name,
                user_id=user_id,
                parameters=decision.parameters
            )

            # Add original input to parameters for response enhancement
            decision.parameters['original_input'] = message

            # Step 5: Format response based on tool result
            response = await self._format_tool_response(
                decision.tool_name,
                tool_result,
                decision.parameters
            )

            return response

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return "I'm sorry, something went wrong. Please try again."

    async def _load_context(self, conversation_id: UUID) -> Dict[str, Any]:
        """
        Load conversation context

        Args:
            conversation_id: Conversation UUID

        Returns:
            Context dictionary
        """
        try:
            history = await self.memory.load_history(
                conversation_id,
                self.db_session,
                max_messages=50
            )

            # Extract task references
            task_refs = self.memory.extract_task_references(history)

            return {
                "history": history,
                "task_references": task_refs
            }

        except Exception as e:
            logger.warning(f"Could not load conversation context: {str(e)}")
            return {}

    async def _cohere_intent_to_task_decision(self, cohere_result, context) -> 'TaskDecision':
        """
        Convert Cohere AI parsed intent to task decision

        Args:
            cohere_result: Result from Cohere AI parsing
            context: Conversation context

        Returns:
            TaskDecision compatible with existing flow
        """
        # Map Cohere intents to MCP tool names
        intent_to_tool_map = {
            'add_task': 'add_task',
            'list_tasks': 'list_tasks',
            'view_task': 'view_task',
            'update_task': 'update_task',
            'complete_task': 'complete_task',
            'delete_task': 'delete_task',
        }

        tool_name = intent_to_tool_map.get(cohere_result.intent.value)

        if tool_name:
            # Process parameters to ensure they're in the correct format
            processed_params = self._process_parameters_for_tool(tool_name, cohere_result.parameters)

            return TaskDecision(
                tool_name=tool_name,
                parameters=processed_params,
                confidence=cohere_result.confidence,
                needs_clarification=False
            )
        else:
            # For help, greeting, or unknown intents
            if cohere_result.intent in ['help', 'greeting']:
                return TaskDecision(
                    tool_name=None,
                    parameters={},
                    confidence=cohere_result.confidence,
                    needs_clarification=False,
                    clarification_message=cohere_result.ai_response
                )
            else:
                # Unknown intent - need clarification
                return TaskDecision(
                    tool_name=None,
                    parameters={},
                    confidence=cohere_result.confidence,
                    needs_clarification=True,
                    clarification_message=cohere_result.ai_response or "I'm not sure what you'd like to do. Can you provide more details?"
                )

    def _process_parameters_for_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process parameters to ensure they're in the correct format for the specific tool

        Args:
            tool_name: Name of the tool
            parameters: Raw parameters from Cohere AI

        Returns:
            Processed parameters in correct format for the tool
        """
        processed = parameters.copy()

        if tool_name == "add_task":
            # Ensure title is properly formatted
            title = processed.get('title', '')

            # If title is missing or empty, try alternative parameter names
            if not title:
                # Check for alternative names that Cohere might use
                for alt_param in ['task_title', 'task', 'item', 'title_text']:
                    if alt_param in processed and processed[alt_param]:
                        title = processed[alt_param]
                        break

            # If we found a title in an alternative parameter, normalize it
            if title and isinstance(title, str):
                processed['title'] = title.strip()
            elif not title:
                # If no title found, we'll need clarification later
                processed['title'] = ''

        elif tool_name in ["update_task", "complete_task", "delete_task", "view_task"]:
            # Ensure task_id is properly formatted
            task_id = processed.get('task_id')

            # If task_id is missing, try alternative names
            if not task_id:
                for alt_param in ['id', 'task_number', 'number', 'task_num']:
                    if alt_param in processed and processed[alt_param]:
                        task_id = processed[alt_param]
                        break

            if task_id:
                # Convert to int if it's a string number
                if isinstance(task_id, str) and task_id.isdigit():
                    processed['task_id'] = int(task_id)
                elif isinstance(task_id, int):
                    processed['task_id'] = task_id

        return processed

    async def _format_tool_response(
        self,
        tool_name: str,
        tool_result: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> str:
        """
        Format MCP tool result into user-friendly response

        Args:
            tool_name: Name of executed tool
            tool_result: Tool execution result
            parameters: Tool parameters

        Returns:
            Formatted response string
        """
        # Handle errors
        if not tool_result.get("success", True):
            error = tool_result.get("error", {})
            base_response = await self.formatter.format_error(error)

            # Enhance error response with Cohere if available
            if cohere_ai_subagent.enabled:
                return await cohere_ai_subagent.enhance_response_with_cohere(
                    base_response,
                    "Error occurred",
                    tool_result
                )
            return base_response

        # Get data from result
        data = tool_result.get("data", {})

        # Format based on tool type
        if tool_name == "add_task":
            base_response = await self.formatter.format_task_added(data)
        elif tool_name == "list_tasks":
            tasks = data.get("tasks", [])
            filter_type = parameters.get("filter_type", "all")
            base_response = self.formatter.format_task_list(tasks, filter_type)
        elif tool_name == "view_task":
            task = data
            title = task.get("title")
            desc = task.get("description")
            completed = task.get("completed")
            created = task.get("created_at", "")
            updated = task.get("updated_at", "")

            status_emoji = "✅" if completed else "⏳"
            status_text = "Completed" if completed else "Pending"

            base_response = f"{status_emoji} **Task #{task.get('id')}: {title}**\n\n"
            base_response += f"📊 Status: {status_text}\n"
            if desc:
                base_response += f"📝 Description: {desc}\n"
            base_response += f"📅 Created: {created}\n"
            base_response += f"🔄 Last updated: {updated}\n\n"
            base_response += "What would you like to do with this task?"
        elif tool_name == "update_task":
            task_id = parameters.get("task_id")
            new_title = parameters.get("title") or parameters.get("new_title")
            new_description = parameters.get("description")
            if new_description:
                base_response = f"✅ Task {task_id} updated to '{new_title}' with description: {new_description}"
            else:
                base_response = self.formatter.format_task_updated(task_id, new_title)
        elif tool_name == "complete_task":
            task_id = parameters.get("task_id")
            title = data.get("title")
            base_response = self.formatter.format_task_completed(task_id, title)
        elif tool_name == "delete_task":
            task_id = parameters.get("task_id")
            title = data.get("title")
            base_response = self.formatter.format_task_deleted(task_id, title)
        else:
            # Fallback
            base_response = self.formatter.format_success("Done", "")

        # Enhance the response with Cohere AI if available
        if cohere_ai_subagent.enabled:
            user_input = parameters.get('original_input', 'Task operation')  # We'll need to pass the original input
            return await cohere_ai_subagent.enhance_response_with_cohere(
                base_response,
                user_input,
                tool_result
            )

        return base_response


def create_todo_chat_agent(mcp_server: MCPServer, db_session: Session) -> TodoChatAgent:
    """Factory function to create agent instance"""
    return TodoChatAgent(mcp_server, db_session)
