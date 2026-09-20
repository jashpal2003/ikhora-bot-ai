"""Append-only audit writer with SHA-256 cryptographic hash-chaining."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from relay.platform.ids import generate_id


def canonical_json(data: dict[str, Any]) -> str:
    """Produce deterministic, sorted-key JSON serialization without whitespace."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def compute_audit_hash(prev_hash: str | None, event_data: dict[str, Any]) -> str:
    """Compute SHA-256 hash chaining: hash = sha256(prev_hash || canonical_json(event))."""
    serialized = canonical_json(event_data)
    hasher = hashlib.sha256()
    if prev_hash:
        hasher.update(prev_hash.encode("utf-8"))
    hasher.update(serialized.encode("utf-8"))
    return hasher.hexdigest()


class AuditWriter:
    """Writes immutable, hash-chained audit events."""

    @staticmethod
    async def record_event(
        session: AsyncSession,
        tenant_id: str,
        event_type: str,
        actor_type: str,
        actor_id: str | None,
        on_behalf_of: str | None,
        correlation_id: str,
        data: dict[str, Any],
        target_type: str | None = None,
        target_id: str | None = None,
        causation_id: str | None = None,
        data_ref: str | None = None,
    ) -> str:
        """Record an append-only audit event with verifiable hash continuity."""
        # 1. Fetch the latest head hash for this tenant (serial execution inside transaction)
        result = await session.execute(
            text("""
                SELECT hash FROM audit_events
                WHERE tenant_id = :tenant_id
                ORDER BY occurred_at DESC, id DESC
                LIMIT 1
                FOR UPDATE
            """),
            {"tenant_id": tenant_id},
        )
        row = result.fetchone()
        prev_hash = row[0] if row else None

        audit_id = generate_id("audit")
        occurred_at = datetime.now(timezone.utc)

        # 2. Prepare payload for hashing
        hashable_event = {
            "id": audit_id,
            "tenant_id": tenant_id,
            "occurred_at": occurred_at.isoformat(),
            "event_type": event_type,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "on_behalf_of": on_behalf_of,
            "target_type": target_type,
            "target_id": target_id,
            "correlation_id": correlation_id,
            "causation_id": causation_id,
            "data": data,
            "data_ref": data_ref,
        }

        # 3. Compute current cryptographic hash
        current_hash = compute_audit_hash(prev_hash, hashable_event)

        # 4. Insert into database
        await session.execute(
            text("""
                INSERT INTO audit_events (
                    id, tenant_id, occurred_at, event_type, actor_type, actor_id,
                    on_behalf_of, target_type, target_id, correlation_id, causation_id,
                    data, data_ref, prev_hash, hash
                ) VALUES (
                    :id, :tenant_id, :occurred_at, :event_type, :actor_type, :actor_id,
                    :on_behalf_of, :target_type, :target_id, :correlation_id, :causation_id,
                    :data, :data_ref, :prev_hash, :hash
                )
            """),
            {
                "id": audit_id,
                "tenant_id": tenant_id,
                "occurred_at": occurred_at,
                "event_type": event_type,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "on_behalf_of": on_behalf_of,
                "target_type": target_type,
                "target_id": target_id,
                "correlation_id": correlation_id,
                "causation_id": causation_id,
                "data": json.dumps(data),
                "data_ref": data_ref,
                "prev_hash": prev_hash,
                "hash": current_hash,
            },
        )
        return audit_id
