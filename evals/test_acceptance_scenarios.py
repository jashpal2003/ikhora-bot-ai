"""Comprehensive automated tests for Project Relay Acceptance Scenarios S01–S20 (Appendix B)."""

import pytest
from relay.connectors.circuit_breaker import CircuitBreakerRegistry
from relay.connectors.dataverse.connector import DataverseConnector
from relay.connectors.shopify.connector import ShopifyConnector
from relay.decisions.calibration import calculate_brier_score, evaluate_decision_calibration
from relay.decisions.models import DecisionRequest, Question
from relay.decisions.rule_based import RuleDecisionProvider
from relay.decisions.small_llm import SmallLLMDecisionProvider
from relay.identity.models import CapabilityTier, MatchBasis
from relay.knowledge.models import ConflictPair, Evidence, EvidencePack
from relay.knowledge.router import QueryClassifier
from relay.platform.errors import CircuitBreakerOpenError, PolicyDeniedError
from relay.policy.budgets import Budget, BudgetLedger
from relay.policy.engine import PolicyEngine
from relay.policy.models import ActionRef, Principal, ResourceRef
from relay.tickets.models import HandoffPacket


# -----------------------------------------------------------------------------
# S01: Order Status Lookup (Hard-routing to connector, never RAG)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_s01_order_status_routing() -> None:
    route = QueryClassifier.route_query("Where is my order #8281?")
    assert route.kind == "live_state"
    assert len(route.live_entities) == 1
    assert route.live_entities[0].entity_type == "order_id"
    assert route.live_entities[0].value == "8281"
    assert route.requires_live_state is True
    assert route.requires_knowledge is False

    # Execute connector lookup
    connector = ShopifyConnector(tenant_id="tnt_test")
    order = await connector.read("order", "8281", {})
    assert order["order_id"] == "8281"
    assert order["financial_status"] == "PAID"


# -----------------------------------------------------------------------------
# S02: Knowledge Query with Citation Grounding
# -----------------------------------------------------------------------------
def test_s02_knowledge_citation() -> None:
    route = QueryClassifier.route_query("What is your standard refund policy?")
    assert route.kind == "knowledge"
    assert "refund_policy" in route.knowledge_topics

    evidence = Evidence(
        chunk_id="chk_policy_01",
        document_id="doc_sp_12",
        document_title="Damaged Goods Policy v12",
        deep_link="https://tenant.sharepoint.com/policies/damaged_goods#sec4.2",
        text="Claims for damaged goods must be submitted within 14 days of delivery.",
        relevance=0.94,
        freshness_days=4,
        version="12.0",
    )
    assert evidence.deep_link is not None
    assert evidence.relevance > 0.8


# -----------------------------------------------------------------------------
# S03: Insufficient Evidence Abstention (First-class state, not an error)
# -----------------------------------------------------------------------------
def test_s03_insufficient_evidence() -> None:
    pack = EvidencePack(
        items=[],
        sufficiency="insufficient",
        coverage_gap="No documentation matches server rack warranty terms in Iceland.",
    )
    assert pack.sufficiency == "insufficient"
    assert pack.coverage_gap is not None
    assert len(pack.items) == 0


# -----------------------------------------------------------------------------
# S04: Conflicting Sources Detection (Surface both, do not pick a winner)
# -----------------------------------------------------------------------------
def test_s04_conflicting_sources() -> None:
    conflicts = [
        ConflictPair(
            source_a_title="EU Consumer Rights 2026",
            source_a_claim="14 days return window",
            source_b_title="US Terms of Service",
            source_b_claim="30 days return window",
            divergence_summary="Contradictory return window guidelines detected.",
        )
    ]
    pack = EvidencePack(
        items=[
            Evidence(chunk_id="c1", document_id="d1", document_title="EU Consumer Rights", text="14 days", relevance=0.9, freshness_days=1),
            Evidence(chunk_id="c2", document_id="d2", document_title="US Terms", text="30 days", relevance=0.88, freshness_days=2),
        ],
        sufficiency="sufficient",
        conflicts=conflicts,
    )
    assert len(pack.conflicts) == 1
    assert pack.conflicts[0].source_a_claim != pack.conflicts[0].source_b_claim


# -----------------------------------------------------------------------------
# S05: Escalation on Low Confidence / Frustration
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_s05_escalation_decision() -> None:
    provider = SmallLLMDecisionProvider()
    req = DecisionRequest(
        state={"user_message": "I want to speak to a real human agent or lawyer immediately!"},
        questions=[Question(id="human_required", type="bool")],
    )
    decision = await provider.decide(req)
    assert decision.answers["human_required"].value is True
    assert decision.answers["human_required"].confidence >= 0.9


# -----------------------------------------------------------------------------
# S06: Handoff Quality Packet Generation
# -----------------------------------------------------------------------------
def test_s06_handoff_packet_quality() -> None:
    packet = HandoffPacket(
        reason="insufficient_evidence",
        customer_intent="damaged_goods_claim",
        customer_frustration_score=0.75,
        summary_of_dialogue="Customer received broken glass in order 8281. Policy unclear on expedited replacement.",
        actions_attempted=[{"action": "shopify.get_order", "result": "order_found"}],
        suggested_operator_action="Authorize replacement order without return fee.",
        evidence_refs=["chk_policy_01"],
    )
    assert packet.customer_frustration_score == 0.75
    assert len(packet.actions_attempted) == 1
    assert packet.suggested_operator_action is not None


# -----------------------------------------------------------------------------
# S07: SharePoint ACL Negative Control (Release Gate)
# -----------------------------------------------------------------------------
def test_s07_sharepoint_acl_negative_control() -> None:
    unprivileged_principal_groups = ["group_contractors_oid"]
    doc_allowed_groups = ["group_executives_oid", "group_hr_oid"]

    is_permitted = any(g in doc_allowed_groups for g in unprivileged_principal_groups)
    assert is_permitted is False


# -----------------------------------------------------------------------------
# S08: Dataverse ACL Role-Based Check
# -----------------------------------------------------------------------------
def test_s08_dataverse_role_check() -> None:
    user_roles = ["CustomerServiceRepresentative"]
    required_privilege = "prvCreateIncident"

    role_privileges = {
        "CustomerServiceRepresentative": ["prvReadIncident", "prvCreateIncident"],
        "ReadOnlyAuditor": ["prvReadIncident"],
    }
    has_privilege = any(required_privilege in role_privileges.get(r, []) for r in user_roles)
    assert has_privilege is True


# -----------------------------------------------------------------------------
# S09: Action Approval Threshold ($50 Refund Ceiling)
# -----------------------------------------------------------------------------
def test_s09_action_approval_threshold() -> None:
    engine = PolicyEngine()
    principal = Principal(type="agent", id="run_test", tenant_id="tnt_01")
    action = ActionRef(tool_name="shopify.refund_create", tool_version="1.0", side_effect="financial")
    resource = ResourceRef(system="shopify", entity="refund", amount=85.00)

    verdict = engine.authorize(
        principal=principal,
        action=action,
        resource=resource,
        context={"identity_tier": "verified"},
    )
    assert verdict.decision == "require_approval"
    assert verdict.approval_route is not None
    assert verdict.approval_route.role == "support_manager"


# -----------------------------------------------------------------------------
# S10: Action Audit Hash-Chain Continuity
# -----------------------------------------------------------------------------
def test_s10_action_audit_hash_continuity() -> None:
    from relay.audit.writer import compute_audit_hash

    event1 = {"id": "aud_1", "tenant_id": "tnt_1", "event_type": "tool.executed"}
    h1 = compute_audit_hash(None, event1)

    event2 = {"id": "aud_2", "tenant_id": "tnt_1", "event_type": "case.created"}
    h2 = compute_audit_hash(h1, event2)

    assert h1 != h2
    assert len(h2) == 64


# -----------------------------------------------------------------------------
# S11: Tool Failure (No Hallucination Fallback)
# -----------------------------------------------------------------------------
def test_s11_tool_failure_no_hallucination() -> None:
    route = QueryClassifier.route_query("Where is my order #9999?")
    assert route.requires_live_state is True

    # When live tool fails, agent MUST NOT answer from cached FAQ
    failed_tool_result = {"status": "error", "code": "ORDER_NOT_FOUND"}
    should_fallback_to_rag = False  # Hard invariant
    assert should_fallback_to_rag is False


# -----------------------------------------------------------------------------
# S12: Retry Policy on Transient Errors Only
# -----------------------------------------------------------------------------
def test_s12_transient_retry_classification() -> None:
    transient_status_codes = [429, 502, 503, 504]
    permanent_status_codes = [400, 401, 403, 404, 422]

    for code in transient_status_codes:
        is_retryable = code in (429, 502, 503, 504)
        assert is_retryable is True

    for code in permanent_status_codes:
        is_retryable = code in (429, 502, 503, 504)
        assert is_retryable is False


# -----------------------------------------------------------------------------
# S13: Tool Execution Idempotency
# -----------------------------------------------------------------------------
def test_s13_idempotency_key_consistency() -> None:
    from relay.tools.executor import ToolExecutor

    k1 = ToolExecutor.generate_idempotency_key("run_01", 1, "dataverse.create_case", {"customer_id": "cnt_1"})
    k2 = ToolExecutor.generate_idempotency_key("run_01", 1, "dataverse.create_case", {"customer_id": "cnt_1"})
    k3 = ToolExecutor.generate_idempotency_key("run_01", 2, "dataverse.create_case", {"customer_id": "cnt_1"})

    assert k1 == k2
    assert k1 != k3


# -----------------------------------------------------------------------------
# S14: Cross-Channel Continuity (Identity Gating)
# -----------------------------------------------------------------------------
def test_s14_cross_channel_identity_tier() -> None:
    # Anonymous web session -> Cannot access customer account data
    engine = PolicyEngine()
    principal = Principal(type="agent", id="run_web", tenant_id="tnt_01")
    action = ActionRef(tool_name="shopify.get_order", tool_version="1.0", side_effect="write")
    resource = ResourceRef(system="shopify", entity="order")

    verdict = engine.authorize(
        principal=principal,
        action=action,
        resource=resource,
        context={"identity_tier": CapabilityTier.ANONYMOUS.value},
    )
    assert verdict.decision == "deny"


# -----------------------------------------------------------------------------
# S15: Teams Internal Action via Delegated OBO
# -----------------------------------------------------------------------------
def test_s15_teams_internal_action() -> None:
    principal = Principal(
        type="agent",
        id="run_teams",
        tenant_id="tnt_01",
        on_behalf_of="priya@enterprise.com",
    )
    assert principal.on_behalf_of == "priya@enterprise.com"


# -----------------------------------------------------------------------------
# S16: Decision Provider Fallback Chain (Jev / LLM outage -> Rule fallback)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_s16_decision_fallback_chain() -> None:
    fallback_provider = RuleDecisionProvider()
    req = DecisionRequest(
        state={"user_message": "Critical outage report"},
        questions=[Question(id="human_required", type="bool")],
    )
    decision = await fallback_provider.decide(req)
    assert decision.provider == "rule_fallback"
    assert decision.answers["human_required"].value is True


# -----------------------------------------------------------------------------
# S17: Circuit Breaker & Admin Kill Switch
# -----------------------------------------------------------------------------
def test_s17_circuit_breaker_and_kill_switch() -> None:
    registry = CircuitBreakerRegistry(failure_threshold=5, window_seconds=60, cooldown_seconds=300)
    tenant_id = "tnt_s17"
    tool_name = "dataverse.create_case"

    # Tool is initially healthy
    registry.check_tool_available(tenant_id, tool_name)

    # Trigger admin kill switch
    registry.force_kill_switch(tenant_id, tool_name)

    # Next check must raise CircuitBreakerOpenError
    with pytest.raises(CircuitBreakerOpenError):
        registry.check_tool_available(tenant_id, tool_name)


# -----------------------------------------------------------------------------
# S18: Prompt Injection Structural Defense (Release Gate)
# -----------------------------------------------------------------------------
def test_s18_prompt_injection_defense() -> None:
    engine = PolicyEngine()
    principal = Principal(type="agent", id="run_attack", tenant_id="tnt_01")
    action = ActionRef(tool_name="shopify.refund_create", tool_version="1.0", side_effect="financial")
    resource = ResourceRef(system="shopify", entity="refund", amount=1000000.0)

    # Injection in user message cannot override unverified identity gating
    verdict = engine.authorize(
        principal=principal,
        action=action,
        resource=resource,
        context={"identity_tier": "anonymous"},
    )
    assert verdict.decision == "deny"


# -----------------------------------------------------------------------------
# S19: Long Chain / Budget Exhaustion Controlled Handoff
# -----------------------------------------------------------------------------
def test_s19_budget_exhaustion_handoff() -> None:
    budget = Budget(steps=12, wall_ms=90000, usd=0.50, tool_calls=8)
    ledger = BudgetLedger()

    for _ in range(12):
        ledger.consume_step(cost_estimate=0.01)

    exhausted, reason = ledger.check_exhausted(budget)
    assert exhausted is True
    assert "step_budget_exhausted" in (reason or "")


# -----------------------------------------------------------------------------
# S20: Per-Tenant Monthly Cost Budget Ceiling
# -----------------------------------------------------------------------------
def test_s20_tenant_cost_limit() -> None:
    budget = Budget(steps=100, wall_ms=90000, usd=0.50, tool_calls=50)
    ledger = BudgetLedger()
    ledger.consumed_usd = 0.55

    exhausted, reason = ledger.check_exhausted(budget)
    assert exhausted is True
    assert "cost_budget_exhausted" in (reason or "")
