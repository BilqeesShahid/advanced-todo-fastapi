"""
List Tasks MCP Tool

Retrieves all tasks for the user with advanced filtering and sorting.

Constitution Compliance:
- Validates user_id (§7.4)
- Enforces user ownership (§7.4)
- Publishes events to Kafka via Dapr (§10.3, §10.4)
- No direct database access (§10.4)
"""

from typing import Dict, Any, List
from sqlmodel import Session, select
from datetime import datetime

from app.mcp.base_tool import BaseMCPTool, MCPToolError, create_success_response, create_error_response
from app.models.task import Task
from app.dapr.client import dapr_publisher


class ListTasksTool(BaseMCPTool):
    """MCP Tool for listing tasks with advanced filtering"""

    async def execute(self, user_id: str, filter_type: str = "all", priority: str = None,
                     tag: str = None, due_from: str = None, due_to: str = None,
                     sort_by: str = "created_at", search: str = None, **kwargs) -> Dict[str, Any]:
        """
        List all tasks for the user with advanced filtering

        Args:
            user_id: Owner of the tasks
            filter_type: Filter by status ("all", "pending", "completed")
            priority: Filter by priority ("high", "medium", "low")
            tag: Filter by specific tag
            due_from: Filter tasks with due date >= this date (ISO format)
            due_to: Filter tasks with due date <= this date (ISO format)
            sort_by: Sort by field ("created_at", "due_date", "priority", "title")
            search: Search keyword for title/description

        Returns:
            Array of task objects
        """
        # Log invocation
        self.log_tool_invocation("list_tasks", user_id, {
            "filter_type": filter_type,
            "priority": priority,
            "tag": tag,
            "due_from": due_from,
            "due_to": due_to,
            "sort_by": sort_by,
            "search": search
        })

        # Validate user_id
        self.validate_user_id(user_id)

        # Validate filter_type
        valid_filters = ["all", "pending", "completed"]
        if filter_type not in valid_filters:
            raise MCPToolError(
                code="VALIDATION_ERROR",
                message=f"Invalid filter_type. Must be one of: {', '.join(valid_filters)}",
                details={"field": "filter_type", "value": filter_type}
            )

        # Validate priority
        if priority and priority not in ["high", "medium", "low"]:
            raise MCPToolError(
                code="VALIDATION_ERROR",
                message="Priority must be one of: high, medium, low",
                details={"field": "priority", "value": priority}
            )

        # Validate sort_by
        valid_sort_fields = ["created_at", "due_date", "priority", "title"]
        if sort_by not in valid_sort_fields:
            raise MCPToolError(
                code="VALIDATION_ERROR",
                message=f"Sort field must be one of: {', '.join(valid_sort_fields)}",
                details={"field": "sort_by", "value": sort_by}
            )

        try:
            # Build query
            statement = select(Task).where(Task.user_id == user_id)

            # Apply status filter
            if filter_type == "pending":
                statement = statement.where(Task.completed == False)
            elif filter_type == "completed":
                statement = statement.where(Task.completed == True)

            # Apply priority filter
            if priority:
                statement = statement.where(Task.priority == priority)

            # Apply tag filter (if tag is provided)
            if tag:
                # SQLAlchemy ARRAY operations - find tasks that have the specified tag
                statement = statement.where(Task.tags.op('@>')([tag]))

            # Apply due date range filters
            if due_from:
                try:
                    from_date = datetime.fromisoformat(due_from.replace('Z', '+00:00'))
                    statement = statement.where(Task.due_date >= from_date)
                except ValueError:
                    raise MCPToolError(
                        code="VALIDATION_ERROR",
                        message="Invalid due_from date format. Use ISO format.",
                        details={"field": "due_from"}
                    )

            if due_to:
                try:
                    to_date = datetime.fromisoformat(due_to.replace('Z', '+00:00'))
                    statement = statement.where(Task.due_date <= to_date)
                except ValueError:
                    raise MCPToolError(
                        code="VALIDATION_ERROR",
                        message="Invalid due_to date format. Use ISO format.",
                        details={"field": "due_to"}
                    )

            # Apply search filter
            if search:
                search_pattern = f"%{search}%"
                statement = statement.where(
                    Task.title.ilike(search_pattern) |
                    (Task.description.is_not(None) & Task.description.ilike(search_pattern))
                )

            # Apply sorting
            if sort_by == "created_at":
                statement = statement.order_by(Task.created_at.desc())
            elif sort_by == "due_date":
                statement = statement.order_by(Task.due_date.asc().nullslast())
            elif sort_by == "priority":
                # Sort by priority: high, medium, low (high first)
                from sqlalchemy import case
                statement = statement.order_by(
                    case(
                        (Task.priority == 'high', 1),
                        (Task.priority == 'medium', 2),
                        (Task.priority == 'low', 3),
                        else_=4
                    ).asc(),
                    Task.created_at.desc()
                )
            elif sort_by == "title":
                statement = statement.order_by(Task.title.asc())

            # Execute query
            tasks = self.db.exec(statement).all()

            # Serialize tasks
            tasks_data = [
                {
                    "id": task.id,
                    "user_id": task.user_id,
                    "title": task.title,
                    "description": task.description,
                    "completed": task.completed,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                    "priority": task.priority,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "tags": task.tags or [],
                    "recurrence": task.recurrence,
                    "recurrence_rule": task.recurrence_rule,
                    "next_occurrence": task.next_occurrence.isoformat() if task.next_occurrence else None
                }
                for task in tasks
            ]

            # Publish event for audit/logging (only if Dapr is available)
            try:
                dapr_publisher.publish_event(
                    topic="task-updates",
                    event_type="task.listed",
                    data={
                        "user_id": user_id,
                        "filters": {
                            "filter_type": filter_type,
                            "priority": priority,
                            "tag": tag,
                            "due_from": due_from,
                            "due_to": due_to,
                            "sort_by": sort_by,
                            "search": search
                        },
                        "result_count": len(tasks_data)
                    }
                )
            except Exception as e:
                # Log the error but don't fail the operation since this is just for audit/logging
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to publish task.listed event: {str(e)}. Continuing with task listing.")

            # Return success response
            message = self._generate_message(len(tasks_data), filter_type, search)
            return create_success_response(
                data={"tasks": tasks_data, "count": len(tasks_data)},
                message=message
            )

        except Exception as e:
            raise MCPToolError(
                code="INTERNAL_ERROR",
                message="Failed to retrieve tasks",
                details={"error": str(e)}
            )

    def _generate_message(self, count: int, filter_type: str, search: str = None) -> str:
        """Generate user-friendly message based on results"""
        base_msg = ""

        if search:
            if count == 0:
                return f"No tasks found matching '{search}'."
            else:
                return f"Found {count} task{'s' if count != 1 else ''} matching '{search}'."
        else:
            if count == 0:
                if filter_type == "pending":
                    return "You have no pending tasks."
                elif filter_type == "completed":
                    return "You have no completed tasks."
                else:
                    return "You have no tasks yet."
            else:
                if filter_type == "pending":
                    return f"You have {count} pending task{'s' if count != 1 else ''}."
                elif filter_type == "completed":
                    return f"You have {count} completed task{'s' if count != 1 else ''}."
                else:
                    return f"You have {count} total task{'s' if count != 1 else ''}."


def register_list_tasks_tool(mcp_server, db_session: Session):
    """Register list_tasks tool with MCP server"""
    from app.mcp.server import MCPTool
    from sqlalchemy import case

    tool = MCPTool(
        name="list_tasks",
        description="List all tasks for the user with advanced filtering and sorting",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User ID"},
                "filter_type": {
                    "type": "string",
                    "description": "Filter by status: 'all', 'pending', or 'completed'",
                    "enum": ["all", "pending", "completed"],
                    "default": "all"
                },
                "priority": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Filter by priority (optional)"
                },
                "tag": {
                    "type": "string",
                    "description": "Filter by specific tag (optional)"
                },
                "due_from": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Filter tasks with due date >= this date (ISO format, optional)"
                },
                "due_to": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Filter tasks with due date <= this date (ISO format, optional)"
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["created_at", "due_date", "priority", "title"],
                    "default": "created_at",
                    "description": "Sort by field (default: created_at)"
                },
                "search": {
                    "type": "string",
                    "description": "Search keyword for title/description (optional)"
                }
            },
            "required": ["user_id"]
        },
        handler=lambda **kwargs: ListTasksTool(db_session).execute(**kwargs)
    )

    mcp_server.register_tool(tool)
