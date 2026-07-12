"""Durable send-once guard for outbound notifications."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable

log = logging.getLogger(__name__)


def _agency_id() -> str:
    return os.environ.get("NUVU_AGENCY_ID", "dbe").strip() or "dbe"


def _client():
    from db_supabase import supabase_for_backend

    return supabase_for_backend()


def _canonical_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, sort_keys=True, separators=(",", ":"), default=str)


def _content_hash(content: Any) -> str:
    return hashlib.sha256(_canonical_content(content).encode("utf-8")).hexdigest()


def _is_unique_violation(exc: Exception) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return (
        "23505" in text
        or "duplicate key" in text
        or "uniq_notification_hash_v2" in text
    )


def _notification_exists(
    property_address: str,
    notification_type: str,
    content: Any,
    *,
    agency_id: str | None = None,
    client=None,
) -> bool:
    client = client or _client()
    digest = _content_hash(content)
    result = (
        client.table("notification_log")
        .select("id")
        .eq("agency_id", agency_id or _agency_id())
        .eq("content_hash", digest)
        .limit(1)
        .execute()
    )
    return bool(result.data)


def _insert_notification_log(
    property_address: str,
    notification_type: str,
    content: Any,
    recipient: str,
    payload: dict[str, Any] | None = None,
    *,
    agency_id: str | None = None,
    client=None,
) -> None:
    client = client or _client()
    row = {
        "agency_id": agency_id or _agency_id(),
        "property_address": property_address,
        "notification_type": notification_type,
        "content_hash": _content_hash(content),
        "recipient": recipient,
        "payload": payload or {"content": content},
    }
    client.table("notification_log").insert(row).execute()


def _reserve_notification_log(
    property_address: str,
    notification_type: str,
    content: Any,
    recipient: str,
    *,
    agency_id: str,
    client=None,
) -> str | None:
    client = client or _client()
    digest = _content_hash(content)
    row = {
        "agency_id": agency_id,
        "property_address": property_address,
        "notification_type": notification_type,
        "content_hash": digest,
        "recipient": recipient,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "status": "reserved",
            "content": content,
            "content_hash": digest,
        },
    }
    result = client.table("notification_log").insert(row).execute()
    rows = result.data or []
    return str(rows[0].get("id")) if rows else None


def _update_notification_payload(
    row_id: str,
    payload: dict[str, Any],
    *,
    client=None,
) -> None:
    client = client or _client()
    client.table("notification_log").update({"payload": payload}).eq("id", row_id).execute()


def send_notification_once(
    property_address: str,
    notification_type: str,
    content: Any,
    recipient: str,
    send_fn: Callable[[], Any],
) -> str:
    """
    Sends via send_fn ONLY if this exact notification has not already been sent.

    Returns: 'sent' | 'duplicate_skipped' | 'error:<detail>'
    """
    agency_id = _agency_id()
    recipient = (recipient or "").strip()
    property_address = (property_address or "").strip()
    notification_type = (notification_type or "").strip()

    if not property_address or not notification_type or not recipient:
        return "error:missing_required_fields"

    try:
        client = _client()
        if _notification_exists(
            property_address,
            notification_type,
            content,
            agency_id=agency_id,
            client=client,
        ):
            return "duplicate_skipped"
    except Exception as exc:
        log.warning(
            "[notification_log] duplicate check failed for %s/%s: %s",
            property_address,
            notification_type,
            exc,
        )
        return f"error:check_failed:{exc}"

    try:
        row_id = _reserve_notification_log(
            property_address,
            notification_type,
            content,
            recipient,
            agency_id=agency_id,
            client=client,
        )
    except Exception as exc:
        if _is_unique_violation(exc):
            return "duplicate_skipped"
        log.warning(
            "[notification_log] reservation failed for %s/%s: %s",
            property_address,
            notification_type,
            exc,
        )
        return f"error:reserve_failed:{exc}"

    if not row_id:
        return "error:reserve_failed:no_row_id"

    try:
        send_result = send_fn()
    except Exception as exc:
        payload = {
            "status": "failed",
            "content": content,
            "content_hash": _content_hash(content),
            "error": str(exc),
        }
        try:
            _update_notification_payload(row_id, payload, client=client)
        except Exception as update_exc:
            log.error(
                "[notification_log] failed to mark reserved row %s failed: %s",
                row_id,
                update_exc,
            )
        log.warning(
            "[notification_log] send failed for %s/%s: %s",
            property_address,
            notification_type,
            exc,
        )
        return f"error:send_failed:{exc}"

    payload: dict[str, Any] = {
        "status": "sent",
        "content": content,
        "content_hash": _content_hash(content),
    }
    if send_result is not None:
        try:
            json.dumps(send_result, default=str)
            payload["send_result"] = send_result
        except TypeError:
            payload["send_result"] = str(send_result)

    try:
        _update_notification_payload(row_id, payload, client=client)
    except Exception as exc:
        log.error(
            "[notification_log] SENT BUT FAILED TO MARK SENT %s/%s to %s: %s",
            property_address,
            notification_type,
            recipient,
            exc,
        )
        return f"error:log_failed:{exc}"

    return "sent"
