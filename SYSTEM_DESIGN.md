# Project Relay — Detailed System Design & Data Dictionary

This document details the concrete data models, state machines, identifier conventions, and component interactions within Project Relay.

---

## 1. Identifier Strategy

Project Relay uses **Universally Unique Lexicographically Sortable Identifiers (ULIDs)** encoded as 26-character Crockford base32 strings.

### 1.1 Type Prefixing Standard
All external APIs, database records, event streams, and logs MUST prefix identifiers with their entity type:

| Entity | Prefix | Example | Description |
|---|---|---|---|
| Tenant | `tnt_` | `tnt_01J8XQP...` | Enterprise organization boundary |
| Contact | `cnt_` | `cnt_01J8XQP...` | Unified customer entity |
| Identity | `idt_` | `idt_01J8XQP...` | Channel-specific account or handle |
| Conversation | `cnv_` | `cnv_01J8XQP...` | Customer-agent interaction session |
| Message | `msg_` | `msg_01J8XQP...` | Discrete channel message or internal note |
| Agent Run | `run_` | `run_01J8XQP...` | Temporal workflow execution instance |
| Agent Step | `stp_` | `stp_01J8XQP...` | Atomic decision or activity step |
| Tool Execution | `tex_` | `tex_01J8XQP...` | Authorized tool invocation record |
| Audit Event | `aud_` | `aud_01J8XQP...` | Append-only cryptographically chained event |
| Ticket | `tkt_` | `tkt_01J8XQP...` | Tracked escalation or work item |
| Knowledge Doc | `doc_` | `doc_01J8XQP...` | Ingested enterprise document |
| Document Chunk | `chk_` | `chk_01J8XQP...` | Embedded text segment |
| Approval | `apr_` | `apr_01J8XQP...` | Pending human authorization request |

---

## 2. Core State Machines

### 2.1 Ticket Lifecycle
```
                 ┌──────────────┐
                 │     NEW      │
                 └──────┬───────┘
                        │
                  assigned to agent / operator
                        │
                        ▼
                 ┌──────────────┐
     ┌───────────│ IN_PROGRESS  │◄────────────┐
     │           └──────┬───────┘             │
     │                  │                     │
need customer input     │ human escalation    │ customer replied
     │                  ▼                     │
     │           ┌──────────────┐             │
     │           │   ESCALATED  │─────────────┘
     │           └──────┬───────┘
     ▼                  │
┌─────────┐             │ resolved by operator / agent
│ WAITING │             │
└────┬────┘             ▼
     │           ┌──────────────┐
     └──────────►│   RESOLVED   │
                 └──────┬───────┘
                        │ SLA window elapsed
                        ▼
                 ┌──────────────┐
                 │    CLOSED    │
                 └──────────────┘
```

### 2.2 Agent Run Lifecycle (Temporal Workflow)
```
          ┌─────────────┐
          │   RUNNING   │
          └──────┬──────┘
                 │
       ┌─────────┴───────────────┐
       │ (plan tool call)        │
       ▼                         ▼
┌───────────────┐       ┌──────────────────┐
│  AUTHORIZED   │       │ REQUIRES_APPROVAL│
└──────┬────────┘       └────────┬─────────┘
       │                         │
       │                         ├─ approved ──► execute tool
       │                         ├─ rejected ──► HANDED_OFF
       │                         └─ timeout (48h) ──► HANDED_OFF
       ▼
┌───────────────┐
│ EXECUTED_TOOL │
└──────┬────────┘
       │
       ├─ loop condition satisfied ──► RUNNING
       ├─ budget exhausted ──────────► HANDED_OFF (reason="budget_exhausted")
       ├─ final reply sent ──────────► COMPLETED
       └─ unrecoverable error ───────► FAILED
```

---

## 3. Data Dictionary

### 3.1 Tenancy & Contact Identity Models

#### `tenants`
*   `id` (`TEXT PRIMARY KEY`): Prefixed ULID (`tnt_...`).
*   `name` (`TEXT NOT NULL`): Enterprise display name.
*   `plan` (`TEXT NOT NULL DEFAULT 'starter'`): Billing tier (`starter`, `growth`, `enterprise`).
*   `region` (`TEXT NOT NULL DEFAULT 'weu'`): Target cloud region (`weu`, `eus`).
*   `settings` (`JSONB NOT NULL DEFAULT '{}'`): Tenant-wide configurations, budget ceilings, policy flags.
*   `status` (`TEXT NOT NULL DEFAULT 'active'`): Status (`active`, `suspended`, `deprovisioned`).
*   `created_at` (`TIMESTAMPTZ NOT NULL DEFAULT now()`).

#### `contacts`
*   `id` (`TEXT PRIMARY KEY`): Prefixed ULID (`cnt_...`).
*   `tenant_id` (`TEXT NOT NULL REFERENCES tenants(id)`): Foreign key with RLS enforcement.
*   `display_name` (`TEXT`): Resolved customer name.
*   `profile` (`JSONB NOT NULL DEFAULT '{}'`): Metadata attributes (VIP status, CRM IDs).
*   `consent` (`JSONB NOT NULL DEFAULT '{}'`): Opt-in status and privacy tracking.
*   `merged_into` (`TEXT REFERENCES contacts(id)`): Soft-merge target pointer; preserves history.
*   `created_at` (`TIMESTAMPTZ NOT NULL DEFAULT now()`).

#### `contact_identities`
*   `id` (`TEXT PRIMARY KEY`): Prefixed ULID (`idt_...`).
*   `tenant_id` (`TEXT NOT NULL`): Tenant isolation key.
*   `contact_id` (`TEXT NOT NULL REFERENCES contacts(id)`).
*   `channel` (`TEXT NOT NULL`): Channel name (`whatsapp`, `teams`, `web`, `email`).
*   `external_id` (`TEXT NOT NULL`): E.164 phone number, Entra Object ID (`oid`), or anonymous token.
*   `verified` (`BOOLEAN NOT NULL DEFAULT false`): True if cryptographic or OTP proof has succeeded.
*   `confidence` (`NUMERIC(4,3)`): Match confidence score ($0.000$ to $1.000$).
*   `match_reason` (`TEXT`): Match basis (`channel_exact`, `verified_otp`, `oauth_subject`, `candidate_link`).
*   *Constraint:* `UNIQUE (tenant_id, channel, external_id)`.

---

### 3.2 Conversational & Agent State Models

#### `conversations`
*   `id` (`TEXT PRIMARY KEY`): Prefixed ULID (`cnv_...`).
*   `tenant_id` (`TEXT NOT NULL`): Tenant isolation key.
*   `contact_id` (`TEXT REFERENCES contacts(id)`).
*   `channel_id` (`TEXT NOT NULL`): Ingress channel reference.
*   `status` (`TEXT NOT NULL DEFAULT 'open'`): `open`, `pending`, `snoozed`, `closed`.
*   `priority` (`TEXT NOT NULL DEFAULT 'normal'`): `low`, `normal`, `high`, `urgent`.
*   `assignee_id` (`TEXT`): Operator user ID or NULL if unassigned.
*   `autonomy_mode` (`TEXT NOT NULL DEFAULT 'assist'`): `observe`, `assist`, `autonomous`.
*   `last_msg_at` (`TIMESTAMPTZ`): Timestamp of newest incoming/outgoing message.
*   `sla_due_at` (`TIMESTAMPTZ`): Calculated resolution deadline.
*   `version` (`INT NOT NULL DEFAULT 1`): Concurrency version column for optimistic locking.
*   `created_at` (`TIMESTAMPTZ NOT NULL DEFAULT now()`).

#### `messages`
*   `id` (`TEXT PRIMARY KEY`): Prefixed ULID (`msg_...`).
*   `tenant_id` (`TEXT NOT NULL`): Tenant isolation key.
*   `conversation_id` (`TEXT NOT NULL REFERENCES conversations(id)`).
*   `direction` (`TEXT NOT NULL`): `inbound`, `outbound`, `internal_note`.
*   `author_type` (`TEXT NOT NULL`): `contact`, `agent`, `human`, `system`.
*   `author_id` (`TEXT`): Originating actor ID.
*   `content` (`JSONB NOT NULL`): Structured payload: `{text: str, blocks: list, attachments: list}`.
*   `external_id` (`TEXT`): Provider's message ID (for webhook deduplication).
*   `channel_external_key` (`TEXT`): Unique synthetic key `channel:external_id`.
*   `agent_run_id` (`TEXT`): Associated run if emitted by an agent.
*   `created_at` (`TIMESTAMPTZ NOT NULL DEFAULT now()`).
*   *Constraint:* `UNIQUE (tenant_id, channel_external_key)`.

#### `agent_runs`
*   `id` (`TEXT PRIMARY KEY`): Prefixed ULID (`run_...`).
*   `tenant_id` (`TEXT NOT NULL`): Tenant isolation key.
*   `conversation_id` (`TEXT REFERENCES conversations(id)`).
*   `agent_version` (`TEXT NOT NULL`): Content-addressed hash reference (`agv_<sha256>`).
*   `workflow_id` (`TEXT NOT NULL`): Temporal workflow ID.
*   `trigger` (`JSONB NOT NULL`): Trigger metadata.
*   `status` (`TEXT NOT NULL`): `running`, `waiting_approval`, `completed`, `failed`, `handed_off`, `budget_exceeded`.
*   `outcome` (`JSONB`): Final execution summary and customer reply details.
*   `budget` (`JSONB NOT NULL`): `{steps: 12, wall_ms: 90000, usd: 0.50, tool_calls: 8}`.
*   `consumed` (`JSONB NOT NULL DEFAULT '{}'`): Actual resource consumption.
*   `trace_id` (`TEXT NOT NULL`): Unified correlation ID matching OpenTelemetry.
*   `started_at` (`TIMESTAMPTZ NOT NULL DEFAULT now()`).
*   `finished_at` (`TIMESTAMPTZ`).

---

### 3.3 Audit Store & Cryptographic Hash Chaining

#### `audit_events`
*   `id` (`TEXT PRIMARY KEY`): Prefixed ULID (`aud_...`).
*   `tenant_id` (`TEXT NOT NULL`): Tenant isolation key.
*   `occurred_at` (`TIMESTAMPTZ NOT NULL DEFAULT now()`).
*   `event_type` (`TEXT NOT NULL`): Domain event type (e.g., `tool.executed`, `policy.verdict`).
*   `actor_type` (`TEXT NOT NULL`): `human`, `agent`, `system`, `connector`.
*   `actor_id` (`TEXT`): Machine or human subject.
*   `on_behalf_of` (`TEXT`): Delegating human principal (crucial enterprise accountability field).
*   `target_type` (`TEXT`): Type of modified entity (`case`, `order`, `ticket`).
*   `target_id` (`TEXT`): Identity of modified entity in upstream systems.
*   `correlation_id` (`TEXT NOT NULL`): Distributed trace correlation ID (`trace_id`).
*   `causation_id` (`TEXT`): Upstream triggering event ID.
*   `data` (`JSONB NOT NULL`): Structured event body (or redacted payload metadata).
*   `data_ref` (`TEXT`): Offloaded Azure Blob Storage URI for large payloads.
*   `prev_hash` (`TEXT`): SHA-256 hash of previous audit event in tenant stream.
*   `hash` (`TEXT NOT NULL`): Current row hash:
    $$\text{hash} = \text{SHA256}(\text{prev\_hash} \parallel \text{canonical\_json}(\text{event}))$$

---

## 4. Payload Offloading Policy

To preserve PostgreSQL performance, minimize TOAST table overhead, and enable GDPR erasure compliance:
1. Payloads exceeding **32 KB** or containing sensitive customer data are offloaded to Azure Blob Storage.
2. The database row records an immutable pointer:
   ```json
   {
     "blob_uri": "https://relaystorage.blob.core.windows.net/tenants/tnt_123/payloads/01J8X...",
     "sha256": "4f9d2c...",
     "bytes": 45120,
     "redaction_profile": "customer_pii_v1"
   }
   ```
3. When processing a Right-to-Erasure (GDPR) request, deleting the blob removes the PII while leaving the audit event structure and hash chain mathematically intact.
