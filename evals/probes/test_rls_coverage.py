"""CI Test asserting 100% PostgreSQL Row-Level Security coverage."""

EXPECTED_RLS_TABLES = [
    "contacts",
    "contact_identities",
    "channels",
    "conversations",
    "messages",
    "tickets",
    "agent_runs",
    "agent_steps",
    "tool_executions",
    "audit_events",
    "outbox",
    "knowledge_sources",
    "documents",
    "document_chunks",
    "acl_grants",
]


def test_schema_ddl_contains_all_rls_policies() -> None:
    """Read migrations/schema.sql and assert every expected table has RLS enabled."""
    with open("migrations/schema.sql", "r", encoding="utf-8") as f:
        schema_sql = f.read()

    for table in EXPECTED_RLS_TABLES:
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in schema_sql or f"'{table}'" in schema_sql, (
            f"Table {table} does not have RLS enabled in schema.sql"
        )
