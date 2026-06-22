"""
NUVU Intake Queue Notifications — utils/intake_notifications.py

Sends a brief Resend email to NOTIFICATION_EMAIL when a property's gate_status
changes (new entry blocked, or blocked → ready).

Rate limiting: uses the intake_queue.notification_sent flag — one notification
per gate_status transition.  When gate_status changes, the completeness gate
resets notification_sent to False so a fresh notification is sent.

Fail-silent: all errors are logged, never raised.
"""

from __future__ import annotations

import logging
import os

import resend

log = logging.getLogger(__name__)

SEND_FROM = "David Britton Estates, powered by NUVU <salesprog@brittonestates.co.uk>"


def _notification_email() -> str:
    return os.environ.get("NOTIFICATION_EMAIL", "").strip()


def _base_url() -> str:
    return os.environ.get("NUVU_BASE_URL", "https://nuvu-production.up.railway.app").rstrip("/")


def send_intake_notification(
    property_address: str,
    gate_status: str,
    property_data: dict,
    missing_fields: list[str],
    tiers: dict,
) -> None:
    """Send one notification to the office inbox for this gate_status event.

    Called by completeness_gate._evaluate_property only on first appearance
    or status change, and only when notification_sent is False.
    Marks notification_sent = True on success.
    """
    to_email = _notification_email()
    if not to_email:
        log.info("[intake_notifications] NOTIFICATION_EMAIL not set — skipping")
        return

    # Re-check notification_sent flag from DB to prevent duplicates
    try:
        from db_supabase import supabase_for_backend
        client = supabase_for_backend()

        check = (
            client.table("intake_queue")
            .select("notification_sent")
            .eq("property_address", property_address)
            .execute()
        )
        row = (check.data or [{}])[0]
        if row.get("notification_sent") is True:
            return
    except Exception as exc:
        log.warning("[intake_notifications] could not check notification_sent: %s", exc)

    subject, body = _build_email(property_address, gate_status, property_data, missing_fields, tiers)

    try:
        resend.Emails.send(
            {
                "from": SEND_FROM,
                "to": [to_email],
                "subject": subject,
                "text": body,
            }
        )
        log.info("[intake_notifications] sent %s notification for '%s'", gate_status, property_address)

        # Mark sent
        try:
            client.table("intake_queue").update({"notification_sent": True}).eq(
                "property_address", property_address
            ).execute()
        except Exception as upd_exc:
            log.warning("[intake_notifications] failed to set notification_sent: %s", upd_exc)

    except Exception as exc:
        log.warning("[intake_notifications] Resend send failed for '%s': %s", property_address, exc)


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
