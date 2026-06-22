"""
NUVU Webhook Receiver — routes/webhook.py

POST /api/webhook/eatoc
Accepts real-time property-change notifications from EATOC.
Authenticates via x-webhook-secret header matched against NUVU_WEBHOOK_SECRET.
Returns 200 immediately; the targeted sync runs in a background daemon thread.

Kill switch: WEBHOOK_RECEIVER_ENABLED env var (default false → 503).
Debounce: if the same property fires again within 10 seconds, skip the sync
          and return 200 (EATOC field-by-field saves can produce bursts).
"""

from __future__ import annotations

import logging
import os
import threading
import time

from flask import Blueprint, jsonify, request

log = logging.getLogger(__name__)

webhook_bp = Blueprint("webhook", __name__)

# In-memory debounce store: { property_address: last_triggered monotonic time }
_debounce: dict[str, float] = {}
_DEBOUNCE_SECONDS = 10


def _webhook_receiver_enabled() -> bool:
    return os.environ.get("WEBHOOK_RECEIVER_ENABLED", "false").lower() == "true"


def _valid_secret(provided: str | None) -> bool:
    expected = os.environ.get("NUVU_WEBHOOK_SECRET", "")
    if not expected:
        log.warning("[webhook] NUVU_WEBHOOK_SECRET not configured — all requests rejected")
        return False
    return bool(provided and provided == expected)


def _background_sync(property_address: str) -> None:
    """Debounce check → single-property sync → emit progression_state_changed event."""
    now = time.monotonic()
    last = _debounce.get(property_address, 0.0)
    if now - last < _DEBOUNCE_SECONDS:
        log.info(
            "[webhook] debounced '%s' — last sync %.1fs ago (threshold %ds)",
            property_address, now - last, _DEBOUNCE_SECONDS,
        )
        return

    _debounce[property_address] = now

    try:
        from utils.adapter_sync import sync_single_property
        sync_single_property(property_address)
    except Exception as exc:
        log.warning("[webhook] sync_single_property error for '%s': %s", property_address, exc)

    try:
        from utils.events import emit_event
        emit_event(
            event_type="progression_state_changed",
            property_address=property_address,
            actor="webhook",
            summary=f"Webhook triggered real-time sync for {property_address}",
            payload={"trigger": "webhook", "property_address": property_address},
        )
    except Exception as exc:
        log.warning("[webhook] emit_event error for '%s': %s", property_address, exc)


@webhook_bp.route("/api/webhook/eatoc", methods=["POST"])
def eatoc_webhook():
    if not _webhook_receiver_enabled():
        return jsonify({"error": "Webhook receiver disabled"}), 503

    secret = request.headers.get("x-webhook-secret")
    if not _valid_secret(secret):
        log.warning("[webhook] rejected — invalid or missing x-webhook-secret")
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    event = (data.get("event") or "").strip()
    property_address = (data.get("property_address") or "").strip()

    if not event or not property_address:
        missing = [f for f, v in [("event", event), ("property_address", property_address)] if not v]
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    log.info(
        "[webhook] accepted event='%s' property='%s' source='%s' ts='%s'",
        event, property_address,
        data.get("source", "unknown"),
        data.get("timestamp", ""),
    )

    t = threading.Thread(
        target=_background_sync,
        args=(property_address,),
        daemon=True,
        name=f"webhook-sync-{property_address[:40]}",
    )
    t.start()

    return jsonify({"status": "accepted"}), 200
