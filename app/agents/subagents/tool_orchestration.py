"""
Tool Orchestration Subagent

Validates parameters, chains MCP tools, handles multi-step operations.

Reusability: Kafka workflows, background jobs, AI automation pipelines

Constitution Compliance:
- MCP-only interface (§2.4)
- Reusable intelligence (§2.6)
"""

from typing import Dict, Any, List, Optional
import logging
from app.mcp.server import MCPServer
from app.mcp.base_tool import MCPToolError

logger = logging.getLogger(__name__)


class ToolOrchestrationSubagent:
    """
    Subagent for orchestrating MCP tool calls

    Responsibilities:
    - Validate tool parameters
    - Chain multiple tool calls
    - Handle multi-step operations
    - Manage tool execution flow
    """

    def __init__(self, mcp_server: MCPServer):
        self.mcp_server = mcp_server

    async def execute_tool(
        self,
        tool_name: str,
        user_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single MCP tool with validation

        Args:
            tool_name: MCP tool to execute
            user_id: User ID (required)
            parameters: Tool parameters

        Returns:
            Tool execution result
        """
        # Ensure user_id is included
        params = {**parameters, "user_id": user_id}

        logger.info(f"Executing tool: {tool_name} for user: {user_id}")

        try:
            result = await self.mcp_server.invoke_tool(tool_name, **params)
            logger.info(f"Tool {tool_name} executed successfully")
            return result

        except MCPToolError as e:
            logger.error(f"Tool {tool_name} failed: {e.message}")
            return {
                "success": False,
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "details": e.details
                }
            }

        except ValueError as e:
            # Tool not found
            error_msg = str(e)
            if "not found" in error_msg.lower():
                available_tools = self.mcp_server.list_tools()
                logger.error(f"Tool {tool_name} not available. Available: {available_tools}")
                return {
                    "success": False,
                    "error": {
                        "code": "TOOL_NOT_FOUND",
                        "message": f"The '{tool_name.replace('_', ' ')}' feature is not available yet. Currently available: add tasks and list tasks."
                    }
                }
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }

        except Exception as e:
            logger.error(f"Unexpected error in tool {tool_name}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred"
                }
            }

    async def execute_chain(
        self,
        tool_chain: List[Dict[str, Any]],
        user_id: str,
        stop_on_error: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Execute a chain of MCP tools

        Args:
            tool_chain: List of tool specs [{"tool": "name", "params": {...}}, ...]
            user_id: User ID
            stop_on_error: Stop chain if any tool fails

        Returns:
            List of tool execution results
        """
        results = []

        for step in tool_chain:
            tool_name = step.get("tool")
            params = step.get("params", {})

            result = await self.execute_tool(tool_name, user_id, params)
            results.append(result)

            # Stop if error and stop_on_error is True
            if stop_on_error and not result.get("success", True):
                logger.warning(f"Chain stopped at tool {tool_name} due to error")
                break

        return results

    def validate_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate tool parameters before execution

        Args:
            tool_name: Tool to validate for
            parameters: Parameters to validate

        Returns:
            Validation result {"valid": bool, "errors": [...]}
        """
        errors = []

        # Required parameters per tool
        required_params = {
            "add_task": ["title"],
            "list_tasks": [],
            "update_task": ["task_id"],
            "complete_task": ["task_id"],
            "delete_task": ["task_id"],
        }

        if tool_name not in required_params:
            return {"valid": True, "errors": []}

        # Check required parameters
        for param in required_params[tool_name]:
            if param not in parameters or not parameters[param]:
                errors.append(f"Missing required parameter: {param}")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


# Factory function
def create_tool_orchestration_subagent(mcp_server: MCPServer) -> ToolOrchestrationSubagent:
    return ToolOrchestrationSubagent(mcp_server)
