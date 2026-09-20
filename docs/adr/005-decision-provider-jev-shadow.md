# ADR 005: DecisionProvider Abstraction and Jev Shadow Mode

## Status
Accepted

## Context
High-volume classification and threshold-based routing (e.g., intent categorization, priority scoring) require fast, calibrated, low-cost model outputs. Jev provides typed, bounded decisions with low latency, but is in early access, hosted exclusively in a single US-West region, and lacks multi-region failover and enterprise SLAs.

## Decision
We decouple decision logic behind a strict `DecisionProvider` Protocol:
1. **Production Default:** `SmallLLMDecisionProvider` (low-latency, multi-region LLM with structured output schemas).
2. **Shadow Mode:** `JevDecisionProvider` runs asynchronously in parallel on a traffic sample. Decisions are logged for latency, cost, and calibration (Brier score) evaluation, but never execute live actions.
3. **Emergency Fallback:** `RuleDecisionProvider` (deterministic rule-based heuristics with conservative safety defaults: `human_required = true`).

Promotion of Jev (or any alternative model) occurs on a per-decision-type basis only after meeting strict accuracy, latency, calibration, and SLA criteria.

## Consequences
- **Positive:** Protects the production critical path against third-party outages while establishing a quantitative benchmarking pipeline for emerging decision models.
- **Negative:** Requires maintaining multiple provider implementations behind the protocol.
