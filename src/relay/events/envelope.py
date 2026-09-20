"""Standardized event envelope per §7.2."""

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field

from relay.platform.ids import generate_id


class Actor(BaseModel):
    """The subject initiating the event."""

    type: Literal["human", "agent", "system", "connector"]
    id: str | None = None
    on_behalf_of: str | None = None  # Delegating enterprise principal


class EventEnvelope(BaseModel):
    """Canonical event envelope for all system and audit events."""

    event_id: str = Field(default_factory=lambda: generate_id("event"))
    event_type: str
    event_version: int = 1
    tenant_id: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: Actor
    correlation_id: str  # trace_id
    causation_id: str | None = None
    data: dict[str, Any]
    data_ref: str | None = None  # Blob URI for offloaded payloads
