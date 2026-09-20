"""Microsoft Graph connector with On-Behalf-Of (OBO) token exchange."""

from typing import Any


class GraphConnector:
    """Enterprise connector for SharePoint, OneDrive, and Teams via Microsoft Graph OBO."""

    def __init__(self, tenant_id: str, client_id: str = "mock-graph-client") -> None:
        self.tenant_id = tenant_id
        self.client_id = client_id

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "service": "microsoft_graph", "obo_enabled": True}

    async def read(self, entity: str, record_id: str, ctx: dict[str, Any]) -> dict[str, Any]:
        """Read DriveItem or List item with user's delegated token."""
        return {
            "entity": entity,
            "id": record_id,
            "title": "Refund Policy.docx",
            "webUrl": f"https://tenant.sharepoint.com/sites/ops/docs/{record_id}",
        }

    async def search(self, entity: str, query: str, ctx: dict[str, Any]) -> list[dict[str, Any]]:
        """Search Graph resources."""
        return [
            {
                "id": "doc_graph_01",
                "name": "Damaged Goods Policy v12",
                "webUrl": "https://tenant.sharepoint.com/policies/damaged_goods",
            }
        ]

    async def write(
        self,
        entity: str,
        payload: dict[str, Any],
        ctx: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Send Teams channel notification or update list item."""
        return {
            "id": f"msg_{idempotency_key[:8]}",
            "status": "delivered",
            "channel": payload.get("channel", "#support"),
        }
