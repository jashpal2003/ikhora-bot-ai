"""Ticket lifecycle and handoff service."""

import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from relay.events.envelope import Actor, EventEnvelope
from relay.events.outbox import OutboxWriter
from relay.platform.ids import generate_id
from relay.tickets.models import HandoffPacket, TicketStatus


class TicketService:
    """Manages tickets, status transitions, SLA checks, and handoffs."""

    @staticmethod
    async def create_ticket(
        session: AsyncSession,
        tenant_id: str,
        title: str,
        conversation_id: str | None = None,
        contact_id: str | None = None,
        priority: str = "normal",
        handoff_packet: HandoffPacket | None = None,
        correlation_id: str | None = None,
    ) -> str:
        """Create a new ticket and record outbox creation event."""
        ticket_id = generate_id("ticket")
        packet_json = json.dumps(handoff_packet.model_dump(mode="json")) if handoff_packet else None

        await session.execute(
            text("""
                INSERT INTO tickets (
                    id, tenant_id, conversation_id, contact_id, title,
                    status, priority, handoff_packet
                ) VALUES (
                    :id, :tenant_id, :conversation_id, :contact_id, :title,
                    :status, :priority, :handoff_packet
                )
            """),
            {
                "id": ticket_id,
                "tenant_id": tenant_id,
                "conversation_id": conversation_id,
                "contact_id": contact_id,
                "title": title,
                "status": TicketStatus.NEW.value,
                "priority": priority,
                "handoff_packet": packet_json,
            },
        )

        corr_id = correlation_id or generate_id("trace")
        envelope = EventEnvelope(
            event_type="ticket.created",
            tenant_id=tenant_id,
            actor=Actor(type="system"),
            correlation_id=corr_id,
            data={
                "ticket_id": ticket_id,
                "title": title,
                "conversation_id": conversation_id,
                "priority": priority,
                "has_handoff": handoff_packet is not None,
            },
        )
        await OutboxWriter.record_event(session, envelope)
        return ticket_id

    @staticmethod
    async def transition_status(
        session: AsyncSession,
        tenant_id: str,
        ticket_id: str,
        new_status: TicketStatus,
        operator_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Transition ticket status and notify outbox."""
        await session.execute(
            text("""
                UPDATE tickets
                SET status = :status, updated_at = now()
                WHERE id = :id AND tenant_id = :tenant_id
            """),
            {"id": ticket_id, "tenant_id": tenant_id, "status": new_status.value},
        )

        corr_id = correlation_id or generate_id("trace")
        envelope = EventEnvelope(
            event_type="ticket.transitioned",
            tenant_id=tenant_id,
            actor=Actor(type="human" if operator_id else "system", id=operator_id),
            correlation_id=corr_id,
            data={"ticket_id": ticket_id, "new_status": new_status.value},
        )
        await OutboxWriter.record_event(session, envelope)
