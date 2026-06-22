"""EATOC live property list mapped to dashboard card shape (dashboard + portal)."""

import os
from datetime import datetime

import requests as http_requests

EATOC_API_URL = "https://app.eatoc.co.uk/api/nuvu/properties"
NUVU_API_KEY = os.environ.get("NUVU_API_KEY", "dbe-nuvu-2026")


def _iso_date_prefix(val):
    if not val:
        return None
    s = str(val).strip()
    return s[:10] if len(s) >= 10 else None


def fetch_eatoc_properties():
    """Fetch live sales progression data from the EATOC CRM API."""
    try:
        resp = http_requests.get(
            EATOC_API_URL,
            headers={"x-api-key": NUVU_API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json(), None
    except http_requests.RequestException as e:
        return [], str(e)


STATUS_MAP = {
    "active": "on-track",
    "exchanged": "exchanged",
    "development": "on-track",
    "problem": "at-risk",
    "incomplete_chain": "stalled",
}
STATUS_LABELS = {
    "on-track": "ON TRACK",
    "exchanged": "EXCHANGED",
    "at-risk": "AT RISK",
    "stalled": "STALLED",
}

FALLBACK_GRADIENTS = [
    "linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%)",
    "linear-gradient(135deg,#2d3436 0%,#636e72 100%)",
    "linear-gradient(135deg,#355c7d 0%,#6c5b7b 50%,#c06c84 100%)",
    "linear-gradient(135deg,#667eea 0%,#764ba2 100%)",
    "linear-gradient(135deg,#11998e 0%,#38ef7d 100%)",
    "linear-gradient(135deg,#e0c3fc 0%,#8ec5fc 100%)",
    "linear-gradient(135deg,#89f7fe 0%,#66a6ff 100%)",
    "linear-gradient(135deg,#fbc2eb 0%,#a6c1ee 100%)",
]


def _progress_from_record(r):
    """Estimate progress % from which milestone fields are populated."""
    steps = [
        r.get("offer_accepted"),
        r.get("memo_sent"),
        r.get("searches_ordered"),
        r.get("mortgage_offered"),
        r.get("enquiries_raised"),
        r.get("enquiries_answered"),
        r.get("exchange_date"),
        r.get("completion_date"),
    ]
    done = sum(1 for s in steps if s)
    if r.get("status") == "exchanged":
        return 90
    return max(10, int(done / len(steps) * 80))


def _card_checks_from_record(r):
    return [
        {"label": "Memo Sent", "done": bool(r.get("memo_sent"))},
        {"label": "Exchange", "done": bool(r.get("exchange_date"))},
        {"label": "Completion", "done": bool(r.get("completion_date"))},
    ]


def _milestones_from_record(r):
    return [
        {
            "label": "Offer Accepted",
            "field": "offer_accepted",
            "done": bool(r.get("offer_accepted")),
            "date": r.get("offer_accepted") or "",
        },
        {
            "label": "Memo Sent",
            "field": "memo_sent",
            "done": bool(r.get("memo_sent")),
            "date": r.get("memo_sent") or "",
        },
        {
            "label": "Searches Ordered",
            "field": "searches_ordered",
            "done": bool(r.get("searches_ordered")),
            "date": r.get("searches_ordered") or "",
        },
        {
            "label": "Searches Received",
            "field": "searches_received",
            "done": bool(r.get("searches_received")),
            "date": r.get("searches_received") or "",
        },
        {
            "label": "Survey Instructed",
            "field": "survey_instructed",
            "done": bool(r.get("survey_instructed")),
            "date": r.get("survey_instructed") or "",
        },
        {
            "label": "Mortgage Offer Received",
            "field": "mortgage_offered",
            "done": bool(r.get("mortgage_offered")),
            "date": r.get("mortgage_offered") or "",
        },
        {
            "label": "Draft Contract Sent",
            "field": "draft_contract_sent",
            "done": bool(r.get("draft_contract_sent")),
            "date": r.get("draft_contract_sent") or "",
        },
        {
            "label": "Search fees paid (buyer)",
            "field": "search_fees_confirmed",
            "done": bool(r.get("search_fees_confirmed")),
            "date": r.get("search_fees_confirmed") or "",
        },
        {
            "label": "Draft contract issued",
            "field": "draft_contract_issued",
            "done": bool(r.get("draft_contract_issued")),
            "date": r.get("draft_contract_issued") or "",
        },
        {
            "label": "Enquiries Raised",
            "field": "enquiries_raised",
            "done": bool(r.get("enquiries_raised")),
            "date": r.get("enquiries_raised") or "",
        },
        {
            "label": "Enquiries Satisfied",
            "field": "enquiries_answered",
            "done": bool(r.get("enquiries_answered")),
            "date": r.get("enquiries_answered") or "",
        },
        {
            "label": "Report on title sent",
            "field": "report_on_title",
            "done": bool(r.get("report_on_title")),
            "date": r.get("report_on_title") or "",
        },
        {
            "label": "Target exchange date (NUVU)",
            "field": "exchange_target_date",
            "done": bool(r.get("exchange_target_date")),
            "date": r.get("exchange_target_date") or "",
        },
        {
            "label": "Buyer protocol forms returned",
            "field": "protocol_forms_returned",
            "done": bool(r.get("protocol_forms_returned")),
            "date": r.get("protocol_forms_returned") or "",
        },
        {
            "label": "Seller TA6/TA10 dispatched",
            "field": "seller_forms_returned",
            "done": bool(r.get("seller_forms_returned")),
            "date": r.get("seller_forms_returned") or "",
        },
        {
            "label": "Exchange",
            "field": "exchange_date",
            "done": bool(r.get("exchange_date")),
            "date": r.get("exchange_date") or "",
        },
        {
            "label": "Completion",
            "field": "completion_date",
            "done": bool(r.get("completion_date")),
            "date": r.get("completion_date") or "",
        },
    ]


_OVERLAY_SKIP_SUPABASE_NULL = frozenset(
    {"notes", "nuvu_notes", "buyer_solicitor_notes", "seller_solicitor_notes"}
)


def _merge_supabase_progression_overlay(raw_rows):
    """NUVU PATCH writes to Supabase; EATOC list may lag. Overlay authoritative columns."""
    if not raw_rows:
        return
    try:
        from db_supabase import (
            SALES_PROGRESSION_OVERLAY_COLS,
            fetch_sales_progression_overlay_by_addresses,
        )
        from utils.address import normalise_address

        addrs = [r.get("property_address") for r in raw_rows]
        by_norm = fetch_sales_progression_overlay_by_addresses(addrs)
        for r in raw_rows:
            key = normalise_address(r.get("property_address") or "")
            if not key:
                continue
            row = by_norm.get(key)
            if not row:
                continue
            for col in SALES_PROGRESSION_OVERLAY_COLS:
                if col not in row:
                    continue
                val = row[col]
                if val is None and col in _OVERLAY_SKIP_SUPABASE_NULL:
                    continue
                r[col] = val
            rid = row.get("id")
            if rid is not None:
                r["sales_progression_supabase_id"] = rid
    except Exception:
        pass


def _map_live_properties():
    """Fetch from EATOC API and map to the dict shape DASHBOARD_HTML expects."""
    raw, error = fetch_eatoc_properties()
    if error:
        return [], error
    _merge_supabase_progression_overlay(raw)
    mapped = []
    for i, r in enumerate(raw):
        raw_status = (r.get("status") or "active").lower()
        if raw_status not in STATUS_MAP:
            raw_status = "active"
        status = STATUS_MAP.get(raw_status, "on-track")
        progress = _progress_from_record(r)
        mapped.append(
            {
                "id": r["id"],
                "address": r.get("property_address", "Unknown"),
                "location": (r.get("branch") or "").title(),
                "price": r.get("sale_price") or r.get("fee") or 0,
                "status": status,
                "status_label": STATUS_LABELS.get(status, "ON TRACK"),
                "progress": progress,
                "duration_days": (
                    datetime.utcnow()
                    - datetime.strptime(r["created_at"][:19], "%Y-%m-%dT%H:%M:%S")
                ).days
                if r.get("created_at")
                else 0,
                "target_days": 60,
                "days_since_update": 0,
                "card_checks": _card_checks_from_record(r),
                "milestones": _milestones_from_record(r),
                "buyer": r.get("buyer_name") or "\u2014",
                "buyer_phone": r.get("buyer_phone") or "\u2014",
                "buyer_solicitor": r.get("buyer_solicitor") or "\u2014",
                "buyer_sol_phone": r.get("buyer_solicitor_phone") or "\u2014",
                "seller_solicitor": r.get("vendor_solicitor") or "\u2014",
                "seller_sol_phone": r.get("seller_solicitor_phone") or "\u2014",
                # Enriched solicitor fields (populated by adapter_sync solicitor enrichment)
                "buyer_solicitor_contact_name": r.get("buyer_solicitor_contact_name") or "\u2014",
                "buyer_solicitor_email": r.get("buyer_solicitor_email") or "\u2014",
                "buyer_solicitor_phone": r.get("buyer_solicitor_phone") or "\u2014",
                "buyer_solicitor_address": r.get("buyer_solicitor_address") or "\u2014",
                "seller_solicitor_contact_name": r.get("seller_solicitor_contact_name") or "\u2014",
                "seller_solicitor_email": r.get("seller_solicitor_email") or "\u2014",
                "seller_solicitor_phone": r.get("seller_solicitor_phone") or "\u2014",
                "seller_solicitor_address": r.get("seller_solicitor_address") or "\u2014",
                "offer_date": r.get("offer_accepted"),
                "memo_sent": r.get("memo_sent"),
                "searches_ordered": r.get("searches_ordered"),
                "searches_received": r.get("searches_received"),
                "search_fees_confirmed": r.get("search_fees_confirmed"),
                "survey_instructed": r.get("survey_instructed"),
                "draft_contract_sent": r.get("draft_contract_sent"),
                "draft_contract_issued": r.get("draft_contract_issued"),
                "enquiries_raised": r.get("enquiries_raised"),
                "enquiries_answered": r.get("enquiries_answered"),
                "report_on_title": r.get("report_on_title"),
                "exchange_target_date": r.get("exchange_target_date"),
                "mortgage_offered": r.get("mortgage_offered"),
                "exchange_target": r.get("exchange_date"),
                "completion_target": r.get("completion_target") or r.get("completion_date"),
                "protocol_forms_returned": r.get("protocol_forms_returned"),
                "seller_forms_returned": r.get("seller_forms_returned"),
                "welcome_emails_sent": r.get("welcome_emails_sent"),
                # EATOC API aliases (funnel / display co-read; see dashboard funnel mapping)
                "welcome_sent": r.get("welcome_sent"),
                "protocol_forms_sent": r.get("protocol_forms_sent"),
                "protocol_forms_received": r.get("protocol_forms_received"),
                "chain": "\u2014",
                "alert": r.get("notes") if raw_status == "problem" else None,
                "next_action": r.get("notes") or "\u2014",
                "notes": r.get("notes") or "",
                "nuvu_notes": r.get("nuvu_notes") or "",
                "buyer_solicitor_notes": r.get("buyer_solicitor_notes") or "",
                "seller_solicitor_notes": r.get("seller_solicitor_notes") or "",
                "image_bg": FALLBACK_GRADIENTS[i % len(FALLBACK_GRADIENTS)],
                "image_url": r.get("image_url") or "",
                "_progression_id": r.get("sales_progression_supabase_id") or r.get("id"),
                "_portal_progression_id": r.get("sales_progression_supabase_id") or "",
                "_eatoc_property_id": r.get("id"),
                "_raw_status": raw_status,
                "_eatoc_created_at": r.get("created_at"),
                "_sewage_type": r.get("sewage_type") or "\u2014",
                "_mortgage_broker": r.get("mortgage_broker") or "\u2014",
                "_surveyor": r.get("surveyor") or "\u2014",
                "_buyer_email": r.get("buyer_email") or "\u2014",
                "_vendor_name": r.get("vendor_name") or "\u2014",
                "_vendor_phone": r.get("vendor_phone") or "\u2014",
                "_vendor_email": r.get("vendor_email") or "\u2014",
                "_nuvu_notes": r.get("nuvu_notes") or "\u2014",
                "_staff_initials": r.get("staff_initials") or "\u2014",
                "_negotiator_name": (
                    (r.get("negotiator_name") or r.get("negotiator") or "")
                    .strip()
                ),
                "agreed_fee": r.get("agreed_fee"),
                "_fee": r.get("fee"),
                "_invoice_status": r.get("invoice_status") or "\u2014",
                "_beds": r.get("beds"),
                "_baths": r.get("baths"),
                "_property_type": r.get("property_type") or "\u2014",
                "_date_agreed": _iso_date_prefix(r.get("offer_accepted"))
                or _iso_date_prefix(r.get("created_at")),
            }
        )
    return mapped, None


def _sandbox_duration_days(created_val):
    if not created_val:
        return 0
    s = str(created_val)
    try:
        if len(s) >= 19 and "T" in s[:19]:
            d = datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
        elif len(s) >= 10:
            d = datetime.strptime(s[:10], "%Y-%m-%d")
        else:
            return 0
        return max(0, (datetime.utcnow() - d).days)
    except Exception:
        return 0


def _map_supabase_test_property(prog: dict, pipe: dict, idx: int) -> dict:
    """Dashboard row from Supabase-only sandbox (sales_progression + sales_pipeline)."""
    r = prog
    rid = str(r.get("id") or "")
    raw_status = (r.get("status") or "active").lower()
    if raw_status not in STATUS_MAP:
        raw_status = "active"
    status = STATUS_MAP.get(raw_status, "on-track")
    progress = _progress_from_record(r)
    created_src = pipe.get("created_at") or r.get("created_at")
    neg = ((pipe.get("negotiator") or r.get("negotiator_name") or "")).strip()
    return {
        "id": rid,
        "address": (r.get("property_address") or "Unknown").strip(),
        "location": "Testington",
        "price": r.get("sale_price") or pipe.get("current_price") or 0,
        "status": status,
        "status_label": STATUS_LABELS.get(status, "ON TRACK"),
        "progress": progress,
        "duration_days": _sandbox_duration_days(created_src),
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": _card_checks_from_record(r),
        "milestones": _milestones_from_record(r),
        "buyer": r.get("buyer_name") or "\u2014",
        "buyer_phone": r.get("buyer_phone") or "\u2014",
        "buyer_solicitor": (pipe.get("buyers_solicitor") or r.get("buyer_solicitor") or "\u2014"),
        "buyer_sol_phone": pipe.get("buyer_solicitor_phone") or "\u2014",
        "seller_solicitor": (pipe.get("vendors_solicitor") or r.get("vendor_solicitor") or "\u2014"),
        "seller_sol_phone": pipe.get("seller_solicitor_phone") or "\u2014",
        # Enriched solicitor fields
        "buyer_solicitor_contact_name": pipe.get("buyer_solicitor_contact_name") or "\u2014",
        "buyer_solicitor_email": pipe.get("buyer_solicitor_email") or "\u2014",
        "buyer_solicitor_phone": pipe.get("buyer_solicitor_phone") or "\u2014",
        "buyer_solicitor_address": pipe.get("buyer_solicitor_address") or "\u2014",
        "seller_solicitor_contact_name": pipe.get("seller_solicitor_contact_name") or "\u2014",
        "seller_solicitor_email": pipe.get("seller_solicitor_email") or "\u2014",
        "seller_solicitor_phone": pipe.get("seller_solicitor_phone") or "\u2014",
        "seller_solicitor_address": pipe.get("seller_solicitor_address") or "\u2014",
        "offer_date": r.get("offer_accepted"),
        "memo_sent": r.get("memo_sent"),
        "searches_ordered": r.get("searches_ordered"),
        "searches_received": r.get("searches_received"),
        "search_fees_confirmed": r.get("search_fees_confirmed"),
        "survey_instructed": r.get("survey_instructed"),
        "draft_contract_sent": r.get("draft_contract_sent"),
        "draft_contract_issued": r.get("draft_contract_issued"),
        "enquiries_raised": r.get("enquiries_raised"),
        "enquiries_answered": r.get("enquiries_answered"),
        "report_on_title": r.get("report_on_title"),
        "exchange_target_date": r.get("exchange_target_date"),
        "mortgage_offered": r.get("mortgage_offered"),
        "exchange_target": r.get("exchange_date"),
        "completion_target": r.get("completion_target") or r.get("completion_date"),
        "protocol_forms_returned": r.get("protocol_forms_returned"),
        "seller_forms_returned": r.get("seller_forms_returned"),
        "welcome_emails_sent": r.get("welcome_emails_sent"),
        "welcome_sent": r.get("welcome_sent"),
        "protocol_forms_sent": r.get("protocol_forms_sent"),
        "protocol_forms_received": r.get("protocol_forms_received"),
        "chain": "\u2014",
        "alert": r.get("notes") if raw_status == "problem" else None,
        "next_action": r.get("notes") or "\u2014",
        "notes": r.get("notes") or "",
        "nuvu_notes": r.get("nuvu_notes") or "",
        "buyer_solicitor_notes": r.get("buyer_solicitor_notes") or "",
        "seller_solicitor_notes": r.get("seller_solicitor_notes") or "",
        "image_bg": FALLBACK_GRADIENTS[idx % len(FALLBACK_GRADIENTS)],
        "image_url": r.get("image_url") or "",
        "_progression_id": rid,
        "_portal_progression_id": rid,
        "_eatoc_property_id": "",
        "_raw_status": raw_status,
        "_eatoc_created_at": created_src,
        "_sewage_type": r.get("sewage_type") or "\u2014",
        "_mortgage_broker": r.get("mortgage_broker") or "\u2014",
        "_surveyor": r.get("surveyor") or "\u2014",
        "_buyer_email": r.get("buyer_email") or "\u2014",
        "_vendor_name": r.get("vendor_name") or "\u2014",
        "_vendor_phone": r.get("vendor_phone") or "\u2014",
        "_vendor_email": r.get("vendor_email") or "\u2014",
        "_nuvu_notes": r.get("nuvu_notes") or "\u2014",
        "_staff_initials": r.get("staff_initials") or "\u2014",
        "_negotiator_name": neg,
        "agreed_fee": pipe.get("agreed_fee") or r.get("agreed_fee"),
        "_fee": pipe.get("fee") or r.get("fee"),
        "_invoice_status": r.get("invoice_status") or "\u2014",
        "_beds": r.get("beds"),
        "_baths": r.get("baths"),
        "_property_type": r.get("property_type") or "Sandbox",
        "_date_agreed": _iso_date_prefix(r.get("offer_accepted"))
        or _iso_date_prefix(created_src),
        "_is_test": True,
    }
