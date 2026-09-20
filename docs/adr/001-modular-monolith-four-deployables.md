# ADR 001: Modular Monolith ("Modulith") with Four Deployables

## Status
Accepted

## Context
Project Relay is an enterprise AI Workforce Platform in its initial build phase (pre-PMF). Workflows and domain boundaries will evolve through pilot customer discovery. We evaluated two architectural extremes:
1. **Microservices:** Solves organizational scaling when domain boundaries are fixed. However, introducing network boundaries now creates distributed transaction complexity across messages, tickets, and audit records, high operational overhead, and difficult local development.
2. **Single Monolithic Process:** Co-locating webhook ingress, long-running agent workflows, and heavy ingestion jobs causes resource starvation. A slow agent run can delay Meta/Teams webhook ACKs (>200ms), resulting in channel suspension.

## Decision
We adopt a **modular monolith** ("modulith") deployed as four separate processes sharing a single codebase, schema, and dependency tree:
1. `relay-gateway` (D1): Channel webhook receivers, signature verification, raw event persistence, widget WebSockets.
2. `relay-api` (D2): Public REST API, operator inbox (SSE), ticket lifecycle, knowledge admin.
3. `relay-agent` (D3): Temporal workflow workers executing agent loops, tools, and approval waits.
4. `relay-ingest` (D4): Batch crawlers, chunkers, embedders, and Microsoft Graph ACL delta synchronizers.

Module boundaries within `src/relay/` are strictly enforced at build time via `import-linter`.

## Consequences
- **Positive:** Single repository, single migration history, zero distributed transactions, sub-second local dev boot with `docker compose up`.
- **Negative:** Requires strict discipline and automated CI linting to prevent module coupling.
