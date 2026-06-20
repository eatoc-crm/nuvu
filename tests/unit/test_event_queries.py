"""Unit: Event query functions return expected shapes."""
from utils.event_queries import (
    get_recent_events, get_property_events,
    get_event_counts_by_type, get_active_gates,
    get_event_activity_summary,
)


def test_recent_events_returns_list():
    result = get_recent_events(limit=5)
    assert isinstance(result, list)


def test_recent_events_respects_limit():
    result = get_recent_events(limit=3)
    assert len(result) <= 3


def test_property_events_returns_list():
    result = get_property_events("NONEXISTENT_ADDRESS_XYZ")
    assert isinstance(result, list)
    assert len(result) == 0


def test_event_counts_returns_dict():
    result = get_event_counts_by_type()
    assert isinstance(result, dict)


def test_active_gates_returns_list():
    result = get_active_gates()
    assert isinstance(result, list)


def test_activity_summary_returns_list():
    result = get_event_activity_summary(days=7)
    assert isinstance(result, list)
