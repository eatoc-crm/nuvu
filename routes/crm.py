import json
import os
from datetime import date, datetime

import requests as http_requests
from flask import Blueprint, jsonify, render_template, render_template_string, request

crm_bp = Blueprint("crm", __name__)


# ─────────────────────────────────────────────────────────────
#  EATOC CRM LIVE PROPERTY CARDS
# ─────────────────────────────────────────────────────────────

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


def build_ai_panel(prop):
    """Generate AI insight panel from property milestone state."""
    done = []
    todo = []
    human = []

    if prop.get("offer_accepted"):
        done.append("Offer accepted and recorded")
    else:
        todo.append("Chase offer acceptance confirmation")

    if prop.get("memo_sent"):
        done.append("Memorandum of sale sent to all parties")
    else:
        todo.append("Send memorandum of sale")

    if prop.get("buyer_solicitor"):
        done.append("Buyer solicitor instructed")
    else:
        todo.append("Confirm buyer solicitor instruction")

    if prop.get("vendor_solicitor"):
        done.append("Vendor solicitor instructed")
    else:
        todo.append("Confirm vendor solicitor instruction")

    if prop.get("exchange_date"):
        done.append("Exchange completed")
    elif prop.get("memo_sent"):
        todo.append("Progress to exchange — chase solicitors for contract pack")

    if prop.get("completion_date"):
        done.append("Completion achieved")
    elif prop.get("exchange_date"):
        todo.append("Prepare for completion — confirm move date and key handover")

    status = (prop.get("status") or "").lower()
    if status == "problem":
        human.append(
            "Property flagged as PROBLEM — review and resolve before progressing"
        )
    if status == "incomplete_chain":
        human.append("Incomplete chain detected — identify and resolve chain break")
    if not prop.get("buyer_solicitor") and not prop.get("vendor_solicitor"):
        human.append("No solicitors on file — contact buyer and vendor for solicitor details")
    if not prop.get("mortgage_broker") and prop.get("sale_price"):
        human.append("No mortgage broker recorded — confirm buyer's funding position")

    return {"done": done, "todo": todo, "human": human}


# ─────────────────────────────────────────────────────────────
#  LIVE CRM — map API data to DASHBOARD_HTML template shape
# ─────────────────────────────────────────────────────────────

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


# Free-text note columns: Supabase row may exist for milestones while these stay
# null in Postgres; do not overwrite non-null EATOC payloads with null.
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
                "buyer_sol_phone": "\u2014",
                "seller_solicitor": r.get("vendor_solicitor") or "\u2014",
                "seller_sol_phone": "\u2014",
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
                "completion_target": r.get("completion_date"),
                "protocol_forms_returned": r.get("protocol_forms_returned"),
                "seller_forms_returned": r.get("seller_forms_returned"),
                "welcome_emails_sent": r.get("welcome_emails_sent"),
                "chain": "\u2014",
                "alert": r.get("notes") if raw_status == "problem" else None,
                "next_action": r.get("notes") or "\u2014",
                "notes": r.get("notes") or "",
                "nuvu_notes": r.get("nuvu_notes") or "",
                "buyer_solicitor_notes": r.get("buyer_solicitor_notes") or "",
                "seller_solicitor_notes": r.get("seller_solicitor_notes") or "",
                "image_bg": FALLBACK_GRADIENTS[i % len(FALLBACK_GRADIENTS)],
                "image_url": r.get("image_url") or "",
                # extra fields for detail page
                "_progression_id": r.get("sales_progression_supabase_id") or r.get("id"),
                # Supabase sales_progression.id only — use for /portal staff previews (not EATOC id)
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
        "buyer_sol_phone": "\u2014",
        "seller_solicitor": (pipe.get("vendors_solicitor") or r.get("vendor_solicitor") or "\u2014"),
        "seller_sol_phone": "\u2014",
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
        "completion_target": r.get("completion_date"),
        "protocol_forms_returned": r.get("protocol_forms_returned"),
        "seller_forms_returned": r.get("seller_forms_returned"),
        "welcome_emails_sent": r.get("welcome_emails_sent"),
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


def _crm_stats(props):
    """Compute live stats from mapped properties."""
    total = len(props)
    exchanged = sum(1 for p in props if p.get("_raw_status") == "exchanged")
    problems = sum(1 for p in props if p.get("_raw_status") == "problem")
    incomplete = sum(1 for p in props if p.get("_raw_status") == "incomplete_chain")
    active = total - exchanged
    property_pipeline = sum(p["price"] for p in props if p["price"])
    fee_pipeline = sum(p.get("_fee") or 0 for p in props if p.get("_fee"))
    return {
        "active": active,
        "on_track": exchanged,
        "at_risk": problems,
        "action": incomplete,
        "exchanged": exchanged,
        "fee_pipeline": fee_pipeline,
        "property_pipeline": property_pipeline,
    }


def _crm_sections(props):
    """Group live properties into sections for the dashboard template."""
    problems = [p for p in props if p["_raw_status"] == "problem"]
    incomplete = [p for p in props if p["_raw_status"] == "incomplete_chain"]
    exchanged = [p for p in props if p["_raw_status"] == "exchanged"]
    active = [p for p in props if p["_raw_status"] in ("active", "development")]

    def _section(sid, icon, title, subtitle, border, items):
        visible = items[:3]
        hidden = items[3:]
        avg = int(sum(p["progress"] for p in items) / len(items)) if items else 0
        color = (
            "#e25555"
            if border == "stalled-banner"
            else "#e88a3a"
            if border == "amber-banner"
            else "#27ae60"
        )
        return {
            "id": sid,
            "icon": icon,
            "title": title,
            "subtitle": subtitle,
            "avg_progress": avg,
            "avg_color": color,
            "border_class": border,
            "visible_ids": [],
            "hidden_ids": [],
            "visible": visible,
            "hidden": hidden,
            "extra_count": 0,
        }

    sections = []
    if problems or incomplete:
        needs = problems + incomplete
        sections.append(
            _section(
                "needs-action",
                "\U0001F6A8",
                "Needs Action",
                f"{len(needs)} transactions requiring attention",
                "stalled-banner",
                needs,
            )
        )
    if exchanged:
        sections.append(
            _section(
                "exchanged",
                "\u2705",
                "Exchanged",
                f"{len(exchanged)} exchanged",
                "green-banner",
                exchanged,
            )
        )
    if active:
        sections.append(
            _section(
                "active",
                "\U0001F4C5",
                "Active Pipeline",
                f"{len(active)} active transactions",
                "blue-banner",
                active,
            )
        )
    return sections


# JS snippet appended after DASHBOARD_HTML to redirect card clicks to detail page
CRM_OVERRIDE_JS = r"""
<script>
(function(){
  var base = "{{ detail_base_url }}";
  if (!base) return;
  var PROPS = {{ properties_json|safe }};
  for (var i = 0; i < PROPS.length; i++) {
    (function(pid){
      var card = document.getElementById("card-" + pid);
      if (card) {
        card.onclick = function(e) {
          e.stopPropagation();
          window.location.href = base + "/" + pid;
        };
      }
    })(PROPS[i].id);
  }

})();
</script>
"""


_RECIPIENT_LABELS = {
    "buyer": "Buyer",
    "seller": "Seller",
    "buyer_solicitor": "Buyer Sol.",
    "seller_solicitor": "Seller Sol.",
    "negotiator": "Team",
    "chain_solicitor": "Chain Sol.",
}


def _recipient_type_label(rt):
    k = (rt or "").strip().lower()
    return _RECIPIENT_LABELS.get(k, (rt or "Party").replace("_", " ").title())


_CHASE_STAGE_LABELS = {
    "buyer_protocol_forms": "Buyer protocol forms",
    "seller_ta6_ta10": "Seller TA6 / TA10",
    "survey_instruction": "Survey instruction",
    "post_survey_followup": "Post-survey follow-up",
}


def _chase_stage_label(stage, day):
    st = (stage or "").strip()
    base = _CHASE_STAGE_LABELS.get(st, st.replace("_", " ").title())
    try:
        d = int(day)
    except (TypeError, ValueError):
        d = 0
    return f"{base} — Day {d}"


def _format_detail_dt(val):
    if not val:
        return ""
    s = str(val).strip()
    if not s:
        return ""
    from datetime import datetime

    try:
        s2 = s.replace("Z", "+00:00") if s.endswith("Z") else s
        if len(s2) >= 19 and "T" in s2[:19]:
            dt = datetime.fromisoformat(s2)
        elif len(s) >= 10 and s[4] == "-" and s[7] == "-":
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
        else:
            return s[:19]
    except Exception:
        return s[:19]
    if getattr(dt, "hour", 0) or getattr(dt, "minute", 0) or getattr(dt, "second", 0):
        return f"{dt.day} {dt.strftime('%B %Y')}, {dt.strftime('%H:%M')}"
    return f"{dt.day} {dt.strftime('%B %Y')}"


def _format_detail_date_only(val):
    if not val:
        return ""
    s = str(val).strip()
    if not s:
        return ""
    from datetime import datetime

    try:
        if len(s) >= 19 and "T" in s[:19]:
            dt = datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
        elif len(s) >= 10:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
        else:
            return s[:10]
    except Exception:
        return s[:10]
    return f"{dt.day} {dt.strftime('%B %Y')}"


def _date_input_from_raw(val):
    """YYYY-MM-DD for HTML date inputs."""
    if not val:
        return ""
    s = str(val).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return ""


def _prog_value(prop, field):
    alias = {
        "offer_accepted": ("offer_date",),
        "exchange_date": ("exchange_target",),
        "completion_date": ("completion_target",),
    }
    for key in alias.get(field, (field,)):
        v = prop.get(key)
        if v:
            return v
    return prop.get(field)


def _welcome_anchor_dt(prop):
    from utils.needs_attention import parse_progression_timestamp

    return parse_progression_timestamp(
        prop.get("welcome_emails_sent")
    ) or parse_progression_timestamp(prop.get("memo_sent"))


def _milestone_overdue(prop, field, today):
    from utils.needs_attention import parse_progression_timestamp

    if _prog_value(prop, field):
        return False
    w = _welcome_anchor_dt(prop)
    if not w:
        return False
    wd = w.date() if hasattr(w, "date") else w
    try:
        days_w = (today - wd).days
    except Exception:
        return False
    proto = parse_progression_timestamp(_prog_value(prop, "protocol_forms_returned"))
    proto_d = proto.date() if proto and hasattr(proto, "date") else None
    sfr = parse_progression_timestamp(_prog_value(prop, "seller_forms_returned"))
    sfr_d = sfr.date() if sfr and hasattr(sfr, "date") else None
    so = parse_progression_timestamp(_prog_value(prop, "searches_ordered"))
    so_d = so.date() if so and hasattr(so, "date") else None

    if field == "protocol_forms_returned":
        return days_w >= 4
    if field == "survey_instructed":
        return days_w >= 4
    if field == "searches_ordered":
        if not proto_d:
            return False
        return (today - proto_d).days >= 3
    if field == "draft_contract_sent":
        if not sfr_d:
            return False
        return (today - sfr_d).days >= 4
    if field == "searches_received":
        if not so_d:
            return False
        return (today - so_d).days >= 21
    if field == "enquiries_raised":
        sr = parse_progression_timestamp(_prog_value(prop, "searches_received"))
        si = parse_progression_timestamp(_prog_value(prop, "survey_instructed"))
        if not (sr and si):
            return False
        ad = max(sr.date(), si.date())
        return (today - ad).days >= 1
    return False


_PATCHABLE_MILESTONE_FIELDS = frozenset(
    {
        "welcome_emails_sent",
        "offer_accepted",
        "memo_sent",
        "protocol_forms_returned",
        "survey_instructed",
        "searches_ordered",
        "searches_received",
        "draft_contract_sent",
        "seller_forms_returned",
        "mortgage_offered",
        "enquiries_raised",
        "enquiries_answered",
        "report_on_title",
        "exchange_date",
        "completion_date",
    }
)


def build_detail_timeline_milestones(prop, today):
    ordered = [
        ("Welcome emails sent", "welcome_emails_sent"),
        ("Offer accepted", "offer_accepted"),
        ("Memorandum of sale sent", "memo_sent"),
        ("Buyer protocol forms returned", "protocol_forms_returned"),
        ("Survey instructed", "survey_instructed"),
        ("Search fees / searches ordered", "searches_ordered"),
        ("Searches received", "searches_received"),
        ("Draft contract issued", "draft_contract_sent"),
        ("Seller forms returned (TA6/TA10)", "seller_forms_returned"),
        ("Mortgage offer received", "mortgage_offered"),
        ("Enquiries raised", "enquiries_raised"),
        ("Enquiries answered", "enquiries_answered"),
        ("Report on title", "report_on_title"),
        ("Exchange", "exchange_date"),
        ("Completion", "completion_date"),
    ]
    out = []
    for label, field in ordered:
        raw = _prog_value(prop, field)
        done = bool(raw)
        disp = _format_detail_date_only(raw) if done else "Pending"
        dot = "sage" if done else "grey"
        if not done and _milestone_overdue(prop, field, today):
            dot = "coral"
        out.append(
            {
                "label": label,
                "field": field,
                "done": done,
                "date_display": disp,
                "input_date": _date_input_from_raw(raw) if done else "",
                "dot": dot,
                "patchable": field in _PATCHABLE_MILESTONE_FIELDS,
            }
        )
    return out


def _chain_solicitor_status_class(cl):
    raw = (cl.get("solicitor_status") or "").strip().lower()
    if raw in ("not_set", "contacted", "confirmed", "unresponsive"):
        return raw
    if cl.get("solicitor_acting_confirmed_at") or cl.get("solicitor_details_received"):
        return "confirmed"
    if (
        cl.get("last_chain_inform_sent_at")
        or cl.get("last_chain_request_sent_at")
        or cl.get("chain_solicitor_intro_sent_at")
        or cl.get("nuvu_introduced")
    ):
        return "contacted"
    return "not_set"


def _enrich_crm_detail_view(prop, today):
    for cm in prop.get("chase_messages") or []:
        cm["_sent_display"] = _format_detail_dt(cm.get("sent_at"))
        cm["_stage_display"] = _chase_stage_label(
            cm.get("chase_stage"), cm.get("chase_day")
        )
        cm["_recipient_label"] = _recipient_type_label(cm.get("recipient_type"))
    for c in prop.get("chase_confirmations_list") or []:
        c["_created_display"] = _format_detail_dt(c.get("created_at"))
        c["_actioned_display"] = _format_detail_dt(c.get("actioned_at"))
    for e in prop.get("inbound_emails_list") or []:
        e["_received_display"] = _format_detail_dt(e.get("received_at"))
    prop["_timeline_milestones"] = build_detail_timeline_milestones(prop, today)
    sol_links = [
        cl
        for cl in (prop.get("chain_links") or [])
        if (str(cl.get("solicitor_email") or "").strip())
    ]
    prop["_chain_solicitor_links"] = sol_links
    for cl in sol_links:
        cl["_status_class"] = _chain_solicitor_status_class(cl)
        intro = cl.get("chain_solicitor_intro_sent_at") or cl.get("nuvu_introduced")
        if intro is True:
            cl["_phase1_display"] = "Yes"
        elif intro:
            cl["_phase1_display"] = _format_detail_dt(intro)
        else:
            cl["_phase1_display"] = ""
        lu = cl.get("last_chain_inform_sent_at") or cl.get(
            "last_chain_request_sent_at"
        )
        cl["_last_update_display"] = _format_detail_dt(lu) if lu else ""
        cl["_last_reply_display"] = _format_detail_dt(
            cl.get("last_chain_solicitor_reply_at")
        )
    pt = prop.get("portal_ta6_ta10")
    if isinstance(pt, dict):
        if pt.get("link_sent_at"):
            pt["link_sent_at_display"] = _format_detail_dt(pt["link_sent_at"])
        if pt.get("submitted_at"):
            pt["submitted_at_display"] = _format_detail_dt(pt["submitted_at"])


@crm_bp.route("/crm")
def crm_dashboard():
    """Live CRM dashboard using NUVU design with real property data."""
    from routes.dashboard import (
        DASHBOARD_HTML,
        LEADERBOARD_TABS,
        _build_live_dashboard_data,
    )

    show_test = request.args.get("show_test", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    try:
        (
            props,
            sections,
            stats,
            pipeline,
            needs_attention_items,
            chase_confirmation_items,
        ) = _build_live_dashboard_data(show_test_properties=show_test)
    except Exception as e:
        return f"<h2>Error fetching live data</h2><pre>{e}</pre>", 500

    props_json = (
        props if show_test else [p for p in props if not p.get("_is_test")]
    )
    html = render_template_string(
        DASHBOARD_HTML + CRM_OVERRIDE_JS,
        sections=sections,
        needs_attention_items=needs_attention_items,
        chase_confirmation_items=chase_confirmation_items,
        stats=stats,
        pipeline=pipeline,
        properties_json=json.dumps(props_json, default=str),
        detail_base_url="/crm/property",
        leaderboard_tabs=LEADERBOARD_TABS,
        show_test_properties=show_test,
        test_props_toggle_base="/crm",
    )
    return html


@crm_bp.route("/crm/property/<prop_id>")
def crm_property_detail(prop_id):
    """Full-page detail view for a single CRM property."""
    from routes.dashboard import _build_live_dashboard_data

    show_test = request.args.get("show_test", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    try:
        props, _, _, _, _, _ = _build_live_dashboard_data(
            show_test_properties=show_test
        )
    except Exception as e:
        return f"<h2>Error fetching live data</h2><pre>{e}</pre>", 500

    prop = None
    for p in props:
        if str(p.get("id")) == str(prop_id):
            prop = p
            break
    if not prop:
        return "<h2>Property not found</h2>", 404

    _enrich_crm_detail_view(prop, date.today())
    return render_template("crm_property_detail.html", p=prop)


@crm_bp.route("/api/crm/notes/<prop_id>", methods=["POST"])
def save_crm_note(prop_id):
    """Save a NUVU note back to the EATOC CRM."""
    data = request.get_json(force=True)
    nuvu_notes = data.get("nuvu_notes", "")
    try:
        resp = http_requests.patch(
            f"{EATOC_API_URL}/{prop_id}",
            headers={
                "x-api-key": NUVU_API_KEY,
                "Content-Type": "application/json",
            },
            json={"nuvu_notes": nuvu_notes},
            timeout=10,
        )
        resp.raise_for_status()
        return jsonify({"ok": True})
    except http_requests.RequestException as e:
        return jsonify({"error": str(e)}), 502

