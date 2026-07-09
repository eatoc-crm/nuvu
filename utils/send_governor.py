"""Engine-level outbound email governor.

All Resend sends must pass through governed_send().
"""

from __future__ import annotations

import logging
import os
from collections import Counter
from datetime import datetime, time, timedelta, timezone
from typing import Any

import resend

log = logging.getLogger(__name__)

DEFAULT_SEND_FROM = "David Britton Estates, powered by NUVU <salesprog@brittonestates.co.uk>"
SYSTEM_CATEGORY = "system"


def _agency_id() -> str:
    return os.environ.get("NUVU_AGENCY_ID", "dbe").strip() or "dbe"


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    try:
        return max(0, int(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _client():
    from db_supabase import supabase_for_backend

    return supabase_for_backend()


def _category_enabled(category: str) -> bool:
    if category == SYSTEM_CATEGORY:
        return True
    defaults = {
        "notifications": True,
        "welcome": False,
        "chase": False,
        "portal": False,
    }
    env_name = f"SEND_CATEGORY_{category.upper()}"
    return _bool_env(env_name, defaults.get(category, False))


def _window_start_day(now: datetime) -> datetime:
    return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)


def _window_start_hour(now: datetime) -> datetime:
    return now.replace(minute=0, second=0, microsecond=0)


def _fetch_sent_rows_since(client, start: datetime, agency_id: str) -> list[dict[str, Any]]:
    result = (
        client.table("send_log")
        .select("category,outcome,attempted_at")
        .eq("agency_id", agency_id)
        .gte("attempted_at", start.isoformat())
        .execute()
    )
    return [
        row
        for row in (result.data or [])
        if row.get("outcome") == "sent" and row.get("category") != SYSTEM_CATEGORY
    ]


def _insert_send_log(
    *,
    client,
    agency_id: str,
    category: str,
    recipient: str,
    subject: str,
    outcome: str,
    attempted_at: datetime,
    metadata: dict[str, Any] | None,
) -> None:
    row = {
        "agency_id": agency_id,
        "category": category,
        "recipient": recipient,
        "subject": subject,
        "outcome": outcome,
        "attempted_at": attempted_at.isoformat(),
        "metadata": metadata or None,
    }
    client.table("send_log").insert(row).execute()


def _safe_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not metadata:
        return None
    safe = dict(metadata)
    safe.pop("attachments", None)
    return safe


def _recipients(to: str | list[str] | tuple[str, ...]) -> list[str]:
    if isinstance(to, (list, tuple)):
        return [str(addr).strip() for addr in to if str(addr).strip()]
    addr = str(to or "").strip()
    return [addr] if addr else []


def _counts_by_category(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(row.get("category") or "unknown") for row in rows))


def _cap_alert_body(reason: str, counts: dict[str, int], window_start: datetime) -> str:
    lines = [
        "<p>NUVU Send Governor has blocked outbound email because a send cap was hit.</p>",
        f"<p><strong>Cap:</strong> {reason}</p>",
        f"<p><strong>Window start:</strong> {window_start.isoformat()}</p>",
        "<p><strong>Current sent counts by category:</strong></p>",
        "<ul>",
    ]
    for category, count in sorted(counts.items()):
        lines.append(f"<li>{category}: {count}</li>")
    lines.extend(
        [
            "</ul>",
            "<p>Further sends are blocked until the window resets.</p>",
        ]
    )
    return "".join(lines)


def _maybe_send_cap_alert(
    *,
    reason: str,
    window_start: datetime,
    rows: list[dict[str, Any]],
) -> None:
    to_email = os.environ.get("NOTIFICATION_EMAIL", "").strip()
    if not to_email:
        return

    try:
        from utils.notification_log import send_notification_once

        content = {"cap": reason, "window_start": window_start.isoformat()}
        subject = f"NUVU Send Governor cap hit: {reason}"
        html = _cap_alert_body(reason, _counts_by_category(rows), window_start)
        send_notification_once(
            "__send_governor__",
            "governor_cap_alert",
            content,
            to_email,
            lambda: governed_send(
                SYSTEM_CATEGORY,
                to_email,
                subject,
                html,
                metadata={
                    "category": SYSTEM_CATEGORY,
                    "cap": reason,
                    "window_start": window_start.isoformat(),
                },
            ),
        )
    except Exception as exc:
        log.warning("[send_governor] cap alert failed for %s: %s", reason, exc)


def _block(
    *,
    client,
    agency_id: str,
    category: str,
    recipients: list[str],
    subject: str,
    reason: str,
    attempted_at: datetime,
    metadata: dict[str, Any] | None,
    alert_rows: list[dict[str, Any]] | None = None,
    alert_window_start: datetime | None = None,
) -> str:
    outcome = f"blocked:{reason}"
    try:
        _insert_send_log(
            client=client,
            agency_id=agency_id,
            category=category,
            recipient=", ".join(recipients),
            subject=subject,
            outcome=outcome,
            attempted_at=attempted_at,
            metadata=metadata,
        )
    except Exception as exc:
        log.warning("[send_governor] failed to log blocked send: %s", exc)

    if reason in {"hourly_cap", "daily_cap"} and alert_rows is not None and alert_window_start:
        _maybe_send_cap_alert(
            reason=reason,
            window_start=alert_window_start,
            rows=alert_rows,
        )

    return outcome


def governed_send(
    category: str,
    to: str | list[str],
    subject: str,
    html: str,
    metadata: dict[str, Any] | None = None,
    *,
    from_address: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> str:
    """Send an email through the global governor.

    Returns: 'sent' | 'blocked:<reason>'
    Reasons: kill_switch_global, kill_switch_category, hourly_cap, daily_cap
    """
    attempted_at = _now()
    agency_id = _agency_id()
    category = (category or "").strip().lower() or "unknown"
    recipients = _recipients(to)
    subject = str(subject or "")
    safe_metadata = _safe_metadata(metadata)
    client = _client()

    if not _bool_env("SEND_GOVERNOR_ENABLED", True):
        return _block(
            client=client,
            agency_id=agency_id,
            category=category,
            recipients=recipients,
            subject=subject,
            reason="kill_switch_global",
            attempted_at=attempted_at,
            metadata=safe_metadata,
        )

    if not _category_enabled(category):
        return _block(
            client=client,
            agency_id=agency_id,
            category=category,
            recipients=recipients,
            subject=subject,
            reason="kill_switch_category",
            attempted_at=attempted_at,
            metadata=safe_metadata,
        )

    if category != SYSTEM_CATEGORY:
        hour_start = attempted_at - timedelta(hours=1)
        day_start = _window_start_day(attempted_at)
        hourly_rows = _fetch_sent_rows_since(client, hour_start, agency_id)
        if len(hourly_rows) >= _int_env("SEND_CAP_PER_HOUR", 30):
            return _block(
                client=client,
                agency_id=agency_id,
                category=category,
                recipients=recipients,
                subject=subject,
                reason="hourly_cap",
                attempted_at=attempted_at,
                metadata=safe_metadata,
                alert_rows=hourly_rows,
                alert_window_start=_window_start_hour(attempted_at),
            )

        daily_rows = _fetch_sent_rows_since(client, day_start, agency_id)
        if len(daily_rows) >= _int_env("SEND_CAP_PER_DAY", 100):
            return _block(
                client=client,
                agency_id=agency_id,
                category=category,
                recipients=recipients,
                subject=subject,
                reason="daily_cap",
                attempted_at=attempted_at,
                metadata=safe_metadata,
                alert_rows=daily_rows,
                alert_window_start=day_start,
            )

    if not getattr(resend, "api_key", None):
        resend.api_key = os.environ.get("RESEND_API_KEY", "")

    payload: dict[str, Any] = {
        "from": from_address or DEFAULT_SEND_FROM,
        "to": recipients,
        "subject": subject,
        "html": html,
    }
    if attachments:
        payload["attachments"] = attachments

    try:
        resend.Emails.send(payload)
    except Exception as exc:
        log.warning("[send_governor] Resend failed for %s to %s: %s", category, recipients, exc)
        raise

    _insert_send_log(
        client=client,
        agency_id=agency_id,
        category=category,
        recipient=", ".join(recipients),
        subject=subject,
        outcome="sent",
        attempted_at=attempted_at,
        metadata=safe_metadata,
    )
    return "sent"
