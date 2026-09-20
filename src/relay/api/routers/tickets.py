"""Tickets API router with full database operations and handoff support."""

from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from relay.platform.database import get_session
from relay.platform.tenancy import tenant_scope
from relay.tickets.models import TicketStatus
from relay.tickets.service import TicketService

router = APIRouter(prefix="/tickets", tags=["Tickets"])


class CreateTicketRequest(BaseModel):
    title: str
    conversation_id: str | None = None
    contact_id: str | None = None
    priority: str = "normal"


class UpdateTicketStatusRequest(BaseModel):
    status: TicketStatus
    operator_id: str | None = None


@router.post("")
async def create_ticket(
    req: CreateTicketRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Create an escalation ticket inside tenant scope."""
    async with tenant_scope(session, x_tenant_id):
        ticket_id = await TicketService.create_ticket(
            session=session,
            tenant_id=x_tenant_id,
            title=req.title,
            conversation_id=req.conversation_id,
            contact_id=req.contact_id,
            priority=req.priority,
        )
        await session.commit()
    return {"status": "created", "ticket_id": ticket_id, "tenant_id": x_tenant_id}


@router.get("")
async def list_tickets(
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    status: str | None = Query(None),
    limit: int = Query(50, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """List escalation tickets for operator console."""
    async with tenant_scope(session, x_tenant_id):
        query_str = """
            SELECT id, tenant_id, conversation_id, contact_id, title,
                   status, priority, assigned_to, handoff_packet, created_at
            FROM tickets
            WHERE tenant_id = :tenant_id
        """
        params: dict[str, Any] = {"tenant_id": x_tenant_id, "limit": limit}
        if status:
            query_str += " AND status = :status"
            params["status"] = status
        query_str += " ORDER BY created_at DESC LIMIT :limit"

        result = await session.execute(text(query_str), params)
        rows = result.fetchall()

    return {
        "tickets": [
            {
                "id": r.id,
                "tenant_id": r.tenant_id,
                "conversation_id": r.conversation_id,
                "contact_id": r.contact_id,
                "title": r.title,
                "status": r.status,
                "priority": r.priority,
                "assigned_to": r.assigned_to,
                "handoff_packet": r.handoff_packet,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.patch("/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: str,
    req: UpdateTicketStatusRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Transition ticket status with outbox notification."""
    async with tenant_scope(session, x_tenant_id):
        await TicketService.transition_status(
            session=session,
            tenant_id=x_tenant_id,
            ticket_id=ticket_id,
            new_status=req.status,
            operator_id=req.operator_id,
        )
        await session.commit()
    return {"status": "updated", "ticket_id": ticket_id, "new_status": req.status}
