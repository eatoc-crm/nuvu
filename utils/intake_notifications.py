"""
NUVU Intake Queue Notifications — utils/intake_notifications.py

Sends gate notifications through notification_log so queue rebuilds cannot
re-trigger the same email. The intake_queue.notification_sent column is kept
only as a display flag.

Fail-silent: all errors are logged, never raised.
"""

from __future__ import annotations

import logging
import os
from html import escape

from utils.notification_log import (
    _content_hash,
    _insert_notification_log,
    _notification_exists,
    send_notification_once,
)
from utils.send_governor import governed_send

log = logging.getLogger(__name__)

SEND_FROM = "David Britton Estates, powered by NUVU <salesprog@brittonestates.co.uk>"
DIGEST_PROPERTY_ADDRESS = "__gate_digest__"


def _notification_email() -> str:
    return os.environ.get("NOTIFICATION_EMAIL", "").strip()


def _base_url() -> str:
    return os.environ.get("NUVU_BASE_URL", "https://nuvu-production.up.railway.app").rstrip("/")


def _send_notification_email(to_email: str, subject: str, body: str, source: str):
    result = governed_send(
        "notifications",
        to_email,
        subject,
        f"<pre style=\"font-family:system-ui,-apple-system,sans-serif;white-space:pre-wrap;\">{escape(body)}</pre>",
        metadata={"source": source},
        from_address=SEND_FROM,
    )
    if result != "sent":
        raise RuntimeError(result)
    return result


def send_intake_notification(
    property_address: str,
    gate_status: str,
    property_data: dict,
    missing_fields: list[str],
    tiers: dict,
) -> None:
    """Send one notification to the office inbox for this gate_status event.

    Used for single-property gate evaluations and ready notifications. Full
    gate sweeps send blocked-property digest emails via send_gate_digest().
    """
    to_email = _notification_email()
    if not to_email:
        log.info("[intake_notifications] NOTIFICATION_EMAIL not set — skipping")
        return

    subject, body = _build_email(property_address, gate_status, property_data, missing_fields, tiers)
    notification_type = "gate_blocked" if gate_status == "blocked" else "gate_ready"
    content = _gate_blocked_content(missing_fields) if gate_status == "blocked" else body

    try:
        result = send_notification_once(
            property_address,
            notification_type,
            content,
            to_email,
            lambda: _send_notification_email(
                to_email,
                subject,
                body,
                "intake.single_notification",
            ),
        )
        if result in ("sent", "duplicate_skipped"):
            _mark_notification_sent(property_address)
        if result == "sent":
            log.info("[intake_notifications] sent %s notification for '%s'", gate_status, property_address)
        elif result == "duplicate_skipped":
            log.info(
                "[intake_notifications] skipped duplicate %s notification for '%s'",
                gate_status,
                property_address,
            )
        else:
            log.warning(
                "[intake_notifications] notification failed for '%s': %s",
                property_address,
                result,
            )
    except Exception as exc:
        log.warning("[intake_notifications] notification send failed for '%s': %s", property_address, exc)


def send_gate_digest(candidates: list[dict], send_fn=None) -> None:
    """Send one digest email for newly notifiable blocked properties."""
    to_email = _notification_email()
    if not to_email:
        log.info("[intake_notifications] NOTIFICATION_EMAIL not set — skipping digest")
        return

    blocked = [c for c in candidates if c.get("gate_status") == "blocked"]
    if not blocked:
        return

    newly_notifiable: list[dict] = []
    for item in blocked:
        property_address = item.get("property_address", "")
        content = _gate_blocked_content(item.get("missing_fields") or [])
        try:
            if _notification_exists(property_address, "gate_blocked", content):
                _mark_notification_sent(property_address)
            else:
                newly_notifiable.append(item)
        except Exception as exc:
            log.warning(
                "[intake_notifications] could not check notification_log for '%s': %s",
                property_address,
                exc,
            )

    if not newly_notifiable:
        log.info("[intake_notifications] no new blocked properties for digest")
        return

    subject, body = _build_digest_email(newly_notifiable)
    message = {
        "from": SEND_FROM,
        "to": [to_email],
        "subject": subject,
        "text": body,
    }

    def _send_digest():
        if send_fn is not None:
            return send_fn(message)
        return _send_notification_email(
            to_email,
            subject,
            body,
            "intake.gate_digest",
        )

    result = send_notification_once(
        DIGEST_PROPERTY_ADDRESS,
        "gate_digest",
        body,
        to_email,
        _send_digest,
    )

    if result not in ("sent", "duplicate_skipped"):
        log.warning("[intake_notifications] digest notification failed: %s", result)
        return

    digest_hash = _content_hash(body)
    for item in newly_notifiable:
        property_address = item.get("property_address", "")
        content = _gate_blocked_content(item.get("missing_fields") or [])
        payload = {
            "content": content,
            "property_address": property_address,
            "included_in_digest": True,
            "digest_content_hash": digest_hash,
            "missing_fields": content,
            "tiers": item.get("tiers") or {},
        }
        try:
            if not _notification_exists(property_address, "gate_blocked", content):
                _insert_notification_log(
                    property_address,
                    "gate_blocked",
                    content,
                    to_email,
                    payload,
                )
            _mark_notification_sent(property_address)
        except Exception as exc:
            log.error(
                "[intake_notifications] digest sent but failed to log property '%s': %s",
                property_address,
                exc,
            )

    log.info(
        "[intake_notifications] %s gate digest for %d blocked properties",
        "sent" if result == "sent" else "skipped duplicate",
        len(newly_notifiable),
    )


def _mark_notification_sent(property_address: str) -> None:
    try:
        from db_supabase import supabase_for_backend

        supabase_for_backend().table("intake_queue").update({"notification_sent": True}).eq(
            "property_address", property_address
        ).execute()
    except Exception as upd_exc:
        log.warning("[intake_notifications] failed to set notification_sent: %s", upd_exc)


def _gate_blocked_content(missing_fields: list[str]) -> list[str]:
    return sorted(str(field) for field in (missing_fields or []))


def _build_digest_email(candidates: list[dict]) -> tuple[str, str]:
    queue_url = f"{_base_url()}/intake-queue"
    subject = f"NUVU Intake: {len(candidates)} Properties Need Data"
    lines = [
        "The completeness gate found new properties that need attention:",
        "",
    ]

    for item in sorted(candidates, key=lambda c: c.get("property_address", "")):
        property_address = item.get("property_address") or "Unknown property"
        missing = ", ".join(_gate_blocked_content(item.get("missing_fields") or []))
        lines.append(f"- {property_address}")
        lines.append(f"  Missing: {missing or 'See NUVU for details'}")

    lines.extend(
        [
            "",
            f"View details: {queue_url}",
            "",
            "Please enter the missing data in EATOC.",
            "NUVU will re-check automatically on next sync.",
        ]
    )
    return subject, "\n".join(lines)


def _build_email(
    property_address: str,
    gate_status: str,
    property_data: dict,
    missing_fields: list[str],
    tiers: dict,
) -> tuple[str, str]:
    queue_url = f"{_base_url()}/intake-queue"

    buyer_name  = (property_data.get("buyer_name")  or "Unknown").strip()
    vendor_name = (property_data.get("vendor_name") or "Unknown").strip()
    sale_price  = (
        property_data.get("sale_price")
        or property_data.get("agreed_price")
        or property_data.get("current_price")
    )
    price_str = f"£{float(sale_price):,.0f}" if sale_price else "Not recorded"

    if gate_status == "ready":
        subject = f"NUVU Intake: {property_address} — Ready for Approval"
        body = (
            f"New property awaiting your approval:\n\n"
            f"  Property: {property_address}\n"
            f"  Buyer:    {buyer_name}\n"
            f"  Seller:   {vendor_name}\n"
            f"  Price:    {price_str}\n"
            f"  Chain:    Chain-free\n\n"
            f"  Review and approve: {queue_url}\n\n"
            f"This property has passed all completeness checks.\n"
            f"A welcome email will be sent once you approve."
        )
    else:
        failed_tiers = [
            label for key, label in [
                ("1a", "Tier 1A (buyer/seller details)"),
                ("1b", "Tier 1B (solicitors)"),
                ("1c", "Tier 1C (chain)"),
                ("1d", "Tier 1D (transaction details)"),
            ]
            if not tiers.get(key, True)
        ]
        missing_str  = ", ".join(missing_fields) if missing_fields else "See NUVU for details"
        failed_str   = ", ".join(failed_tiers)   if failed_tiers  else "Unknown tier"

        subject = f"NUVU Intake: {property_address} — Data Incomplete"
        body = (
            f"New property needs attention:\n\n"
            f"  Property: {property_address}\n"
            f"  Missing:  {missing_str}\n"
            f"  Failed:   {failed_str}\n\n"
            f"  View details: {queue_url}\n\n"
            f"Please enter the missing data in EATOC.\n"
            f"NUVU will re-check automatically on next sync."
        )

    return subject, body
