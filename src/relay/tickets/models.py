"""Ticket models and handoff packet schemas."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class HandoffPacket(BaseModel):
    """Structured escalation packet for human operators per scenario S06."""

    reason: str  # e.g., "insufficient_evidence", "policy_approval_denied", "budget_exhausted"
    customer_intent: str
    customer_frustration_score: float = Field(ge=0.0, le=1.0, default=0.0)
    summary_of_dialogue: str
    actions_attempted: list[dict[str, Any]] = Field(default_factory=list)
    suggested_operator_action: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Ticket(BaseModel):
    id: str
    tenant_id: str
    conversation_id: str | None
    contact_id: str | None
    title: str
    status: TicketStatus
    priority: str
    assigned_to: str | None
    handoff_packet: HandoffPacket | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
