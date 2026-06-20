"""Smoke: Supabase is reachable and expected tables exist."""

REQUIRED_TABLES = [
    "events",
    "sales_pipeline",
    "chain_links",
    "sales_progression",
    "chase_messages",
    "chase_confirmations",
    "inbound_emails",
    "chain_chase_state",
]


def test_supabase_connection(supabase_client):
    """Can we connect and run a query?"""
    result = supabase_client.table("events").select("id").limit(1).execute()
    assert result is not None


def test_required_tables_exist(supabase_client):
    """All tables the app depends on must exist."""
    for table in REQUIRED_TABLES:
        result = supabase_client.table(table).select("id").limit(1).execute()
        assert result is not None, f"Table {table} missing or inaccessible"
