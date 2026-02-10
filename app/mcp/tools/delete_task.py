"""
Delete Task MCP Tool

Permanently deletes a task from the database.

Constitution Compliance:
- Validates user_id (§7.4)
- Enforces user ownership (§7.4)
- Database access via SQLModel (not direct by agents) (§2.4)
"""

from typing import Dict, Any
from sqlmodel import Session, select
from datetime import datetime

from app.mcp.base_tool import BaseMCPTool, MCPToolError, create_success_response
from app.models.task import Task


class DeleteTaskTool(BaseMCPTool):
    """MCP Tool for deleting tasks"""

    async def execute(self, user_id: str, task_id: int, **kwargs) -> Dict[str, Any]:
        """
        Delete a task permanently

        Args:
            user_id: Owner of the task
            task_id: ID of task to delete

        Returns:
            Success confirmation
        """
        # Log invocation
        self.log_tool_invocation("delete_task", user_id, {"task_id": task_id})

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

            # Store title for response message
            task_title = task.title

            try:
                # Publish task.deleted event to Kafka via Dapr
                from app.dapr.client import dapr_publisher
                dapr_publisher.publish_task_deleted({
                    "id": task_id,
                    "user_id": user_id,
                    "title": task_title
                })

                # For production mode (with Dapr), delete task in the original session
                self.db.delete(task)
                self.db.commit()

            except Exception as event_publish_error:
                # Log the error but fallback to direct database deletion
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to publish task deletion event: {str(event_publish_error)}. Falling back to direct database deletion.")

                # Delete task directly in database using a fresh session
                from app.db.config import engine
                from sqlmodel import Session, select
                with Session(engine) as session:
                    # Find task again in the fresh session
                    statement = select(Task).where(Task.id == task_id)
                    task_to_delete = session.exec(statement).first()
                    
                    if not task_to_delete:
                        raise MCPToolError(
                            code="NOT_FOUND",
                            message=f"Task {task_id} not found",
                            details={"task_id": task_id}
                        )

                    # Validate ownership
                    self.validate_ownership(task_to_delete.user_id, user_id)

                    # Delete task
                    session.delete(task_to_delete)
                    session.commit()

            # Return success response
            return create_success_response(
                data={"task_id": task_id, "title": task_title},
                message=f"Task {task_id} '{task_title}' deleted"
            )

        except MCPToolError:
            raise
        except Exception as e:
            self.db.rollback()
            raise MCPToolError(
                code="INTERNAL_ERROR",
                message="Failed to delete task",
                details={"error": str(e)}
            )


def register_delete_task_tool(mcp_server, db_session: Session):
    """Register delete_task tool with MCP server"""
    from app.mcp.server import MCPTool

    tool = MCPTool(
        name="delete_task",
        description="Permanently delete a task",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User ID"},
                "task_id": {"type": "integer", "description": "Task ID to delete"}
            },
            "required": ["user_id", "task_id"]
        },
        handler=lambda **kwargs: DeleteTaskTool(db_session).execute(**kwargs)
    )

    mcp_server.register_tool(tool)
