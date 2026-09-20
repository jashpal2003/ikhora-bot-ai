"""Connector Protocol per §13.2."""

from typing import Any, Protocol


class Connector(Protocol):
    """Abstract protocol required for all external enterprise connectors."""

    async def health(self) -> dict[str, Any]:
        """Check connection health and token validity."""
        ...

    async def read(self, entity: str, record_id: str, ctx: dict[str, Any]) -> dict[str, Any]:
        """Fetch a single record by entity type and ID."""
        ...

    async def search(self, entity: str, query: str, ctx: dict[str, Any]) -> list[dict[str, Any]]:
        """Search records within the connector target."""
        ...

    async def write(
        self,
        entity: str,
        payload: dict[str, Any],
        ctx: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Create or update a record idempotently."""
        ...
