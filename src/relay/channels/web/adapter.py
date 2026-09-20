"""Customer Web Widget Adapter."""

from typing import Any
from relay.channels.contracts import ChannelMessageEnvelope


class WebWidgetAdapter:
    """Adapter for embedded Preact Shadow DOM customer widget."""

    def normalize_inbound(self, payload: dict[str, Any], tenant_id: str) -> ChannelMessageEnvelope:
        return ChannelMessageEnvelope(
            channel="web",
            tenant_id=tenant_id,
            external_sender_id=payload.get("session_id", "anon_session"),
            external_message_id=payload.get("message_id", "msg_web"),
            display_name=payload.get("visitor_name"),
            text=payload.get("text", ""),
        )

    async def send_outbound(self, recipient_id: str, text: str, ctx: dict[str, Any]) -> str:
        return "widget_ack"
