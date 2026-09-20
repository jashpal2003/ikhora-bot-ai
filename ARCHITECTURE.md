# Project Relay — Engineering Architecture & System Design
**Document Type:** Engineering Architecture, System Design and Delivery Plan  
**Status:** Build-Ready Baseline  
**Codename:** Relay  
**Platform:** AI Workforce Platform  

---

## 0. Strategic Context & The Surviving Wedge

### 0.1 The Competitive Landscape (2026 Shift)
Between early product concepts and the current market reality, two enterprise tech giants commoditized major entry-level AI capabilities:
1. **Meta Business Agent (GA June 2026):** Native, free, in-app customer support across WhatsApp, Instagram, and Messenger. Handles basic catalog lookups, simple FAQs, and Shopify connections.
2. **Microsoft Copilot Studio & Agent 365 (GA 2026):** Free/zero-rated inside Teams and SharePoint for M365 Copilot subscribers. Provides Entra Agent ID governance for pure Microsoft estates.

### 0.2 The Seam Between the Two Giants
Meta cannot cross the enterprise trust boundary into SharePoint, Dataverse, Entra ID, or ERP systems. Microsoft Copilot Studio is cost-prohibitive when customer-facing and lacks a multi-channel unified inbox, ticket lifecycle, and cross-tenant identity resolution.

**The Defensible Wedge:**
> *The governed execution layer that turns an external customer conversation into an authorized, audited action inside a Microsoft-centric business system — and hands it to a human cleanly when it should not act.*

The conversation is merely the input; **the audit trail and policy-gated action are the product.**

---

## 1. Core Architectural Principles

*   **P1 — Model proposes, policy authorizes, code executes:** No LLM output constitutes a capability grant. Tool allow-lists are pre-computed and frozen prior to run initiation.
*   **P2 — Instructions and data are different channels:** System prompts and operator rules are instructions. Tool outputs, retrieved chunks, and customer messages are data. Data is never promoted to instruction.
*   **P3 — Tenant isolation is a database property, not a code convention:** PostgreSQL Row-Level Security (RLS) is forced across all tables.
*   **P4 — Every consequential action is a durable, replayable, idempotent workflow step:** Temporal workflows checkpoint state before any external side effect.
*   **P5 — Knowledge answers "what we know"; connectors answer "what is true now":** RAG never answers live-state questions. Live queries must hard-route to connectors.
*   **P6 — Evidence or abstain:** `insufficient_evidence` and `sources_conflict` are first-class, tested, shipped response states.
*   **P7 — The audit record is a primary output, not a log:** Schematized, append-only, cryptographic hash-chained, and retention-governed.
*   **P8 — Modules are hard boundaries; services are a deployment detail:** Domain boundaries are enforced at build time via import linting.
*   **P9 — Everything expensive has a budget and a circuit breaker:** Hard limits on steps, time, tokens, and cost per run and per tenant.
*   **P10 — Vendor-specific logic lives only in adapters:** Domain logic contains zero references to external vendor SDK signatures.

---

## 2. System Context & Execution Flow

```
                       ┌──────────── CUSTOMER SIDE ────────────┐
                       │  WhatsApp   Web widget   (Instagram)  │
                       └──────────────────┬────────────────────┘
                                          │  webhooks / WSS
                       ┌──────────────────▼────────────────────┐
                       │      CHANNEL GATEWAY  (stateless)     │
                       │  verify · dedupe · persist raw · ack  │
                       └──────────────────┬────────────────────┘
                                          │  normalized MessageEnvelope
                       ┌──────────────────▼────────────────────┐
                       │            CORE API (modulith)        │
                       │  identity · conversations · tickets   │
                       │  policy · tools · audit · admin       │
                       └───┬───────────────┬──────────────┬────┘
                           │               │              │
         ┌─────────────────▼──┐  ┌─────────▼────────┐  ┌──▼──────────────┐
         │  KNOWLEDGE FABRIC  │  │  AGENT RUNTIME   │  │  LIVE STATE     │
         │  Graph/SP/OneDrive │  │  durable workflow│  │  Dataverse      │
         │  ACL-aware hybrid  │  │  plan→act→verify │  │  Shopify/CRM    │
         │  retrieval         │  │  step budgets    │  │  Graph actions  │
         └─────────┬──────────┘  └─────────┬────────┘  └──┬──────────────┘
                   │                       │              │
                   └───────────┬───────────┴──────────────┘
                               │  every call routed through
                   ┌───────────▼────────────┐
                   │    POLICY / EXEC GATE  │  ← the single chokepoint
                   │  authorize(P,A,R,Ctx)  │
                   └───────┬────────┬───────┘
                      AUTO │        │ APPROVAL REQUIRED
                           │        ▼
                           │   ┌──────────────────┐
                           │   │  ACTION CENTER   │ ← operator console
                           │   │  approve/reject  │
                           │   └────────┬─────────┘
                           └────────────┤
                                        ▼
                        ┌───────────────────────────────┐
                        │  EVENT + AUDIT STORE (append) │
                        │  correlation_id == trace_id   │
                        └───────────────┬───────────────┘
                                        ▼
                        ┌───────────────────────────────┐
                        │  ANALYTICS · EVAL · REPLAY    │
                        └───────────────────────────────┘

                       ┌──────── EMPLOYEE SIDE ────────┐
                       │  Teams  ·  Operator console   │
                       └───────────────────────────────┘
```

---

## 3. Macro Architecture: Modular Monolith ("Modulith")

### 3.1 Why Modulith (Not Microservices)
1. Pre-PMF domain boundaries evolve rapidly; network boundaries turn refactors into distributed migrations.
2. Prevents distributed transaction failures across messages, tickets, and audit tables.
3. Keeps local developer setup down to a single command (`docker compose up`).

### 3.2 Four Independent Deployables
*   **D1 `relay-gateway`:** Ingests webhooks, verifies HMAC signatures, dedupes in Redis, persists raw payloads, ACKs <200ms.
*   **D2 `relay-api`:** Modulith REST API, SSE streaming for the operator inbox, admin surfaces, ticket state machine.
*   **D3 `relay-agent`:** Temporal workflow workers executing the agent loop, policy evaluations, and tool calls.
*   **D4 `relay-ingest`:** Long-running batch crawler, structure-aware chunker, vector embedder, and Microsoft Graph ACL delta synchronizer.

### 3.3 Strict Layering & Import Enforcement
```
src/relay/
  platform/        # tenancy, RLS session, config, errors, IDs, clock
  events/          # outbox, event bus, event schemas
  audit/           # append-only audit writer + query
  identity/        # contacts, contact_identities, merge, consent
  conversations/   # conversations, messages, assignment, inbox queries
  tickets/         # ticket lifecycle, SLA, handoff packet
  knowledge/       # sources, documents, chunks, retrieval, ACL, evidence
  decisions/       # DecisionProvider interface + implementations
  policy/          # authorize(), rules, approval routing, budgets
  tools/           # tool registry, contracts, execution, idempotency
  connectors/      # graph/, dataverse/, shopify/, hubspot/ ...
  channels/        # whatsapp/, teams/, web/ adapters
  agent/           # runtime, planner, verifier, workflow definitions
  analytics/       # metrics, eval harness, replay
  api/             # HTTP layer only — zero business logic
```

**Rules Enforced in CI:**
1. Downward dependencies only.
2. Connectors and channels are accessed only through interfaces defined in `tools/` and `channels/contracts.py`.
3. Inter-module communication passes through public `api.py` boundaries.
4. No cross-module database writes (must call the owning service).
5. `api/` contains zero business logic (validate, dispatch, format).

---

## 4. Technology Stack & Infrastructure

*   **Core Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (asyncio), Alembic.
*   **Teams Adapter:** Node.js/TypeScript or C# with `@microsoft/agents-hosting` (isolated polyglot adapter).
*   **Frontend:** Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, TanStack Query, Zustand.
*   **Customer Widget:** Preact + Shadow DOM (<40KB gzipped).
*   **Primary Store:** Azure Database for PostgreSQL Flexible Server 16 with `pgvector` 0.8+ and full-text search (`tsvector` + GIN).
*   **Ephemeral / Cache:** Azure Managed Redis 7 (rate limiting, idempotency caches, presence, SSE pub/sub).
*   **Durable Workflows:** Temporal Cloud (or local Temporal server).
*   **Object Storage:** Azure Blob Storage with immutable container policies for audit records.
*   **Secrets & Identities:** Azure Key Vault + Entra Workload Managed Identity.
*   **Deployment:** Azure Container Apps with KEDA scaling rules.

---

## 5. Tenancy & Row-Level Security

### 5.1 Tenancy Architecture
Shared database, shared schema, `tenant_id` on every table, enforced by PostgreSQL Row-Level Security:

```sql
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON conversations
  USING (tenant_id = current_setting('relay.tenant_id', true)::text)
  WITH CHECK (tenant_id = current_setting('relay.tenant_id', true)::text);
```

### 5.2 Transaction-Local Scoping
Every database session sets the tenant context locally within the active transaction:
```python
@asynccontextmanager
async def tenant_scope(session: AsyncSession, tenant_id: str):
    await session.execute(
        text("SELECT set_config('relay.tenant_id', :tid, true)"),
        {"tid": tenant_id},
    )
    yield session
```
*`is_local = true` ensures connection poolers (PgBouncer) cannot leak tenant context between pooled requests.*

---

## 6. Tamper-Evident Audit & Append-Only Log

*   **Append-Only Enforced by Engine:** Table-level triggers prevent `UPDATE` or `DELETE` operations on `audit_events`.
*   **Cryptographic Chaining:**
    $$\text{hash}_n = \text{SHA256}(\text{hash}_{n-1} \parallel \text{canonical\_json}(\text{event}_n))$$
*   **Payload Offloading:** Large request/response bodies are offloaded to Azure Blob Storage with SHA-256 integrity verification (`data_ref`).
*   **Accountability:** Every audit entry explicitly records `actor_id` and `on_behalf_of` (human delegator).

---

## 7. Durable Execution & The Agent Runtime

The agent runtime is implemented as a deterministic Temporal workflow:

```python
@workflow.defn
class AgentRunWorkflow:
    @workflow.run
    async def run(self, ctx: RunContext) -> RunOutcome:
        budget = Budget(steps=12, wall_ms=90_000, usd=0.50, tool_calls=8)
        decision = await workflow.execute_activity(classify_intent, ctx)

        while not budget.exhausted():
            plan = await workflow.execute_activity(plan_next_step, ctx, decision)
            if plan.kind == "respond":
                await workflow.execute_activity(send_reply, ctx, plan.message)
                return RunOutcome.completed()
            if plan.kind == "handoff":
                await workflow.execute_activity(create_handoff_packet, ctx)
                return RunOutcome.handed_off()

            verdict = await workflow.execute_activity(authorize, ctx, plan.tool_call)
            if verdict.requires_approval:
                await workflow.execute_activity(request_approval, ctx, verdict)
                approved = await workflow.wait_condition(
                    lambda: self._approval is not None, timeout=timedelta(hours=48)
                )
                if not approved or not self._approval.granted:
                    return RunOutcome.rejected()
            elif verdict.denied:
                await workflow.execute_activity(record_denial, ctx, verdict)
                return RunOutcome.handed_off(reason="policy_denied")

            result = await workflow.execute_activity(execute_tool, ctx, plan.tool_call, verdict)
            ctx = await workflow.execute_activity(verify_and_update, ctx, result)
            budget.consume(plan.cost_estimate)

        await workflow.execute_activity(create_handoff_packet, ctx, reason="budget_exhausted")
        return RunOutcome.handed_off()
```

---

## 8. Knowledge Fabric & Three-Layer ACL Retrieval

To eliminate data leakage from enterprise knowledge sources (e.g., SharePoint):

1.  **Layer 1 (Index-Time):** Extract ACL permissions and compute `acl_hash`. Incremental delta synchronization tracks ACL changes independently from document bodies.
2.  **Layer 2 (Query-Time SQL Filtering):** Expand user Entra group memberships (`transitiveMemberOf`) and filter candidate chunks directly inside PostgreSQL SQL queries prior to vector/BM25 scoring.
3.  **Layer 3 (Pre-Release OBO Verification):** For top candidate chunks ($K=8$), batch-verify current permissions via Microsoft Graph On-Behalf-Of (OBO) before tokens enter LLM prompts.

**Hybrid Search & Ranking:** Reciprocal Rank Fusion (RRF) blends `pgvector` HNSW cosine similarity and PostgreSQL `tsvector` BM25 candidates, followed by cross-encoder reranking (`bge-reranker-v2-m3`).

---

## 9. Decision Layer & Calibrated Autonomy

*   `DecisionProvider` Protocol provides typed, bounded decisions.
*   **Phase 1 Default:** `SmallLLMDecisionProvider` (low-latency, structured JSON output).
*   **Shadow Mode:** `JevDecisionProvider` (evaluating latency, cost, and Brier calibration score in parallel without taking live action).
*   **Fallback:** `RuleDecisionProvider` (deterministic safety fallback).

---

## 10. Policy & Authorization: The Single Chokepoint

```python
def authorize(
    principal: Principal,
    action: ActionRef,
    resource: ResourceRef,
    context: RunContext
) -> Verdict
```
*   `tools.invoke()` requires an immutable `Verdict` token created exclusively by `policy.authorize()`.
*   Declarative tenant rules evaluate thresholds (e.g., refund > $50), customer verification tiers, probation windows for new skills, and protected topics.

---

## 11. Connectors Priority

1.  **P0:** Microsoft Graph (SharePoint, OneDrive, Teams, Outlook OBO)
2.  **P0:** Microsoft Dataverse (Web API with role-based and column-level security)
3.  **P0:** Internal Relay Tools (ticket transition, notification, approval request)
4.  **P1:** Shopify Admin GraphQL
5.  **P1:** HubSpot / Salesforce CRM
6.  **P2:** Zendesk / Freshdesk / Jira Bridge
7.  **P3:** MCP Client (isolated in data channel; descriptions never in system instructions)

---

## 12. Security Architecture & Prompt Injection Defense

*   **Instruction vs. Data Segregation:** System prompt and local `ToolSpec` definitions live in the trusted instruction channel. User messages, retrieved knowledge, and tool outputs live in the quarantined data channel.
*   **Capability Lockdown:** LLMs cannot discover or expand tool sets at runtime. Capabilities are pre-frozen.
*   **Channel Hardening:**
    *   *WhatsApp:* HMAC-SHA256 signature verification (`X-Hub-Signature-256`), 24h service window tracking, task-specific agent scoping.
    *   *Teams:* JWKS signature validation and OBO user token exchange.
    *   *Web:* Tenant origin validation, short-lived signed tokens, rate limits.

---

## 13. Operator Action Center View Model

The Action Center view model unifies live execution, compliance verification, and human oversight:

```
RUN 01J8X… · WhatsApp · +971 5X XXX XXXX · 14:03:11 → 14:03:19 · $0.0041

  WHAT      Created case CAS-4471 in Dataverse
  WHY       Customer reported damaged order; policy requires case for claims
  WHO       Agent "Support Employee v7" on behalf of priya@customer.com
  DATA      Order 8281 (Shopify, read 14:03:14) · Contact verified via OTP
  EVIDENCE  Damaged Goods Policy §4.2 (SharePoint, v12, 4 days old) ✓ validated
  POLICY    refund_threshold — amount $42 below $50 → auto-approved
  DECISION  intent=damage_claim (0.94) · priority=high (0.88) · human=no (0.21)
  RESULT    ✓ CAS-4471 created · Teams notified #support · reply sent 14:03:19
  BUDGET    4 / 12 steps · 8.2s / 90s · $0.0041 / $0.50

  [ Replay ]  [ Export audit JSON ]  [ Open trace ]  [ Report incorrect ]
```

---

## 14. Observability & Quality Gates

*   **Unified Trace ID:** `agent_run.id` = OpenTelemetry `trace_id` = `correlation_id` on all events, audit rows, and UI links.
*   **Golden Set:** 150+ journeys across happy paths, ambiguous inputs, insufficient evidence (S03), conflicting sources (S04), ACL negative controls (S07/S08), prompt injections (S18), and budget exhaustion (S19).
*   **Release Gates:** CI runs ACL negative controls and prompt injection regressions on every PR.
