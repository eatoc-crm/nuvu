"""Chase Engine — cadence, inbound classification, confirmations (Phases A + B + C)."""

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
    render_enquiries_answer_seller_chase,
    render_enquiries_raise_buyer_chase,
    render_exchange_target_chase,
    render_post_survey_followup,
    render_report_on_title_chase,
    render_seller_forms_chase,
    render_stage4_search_fee_chase,
    render_stage4_search_fee_flag,
    render_stage5_draft_contract_chase,
    render_stage5_draft_contract_flag,
    render_stage6_search_results_chase,
    render_stage6_search_results_flag,
    render_stage6_searches_ordered_chase,
    render_survey_chase,
)
from utils.needs_attention import parse_progression_timestamp as _parse_ts

chase_engine_bp = Blueprint("chase_engine", __name__)

# --- Keyword classification — first match wins (ordered; specific before broad) ---
_CLASSIFICATION_RULES: list[tuple[tuple[str, ...], str]] = [
    (
        ("forms returned", "sent the forms", "posted the forms", "completed the forms"),
        "protocol_forms_returned",
    ),
    (
        (
            "replies to enquiries",
            "enquiries answered",
            "responses sent",
            "responses to enquiries",
            "replied to enquiries",
        ),
        "enquiries_answered",
    ),
    (
        (
            "enquiries raised",
            "raised enquiries",
            "sent additional enquiries",
            "raised enquiries on",
        ),
        "enquiries_raised",
    ),
    (
        (
            "report on title",
            "report on title sent",
            "title report sent",
            "sent the report on title",
        ),
        "report_on_title",
    ),
    (
        (
            "searches received",
            "search results received",
            "searches complete",
            "searches now complete",
            "searches back",
        ),
        "searches_received",
    ),
    (
        ("instructed searches", "searches have been ordered", "searches ordered"),
        "searches_ordered",
    ),
    (
        (
            "search fees paid",
            "paid the search fees",
            "paid search fees",
            "transferred the search fees",
            "fees transferred",
        ),
        "search_fees_confirmed",
    ),
    (
        (
            "draft contract issued",
            "issued the draft contract",
            "sent the draft contract",
            "sent draft contract to buyer",
            "sent to buyer's solicitor",
            "sent to buyers solicitor",
        ),
        "draft_contract_issued",
    ),
    (
        ("survey booked", "surveyor booked", "survey arranged", "valuation booked"),
        "survey_instructed",
    ),
    (("draft contract", "contract pack"), "draft_contract_issued"),
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


# Human-readable labels for dashboard chase confirmation cards
CHASE_CONFIRMATION_LABELS: dict[str, str] = {
    "protocol_forms_returned": "Protocol forms returned",
    "survey_instructed": "Survey instructed",
    "searches_ordered": "Searches ordered",
    "searches_received": "Searches received",
    "search_fees_confirmed": "Search fees paid (buyer)",
    "draft_contract_sent": "Draft contract sent (legacy)",
    "draft_contract_issued": "Draft contract issued",
    "seller_forms_returned": "Seller forms returned",
    "enquiries_raised": "Enquiries raised",
    "enquiries_answered": "Enquiries answered",
    "report_on_title": "Report on title sent",
}


def _already_sent(
    client,
    property_id: str,
    chase_stage: str,
    chase_day: int,
    chain_link_id: str | None = None,
) -> bool:
    try:
        q = (
            client.table("chase_messages")
            .select("id")
            .eq("property_id", str(property_id))
            .eq("chase_stage", chase_stage)
            .eq("chase_day", chase_day)
            .not_.is_("sent_at", "null")
        )
        if chain_link_id:
            q = q.eq("chain_link_id", str(chain_link_id))
        else:
            q = q.is_("chain_link_id", "null")
        r = q.limit(1).execute()
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
            .select("*")
            .eq("property_address", addr)
            .limit(1)
            .execute()
        )
        rows = r.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def _add_working_days_mon_fri(start: date, n: int) -> date:
    """Add n Mon–Fri working days (UK chase brief: ~10 weeks = 50 working days)."""
    if n <= 0:
        return start
    d = start
    left = n
    while left > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            left -= 1
    return d


def _parse_progression_date(val: Any) -> date | None:
    """DATE or timestamptz column → date."""
    dt = _parse_ts_value(val)
    if not dt:
        return None
    try:
        return dt.date() if isinstance(dt, datetime) else dt
    except (TypeError, ValueError, AttributeError):
        return None


def _pipeline_or_prog_exchanged(pipe: dict[str, Any] | None, prog: dict[str, Any]) -> bool:
    pst = (pipe.get("status") or "") if pipe else ""
    if "exchanged" in pst.lower():
        return True
    st = (prog.get("status") or "").strip().lower()
    if st == "exchanged":
        return True
    if _parse_ts_value(prog.get("exchange_date")):
        return True
    return False


def _resolve_exchange_target_date(
    prog: dict[str, Any], pipe: dict[str, Any] | None
) -> date | None:
    """Phase C: manual date, or est_completion−14d, or offer_accepted+50 working days."""
    manual = _parse_progression_date(prog.get("exchange_target_date"))
    if manual:
        return manual

    est_raw = None
    if pipe:
        est_raw = pipe.get("est_completion") or pipe.get("completion_target")
    if not est_raw:
        est_raw = prog.get("est_completion") or prog.get("completion_date")
    est_d = _parse_progression_date(est_raw)
    if est_d:
        return est_d - timedelta(days=14)

    agreed = _parse_progression_date(prog.get("offer_accepted"))
    if not agreed:
        return None
    return _add_working_days_mon_fri(agreed, 50)


def _maybe_persist_exchange_target_date(
    client, pid: str, prog: dict[str, Any], pipe: dict[str, Any] | None
) -> date | None:
    """When progression.exchange_target_date is null, store computed default (DATE)."""
    if _parse_progression_date(prog.get("exchange_target_date")):
        return _parse_progression_date(prog.get("exchange_target_date"))
    computed = _resolve_exchange_target_date(prog, pipe)
    if not computed:
        return None
    try:
        client.table("sales_progression").update(
            {"exchange_target_date": computed.isoformat()}
        ).eq("id", pid).execute()
    except Exception as ex:
        print(f"[chase_engine] exchange_target_date persist failed: {ex}")
    return computed


def _solicitor_emails(
    pipe: dict[str, Any] | None,
) -> tuple[str | None, str | None]:
    if not pipe:
        return None, None
    be = (pipe.get("buyers_solicitor_email") or "").strip()
    se = (pipe.get("vendors_solicitor_email") or "").strip()
    if be and "@" not in be:
        be = ""
    if se and "@" not in se:
        se = ""
    return be or None, se or None


def _buyer_seller_sol_emails(
    prog: dict[str, Any], pipe: dict[str, Any] | None
) -> tuple[str | None, str | None]:
    """Prefer sales_progression solicitor emails; fall back to sales_pipeline."""
    be = (prog.get("buyer_solicitor_email") or "").strip()
    se = (prog.get("seller_solicitor_email") or "").strip()
    if be and "@" not in be:
        be = ""
    if se and "@" not in se:
        se = ""
    pe_be, pe_se = _solicitor_emails(pipe)
    return (be or pe_be), (se or pe_se)


def _solicitor_firm_label(pipe: dict[str, Any] | None, which: str) -> str:
    if not pipe:
        return ""
    raw = (
        pipe.get("buyers_solicitor")
        if which == "buyer"
        else pipe.get("vendors_solicitor")
    ) or ""
    line = raw.split(",")[0].strip()
    return line[:200] if line else ""


def _draft_contract_satisfied(prog: dict[str, Any]) -> bool:
    return bool(
        _parse_ts_value(prog.get("draft_contract_issued"))
        or _parse_ts_value(prog.get("draft_contract_sent"))
    )


def _fetch_la_turnaround_map(client) -> dict[str, int]:
    from utils.address import normalise_address

    out: dict[str, int] = {}
    try:
        r = (
            client.table("local_authority_search_times")
            .select("local_authority_name,avg_turnaround_days")
            .execute()
        )
        for row in r.data or []:
            nm = (row.get("local_authority_name") or "").strip()
            if not nm:
                continue
            k = normalise_address(nm)
            if not k:
                continue
            try:
                out[k] = max(1, int(row.get("avg_turnaround_days") or 15))
            except (TypeError, ValueError):
                out[k] = 15
    except Exception:
        pass
    dk = normalise_address("default")
    if dk and dk not in out:
        out[dk] = 15
    return out


def _lookup_search_turnaround_working_days(
    la_map: dict[str, int],
    prog: dict[str, Any],
    pipe: dict[str, Any] | None,
    property_address: str,
) -> int:
    from utils.address import normalise_address

    addr_n = normalise_address(property_address or "")
    la_raw = ""
    if pipe:
        la_raw = (pipe.get("local_authority") or "").strip()
    if not la_raw:
        la_raw = (prog.get("local_authority") or "").strip()
    la_key = normalise_address(la_raw)
    if la_key and la_key in la_map:
        return max(1, int(la_map[la_key]))
    for nk, days in la_map.items():
        if not nk or nk == normalise_address("default"):
            continue
        if nk in la_key or la_key in nk:
            return max(1, int(days))
        if addr_n and (nk in addr_n or addr_n in nk):
            return max(1, int(days))
    dk = normalise_address("default")
    return max(1, int(la_map.get(dk, 15)))


def _phase_b_try_immediate_after_confirm(
    client, pid: str, confirmed_ms: str
) -> None:
    """Fire Phase B Day-0 chases when a trigger milestone is confirmed or PATCHed."""
    if confirmed_ms not in {
        "protocol_forms_returned",
        "seller_forms_returned",
        "search_fees_confirmed",
    }:
        return
    try:
        r = (
            client.table("sales_progression")
            .select("*")
            .eq("id", pid)
            .limit(1)
            .execute()
        )
    except Exception as ex:
        print(f"[chase_engine] phase_b refetch progression failed: {ex}")
        return
    rows = r.data or []
    if not rows:
        return
    prog = rows[0]
    addr = (prog.get("property_address") or "").strip()
    pipe = _pipeline_row_for_address(client, addr)
    neg_name = (prog.get("staff_initials") or "").strip()
    if not neg_name and pipe:
        neg_name = (pipe.get("negotiator") or "").strip()
    buyer_sol_em, seller_sol_em = _buyer_seller_sol_emails(prog, pipe)
    buyer_email = (prog.get("buyer_email") or "").strip()
    buyer_name = (prog.get("buyer_name") or "").strip() or "there"
    ctx: dict[str, Any] = {
        "property_address": addr,
        "buyer_name": buyer_name,
        "negotiator_name": neg_name,
        "solicitor_firm": _solicitor_firm_label(pipe, "seller"),
    }

    if confirmed_ms == "protocol_forms_returned":
        if not _parse_ts_value(prog.get("protocol_forms_returned")):
            return
        if _parse_ts_value(prog.get("search_fees_confirmed")):
            return
        if not _already_sent(client, pid, "stage4_search_fees", 0):
            subj, html_b = render_stage4_search_fee_chase(0, ctx)
            send_chase_message(
                property_id=pid,
                chase_stage="stage4_search_fees",
                chase_day=0,
                recipient_type="buyer",
                recipient_email=buyer_email or None,
                subject=subj,
                html_body=html_b,
                dry_run_label="phase_b_s4_d0",
            )

    if confirmed_ms == "seller_forms_returned":
        if not _parse_ts_value(prog.get("seller_forms_returned")):
            return
        if _draft_contract_satisfied(prog):
            return
        ctx["solicitor_firm"] = _solicitor_firm_label(pipe, "seller")
        if not _already_sent(client, pid, "stage5_draft_contract", 0):
            subj, html_b = render_stage5_draft_contract_chase(0, ctx)
            send_chase_message(
                property_id=pid,
                chase_stage="stage5_draft_contract",
                chase_day=0,
                recipient_type="seller_solicitor",
                recipient_email=seller_sol_em,
                subject=subj,
                html_body=html_b,
                dry_run_label="phase_b_s5_d0",
            )

    if confirmed_ms == "search_fees_confirmed":
        if not _parse_ts_value(prog.get("search_fees_confirmed")):
            return
        if _parse_ts_value(prog.get("searches_ordered")):
            return
        ctx["solicitor_firm"] = _solicitor_firm_label(pipe, "buyer")
        if not _already_sent(client, pid, "stage6_order_searches", 0):
            subj, html_b = render_stage6_searches_ordered_chase(0, ctx)
            send_chase_message(
                property_id=pid,
                chase_stage="stage6_order_searches",
                chase_day=0,
                recipient_type="buyer_solicitor",
                recipient_email=buyer_sol_em,
                subject=subj,
                html_body=html_b,
                dry_run_label="phase_b_s6_d0",
            )


_PATCH_TRIGGERS_PHASE_C_IMMEDIATE: frozenset[str] = frozenset(
    {
        "searches_received",
        "survey_instructed",
        "enquiries_raised",
        "enquiries_answered",
    }
)


def on_sales_progression_patch(prog_id: str, updated_field_keys: list[str]) -> None:
    """Call from routes/progression after a successful PATCH (event-driven Phase B/C Day 0)."""
    client = supabase_for_backend()
    for k in updated_field_keys:
        _phase_b_try_immediate_after_confirm(client, prog_id, k)
    if _PATCH_TRIGGERS_PHASE_C_IMMEDIATE.intersection(updated_field_keys):
        try:
            _phase_c_try_immediate_after_confirm(client, prog_id, "")
        except Exception as ex:
            print(f"[chase_engine] phase_c immediate chases after PATCH: {ex}")


def _run_phase_b_cadence(
    client,
    pid: str,
    prog: dict[str, Any],
    pipe: dict[str, Any] | None,
    today: date,
    la_map: dict[str, int],
) -> None:
    """Phase B Stages 4–6: solicitor / buyer chases and flags."""
    addr = (prog.get("property_address") or "").strip()
    neg_name = (prog.get("staff_initials") or "").strip()
    if not neg_name and pipe:
        neg_name = (pipe.get("negotiator") or "").strip()
    buyer_email = (prog.get("buyer_email") or "").strip()
    buyer_name = (prog.get("buyer_name") or "").strip() or "there"
    buyer_sol_em, seller_sol_em = _buyer_seller_sol_emails(prog, pipe)
    ctx: dict[str, Any] = {
        "property_address": addr,
        "buyer_name": buyer_name,
        "negotiator_name": neg_name,
        "solicitor_firm": _solicitor_firm_label(pipe, "seller"),
    }
    team = _team_flag_email()

    pfr = _parse_ts_value(prog.get("protocol_forms_returned"))
    sfc = _parse_ts_value(prog.get("search_fees_confirmed"))
    if pfr and not sfc:
        try:
            ad = pfr.date() if isinstance(pfr, datetime) else pfr
            elapsed_pf = (today - ad).days
        except (TypeError, ValueError, AttributeError):
            elapsed_pf = None
        if elapsed_pf is not None:
            for day in (0, 1):
                if elapsed_pf < day:
                    continue
                if _already_sent(client, pid, "stage4_search_fees", day):
                    continue
                subj, html_b = render_stage4_search_fee_chase(day, ctx)
                send_chase_message(
                    property_id=pid,
                    chase_stage="stage4_search_fees",
                    chase_day=day,
                    recipient_type="buyer",
                    recipient_email=buyer_email or None,
                    subject=subj,
                    html_body=html_b,
                    dry_run_label=f"phase_b_s4_d{day}",
                )
            if elapsed_pf >= 3 and not _already_sent(client, pid, "stage4_search_fees", 3):
                subj, html_b, _ = render_stage4_search_fee_flag(ctx)
                send_chase_message(
                    property_id=pid,
                    chase_stage="stage4_search_fees",
                    chase_day=3,
                    recipient_type="negotiator",
                    recipient_email=team or None,
                    subject=subj,
                    html_body=html_b,
                    message_type="flag_to_team",
                    dry_run_label="phase_b_s4_flag",
                )

    sfr = _parse_ts_value(prog.get("seller_forms_returned"))
    if sfr and not _draft_contract_satisfied(prog):
        try:
            sd = sfr.date() if isinstance(sfr, datetime) else sfr
            elapsed_sf = (today - sd).days
        except (TypeError, ValueError, AttributeError):
            elapsed_sf = None
        if elapsed_sf is not None:
            ctx["solicitor_firm"] = _solicitor_firm_label(pipe, "seller")
            for day in (0, 1, 2, 3):
                if elapsed_sf < day:
                    continue
                if _already_sent(client, pid, "stage5_draft_contract", day):
                    continue
                subj, html_b = render_stage5_draft_contract_chase(day, ctx)
                send_chase_message(
                    property_id=pid,
                    chase_stage="stage5_draft_contract",
                    chase_day=day,
                    recipient_type="seller_solicitor",
                    recipient_email=seller_sol_em,
                    subject=subj,
                    html_body=html_b,
                    dry_run_label=f"phase_b_s5_d{day}",
                )
            if elapsed_sf >= 4 and not _already_sent(
                client, pid, "stage5_draft_contract", 4
            ):
                subj, html_b, _ = render_stage5_draft_contract_flag(ctx)
                send_chase_message(
                    property_id=pid,
                    chase_stage="stage5_draft_contract",
                    chase_day=4,
                    recipient_type="negotiator",
                    recipient_email=team or None,
                    subject=subj,
                    html_body=html_b,
                    message_type="flag_to_team",
                    dry_run_label="phase_b_s5_flag",
                )

    fees_c = _parse_ts_value(prog.get("search_fees_confirmed"))
    so = _parse_ts_value(prog.get("searches_ordered"))
    sr = _parse_ts_value(prog.get("searches_received"))
    if fees_c and not so:
        try:
            fd = fees_c.date() if isinstance(fees_c, datetime) else fees_c
            elapsed_f = (today - fd).days
        except (TypeError, ValueError, AttributeError):
            elapsed_f = None
        if elapsed_f is not None:
            ctx["solicitor_firm"] = _solicitor_firm_label(pipe, "buyer")
            for day in (0, 1):
                if elapsed_f < day:
                    continue
                if _already_sent(client, pid, "stage6_order_searches", day):
                    continue
                subj, html_b = render_stage6_searches_ordered_chase(day, ctx)
                send_chase_message(
                    property_id=pid,
                    chase_stage="stage6_order_searches",
                    chase_day=day,
                    recipient_type="buyer_solicitor",
                    recipient_email=buyer_sol_em,
                    subject=subj,
                    html_body=html_b,
                    dry_run_label=f"phase_b_s6_ord_{day}",
                )

    if so and not sr:
        wd = _lookup_search_turnaround_working_days(la_map, prog, pipe, addr)
        so_d = so.date() if isinstance(so, datetime) else so
        due = _add_working_days_mon_fri(so_d, wd)
        chase_date_iso = datetime(
            due.year, due.month, due.day, tzinfo=timezone.utc
        ).isoformat()
        ctx["solicitor_firm"] = _solicitor_firm_label(pipe, "buyer")
        if today >= due:
            if not _already_sent(client, pid, "stage6_search_results", 0):
                subj, html_b = render_stage6_search_results_chase(False, ctx, wd)
                send_chase_message(
                    property_id=pid,
                    chase_stage="stage6_search_results",
                    chase_day=0,
                    recipient_type="buyer_solicitor",
                    recipient_email=buyer_sol_em,
                    subject=subj,
                    html_body=html_b,
                    dry_run_label="phase_b_s6_res0",
                    chase_date=chase_date_iso,
                )
        if today >= due + timedelta(days=3):
            if _already_sent(client, pid, "stage6_search_results", 0) and not _already_sent(
                client, pid, "stage6_search_results", 3
            ):
                subj, html_b = render_stage6_search_results_chase(True, ctx, wd)
                send_chase_message(
                    property_id=pid,
                    chase_stage="stage6_search_results",
                    chase_day=3,
                    recipient_type="buyer_solicitor",
                    recipient_email=buyer_sol_em,
                    subject=subj,
                    html_body=html_b,
                    dry_run_label="phase_b_s6_res3",
                )
        if today >= due + timedelta(days=6):
            if not _already_sent(client, pid, "stage6_search_results", 6):
                subj, html_b, _ = render_stage6_search_results_flag(ctx)
                send_chase_message(
                    property_id=pid,
                    chase_stage="stage6_search_results",
                    chase_day=6,
                    recipient_type="negotiator",
                    recipient_email=team or None,
                    subject=subj,
                    html_body=html_b,
                    message_type="flag_to_team",
                    dry_run_label="phase_b_s6_flag",
                )


def _phase_c_try_immediate_after_confirm(
    client, pid: str, confirmed_milestone: str
) -> None:
    """After confirm or PATCH: Stage 7a (both searches_received + survey_instructed), 7b/8 on enquiries_raised, report on title Day 0 when enquiries_answered set."""
    try:
        r = (
            client.table("sales_progression")
            .select("*")
            .eq("id", pid)
            .limit(1)
            .execute()
        )
    except Exception as ex:
        print(f"[chase_engine] phase_c refetch progression failed: {ex}")
        return
    rows = r.data or []
    if not rows:
        return
    prog = rows[0]
    addr = (prog.get("property_address") or "").strip()
    pipe = _pipeline_row_for_address(client, addr)
    neg_name = (prog.get("staff_initials") or "").strip()
    if not neg_name and pipe:
        neg_name = (pipe.get("negotiator") or "").strip()
    buyer_em, seller_em = _solicitor_emails(pipe)
    base_ctx: dict[str, Any] = {
        "property_address": addr,
        "negotiator_name": neg_name,
    }

    sr = _parse_ts_value(prog.get("searches_received"))
    si = _parse_ts_value(prog.get("survey_instructed"))
    er = _parse_ts_value(prog.get("enquiries_raised"))

    if sr and si and not er:
        if not _already_sent(client, pid, "enquiries_raise_buyer", 0):
            subj, html_b = render_enquiries_raise_buyer_chase(0, base_ctx)
            send_chase_message(
                property_id=pid,
                chase_stage="enquiries_raise_buyer",
                chase_day=0,
                recipient_type="buyer_solicitor",
                recipient_email=buyer_em,
                subject=subj,
                html_body=html_b,
                dry_run_label="phase_c_7a_d0",
            )

    if er:
        if not _already_sent(client, pid, "enquiries_answer_seller", 0):
            subj, html_b = render_enquiries_answer_seller_chase(0, base_ctx)
            send_chase_message(
                property_id=pid,
                chase_stage="enquiries_answer_seller",
                chase_day=0,
                recipient_type="seller_solicitor",
                recipient_email=seller_em,
                subject=subj,
                html_body=html_b,
                dry_run_label="phase_c_7b_d0",
            )
        tgt = _maybe_persist_exchange_target_date(client, pid, prog, pipe)
        today_u = datetime.now(timezone.utc).date()
        if tgt and not _pipeline_or_prog_exchanged(pipe, prog):
            ctx_ex = {
                **base_ctx,
                "exchange_target_date": tgt,
                "days_until_exchange": max(0, (tgt - today_u).days),
            }
            for stage_suffix, em, label in (
                ("buyer", buyer_em, "phase_c_8_bs_d0"),
                ("seller", seller_em, "phase_c_8_ss_d0"),
            ):
                stg = f"exchange_target_{stage_suffix}"
                if not _already_sent(client, pid, stg, 0):
                    subj, html_b = render_exchange_target_chase("d0", ctx_ex)
                    send_chase_message(
                        property_id=pid,
                        chase_stage=stg,
                        chase_day=0,
                        recipient_type="buyer_solicitor"
                        if stage_suffix == "buyer"
                        else "seller_solicitor",
                        recipient_email=em,
                        subject=subj,
                        html_body=html_b,
                        dry_run_label=label,
                    )

    ea_done = _parse_ts_value(prog.get("enquiries_answered"))
    rt_done = _parse_ts_value(prog.get("report_on_title"))
    if ea_done and not rt_done:
        if not _already_sent(client, pid, "report_on_title", 0):
            subj, html_b = render_report_on_title_chase(0, base_ctx)
            send_chase_message(
                property_id=pid,
                chase_stage="report_on_title",
                chase_day=0,
                recipient_type="buyer_solicitor",
                recipient_email=buyer_em,
                subject=subj,
                html_body=html_b,
                dry_run_label="phase_c_report_d0",
            )


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
    chain_link_id: str | None = None,
    outbound_enabled: bool | None = None,
    chase_date: str | None = None,
) -> bool:
    """Log + send when enabled. Returns True if send succeeded or dry-run logged.

    outbound_enabled: when set, overrides CHASE_ENGINE_ENABLED (Track 6 uses CHAIN_CHASE_ENABLED).
    chain_link_id: optional FK for per–chain-link duplicate guard on chase_messages.
    """
    client = supabase_for_backend()
    rid = str(property_id).strip()
    if not rid:
        return False
    clid = (chain_link_id or "").strip() or None
    if _already_sent(client, rid, chase_stage, chase_day, chain_link_id=clid):
        return True

    preview = _strip_html(html_body)[:500]
    enabled = (
        chase_engine_sending_enabled()
        if outbound_enabled is None
        else bool(outbound_enabled)
    )

    if not enabled:
        print(
            f"[chase_engine] DRY-RUN {dry_run_label or chase_stage} day={chase_day} "
            f"property={rid} chain_link={clid or '-'} "
            f"to={recipient_email or '(no email)'} subject={subject[:80]!r}"
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
        send_result = send_html_email(em, subject, html_body, from_address=CHASE_SEND_FROM)
        if send_result != "sent":
            print(
                f"[chase_engine] send blocked {chase_stage} day={chase_day} "
                f"property={rid}: {send_result}"
            )
            return False
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
    row: dict[str, Any] = {
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
    if clid:
        row["chain_link_id"] = clid
    if chase_date:
        row["chase_date"] = chase_date
    try:
        client.table("chase_messages").insert(row).execute()
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
            .select("id,property_id,subject,body_preview,sender_email")
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
    try:
        from routes.chain_chase import (
            check_reinstate_keywords_on_note_text,
            handle_inbound_sender_for_chain_solicitor,
        )

        handle_inbound_sender_for_chain_solicitor(
            str(pid), row.get("sender_email")
        )
        check_reinstate_keywords_on_note_text(str(pid), blob)
    except Exception:
        pass

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
    """15-minute sweep: time-based chases for active properties (Phase A + Phase C)."""
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
    la_map = _fetch_la_turnaround_map(client)

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

        _run_phase_b_cadence(client, pid, prog, pipe, today, la_map)

        # --- Phase C: enquiries (7a/7b), report on title, exchange target (8) ---
        buyer_sol_em, seller_sol_em = _solicitor_emails(pipe)
        sol_ctx: dict[str, Any] = {
            "property_address": addr,
            "negotiator_name": neg_name,
        }

        sr_c = _parse_ts_value(prog.get("searches_received"))
        si_c = _parse_ts_value(prog.get("survey_instructed"))
        er_c = _parse_ts_value(prog.get("enquiries_raised"))
        ea_c = _parse_ts_value(prog.get("enquiries_answered"))
        rt_c = _parse_ts_value(prog.get("report_on_title"))

        if sr_c and si_c and not er_c:
            anchor_dt = max(sr_c, si_c)
            try:
                ad7 = anchor_dt.date() if isinstance(anchor_dt, datetime) else anchor_dt
                el_st7 = (today - ad7).days
            except (TypeError, ValueError, AttributeError):
                el_st7 = None
            if el_st7 is not None:
                for day in (0, 3, 7):
                    if el_st7 < day:
                        continue
                    if _already_sent(client, pid, "enquiries_raise_buyer", day):
                        continue
                    subj, html_b = render_enquiries_raise_buyer_chase(day, sol_ctx)
                    send_chase_message(
                        property_id=pid,
                        chase_stage="enquiries_raise_buyer",
                        chase_day=day,
                        recipient_type="buyer_solicitor",
                        recipient_email=buyer_sol_em,
                        subject=subj,
                        html_body=html_b,
                        dry_run_label=f"phase_c_7a_d{day}",
                    )
                if el_st7 >= 10 and not _already_sent(
                    client, pid, "enquiries_raise_buyer", 10
                ):
                    team = _team_flag_email()
                    subj, html_b, _ = render_day4_flag("enquiries_raise_buyer", sol_ctx)
                    send_chase_message(
                        property_id=pid,
                        chase_stage="enquiries_raise_buyer",
                        chase_day=10,
                        recipient_type="negotiator",
                        recipient_email=team or None,
                        subject=subj,
                        html_body=html_b,
                        message_type="flag_to_team",
                        dry_run_label="phase_c_7a_flag",
                    )

        if er_c and not ea_c:
            try:
                er_d = er_c.date() if isinstance(er_c, datetime) else er_c
                el_7b = (today - er_d).days
            except (TypeError, ValueError, AttributeError):
                el_7b = None
            if el_7b is not None:
                for day in (0, 7, 14):
                    if el_7b < day:
                        continue
                    if _already_sent(client, pid, "enquiries_answer_seller", day):
                        continue
                    subj, html_b = render_enquiries_answer_seller_chase(day, sol_ctx)
                    send_chase_message(
                        property_id=pid,
                        chase_stage="enquiries_answer_seller",
                        chase_day=day,
                        recipient_type="seller_solicitor",
                        recipient_email=seller_sol_em,
                        subject=subj,
                        html_body=html_b,
                        dry_run_label=f"phase_c_7b_d{day}",
                    )
                if el_7b >= 17 and not _already_sent(
                    client, pid, "enquiries_answer_seller", 17
                ):
                    team = _team_flag_email()
                    subj, html_b, _ = render_day4_flag(
                        "enquiries_answer_seller", sol_ctx
                    )
                    send_chase_message(
                        property_id=pid,
                        chase_stage="enquiries_answer_seller",
                        chase_day=17,
                        recipient_type="negotiator",
                        recipient_email=team or None,
                        subject=subj,
                        html_body=html_b,
                        message_type="flag_to_team",
                        dry_run_label="phase_c_7b_flag",
                    )

        if ea_c and not rt_c:
            try:
                ea_d = ea_c.date() if isinstance(ea_c, datetime) else ea_c
                el_rt = (today - ea_d).days
            except (TypeError, ValueError, AttributeError):
                el_rt = None
            if el_rt is not None:
                for day in (0, 5):
                    if el_rt < day:
                        continue
                    if _already_sent(client, pid, "report_on_title", day):
                        continue
                    subj, html_b = render_report_on_title_chase(day, sol_ctx)
                    send_chase_message(
                        property_id=pid,
                        chase_stage="report_on_title",
                        chase_day=day,
                        recipient_type="buyer_solicitor",
                        recipient_email=buyer_sol_em,
                        subject=subj,
                        html_body=html_b,
                        dry_run_label=f"phase_c_report_d{day}",
                    )
                if el_rt >= 8 and not _already_sent(client, pid, "report_on_title", 8):
                    team = _team_flag_email()
                    subj, html_b, _ = render_day4_flag("report_on_title", sol_ctx)
                    send_chase_message(
                        property_id=pid,
                        chase_stage="report_on_title",
                        chase_day=8,
                        recipient_type="negotiator",
                        recipient_email=team or None,
                        subject=subj,
                        html_body=html_b,
                        message_type="flag_to_team",
                        dry_run_label="phase_c_report_flag",
                    )

        exchanged = _pipeline_or_prog_exchanged(pipe, prog)
        if er_c and not exchanged:
            tgt = _maybe_persist_exchange_target_date(client, pid, prog, pipe)
            if tgt and today <= tgt:
                try:
                    er_d2 = er_c.date() if isinstance(er_c, datetime) else er_c
                    el_er = (today - er_d2).days
                except (TypeError, ValueError, AttributeError):
                    el_er = None
                if el_er is not None:
                    n_to_t = (tgt - today).days
                    ctx_ex = {
                        **sol_ctx,
                        "exchange_target_date": tgt,
                        "days_until_exchange": max(0, n_to_t),
                    }
                    for d_send, variant in ((0, "d0"), (14, "d14"), (21, "d21")):
                        if el_er < d_send:
                            continue
                        for suffix, em, lab in (
                            ("buyer", buyer_sol_em, "bs"),
                            ("seller", seller_sol_em, "ss"),
                        ):
                            stg = f"exchange_target_{suffix}"
                            if _already_sent(client, pid, stg, d_send):
                                continue
                            subj, html_b = render_exchange_target_chase(variant, ctx_ex)
                            send_chase_message(
                                property_id=pid,
                                chase_stage=stg,
                                chase_day=d_send,
                                recipient_type="buyer_solicitor"
                                if suffix == "buyer"
                                else "seller_solicitor",
                                recipient_email=em,
                                subject=subj,
                                html_body=html_b,
                                dry_run_label=f"phase_c_8_{lab}_d{d_send}",
                            )
                    if (tgt - today).days == 7:
                        ctx_t7 = {
                            **sol_ctx,
                            "exchange_target_date": tgt,
                            "days_until_exchange": 7,
                        }
                        for suffix, em, lab in (
                            ("buyer", buyer_sol_em, "bs"),
                            ("seller", seller_sol_em, "ss"),
                        ):
                            stg = f"exchange_target_{suffix}"
                            if _already_sent(client, pid, stg, 7007):
                                continue
                            subj, html_b = render_exchange_target_chase("t7", ctx_t7)
                            send_chase_message(
                                property_id=pid,
                                chase_stage=stg,
                                chase_day=7007,
                                recipient_type="buyer_solicitor"
                                if suffix == "buyer"
                                else "seller_solicitor",
                                recipient_email=em,
                                subject=subj,
                                html_body=html_b,
                                dry_run_label=f"phase_c_8_{lab}_t7",
                            )
                    if today == tgt:
                        ctx_due = {
                            **sol_ctx,
                            "exchange_target_date": tgt,
                            "days_until_exchange": 0,
                        }
                        for suffix, em, lab in (
                            ("buyer", buyer_sol_em, "bs"),
                            ("seller", seller_sol_em, "ss"),
                        ):
                            stg = f"exchange_target_{suffix}"
                            if _already_sent(client, pid, stg, 9000):
                                continue
                            subj, html_b = render_exchange_target_chase("due", ctx_due)
                            send_chase_message(
                                property_id=pid,
                                chase_stage=stg,
                                chase_day=9000,
                                recipient_type="buyer_solicitor"
                                if suffix == "buyer"
                                else "seller_solicitor",
                                recipient_email=em,
                                subject=subj,
                                html_body=html_b,
                                dry_run_label=f"phase_c_8_{lab}_due",
                            )


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
    labels = CHASE_CONFIRMATION_LABELS
    for row in rows:
        pid = str(row.get("property_id") or "")
        row["property_address"] = addr_by.get(pid, "")
        ms = (row.get("suggested_milestone") or "").strip()
        row["suggested_milestone_label"] = labels.get(ms, ms.replace("_", " ").title())
    return rows


_ALLOWED_CONFIRM_MILESTONES = frozenset(
    {
        "protocol_forms_returned",
        "survey_instructed",
        "searches_ordered",
        "searches_received",
        "search_fees_confirmed",
        "draft_contract_sent",
        "draft_contract_issued",
        "seller_forms_returned",
        "enquiries_raised",
        "enquiries_answered",
        "report_on_title",
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

    try:
        from routes.chain_chase import notify_confirmed_chain_solicitors_milestone

        notify_confirmed_chain_solicitors_milestone(pid, ms)
    except Exception as ex:
        print(f"[chase_engine] chain inform after confirm failed: {ex}")

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

    try:
        _phase_c_try_immediate_after_confirm(client, pid, ms)
    except Exception as ex:
        print(f"[chase_engine] phase_c immediate chases after confirm: {ex}")

    try:
        _phase_b_try_immediate_after_confirm(client, pid, ms)
    except Exception as ex:
        print(f"[chase_engine] phase_b immediate chases after confirm: {ex}")

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
