"""Multi-tenant context manager enforcing PostgreSQL Row-Level Security."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from relay.platform.errors import TenantContextMissingError

_current_tenant_id: ContextVar[str | None] = ContextVar("current_tenant_id", default=None)


def get_current_tenant_id() -> str:
    """Retrieve the current active tenant ID from context, raising an error if absent."""
    tid = _current_tenant_id.get()
    if not tid:
        raise TenantContextMissingError("No active tenant context found in current task.")
    return tid


@asynccontextmanager
async def tenant_scope(
    session: AsyncSession, 
    tenant_id: str
) -> AsyncGenerator[AsyncSession, Any]:
    """Execute a database block scoped to a specific tenant.
    
    Uses `set_config('relay.tenant_id', :tid, true)` with `is_local = true`
    so the configuration is transaction-scoped. This guarantees that pooled
    connections in PgBouncer cannot leak tenant identity across requests.
    """
    token = _current_tenant_id.set(tenant_id)
    try:
        await session.execute(
            text("SELECT set_config('relay.tenant_id', :tid, true)"),
            {"tid": tenant_id},
        )
        yield session
    finally:
        _current_tenant_id.reset(token)
