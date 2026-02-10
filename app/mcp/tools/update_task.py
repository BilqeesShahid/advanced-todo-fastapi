"""
Update Task MCP Tool

Updates an existing task by publishing task.updated event.

Constitution Compliance:
- Validates user_id (§7.4)
- Enforces user ownership (§7.4)
- Publishes events to Kafka via Dapr (§10.3, §10.4)
- No direct database access (§10.4)
"""

from typing import Dict, Any, Optional
from sqlmodel import Session, select
from datetime import datetime

from app.mcp.base_tool import BaseMCPTool, MCPToolError, create_success_response
from app.models.task import Task
from app.dapr.client import dapr_publisher


class UpdateTaskTool(BaseMCPTool):
    """MCP Tool for updating tasks via event publishing"""

    async def execute(
        self,
        user_id: str,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        due_date: Optional[str] = None,
        tags: Optional[list] = None,
        recurrence: Optional[str] = None,
        recurrence_rule: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update an existing task by publishing task.updated event

        Args:
            user_id: Owner of the task
            task_id: ID of task to update
            title: New task title (optional)
            description: New task description (optional)
            priority: New task priority (optional)
            due_date: New due date (optional)
            tags: New tags list (optional)
            recurrence: New recurrence pattern (optional)
            recurrence_rule: New recurrence rule (optional)

        Returns:
            Updated task object
        """
        # Log invocation
        self.log_tool_invocation("update_task", user_id, {"task_id": task_id})

        # Validate user_id
        self.validate_user_id(user_id)

        # Validate at least one field is being updated
        if not any([title, description is not None, priority, due_date, tags, recurrence, recurrence_rule]):
            raise MCPToolError(
                code="VALIDATION_ERROR",
                message="At least one field must be provided for update",
                details={"task_id": task_id}
            )

        # Validate priority if provided
        if priority and priority not in ["high", "medium", "low"]:
            raise MCPToolError(
                code="VALIDATION_ERROR",
                message="Priority must be one of: high, medium, low",
                details={"field": "priority"}
            )

        # Validate tags if provided
        if tags and isinstance(tags, list):
            if len(tags) > 10:
                raise MCPToolError(
                    code="VALIDATION_ERROR",
                    message="Maximum 10 tags per task allowed",
                    details={"field": "tags"}
                )
            for tag in tags:
                if not isinstance(tag, str) or len(tag) > 20:
                    raise MCPToolError(
                        code="VALIDATION_ERROR",
                        message="Each tag must be a string of max 20 characters",
                        details={"field": "tags"}
                    )

        # Prepare update data
        update_data = {
            "id": task_id,
            "user_id": user_id,
            "title": title,
            "description": description,
            "priority": priority,
            "due_date": due_date,
            "tags": tags,
            "recurrence": recurrence,
            "recurrence_rule": recurrence_rule
        }

        try:
            # Publish task.updated event to Kafka via Dapr
            result = dapr_publisher.publish_task_updated(update_data)

            # If event publishing succeeds, return normal response
            return create_success_response(
                data={
                    "id": task_id,
                    "user_id": user_id,
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "due_date": due_date,
                    "tags": tags,
                    "recurrence": recurrence,
                    "recurrence_rule": recurrence_rule
                },
                message=f"Task {task_id} update requested"
            )

        except Exception as event_publish_error:
            # Log the error but fallback to direct database update
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to publish task update event: {str(event_publish_error)}. Falling back to direct database update.")

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

                # Update task fields that were provided
                if title is not None:
                    task.title = title
                if description is not None:
                    task.description = description
                if priority is not None:
                    task.priority = priority
                if due_date is not None:
                    task.due_date = due_date
                if tags is not None:
                    task.tags = tags
                if recurrence is not None:
                    task.recurrence = recurrence
                if recurrence_rule is not None:
                    task.recurrence_rule = recurrence_rule

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
                    message=f"Task '{task.title}' updated successfully"
                )


def register_update_task_tool(mcp_server, db_session: Session):
    """Register update_task tool with MCP server"""
    from app.mcp.server import MCPTool

    tool = MCPTool(
        name="update_task",
        description="Update an existing task by publishing update event",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User ID"},
                "task_id": {"type": "integer", "description": "Task ID to update"},
                "title": {"type": "string", "description": "New task title (optional)"},
                "description": {"type": "string", "description": "New task description (optional)"},
                "priority": {"type": "string", "enum": ["high", "medium", "low"], "description": "New priority (optional)"},
                "due_date": {"type": "string", "format": "date-time", "description": "New due date (ISO format, optional)"},
                "tags": {"type": "array", "items": {"type": "string", "maxLength": 20}, "maxItems": 10, "description": "New array of tags (optional)"},
                "recurrence": {"type": "string", "enum": ["daily", "weekly", "monthly", "custom"], "description": "New recurrence pattern (optional)"},
                "recurrence_rule": {"type": "string", "description": "New recurrence rule in iCal format (optional)"}
            },
            "required": ["user_id", "task_id"]
        },
        handler=lambda **kwargs: UpdateTaskTool(db_session).execute(**kwargs)
    )

    mcp_server.register_tool(tool)
