"""
MCP Server Implementation

This module implements the MCP (Model Context Protocol) server that provides
tools for AI agents to interact with the task management system.

Constitution Compliance:
- MCP is the ONLY system interface for agents (§2.4)
- All tools validate user_id (§7.4)
- No direct database access by agents
"""

from typing import Dict, Any, Callable
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """MCP Tool definition"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable


class MCPServer:
    """
    MCP Server for Task Management

    Provides tools that agents can invoke to interact with the system.
    All tools enforce user isolation and ownership validation.
    """

    def __init__(self):
        self.tools: Dict[str, MCPTool] = {}
        self.name = "todo-mcp-server"
        logger.info(f"Initializing MCP Server: {self.name}")

    def register_tool(self, tool: MCPTool):
        """Register a tool with the MCP server"""
        if tool.name in self.tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")

        self.tools[tool.name] = tool
        logger.info(f"Registered MCP tool: {tool.name}")

    def get_tool(self, name: str) -> MCPTool:
        """Get a registered tool by name"""
        if name not in self.tools:
            raise ValueError(f"Tool {name} not found. Available tools: {list(self.tools.keys())}")
        return self.tools[name]

    def list_tools(self) -> list[str]:
        """List all registered tool names"""
        return list(self.tools.keys())

    async def invoke_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Invoke a tool with parameters

        Args:
            tool_name: Name of the tool to invoke
            **kwargs: Tool parameters (must include user_id)

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found or user_id missing
        """
        tool = self.get_tool(tool_name)

        # Validate user_id is always present (Constitution §7.4)
        if 'user_id' not in kwargs:
            raise ValueError(f"user_id is required for all MCP tool calls (Constitution §7.4)")

        logger.info(f"Invoking MCP tool: {tool_name} for user: {kwargs['user_id']}")

        try:
            result = await tool.handler(**kwargs)
            logger.info(f"Tool {tool_name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {str(e)}")
            raise

    def get_tool_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Get JSON schemas for all registered tools"""
        return {
            name: {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for name, tool in self.tools.items()
        }


# Global MCP server instance
mcp_server = MCPServer()


def get_mcp_server() -> MCPServer:
    """Get the global MCP server instance"""
    return mcp_server
