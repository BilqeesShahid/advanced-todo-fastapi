"""
Intent Parsing Skill

Parses natural language input to identify user intent and extract parameters.

Reusability: Can be used in any conversational feature (voice, multilingual, etc.)

Constitution Compliance:
- Generic and composable (§5.3)
- Reusable for future phases (§2.6)
"""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """User intent types"""
    ADD = "add"
    LIST = "list"
    VIEW = "view"
    UPDATE = "update"
    COMPLETE = "complete"
    DELETE = "delete"
    HELP = "help"
    GREETING = "greeting"
    UNKNOWN = "unknown"


@dataclass
class ParsedIntent:
    """Parsed intent with extracted parameters"""
    intent: IntentType
    confidence: float  # 0.0 to 1.0
    parameters: Dict[str, Any]
    raw_text: str


class IntentParsingSkill:
    """
    Skill for parsing user intent from natural language

    This is a simple pattern-based parser. In production, you might use:
    - OpenAI function calling
    - Fine-tuned NLU model
    - Rule-based + ML hybrid
    """

    # Intent patterns (keyword-based for simplicity)
    INTENT_PATTERNS = {
        IntentType.ADD: [
            r'\b(add|create|new|make)\b.*\btask\b',
            r'\badd\b',
            r'\bcreate\b.*\b(task|todo)\b',
            r'\b(i need to|i have to|remember to|remind me to)\b',
            r'\b(buy|get|pickup|purchase)\b',  # Common task actions
        ],
        IntentType.VIEW: [
            r'\b(view|see|show|display)\b\s+(task|details|info)?\s*#?\s*\d+',  # "view task 3" or "see 5"
            r'\bdetails\b.*\btask\b.*\d+',
            r'\bshow\b.*\btask\b.*\d+',
        ],
        IntentType.LIST: [
            r'\b(show|list|display|view|what|get)\b.*(tasks|todos|all)',  # Plural
            r'\bshow\b.*\b(my|all)\b',
            r'\bwhat.*\b(tasks|todos)',
            r'\blist\b',
        ],
        IntentType.UPDATE: [
            r'\b(update|change|modify|edit|rename)\b.*\btask\b',
            r'\bchange\b.*\bto\b',
            r'\bupdate\b.*\d+',  # "update 3" or "update task 3"
            r'\bedit\b',
            r'\bmodify\b',
        ],
        IntentType.COMPLETE: [
            r'\b(complete|finish|done|mark.*done|mark.*complete)\b',
            r'\bdone\b.*\b(with|task)',
            r'\bcompleted?\b',
            r'\bfinish\b.*\btask\b',
            r'\bcheck off\b',
        ],
        IntentType.DELETE: [
            r'\b(delete|remove|get rid|cancel|discard)\b',
            r'\bdelete\b.*\btask\b',
            r'\bremove\b.*\btask\b',
        ],
        IntentType.HELP: [
            r'\b(help|what can you do|commands)\b',
        ],
        IntentType.GREETING: [
            r'\b(hi|hello|hey|greetings|good morning|good afternoon|good evening)\b',
            r'\bhow are you\b',
            r'\bwho are you\b',
            r'\bwhat are you\b',
            r'\bintroduce yourself\b',
        ]
    }

    def parse(self, text: str) -> ParsedIntent:
        """
        Parse user input to identify intent and extract parameters

        Args:
            text: Natural language input from user

        Returns:
            ParsedIntent with detected intent and parameters
        """
        if not text or not text.strip():
            return ParsedIntent(
                intent=IntentType.UNKNOWN,
                confidence=1.0,
                parameters={},
                raw_text=text
            )

        text_lower = text.lower().strip()

        # Try to match intent patterns
        for intent_type, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    params = self._extract_parameters(text, text_lower, intent_type)
                    return ParsedIntent(
                        intent=intent_type,
                        confidence=0.8,  # Simple pattern matching has moderate confidence
                        parameters=params,
                        raw_text=text
                    )

        # No pattern matched
        logger.warning(f"Could not parse intent from: {text}")
        return ParsedIntent(
            intent=IntentType.UNKNOWN,
            confidence=0.0,
            parameters={"raw_text": text},
            raw_text=text
        )

    def _extract_parameters(self, text: str, text_lower: str, intent: IntentType) -> Dict[str, Any]:
        """
        Extract parameters based on intent type

        Args:
            text: Original text
            text_lower: Lowercase text
            intent: Detected intent type

        Returns:
            Dictionary of extracted parameters
        """
        params = {}

        if intent == IntentType.ADD:
            # Extract task title and optional description
            title, description = self._extract_add_title_and_description(text, text_lower)
            if title:
                params["title"] = title
            if description:
                params["description"] = description

            # Extract advanced features
            # Look for priority indicators
            if any(word in text_lower for word in ['high priority', 'high prio', 'urgent', 'asap', 'important']):
                params["priority"] = "high"
            elif any(word in text_lower for word in ['low priority', 'low prio', 'not urgent', 'not important']):
                params["priority"] = "low"

            # Look for due date indicators
            due_patterns = [
                r'due\s+(today|tomorrow|\w+\s+\d+\w*|\d+\w*\s+\w+)',
                r'by\s+(today|tomorrow|\w+\s+\d+\w*|\d+\w*\s+\w+)',
                r'before\s+(today|tomorrow|\w+\s+\d+\w*|\d+\w*\s+\w+)'
            ]
            for pattern in due_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    params["due_date"] = match.group(1)
                    break

            # Look for tags
            tag_pattern = r'(?:tag|with tags?|with tag)\s+([^\.,!?]+)'
            tag_match = re.search(tag_pattern, text_lower)
            if tag_match:
                tag_text = tag_match.group(1).strip()
                # Split by comma or 'and'
                tag_parts = re.split(r',|\sand\s', tag_text)
                tags = [tag.strip() for tag in tag_parts if tag.strip()]
                params["tags"] = tags[:10]  # Limit to 10 tags

            # Look for recurrence patterns - enhanced detection
            if any(pattern in text_lower for pattern in ['every day', 'daily', 'each day']):
                params["recurrence"] = "daily"
            elif any(pattern in text_lower for pattern in ['every week', 'weekly', 'each week', 'every monday', 'every tuesday', 'every wednesday', 'every thursday', 'every friday', 'every saturday', 'every sunday', 'every mon', 'every tues', 'every wed', 'every thu', 'every fri', 'every sat', 'every sun']):
                params["recurrence"] = "weekly"
            elif any(pattern in text_lower for pattern in ['every month', 'monthly', 'each month']):
                params["recurrence"] = "monthly"
            elif 'every' in text_lower and any(day in text_lower for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'mon', 'tues', 'wed', 'thu', 'fri', 'sat', 'sun']):
                params["recurrence"] = "weekly"
            elif 'every' in text_lower and any(interval in text_lower for interval in ['hour', 'minute', 'second']):
                params["recurrence"] = "custom"  # For more complex patterns
            # Also check for more explicit recurrence indicators
            elif 'recurring' in text_lower or 'repeat' in text_lower or 'repeats' in text_lower:
                # Try to extract more specific recurrence from context
                if any(day in text_lower for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
                    params["recurrence"] = "weekly"
                elif 'week' in text_lower:
                    params["recurrence"] = "weekly"
                elif 'month' in text_lower:
                    params["recurrence"] = "monthly"
                elif 'day' in text_lower:
                    params["recurrence"] = "daily"
                else:
                    params["recurrence"] = "weekly"  # Default to weekly for recurring tasks

        elif intent in [IntentType.VIEW, IntentType.UPDATE, IntentType.COMPLETE, IntentType.DELETE]:
            # Extract task ID
            task_id = self._extract_task_id(text_lower)
            if task_id:
                params["task_id"] = task_id

            # For update, also extract new title and description
            if intent == IntentType.UPDATE:
                new_content = self._extract_update_title(text, text_lower)
                if new_content:
                    # Check if it has description separator (dash)
                    if ' - ' in new_content:
                        parts = new_content.split(' - ', 1)
                        params["title"] = parts[0].strip()
                        params["description"] = parts[1].strip()
                    else:
                        params["title"] = new_content

        elif intent == IntentType.LIST:
            # Extract filter (all, pending, completed)
            filter_type = self._extract_list_filter(text_lower)
            params["filter"] = filter_type

            # Extract additional filters for advanced search
            # Look for priority filter
            if 'high priority' in text_lower or 'high prio' in text_lower or 'urgent' in text_lower:
                params["priority"] = "high"
            elif 'low priority' in text_lower or 'low prio' in text_lower or 'not urgent' in text_lower:
                params["priority"] = "low"
            elif 'medium priority' in text_lower or 'medium prio' in text_lower:
                params["priority"] = "medium"

            # Look for tag filter
            tag_filter_pattern = r'(?:tagged|with|having)\s+(?:tag|tags?)\s+([^\.,!?]+)'
            tag_filter_match = re.search(tag_filter_pattern, text_lower)
            if tag_filter_match:
                tag_text = tag_filter_match.group(1).strip()
                params["tag"] = tag_text.split()[0]  # Take first tag for filtering

        return params

    def _extract_add_title_and_description(self, text: str, text_lower: str) -> tuple[Optional[str], Optional[str]]:
        """Extract task title and optional description from add intent"""
        # Remove common prefixes
        remaining_text = text
        for prefix in ["add task", "add", "create task", "create", "new task", "i need to", "i have to", "remember to", "remind me to"]:
            if text_lower.startswith(prefix):
                remaining_text = text[len(prefix):].strip()
                break

        # If no prefix matched, use full text
        if remaining_text == text:
            remaining_text = text.strip()

        # Extract advanced features first, then title and description

        # Look for priority indicators
        priority = None
        if 'high priority' in text_lower or 'high prio' in text_lower or 'urgent' in text_lower or 'asap' in text_lower:
            priority = 'high'
        elif 'low priority' in text_lower or 'low prio' in text_lower or 'not urgent' in text_lower:
            priority = 'low'

        # Look for due date indicators
        due_date = None
        due_patterns = [
            r'due\s+(today|tomorrow|\w+\s+\d+\w*|\d+\w*\s+\w+)',
            r'by\s+(today|tomorrow|\w+\s+\d+\w*|\d+\w*\s+\w+)',
            r'before\s+(today|tomorrow|\w+\s+\d+\w*|\d+\w*\s+\w+)'
        ]
        for pattern in due_patterns:
            match = re.search(pattern, text_lower)
            if match:
                due_date = match.group(1)
                break

        # Look for tags
        tags = []
        tag_pattern = r'(?:tag|with tags?|with tag)\s+([^\.,!?]+)'
        tag_match = re.search(tag_pattern, text_lower)
        if tag_match:
            tag_text = tag_match.group(1).strip()
            # Split by comma or 'and'
            tag_parts = re.split(r',|\sand\s', tag_text)
            tags = [tag.strip() for tag in tag_parts if tag.strip()]

        # Look for recurrence patterns - enhanced detection
        recurrence = None
        if any(pattern in text_lower for pattern in ['every day', 'daily', 'each day']):
            recurrence = 'daily'
        elif any(pattern in text_lower for pattern in ['every week', 'weekly', 'each week', 'every monday', 'every tuesday', 'every wednesday', 'every thursday', 'every friday', 'every saturday', 'every sunday', 'every mon', 'every tues', 'every wed', 'every thu', 'every fri', 'every sat', 'every sun']):
            recurrence = 'weekly'
        elif any(pattern in text_lower for pattern in ['every month', 'monthly', 'each month']):
            recurrence = 'monthly'
        elif 'every' in text_lower and any(day in text_lower for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'mon', 'tues', 'wed', 'thu', 'fri', 'sat', 'sun']):
            recurrence = 'weekly'
        elif 'every' in text_lower and any(interval in text_lower for interval in ['hour', 'minute', 'second']):
            recurrence = 'custom'  # For more complex patterns

        # Look for description patterns:
        # 1. "title with description xyz"
        # 2. "title, description"
        # 3. "title - description"
        # 4. "title (description)"

        title = remaining_text
        description = None

        # Pattern 1: "with description ..."
        match = re.match(r'(.+?)\s+with description\s+(.+)', remaining_text, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            description = match.group(2).strip()
            # Store advanced features in params if we had access to them here
            # Since this method only returns title and description, we'll extract these in the main method

        # Pattern 2: "title, description" (comma separated)
        if ',' in remaining_text and not remaining_text.count(',') > 3:  # Max 3 commas
            parts = remaining_text.split(',', 1)
            title = parts[0].strip()
            description = parts[1].strip()
            return title, description

        # Pattern 3: "title - description" (dash separated)
        if ' - ' in remaining_text:
            parts = remaining_text.split(' - ', 1)
            title = parts[0].strip()
            description = parts[1].strip()
            return title, description

        # Pattern 4: "title (description)" (parentheses)
        match = re.match(r'(.+?)\s*\((.+)\)$', remaining_text)
        if match:
            title = match.group(1).strip()
            description = match.group(2).strip()
            return title, description

        # No description found, return just title
        return title, None

    def _extract_task_id(self, text_lower: str) -> Optional[int]:
        """Extract task ID from text"""
        # Look for patterns like "task 3", "task #3", "id 3", etc.
        match = re.search(r'\b(task|id|number)\s*#?\s*(\d+)\b', text_lower)
        if match:
            return int(match.group(2))

        # Look for standalone number
        match = re.search(r'\b(\d+)\b', text_lower)
        if match:
            return int(match.group(1))

        return None

    def _extract_update_title(self, text: str, text_lower: str) -> Optional[str]:
        """Extract new title from update intent"""
        # Pattern 1: "update task 3 to <new title>" (explicit "to")
        match = re.search(r'\bto\s+(.+)$', text_lower)
        if match:
            start_pos = match.start(1)
            return text[start_pos:].strip()

        # Pattern 2: "update task 3 <new title>" (text after task number)
        # Find the task number first, then take everything after it
        task_match = re.search(r'\b(task|id)\s*#?\s*(\d+)\s+(.+)$', text_lower)
        if task_match:
            # Get remaining text after task number from original text
            start_pos = task_match.start(3)
            remaining = text[start_pos:].strip()
            # Remove "to" if it's at the start
            if remaining.lower().startswith('to '):
                remaining = remaining[3:].strip()
            return remaining

        return None

    def _extract_list_filter(self, text_lower: str) -> str:
        """Extract list filter type"""
        if any(word in text_lower for word in ["pending", "incomplete", "active", "unfinished"]):
            return "pending"
        elif any(word in text_lower for word in ["completed", "done", "finished"]):
            return "completed"
        else:
            return "all"


# Singleton instance for easy import
intent_parsing_skill = IntentParsingSkill()
