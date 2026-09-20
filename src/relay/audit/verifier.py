"""Audit chain integrity verifier."""

import json
from dataclasses import dataclass
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from relay.audit.writer import compute_audit_hash


@dataclass
class ChainVerificationResult:
    is_valid: bool
    events_verified: int
    broken_at_id: str | None = None
    expected_hash: str | None = None
    actual_hash: str | None = None


class AuditVerifier:
    """Verifies that audit_events rows have not been tampered with or truncated."""

    @staticmethod
    async def verify_tenant_chain(session: AsyncSession, tenant_id: str) -> ChainVerificationResult:
        """Scan all audit events for a tenant in chronological order and re-verify hashes."""
        result = await session.execute(
            text("""
                SELECT id, tenant_id, occurred_at, event_type, actor_type, actor_id,
                       on_behalf_of, target_type, target_id, correlation_id, causation_id,
                       data, data_ref, prev_hash, hash
                FROM audit_events
                WHERE tenant_id = :tenant_id
                ORDER BY occurred_at ASC, id ASC
            """),
            {"tenant_id": tenant_id},
        )
        rows = result.fetchall()
        if not rows:
            return ChainVerificationResult(is_valid=True, events_verified=0)

        expected_prev_hash: str | None = None

        for count, row in enumerate(rows, start=1):
            (
                event_id,
                t_id,
                occurred_at,
                event_type,
                actor_type,
                actor_id,
                on_behalf_of,
                target_type,
                target_id,
                correlation_id,
                causation_id,
                data,
                data_ref,
                stored_prev_hash,
                stored_hash,
            ) = row

            # Verify chain linkage
            if stored_prev_hash != expected_prev_hash:
                return ChainVerificationResult(
                    is_valid=False,
                    events_verified=count - 1,
                    broken_at_id=event_id,
                    expected_hash=expected_prev_hash,
                    actual_hash=stored_prev_hash,
                )

            # Reconstruct the canonical payload
            parsed_data = json.loads(data) if isinstance(data, str) else data
            hashable_event = {
                "id": event_id,
                "tenant_id": t_id,
                "occurred_at": occurred_at.isoformat(),
                "event_type": event_type,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "on_behalf_of": on_behalf_of,
                "target_type": target_type,
                "target_id": target_id,
                "correlation_id": correlation_id,
                "causation_id": causation_id,
                "data": parsed_data,
                "data_ref": data_ref,
            }

            calculated_hash = compute_audit_hash(stored_prev_hash, hashable_event)
            if calculated_hash != stored_hash:
                return ChainVerificationResult(
                    is_valid=False,
                    events_verified=count - 1,
                    broken_at_id=event_id,
                    expected_hash=calculated_hash,
                    actual_hash=stored_hash,
                )

            expected_prev_hash = stored_hash

        return ChainVerificationResult(is_valid=True, events_verified=len(rows))
