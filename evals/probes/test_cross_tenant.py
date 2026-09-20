"""Automated Cross-Tenant Probe Suite (ADR 002, §6.3)."""

from relay.platform.errors import TenantContextMissingError
from relay.platform.tenancy import get_current_tenant_id


def test_tenant_context_is_enforced() -> None:
    """Assert that accessing tenant context without setting it raises TenantContextMissingError."""
    try:
        get_current_tenant_id()
        assert False, "Expected TenantContextMissingError"
    except TenantContextMissingError:
        pass
