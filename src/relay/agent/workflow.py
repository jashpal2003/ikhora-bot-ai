"""Durable Temporal Workflow for Agent Execution Loop (P4, §7.3)."""

from datetime import timedelta
from typing import Any
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from relay.agent.activities import (
        authorize_activity,
        classify_intent_activity,
        create_handoff_packet_activity,
        execute_tool_activity,
        plan_next_step_activity,
        send_reply_activity,
    )
    from relay.agent.models import PlanStep, RunContext, RunOutcome
    from relay.policy.budgets import BudgetLedger


@workflow.defn
class AgentRunWorkflow:
    """The auditable, durable agent loop running on Temporal."""

    def __init__(self) -> None:
        self._approval_granted: bool | None = None
        self._approval_received: bool = False

    @workflow.signal
    def approve(self, decision: bool) -> None:
        """Signal received when human operator reviews an approval request."""
        self._approval_granted = decision
        self._approval_received = True

    @workflow.run
    async def run(self, ctx: RunContext) -> RunOutcome:
        """Execute deterministic plan-act-verify loop with budget enforcement."""
        ledger = BudgetLedger()
        activity_retry = RetryPolicy(maximum_attempts=2)

        # 1. Classify intent via DecisionProvider
        decision = await workflow.execute_activity(
            classify_intent_activity,
            ctx,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=activity_retry,
        )

        while True:
            # 2. Assert budget constraint (P9)
            exhausted, budget_reason = ledger.check_exhausted(ctx.budget)
            if exhausted:
                await workflow.execute_activity(
                    create_handoff_packet_activity,
                    args=[ctx, budget_reason or "budget_exhausted"],
                    start_to_close_timeout=timedelta(seconds=10),
                )
                return RunOutcome.handed_off(
                    reason="budget_exhausted",
                    steps=ledger.consumed_steps,
                    cost=ledger.consumed_usd,
                )

            # 3. Plan next step
            plan: PlanStep = await workflow.execute_activity(
                plan_next_step_activity,
                args=[ctx, decision],
                start_to_close_timeout=timedelta(seconds=15),
            )

            # 4. Handle response termination
            if plan.kind == "respond":
                reply = plan.message or "Acknowledged."
                await workflow.execute_activity(
                    send_reply_activity,
                    args=[ctx, reply],
                    start_to_close_timeout=timedelta(seconds=10),
                )
                ledger.consume_step(plan.cost_estimate)
                return RunOutcome.completed(
                    reply_text=reply,
                    steps=ledger.consumed_steps,
                    cost=ledger.consumed_usd,
                )

            # 5. Handle handoff termination
            if plan.kind == "handoff":
                await workflow.execute_activity(
                    create_handoff_packet_activity,
                    args=[ctx, plan.handoff_reason or "general_escalation"],
                    start_to_close_timeout=timedelta(seconds=10),
                )
                ledger.consume_step(plan.cost_estimate)
                return RunOutcome.handed_off(
                    reason=plan.handoff_reason or "general_escalation",
                    steps=ledger.consumed_steps,
                    cost=ledger.consumed_usd,
                )

            # 6. Policy Authorization Chokepoint (P1)
            tool_name = plan.tool_name or "unknown.tool"
            verdict = await workflow.execute_activity(
                authorize_activity,
                args=[ctx, tool_name, plan.tool_input],
                start_to_close_timeout=timedelta(seconds=10),
            )

            # Check if approval required (e.g., manager sign-off)
            if verdict.get("decision") == "require_approval":
                # Durable pause surviving restarts (up to 48h)
                try:
                    await workflow.wait_condition(
                        lambda: self._approval_received,
                        timeout=timedelta(hours=48),
                    )
                except TimeoutError:
                    return RunOutcome.handed_off(
                        reason="approval_timed_out",
                        steps=ledger.consumed_steps,
                        cost=ledger.consumed_usd,
                    )

                if not self._approval_granted:
                    return RunOutcome.rejected(
                        steps=ledger.consumed_steps,
                        cost=ledger.consumed_usd,
                    )

            elif verdict.get("decision") == "deny":
                await workflow.execute_activity(
                    create_handoff_packet_activity,
                    args=[ctx, "policy_denied"],
                    start_to_close_timeout=timedelta(seconds=10),
                )
                return RunOutcome.handed_off(
                    reason="policy_denied",
                    steps=ledger.consumed_steps,
                    cost=ledger.consumed_usd,
                )

            # 7. Execute Tool Activity
            tool_result = await workflow.execute_activity(
                execute_tool_activity,
                args=[ctx, tool_name, plan.tool_input, verdict],
                start_to_close_timeout=timedelta(seconds=30),
            )

            # 8. Update run context and consume budget
            ledger.consume_step(
                cost_estimate=plan.cost_estimate,
                is_tool_call=True,
                is_destructive=False,
            )
            ctx.state["last_tool_result"] = tool_result

            # Finalize run after tool action (in this workflow pattern)
            final_reply = f"I have processed your request. Created case {tool_result.get('case_id')}."
            await workflow.execute_activity(
                send_reply_activity,
                args=[ctx, final_reply],
                start_to_close_timeout=timedelta(seconds=10),
            )
            return RunOutcome.completed(
                reply_text=final_reply,
                steps=ledger.consumed_steps,
                cost=ledger.consumed_usd,
            )
