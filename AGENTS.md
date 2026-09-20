# Project Relay — AI Agent & Developer Directives

This document defines the mandatory guidelines, architectural constraints, and development standards for any AI agent or software engineer operating within this repository.

---

## 1. Prime Directives (Non-Negotiable)

Every task performed in this codebase must adhere to the ten core architectural principles:

1.  **P1 — Model proposes, policy authorizes, code executes:** Never grant autonomous capability to an LLM. Tool allow-lists are pre-computed and frozen prior to workflow initiation.
2.  **P2 — Instructions and data are separate channels:** System prompts, skill definitions, and policies are instructions. Retrieved text, tool outputs, and customer messages are quarantined data.
3.  **P3 — Tenant isolation is a database property:** PostgreSQL Row-Level Security (RLS) is enabled on all tenant-bearing tables. Never rely on application-level `WHERE tenant_id = ?` clauses alone.
4.  **P4 — Actions are durable and idempotent:** All side effects must run through Temporal activities, record an `idempotency_key`, and write to append-only audit logs.
5.  **P5 — Knowledge vs. Live State segregation:** Never allow RAG retrieval to answer live-state queries (order status, account balance, delivery times). Hard-route them to connectors.
6.  **P6 — Evidence or abstain:** Insufficient evidence and conflicting sources are first-class, tested response states. Never hallucinate plausible answers.
7.  **P7 — Audit records are primary products:** Audit rows are immutable, append-only, and cryptographically hash-chained per tenant.
8.  **P8 — Modules are hard boundaries:** Module dependencies flow downward only. Do not introduce circular dependencies or bypass public module APIs.
9.  **P9 — Enforce budgets and circuit breakers:** Step, time, tool call, and USD cost ceilings are enforced at workflow chokepoints.
10. **P10 — Vendor-specific code lives only in adapters:** Domain modules must never reference external SDK types directly.

---

## 2. Module Layering & Import Rules

Module dependencies MUST follow this strict downward hierarchy:

```
platform
  ▲
events
  ▲
audit
  ▲
identity
  ▲
conversations
  ▲
tickets
  ▲
knowledge
  ▲
decisions
  ▲
policy
  ▲
tools
  ▲
connectors  /  channels
  ▲
agent
  ▲
analytics
  ▲
api
```

### 2.1 Enforced Boundary Rules
*   A module may only import from modules positioned **below** it in the hierarchy, plus `platform`.
*   `connectors/*` and `channels/*` must **never** be imported directly by domain modules. Access them strictly through `tools/` and `channels/contracts.py`.
*   Cross-module access must route through the owning module's public `api.py` or root `__init__.py`. Never reach into module internals.
*   **No Cross-Module Database Writes:** A module may never write to another module's database tables. Cross-module writes must call the owning module's service functions.
*   `api/` contains zero business logic. Controllers parse inputs, invoke a single service function, and serialize the result.

---

## 3. Database & RLS Conventions

### 3.1 Mandatory Transaction-Scoped RLS
Every database query that touches tenant data must execute within `tenant_scope`:

```python
from relay.platform.tenancy import tenant_scope

async with tenant_scope(session, tenant_id):
    result = await session.execute(select(Conversation))
```

*   `set_config` MUST use `is_local = true` to prevent connection pool leakage under PgBouncer.
*   The application database role must NOT be a superuser or table owner.

---

## 4. Policy & Tool Execution

### 4.1 Single Authorization Chokepoint
Tools can only be invoked with a valid, tamper-proof `Verdict` object produced by `policy.authorize()`:

```python
# CORRECT:
verdict = await policy_engine.authorize(principal, action, resource, context)
if verdict.allowed:
    result = await tool_executor.invoke(tool, input_data, verdict)

# FORBIDDEN: Direct tool invocation without policy verdict
result = await tool_executor.raw_call(...)  # Will raise AuthorizationRequiredError
```

---

## 5. Coding & Testing Standards

*   **Type Safety:** All Python code must pass `mypy --strict`.
*   **Schemas:** Every request, response, event, and tool input/output must be a Pydantic v2 `BaseModel`.
*   **Identifiers:** Always generate prefixed ULIDs using `relay.platform.ids.generate_id(prefix)` (`run_01J...`, `msg_01J...`).
*   **Testing Requirement:** Every PR adding a tool must include:
    1. A Pydantic schema contract.
    2. A declarative policy rule.
    3. An append-only audit event assertion.
    4. An idempotency test with duplicate keys.
    5. A compensation (undo) path where side effects are destructive or financial.
