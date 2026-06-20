"""
NUVU Event Log — utils/events.py

Immutable event emitter. Every AI action, human decision,
and state change flows through emit_event().

Event types (locked):
  comms_sent, inbound_parsed, milestone_changed,
  gate_raised, human_decision, progression_state_changed
"""
import logging
from db_supabase import supabase

logger = logging.getLogger(__name__)

VALID_EVENT_TYPES = {
    "comms_sent",
    "inbound_parsed",
    "milestone_changed",
    "gate_raised",
    "human_decision",
    "progression_state_changed",
}


def emit_event(event_type, property_address, summary=None,
               actor=None, payload=None):
    """
    Append an immutable event to the events log.

    Args:
        event_type: One of VALID_EVENT_TYPES (enforced here + DB CHECK).
        property_address: Canonical join key for the property.
        summary: Human-readable one-liner for dashboard display.
        actor: Who/what triggered — 'system', 'chase_engine',
               user email, staff name, etc.
        payload: Dict of event-specific data. Stored as JSONB.

    Returns:
        The inserted event dict, or None on failure.
    """
    if event_type not in VALID_EVENT_TYPES:
        logger.error(f"Invalid event_type: {event_type}")
        return None

    if not property_address:
        logger.error("emit_event called without property_address")
        return None

    row = {
        "event_type": event_type,
        "property_address": property_address,
        "summary": summary,
        "actor": actor or "system",
        "payload": payload or {},
    }

    try:
        result = (
            supabase.table("events")
            .insert(row)
            .execute()
        )
        if result.data:
            logger.info(
                f"Event emitted: {event_type} | "
                f"{property_address} | {summary}"
            )
            return result.data[0]
        else:
            logger.error(f"Event insert returned no data: {row}")
            return None
    except Exception as e:
        logger.error(f"Failed to emit event: {e} | {row}")
        return None
