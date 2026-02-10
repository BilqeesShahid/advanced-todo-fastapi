"""
MCP Tool Invocation Skill

Invokes MCP tools with parameter validation and error handling.

Reusability: Can be used by any agent/subagent that needs to call MCP tools

Constitution Compliance:
- All system interactions through MCP (§2.4)
- Always validates user_id (§7.4)
- Generic and composable (§5.3)
"""

from typing import Dict, Any, Optional
import logging
from app.mcp.server import MCPServer
from app.mcp.base_tool import MCPToolError

logger = logging.getLogger(__name__)


class MCPInvocationSkill:
    """
    Skill for invoking MCP tools safely

    Handles:
    - Parameter validation
    - Error handling
    - Logging
    - Result formatting
    """

    def __init__(self, mcp_server: MCPServer):
        self.mcp_server = mcp_server

    async def invoke(
        self,
        tool_name: str,
        user_id: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Invoke an MCP tool with validation

        Args:
            tool_name: Name of the MCP tool to invoke
            user_id: User ID (required for all tool calls)
            parameters: Additional tool parameters

        Returns:
            Tool execution result

        Raises:
            MCPToolError: If tool invocation fails
        """
        # Validate user_id
        if not user_id:
            raise MCPToolError(
                code="UNAUTHORIZED",
                message="user_id is required for MCP tool invocation"
            )

        # Merge user_id with parameters
        tool_params = parameters or {}
        tool_params["user_id"] = user_id

        # Validate required fields for specific tools
        self._validate_tool_parameters(tool_name, tool_params)

        # Invoke the tool
        try:
            logger.info(f"Invoking MCP tool: {tool_name} for user: {user_id}")
            result = await self.mcp_server.invoke_tool(tool_name, **tool_params)
            logger.info(f"MCP tool {tool_name} executed successfully")
            return result

        except MCPToolError as e:
            logger.error(f"MCP tool {tool_name} failed: {e.message}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error invoking MCP tool {tool_name}: {str(e)}")
            raise MCPToolError(
                code="INTERNAL_ERROR",
                message=f"Failed to execute tool: {str(e)}"
            )

    def _validate_tool_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> None:
        """
        Validate required parameters for each tool

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters

        Raises:
            MCPToolError: If required parameters are missing
        """
        # Define required parameters for each tool
        REQUIRED_PARAMS = {
            "add_task": ["user_id", "title"],
            "list_tasks": ["user_id"],
            "update_task": ["user_id", "task_id"],
            "complete_task": ["user_id", "task_id"],
            "delete_task": ["user_id", "task_id"],
        }

        if tool_name not in REQUIRED_PARAMS:
            logger.warning(f"Unknown tool: {tool_name}, skipping parameter validation")
            return

        required = REQUIRED_PARAMS[tool_name]
        missing = [param for param in required if param not in parameters or not parameters[param]]

        if missing:
            raise MCPToolError(
                code="VALIDATION_ERROR",
                message=f"Missing required parameters: {', '.join(missing)}",
                details={"missing_parameters": missing}
            )

    def list_available_tools(self) -> list[str]:
        """Get list of available MCP tools"""
        return self.mcp_server.list_tools()

    def get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """Get JSON schema for a specific tool"""
        tool = self.mcp_server.get_tool(tool_name)
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters
        }
