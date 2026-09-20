"""Conversations API router (Thin controller per §3.5)."""

from typing import Any
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from relay.conversations.models import AuthorType, MessageContent, MessageDirection
from relay.conversations.service import ConversationService

router = APIRouter(prefix="/conversations", tags=["Conversations"])


class CreateConversationRequest(BaseModel):
    channel_id: str
    contact_id: str | None = None


class SendMessageRequest(BaseModel):
    text: str
    author_type: AuthorType = AuthorType.HUMAN
    author_id: str | None = None


@router.post("")
async def create_conversation(
    req: CreateConversationRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> dict[str, Any]:
    """Create a new conversation session."""
    # Note: In real setup, session injected via FastAPI Depends
    return {
        "status": "created",
        "tenant_id": x_tenant_id,
        "channel_id": req.channel_id,
    }


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    req: SendMessageRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> dict[str, Any]:
    """Append a message to an existing conversation."""
    return {
        "status": "sent",
        "conversation_id": conversation_id,
        "text": req.text,
    }
