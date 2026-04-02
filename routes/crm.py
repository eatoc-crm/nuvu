import json
import os
from datetime import datetime

import requests as http_requests
from flask import Blueprint, jsonify, render_template_string, request

crm_bp = Blueprint("crm", __name__)


# ─────────────────────────────────────────────────────────────
#  EATOC CRM LIVE PROPERTY CARDS
# ─────────────────────────────────────────────────────────────

EATOC_API_URL = "https://etoc-crm-production-688d.up.railway.app/api/nuvu/properties"
NUVU_API_KEY = os.environ.get("NUVU_API_KEY", "dbe-nuvu-2026")


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
    "exchanged": "on-track",
    "development": "on-track",
    "problem": "at-risk",
    "incomplete_chain": "stalled",
}
STATUS_LABELS = {"on-track": "ON TRACK", "at-risk": "AT RISK", "stalled": "STALLED"}

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
            "label": "Mortgage Offer Received",
            "field": "mortgage_offered",
            "done": bool(r.get("mortgage_offered")),
            "date": r.get("mortgage_offered") or "",
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


def _map_live_properties():
    """Fetch from EATOC API and map to the dict shape DASHBOARD_HTML expects."""
    raw, error = fetch_eatoc_properties()
    if error:
        return [], error
    mapped = []
    for i, r in enumerate(raw):
        status = STATUS_MAP.get(r.get("status", "active"), "on-track")
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
                "enquiries_raised": r.get("enquiries_raised"),
                "enquiries_answered": r.get("enquiries_answered"),
                "mortgage_offered": r.get("mortgage_offered"),
                "survey_booked": r.get("survey_booked"),
                "survey_complete": r.get("survey_complete"),
                "exchange_target": r.get("exchange_date"),
                "completion_target": r.get("completion_date"),
                "chain": "\u2014",
                "alert": r.get("notes") if r.get("status") == "problem" else None,
                "next_action": r.get("notes") or "\u2014",
                "notes": r.get("notes") or "",
                "nuvu_notes": r.get("nuvu_notes") or "",
                "buyer_solicitor_notes": r.get("buyer_solicitor_notes") or "",
                "seller_solicitor_notes": r.get("seller_solicitor_notes") or "",
                "image_bg": FALLBACK_GRADIENTS[i % len(FALLBACK_GRADIENTS)],
                "image_url": r.get("image_url") or "",
                # extra fields for detail page
                "_progression_id": r.get("id"),
                "_raw_status": r.get("status"),
                "_sewage_type": r.get("sewage_type") or "\u2014",
                "_mortgage_broker": r.get("mortgage_broker") or "\u2014",
                "_surveyor": r.get("surveyor") or "\u2014",
                "_buyer_email": r.get("buyer_email") or "\u2014",
                "_vendor_name": r.get("vendor_name") or "\u2014",
                "_vendor_phone": r.get("vendor_phone") or "\u2014",
                "_vendor_email": r.get("vendor_email") or "\u2014",
                "_nuvu_notes": r.get("nuvu_notes") or "\u2014",
                "_staff_initials": r.get("staff_initials") or "\u2014",
                "_fee": r.get("fee"),
                "_invoice_status": r.get("invoice_status") or "\u2014",
                "_beds": r.get("beds"),
                "_baths": r.get("baths"),
                "_property_type": r.get("property_type") or "\u2014",
            }
        )
    return mapped, None


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

  /* Update stats bar labels for CRM view */
  var labels = {
    "stat-on-track": "Exchanged",
    "stat-at-risk": "Problems",
    "stat-action": "Inc. Chain"
  };
  for (var id in labels) {
    var el = document.getElementById(id);
    if (el) {
      var lbl = el.querySelector(".hs-lbl");
      if (lbl) lbl.textContent = labels[id];
    }
  }
})();
</script>
"""


DETAIL_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ p.address }} — NUVU</title>
<link rel="icon" href="/static/logo.png">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --navy:#0f1b2d;--navy-lt:#162236;--navy-md:#1c2e4a;--navy-card:#182842;
  --lime:#c4e233;--lime-dk:#a3bf1a;
  --red:#e25555;--red-chip:#e84545;
  --amber:#e88a3a;--amber-chip:#e8873a;
  --green:#27ae60;--green-chip:#2fa868;
  --blue:#3b82f6;
  --white:#ffffff;--off-white:#f4f6f9;
  --txt:#1e293b;--txt-mid:#475569;--txt-light:#94a3b8;
  --card-shadow:0 2px 12px rgba(0,0,0,.08);
  --t:.22s ease;
}
html{font-size:15px;scroll-behavior:smooth}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--off-white);color:var(--txt);min-height:100vh}

/* back bar */
.back-bar{background:var(--navy);padding:16px 32px;display:flex;align-items:center;gap:12px}
.back-btn{
  display:inline-flex;align-items:center;gap:8px;
  color:var(--lime);font-size:.88rem;font-weight:700;text-decoration:none;
  padding:8px 18px;border-radius:8px;border:1px solid rgba(196,226,51,.3);
  transition:all var(--t);
}
.back-btn:hover{background:rgba(196,226,51,.12);border-color:var(--lime)}

/* hero photo */
.detail-hero{position:relative;width:100%;height:320px;overflow:hidden;background:var(--navy)}
.detail-hero img{width:100%;height:100%;object-fit:cover}
.detail-hero-overlay{
  position:absolute;bottom:0;left:0;right:0;
  background:linear-gradient(transparent,rgba(15,27,45,.85));
  padding:40px 32px 24px;
}
.detail-hero-overlay h1{font-size:1.6rem;font-weight:800;color:var(--white);margin-bottom:4px}
.detail-hero-overlay .detail-loc{font-size:.88rem;color:rgba(255,255,255,.6)}
.detail-hero-overlay .detail-price{font-size:1.4rem;font-weight:900;color:var(--lime);margin-top:8px}
.detail-chip{
  position:absolute;top:20px;right:24px;
  padding:6px 16px;border-radius:6px;
  font-size:.72rem;font-weight:800;letter-spacing:.8px;color:var(--white);
}
.chip-stalled{background:var(--red-chip)}
.chip-at-risk{background:var(--amber-chip)}
.chip-on-track{background:var(--green-chip)}

/* content */
.detail-content{max-width:900px;margin:0 auto;padding:32px}

/* progress */
.detail-prog{margin-bottom:28px}
.detail-prog-bar{width:100%;height:10px;border-radius:5px;background:#e8ecf1;overflow:hidden}
.detail-prog-fill{height:100%;border-radius:5px}
.detail-prog-fill.clr-stalled{background:var(--red)}
.detail-prog-fill.clr-at-risk{background:var(--amber)}
.detail-prog-fill.clr-on-track{background:var(--green)}
.detail-prog-labels{display:flex;justify-content:space-between;font-size:.72rem;color:var(--txt-light);margin-top:6px}

/* cards */
.detail-card{
  background:var(--white);border-radius:14px;border:1px solid #e8ecf1;
  box-shadow:var(--card-shadow);padding:24px;margin-bottom:20px;
}
.detail-card h3{font-size:.92rem;font-weight:700;color:var(--txt);margin-bottom:14px;display:flex;align-items:center;gap:8px}

/* milestones */
.ms-list{display:flex;flex-direction:column}
.ms-item{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #f1f5f9;font-size:.85rem}
.ms-item:last-child{border-bottom:none}
.ms-ic{width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:.65rem}
.ms-ic.done{background:var(--green);color:#fff}
.ms-ic.pending{background:#f1f5f9;border:2px solid #cbd5e1;color:transparent}
.ms-lb{color:var(--txt);flex:1}
.ms-lb.done-lb{color:var(--txt-light);text-decoration:line-through}
.ms-pending-lb{color:var(--txt-light);font-style:italic}
.ms-date{margin-left:auto;font-size:.78rem;color:var(--txt-light);font-weight:600;white-space:nowrap}
.ms-edit-btn{background:none;border:1px solid #d1d5db;border-radius:5px;padding:2px 8px;font-size:.65rem;color:var(--txt-mid);cursor:pointer;transition:all var(--t);flex-shrink:0}
.ms-edit-btn:hover{border-color:var(--green);color:var(--green)}
.ms-edit-form{display:flex;align-items:center;gap:6px;margin-left:auto;flex-shrink:0}
.ms-edit-form input[type=date]{font-size:.72rem;padding:2px 6px;border:1px solid #d1d5db;border-radius:5px;color:var(--txt)}
.ms-edit-form button{padding:2px 8px;border-radius:5px;font-size:.65rem;font-weight:600;cursor:pointer;border:none}
.ms-save-btn{background:var(--green);color:#fff}
.ms-cancel-btn{background:#f1f5f9;color:var(--txt-mid)}
.note-block{background:#f8fafc;border:1px solid #e8ecf1;border-radius:8px;padding:10px 14px;margin-bottom:8px}
.note-block-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.note-block-lbl{font-size:.68rem;text-transform:uppercase;letter-spacing:.8px;color:var(--txt-light);font-weight:600}
.note-edit-btn{background:none;border:1px solid #d1d5db;border-radius:5px;padding:2px 10px;font-size:.65rem;color:var(--txt-mid);cursor:pointer;transition:all var(--t)}
.note-edit-btn:hover{border-color:var(--green);color:var(--green)}
.note-block-txt{font-size:.82rem;line-height:1.5;color:var(--txt);white-space:pre-wrap}
.note-block-txt.empty{color:var(--txt-light);font-style:italic}
.note-textarea{width:100%;min-height:60px;font-size:.82rem;font-family:inherit;line-height:1.5;border:1px solid #d1d5db;border-radius:6px;padding:8px 10px;resize:vertical;color:var(--txt)}
.note-textarea:focus{outline:none;border-color:var(--green)}
.note-actions{display:flex;gap:6px;margin-top:6px}
.note-save-btn{background:var(--green);color:#fff;border:none;border-radius:5px;padding:4px 14px;font-size:.72rem;font-weight:600;cursor:pointer}
.note-cancel-btn{background:#f1f5f9;color:var(--txt-mid);border:none;border-radius:5px;padding:4px 14px;font-size:.72rem;cursor:pointer}

/* alert box */
.alert-box{
  padding:14px 18px;border-radius:10px;margin-bottom:20px;
  font-size:.88rem;line-height:1.5;display:flex;gap:10px;align-items:flex-start;
}
.alert-red{background:#fef2f2;color:#b91c1c;border:1px solid #fecaca}
.alert-amber{background:#fffbeb;color:#92400e;border:1px solid #fde68a}
.alert-green{background:#f0fdf4;color:#166534;border:1px solid #bbf7d0}

/* next action */
.next-box{background:#f8fafc;border:1px solid #e8ecf1;border-radius:10px;padding:14px 18px;margin-bottom:20px}
.next-lbl{font-size:.68rem;text-transform:uppercase;letter-spacing:1.2px;color:var(--green);font-weight:700;margin-bottom:4px}
.next-txt{font-size:.88rem;color:var(--txt);line-height:1.5}

/* detail grid */
.det-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 20px}
.d-r{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f1f5f9;font-size:.85rem}
.d-r:last-child{border-bottom:none}
.d-l{color:var(--txt-light)}
.d-v{font-weight:600;color:var(--txt);text-align:right}

/* two col layout */
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:20px}

@media(max-width:700px){
  .detail-hero{height:220px}
  .detail-content{padding:20px 16px}
  .det-grid,.two-col{grid-template-columns:1fr}
  .back-bar{padding:12px 16px}
}
</style>
</head>
<body>

<div class="back-bar">
  <a class="back-btn" href="/crm">&larr; Back to Dashboard</a>
</div>

<div class="detail-hero">
  {% if p.image_url %}
  <img src="{{ p.image_url }}" alt="{{ p.address }}" style="background:{{ p.image_bg }}">
  {% else %}
  <div style="width:100%;height:100%;background:{{ p.image_bg }}"></div>
  {% endif %}
  <span class="detail-chip chip-{{ p.status }}">{{ p.status_label }}</span>
  <div class="detail-hero-overlay">
    <h1>{{ p.address }}</h1>
    <div class="detail-loc">{{ p.location }}{% if p._property_type and p._property_type != '\u2014' %} &bull; {{ p._property_type }}{% endif %}{% if p._beds %} &bull; {{ p._beds }} bed{% endif %}{% if p._baths %} &bull; {{ p._baths }} bath{% endif %}</div>
    {% if p.price %}<div class="detail-price">&pound;{{ "{:,.0f}".format(p.price) }}</div>{% endif %}
  </div>
</div>

<div class="detail-content">

  <!-- Progress bar -->
  <div class="detail-prog">
    <div class="detail-prog-bar"><div class="detail-prog-fill clr-{{ p.status }}" style="width:{{ p.progress }}%"></div></div>
    <div class="detail-prog-labels"><span>Offer Accepted</span><span>{{ p.progress }}% complete</span><span>Completion</span></div>
  </div>

  <!-- Alert -->
  {% if p.alert %}
  <div class="alert-box {% if p.status == 'stalled' %}alert-red{% elif p.status == 'at-risk' %}alert-amber{% else %}alert-green{% endif %}">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
    <span>{{ p.alert }}</span>
  </div>
  {% endif %}

  <!-- Next Action -->
  <div class="next-box">
    <div class="next-lbl">Next Action</div>
    <div class="next-txt">{{ p.next_action }}</div>
  </div>

  <div class="two-col">
    <!-- Milestones -->
    <div class="detail-card">
      <h3>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>
        Milestones
      </h3>
      <div class="ms-list">
        {% for ms in p.milestones %}
        <div class="ms-item" id="dms-row-{{ loop.index0 }}">
          <span class="ms-ic {{ 'done' if ms.done else 'pending' }}">{% if ms.done %}&#x2713;{% endif %}</span>
          <span class="ms-lb {{ 'done-lb' if ms.done else 'ms-pending-lb' }}">{{ ms.label }}</span>
          {% if ms.date %}<span class="ms-date">{{ ms.date }}</span>{% endif %}
          {% if p._progression_id %}<button class="ms-edit-btn" data-field="{{ ms.field }}" data-idx="{{ loop.index0 }}">Edit</button>{% endif %}
        </div>
        {% endfor %}
      </div>
    </div>

    <!-- Contacts & details -->
    <div class="detail-card">
      <h3>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--blue)" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        Contacts &amp; Details
      </h3>
      <div class="det-grid">
        <div class="d-r"><span class="d-l">Buyer</span><span class="d-v">{{ p.buyer }}</span></div>
        <div class="d-r"><span class="d-l">Buyer Phone</span><span class="d-v">{{ p.buyer_phone }}</span></div>
        <div class="d-r"><span class="d-l">Buyer Solicitor</span><span class="d-v">{{ p.buyer_solicitor }}</span></div>
        <div class="d-r"><span class="d-l">Vendor</span><span class="d-v">{{ p._vendor_name }}</span></div>
        <div class="d-r"><span class="d-l">Vendor Phone</span><span class="d-v">{{ p._vendor_phone }}</span></div>
        <div class="d-r"><span class="d-l">Vendor Solicitor</span><span class="d-v">{{ p.seller_solicitor }}</span></div>
        <div class="d-r"><span class="d-l">Mortgage Broker</span><span class="d-v">{{ p._mortgage_broker }}</span></div>
        <div class="d-r"><span class="d-l">Surveyor</span><span class="d-v">{{ p._surveyor }}</span></div>
        <div class="d-r"><span class="d-l">Sewage Type</span><span class="d-v">{{ p._sewage_type }}</span></div>
        <div class="d-r"><span class="d-l">Staff</span><span class="d-v">{{ p._staff_initials }}</span></div>
      </div>
    </div>
  </div>

  <!-- Dates & timeline -->
  <div class="detail-card">
    <h3>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--amber)" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
      Timeline
    </h3>
    <div class="det-grid">
      <div class="d-r"><span class="d-l">Offer Accepted</span><span class="d-v">{{ p.offer_date or '\u2014' }}</span></div>
      <div class="d-r"><span class="d-l">Memo Sent</span><span class="d-v">{{ p.memo_sent or '\u2014' }}</span></div>
      <div class="d-r"><span class="d-l">Exchange Date</span><span class="d-v">{{ p.exchange_target or '\u2014' }}</span></div>
      <div class="d-r"><span class="d-l">Completion Date</span><span class="d-v">{{ p.completion_target or '\u2014' }}</span></div>
      <div class="d-r"><span class="d-l">Fee</span><span class="d-v">&pound;{{ "{:,.2f}".format(p._fee) if p._fee else '\u2014' }}</span></div>
      <div class="d-r"><span class="d-l">Invoice Status</span><span class="d-v">{{ p._invoice_status }}</span></div>
    </div>
  </div>

  <!-- Notes -->
  <div class="detail-card">
    <h3>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--txt-mid)" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
      Notes
    </h3>
    <div id="d-notes-list">
      {% set note_fields = [("notes","General Notes"),("nuvu_notes","NUVU Notes"),("buyer_solicitor_notes","Buyer Solicitor Notes"),("seller_solicitor_notes","Seller Solicitor Notes")] %}
      {% for key, label in note_fields %}
      <div class="note-block" id="d-note-blk-{{ loop.index0 }}">
        <div class="note-block-hdr"><span class="note-block-lbl">{{ label }}</span>{% if p._progression_id %}<button class="note-edit-btn" data-nkey="{{ key }}" data-nidx="{{ loop.index0 }}">Edit</button>{% endif %}</div>
        <div class="note-block-txt{{ ' empty' if not p[key] }}" id="d-note-txt-{{ loop.index0 }}">{{ p[key] or 'No notes yet' }}</div>
      </div>
      {% endfor %}
    </div>
  </div>

</div>

<script>
(function(){
  var progId = "{{ p._progression_id or '' }}";
  if (!progId) return;

  function patchField(field, value, onSuccess) {
    var body = {}; body[field] = value;
    fetch("/api/progression/" + progId, {
      method: "PATCH",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body)
    }).then(function(r){ return r.json(); }).then(function(j){
      if (j.ok) { if (onSuccess) onSuccess(); }
      else { alert("Save failed: " + (j.error || "Unknown error")); }
    }).catch(function(e){ alert("Network error: " + e.message); });
  }

  /* milestone edit */
  var msBtns = document.querySelectorAll(".ms-edit-btn");
  for (var i = 0; i < msBtns.length; i++) {
    (function(btn){
      btn.onclick = function() {
        var field = btn.getAttribute("data-field");
        var idx = btn.getAttribute("data-idx");
        var row = document.getElementById("dms-row-" + idx);
        var label = row.querySelector(".ms-lb").textContent;
        var dateEl = row.querySelector(".ms-date");
        var curVal = dateEl ? dateEl.textContent : "";
        row.innerHTML = '<span class="ms-ic pending"></span><span class="ms-lb">' + label + '</span>' +
          '<div class="ms-edit-form"><input type="date" id="dms-date-' + idx + '" value="' + curVal + '">' +
          '<button class="ms-save-btn" id="dms-sv-' + idx + '">Save</button>' +
          '<button class="ms-cancel-btn" id="dms-cn-' + idx + '">Cancel</button></div>';
        document.getElementById("dms-sv-" + idx).onclick = function() {
          var val = document.getElementById("dms-date-" + idx).value;
          patchField(field, val, function(){ location.reload(); });
        };
        document.getElementById("dms-cn-" + idx).onclick = function() { location.reload(); };
      };
    })(msBtns[i]);
  }

  /* note edit */
  var noteBtns = document.querySelectorAll(".note-edit-btn");
  for (var n = 0; n < noteBtns.length; n++) {
    (function(btn){
      btn.onclick = function() {
        var nkey = btn.getAttribute("data-nkey");
        var nidx = btn.getAttribute("data-nidx");
        var blk = document.getElementById("d-note-blk-" + nidx);
        var txtEl = document.getElementById("d-note-txt-" + nidx);
        var curVal = txtEl.classList.contains("empty") ? "" : txtEl.textContent;
        var label = blk.querySelector(".note-block-lbl").textContent;
        blk.innerHTML = '<div class="note-block-hdr"><span class="note-block-lbl">' + label + '</span></div>' +
          '<textarea class="note-textarea" id="d-note-ta-' + nidx + '">' + curVal + '</textarea>' +
          '<div class="note-actions"><button class="note-save-btn" id="d-note-sv-' + nidx + '">Save</button>' +
          '<button class="note-cancel-btn" id="d-note-cn-' + nidx + '">Cancel</button></div>';
        document.getElementById("d-note-sv-" + nidx).onclick = function() {
          var val = document.getElementById("d-note-ta-" + nidx).value;
          patchField(nkey, val, function(){ location.reload(); });
        };
        document.getElementById("d-note-cn-" + nidx).onclick = function() { location.reload(); };
      };
    })(noteBtns[n]);
  }
})();
</script>

</body>
</html>"""


@crm_bp.route("/crm")
def crm_dashboard():
    """Live CRM dashboard using NUVU design with real property data."""
    from app import DASHBOARD_HTML  # shared template constant (dashboard extraction pending)

    props, error = _map_live_properties()
    if error:
        return f"<h2>Error fetching live data</h2><pre>{error}</pre>", 500

    stats = _crm_stats(props)
    sections = _crm_sections(props)

    pipeline = {
        "this_week": {
            "count": stats["on_track"],
            "value": stats["property_pipeline"],
            "fee": stats["fee_pipeline"],
            "confidence": 90,
        },
        "this_month": {
            "count": stats["active"],
            "value": stats["property_pipeline"],
            "fee": stats["fee_pipeline"],
            "confidence": 75,
        },
        "this_quarter": {
            "count": len(props),
            "value": stats["property_pipeline"],
            "fee": stats["fee_pipeline"],
            "confidence": 60,
        },
    }

    html = render_template_string(
        DASHBOARD_HTML + CRM_OVERRIDE_JS,
        sections=sections,
        stats=stats,
        pipeline=pipeline,
        properties_json=json.dumps(props),
        detail_base_url="/crm/property",
    )
    return html


@crm_bp.route("/crm/property/<prop_id>")
def crm_property_detail(prop_id):
    """Full-page detail view for a single CRM property."""
    props, error = _map_live_properties()
    if error:
        return f"<h2>Error fetching live data</h2><pre>{error}</pre>", 500

    prop = None
    for p in props:
        if p["id"] == prop_id:
            prop = p
            break
    if not prop:
        return "<h2>Property not found</h2>", 404

    return render_template_string(DETAIL_HTML, p=prop)


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

