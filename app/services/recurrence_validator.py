"""Recurrence Validator."""
from datetime import datetime
from typing import Dict, Any, Optional
import re


class RecurrenceValidator:
    """Validate recurrence rules for tasks."""

    @staticmethod
    def validate_recurrence_pattern(recurrence: str, recurrence_rule: str = None) -> Dict[str, Any]:
        """
        Validate recurrence pattern and rule.

        Args:
            recurrence: Recurrence type (daily, weekly, monthly, custom)
            recurrence_rule: Optional rule for custom patterns

        Returns:
            Dict with validation result
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Validate recurrence type
        if recurrence not in ["daily", "weekly", "monthly", "custom"]:
            result["valid"] = False
            result["errors"].append("Recurrence must be one of: daily, weekly, monthly, custom")
            return result

        # For custom recurrence, validate the rule
        if recurrence == "custom":
            if not recurrence_rule or not isinstance(recurrence_rule, str):
                result["valid"] = False
                result["errors"].append("Custom recurrence requires a recurrence rule")
                return result

            # Validate basic custom rule format
            if not RecurrenceValidator._validate_custom_rule(recurrence_rule):
                result["valid"] = False
                result["errors"].append(f"Invalid recurrence rule format: {recurrence_rule}")
                return result

        return result

    @staticmethod
    def _validate_custom_rule(rule: str) -> bool:
        """
        Validate custom recurrence rule format.

        Args:
            rule: Custom recurrence rule string

        Returns:
            True if valid, False otherwise
        """
        # Basic validation for common patterns
        rule_lower = rule.lower()

        # Check for common valid patterns
        valid_patterns = [
            r'every_\d+_days?',  # every_2_days, every_3_days, etc.
            r'every_\w+day',     # every_monday, every_friday, etc.
            r'every_\w+day_and_\w+day',  # every_monday_and_friday
            r'every_\w+day_to_\w+day',   # every_monday_to_friday
        ]

        for pattern in valid_patterns:
            if re.search(pattern, rule_lower):
                return True

        # If it's not a recognized pattern, it might be an iCal RRULE
        # For now, just check if it looks like an iCal rule (contains certain keywords)
        ical_keywords = ['freq=', 'until=', 'count=', 'interval=']
        if any(keyword in rule_lower for keyword in ical_keywords):
            return True

        return False

    @staticmethod
    def validate_task_with_recurrence(task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a task that has recurrence settings.

        Args:
            task_data: Task data dictionary

        Returns:
            Dict with validation result
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        recurrence = task_data.get("recurrence")
        recurrence_rule = task_data.get("recurrence_rule")
        due_date = task_data.get("due_date")

        # If recurrence is set, validate it
        if recurrence:
            validation = RecurrenceValidator.validate_recurrence_pattern(recurrence, recurrence_rule)
            if not validation["valid"]:
                result["valid"] = False
                result["errors"].extend(validation["errors"])
                return result

        # If recurrence is set, due_date should typically be provided
        if recurrence and not due_date:
            result["warnings"].append("Task with recurrence should typically have a due date")

        return result

    @staticmethod
    def validate_tag_limits(tags: list) -> Dict[str, Any]:
        """
        Validate tag limits.

        Args:
            tags: List of tags

        Returns:
            Dict with validation result
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        if not tags:
            return result

        if not isinstance(tags, list):
            result["valid"] = False
            result["errors"].append("Tags must be a list")
            return result

        if len(tags) > 10:
            result["valid"] = False
            result["errors"].append(f"Maximum 10 tags allowed, got {len(tags)}")
            return result

        for i, tag in enumerate(tags):
            if not isinstance(tag, str):
                result["valid"] = False
                result["errors"].append(f"Tag at index {i} must be a string")
                return result

            if len(tag) > 20:
                result["valid"] = False
                result["errors"].append(f"Tag '{tag}' exceeds maximum length of 20 characters")
                return result

            # Check for invalid characters in tag
            if not re.match(r'^[\w\s\-_.]+$', tag):
                result["warnings"].append(f"Tag '{tag}' contains potentially problematic characters")

        return result

    @staticmethod
    def validate_priority(priority: str) -> Dict[str, Any]:
        """
        Validate priority value.

        Args:
            priority: Priority string

        Returns:
            Dict with validation result
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        if not priority:
            return result

        if priority not in ["high", "medium", "low"]:
            result["valid"] = False
            result["errors"].append(f"Priority must be one of: high, medium, low, got: {priority}")

        return result