import secrets
import time

try:
    import ulid  # type: ignore[import-untyped]

    def _generate_ulid_str() -> str:
        return str(ulid.new().str)
except ImportError:
    # Built-in Crockford Base32 fallback when ulid-py is not installed
    _CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

    def _generate_ulid_str() -> str:
        timestamp_ms = int(time.time() * 1000)
        time_chars = []
        for _ in range(10):
            time_chars.append(_CROCKFORD_BASE32[timestamp_ms & 0x1F])
            timestamp_ms >>= 5
        time_part = "".join(reversed(time_chars))
        random_part = "".join(secrets.choice(_CROCKFORD_BASE32) for _ in range(16))
        return f"{time_part}{random_part}"

# Recognized entity prefixes
PREFIX_MAP = {
    "tenant": "tnt",
    "contact": "cnt",
    "identity": "idt",
    "conversation": "cnv",
    "message": "msg",
    "run": "run",
    "step": "stp",
    "tool_execution": "tex",
    "audit": "aud",
    "ticket": "tkt",
    "knowledge_source": "ksr",
    "document": "doc",
    "chunk": "chk",
    "acl": "acl",
    "approval": "apr",
    "channel": "chn",
    "event": "evt",
    "trace": "trc",
}


def generate_id(entity_type: str) -> str:
    """Generate a type-prefixed, lexicographically sortable ULID string.
    
    Example:
        generate_id("run") -> "run_01J8XQPKZ7M40K0..."
    """
    prefix = PREFIX_MAP.get(entity_type, entity_type)
    raw_ulid = _generate_ulid_str()
    return f"{prefix}_{raw_ulid}"


def validate_id_prefix(entity_id: str, expected_prefix: str) -> bool:
    """Validate that an identifier matches its expected type prefix."""
    prefix = PREFIX_MAP.get(expected_prefix, expected_prefix)
    return entity_id.startswith(f"{prefix}_")
