"""Smoke: Events table accepts writes and reads."""


def test_event_write_read_cycle(supabase_client):
    """Insert a test event, read it back, delete it."""
    test_row = {
        "event_type": "comms_sent",
        "property_address": "SMOKE_TEST_DELETE_ME",
        "summary": "Smoke test event",
        "actor": "pytest",
        "payload": {"smoke_test": True},
    }

    insert = supabase_client.table("events").insert(test_row).execute()
    assert insert.data, "Event insert returned no data"
    event_id = insert.data[0]["id"]

    read = (
        supabase_client.table("events")
        .select("*")
        .eq("id", event_id)
        .execute()
    )
    assert len(read.data) == 1
    assert read.data[0]["property_address"] == "SMOKE_TEST_DELETE_ME"

    supabase_client.table("events").delete().eq("id", event_id).execute()
