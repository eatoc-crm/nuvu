"""Durable send-once guard for outbound notifications."""

from __future__ import annotations

import hashlib
import json
import logging
import os
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
        .eq("property_address", property_address)
        .eq("notification_type", notification_type)
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
        send_result = send_fn()
    except Exception as exc:
        log.warning(
            "[notification_log] send failed for %s/%s: %s",
            property_address,
            notification_type,
            exc,
        )
        return f"error:send_failed:{exc}"

    payload: dict[str, Any] = {
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
        _insert_notification_log(
            property_address,
            notification_type,
            content,
            recipient,
            payload,
            agency_id=agency_id,
            client=client,
        )
    except Exception as exc:
        log.error(
            "[notification_log] SENT BUT FAILED TO LOG %s/%s to %s: %s",
            property_address,
            notification_type,
            recipient,
            exc,
        )
        return f"error:log_failed:{exc}"

    return "sent"
