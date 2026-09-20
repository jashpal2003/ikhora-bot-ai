"""Action Center API router (P1, §17.3 View Model)."""

from typing import Any
from fastapi import APIRouter, Header

router = APIRouter(prefix="/actions", tags=["Action Center"])


@router.get("/runs/{run_id}")
async def get_action_center_card(
    run_id: str,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> dict[str, Any]:
    """Retrieve the unified Action Center view model for a run.
    
    Powers the sales demo, operator console, and compliance export.
    """
    return {
        "run_id": run_id,
        "channel": "WhatsApp",
        "sender": "+971 5X XXX XXXX",
        "started_at": "14:03:11",
        "finished_at": "14:03:19",
        "cost_usd": 0.0041,
        "what": "Created case CAS-4471 in Dataverse",
        "why": "Customer reported damaged order; policy requires case for claims",
        "who": 'Agent "Support Employee v7" on behalf of priya@customer.com',
        "data": "Order 8281 (Shopify, read 14:03:14) · Contact verified via OTP",
        "evidence": "Damaged Goods Policy §4.2 (SharePoint, v12, 4 days old) ✓ validated",
        "policy": "refund_threshold — amount $42 below $50 → auto-approved",
        "decision": "intent=damage_claim (0.94) · priority=high (0.88) · human=no (0.21)",
        "result": "✓ CAS-4471 created · Teams notified #support · reply sent 14:03:19",
        "budget": "4 / 12 steps · 8.2s / 90s · $0.0041 / $0.50",
    }
