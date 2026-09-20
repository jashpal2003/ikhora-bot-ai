"""The Policy Engine — The Single Chokepoint (P1, §12.1)."""

from typing import Any
from relay.policy.models import ActionRef, ApprovalRoute, Principal, Reason, ResourceRef, Verdict


class PolicyEngine:
    """The central authorization chokepoint.
    
    All agent tool calls MUST pass through authorize().
    No tool can be invoked without a valid Verdict issued here.
    """

    def __init__(self, policy_version: str = "v1.0") -> None:
        self.policy_version = policy_version

    def authorize(
        self,
        principal: Principal,
        action: ActionRef,
        resource: ResourceRef,
        context: dict[str, Any],
    ) -> Verdict:
        """Evaluate declarative tenant policies against requested action."""
        matched_rules: list[str] = []
        reasons: list[Reason] = []
        identity_tier = context.get("identity_tier", "anonymous")
        skill_age_days = context.get("skill_age_days", 30)
        knowledge_topics = context.get("knowledge_topics", [])

        # Rule 0: Emergency Kill Switch / Tool Disable (Scenario S17)
        if context.get("kill_switch_active", False) or context.get("tool_disabled", False):
            matched_rules.append("emergency_kill_switch")
            reasons.append(
                Reason(
                    code="KILL_SWITCH_ACTIVE",
                    message=f"Action '{action.tool_name}' halted by administrator emergency kill switch.",
                )
            )
            return Verdict(
                decision="deny",
                reasons=reasons,
                matched_rules=matched_rules,
                policy_version=self.policy_version,
            )

        # Rule 1: Identity verification gating (P1, §12.2)
        # Unverified customer accounts cannot touch customer private data or write
        if identity_tier in ("anonymous", "weak") and action.side_effect in ("write", "destructive", "financial"):
            matched_rules.append("unverified_no_write")
            reasons.append(
                Reason(
                    code="IDENTITY_NOT_VERIFIED",
                    message="Customer identity must be verified via OTP or SSO before modifying records.",
                )
            )
            return Verdict(
                decision="deny",
                reasons=reasons,
                matched_rules=matched_rules,
                policy_version=self.policy_version,
            )

        # Rule 2: Financial Threshold (e.g. refund > $50 requires manager approval)
        if action.side_effect == "financial" and (resource.amount or 0.0) > 50.0:
            matched_rules.append("refund_threshold_exceeded")
            reasons.append(
                Reason(
                    code="REFUND_THRESHOLD",
                    message=f"Financial action of amount ${resource.amount:.2f} exceeds the $50.00 autonomous threshold.",
                )
            )
            return Verdict(
                decision="require_approval",
                reasons=reasons,
                matched_rules=matched_rules,
                approval_route=ApprovalRoute(role="support_manager", sla_minutes=120, channel="teams"),
                policy_version=self.policy_version,
            )

        # Rule 3: Protected Topics (legal, compliance, hr) require review
        if any(topic in ["legal", "hr", "compliance"] for topic in knowledge_topics):
            matched_rules.append("protected_topic_review")
            reasons.append(
                Reason(
                    code="PROTECTED_TOPIC",
                    message="Actions involving legal or compliance topics require human approval.",
                )
            )
            return Verdict(
                decision="require_approval",
                reasons=reasons,
                matched_rules=matched_rules,
                approval_route=ApprovalRoute(role="compliance", sla_minutes=60, channel="teams"),
                policy_version=self.policy_version,
            )

        # Rule 4: Progressive autonomy - new skills start in probation review
        if skill_age_days < 14 and action.side_effect != "read":
            matched_rules.append("new_skill_probation")
            reasons.append(
                Reason(
                    code="SKILL_PROBATION",
                    message=f"Skill is under probation ({skill_age_days}/14 days); actions require review.",
                )
            )
            return Verdict(
                decision="require_approval",
                reasons=reasons,
                matched_rules=matched_rules,
                approval_route=ApprovalRoute(role="support_lead", sla_minutes=240, channel="teams"),
                policy_version=self.policy_version,
            )

        # Default: Allow read operations and low-risk policy-cleared writes
        matched_rules.append("standard_allow")
        reasons.append(
            Reason(
                code="POLICY_CLEARED",
                message="Action satisfies all automated policy constraints.",
            )
        )
        return Verdict(
            decision="allow",
            reasons=reasons,
            matched_rules=matched_rules,
            policy_version=self.policy_version,
        )
