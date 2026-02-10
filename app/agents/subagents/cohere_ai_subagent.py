"""
Cohere AI Subagent

Uses Cohere's language models for advanced natural language understanding
and response generation for the todo chatbot.

Constitution Compliance:
- Agent-first design: Business logic in agents (§2.3)
- Reusable intelligence (§2.6)
"""

import os
import logging
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
import json

try:
    import cohere
except ImportError:
    cohere = None
    print("Warning: Cohere library not installed. Install with 'pip install cohere'")

from app.agents.skills.intent_parsing import IntentType, ParsedIntent

logger = logging.getLogger(__name__)


class CohereIntentType(Enum):
    """Enhanced intent types for Cohere AI"""
    ADD_TASK = "add_task"
    LIST_TASKS = "list_tasks"
    VIEW_TASK = "view_task"
    UPDATE_TASK = "update_task"
    COMPLETE_TASK = "complete_task"
    DELETE_TASK = "delete_task"
    HELP = "help"
    GREETING = "greeting"
    UNKNOWN = "unknown"


@dataclass
class CohereParsedIntent:
    """Parsed intent from Cohere AI with confidence score"""
    intent: CohereIntentType
    confidence: float  # 0.0 to 1.0
    parameters: Dict[str, Any]
    raw_text: str
    ai_response: Optional[str] = None  # Direct AI response if no specific action needed


class CohereAISubagent:
    """
    Subagent using Cohere AI for natural language understanding

    Responsibilities:
    - Use Cohere models for intent classification
    - Extract entities and parameters using AI
    - Generate contextual responses
    - Fallback to rule-based parsing if Cohere unavailable
    """

    def __init__(self):
        """Initialize Cohere client with API key from environment"""
        self.api_key = os.getenv("COHERE_API_KEY")
        self.model = os.getenv("COHERE_MODEL", "command-r-plus")  # Default to a powerful model
        self.temperature = float(os.getenv("COHERE_TEMPERATURE", "0.7"))

        if cohere and self.api_key:
            self.client = cohere.Client(api_key=self.api_key)
            self.enabled = True
            logger.info(f"Cohere AI subagent initialized with model: {self.model}")
        else:
            self.client = None
            self.enabled = False
            logger.warning("Cohere AI subagent disabled - COHERE_API_KEY not set or cohere library not installed")

    async def parse_intent(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> CohereParsedIntent:
        """
        Parse user intent using Cohere AI

        Args:
            user_input: Natural language input from user
            context: Optional conversation context

        Returns:
            CohereParsedIntent with detected intent and parameters
        """
        if not self.enabled:
            # Fallback to rule-based parsing if Cohere is not available
            return await self._fallback_parse_intent(user_input, context)

        try:
            # Create a structured prompt for intent classification
            prompt = self._build_intent_classification_prompt(user_input, context)

            response = self.client.chat(
                model=self.model,
                message=prompt,
                temperature=self.temperature,
                max_tokens=200,
                # Use JSON format to ensure structured output
                preamble="You are an intelligent task management assistant. Classify user intents and extract parameters in JSON format."
            )

            # Parse the AI response
            result = self._parse_cohere_response(response.text)

            return CohereParsedIntent(
                intent=result.get('intent', CohereIntentType.UNKNOWN),
                confidence=result.get('confidence', 0.7),
                parameters=result.get('parameters', {}),
                raw_text=user_input,
                ai_response=result.get('ai_response')
            )

        except Exception as e:
            logger.error(f"Error in Cohere AI parsing: {str(e)}")

            # Check if it's a model deprecation error
            error_str = str(e).lower()
            if "model" in error_str and ("removed" in error_str or "deprecated" in error_str or "was removed" in error_str):
                logger.warning(f"Cohere model {self.model} is deprecated. Please update your configuration.")

            # Fallback to rule-based parsing on error
            return await self._fallback_parse_intent(user_input, context)

    def _build_intent_classification_prompt(self, user_input: str, context: Optional[Dict[str, Any]]) -> str:
        """Build prompt for intent classification"""
        context_str = ""
        if context:
            context_str = f"\nPrevious conversation context: {json.dumps(context, indent=2)}"

        prompt = f"""
Classify the following user input and extract parameters. Respond in JSON format with the following structure:
{{
    "intent": "add_task|list_tasks|view_task|update_task|complete_task|delete_task|help|greeting|unknown",
    "confidence": 0.0-1.0,
    "parameters": {{"task_id": 123, "title": "task title", "description": "task description", ...}},
    "ai_response": "direct response if no specific action needed"
}}

IMPORTANT: If the user says something like "add any task", "add any new task", "add something", "add anything", or other generic requests to add a task without specifying a concrete title, DO NOT extract a title. Leave the title parameter empty or omit it entirely. The system will handle asking for clarification.

User input: "{user_input}"
{context_str}

Respond ONLY with the JSON object, no additional text before or after:
"""
        return prompt.strip()

    def _parse_cohere_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Cohere response and extract structured data"""
        try:
            # Try to find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx != -1 and end_idx != 0:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)

                # Convert string intent to enum
                intent_str = result.get('intent', 'unknown')
                try:
                    result['intent'] = CohereIntentType(intent_str)
                except ValueError:
                    result['intent'] = CohereIntentType.UNKNOWN

                # Ensure parameters is a dictionary
                if 'parameters' not in result or not isinstance(result.get('parameters'), dict):
                    result['parameters'] = {}

                return result
            else:
                # If no JSON found, try to extract information differently
                # Sometimes Cohere responses might be more conversational
                # In this case, we'll try to determine intent from the response text
                return self._extract_intent_from_text(response_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract information from the text
            return self._extract_intent_from_text(response_text)

    def _extract_intent_from_text(self, response_text: str) -> Dict[str, Any]:
        """Extract intent and parameters from text response when JSON parsing fails"""
        response_lower = response_text.lower()

        # Determine intent based on keywords in the response
        if any(keyword in response_lower for keyword in ['add', 'create', 'new', 'task']):
            intent = CohereIntentType.ADD_TASK
        elif any(keyword in response_lower for keyword in ['list', 'show', 'view', 'all']):
            intent = CohereIntentType.LIST_TASKS
        elif any(keyword in response_lower for keyword in ['view', 'see', 'detail', 'task']):
            intent = CohereIntentType.VIEW_TASK
        elif any(keyword in response_lower for keyword in ['update', 'change', 'modify', 'edit']):
            intent = CohereIntentType.UPDATE_TASK
        elif any(keyword in response_lower for keyword in ['complete', 'done', 'finish', 'mark']):
            intent = CohereIntentType.COMPLETE_TASK
        elif any(keyword in response_lower for keyword in ['delete', 'remove', 'cancel']):
            intent = CohereIntentType.DELETE_TASK
        elif any(keyword in response_lower for keyword in ['help', 'what can', 'command']):
            intent = CohereIntentType.HELP
        elif any(keyword in response_lower for keyword in ['hello', 'hi', 'hey', 'greet']):
            intent = CohereIntentType.GREETING
        else:
            intent = CohereIntentType.UNKNOWN

        return {
            'intent': intent,
            'confidence': 0.5,
            'parameters': {},
            'ai_response': response_text
        }

    async def _fallback_parse_intent(self, user_input: str, context: Optional[Dict[str, Any]]) -> CohereParsedIntent:
        """
        Fallback to rule-based parsing if Cohere is unavailable
        """
        from app.agents.skills.intent_parsing import intent_parsing_skill

        # Use the existing rule-based parser
        parsed = intent_parsing_skill.parse(user_input)

        # Convert to Cohere format
        intent_mapping = {
            IntentType.ADD: CohereIntentType.ADD_TASK,
            IntentType.LIST: CohereIntentType.LIST_TASKS,
            IntentType.VIEW: CohereIntentType.VIEW_TASK,
            IntentType.UPDATE: CohereIntentType.UPDATE_TASK,
            IntentType.COMPLETE: CohereIntentType.COMPLETE_TASK,
            IntentType.DELETE: CohereIntentType.DELETE_TASK,
            IntentType.HELP: CohereIntentType.HELP,
            IntentType.GREETING: CohereIntentType.GREETING,
            IntentType.UNKNOWN: CohereIntentType.UNKNOWN,
        }

        mapped_intent = intent_mapping.get(parsed.intent, CohereIntentType.UNKNOWN)

        # Create parameters dict
        parameters = parsed.parameters.copy()

        # Check if user input contains generic terms for adding tasks
        if mapped_intent == CohereIntentType.ADD_TASK:
            user_input_lower = user_input.lower().strip()

            # If the user said something like "add any task" or "add any new task",
            # we should not extract the generic term as the title
            if any(generic_term in user_input_lower for generic_term in ['any task', 'any new task', 'add any', 'add something', 'add anything']):
                # Remove any title that might have been extracted from generic terms
                if 'title' in parameters:
                    extracted_title = parameters['title'].lower().strip()
                    if extracted_title in ['any task', 'any new task', 'something', 'anything', 'a task', 'new task', 'some task', 'an item', 'something new', 'anything new', 'any']:
                        parameters.pop('title', None)

        return CohereParsedIntent(
            intent=mapped_intent,
            confidence=parsed.confidence,
            parameters=parameters,
            raw_text=user_input
        )

    async def generate_response(self, intent: CohereIntentType, parameters: Dict[str, Any],
                              context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate contextual response using Cohere AI

        Args:
            intent: Classified intent
            parameters: Extracted parameters
            context: Conversation context

        Returns:
            Generated response string
        """
        if not self.enabled:
            return "I processed your request using rule-based logic."

        try:
            prompt = self._build_response_generation_prompt(intent, parameters, context)

            response = self.client.chat(
                model=self.model,
                message=prompt,
                temperature=self.temperature,
                max_tokens=300
            )

            return response.text

        except Exception as e:
            logger.error(f"Error generating response with Cohere: {str(e)}")

            # Check if it's a model deprecation error
            error_str = str(e).lower()
            if "model" in error_str and ("removed" in error_str or "deprecated" in error_str or "was removed" in error_str):
                logger.warning(f"Cohere model {self.model} is deprecated. Please update your configuration.")

            return "I processed your request successfully."

    async def enhance_response_with_cohere(self, base_response: str, user_input: str,
                                        tool_result: Optional[Dict[str, Any]] = None) -> str:
        """
        Enhance a base response with Cohere AI to make it more contextual and helpful

        Args:
            base_response: The original response from tool processing
            user_input: The user's original input
            tool_result: The result from the executed tool (if any)

        Returns:
            Enhanced response string
        """
        if not self.enabled:
            return base_response

        try:
            # Create a prompt to enhance the base response
            prompt = self._build_enhancement_prompt(base_response, user_input, tool_result)

            response = self.client.chat(
                model=self.model,
                message=prompt,
                temperature=self.temperature,
                max_tokens=400
            )

            # Return the enhanced response, falling back to base if enhancement fails
            enhanced = response.text.strip()
            return enhanced if enhanced else base_response

        except Exception as e:
            logger.error(f"Error enhancing response with Cohere: {str(e)}")

            # Check if it's a model deprecation error
            error_str = str(e).lower()
            if "model" in error_str and ("removed" in error_str or "deprecated" in error_str or "was removed" in error_str):
                logger.warning(f"Cohere model {self.model} is deprecated. Please update your configuration.")

            return base_response

    def _build_enhancement_prompt(self, base_response: str, user_input: str,
                                tool_result: Optional[Dict[str, Any]]) -> str:
        """Build prompt for enhancing responses with Cohere"""
        tool_data_str = f"\nTool result data: {json.dumps(tool_result, indent=2)}" if tool_result else ""

        prompt = f"""
You are an intelligent task management assistant. Enhance the following response to be more engaging, helpful, and natural-sounding.

Original user input: "{user_input}"
Base response: "{base_response}"
{tool_data_str}

Enhanced response that maintains accuracy but sounds more natural and helpful. Return only the enhanced response, no additional text:
"""
        return prompt.strip()

    def _build_response_generation_prompt(self, intent: CohereIntentType, parameters: Dict[str, Any],
                                        context: Optional[Dict[str, Any]]) -> str:
        """Build prompt for response generation"""
        context_str = ""
        if context:
            context_str = f"\nPrevious context: {json.dumps(context, indent=2)}"

        intent_descriptions = {
            CohereIntentType.ADD_TASK: "Adding a new task",
            CohereIntentType.LIST_TASKS: "Listing tasks",
            CohereIntentType.VIEW_TASK: "Viewing a specific task",
            CohereIntentType.UPDATE_TASK: "Updating a task",
            CohereIntentType.COMPLETE_TASK: "Completing a task",
            CohereIntentType.DELETE_TASK: "Deleting a task",
            CohereIntentType.HELP: "Providing help information",
            CohereIntentType.GREETING: "Greeting the user",
            CohereIntentType.UNKNOWN: "Unknown intent"
        }

        prompt = f"""
Generate a friendly, helpful response for a task management assistant.
The user's intent was classified as: {intent_descriptions.get(intent, 'Unknown intent')}
Parameters: {json.dumps(parameters, indent=2)}
{context_str}

Generate an appropriate response that acknowledges the action taken or provides helpful information.
"""
        return prompt.strip()


# Singleton instance for easy import
cohere_ai_subagent = CohereAISubagent()