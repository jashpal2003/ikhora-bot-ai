"""Conversation management and messaging service."""

import json
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from relay.conversations.models import (
    AuthorType,
    AutonomyMode,
    ConversationStatus,
    MessageContent,
    MessageDirection,
    Priority,
)
from relay.events.envelope import Actor, EventEnvelope
from relay.events.outbox import OutboxWriter
from relay.platform.errors import RelayError
from relay.platform.ids import generate_id


class StaleWriteError(RelayError):
    """Raised when an optimistic concurrency check fails on conversation update."""

    def __init__(self, conversation_id: str, expected_version: int) -> None:
        super().__init__(
            f"Stale write detected for conversation '{conversation_id}' (version {expected_version})",
            {"conversation_id": conversation_id, "expected_version": expected_version},
        )


class ConversationService:
    """Manages conversations, messages, optimistic locking, and event emission."""

    @staticmethod
    async def create_conversation(
        session: AsyncSession,
        tenant_id: str,
        channel_id: str,
        contact_id: str | None = None,
        autonomy_mode: AutonomyMode = AutonomyMode.ASSIST,
        priority: Priority = Priority.NORMAL,
    ) -> str:
        """Create a new conversation."""
        conversation_id = generate_id("conversation")
        await session.execute(
            text("""
                INSERT INTO conversations (
                    id, tenant_id, channel_id, contact_id, autonomy_mode, priority, status
                ) VALUES (
                    :id, :tenant_id, :channel_id, :contact_id, :autonomy_mode, :priority, :status
                )
            """),
            {
                "id": conversation_id,
                "tenant_id": tenant_id,
                "channel_id": channel_id,
                "contact_id": contact_id,
                "autonomy_mode": autonomy_mode.value,
                "priority": priority.value,
                "status": ConversationStatus.OPEN.value,
            },
        )
        return conversation_id

    @staticmethod
    async def add_message(
        session: AsyncSession,
        tenant_id: str,
        conversation_id: str,
        direction: MessageDirection,
        author_type: AuthorType,
        content: MessageContent,
        author_id: str | None = None,
        external_id: str | None = None,
        agent_run_id: str | None = None,
        channel_external_key: str | None = None,
        correlation_id: str | None = None,
    ) -> str:
        """Append a message to a conversation and atomically record outbox event."""
        message_id = generate_id("message")
        now = datetime.now(timezone.utc)

        await session.execute(
            text("""
                INSERT INTO messages (
                    id, tenant_id, conversation_id, direction, author_type, author_id,
                    content, external_id, channel_external_key, agent_run_id, created_at
                ) VALUES (
                    :id, :tenant_id, :conversation_id, :direction, :author_type, :author_id,
                    :content, :external_id, :channel_external_key, :agent_run_id, :created_at
                )
            """),
            {
                "id": message_id,
                "tenant_id": tenant_id,
                "conversation_id": conversation_id,
                "direction": direction.value,
                "author_type": author_type.value,
                "author_id": author_id,
                "content": json.dumps(content.model_dump()),
                "external_id": external_id,
                "channel_external_key": channel_external_key,
                "agent_run_id": agent_run_id,
                "created_at": now,
            },
        )

        # Update conversation last_msg_at timestamp and bump version
        await session.execute(
            text("""
                UPDATE conversations 
                SET last_msg_at = :now, version = version + 1, updated_at = :now
                WHERE id = :conv_id AND tenant_id = :tenant_id
            """),
            {"conv_id": conversation_id, "tenant_id": tenant_id, "now": now},
        )

        # Emit message.created event via outbox
        corr_id = correlation_id or generate_id("trace")
        envelope = EventEnvelope(
            event_type="message.created",
            tenant_id=tenant_id,
            actor=Actor(type=author_type.value, id=author_id),
            correlation_id=corr_id,
            data={
                "message_id": message_id,
                "conversation_id": conversation_id,
                "direction": direction.value,
                "author_type": author_type.value,
                "text": content.text,
            },
        )
        await OutboxWriter.record_event(session, envelope)
        return message_id

    @staticmethod
    async def assign_conversation(
        session: AsyncSession,
        tenant_id: str,
        conversation_id: str,
        assignee_id: str | None,
        expected_version: int,
    ) -> None:
        """Assign conversation to an operator with optimistic locking."""
        result = await session.execute(
            text("""
                UPDATE conversations
                SET assignee_id = :assignee_id, version = version + 1, updated_at = now()
                WHERE id = :id AND tenant_id = :tenant_id AND version = :expected_version
            """),
            {
                "id": conversation_id,
                "tenant_id": tenant_id,
                "assignee_id": assignee_id,
                "expected_version": expected_version,
            },
        )
        if result.rowcount == 0:
            raise StaleWriteError(conversation_id, expected_version)
