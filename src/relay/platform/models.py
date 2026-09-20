"""SQLAlchemy declarative models reflecting schema.sql."""

from datetime import datetime, timezone
from typing import Any
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base declarative class for all models."""
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    plan = Column(Text, nullable=False, default="starter")
    region = Column(Text, nullable=False, default="weu")
    settings = Column(JSONB, nullable=False, default=dict)
    status = Column(Text, nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    contacts = relationship("Contact", back_populates="tenant", cascade="all, delete-orphan")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Text, primary_key=True)
    tenant_id = Column(Text, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    display_name = Column(Text)
    profile = Column(JSONB, nullable=False, default=dict)
    consent = Column(JSONB, nullable=False, default=dict)
    merged_into = Column(Text, ForeignKey("contacts.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="contacts")
    identities = relationship("ContactIdentity", back_populates="contact", cascade="all, delete-orphan")


class ContactIdentity(Base):
    __tablename__ = "contact_identities"

    id = Column(Text, primary_key=True)
    tenant_id = Column(Text, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(Text, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    channel = Column(Text, nullable=False)
    external_id = Column(Text, nullable=False)
    verified = Column(Boolean, nullable=False, default=False)
    confidence = Column(Numeric(4, 3), nullable=False, default=1.000)
    match_reason = Column(Text, nullable=False, default="channel_exact")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    contact = relationship("Contact", back_populates="identities")


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Text, primary_key=True)
    tenant_id = Column(Text, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    type = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    config = Column(JSONB, nullable=False, default=dict)
    status = Column(Text, nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Text, primary_key=True)
    tenant_id = Column(Text, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(Text, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    channel_id = Column(Text, ForeignKey("channels.id"), nullable=False)
    status = Column(Text, nullable=False, default="open", index=True)
    priority = Column(Text, nullable=False, default="normal")
    assignee_id = Column(Text, nullable=True)
    autonomy_mode = Column(Text, nullable=False, default="assist")
    last_msg_at = Column(DateTime(timezone=True), nullable=True)
    sla_due_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Text, primary_key=True)
    tenant_id = Column(Text, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(Text, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    direction = Column(Text, nullable=False)
    author_type = Column(Text, nullable=False)
    author_id = Column(Text, nullable=True)
    content = Column(JSONB, nullable=False)
    external_id = Column(Text, nullable=True)
    channel_external_key = Column(Text, nullable=True, unique=True)
    agent_run_id = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    conversation = relationship("Conversation", back_populates="messages")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Text, primary_key=True)
    tenant_id = Column(Text, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(Text, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    contact_id = Column(Text, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    title = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="new", index=True)
    priority = Column(Text, nullable=False, default="normal")
    assigned_to = Column(Text, nullable=True)
    handoff_packet = Column(JSONB, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Text, primary_key=True)
    tenant_id = Column(Text, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(Text, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    agent_version = Column(Text, nullable=False)
    workflow_id = Column(Text, nullable=False)
    trigger = Column(JSONB, nullable=False)
    status = Column(Text, nullable=False)
    outcome = Column(JSONB, nullable=True)
    budget = Column(JSONB, nullable=False)
    consumed = Column(JSONB, nullable=False, default=dict)
    trace_id = Column(Text, nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime(timezone=True), nullable=True)


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id = Column(Text, primary_key=True)
    tenant_id = Column(Text, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Text, ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)
    step_id = Column(Text, nullable=True)
    tool_name = Column(Text, nullable=False)
    tool_version = Column(Text, nullable=False)
    side_effect = Column(Text, nullable=False)
    idempotency_key = Column(Text, nullable=False)
    input_hash = Column(Text, nullable=False)
    output_ref = Column(Text, nullable=True)
    status = Column(Text, nullable=False)
    policy_verdict = Column(JSONB, nullable=False)
    approval_id = Column(Text, nullable=True)
    external_ref = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Text, primary_key=True)
    tenant_id = Column(Text, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    event_type = Column(Text, nullable=False)
    actor_type = Column(Text, nullable=False)
    actor_id = Column(Text, nullable=True)
    on_behalf_of = Column(Text, nullable=True)
    target_type = Column(Text, nullable=True)
    target_id = Column(Text, nullable=True)
    correlation_id = Column(Text, nullable=False, index=True)
    causation_id = Column(Text, nullable=True)
    data = Column(JSONB, nullable=False)
    data_ref = Column(Text, nullable=True)
    prev_hash = Column(Text, nullable=True)
    hash = Column(Text, nullable=False)


class Outbox(Base):
    __tablename__ = "outbox"

    id = Column(Text, primary_key=True)
    tenant_id = Column(Text, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    topic = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
