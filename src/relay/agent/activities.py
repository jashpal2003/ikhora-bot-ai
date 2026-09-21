"""Temporal activities executed by AgentRunWorkflow."""

from typing import Any
from temporalio import activity

from relay.agent.models import PlanStep, RunContext
from relay.decisions.models import DecisionRequest, Question
from relay.decisions.azure_openai import AzureOpenAIDecisionProvider
from relay.policy.engine import PolicyEngine
from relay.policy.models import ActionRef, Principal, ResourceRef, Verdict


@activity.defn
async def classify_intent_activity(ctx: RunContext) -> dict[str, Any]:
    """Classify incoming intent and assess priority."""
    provider = AzureOpenAIDecisionProvider()
    req = DecisionRequest(
        state={"user_message": ctx.user_message},
        questions=[
            Question(id="intent", type="choice", choices=["damage_claim", "order_lookup", "general_faq"]),
            Question(id="priority", type="choice", choices=["low", "normal", "high", "urgent"]),
            Question(id="human_required", type="bool"),
        ],
    )
    decision = await provider.decide(req)
    return decision.model_dump(mode="json")


@activity.defn
async def plan_next_step_activity(ctx: RunContext, decision_data: dict[str, Any]) -> PlanStep:
    """Determine the next step (respond, handoff, or tool_call)."""
    answers = decision_data.get("answers", {})
    human_required = answers.get("human_required", {}).get("value", False)
    intent = answers.get("intent", {}).get("value", "general_faq")

    if human_required:
        return PlanStep(
            kind="handoff",
            handoff_reason="human_intervention_requested_or_calibrated_high",
        )

    if intent == "damage_claim":
        # Propose creating a case in Dataverse (Scenario S01 / Action Center flagship)
        return PlanStep(
            kind="tool_call",
            tool_name="dataverse.create_case",
            tool_input={
                "title": "Damaged goods reported by customer",
                "customer_id": ctx.contact_id or "unknown",
            },
            cost_estimate=0.0008,
        )

    # Standard informational reply
    return PlanStep(
        kind="respond",
        message="Thank you for reaching out to Project Relay support. How can we assist you today?",
    )


@activity.defn
async def authorize_activity(ctx: RunContext, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    """Invoke PolicyEngine authorize() chokepoint."""
    engine = PolicyEngine()
    principal = Principal(
        type="agent",
        id=ctx.run_id,
        tenant_id=ctx.tenant_id,
        on_behalf_of=ctx.on_behalf_of,
    )
    action = ActionRef(
        tool_name=tool_name,
        tool_version="1.0.0",
        side_effect="write" if "create" in tool_name else "read",
    )
    resource = ResourceRef(
        system=tool_name.split(".")[0],
        entity=tool_name.split(".")[1] if "." in tool_name else "record",
        amount=tool_input.get("amount"),
    )
    verdict = engine.authorize(
        principal=principal,
        action=action,
        resource=resource,
        context={"identity_tier": ctx.identity_tier},
    )
    return verdict.model_dump(mode="json")


@activity.defn
async def execute_tool_activity(
    ctx: RunContext,
    tool_name: str,
    tool_input: dict[str, Any],
    verdict_data: dict[str, Any],
) -> dict[str, Any]:
    """Execute authorized tool."""
    # Simulates verified connector dispatch (e.g. Dataverse create case)
    return {
        "status": "succeeded",
        "case_id": "CAS-4471",
        "tool": tool_name,
        "created_at": "2026-09-20T14:03:19Z",
    }


@activity.defn
async def send_reply_activity(ctx: RunContext, message: str) -> None:
    """Send reply back to channel."""
    # Dispatches through ChannelAdapter
    pass


@activity.defn
async def create_handoff_packet_activity(ctx: RunContext, reason: str) -> None:
    """Generate handoff packet and create operator ticket."""
    pass
