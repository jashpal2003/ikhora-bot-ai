"""Conversation models and message types."""

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class AutonomyMode(str, Enum):
    OBSERVE = "observe"  # Agent monitors only; human operators answer
    ASSIST = "assist"  # Agent drafts responses and actions for human review
    AUTONOMOUS = "autonomous"  # Agent takes policy-approved actions automatically


class ConversationStatus(str, Enum):
    OPEN = "open"
    PENDING = "pending"
    SNOOZED = "snoozed"
    CLOSED = "closed"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL_NOTE = "internal_note"


class AuthorType(str, Enum):
    CONTACT = "contact"
    AGENT = "agent"
    HUMAN = "human"
    SYSTEM = "system"


class MessageContent(BaseModel):
    text: str
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class Conversation(BaseModel):
    id: str
    tenant_id: str
    contact_id: str | None
    channel_id: str
    status: ConversationStatus
    priority: Priority
    assignee_id: str | None
    autonomy_mode: AutonomyMode
    last_msg_at: datetime | None
    sla_due_at: datetime | None
    version: int


class Message(BaseModel):
    id: str
    tenant_id: str
    conversation_id: str
    direction: MessageDirection
    author_type: AuthorType
    author_id: str | None
    content: MessageContent
    external_id: str | None = None
    agent_run_id: str | None = None
    created_at: datetime
