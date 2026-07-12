# utils/event_queries.py
# Reusable query helpers for the events table. Used by dashboard routes only.
# All queries are server-side; never exposed directly as public API endpoints.

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from db_supabase import supabase

logger = logging.getLogger(__name__)


def get_recent_events(limit: int = 50) -> list[dict]:
    """Most recent events across all properties."""
    try:
        result = (
            supabase.table("events")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Failed to fetch recent events: {e}")
        return []


def get_property_events(property_address: str, limit: int = 50) -> list[dict]:
    """All events for a specific property, newest first."""
    try:
        result = (
            supabase.table("events")
            .select("*")
            .eq("property_address", property_address)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Failed to fetch events for {property_address}: {e}")
        return []


def get_event_counts_by_type() -> dict[str, int]:
    """Count of events grouped by type. For dashboard summary cards."""
    try:
        result = (
            supabase.table("events")
            .select("event_type")
            .execute()
        )
        rows = result.data or []
        counts: dict[str, int] = {}
        for row in rows:
            t = row["event_type"]
            counts[t] = counts.get(t, 0) + 1
        return counts
    except Exception as e:
        logger.error(f"Failed to fetch event counts: {e}")
        return {}


def get_active_gates() -> list[dict]:
    """Properties currently waiting in the completeness gate queue."""
    try:
        result = (
            supabase.table("intake_queue")
            .select("property_address,gate_status,missing_fields,created_at,updated_at")
            .in_("gate_status", ["ready", "blocked"])
            .order("updated_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Failed to fetch active gates: {e}")
        return []


def get_event_activity_summary(days: int = 7) -> list[dict]:
    """Activity rows for the last N days. For charts or future sparklines."""
    try:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        result = (
            supabase.table("events")
            .select("event_type,created_at")
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Failed to fetch activity summary: {e}")
        return []
