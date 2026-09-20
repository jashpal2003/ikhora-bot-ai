"""Unit tests for cryptographic audit hash chaining (ADR 012, §6.6)."""

from relay.audit.writer import compute_audit_hash, canonical_json


def test_audit_hash_chain_calculation() -> None:
    """Verify deterministic hash computation and continuity."""
    event_1 = {
        "id": "aud_01J8X01",
        "tenant_id": "tnt_01",
        "event_type": "ticket.created",
        "data": {"title": "Test Ticket"},
    }
    hash_1 = compute_audit_hash(None, event_1)
    assert len(hash_1) == 64  # SHA-256 hex string

    event_2 = {
        "id": "aud_01J8X02",
        "tenant_id": "tnt_01",
        "event_type": "tool.executed",
        "data": {"tool": "dataverse.create_case"},
    }
    hash_2 = compute_audit_hash(hash_1, event_2)
    assert len(hash_2) == 64
    assert hash_2 != hash_1


def test_canonical_json_key_order_invariance() -> None:
    """Verify that key ordering does not alter canonical serialization."""
    d1 = {"b": 2, "a": 1, "nested": {"z": 10, "y": 9}}
    d2 = {"nested": {"y": 9, "z": 10}, "a": 1, "b": 2}
    assert canonical_json(d1) == canonical_json(d2)
