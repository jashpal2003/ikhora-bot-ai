# ADR 002: PostgreSQL Row-Level Security for Multi-Tenant Isolation

## Status
Accepted

## Context
Multi-tenancy isolation can be implemented via database-per-tenant, schema-per-tenant, application-level `WHERE` clauses, or PostgreSQL Row-Level Security (RLS).
- Application-level filtering alone poses severe security risks: a single missing `WHERE tenant_id = ?` clause causes a critical cross-tenant data breach.
- Schema-per-tenant introduces migration overhead at scale (500+ tenants require hours of Alembic runs).
- Database-per-tenant is economically and operationally prohibitive for hundreds of mid-market customers.

## Decision
We enforce **PostgreSQL Row-Level Security (RLS)** on all tenant-bearing tables:
1. `FORCE ROW LEVEL SECURITY` is enabled on all tables (applying to table owners and application roles alike).
2. The application executes under a dedicated non-superuser role.
3. Every transaction invokes `SELECT set_config('relay.tenant_id', :tid, true)` with `is_local = true` to prevent tenant leakage across pooled connections (PgBouncer).
4. CI includes an automated test asserting 100% RLS policy coverage on all tables, plus nightly cross-tenant access probe suites.

## Consequences
- **Positive:** Multi-tenant security is guaranteed at the database engine level.
- **Negative:** Transaction-local settings must be strictly maintained across all database calls, background workers, and Temporal activities.
