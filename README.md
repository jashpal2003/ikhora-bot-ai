# Project Relay — AI Workforce Platform

[![Status](https://img.shields.io/badge/Status-Build--Ready%20Baseline-success)](#)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](#)
[![Architecture](https://img.shields.io/badge/Architecture-Modular%20Monolith-orange)](#)
[![Isolation](https://img.shields.io/badge/Isolation-Postgres%20RLS-red)](#)
[![Orchestration](https://img.shields.io/badge/Durable%20Execution-Temporal-purple)](#)

> **The Governed Execution Layer** that turns external customer conversations into authorized, audited actions inside Microsoft-centric enterprise business systems — and hands them to a human cleanly when the model should not act.

---

## 1. Executive Summary

Meta owns the conversation (WhatsApp, Messenger, Instagram). Microsoft owns the enterprise (Teams, SharePoint, Dataverse, Entra ID). Neither owns the seam between them, and neither has the incentive or architectural capability to build it cleanly:

*   **Meta Business Agent** is free and ubiquitous for consumer chat, but cannot cross enterprise trust boundaries into SharePoint, Dataverse, or ERP systems.
*   **Microsoft Copilot Studio** is cost-effective inside Teams for employee chats, but becomes prohibitively expensive on external channels and lacks a unified operator inbox, multi-channel ticket lifecycle, and cross-tenant identity resolution.
*   **The Moat:** The conversation is merely the input; **the audit trail and governed execution are the product**.

Project Relay bridges this gap with a four-deployable modular monolith ("modulith") enforcing tenant-level database isolation, durable human-in-the-loop workflows, calibrated shadow decisions, and tamper-evident cryptographic audit logs.

---

## 2. Architectural Principles

Every line of code and architectural decision in this repository is bound by ten core principles:

1.  **P1 — Model proposes, policy authorizes, code executes:** LLMs have zero capability grants. Tool allow-lists are pre-computed and frozen prior to run initiation.
2.  **P2 — Instructions and data are strictly separated:** System prompts and operator policies are instructions. Retrieved chunks, tool results, and customer inputs are quarantined data channels.
3.  **P3 — Tenant isolation is a database property, not a code convention:** PostgreSQL Row-Level Security (RLS) is forced across all tables. No application code relies solely on `WHERE tenant_id = ?`.
4.  **P4 — Every consequential action is durable, replayable, and idempotent:** Temporal workflows checkpoint state before any side-effect and log to append-only audit stores afterward.
5.  **P5 — Knowledge answers "what we know"; connectors answer "what is true now":** RAG never answers live-state queries. Hard-routed connector calls prevent stale answers.
6.  **P6 — Evidence or abstain:** `insufficient_evidence` and `sources_conflict` are first-class, tested response states rather than error paths.
7.  **P7 — Audit records are primary outputs:** Audit logs feature strict JSON schemas, cryptographic hash-chaining, retention policies, and compliance export pipelines.
8.  **P8 — Modules are hard boundaries; services are a deployment detail:** Domain boundaries are strictly enforced via static import analysis (`import-linter`).
9.  **P9 — Everything expensive has a budget and circuit breaker:** Hard ceilings for steps, wall-clock time, tool invocations, and dollar spend protect against runaway execution loops.
10. **P10 — Vendor-specific logic lives only in adapters:** All model providers, channels, and SaaS connectors are encapsulated behind abstract interfaces.

---

## 3. High-Level Architecture

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

## 4. The Four Deployables

The system is authored as a single modular monolith ("modulith") and built into four specialized deployables running on Azure Container Apps:

| # | Deployable | Responsibility | Scaling Trigger | Target Resources |
|---|------------|----------------|-----------------|------------------|
| **D1** | `relay-gateway` | Fast webhook ingest (<200ms ACK), HMAC verification, deduplication, raw event persistence, WebSockets for widgets | Inbound message rate | 2–10 replicas (lightweight) |
| **D2** | `relay-api` | Public REST API, operator inbox (SSE), ticket management, knowledge management, admin endpoints | Concurrent operators | 2–8 replicas (interactive) |
| **D3** | `relay-agent` | Temporal workflow workers: plan-act-verify loops, decision execution, tool invocation, human approval signal waits | Task queue depth & latency | 2–20 replicas (KEDA autoscaled) |
| **D4** | `relay-ingest` | Batch document crawlers, structure-aware chunking, vector embedding, Graph ACL delta synchronization | Ingestion backlog | 0–6 replicas (scale-to-zero) |

---

## 5. Directory Structure

```
.
├── apps/                        # Entrypoints for the 4 deployables + frontends
│   ├── gateway/                 # D1: Fast channel webhook receiver
│   ├── api/                     # D2: Core modulith REST & SSE API
│   ├── agent/                   # D3: Temporal workflow worker
│   ├── ingest/                  # D4: Ingestion and ACL delta worker
│   ├── teams-adapter/           # Microsoft Agents SDK service (TS/C#)
│   ├── web/                     # Next.js 15 App Router operator console
│   └── widget/                  # Preact Shadow DOM embeddable bundle
├── src/relay/                   # The Core Modulith (strictly layered)
│   ├── platform/                # Tenancy, RLS context, ULIDs, errors, clock
│   ├── events/                  # Transactional outbox & Redis Streams
│   ├── audit/                   # Append-only hash-chained audit engine
│   ├── identity/                # Contacts, capability tiers, soft-merges
│   ├── conversations/           # Messages, assignment, optimistic concurrency
│   ├── tickets/                 # Ticket lifecycle & HandoffPacket builder
│   ├── knowledge/               # 3-layer ACL retrieval, hybrid RRF, EvidencePack
│   ├── decisions/               # DecisionProvider protocol, Small-LLM, Jev shadow
│   ├── policy/                  # authorize() chokepoint, declarative rules, budgets
│   ├── tools/                   # ToolSpec, frozen registry, idempotent executor
│   ├── connectors/              # Microsoft Graph OBO, Dataverse, Shopify, Internal
│   ├── channels/                # WhatsApp, Teams, Web adapters
│   ├── agent/                   # Temporal workflows, activities, budgets, replay
│   ├── analytics/               # Tracing, rollups, cost ledgers
│   └── api/                     # Thin controllers (zero business logic)
├── migrations/                  # PostgreSQL 16 schema DDL with RLS policies
├── infra/                       # Terraform modules for Azure infrastructure
├── evals/                       # 150+ Golden Set journeys & security probes
├── docs/adr/                    # Architecture Decision Records (001–012)
├── .agents/                     # Antigravity agent rules and custom skills
└── docker-compose.yml           # Local development orchestrator
```

---

## 6. Quick Start (Local Development)

### Prerequisites
*   Python 3.12+ with [`uv`](https://github.com/astral-sh/uv)
*   Docker & Docker Compose
*   Node.js 20+ and `pnpm`

### 1. Launch Dependencies
Launch PostgreSQL 16 (with `pgvector`), Redis 7, and Temporal Dev Server:
```bash
docker compose up -d postgres redis temporal
```

### 2. Initialize Database & Row-Level Security
```bash
uv sync --all-extras
uv run alembic upgrade head
```

### 3. Run Core Verification Checks
Validate strict architectural boundaries, types, and security isolation:
```bash
# 1. Assert module boundary rules (fails on invalid layer imports)
uv run lint-imports --config .importlinter

# 2. Strict type check
uv run mypy --strict src/relay

# 3. Verify PostgreSQL RLS coverage across 100% of tables
uv run pytest evals/probes/test_rls_coverage.py

# 4. Run automated cross-tenant security probes
uv run pytest evals/probes/test_cross_tenant.py
```

### 4. Start Services Locally
```bash
# Start API & SSE Server (Port 8000)
uv run uvicorn apps.api.main:app --reload --port 8000

# Start Channel Gateway (Port 8001)
uv run uvicorn apps.gateway.main:app --reload --port 8001

# Start Temporal Agent Worker
uv run python -m apps.agent.worker
```

---

## 7. Documentation Index

*   [Comprehensive Engineering Architecture](ARCHITECTURE.md)
*   [Detailed System Design & Data Dictionary](SYSTEM_DESIGN.md)
*   [Antigravity Agent Instructions & Boundaries](AGENTS.md)
*   [Architecture Decision Records (docs/adr/)](docs/adr/)
*   [Contributing & Code Standards](CONTRIBUTING.md)
