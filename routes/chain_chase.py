"""Track 6 — chain solicitor outreach, cadence, reinstatement, inform/request (Session 19 brief)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

from flask import Blueprint

from db_supabase import supabase_for_backend
from shared import chain_chase_sending_enabled
from routes.chase_engine import send_chase_message
from utils.chase_templates import (
    chain_solicitor_flag_note_text,
    chain_solicitor_reinstate_prompt_text,
    render_chain_solicitor_lead_in,
    render_chain_solicitor_milestone_update,
    render_chain_solicitor_nudge_1,
    render_chain_solicitor_nudge_2,
    render_chain_solicitor_progress_request,
)
from utils.needs_attention import parse_progression_timestamp as _parse_ts

chain_chase_bp = Blueprint("chain_chase", __name__)

_INFORM_DAY_BY_MILESTONE: dict[str, int] = {
    "protocol_forms_returned": 11,
    "seller_forms_returned": 12,
    "survey_instructed": 13,
    "searches_ordered": 14,
    "searches_received": 15,
    "draft_contract_sent": 16,
    "enquiries_raised": 17,
    "enquiries_answered": 18,
    "mortgage_offered": 19,
    "exchange_date": 20,
    "completion_date": 21,
}

_MILESTONE_LABELS: dict[str, str] = {
    "protocol_forms_returned": "Protocol forms returned",
    "seller_forms_returned": "Seller property information forms returned",
    "survey_instructed": "Survey instructed",
    "searches_ordered": "Searches ordered",
    "searches_received": "Searches received",
    "draft_contract_sent": "Draft contract sent",
    "enquiries_raised": "Enquiries raised",
    "enquiries_answered": "Replies to enquiries received",
    "mortgage_offered": "Mortgage offer progress",
    "exchange_date": "Exchange date agreed",
    "completion_date": "Completion date locked",
}


def chain_inform_milestone_field(key: str) -> bool:
    """True if updating this sales_progression column should email confirmed chain solicitors."""
    return key in _INFORM_DAY_BY_MILESTONE


def _norm_email(s: str | None) -> str:
    return (s or "").strip().lower()


def _email_from_free_text(text: str | None) -> str:
    if not text:
        return ""
    m = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", str(text))
    return m.group(0).strip() if m else ""


def _recipient_email_for_link(cl: dict[str, Any]) -> str:
    em = _norm_email(cl.get("solicitor_email"))
    if em and "@" in em:
        return em
    return _email_from_free_text(cl.get("buyer_solicitor")) or _email_from_free_text(
        cl.get("seller_solicitor")
    )


def _firm_label(cl: dict[str, Any]) -> str:
    for k in ("solicitor_firm", "estate_agent", "link_address"):
        v = (cl.get(k) or "").strip()
        if v:
            return v
    return "Chain solicitor"


def _salutation_from_firm(firm: str) -> str:
    f = (firm or "").strip()
    return f if f else "Sir/Madam"


def _append_nuvu_notes(client, prog_id: str, paragraph: str) -> None:
    para = (paragraph or "").strip()
    if not para:
        return
    try:
        r = (
            client.table("sales_progression")
            .select("nuvu_notes")
            .eq("id", prog_id)
            .limit(1)
            .execute()
        )
    except Exception as ex:
        print(f"[chain_chase] read nuvu_notes failed: {ex}")
        return
    rows = r.data or []
    prev = (rows[0].get("nuvu_notes") or "").strip() if rows else ""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    block = f"[{stamp}] {para}"
    merged = f"{prev}\n\n{block}".strip() if prev else block
    try:
        client.table("sales_progression").update({"nuvu_notes": merged}).eq(
            "id", prog_id
        ).execute()
    except Exception as ex:
        print(f"[chain_chase] append nuvu_notes failed: {ex}")


def _load_progression_row(client, prog_id: str) -> dict[str, Any] | None:
    try:
        r = (
            client.table("sales_progression")
            .select("*")
            .eq("id", prog_id)
            .limit(1)
            .execute()
        )
        rows = r.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def _pipeline_negotiator(client, property_address: str) -> str:
    addr = (property_address or "").strip()
    if not addr:
        return ""
    try:
        r = (
            client.table("sales_pipeline")
            .select("negotiator")
            .eq("property_address", addr)
            .limit(1)
            .execute()
        )
        rows = r.data or []
        if rows:
            return (rows[0].get("negotiator") or "").strip()
    except Exception:
        pass
    return ""


def _completion_phrase_from_prog(prog: dict[str, Any]) -> str:
    oa = _parse_ts(prog.get("offer_accepted"))
    if oa:
        try:
            d = oa.date() if isinstance(oa, datetime) else oa
            target = d + timedelta(days=77)
            return f"{target.day} {target.strftime('%B %Y')}"
        except (TypeError, ValueError, AttributeError):
            pass
    return "10–12 weeks from agreement"


def _milestone_date_display(prog: dict[str, Any], key: str) -> str:
    ts = _parse_ts(prog.get(key))
    if not ts:
        return ""
    try:
        d = ts.date() if isinstance(ts, datetime) else ts
        return f"{d.day} {d.strftime('%B %Y')}"
    except (TypeError, ValueError, AttributeError):
        return ""


def try_process_chain_link_outreach_for_row(
    client, chain_row: dict[str, Any], *, reason: str = ""
) -> None:
    """Phase 1 when a chain_links row has a solicitor email and no intro yet."""
    lid = str(chain_row.get("id") or "")
    pid = str(chain_row.get("property_id") or "")
    if not lid or not pid:
        return

    to_em = _recipient_email_for_link(chain_row)
    if not to_em or "@" not in to_em:
        return

    intro_at = _parse_ts(chain_row.get("chain_solicitor_intro_sent_at"))
    if intro_at:
        return

    st = (chain_row.get("solicitor_status") or "not_set").strip().lower()
    if st == "confirmed":
        return

    prog = _load_progression_row(client, pid)
    if not prog:
        return
    pst = (prog.get("status") or "").strip().lower()
    if pst in (
        "completed",
        "for sale",
        "withdrawn",
        "fallen through",
        "exchanged",
    ):
        return

    addr = (prog.get("property_address") or "").strip()
    neg = (prog.get("staff_initials") or "").strip() or _pipeline_negotiator(
        client, addr
    )
    ctx = {"property_address": addr, "negotiator_name": neg}
    subj, html_b = render_chain_solicitor_lead_in(ctx)

    sent_ok = send_chase_message(
        property_id=pid,
        chase_stage="chain_solicitor_outreach",
        chase_day=0,
        recipient_type="chain_solicitor",
        recipient_email=to_em,
        subject=subj,
        html_body=html_b,
        dry_run_label="chain_solicitor_phase1",
        chain_link_id=lid,
        outbound_enabled=chain_chase_sending_enabled(),
    )

    if not chain_chase_sending_enabled():
        print(
            f"[chain_chase] Phase 1 dry-run (no DB progression) link={lid} property={pid} "
            f"reason={reason or 'cadence'}"
        )
        return

    if not sent_ok:
        return

    now = datetime.now(timezone.utc).isoformat()
    try:
        client.table("chain_links").update(
            {
                "solicitor_status": "contacted",
                "chain_solicitor_first_email_at": now,
                "chain_solicitor_intro_sent_at": now,
                "solicitor_email": to_em,
            }
        ).eq("id", lid).execute()
    except Exception as ex:
        print(f"[chain_chase] chain_links update after Phase1 failed: {ex}")


def run_chain_cadence_check() -> None:
    """Nudges, Day 9 flag, 48h reinstate prompt, Week 4/8 request emails."""
    client = supabase_for_backend()
    today = datetime.now(timezone.utc).date()
    now = datetime.now(timezone.utc)

    try:
        res = (
            client.table("chain_links")
            .select("*")
            .limit(500)
            .execute()
        )
    except Exception as e:
        print(f"[chain_chase] fetch chain_links failed: {e}")
        return

    for cl in res.data or []:
        lid = str(cl.get("id") or "")
        pid = str(cl.get("property_id") or "")
        if not lid or not pid:
            continue

        to_em = _recipient_email_for_link(cl)
        if to_em and "@" in to_em and not _parse_ts(cl.get("chain_solicitor_intro_sent_at")):
            try_process_chain_link_outreach_for_row(client, cl, reason="cadence_pickup")

        intro = _parse_ts(cl.get("chain_solicitor_intro_sent_at"))
        if not intro:
            continue

        prog = _load_progression_row(client, pid)
        if not prog:
            continue
        pst = (prog.get("status") or "").strip().lower()
        if pst in (
            "completed",
            "for sale",
            "withdrawn",
            "fallen through",
            "exchanged",
        ):
            continue

        st = (cl.get("solicitor_status") or "not_set").strip().lower()
        if st == "confirmed":
            _maybe_send_progress_request(client, cl, prog, today)
            continue

        if st == "unresponsive":
            _maybe_reinstate_prompt(client, cl, prog, now)
            continue

        if st not in ("contacted", "not_set"):
            continue

        if _parse_ts(cl.get("solicitor_acting_confirmed_at")) or _parse_ts(
            cl.get("last_chain_solicitor_reply_at")
        ):
            continue

        try:
            intro_d = intro.date() if isinstance(intro, datetime) else intro
            elapsed = (today - intro_d).days
        except (TypeError, ValueError, AttributeError):
            continue

        addr = (prog.get("property_address") or "").strip()
        neg = (prog.get("staff_initials") or "").strip() or _pipeline_negotiator(
            client, addr
        )
        ctx = {"property_address": addr, "negotiator_name": neg}

        if elapsed >= 3:
            subj, html_b = render_chain_solicitor_nudge_1(ctx)
            send_chase_message(
                property_id=pid,
                chase_stage="chain_solicitor_nudge1",
                chase_day=3,
                recipient_type="chain_solicitor",
                recipient_email=to_em,
                subject=subj,
                html_body=html_b,
                dry_run_label="chain_nudge1",
                chain_link_id=lid,
                outbound_enabled=chain_chase_sending_enabled(),
            )

        if elapsed >= 6:
            subj, html_b = render_chain_solicitor_nudge_2(ctx)
            send_chase_message(
                property_id=pid,
                chase_stage="chain_solicitor_nudge2",
                chase_day=6,
                recipient_type="chain_solicitor",
                recipient_email=to_em,
                subject=subj,
                html_body=html_b,
                dry_run_label="chain_nudge2",
                chain_link_id=lid,
                outbound_enabled=chain_chase_sending_enabled(),
            )

        if elapsed >= 9 and st != "unresponsive":
            firm = _firm_label(cl)
            email_disp = to_em or "unknown email"
            _append_nuvu_notes(client, pid, chain_solicitor_flag_note_text(firm, email_disp))
            try:
                client.table("chain_links").update(
                    {
                        "solicitor_status": "unresponsive",
                        "chain_solicitor_unresponsive_at": now.isoformat(),
                    }
                ).eq("id", lid).execute()
            except Exception as ex:
                print(f"[chain_chase] Day-9 flag update failed: {ex}")


def _maybe_reinstate_prompt(
    client, cl: dict[str, Any], prog: dict[str, Any], now: datetime
) -> None:
    if _parse_ts(cl.get("chain_solicitor_reinstate_prompt_at")):
        return
    flagged = _parse_ts(cl.get("chain_solicitor_unresponsive_at"))
    if not flagged:
        return
    try:
        if isinstance(flagged, datetime):
            fd = flagged if flagged.tzinfo else flagged.replace(tzinfo=timezone.utc)
            fd = fd.astimezone(timezone.utc)
        else:
            fd = datetime.combine(flagged, datetime.min.time(), tzinfo=timezone.utc)
        if now - fd < timedelta(hours=48):
            return
    except (TypeError, ValueError, AttributeError):
        return

    pid = str(cl.get("property_id") or "")
    firm = _firm_label(cl)
    _append_nuvu_notes(client, pid, chain_solicitor_reinstate_prompt_text(firm))
    try:
        client.table("chain_links").update(
            {"chain_solicitor_reinstate_prompt_at": now.isoformat()}
        ).eq("id", str(cl.get("id"))).execute()
    except Exception as ex:
        print(f"[chain_chase] reinstate prompt stamp failed: {ex}")


def _maybe_send_progress_request(
    client, cl: dict[str, Any], prog: dict[str, Any], today: date
) -> None:
    oa = _parse_ts(prog.get("offer_accepted"))
    if not oa:
        return
    try:
        od = oa.date() if isinstance(oa, datetime) else oa
        weeks = max(0, (today - od).days // 7)
    except (TypeError, ValueError, AttributeError):
        return

    lid = str(cl.get("id") or "")
    pid = str(cl.get("property_id") or "")
    to_em = _recipient_email_for_link(cl)
    if not to_em:
        return

    addr = (prog.get("property_address") or "").strip()
    firm = _firm_label(cl)
    sal = _salutation_from_firm(firm)
    neg = (prog.get("staff_initials") or "").strip() or _pipeline_negotiator(
        client, addr
    )
    target = _completion_phrase_from_prog(prog)
    ctx = {
        "property_address": addr,
        "negotiator_name": neg,
        "firm_salutation": sal,
        "weeks_in": 4,
        "target_completion_phrase": target,
    }

    if weeks >= 4:
        ctx["weeks_in"] = 4
        subj, html_b = render_chain_solicitor_progress_request(ctx)
        send_chase_message(
            property_id=pid,
            chase_stage="chain_solicitor_request",
            chase_day=4,
            recipient_type="chain_solicitor",
            recipient_email=to_em,
            subject=subj,
            html_body=html_b,
            dry_run_label="chain_req_w4",
            chain_link_id=lid,
            outbound_enabled=chain_chase_sending_enabled(),
        )

    if weeks >= 8:
        ctx["weeks_in"] = 8
        subj, html_b = render_chain_solicitor_progress_request(ctx)
        send_chase_message(
            property_id=pid,
            chase_stage="chain_solicitor_request",
            chase_day=8,
            recipient_type="chain_solicitor",
            recipient_email=to_em,
            subject=subj,
            html_body=html_b,
            dry_run_label="chain_req_w8",
            chain_link_id=lid,
            outbound_enabled=chain_chase_sending_enabled(),
        )


def check_reinstate_keywords_on_note_text(property_id: str, note_text: str) -> None:
    """Ch3 feed or any note body: detect reinstate / no contact for unresponsive links."""
    pid = (property_id or "").strip()
    blob = (note_text or "").lower()
    if not pid or not blob:
        return

    has_reinstate = "reinstate" in blob
    has_no_contact = "no contact" in blob.replace("_", " ")
    if not has_reinstate and not has_no_contact:
        return

    client = supabase_for_backend()
    try:
        r = (
            client.table("chain_links")
            .select("*")
            .eq("property_id", pid)
            .execute()
        )
    except Exception as ex:
        print(f"[chain_chase] reinstate fetch links failed: {ex}")
        return

    links = [
        x
        for x in (r.data or [])
        if (x.get("solicitor_status") or "").lower() == "unresponsive"
    ]
    if not links:
        return

    now = datetime.now(timezone.utc)
    date_disp = f"{now.day} {now.strftime('%B %Y')}"

    if has_reinstate:
        for cl in links:
            lid = str(cl.get("id") or "")
            if not lid:
                continue
            try:
                client.table("chain_links").update(
                    {
                        "solicitor_status": "contacted",
                        "chain_solicitor_unresponsive_at": None,
                        "chain_solicitor_reinstate_prompt_at": None,
                        "chain_solicitor_intro_sent_at": None,
                        "chain_solicitor_first_email_at": None,
                    }
                ).eq("id", lid).execute()
            except Exception as ex:
                print(f"[chain_chase] reinstate clear failed: {ex}")
                continue
            try:
                r2 = (
                    client.table("chain_links")
                    .select("*")
                    .eq("id", lid)
                    .limit(1)
                    .execute()
                )
                row = (r2.data or [None])[0]
                if row:
                    try_process_chain_link_outreach_for_row(
                        client, row, reason="reinstate_keyword"
                    )
            except Exception as ex:
                print(f"[chain_chase] reinstate resend lookup failed: {ex}")

        _append_nuvu_notes(
            client,
            pid,
            f"Email sequence reinstated {date_disp} following negotiator instruction.",
        )
        return

    if has_no_contact:
        for cl in links:
            firm = _firm_label(cl)
            _append_nuvu_notes(
                client,
                pid,
                f"Negotiator unable to reach {firm} by phone. Chain solicitor remains unresponsive.",
            )


def handle_inbound_sender_for_chain_solicitor(
    property_id: str | None, sender_email: str | None
) -> None:
    """Mark chain solicitor confirmed when inbound email matches a link solicitor email."""
    pid = (property_id or "").strip()
    se = _norm_email(sender_email)
    if not pid or not se or "@" not in se:
        return

    client = supabase_for_backend()
    try:
        r = (
            client.table("chain_links")
            .select("*")
            .eq("property_id", pid)
            .execute()
        )
    except Exception as ex:
        print(f"[chain_chase] inbound chain lookup failed: {ex}")
        return

    now = datetime.now(timezone.utc).isoformat()
    for cl in r.data or []:
        cand = _norm_email(_recipient_email_for_link(cl))
        if not cand or cand != se:
            continue
        if not _parse_ts(cl.get("chain_solicitor_intro_sent_at")):
            continue
        lid = str(cl.get("id"))
        try:
            client.table("chain_links").update(
                {
                    "solicitor_status": "confirmed",
                    "solicitor_acting_confirmed_at": now,
                    "last_chain_solicitor_reply_at": now,
                }
            ).eq("id", lid).execute()
        except Exception as ex:
            print(f"[chain_chase] confirm chain solicitor failed: {ex}")


def notify_confirmed_chain_solicitors_milestone(
    property_id: str, milestone_key: str, prog: dict[str, Any] | None = None,
) -> None:
    """Inform email to each confirmed chain solicitor when a subject milestone completes."""
    if milestone_key not in _INFORM_DAY_BY_MILESTONE:
        return
    pid = (property_id or "").strip()
    if not pid:
        return

    client = supabase_for_backend()
    prog = prog or _load_progression_row(client, pid)
    if not prog:
        return

    try:
        r = (
            client.table("chain_links")
            .select("*")
            .eq("property_id", pid)
            .execute()
        )
    except Exception as ex:
        print(f"[chain_chase] inform fetch links failed: {ex}")
        return

    day_code = _INFORM_DAY_BY_MILESTONE[milestone_key]
    label = _MILESTONE_LABELS.get(milestone_key, milestone_key.replace("_", " ").title())
    addr = (prog.get("property_address") or "").strip()
    neg = (prog.get("staff_initials") or "").strip() or _pipeline_negotiator(
        client, addr
    )
    target = _completion_phrase_from_prog(prog)
    date_disp = _milestone_date_display(prog, milestone_key)

    for cl in r.data or []:
        if (cl.get("solicitor_status") or "").lower() != "confirmed":
            continue
        to_em = _recipient_email_for_link(cl)
        if not to_em:
            continue
        lid = str(cl.get("id") or "")
        firm = _firm_label(cl)
        sal = _salutation_from_firm(firm)
        ctx = {
            "property_address": addr,
            "negotiator_name": neg,
            "firm_salutation": sal,
            "milestone_label": label,
            "milestone_date_display": date_disp,
            "target_completion_phrase": target,
        }
        subj, html_b = render_chain_solicitor_milestone_update(ctx)
        send_chase_message(
            property_id=pid,
            chase_stage="chain_solicitor_inform",
            chase_day=day_code,
            recipient_type="chain_solicitor",
            recipient_email=to_em,
            subject=subj,
            html_body=html_b,
            dry_run_label=f"chain_inform_{milestone_key}",
            chain_link_id=lid,
            outbound_enabled=chain_chase_sending_enabled(),
        )
        if chain_chase_sending_enabled():
            try:
                client.table("chain_links").update(
                    {"last_chain_inform_sent_at": datetime.now(timezone.utc).isoformat()}
                ).eq("id", lid).execute()
            except Exception:
                pass


def fetch_property_ids_chain_solicitor_unresponsive() -> dict[str, list[dict[str, Any]]]:
    """property_id (sales_progression) -> list of {firm, chain_link_id} for Needs Attention."""
    client = supabase_for_backend()
    try:
        r = (
            client.table("chain_links")
            .select("id,property_id,link_address,estate_agent,solicitor_firm,solicitor_email")
            .eq("solicitor_status", "unresponsive")
            .limit(500)
            .execute()
        )
    except Exception:
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for row in r.data or []:
        pid = str(row.get("property_id") or "")
        if not pid:
            continue
        firm = _firm_label(row)
        out.setdefault(pid, []).append(
            {"firm": firm, "chain_link_id": str(row.get("id") or "")}
        )
    return out
