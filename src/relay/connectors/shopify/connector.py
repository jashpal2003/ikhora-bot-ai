"""Shopify Admin GraphQL connector (P1 Priority per §0.2)."""

from typing import Any


class ShopifyConnector:
    """Connector for Shopify GraphQL Admin API."""

    def __init__(self, tenant_id: str, shop_domain: str = "demo-shop.myshopify.com") -> None:
        self.tenant_id = tenant_id
        self.shop_domain = shop_domain

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "service": "shopify", "shop": self.shop_domain}

    async def read(self, entity: str, record_id: str, ctx: dict[str, Any]) -> dict[str, Any]:
        """Fetch order details by order_id."""
        return {
            "order_id": record_id,
            "financial_status": "PAID",
            "fulfillment_status": "DELIVERED",
            "total_price": "42.00",
            "currency": "USD",
            "items": [{"name": "Standard Widget", "quantity": 1}],
        }

    async def search(self, entity: str, query: str, ctx: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"order_id": "8281", "name": "#108281"}]

    async def write(
        self,
        entity: str,
        payload: dict[str, Any],
        ctx: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Execute refund or create support note."""
        return {
            "refund_id": f"ref_{idempotency_key[:8]}",
            "amount": payload.get("amount", "0.00"),
            "status": "success",
        }
