# ADR 004: Build Custom Agent Loop Without Heavyweight Frameworks

## Status
Accepted

## Context
High-level agent frameworks (LangChain, CrewAI, AutoGen, LlamaIndex) prioritize rapid prototyping over deterministic enterprise control. Their abstractions obscure step budgets, tamper-evident audit emission, policy chokepoints, and fine-grained error recovery. Enterprise CISOs require exact explanations of run execution traces.

## Decision
We reject third-party agent orchestration frameworks and **build our own custom agent loop (~800–1,200 LOC)** on top of Temporal:
- Use focused, single-purpose libraries: `pydantic` for schema definitions, `tiktoken` for token counting, and structured outputs for typed completions.
- Every step of the loop explicitly invokes our `policy.authorize()` chokepoint and emits structured audit records.

## Consequences
- **Positive:** Complete control over budgeting, policy gating, checkpointing, and compliance traceability.
- **Negative:** The core loop and tool dispatch logic must be authored and maintained in-house.
