"""
MCP Base Tool Interface

Provides base functionality for all MCP tools including:
- User ID validation
- Ownership checks
- Error handling
- Logging

Constitution Compliance:
- All tools validate user_id (§7.4)
- Ownership enforced before CRUD operations (§7.4)
- Security-conscious error messages (§7.4)
"""

from typing import Any, Dict, Optional
from sqlmodel import Session, select
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class MCPToolError(Exception):
    """Base exception for MCP tool errors"""
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class BaseMCPTool(ABC):
    """
    Base class for all MCP tools

    Provides common functionality:
    - User ID validation
    - Database session management
    - Error handling
    - Audit logging
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def validate_user_id(self, user_id: str) -> None:
        """
        Validate that user_id is provided and non-empty

        Args:
            user_id: The user identifier

        Raises:
            MCPToolError: If user_id is invalid
        """
        if not user_id or not isinstance(user_id, str):
            logger.error("MCP tool called without valid user_id")
            raise MCPToolError(
                code="UNAUTHORIZED",
                message="Invalid or missing user_id",
                details={"field": "user_id"}
            )

    def validate_ownership(self, resource_user_id: str, requesting_user_id: str) -> None:
        """
        Validate that the requesting user owns the resource

        Args:
            resource_user_id: The user_id that owns the resource
            requesting_user_id: The user_id making the request

        Raises:
            MCPToolError: If ownership check fails

        Note: Returns generic "not found" error for security (Constitution §7.4)
        """
        if resource_user_id != requesting_user_id:
            logger.warning(
                f"Ownership validation failed: user {requesting_user_id} "
                f"attempted to access resource owned by {resource_user_id}"
            )
            # Return generic error to not reveal resource existence (security best practice)
            raise MCPToolError(
                code="NOT_FOUND",
                message="Resource not found"
            )

    def log_tool_invocation(self, tool_name: str, user_id: str, params: Dict[str, Any]) -> None:
        """
        Log MCP tool invocation for audit trail

        Args:
            tool_name: Name of the tool being invoked
            user_id: User making the request
            params: Tool parameters (sensitive data should be redacted)
        """
        # Redact sensitive parameters for logging
        safe_params = {k: v for k, v in params.items() if k not in ['password', 'token', 'secret']}

        logger.info(
            f"MCP Tool Invocation: {tool_name} | User: {user_id} | Params: {safe_params}"
        )

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool logic

        Must be implemented by subclasses

        Args:
            **kwargs: Tool-specific parameters (must include user_id)

        Returns:
            Tool execution result
        """
        pass


def create_error_response(error: MCPToolError) -> Dict[str, Any]:
    """
    Create a standardized error response

    Args:
        error: The MCPToolError to convert

    Returns:
        Standardized error response dictionary
    """
    return {
        "success": False,
        "error": {
            "code": error.code,
            "message": error.message,
            "details": error.details
        }
    }


def create_success_response(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a standardized success response

    Args:
        data: The response data
        message: Optional success message

    Returns:
        Standardized success response dictionary
    """
    response = {
        "success": True,
        "data": data
    }

    if message:
        response["message"] = message

    return response
