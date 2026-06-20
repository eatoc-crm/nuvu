"""Smoke: All critical modules import without error."""


def test_import_events():
    from utils.events import emit_event, VALID_EVENT_TYPES
    assert len(VALID_EVENT_TYPES) == 6


def test_import_event_queries():
    from utils.event_queries import (
        get_recent_events, get_property_events,
        get_event_counts_by_type, get_active_gates,
    )


def test_import_eatoc_api():
    from utils.eatoc_api import eatoc_post, eatoc_patch, eatoc_get


def test_import_adapter_sync():
    from utils.adapter_sync import sync_sales_pipeline, sync_chain_links


def test_import_needs_attention():
    from utils.needs_attention import emit_needs_attention_events
