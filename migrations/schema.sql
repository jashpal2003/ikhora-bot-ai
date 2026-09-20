-- =============================================================================
-- Project Relay — Production Database Schema & Security Policies
-- Engine: PostgreSQL 16 with pgvector extension
-- Isolation: Row-Level Security (RLS) forced across all tenant tables
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- -----------------------------------------------------------------------------
-- 1. Tenancy
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenants (
    id            TEXT PRIMARY KEY,                     -- tnt_01J8...
    name          TEXT NOT NULL,
    plan          TEXT NOT NULL DEFAULT 'starter',      -- starter|growth|enterprise
    region        TEXT NOT NULL DEFAULT 'weu',          -- weu|eus
    settings      JSONB NOT NULL DEFAULT '{}',
    status        TEXT NOT NULL DEFAULT 'active',       -- active|suspended|deprovisioned
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- 2. Identity & Contacts
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contacts (
    id            TEXT PRIMARY KEY,                     -- cnt_01J8...
    tenant_id     TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    display_name  TEXT,
    profile       JSONB NOT NULL DEFAULT '{}',
    consent       JSONB NOT NULL DEFAULT '{}',
    merged_into   TEXT REFERENCES contacts(id),         -- soft-merge pointer
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_contacts_tenant ON contacts (tenant_id);
CREATE INDEX IF NOT EXISTS idx_contacts_merged ON contacts (merged_into) WHERE merged_into IS NOT NULL;

CREATE TABLE IF NOT EXISTS contact_identities (
    id            TEXT PRIMARY KEY,                     -- idt_01J8...
    tenant_id     TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    contact_id    TEXT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    channel       TEXT NOT NULL,                        -- whatsapp|teams|web|email
    external_id   TEXT NOT NULL,                        -- E.164 phone, Entra OID, session token
    verified      BOOLEAN NOT NULL DEFAULT false,
    confidence    NUMERIC(4,3) NOT NULL DEFAULT 1.000,
    match_reason  TEXT NOT NULL DEFAULT 'channel_exact',-- channel_exact|verified_otp|oauth_subject|candidate_link
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, channel, external_id)
);

CREATE INDEX IF NOT EXISTS idx_contact_identities_lookup 
ON contact_identities (tenant_id, channel, external_id);

-- -----------------------------------------------------------------------------
-- 3. Conversations & Messages
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS channels (
    id            TEXT PRIMARY KEY,                     -- chn_01J8...
    tenant_id     TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    type          TEXT NOT NULL,                        -- whatsapp|teams|web
    name          TEXT NOT NULL,
    config        JSONB NOT NULL DEFAULT '{}',
    status        TEXT NOT NULL DEFAULT 'active',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
    id            TEXT PRIMARY KEY,                     -- cnv_01J8...
    tenant_id     TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    contact_id    TEXT REFERENCES contacts(id) ON DELETE SET NULL,
    channel_id    TEXT NOT NULL REFERENCES channels(id),
    status        TEXT NOT NULL DEFAULT 'open',         -- open|pending|snoozed|closed
    priority      TEXT NOT NULL DEFAULT 'normal',       -- low|normal|high|urgent
    assignee_id   TEXT,                                 -- operator user id
    autonomy_mode TEXT NOT NULL DEFAULT 'assist',       -- observe|assist|autonomous
    last_msg_at   TIMESTAMPTZ,
    sla_due_at    TIMESTAMPTZ,
    version       INT NOT NULL DEFAULT 1,               -- optimistic concurrency
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversations_inbox 
ON conversations (tenant_id, status, last_msg_at DESC);

CREATE TABLE IF NOT EXISTS messages (
    id                    TEXT PRIMARY KEY,             -- msg_01J8...
    tenant_id             TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id       TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    direction             TEXT NOT NULL,                -- inbound|outbound|internal_note
    author_type           TEXT NOT NULL,                -- contact|agent|human|system
    author_id             TEXT,
    content               JSONB NOT NULL,               -- {text, blocks[], attachments[]}
    external_id           TEXT,
    channel_external_key  TEXT,                         -- synthetic key for deduplication
    agent_run_id          TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, channel_external_key)
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation 
ON messages (conversation_id, created_at ASC);

-- -----------------------------------------------------------------------------
-- 4. Tickets & Escalations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tickets (
    id            TEXT PRIMARY KEY,                     -- tkt_01J8...
    tenant_id     TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id TEXT REFERENCES conversations(id) ON DELETE SET NULL,
    contact_id    TEXT REFERENCES contacts(id) ON DELETE SET NULL,
    title         TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'new',          -- new|in_progress|waiting|escalated|resolved|closed
    priority      TEXT NOT NULL DEFAULT 'normal',       -- low|normal|high|urgent
    assigned_to   TEXT,
    handoff_packet JSONB,                               -- structured reason, evidence, attempts
    metadata      JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tickets_tenant_status 
ON tickets (tenant_id, status, created_at DESC);

-- -----------------------------------------------------------------------------
-- 5. Agent Runs, Steps & Tool Executions
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_runs (
    id              TEXT PRIMARY KEY,                   -- run_01J8...
    tenant_id       TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id TEXT REFERENCES conversations(id) ON DELETE SET NULL,
    agent_version   TEXT NOT NULL,                      -- agv_<sha256>
    workflow_id     TEXT NOT NULL,                      -- Temporal workflow instance ID
    trigger         JSONB NOT NULL,
    status          TEXT NOT NULL,                      -- running|waiting_approval|completed|failed|handed_off|budget_exceeded
    outcome         JSONB,
    budget          JSONB NOT NULL,                     -- {steps: 12, wall_ms: 90000, usd: 0.50, tool_calls: 8}
    consumed        JSONB NOT NULL DEFAULT '{}',
    trace_id        TEXT NOT NULL,                      -- OpenTelemetry trace_id == correlation_id
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_trace 
ON agent_runs (trace_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_tenant 
ON agent_runs (tenant_id, started_at DESC);

CREATE TABLE IF NOT EXISTS agent_steps (
    id            TEXT PRIMARY KEY,                     -- stp_01J8...
    tenant_id     TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    run_id        TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    seq           INT NOT NULL,
    step_type     TEXT NOT NULL,                        -- decide|retrieve|plan|tool|verify|respond|handoff
    input_ref     TEXT,                                 -- blob storage pointer or JSON
    output_ref    TEXT,
    latency_ms    INT,
    cost_usd      NUMERIC(12,6),
    error         JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, seq)
);

CREATE TABLE IF NOT EXISTS tool_executions (
    id              TEXT PRIMARY KEY,                   -- tex_01J8...
    tenant_id       TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    run_id          TEXT REFERENCES agent_runs(id) ON DELETE SET NULL,
    step_id         TEXT REFERENCES agent_steps(id) ON DELETE SET NULL,
    tool_name       TEXT NOT NULL,
    tool_version    TEXT NOT NULL,
    side_effect     TEXT NOT NULL,                      -- read|write|external|destructive|financial
    idempotency_key TEXT NOT NULL,
    input_hash      TEXT NOT NULL,
    output_ref      TEXT,
    status          TEXT NOT NULL,                      -- authorized|denied|pending_approval|executing|succeeded|failed|compensated
    policy_verdict  JSONB NOT NULL,                     -- immutable authorize() verdict
    approval_id     TEXT,
    external_ref    TEXT,                               -- id in target system (e.g. CAS-4471)
    latency_ms      INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, tool_name, idempotency_key)      -- DB-enforced exactly-once execution
);

-- -----------------------------------------------------------------------------
-- 6. Append-Only Tamper-Evident Audit Store
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_events (
    id             TEXT PRIMARY KEY,                    -- aud_01J8...
    tenant_id      TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    occurred_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_type     TEXT NOT NULL,
    actor_type     TEXT NOT NULL,                       -- human|agent|system|connector
    actor_id       TEXT,
    on_behalf_of   TEXT,                                -- enterprise delegating user
    target_type    TEXT,
    target_id      TEXT,
    correlation_id TEXT NOT NULL,                       -- trace_id
    causation_id   TEXT,
    data           JSONB NOT NULL,
    data_ref       TEXT,                                -- Azure Blob Storage pointer for large/PII payloads
    prev_hash      TEXT,                                -- preceding event hash for this tenant
    hash           TEXT NOT NULL                        -- sha256(prev_hash || canonical_json(event))
);

CREATE INDEX IF NOT EXISTS idx_audit_events_tenant 
ON audit_events (tenant_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_correlation 
ON audit_events (correlation_id);

-- Enforce append-only invariant on audit_events at database level
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_events is strictly append-only. UPDATE and DELETE operations are prohibited.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_events_immutable ON audit_events;
CREATE TRIGGER trg_audit_events_immutable
BEFORE UPDATE OR DELETE ON audit_events
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

-- -----------------------------------------------------------------------------
-- 7. Transactional Outbox
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS outbox (
    id            TEXT PRIMARY KEY,                     -- out_01J8...
    tenant_id     TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    topic         TEXT NOT NULL,
    payload       JSONB NOT NULL,
    occurred_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_outbox_unprocessed 
ON outbox (occurred_at ASC) WHERE processed_at IS NULL;

-- -----------------------------------------------------------------------------
-- 8. Knowledge Fabric & ACL Tracking
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_sources (
    id            TEXT PRIMARY KEY,                     -- ksr_01J8...
    tenant_id     TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    type          TEXT NOT NULL,                        -- sharepoint|onedrive|web|upload
    name          TEXT NOT NULL,
    config        JSONB NOT NULL DEFAULT '{}',
    visibility    TEXT NOT NULL DEFAULT 'restricted',   -- public|restricted
    last_synced_at TIMESTAMPTZ,
    status        TEXT NOT NULL DEFAULT 'active',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
    id               TEXT PRIMARY KEY,                  -- doc_01J8...
    tenant_id        TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_id        TEXT NOT NULL REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    external_id      TEXT NOT NULL,                     -- Graph DriveItem ID
    title            TEXT NOT NULL,
    uri              TEXT,
    version          TEXT NOT NULL DEFAULT '1.0',
    content_checksum TEXT NOT NULL,
    acl_hash         TEXT NOT NULL,                     -- detects permission changes without re-extracting
    visibility       TEXT NOT NULL DEFAULT 'restricted',
    metadata         JSONB NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, source_id, external_id)
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id            TEXT PRIMARY KEY,                     -- chk_01J8...
    tenant_id     TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_id   TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index   INT NOT NULL,
    content       TEXT NOT NULL,
    breadcrumb    TEXT,                                 -- e.g. "Refund Policy > Damaged Goods"
    embedding     vector(1536),                         -- pgvector embedding
    tsv_content   tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    metadata      JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, chunk_index)
);

-- Full-text GIN index
CREATE INDEX IF NOT EXISTS idx_chunks_tsv ON document_chunks USING GIN(tsv_content);
-- Vector HNSW index for cosine distance
CREATE INDEX IF NOT EXISTS idx_chunks_embedding 
ON document_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE TABLE IF NOT EXISTS acl_grants (
    id            TEXT PRIMARY KEY,                     -- acl_01J8...
    tenant_id     TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_id   TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    principal_id  TEXT NOT NULL,                        -- user OID or Entra group OID
    principal_type TEXT NOT NULL,                       -- user|group|tenant
    permission    TEXT NOT NULL,                        -- read|write|full
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_acl_grants_lookup 
ON acl_grants (tenant_id, principal_id, permission);

-- -----------------------------------------------------------------------------
-- 9. Row-Level Security (RLS) Configuration
-- Enforced on all tables containing tenant-scoped data
-- -----------------------------------------------------------------------------
DO $$ 
DECLARE
    tbl text;
    tables text[] := ARRAY[
        'contacts', 'contact_identities', 'channels', 'conversations',
        'messages', 'tickets', 'agent_runs', 'agent_steps', 'tool_executions',
        'audit_events', 'outbox', 'knowledge_sources', 'documents',
        'document_chunks', 'acl_grants'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', tbl);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY;', tbl);
        EXECUTE format('DROP POLICY IF EXISTS tenant_isolation_policy ON %I;', tbl);
        EXECUTE format('
            CREATE POLICY tenant_isolation_policy ON %I
            AS RESTRICTIVE
            USING (tenant_id = current_setting(''relay.tenant_id'', true)::text)
            WITH CHECK (tenant_id = current_setting(''relay.tenant_id'', true)::text);
        ', tbl);
    END LOOP;
END $$;
