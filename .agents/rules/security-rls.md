# Database Isolation & Row-Level Security Rules

## 1. Row-Level Security (RLS) Mandate
- Every table containing customer or operational data MUST have:
  1. A non-nullable `tenant_id TEXT REFERENCES tenants(id)` column.
  2. `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;`
  3. `ALTER TABLE <table> FORCE ROW LEVEL SECURITY;`
  4. An isolation policy matching `tenant_id = current_setting('relay.tenant_id', true)::text`.

## 2. Transaction-Scoped Execution
- Database sessions must always be wrapped with `tenant_scope(session, tenant_id)`.
- Global or session-wide settings (`is_local = false`) are prohibited to prevent connection pool poisoning under PgBouncer.
- Superuser connections must never be used for application request processing.

## 3. Append-Only Audit Integrity
- The `audit_events` table is append-only.
- Direct `UPDATE` and `DELETE` queries will fail due to PostgreSQL database triggers.
- Every audit entry MUST include valid `hash` and `prev_hash` values.
