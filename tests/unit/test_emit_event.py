"""Unit: emit_event validation and behaviour."""
from utils.events import emit_event, VALID_EVENT_TYPES


def test_valid_event_types_complete():
    """All 6 locked event types are present."""
    expected = {
        "comms_sent", "inbound_parsed", "milestone_changed",
        "gate_raised", "human_decision", "progression_state_changed",
    }
    assert VALID_EVENT_TYPES == expected


def test_invalid_event_type_returns_none():
    """Invalid event_type should return None, not raise."""
    result = emit_event(
        event_type="made_up_type",
        property_address="Test Address",
    )
    assert result is None


def test_missing_property_address_returns_none():
    """Missing property_address should return None."""
    result = emit_event(
        event_type="comms_sent",
        property_address="",
    )
    assert result is None


def test_none_property_address_returns_none():
    result = emit_event(
        event_type="comms_sent",
        property_address=None,
    )
    assert result is None


def test_valid_event_inserts_and_cleanup(supabase_client):
    """A valid emit_event call should insert and return the row."""
    result = emit_event(
        event_type="comms_sent",
        property_address="UNIT_TEST_DELETE_ME",
        summary="Unit test event",
        actor="pytest",
        payload={"unit_test": True},
    )
    assert result is not None
    assert result["event_type"] == "comms_sent"
    assert result["property_address"] == "UNIT_TEST_DELETE_ME"

    supabase_client.table("events").delete().eq("id", result["id"]).execute()


def test_default_actor_is_system(supabase_client):
    """When actor is not provided, defaults to 'system'."""
    result = emit_event(
        event_type="gate_raised",
        property_address="UNIT_TEST_DELETE_ME",
        summary="Default actor test",
    )
    assert result["actor"] == "system"

    supabase_client.table("events").delete().eq("id", result["id"]).execute()


def test_payload_defaults_to_empty_dict(supabase_client):
    """When payload is not provided, defaults to {}."""
    result = emit_event(
        event_type="milestone_changed",
        property_address="UNIT_TEST_DELETE_ME",
        summary="Default payload test",
    )
    assert result["payload"] == {}

    supabase_client.table("events").delete().eq("id", result["id"]).execute()
