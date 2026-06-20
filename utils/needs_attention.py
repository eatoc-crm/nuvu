"""Needs Attention trigger engine (NUVU Progression Engine spec)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import quote

from utils.working_days import add_working_days

# Default search turnaround when no local authority row matches (Phase B seed = 15).
DEFAULT_SEARCH_TURNAROUND_DAYS = 15


def parse_progression_timestamp(val: Any) -> datetime | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("null", "none"):
        return None
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            if "T" in s or s.count("-") >= 3 and len(s) > 10:
                s2 = s.replace("Z", "+00:00")
                dt = datetime.fromisoformat(s2)
                if dt.tzinfo is not None:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt
            d = datetime.strptime(s[:10], "%Y-%m-%d")
            return d
        except (ValueError, TypeError):
            pass
    try:
        return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
    except (ValueError, TypeError):
        return None


_parse_ts = parse_progression_timestamp


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _days_between(start: datetime | None, end: date) -> int | None:
    if not start:
        return None
    try:
        sd = start.date() if isinstance(start, datetime) else start
        return (end - sd).days
    except (TypeError, ValueError, AttributeError):
        return None


def _welcome_anchor(p: dict) -> datetime | None:
    """Spec uses welcome_emails_sent; NUVU overlay may only have memo_sent until column exists."""
    return _parse_ts(p.get("welcome_emails_sent")) or _parse_ts(p.get("memo_sent"))


def _la_threshold_days(p: dict, la_by_norm_name: dict[str, int]) -> int:
    raw = (p.get("local_authority") or "").strip()
    if not raw:
        return DEFAULT_SEARCH_TURNAROUND_DAYS
    from utils.address import normalise_address

    key = normalise_address(raw)
    if not key:
        return DEFAULT_SEARCH_TURNAROUND_DAYS
    # Keys in la_by_norm_name are normalised local_authority_name
    if key in la_by_norm_name:
        return max(1, int(la_by_norm_name[key]))
    # Partial: any LA key contained in property text or vice versa
    for nk, days in la_by_norm_name.items():
        if nk in key or key in nk:
            return max(1, int(days))
    return DEFAULT_SEARCH_TURNAROUND_DAYS


def _phone_uri(phone: str | None) -> str | None:
    if not phone or str(phone).strip() in ("\u2014", "-", "n/a"):
        return None
    digits = "".join(c for c in str(phone) if c.isdigit() or c == "+")
    if len(digits) < 8:
        return None
    return f"tel:{digits}"


def _build_quick_action(
    kind: str, label: str, p: dict
) -> dict[str, str]:
    href = "#"
    if kind == "call_buyer":
        href = _phone_uri(p.get("buyer_phone")) or "#"
    elif kind == "call_seller":
        href = _phone_uri(p.get("_vendor_phone")) or "#"
    elif kind == "email_buyer_sol":
        em = (p.get("_buyer_email") or "").strip()
        href = f"mailto:{em}" if em and "@" in em else "#"
    elif kind == "email_sol":
        subj = quote(f"{(p.get('address') or '').strip()} — progression")
        href = f"mailto:?subject={subj}"
    elif kind == "open_portal":
        href = "/portal/login"
    return {"label": label, "kind": kind, "href": href}


def _append_trigger(
    out: list[dict],
    *,
    trigger_id: str,
    trigger_name: str,
    days_overdue: int,
    severity: str,
    suggested_action: str,
    quick_action: dict[str, str],
) -> None:
    out.append(
        {
            "trigger_id": trigger_id,
            "trigger_name": trigger_name,
            "days_overdue": int(max(0, days_overdue)),
            "severity": severity,
            "suggested_action": suggested_action,
            "quick_action": quick_action,
        }
    )


def get_needs_attention(
    properties: list[dict],
    la_turnaround_by_norm_name: dict[str, int],
    *,
    surveyor_hint: str | None = None,
    today: date | None = None,
    solicitor_non_response_ids: set[str] | None = None,
    chain_unresponsive_by_progression_id: dict[str, list[dict[str, Any]]]
    | None = None,
) -> list[dict]:
    """
    Each input property dict must include merged sales_progression milestone fields
    plus chain_status, local_authority, buyer/seller phones as on the dashboard model.

    Returns list of { 'property': p, 'triggers': [...] } for properties with >=1 trigger.
    """
    day = today or _today_utc()
    survey_note = ""
    if surveyor_hint:
        survey_note = f" Suggest: {surveyor_hint}."

    sol_na = solicitor_non_response_ids or set()
    chain_unresp = chain_unresponsive_by_progression_id or {}
    results: list[dict] = []

    for p in properties:
        triggers: list[dict] = []

        prog_sid = str(p.get("_portal_progression_id") or "").strip()
        if prog_sid:
            for item in chain_unresp.get(prog_sid, []):
                firm = (item.get("firm") or "Chain solicitor").strip()
                crm_id = str(p.get("id") or "").strip()
                href = f"/#property-{crm_id}" if crm_id else "#"
                _append_trigger(
                    triggers,
                    trigger_id="chain_solicitor_unresponsive",
                    trigger_name=f"Chain solicitor unresponsive — {firm}",
                    days_overdue=0,
                    severity="amber",
                    suggested_action=(
                        "Chain solicitor has not replied after three contact attempts — "
                        "call and log outcome in NUVU Notes (reinstate / no contact)."
                    ),
                    quick_action={
                        "label": "Open property",
                        "kind": "open_dashboard_property",
                        "href": href,
                    },
                )

        if prog_sid and prog_sid in sol_na:
            _append_trigger(
                triggers,
                trigger_id="solicitor_non_response",
                trigger_name="Solicitor non-response",
                days_overdue=1,
                severity="amber",
                suggested_action=(
                    "Chase message to a solicitor with no reply within 24 hours — follow up."
                ),
                quick_action=_build_quick_action(
                    "email_sol", "Email solicitor", p
                ),
            )

        chain = (p.get("chain_status") or "stable").strip().lower()
        if chain in ("at_risk", "broken"):
            sev = "amber" if chain == "at_risk" else "red"
            msg = (
                "Chain issue reported — investigate."
                if chain == "at_risk"
                else "Chain has broken — urgent action required."
            )
            _append_trigger(
                triggers,
                trigger_id="chain",
                trigger_name="Chain issue"
                if chain == "at_risk"
                else "Chain breakdown",
                days_overdue=0,
                severity=sev,
                suggested_action=msg,
                quick_action=_build_quick_action(
                    "call_buyer", "Call buyer", p
                ),
            )

        w = _welcome_anchor(p)
        buyer_proto = _parse_ts(p.get("protocol_forms_returned"))
        seller_forms = _parse_ts(p.get("seller_forms_returned"))

        if w and not buyer_proto:
            d = _days_between(w, day)
            if d is not None and d >= 4:
                sev = "red" if d >= 7 else "amber"
                _append_trigger(
                    triggers,
                    trigger_id="buyer_protocol",
                    trigger_name="Buyer forms overdue",
                    days_overdue=d - 3,
                    severity=sev,
                    suggested_action=(
                        "Call buyer — protocol forms not returned after 3 daily chases"
                    ),
                    quick_action=_build_quick_action(
                        "call_buyer", "Call buyer", p
                    ),
                )

        if w and not seller_forms:
            d = _days_between(w, day)
            if d is not None and d >= 4:
                sev = "red" if d >= 7 else "amber"
                _append_trigger(
                    triggers,
                    trigger_id="seller_ta",
                    trigger_name="Seller forms overdue",
                    days_overdue=d - 3,
                    severity=sev,
                    suggested_action=(
                        "Call seller — offer portal link for guided form completion"
                    ),
                    quick_action=_build_quick_action(
                        "call_seller", "Call seller", p
                    ),
                )

        if w and not _parse_ts(p.get("survey_instructed")):
            d = _days_between(w, day)
            if d is not None and d >= 4:
                sev = "red" if d >= 8 else "amber"
                _append_trigger(
                    triggers,
                    trigger_id="survey",
                    trigger_name="Survey not booked",
                    days_overdue=max(0, d - 3),
                    severity=sev,
                    suggested_action=(
                        "Chase buyer/broker re survey. Recommend surveyors if none booked."
                        + survey_note
                    ),
                    quick_action=_build_quick_action(
                        "call_buyer", "Call buyer", p
                    ),
                )

        search_fees_ok = _parse_ts(p.get("search_fees_confirmed"))
        if buyer_proto and not search_fees_ok:
            d = _days_between(buyer_proto, day)
            if d is not None and d >= 3:
                sev = "red" if d >= 6 else "amber"
                _append_trigger(
                    triggers,
                    trigger_id="search_fees_chase",
                    trigger_name="Search fees not confirmed",
                    days_overdue=d - 2,
                    severity=sev,
                    suggested_action=(
                        "Stage 4: no confirmation of search fees — negotiator to follow up with buyer."
                    ),
                    quick_action=_build_quick_action(
                        "call_buyer", "Call buyer", p
                    ),
                )

        draft_done = _parse_ts(p.get("draft_contract_issued")) or _parse_ts(
            p.get("draft_contract_sent")
        )
        if seller_forms and not draft_done:
            d = _days_between(seller_forms, day)
            if d is not None and d >= 4:
                sev = "red" if d >= 7 else "amber"
                _append_trigger(
                    triggers,
                    trigger_id="draft_contract",
                    trigger_name="Draft contract overdue",
                    days_overdue=d - 3,
                    severity=sev,
                    suggested_action=(
                        "Stage 5: draft contract not issued — escalate with seller’s solicitor."
                    ),
                    quick_action=_build_quick_action(
                        "email_sol", "Email solicitor", p
                    ),
                )

        so = _parse_ts(p.get("searches_ordered"))
        if so and not _parse_ts(p.get("searches_received")):
            threshold = _la_threshold_days(p, la_turnaround_by_norm_name)
            due = add_working_days(so, threshold)
            if due is not None and day > due:
                overdue = (day - due).days
                sev = "red" if overdue >= 4 else "amber"
                _append_trigger(
                    triggers,
                    trigger_id="searches_overdue",
                    trigger_name="Searches overdue",
                    days_overdue=overdue,
                    severity=sev,
                    suggested_action=(
                        "Stage 6: expected search turnaround passed — chase buyer’s solicitor."
                    ),
                    quick_action=_build_quick_action(
                        "email_sol", "Email solicitor", p
                    ),
                )

        etd = _parse_ts(p.get("exchange_target_date"))
        if etd and not p.get("_is_exchanged"):
            try:
                etd_d = etd.date() if isinstance(etd, datetime) else etd
                if etd_d < day:
                    days_past = (day - etd_d).days
                    _append_trigger(
                        triggers,
                        trigger_id="exchange_target_passed",
                        trigger_name="Exchange target date passed",
                        days_overdue=days_past,
                        severity="red",
                        suggested_action=(
                            "Exchange target date passed — negotiator to review. "
                            "No further automated exchange chases are sent."
                        ),
                        quick_action=_build_quick_action(
                            "email_sol", "Email solicitor", p
                        ),
                    )
            except (TypeError, ValueError, AttributeError):
                pass

        d_sr = _parse_ts(p.get("searches_received"))
        d_si = _parse_ts(p.get("survey_instructed"))
        if d_sr and d_si and not _parse_ts(p.get("enquiries_raised")):
            ref = max(d_sr, d_si)
            days_waiting = _days_between(ref, day)
            if days_waiting is not None and days_waiting >= 1:
                sev = "red" if days_waiting >= 4 else "amber"
                _append_trigger(
                    triggers,
                    trigger_id="enquiries",
                    trigger_name="Enquiries not raised",
                    days_overdue=days_waiting,
                    severity=sev,
                    suggested_action=(
                        "Prompt buyer's solicitor: you have searches and survey — raise enquiries"
                    ),
                    quick_action=_build_quick_action(
                        "email_sol", "Email solicitor", p
                    ),
                )

        ea_done = _parse_ts(p.get("enquiries_answered"))
        if ea_done and not _parse_ts(p.get("report_on_title")):
            d_rt = _days_between(ea_done, day)
            if d_rt is not None and d_rt >= 8:
                _append_trigger(
                    triggers,
                    trigger_id="report_on_title_overdue",
                    trigger_name="Report on title not confirmed",
                    days_overdue=d_rt - 5,
                    severity="red",
                    suggested_action=(
                        "Report on title not confirmed after chase — negotiator to follow up."
                    ),
                    quick_action=_build_quick_action(
                        "email_buyer_sol", "Email buyer's solicitor", p
                    ),
                )

        if not triggers:
            continue

        triggers.sort(
            key=lambda t: (0 if t["severity"] == "red" else 1, -t["days_overdue"])
        )
        results.append({"property": p, "triggers": triggers})

    def _sort_key(item: dict) -> tuple:
        ts = item["triggers"]
        red_n = sum(1 for t in ts if t["severity"] == "red")
        max_over = max(t["days_overdue"] for t in ts)
        return (-red_n, -max_over)

    results.sort(key=_sort_key)
    return results


def emit_needs_attention_events(na_results: list[dict]) -> None:
    """Emit gate_raised events for newly fired Needs Attention triggers.

    Called after get_needs_attention(). Deduplicates against events seen in
    the last 24 hours so that repeated dashboard loads don't flood the log.
    """
    if not na_results:
        return

    from datetime import timedelta

    from db_supabase import supabase_for_backend
    from utils.events import emit_event

    addrs = []
    for item in na_results:
        p = item.get("property") or {}
        a = (p.get("address") or p.get("property_address") or "").strip()
        if a and a not in addrs:
            addrs.append(a)

    if not addrs:
        return

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    client = supabase_for_backend()
    try:
        res = (
            client.table("events")
            .select("property_address,payload")
            .eq("event_type", "gate_raised")
            .in_("property_address", addrs)
            .gte("created_at", cutoff)
            .execute()
        )
        recent = res.data or []
    except Exception:
        recent = []

    seen: set[tuple[str, str]] = set()
    for ev in recent:
        a = ev.get("property_address") or ""
        payload = ev.get("payload") or {}
        t = payload.get("trigger") or ""
        if a and t:
            seen.add((a, t))

    for item in na_results:
        p = item.get("property") or {}
        addr = (p.get("address") or p.get("property_address") or "").strip()
        if not addr:
            continue
        for t in item.get("triggers") or []:
            trigger_id = t.get("trigger_id") or ""
            if not trigger_id or (addr, trigger_id) in seen:
                continue
            emit_event(
                event_type="gate_raised",
                property_address=addr,
                summary=f"Needs attention: {t.get('trigger_name') or trigger_id}",
                actor="system",
                payload={
                    "trigger": trigger_id,
                    "reason": t.get("suggested_action") or t.get("trigger_name") or trigger_id,
                    "days_stalled": t.get("days_overdue"),
                    "milestone": trigger_id,
                },
            )
            seen.add((addr, trigger_id))
