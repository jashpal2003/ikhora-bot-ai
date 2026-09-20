"""Tickets API router."""

from typing import Any
from fastapi import APIRouter, Header
from pydantic import BaseModel

from relay.tickets.models import TicketStatus

router = APIRouter(prefix="/tickets", tags=["Tickets"])


class CreateTicketRequest(BaseModel):
    title: str
    conversation_id: str | None = None
    contact_id: str | None = None
    priority: str = "normal"


class UpdateTicketStatusRequest(BaseModel):
    status: TicketStatus


@router.post("")
async def create_ticket(
    req: CreateTicketRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> dict[str, Any]:
    return {"status": "created", "tenant_id": x_tenant_id, "title": req.title}


@router.patch("/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: str,
    req: UpdateTicketStatusRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> dict[str, Any]:
    return {"status": "updated", "ticket_id": ticket_id, "new_status": req.status}
