"""Channels module."""

from relay.channels.contracts import ChannelAdapter, ChannelMessageEnvelope
from relay.channels.whatsapp.adapter import WhatsAppAdapter
from relay.channels.web.adapter import WebWidgetAdapter

__all__ = ["ChannelAdapter", "ChannelMessageEnvelope", "WhatsAppAdapter", "WebWidgetAdapter"]
