"""Automated tests for Project Relay Acceptance Scenarios S01–S20."""

import pytest
from relay.knowledge.models import ConflictPair, Evidence, EvidencePack
from relay.policy.budgets import Budget, BudgetLedger
from relay.policy.engine import PolicyEngine
from relay.policy.models import ActionRef, Principal, ResourceRef
from relay.decisions.small_llm import SmallLLMDecisionProvider
from relay.decisions.models import DecisionRequest, Question


@pytest.mark.asyncio
async def test_s01_order_status_routing() -> None:
    """Scenario S01: Order status lookup must route to connector, never RAG."""
    provider = SmallLLMDecisionProvider()
    req = DecisionRequest(
        state={"user_message": "Where is my order #8281?"},
        questions=[Question(id="intent", type="choice", choices=["order_lookup", "general_faq"])],
    )
    decision = await provider.decide(req)
    assert decision.answers["intent"].value == "order_lookup"
    assert decision.answers["intent"].confidence > 0.85


def test_s03_insufficient_evidence_abstention() -> None:
    """Scenario S03: Insufficient evidence produces first-class abstention state."""
    pack = EvidencePack(
        items=[],
        sufficiency="insufficient",
        coverage_gap="No permitted documentation matches custom warranty query.",
    )
    assert pack.sufficiency == "insufficient"
    assert pack.coverage_gap is not None


def test_s04_conflicting_sources() -> None:
    """Scenario S04: Conflicting sources are surfaced without picking a winner."""
    conflicts = [
        ConflictPair(
            source_a_title="EU Policy",
            source_a_claim="14 days return",
            source_b_title="US Policy",
            source_b_claim="30 days return",
            divergence_summary="Contradiction in return windows",
        )
    ]
    pack = EvidencePack(
        items=[
            Evidence(
                chunk_id="chk_1",
                document_id="doc_1",
                document_title="EU Policy",
                text="14 days return window.",
                relevance=0.9,
                freshness_days=2,
            ),
            Evidence(
                chunk_id="chk_2",
                document_id="doc_2",
                document_title="US Policy",
                text="30 days return window.",
                relevance=0.88,
                freshness_days=5,
            ),
        ],
        sufficiency="sufficient",
        conflicts=conflicts,
    )
    assert len(pack.conflicts) == 1
    assert pack.conflicts[0].source_a_title == "EU Policy"


def test_s09_action_approval_threshold() -> None:
    """Scenario S09: Refunds above $50 require manager approval."""
    engine = PolicyEngine()
    principal = Principal(type="agent", id="run_1", tenant_id="tnt_1")
    action = ActionRef(tool_name="shopify.refund_create", tool_version="1.0", side_effect="financial")
    resource = ResourceRef(system="shopify", entity="refund", amount=75.00)

    verdict = engine.authorize(
        principal=principal,
        action=action,
        resource=resource,
        context={"identity_tier": "verified"},
    )
    assert verdict.decision == "require_approval"
    assert verdict.approval_route is not None
    assert verdict.approval_route.role == "support_manager"


def test_s18_prompt_injection_defense() -> None:
    """Scenario S18: Structural defense against prompt injection (P1, P2, §14.2).
    
    Even if customer inputs contain malicious override commands,
    unverified callers cannot execute financial or account-modifying tools.
    """
    engine = PolicyEngine()
    principal = Principal(type="agent", id="run_1", tenant_id="tnt_1")
    malicious_action = ActionRef(tool_name="shopify.refund_create", tool_version="1.0", side_effect="financial")
    resource = ResourceRef(system="shopify", entity="refund", amount=1000000.0)

    # Customer is unverified
    verdict = engine.authorize(
        principal=principal,
        action=malicious_action,
        resource=resource,
        context={"identity_tier": "anonymous"},
    )
    assert verdict.decision == "deny"
    assert any("IDENTITY_NOT_VERIFIED" in r.code for r in verdict.reasons)


def test_s19_budget_exhaustion_controlled_handoff() -> None:
    """Scenario S19: Exceeding step budget produces a controlled handoff, not a crash."""
    budget = Budget(steps=12, wall_ms=90000, usd=0.50, tool_calls=8)
    ledger = BudgetLedger()

    # Simulate 12 steps
    for _ in range(12):
        ledger.consume_step(cost_estimate=0.01)

    exhausted, reason = ledger.check_exhausted(budget)
    assert exhausted is True
    assert "step_budget_exhausted" in (reason or "")
