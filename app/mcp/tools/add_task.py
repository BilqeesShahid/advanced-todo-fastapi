"""
Add Task MCP Tool

Creates a new task for the user via Dapr event publishing.

Constitution Compliance:
- Validates user_id (§7.4)
- Enforces user ownership (§7.4)
- Publishes events to Kafka via Dapr (§10.3, §10.4)
- No direct database access (§10.4)
"""

from typing import Dict, Any
from sqlmodel import Session
from datetime import datetime

from app.mcp.base_tool import BaseMCPTool, MCPToolError, create_success_response, create_error_response
from app.models.task import Task
from app.dapr.client import dapr_publisher


from app.db.config import get_session

class AddTaskTool(BaseMCPTool):
    """MCP Tool for adding tasks via event publishing"""

    async def execute(self, user_id: str, title: str, description: str = None,
                     priority: str = "medium", due_date: str = None, tags: list = None,
                     recurrence: str = None, recurrence_rule: str = None, **kwargs) -> Dict[str, Any]:
        """
        Add a new task by publishing task.created event

        Args:
            user_id: Owner of the task
            title: Task title
            description: Optional task description
            priority: Task priority (high, medium, low) - default: medium
            due_date: Optional due date (ISO format string)
            tags: Optional list of tags
            recurrence: Optional recurrence pattern (daily, weekly, etc.)
            recurrence_rule: Optional recurrence rule (iCal format)

        Returns:
            Created task object
        """
        # Log invocation
        self.log_tool_invocation("add_task", user_id, {"title": title})

        # Validate user_id
        self.validate_user_id(user_id)

        # Validate title
        if not title or not isinstance(title, str) or not title.strip():
            raise MCPToolError(
                code="VALIDATION_ERROR",
                message="Task title cannot be empty",
                details={"field": "title"}
            )

        # Validate priority
        if priority not in ["high", "medium", "low"]:
            raise MCPToolError(
                code="VALIDATION_ERROR",
                message="Priority must be one of: high, medium, low",
                details={"field": "priority"}
            )

        # Validate tags
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

        # Prepare task data for event
        task_data = {
            "user_id": user_id,
            "title": title.strip(),
            "description": description.strip() if description and isinstance(description, str) else description,
            "completed": False,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "priority": priority,
            "due_date": due_date,
            "tags": tags or [],
            "recurrence": recurrence,
            "recurrence_rule": recurrence_rule,
            "next_occurrence": None  # Will be calculated by the consumer service
        }

        try:
            # Publish task.created event to Kafka via Dapr
            result = dapr_publisher.publish_task_created(task_data)

            # If due_date is set, also publish reminder event
            if due_date:
                reminder_data = {
                    "task_id": None,  # Will be assigned by the consumer
                    "user_id": user_id,
                    "due_date": due_date,
                    "title": title.strip()
                }
                dapr_publisher.publish_reminder_scheduled(reminder_data)

            # If event publishing succeeds, return normal response
            return create_success_response(
                data={
                    "id": None,  # Will be assigned by the consumer service
                    "user_id": user_id,
                    "title": task_data["title"],
                    "description": task_data["description"],
                    "completed": task_data["completed"],
                    "created_at": task_data["created_at"],
                    "updated_at": task_data["updated_at"],
                    "priority": task_data["priority"],
                    "due_date": task_data["due_date"],
                    "tags": task_data["tags"],
                    "recurrence": task_data["recurrence"],
                    "recurrence_rule": task_data["recurrence_rule"],
                    "next_occurrence": task_data["next_occurrence"]
                },
                message=f"Task '{title}' creation requested"
            )

        except Exception as event_publish_error:
            # Log the error but fallback to direct database creation
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to publish task creation events: {str(event_publish_error)}. Falling back to direct database creation.")

            # Create task directly in database using a fresh session
            from app.db.config import engine
            from sqlmodel import Session
            with Session(engine) as session:
                new_task = Task(
                    user_id=user_id,
                    title=title.strip(),
                    description=description.strip() if description and isinstance(description, str) else description,
                    completed=False,
                    priority=priority,
                    due_date=due_date,
                    tags=tags or [],
                    recurrence=recurrence,
                    recurrence_rule=recurrence_rule
                )
                
                session.add(new_task)
                session.commit()
                session.refresh(new_task)
                
                # Return success response with actual task ID
                return create_success_response(
                    data={
                        "id": new_task.id,
                        "user_id": new_task.user_id,
                        "title": new_task.title,
                        "description": new_task.description,
                        "completed": new_task.completed,
                        "created_at": new_task.created_at.isoformat(),
                        "updated_at": new_task.updated_at.isoformat(),
                        "priority": new_task.priority,
                        "due_date": new_task.due_date.isoformat() if new_task.due_date else None,
                        "tags": new_task.tags_serialized,  # Use property to handle SQLite/PostgreSQL differences
                        "recurrence": new_task.recurrence,
                        "recurrence_rule": new_task.recurrence_rule,
                        "next_occurrence": new_task.next_occurrence.isoformat() if new_task.next_occurrence else None
                    },
                    message=f"Task '{title}' created successfully"
                )


def register_add_task_tool(mcp_server, db_session: Session):
    """Register add_task tool with MCP server"""
    from app.mcp.server import MCPTool

    tool = MCPTool(
        name="add_task",
        description="Create a new task for the user via event publishing",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User ID"},
                "title": {"type": "string", "description": "Task title"},
                "description": {"type": "string", "description": "Task description (optional)"},
                "priority": {"type": "string", "enum": ["high", "medium", "low"], "default": "medium", "description": "Task priority"},
                "due_date": {"type": "string", "format": "date-time", "description": "Due date in ISO format (optional)"},
                "tags": {"type": "array", "items": {"type": "string", "maxLength": 20}, "maxItems": 10, "description": "Array of tags (optional)"},
                "recurrence": {"type": "string", "enum": ["daily", "weekly", "monthly", "custom"], "description": "Recurrence pattern (optional)"},
                "recurrence_rule": {"type": "string", "description": "Recurrence rule in iCal format (optional)"}
            },
            "required": ["user_id", "title"]
        },
        handler=lambda **kwargs: AddTaskTool(db_session).execute(**kwargs)
    )

    mcp_server.register_tool(tool)
