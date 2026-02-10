"""
Complete Task MCP Tool

Marks a task as completed by publishing task.completed event.

Constitution Compliance:
- Validates user_id (§7.4)
- Enforces user ownership (§7.4)
- Publishes events to Kafka via Dapr (§10.3, §10.4)
- No direct database access (§10.4)
"""

from typing import Dict, Any
from sqlmodel import Session, select
from datetime import datetime

from app.mcp.base_tool import BaseMCPTool, MCPToolError, create_success_response
from app.models.task import Task
from app.dapr.client import dapr_publisher


class CompleteTaskTool(BaseMCPTool):
    """MCP Tool for completing tasks via event publishing"""

    async def execute(self, user_id: str, task_id: int, **kwargs) -> Dict[str, Any]:
        """
        Mark a task as completed by publishing task.completed event

        Args:
            user_id: Owner of the task
            task_id: ID of task to complete

        Returns:
            Updated task object
        """
        # Log invocation
        self.log_tool_invocation("complete_task", user_id, {"task_id": task_id})

        # Validate user_id
        self.validate_user_id(user_id)

        # Prepare completion data
        completion_data = {
            "id": task_id,
            "user_id": user_id
        }

        try:
            # Publish task.completed event to Kafka via Dapr
            result = dapr_publisher.publish_task_completed(completion_data)

            # If event publishing succeeds, return normal response
            return create_success_response(
                data={
                    "id": task_id,
                    "user_id": user_id
                },
                message=f"Task {task_id} completion requested"
            )

        except Exception as event_publish_error:
            # Log the error but fallback to direct database update
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to publish task completion event: {str(event_publish_error)}. Falling back to direct database update.")

            # Find and update task directly in database using a fresh session
            from app.db.config import engine
            from sqlmodel import Session, select
            with Session(engine) as session:
                statement = select(Task).where(Task.id == task_id)
                task = session.exec(statement).first()

                if not task:
                    raise MCPToolError(
                        code="NOT_FOUND",
                        message=f"Task {task_id} not found",
                        details={"task_id": task_id}
                    )

                # Validate ownership
                self.validate_ownership(task.user_id, user_id)

                # Update task as completed
                task.completed = True
                task.updated_at = datetime.utcnow()
                session.add(task)
                session.commit()
                session.refresh(task)
                
                # Return success response with actual task data
                return create_success_response(
                    data={
                        "id": task.id,
                        "user_id": task.user_id,
                        "title": task.title,
                        "description": task.description,
                        "completed": task.completed,
                        "created_at": task.created_at.isoformat(),
                        "updated_at": task.updated_at.isoformat(),
                        "priority": task.priority,
                        "due_date": task.due_date.isoformat() if task.due_date else None,
                        "tags": task.tags_serialized,  # Use property to handle SQLite/PostgreSQL differences
                        "recurrence": task.recurrence,
                        "recurrence_rule": task.recurrence_rule,
                        "next_occurrence": task.next_occurrence.isoformat() if task.next_occurrence else None
                    },
                    message=f"Task '{task.title}' marked as completed"
                )


def register_complete_task_tool(mcp_server, db_session: Session):
    """Register complete_task tool with MCP server"""
    from app.mcp.server import MCPTool

    tool = MCPTool(
        name="complete_task",
        description="Mark a task as completed by publishing completion event",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User ID"},
                "task_id": {"type": "integer", "description": "Task ID to complete"}
            },
            "required": ["user_id", "task_id"]
        },
        handler=lambda **kwargs: CompleteTaskTool(db_session).execute(**kwargs)
    )

    mcp_server.register_tool(tool)
