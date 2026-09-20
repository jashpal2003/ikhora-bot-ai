"""Conversations API router (Thin controller per §3.5)."""

from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from relay.conversations.models import AuthorType, AutonomyMode, MessageContent, MessageDirection, Priority
from relay.conversations.service import ConversationService
from relay.platform.database import get_session
from relay.platform.tenancy import tenant_scope

router = APIRouter(prefix="/conversations", tags=["Conversations"])


class CreateConversationRequest(BaseModel):
    channel_id: str
    contact_id: str | None = None
    priority: Priority = Priority.NORMAL
    autonomy_mode: AutonomyMode = AutonomyMode.ASSIST


class SendMessageRequest(BaseModel):
    text: str
    author_type: AuthorType = AuthorType.HUMAN
    author_id: str | None = None


@router.post("")
async def create_conversation(
    req: CreateConversationRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Create a new conversation session inside tenant scope."""
    async with tenant_scope(session, x_tenant_id):
        conv_id = await ConversationService.create_conversation(
            session=session,
            tenant_id=x_tenant_id,
            channel_id=req.channel_id,
            contact_id=req.contact_id,
            autonomy_mode=req.autonomy_mode,
            priority=req.priority,
        )
        await session.commit()
    return {"status": "created", "conversation_id": conv_id, "tenant_id": x_tenant_id}


@router.get("")
async def list_conversations(
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    status: str | None = Query(None),
    limit: int = Query(50, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """List conversations for operator inbox with RLS enforcement."""
    async with tenant_scope(session, x_tenant_id):
        query_str = """
            SELECT id, tenant_id, channel_id, contact_id, status, priority,
                   assignee_id, autonomy_mode, last_msg_at, version, created_at
            FROM conversations
            WHERE tenant_id = :tenant_id
        """
        params: dict[str, Any] = {"tenant_id": x_tenant_id, "limit": limit}
        if status:
            query_str += " AND status = :status"
            params["status"] = status
        query_str += " ORDER BY last_msg_at DESC NULLS LAST, created_at DESC LIMIT :limit"

        result = await session.execute(text(query_str), params)
        rows = result.fetchall()

    return {
        "conversations": [
            {
                "id": r.id,
                "tenant_id": r.tenant_id,
                "channel_id": r.channel_id,
                "contact_id": r.contact_id,
                "status": r.status,
                "priority": r.priority,
                "assignee_id": r.assignee_id,
                "autonomy_mode": r.autonomy_mode,
                "last_msg_at": r.last_msg_at.isoformat() if r.last_msg_at else None,
                "version": r.version,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("/{conversation_id}/messages")
async def list_conversation_messages(
    conversation_id: str,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Retrieve message history for a conversation."""
    async with tenant_scope(session, x_tenant_id):
        result = await session.execute(
            text("""
                SELECT id, conversation_id, direction, author_type, author_id,
                       content, external_id, created_at
                FROM messages
                WHERE conversation_id = :conv_id AND tenant_id = :tenant_id
                ORDER BY created_at ASC
            """),
            {"conv_id": conversation_id, "tenant_id": x_tenant_id},
        )
        rows = result.fetchall()

    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "id": r.id,
                "direction": r.direction,
                "author_type": r.author_type,
                "author_id": r.author_id,
                "content": r.content,
                "external_id": r.external_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    req: SendMessageRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Append a message to a conversation with outbox recording."""
    content = MessageContent(text=req.text)
    async with tenant_scope(session, x_tenant_id):
        msg_id = await ConversationService.add_message(
            session=session,
            tenant_id=x_tenant_id,
            conversation_id=conversation_id,
            direction=MessageDirection.OUTBOUND if req.author_type == AuthorType.HUMAN else MessageDirection.INBOUND,
            author_type=req.author_type,
            content=content,
            author_id=req.author_id,
        )
        await session.commit()

    return {
        "status": "sent",
        "message_id": msg_id,
        "conversation_id": conversation_id,
    }
