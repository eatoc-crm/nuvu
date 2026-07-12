"""Smoke: health_probe table accepts writes, reads, and cleanup deletes."""


def test_health_probe_write_read_cleanup_cycle(supabase_client):
    """Insert a health probe row, read it back, delete it."""
    test_row = {}

    insert = supabase_client.table("health_probe").insert(test_row).execute()
    assert insert.data, "Health probe insert returned no data"
    event_id = insert.data[0]["id"]

    read = (
        supabase_client.table("health_probe")
        .select("*")
        .eq("id", event_id)
        .execute()
    )
    assert len(read.data) == 1
    assert read.data[0]["id"] == event_id

    supabase_client.table("health_probe").delete().eq("id", event_id).execute()
