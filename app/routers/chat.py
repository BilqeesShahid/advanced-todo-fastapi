"""
Chat API Router

Handles conversational interface for task management.

Constitution Compliance:
- JWT authentication required (§7.2)
- Stateless request flow (§8.2)
- Agent-first design: Delegates to agents (§2.3)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from sqlmodel import Session

from app.db.config import get_session as get_db
from app.middleware.auth import get_current_user, CurrentUser
from app.services.conversation_service import ConversationService
from app.models.message import MessageRole
from app.agents.main_agent import create_todo_chat_agent
from app.mcp.server import get_mcp_server

import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])  # No prefix since main.py adds /api prefix


class ChatRequest(BaseModel):
    """Chat request schema"""
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response schema"""
    response: str
    conversation_id: str


class ConversationListItem(BaseModel):
    """Conversation list item schema"""
    id: str
    created_at: str
    updated_at: str
    message_count: int
    last_message: Optional[str] = None


class ConversationListResponse(BaseModel):
    """Conversation list response schema"""
    conversations: list[ConversationListItem]


class MessageItem(BaseModel):
    """Message item schema"""
    role: str
    content: str
    created_at: str


class ConversationMessagesResponse(BaseModel):
    """Conversation messages response schema"""
    messages: list[MessageItem]


@router.post("/{user_id}/chat", response_model=ChatResponse)
async def chat(
    user_id: str,
    request: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat endpoint for AI-powered task management

    Stateless Request Flow (Constitution §8.2):
    1. Authenticate user (JWT)
    2. Load conversation history from database
    3. Append user message to history
    4. Run OpenAI Agent (with subagents + skills)
    5. Execute MCP tool(s) as needed
    6. Store assistant response in database
    7. Return response to client

    Args:
        user_id: User ID from path (must match JWT token)
        request: Chat request with message and optional conversation_id
        current_user: Current authenticated user from JWT
        db: Database session

    Returns:
        ChatResponse with AI assistant's response and conversation_id
    """
    # Validate user_id matches authenticated user (Constitution §7.3)
    if current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user_id in path does not match authenticated user"
        )

    logger.info(f"Chat request from user {user_id}: {request.message[:50]}...")

    try:
        # Initialize services
        conversation_service = ConversationService(db)
        mcp_server = get_mcp_server()

        # Get or create conversation
        conversation_id = None
        if request.conversation_id:
            # Validate conversation exists and belongs to user
            conversation = conversation_service.get_conversation(
                UUID(request.conversation_id),
                user_id
            )
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )
            conversation_id = conversation.id
        else:
            # Create new conversation
            conversation = conversation_service.create_conversation(user_id)
            conversation_id = conversation.id

        # Store user message
        conversation_service.add_message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=request.message
        )

        # Create agent and process message
        agent = create_todo_chat_agent(mcp_server, db)
        assistant_response = await agent.process_message(
            user_id=user_id,
            message=request.message,
            conversation_id=conversation_id
        )

        # Store assistant response
        conversation_service.add_message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=assistant_response
        )

        logger.info(f"Chat request processed successfully for user {user_id}")

        return ChatResponse(
            response=assistant_response,
            conversation_id=str(conversation_id)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred processing your message"
        )


@router.get("/{user_id}/conversations", response_model=ConversationListResponse)
async def get_conversations(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of user's conversations with message counts and last message preview

    Args:
        user_id: User ID from path (must match JWT token)
        current_user: Current authenticated user from JWT
        db: Database session

    Returns:
        ConversationListResponse with list of conversations
    """
    # Validate user_id matches authenticated user
    if current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user_id in path does not match authenticated user"
        )

    try:
        conversation_service = ConversationService(db)
        conversations = conversation_service.get_user_conversations(user_id)

        conversation_items = []
        for conv in conversations:
            # Get message count and last message
            messages = conversation_service.get_messages(conv.id)
            message_count = len(messages)
            last_message = messages[-1].content if messages else None

            # Truncate last message for preview
            if last_message and len(last_message) > 60:
                last_message = last_message[:60] + "..."

            conversation_items.append(ConversationListItem(
                id=str(conv.id),
                created_at=conv.created_at.isoformat(),
                updated_at=conv.updated_at.isoformat(),
                message_count=message_count,
                last_message=last_message
            ))

        return ConversationListResponse(conversations=conversation_items)

    except Exception as e:
        logger.error(f"Error fetching conversations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred fetching conversations"
        )


@router.get("/{user_id}/conversations/{conversation_id}/messages", response_model=ConversationMessagesResponse)
async def get_conversation_messages(
    user_id: str,
    conversation_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all messages for a specific conversation

    Args:
        user_id: User ID from path (must match JWT token)
        conversation_id: Conversation UUID
        current_user: Current authenticated user from JWT
        db: Database session

    Returns:
        ConversationMessagesResponse with list of messages
    """
    # Validate user_id matches authenticated user
    if current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user_id in path does not match authenticated user"
        )

    try:
        conversation_service = ConversationService(db)

        # Verify conversation belongs to user
        conversation = conversation_service.get_conversation(UUID(conversation_id), user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Get messages
        messages = conversation_service.get_messages(UUID(conversation_id))

        message_items = [
            MessageItem(
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at.isoformat()
            )
            for msg in messages
        ]

        return ConversationMessagesResponse(messages=message_items)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching conversation messages: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred fetching messages"
        )
