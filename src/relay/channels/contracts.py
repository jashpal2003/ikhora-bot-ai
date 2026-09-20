"""Channel Adapter Protocol and Normalized Channel Message Envelope."""

from datetime import datetime, timezone
from typing import Any, Protocol
from pydantic import BaseModel, Field

from relay.platform.ids import generate_id


class ChannelMessageEnvelope(BaseModel):
    """Normalized inbound message from any channel."""

    channel: str  # "whatsapp", "teams", "web"
    tenant_id: str
    external_sender_id: str  # E.164 phone, Entra OID, browser session token
    external_message_id: str
    display_name: str | None = None
    text: str
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    raw_payload_ref: str | None = None
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str = Field(default_factory=lambda: generate_id("trace"))


class ChannelAdapter(Protocol):
    """Protocol implemented by channel ingress/egress adapters."""

    async def verify_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """Verify provider cryptographic signature (e.g. HMAC-SHA256)."""
        ...

    async def normalize_inbound(self, payload: dict[str, Any], tenant_id: str) -> ChannelMessageEnvelope:
        """Translate channel-specific payload to normalized envelope."""
        ...

    async def send_outbound(self, recipient_id: str, text: str, ctx: dict[str, Any]) -> str:
        """Dispatch reply to customer through channel provider."""
        ...
