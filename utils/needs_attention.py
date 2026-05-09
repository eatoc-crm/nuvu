"""Needs Attention trigger engine (NUVU Progression Engine spec)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import quote

# Default search turnaround when no local authority row matches.
DEFAULT_SEARCH_TURNAROUND_DAYS = 21


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
    results: list[dict] = []

    for p in properties:
        triggers: list[dict] = []

        prog_sid = str(p.get("_portal_progression_id") or "").strip()
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

        if buyer_proto and not _parse_ts(p.get("searches_ordered")):
            d = _days_between(buyer_proto, day)
            if d is not None and d >= 3:
                sev = "red" if d >= 6 else "amber"
                _append_trigger(
                    triggers,
                    trigger_id="search_fees",
                    trigger_name="Search fees not paid",
                    days_overdue=d - 2,
                    severity=sev,
                    suggested_action=(
                        "Ask buyer: did your solicitor request search fees?"
                    ),
                    quick_action=_build_quick_action(
                        "call_buyer", "Call buyer", p
                    ),
                )

        if seller_forms and not _parse_ts(p.get("draft_contract_sent")):
            d = _days_between(seller_forms, day)
            if d is not None and d >= 4:
                sev = "red" if d >= 7 else "amber"
                _append_trigger(
                    triggers,
                    trigger_id="draft_contract",
                    trigger_name="Draft contract overdue",
                    days_overdue=d - 3,
                    severity=sev,
                    suggested_action="Chase seller's solicitor for draft contract",
                    quick_action=_build_quick_action(
                        "email_sol", "Email solicitor", p
                    ),
                )

        so = _parse_ts(p.get("searches_ordered"))
        if so and not _parse_ts(p.get("searches_received")):
            d = _days_between(so, day)
            if d is not None:
                threshold = _la_threshold_days(p, la_turnaround_by_norm_name)
                overdue = d - threshold
                if overdue >= 0:
                    sev = "red" if overdue >= 4 else "amber"
                    _append_trigger(
                        triggers,
                        trigger_id="searches_overdue",
                        trigger_name="Searches overdue",
                        days_overdue=overdue,
                        severity=sev,
                        suggested_action="Chase buyer's solicitor for search results",
                        quick_action=_build_quick_action(
                            "email_sol", "Email solicitor", p
                        ),
                    )

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
