"""Chase Engine Phase A — cadence, inbound classification, confirmations (spec + Phase A brief)."""

from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

from flask import Blueprint, jsonify, request, session

from db_supabase import supabase_for_backend
from db_portal import fetch_ta6_ta10_session_for_pipeline
from email_engine import send_html_email
from utils.chase_templates import (
    CHASE_SEND_FROM,
    format_surveyor_panel_ul,
    render_buyer_protocol_chase,
    render_day4_flag,
    render_post_survey_followup,
    render_seller_forms_chase,
    render_survey_chase,
)
from utils.needs_attention import parse_progression_timestamp as _parse_ts

chase_engine_bp = Blueprint("chase_engine", __name__)

# --- Keyword classification (Phase A brief §5.1) — first match wins (ordered) ---
_CLASSIFICATION_RULES: list[tuple[tuple[str, ...], str]] = [
    (
        ("forms returned", "sent the forms", "posted the forms", "completed the forms"),
        "protocol_forms_returned",
    ),
    (
        ("survey booked", "surveyor booked", "survey arranged", "valuation booked"),
        "survey_instructed",
    ),
    (("searches ordered", "search fees paid"), "searches_ordered"),
    (("draft contract", "contract pack"), "draft_contract_sent"),
]


def chase_engine_sending_enabled() -> bool:
    return os.environ.get("CHASE_ENGINE_ENABLED", "false").lower() == "true"


def _team_flag_email() -> str:
    raw = (os.environ.get("CHASE_TEAM_EMAIL") or "").strip()
    if raw:
        return raw
    allowed = os.environ.get("NUVU_ALLOWED_EMAILS", "")
    first = (allowed.split(",")[0] or "").strip()
    return first


def _public_base_url() -> str:
    return (
        os.environ.get("NUVU_BASE_URL", "").strip()
        or os.environ.get("AUTH_BASE_URL", "").strip()
        or "https://nuvu-production.up.railway.app"
    ).rstrip("/")


def _welcome_anchor(row: dict[str, Any]) -> datetime | None:
    return _parse_ts(row.get("welcome_emails_sent")) or _parse_ts(row.get("memo_sent"))


def _elapsed_days(anchor: datetime | None, today: date) -> int | None:
    if not anchor:
        return None
    try:
        ad = anchor.date() if isinstance(anchor, datetime) else anchor
        return (today - ad).days
    except (TypeError, ValueError, AttributeError):
        return None


def _parse_ts_value(val: Any) -> datetime | None:
    return _parse_ts(val)


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", " ", s or "")


def classify_inbound_text(text: str) -> str | None:
    blob = (text or "").lower()
    for phrases, milestone in _CLASSIFICATION_RULES:
        for p in phrases:
            if p in blob:
                return milestone
    return None


def _already_sent(
    client, property_id: str, chase_stage: str, chase_day: int
) -> bool:
    try:
        r = (
            client.table("chase_messages")
            .select("id")
            .eq("property_id", str(property_id))
            .eq("chase_stage", chase_stage)
            .eq("chase_day", chase_day)
            .not_.is_("sent_at", "null")
            .limit(1)
            .execute()
        )
        return bool(r.data)
    except Exception:
        return True


def _pipeline_row_for_address(client, address: str) -> dict[str, Any] | None:
    addr = (address or "").strip()
    if not addr:
        return None
    try:
        r = (
            client.table("sales_pipeline")
            .select("id,negotiator,buyer_type,mortgage_broker")
            .eq("property_address", addr)
            .limit(1)
            .execute()
        )
        rows = r.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def _buyer_survey_type(prog: dict, pipe: dict | None) -> str:
    """'cash' or 'mortgage' — default mortgage when unknown (Phase A brief §4.3)."""
    if not pipe:
        return "mortgage"
    bt = (pipe.get("buyer_type") or "").strip().lower()
    if bt in ("cash", "cash buyer", "cash_buyer"):
        return "cash"
    cb = pipe.get("cash_buyer")
    if cb is True:
        return "cash"
    if cb is False:
        return "mortgage"
    mb = (pipe.get("mortgage_broker") or "").strip()
    if mb and mb.lower() not in ("none", "n/a", "—", "-"):
        return "mortgage"
    return "mortgage"


def _portal_magic_link(pipeline_id: str | None) -> str:
    if not pipeline_id:
        return ""
    sess = fetch_ta6_ta10_session_for_pipeline(str(pipeline_id))
    if not sess:
        return ""
    tok = (sess.get("token") or "").strip()
    if not tok:
        return ""
    return f"{_public_base_url()}/portal/form/ta6_ta10?token={tok}"


def _fetch_preferred_surveyor_rows(client, limit: int = 5) -> list[dict[str, Any]]:
    try:
        r = (
            client.table("preferred_surveyors")
            .select(
                "surveyor_name,surveyor_firm,contact_email,contact_phone,google_rating"
            )
            .eq("agency_id", "dbe")
            .limit(limit)
            .execute()
        )
        return list(r.data or [])
    except Exception:
        return []


def send_chase_message(
    *,
    property_id: str,
    chase_stage: str,
    chase_day: int,
    recipient_type: str,
    recipient_email: str | None,
    subject: str,
    html_body: str,
    message_type: str = "chase",
    dry_run_label: str = "",
) -> bool:
    """Log + send when enabled. Returns True if send succeeded or dry-run logged."""
    client = supabase_for_backend()
    rid = str(property_id).strip()
    if not rid:
        return False
    if _already_sent(client, rid, chase_stage, chase_day):
        return True

    preview = _strip_html(html_body)[:500]
    enabled = chase_engine_sending_enabled()

    if not enabled:
        print(
            f"[chase_engine] DRY-RUN {dry_run_label or chase_stage} day={chase_day} "
            f"property={rid} to={recipient_email or '(no email)'} subject={subject[:80]!r}"
        )
        return True

    em = (recipient_email or "").strip()
    if not em or "@" not in em:
        print(
            f"[chase_engine] SKIP send (no recipient email) {chase_stage} "
            f"day={chase_day} property={rid}"
        )
        return False

    try:
        send_html_email(em, subject, html_body, from_address=CHASE_SEND_FROM)
    except Exception as e:
        print(f"[chase_engine] Resend FAILED {chase_stage} day={chase_day} property={rid}: {e}")
        team = _team_flag_email()
        if team and "@" in team:
            try:
                send_html_email(
                    team,
                    f"[NUVU] Chase send failed — {rid}",
                    f"<p>Stage {chase_stage} day {chase_day}</p><p>{str(e)[:500]}</p>",
                    from_address=CHASE_SEND_FROM,
                )
            except Exception as e2:
                print(f"[chase_engine] team flag email failed: {e2}")
        return False

    now = datetime.now(timezone.utc).isoformat()
    try:
        client.table("chase_messages").insert(
            {
                "property_id": rid,
                "chase_stage": chase_stage,
                "chase_day": chase_day,
                "recipient_type": recipient_type,
                "recipient_email": em,
                "message_type": message_type,
                "subject": subject[:500],
                "body_preview": preview,
                "sent_at": now,
            }
        ).execute()
    except Exception as e:
        print(f"[chase_engine] chase_messages insert after send failed: {e}")
        return False

    return True


def process_inbound_email(email_id: str | None) -> None:
    """After inbound_emails insert: classify and queue chase_confirmations (beta)."""
    eid = (email_id or "").strip()
    if not eid:
        return
    client = supabase_for_backend()
    try:
        r = (
            client.table("inbound_emails")
            .select("id,property_id,subject,body_preview")
            .eq("id", eid)
            .limit(1)
            .execute()
        )
    except Exception as ex:
        print(f"[chase_engine] process_inbound_email lookup failed: {ex}")
        return

    rows = r.data or []
    if not rows:
        return
    row = rows[0]
    pid = row.get("property_id")
    if not pid:
        return
    blob = f"{row.get('subject') or ''} {row.get('body_preview') or ''}"
    milestone = classify_inbound_text(blob)
    if not milestone:
        return

    try:
        dup = (
            client.table("chase_confirmations")
            .select("id")
            .eq("property_id", str(pid))
            .eq("suggested_milestone", milestone)
            .eq("status", "pending")
            .limit(1)
            .execute()
        )
        if dup.data:
            return
    except Exception:
        pass

    snippet = (row.get("body_preview") or row.get("subject") or "")[:500]
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        client.table("chase_confirmations").insert(
            {
                "property_id": str(pid),
                "inbound_email_id": str(row["id"]),
                "suggested_milestone": milestone,
                "suggested_value": now_iso,
                "email_snippet": snippet,
                "status": "pending",
            }
        ).execute()
        print(
            f"[chase_engine] chase_confirmation queued: property={pid} "
            f"milestone={milestone}"
        )
    except Exception as ex:
        print(f"[chase_engine] chase_confirmations insert failed: {ex}")


def run_cadence_check() -> None:
    """15-minute sweep: time-based chases for active properties (Phase A stages)."""
    client = supabase_for_backend()
    today = datetime.now(timezone.utc).date()
    try:
        res = (
            client.table("sales_progression")
            .select("*")
            .order("created_at", desc=True)
            .limit(500)
            .execute()
        )
    except Exception as e:
        print(f"[chase_engine] run_cadence_check fetch failed: {e}")
        return

    surveyors = _fetch_preferred_surveyor_rows(client)
    panel_html = format_surveyor_panel_ul(surveyors)

    for prog in res.data or []:
        st = (prog.get("status") or "").strip().lower()
        if st in (
            "completed",
            "for sale",
            "withdrawn",
            "fallen through",
            "exchanged",
        ):
            continue

        pid = str(prog.get("id") or "")
        if not pid:
            continue

        anchor = _welcome_anchor(prog)
        if not anchor:
            continue

        elapsed = _elapsed_days(anchor, today)
        if elapsed is None:
            continue

        addr = (prog.get("property_address") or "").strip()
        pipe = _pipeline_row_for_address(client, addr)
        pipeline_id = str(pipe.get("id")) if pipe and pipe.get("id") else None
        neg_name = (prog.get("staff_initials") or "").strip()
        if not neg_name and pipe:
            neg_name = (pipe.get("negotiator") or "").strip()

        buyer_name = (prog.get("buyer_name") or "").strip() or "there"
        seller_name = (prog.get("vendor_name") or "").strip() or "there"
        buyer_email = (prog.get("buyer_email") or "").strip()
        seller_email = (prog.get("vendor_email") or "").strip()
        survey_type = _buyer_survey_type(prog, pipe)

        base_ctx: dict[str, Any] = {
            "property_address": addr,
            "buyer_name": buyer_name,
            "seller_name": seller_name,
            "negotiator_name": neg_name,
            "portal_link": _portal_magic_link(pipeline_id),
            "surveyor_panel_html": panel_html,
        }

        # --- Stage 2a buyer protocol ---
        if not _parse_ts_value(prog.get("protocol_forms_returned")):
            for day in (1, 2, 3):
                if elapsed < day - 1:
                    continue
                if _already_sent(client, pid, "buyer_protocol_forms", day):
                    continue
                subj, html_b = render_buyer_protocol_chase(day, base_ctx)
                send_chase_message(
                    property_id=pid,
                    chase_stage="buyer_protocol_forms",
                    chase_day=day,
                    recipient_type="buyer",
                    recipient_email=buyer_email,
                    subject=subj,
                    html_body=html_b,
                    dry_run_label="buyer_protocol",
                )
            if elapsed >= 3 and not _already_sent(client, pid, "buyer_protocol_forms", 4):
                team = _team_flag_email()
                subj, html_b, _ = render_day4_flag("buyer_protocol_forms", base_ctx)
                send_chase_message(
                    property_id=pid,
                    chase_stage="buyer_protocol_forms",
                    chase_day=4,
                    recipient_type="negotiator",
                    recipient_email=team or None,
                    subject=subj,
                    html_body=html_b,
                    message_type="flag_to_team",
                    dry_run_label="buyer_protocol_flag",
                )

        # --- Stage 2b seller forms ---
        if not _parse_ts_value(prog.get("seller_forms_returned")):
            for day in (1, 2, 3):
                if elapsed < day - 1:
                    continue
                if _already_sent(client, pid, "seller_ta6_ta10", day):
                    continue
                subj, html_b = render_seller_forms_chase(day, base_ctx)
                send_chase_message(
                    property_id=pid,
                    chase_stage="seller_ta6_ta10",
                    chase_day=day,
                    recipient_type="seller",
                    recipient_email=seller_email,
                    subject=subj,
                    html_body=html_b,
                    dry_run_label="seller_forms",
                )
            if elapsed >= 3 and not _already_sent(client, pid, "seller_ta6_ta10", 4):
                team = _team_flag_email()
                subj, html_b, _ = render_day4_flag("seller_ta6_ta10", base_ctx)
                send_chase_message(
                    property_id=pid,
                    chase_stage="seller_ta6_ta10",
                    chase_day=4,
                    recipient_type="negotiator",
                    recipient_email=team or None,
                    subject=subj,
                    html_body=html_b,
                    message_type="flag_to_team",
                    dry_run_label="seller_forms_flag",
                )

        # --- Stage 3 survey ---
        if not _parse_ts_value(prog.get("survey_instructed")):
            for day in (1, 2, 3):
                if elapsed < day - 1:
                    continue
                if _already_sent(client, pid, "survey_instruction", day):
                    continue
                ctx = {**base_ctx}
                if day == 3 and not panel_html:
                    ctx["surveyor_panel_html"] = ""
                subj, html_b = render_survey_chase(day, survey_type, ctx)
                send_chase_message(
                    property_id=pid,
                    chase_stage="survey_instruction",
                    chase_day=day,
                    recipient_type="buyer",
                    recipient_email=buyer_email,
                    subject=subj,
                    html_body=html_b,
                    dry_run_label="survey",
                )
            if elapsed >= 3 and not _already_sent(client, pid, "survey_instruction", 4):
                team = _team_flag_email()
                subj, html_b, _ = render_day4_flag("survey_instruction", base_ctx)
                send_chase_message(
                    property_id=pid,
                    chase_stage="survey_instruction",
                    chase_day=4,
                    recipient_type="negotiator",
                    recipient_email=team or None,
                    subject=subj,
                    html_body=html_b,
                    message_type="flag_to_team",
                    dry_run_label="survey_flag",
                )

        # --- Post-survey follow-up (spec §3) ---
        si = _parse_ts_value(prog.get("survey_instructed"))
        if si and not _already_sent(client, pid, "post_survey_followup", 0):
            try:
                sd = si.date() if isinstance(si, datetime) else si
                if (today - sd).days >= 3:
                    subj, html_b = render_post_survey_followup(base_ctx)
                    send_chase_message(
                        property_id=pid,
                        chase_stage="post_survey_followup",
                        chase_day=0,
                        recipient_type="buyer",
                        recipient_email=buyer_email,
                        subject=subj,
                        html_body=html_b,
                        dry_run_label="post_survey",
                    )
            except (TypeError, ValueError, AttributeError):
                pass


def fetch_property_ids_solicitor_non_response() -> set[str]:
    """sales_progression ids with solicitor chase sent 24h+ ago and no reply."""
    client = supabase_for_backend()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    cutoff_iso = cutoff.isoformat()
    try:
        r = (
            client.table("chase_messages")
            .select("property_id")
            .eq("message_type", "chase")
            .eq("response_received", False)
            .in_("recipient_type", ["buyer_solicitor", "seller_solicitor"])
            .lt("sent_at", cutoff_iso)
            .not_.is_("sent_at", "null")
            .limit(2000)
            .execute()
        )
    except Exception:
        return set()
    out: set[str] = set()
    for row in r.data or []:
        pid = row.get("property_id")
        if pid:
            out.add(str(pid))
    return out


def fetch_pending_chase_confirmations(limit: int = 40) -> list[dict[str, Any]]:
    client = supabase_for_backend()
    try:
        r = (
            client.table("chase_confirmations")
            .select("*")
            .eq("status", "pending")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception:
        return []
    rows = list(r.data or [])
    if not rows:
        return []
    ids = list({str(x.get("property_id")) for x in rows if x.get("property_id")})
    addr_by: dict[str, str] = {}
    chunk = 40
    for i in range(0, len(ids), chunk):
        part = ids[i : i + chunk]
        try:
            pr = (
                client.table("sales_progression")
                .select("id,property_address")
                .in_("id", part)
                .execute()
            )
            for p in pr.data or []:
                addr_by[str(p["id"])] = (p.get("property_address") or "").strip()
        except Exception:
            continue
    for row in rows:
        pid = str(row.get("property_id") or "")
        row["property_address"] = addr_by.get(pid, "")
    return rows


_ALLOWED_CONFIRM_MILESTONES = frozenset(
    {
        "protocol_forms_returned",
        "survey_instructed",
        "searches_ordered",
        "draft_contract_sent",
        "seller_forms_returned",
    }
)


def confirm_milestone(confirmation_id: str, confirmed_by: str) -> tuple[bool, str]:
    cid = (confirmation_id or "").strip()
    if not cid:
        return False, "invalid id"
    client = supabase_for_backend()
    try:
        r = (
            client.table("chase_confirmations")
            .select("*")
            .eq("id", cid)
            .limit(1)
            .execute()
        )
    except Exception as e:
        return False, str(e)
    rows = r.data or []
    if not rows:
        return False, "not found"
    c = rows[0]
    if (c.get("status") or "").strip().lower() != "pending":
        return False, "not pending"
    ms = (c.get("suggested_milestone") or "").strip()
    if ms not in _ALLOWED_CONFIRM_MILESTONES:
        return False, "milestone not allowed"
    pid = str(c.get("property_id") or "")
    if not pid:
        return False, "missing property"

    val = c.get("suggested_value") or datetime.now(timezone.utc).isoformat()
    try:
        client.table("sales_progression").update({ms: val}).eq("id", pid).execute()
    except Exception as e:
        return False, f"progression update: {e}"

    now = datetime.now(timezone.utc).isoformat()
    actor = (confirmed_by or "").strip() or "staff"
    try:
        client.table("chase_confirmations").update(
            {
                "status": "confirmed",
                "confirmed_by": actor[:200],
                "actioned_at": now,
            }
        ).eq("id", cid).execute()
    except Exception as e:
        return False, f"confirmation update: {e}"

    return True, "ok"


def dismiss_milestone(confirmation_id: str, confirmed_by: str) -> tuple[bool, str]:
    cid = (confirmation_id or "").strip()
    if not cid:
        return False, "invalid id"
    client = supabase_for_backend()
    now = datetime.now(timezone.utc).isoformat()
    actor = (confirmed_by or "").strip() or "staff"
    try:
        r = (
            client.table("chase_confirmations")
            .update(
                {
                    "status": "dismissed",
                    "confirmed_by": actor[:200],
                    "actioned_at": now,
                }
            )
            .eq("id", cid)
            .eq("status", "pending")
            .execute()
        )
        if not r.data:
            return False, "not found or not pending"
    except Exception as e:
        return False, str(e)
    return True, "ok"


@chase_engine_bp.route("/api/chase/confirmations/<cid>/confirm", methods=["POST"])
def api_chase_confirm(cid):
    if not session.get("nuvu_email"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    who = (data.get("confirmed_by") or session.get("nuvu_email") or "")[:200]
    ok, msg = confirm_milestone(cid, who)
    if not ok:
        return jsonify({"error": msg}), 400
    return jsonify({"ok": True}), 200


@chase_engine_bp.route("/api/chase/confirmations/<cid>/dismiss", methods=["POST"])
def api_chase_dismiss(cid):
    if not session.get("nuvu_email"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    who = (data.get("confirmed_by") or session.get("nuvu_email") or "")[:200]
    ok, msg = dismiss_milestone(cid, who)
    if not ok:
        return jsonify({"error": msg}), 400
    return jsonify({"ok": True}), 200
