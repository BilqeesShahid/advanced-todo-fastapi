"""
View Task MCP Tool

Retrieves detailed information about a specific task.

Constitution Compliance:
- Validates user_id (§7.4)
- Enforces user ownership (§7.4)
- Database access via SQLModel (not direct by agents) (§2.4)
"""

from typing import Dict, Any
from sqlmodel import Session, select

from app.mcp.base_tool import BaseMCPTool, MCPToolError, create_success_response
from app.models.task import Task


class ViewTaskTool(BaseMCPTool):
    """MCP Tool for viewing task details"""

    async def execute(self, user_id: str, task_id: int, **kwargs) -> Dict[str, Any]:
        """
        View detailed information about a task

        Args:
            user_id: Owner of the task
            task_id: ID of task to view

        Returns:
            Task object with all details
        """
        # Log invocation
        self.log_tool_invocation("view_task", user_id, {"task_id": task_id})

        # Validate user_id
        self.validate_user_id(user_id)

        try:
            # Find task
            statement = select(Task).where(Task.id == task_id)
            task = self.db.exec(statement).first()

            if not task:
                raise MCPToolError(
                    code="NOT_FOUND",
                    message=f"Task {task_id} not found",
                    details={"task_id": task_id}
                )

            # Validate ownership
            self.validate_ownership(task.user_id, user_id)

            # Return task details
            return create_success_response(
                data={
                    "id": task.id,
                    "user_id": task.user_id,
                    "title": task.title,
                    "description": task.description,
                    "completed": task.completed,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat()
                },
                message=f"Here are the details for task {task_id}"
            )

        except MCPToolError:
            raise
        except Exception as e:
            raise MCPToolError(
                code="INTERNAL_ERROR",
                message="Failed to retrieve task",
                details={"error": str(e)}
            )


def register_view_task_tool(mcp_server, db_session: Session):
    """Register view_task tool with MCP server"""
    from app.mcp.server import MCPTool

    tool = MCPTool(
        name="view_task",
        description="View detailed information about a specific task",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User ID"},
                "task_id": {"type": "integer", "description": "Task ID to view"}
            },
            "required": ["user_id", "task_id"]
        },
        handler=lambda **kwargs: ViewTaskTool(db_session).execute(**kwargs)
    )

    mcp_server.register_tool(tool)
