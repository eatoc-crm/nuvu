#!/usr/bin/env python3
"""
NUVU Event Backfill Migration
One-time script to seed historical events from existing tables.

Usage: python scripts/backfill_events.py
       python scripts/backfill_events.py --dry-run

Run from project root with NUVU Supabase env vars set.

Source tables:
  chase_messages      -> comms_sent         (sent_at as timestamp)
  inbound_emails      -> inbound_parsed     (received_at as timestamp)
  chase_confirmations -> human_decision     (created_at as timestamp)
  sales_progression   -> milestone_changed  (one event per non-null milestone field)

All three relational tables (chase_messages, inbound_emails, chase_confirmations)
join via property_id -> sales_progression.id to resolve property_address.
"""

import argparse
import logging
import re
from datetime import datetime, timezone
from db_supabase import supabase_for_backend

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# Milestone fields from routes/progression.py _MILESTONE_FIELDS — single source of truth.
_MILESTONE_FIELDS = {
    "offer_accepted", "memo_sent", "welcome_emails_sent",
    "searches_ordered", "searches_received", "search_fees_confirmed",
    "survey_instructed", "mortgage_offered", "draft_contract_sent",
    "draft_contract_issued", "enquiries_raised", "enquiries_answered",
    "exchange_target_date", "report_on_title", "exchange_date",
    "completion_date", "protocol_forms_returned", "seller_forms_returned",
}

# Regex: ISO 8601 date or datetime string (YYYY-MM-DD…)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _looks_like_date(value) -> bool:
    """Return True if value is a non-empty string that starts with an ISO date."""
    return bool(value and isinstance(value, str) and _DATE_RE.match(value.strip()))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_id_to_address_map(client) -> dict[str, str]:
    """Fetch all sales_progression rows and return {id: property_address}."""
    logger.info("Building sales_progression id → property_address map...")
    out: dict[str, str] = {}
    page_size = 500
    offset = 0
    while True:
        res = (
            client.table("sales_progression")
            .select("id,property_address")
            .order("id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = res.data or []
        for row in rows:
            rid = str(row.get("id") or "").strip()
            addr = (row.get("property_address") or "").strip()
            if rid and addr:
                out[rid] = addr
        if len(rows) < page_size:
            break
        offset += len(rows)
    logger.info(f"  Loaded {len(out)} sales_progression records.")
    return out


def _batch_insert(client, events: list[dict], dry_run: bool) -> None:
    """Insert events in chunks of 100; no-op when dry_run is True."""
    if dry_run or not events:
        return
    for i in range(0, len(events), 100):
        chunk = events[i : i + 100]
        client.table("events").insert(chunk).execute()
        logger.info(f"    Inserted {len(chunk)} rows ({i + len(chunk)}/{len(events)})")


# ─────────────────────────────────────────────────────────────────────────────
#  Source 1: chase_messages → comms_sent
# ─────────────────────────────────────────────────────────────────────────────

def backfill_chase_messages(client, id_to_addr: dict[str, str], dry_run=False) -> int:
    """chase_messages → comms_sent events."""
    logger.info("Backfilling chase_messages → comms_sent...")

    res = client.table("chase_messages").select("*").execute()
    rows = res.data or []
    logger.info(f"  Found {len(rows)} rows in chase_messages")

    events = []
    skipped = 0
    for row in rows:
        property_id = str(row.get("property_id") or "").strip()
        property_address = id_to_addr.get(property_id)
        if not property_address:
            logger.warning(
                f"  chase_messages id={row.get('id')}: "
                f"property_id={property_id!r} not in sales_progression — skipping"
            )
            skipped += 1
            continue

        # Prefer sent_at (when the email actually left); fall back to created_at.
        timestamp = row.get("sent_at") or row.get("created_at") or _now_iso()

        recipient_email = row.get("recipient_email") or "unknown"
        recipient_type = row.get("recipient_type") or ""
        label = f"{recipient_type} {recipient_email}".strip() if recipient_type else recipient_email

        events.append({
            "event_type": "comms_sent",
            "property_address": property_address,
            "summary": f"[Backfill] Chase sent to {label}",
            "actor": "chase_engine",
            "payload": {
                "backfill": True,
                "source_table": "chase_messages",
                "source_id": row.get("id"),
                "chase_stage": row.get("chase_stage"),
                "chase_day": row.get("chase_day"),
                "recipient_type": row.get("recipient_type"),
                "recipient_email": recipient_email,
                "subject": row.get("subject"),
                "message_type": row.get("message_type"),
                "chain_link_id": row.get("chain_link_id"),
            },
            "created_at": timestamp,
        })

    logger.info(f"  → {len(events)} events ({skipped} skipped — no address match)")
    _batch_insert(client, events, dry_run)
    return len(events)


# ─────────────────────────────────────────────────────────────────────────────
#  Source 2: inbound_emails → inbound_parsed
# ─────────────────────────────────────────────────────────────────────────────

def backfill_inbound_emails(client, id_to_addr: dict[str, str], dry_run=False) -> int:
    """inbound_emails → inbound_parsed events."""
    logger.info("Backfilling inbound_emails → inbound_parsed...")

    res = client.table("inbound_emails").select("*").execute()
    rows = res.data or []
    logger.info(f"  Found {len(rows)} rows in inbound_emails")

    events = []
    skipped = 0
    for row in rows:
        property_id = str(row.get("property_id") or "").strip()
        property_address = id_to_addr.get(property_id)
        if not property_address:
            logger.warning(
                f"  inbound_emails id={row.get('id')}: "
                f"property_id={property_id!r} not in sales_progression — skipping"
            )
            skipped += 1
            continue

        # Prefer received_at; fall back to created_at.
        timestamp = row.get("received_at") or row.get("created_at") or _now_iso()

        sender = row.get("sender_email") or row.get("sender_name") or "unknown"

        events.append({
            "event_type": "inbound_parsed",
            "property_address": property_address,
            "summary": f"[Backfill] Inbound from {sender}",
            "actor": "inbound_parser",
            "payload": {
                "backfill": True,
                "source_table": "inbound_emails",
                "source_id": row.get("id"),
                "sender_email": row.get("sender_email"),
                "sender_name": row.get("sender_name"),
                "subject": row.get("subject"),
                "body_preview": (row.get("body_preview") or "")[:300],
            },
            "created_at": timestamp,
        })

    logger.info(f"  → {len(events)} events ({skipped} skipped — no address match)")
    _batch_insert(client, events, dry_run)
    return len(events)


# ─────────────────────────────────────────────────────────────────────────────
#  Source 3: chase_confirmations → human_decision
# ─────────────────────────────────────────────────────────────────────────────

def backfill_chase_confirmations(client, id_to_addr: dict[str, str], dry_run=False) -> int:
    """chase_confirmations → human_decision events."""
    logger.info("Backfilling chase_confirmations → human_decision...")

    res = client.table("chase_confirmations").select("*").execute()
    rows = res.data or []
    logger.info(f"  Found {len(rows)} rows in chase_confirmations")

    events = []
    skipped = 0
    for row in rows:
        property_id = str(row.get("property_id") or "").strip()
        property_address = id_to_addr.get(property_id)
        if not property_address:
            logger.warning(
                f"  chase_confirmations id={row.get('id')}: "
                f"property_id={property_id!r} not in sales_progression — skipping"
            )
            skipped += 1
            continue

        timestamp = row.get("created_at") or _now_iso()
        status = row.get("status") or "unknown"
        confirmed_by = row.get("confirmed_by") or "unknown"
        milestone = row.get("suggested_milestone") or ""

        summary_parts = [f"[Backfill] Confirmation ({status})"]
        if milestone:
            summary_parts.append(f"re: {milestone}")
        if confirmed_by and confirmed_by != "unknown":
            summary_parts.append(f"by {confirmed_by}")

        events.append({
            "event_type": "human_decision",
            "property_address": property_address,
            "summary": " ".join(summary_parts),
            "actor": confirmed_by if confirmed_by != "unknown" else "system",
            "payload": {
                "backfill": True,
                "source_table": "chase_confirmations",
                "source_id": row.get("id"),
                "status": status,
                "confirmed_by": row.get("confirmed_by"),
                "suggested_milestone": milestone,
                "suggested_value": row.get("suggested_value"),
                "inbound_email_id": row.get("inbound_email_id"),
            },
            "created_at": timestamp,
        })

    logger.info(f"  → {len(events)} events ({skipped} skipped — no address match)")
    _batch_insert(client, events, dry_run)
    return len(events)


# ─────────────────────────────────────────────────────────────────────────────
#  Source 4: sales_progression milestone fields → milestone_changed
# ─────────────────────────────────────────────────────────────────────────────

def backfill_sales_progression(client, dry_run=False) -> int:
    """sales_progression milestone dates → milestone_changed events.

    One event per non-null milestone field per row.
    Uses the field value as created_at when it looks like an ISO date/datetime;
    falls back to updated_at then created_at of the row.
    """
    logger.info("Backfilling sales_progression → milestone_changed...")

    res = client.table("sales_progression").select("*").execute()
    rows = res.data or []
    logger.info(f"  Found {len(rows)} rows in sales_progression")

    events = []
    for row in rows:
        property_address = (row.get("property_address") or "").strip()
        if not property_address:
            logger.warning(
                f"  sales_progression id={row.get('id')}: "
                "no property_address — skipping all milestone events for this row"
            )
            continue

        row_fallback_ts = row.get("updated_at") or row.get("created_at") or _now_iso()

        for field in sorted(_MILESTONE_FIELDS):
            value = row.get(field)
            if value is None or value == "" or value is False:
                continue

            field_str = str(value)

            # Use the field value itself as the timestamp when it's a date/datetime.
            if _looks_like_date(field_str):
                timestamp = field_str
            else:
                # Boolean True or unexpected format — anchor to the row's own timestamp.
                timestamp = row_fallback_ts

            events.append({
                "event_type": "milestone_changed",
                "property_address": property_address,
                "summary": f"[Backfill] {field} set to {field_str}",
                "actor": "backfill",
                "payload": {
                    "backfill": True,
                    "source_table": "sales_progression",
                    "source_id": row.get("id"),
                    "milestone": field,
                    "new_value": field_str,
                },
                "created_at": timestamp,
            })

    logger.info(f"  → {len(events)} events across {len(rows)} rows")
    _batch_insert(client, events, dry_run)
    return len(events)


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill NUVU historical events")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count events that would be inserted without touching the database",
    )
    args = parser.parse_args()

    if args.dry_run:
        logger.info("=== DRY RUN — nothing will be inserted ===")

    client = supabase_for_backend()

    # Resolve property_id → property_address for relational tables.
    id_to_addr = _build_id_to_address_map(client)

    totals: dict[str, int] = {}
    totals["comms_sent"]      = backfill_chase_messages(client, id_to_addr, args.dry_run)
    totals["inbound_parsed"]  = backfill_inbound_emails(client, id_to_addr, args.dry_run)
    totals["human_decision"]  = backfill_chase_confirmations(client, id_to_addr, args.dry_run)
    totals["milestone_changed"] = backfill_sales_progression(client, args.dry_run)

    logger.info("")
    logger.info("=== BACKFILL COMPLETE ===")
    for etype, count in totals.items():
        logger.info(f"  {etype}: {count} events")
    logger.info(f"  TOTAL: {sum(totals.values())} events")
    if args.dry_run:
        logger.info("  (DRY RUN — nothing inserted)")
    else:
        logger.info("  Events are live in Supabase.")
        logger.info("")
        logger.info("  Verify with:")
        logger.info("    SELECT event_type, COUNT(*) FROM events WHERE payload->>\'backfill\' = \'true\' GROUP BY event_type;")
