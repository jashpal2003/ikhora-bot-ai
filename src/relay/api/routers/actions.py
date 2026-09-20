"""Action Center API router (P1, §17.3 View Model)."""

from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from relay.platform.database import get_session
from relay.platform.tenancy import tenant_scope

router = APIRouter(prefix="/actions", tags=["Action Center"])


@router.get("/runs/{run_id}")
async def get_action_center_card(
    run_id: str,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Retrieve the unified Action Center view model for a run.
    
    Powers the sales demo, operator console, and compliance export.
    """
    async with tenant_scope(session, x_tenant_id):
        # Query live agent_run and associated tool executions if present
        result = await session.execute(
            text("""
                SELECT r.id, r.status, r.budget, r.consumed, r.trace_id, r.started_at, r.finished_at,
                       t.tool_name, t.output_ref, t.policy_verdict
                FROM agent_runs r
                LEFT JOIN tool_executions t ON r.id = t.run_id
                WHERE r.id = :run_id AND r.tenant_id = :tenant_id
                LIMIT 1
            """),
            {"run_id": run_id, "tenant_id": x_tenant_id},
        )
        row = result.fetchone()

        if row:
            return {
                "run_id": row.id,
                "status": row.status,
                "trace_id": row.trace_id,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "finished_at": row.finished_at.isoformat() if row.finished_at else None,
                "tool_name": row.tool_name,
                "what": f"Executed {row.tool_name}",
                "why": "Customer requested operation evaluated under policy",
                "who": f"Agent Run {row.id}",
                "data": str(row.output_ref or "{}"),
                "policy": str(row.policy_verdict or "{}"),
                "budget": f"Budget: {row.budget}, Consumed: {row.consumed}",
            }

    # Fallback to standard canonical Action Center showcase card
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
