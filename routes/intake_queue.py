"""
NUVU Intake Queue — routes/intake_queue.py

GET  /intake-queue          — shows awaiting-approval and blocked cards
POST /intake-queue/approve/<property_address>  — human approval action
"""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

from flask import Blueprint, flash, redirect, render_template_string, request, session

from db_supabase import supabase_for_backend
from utils.events import emit_event
from utils.field_labels import labels_for_fields

intake_queue_bp = Blueprint("intake_queue", __name__)

# ─────────────────────────────────────────────────────────────
#  TEMPLATE
# ─────────────────────────────────────────────────────────────

INTAKE_QUEUE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NUVU — Intake Queue</title>
<link rel="icon" href="/static/logo.png">
<style>
/* ═══ RESET ═══════════════════════════════════════════════ */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --navy:#1B3A5C;--claret:#962D3E;--sage:#4A7C6F;--amber:#D4940A;
  --nuvu-green:#C5D93A;--olive:#2A3A0C;
  --page-warm:#F5F3EF;--stone:#8B8680;--stone-dark:#6B6560;
  --off-white:#FAFAFA;--white:#FFFFFF;--border:#E8E8E8;
  --txt:#1A1A1A;--txt-secondary:#777777;
  --amber-light:#FFF8E1;--amber-border:#F59E0B;
  --green-light:#F0FAF4;--green-border:#22C55E;
  --t:background-color .15s ease;
}
html{font-size:15px;scroll-behavior:smooth}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--page-warm);color:var(--txt);min-height:100vh;font-weight:400}

/* ═══ TOPBAR ══════════════════════════════════════════════ */
.topbar{
  background:var(--navy);padding:0 28px;
  display:flex;align-items:center;justify-content:space-between;
  height:56px;position:sticky;top:0;z-index:200;
  border-bottom:1px solid rgba(255,255,255,.08);
}
.topbar-logo{display:flex;align-items:center;gap:10px;text-decoration:none}
.topbar-logo img{width:32px;height:32px;border-radius:50%}
.topbar-logo span{font-size:1.1rem;font-weight:700;color:var(--white);letter-spacing:6px}
.topbar-nav{display:flex;align-items:center;gap:4px}
.topbar-nav a{
  color:rgba(255,255,255,.75);text-decoration:none;font-size:13px;font-weight:500;
  padding:6px 12px;border-radius:4px;transition:var(--t);position:relative;
}
.topbar-nav a:hover{color:var(--white);background:rgba(255,255,255,.08)}
.topbar-nav a.active{color:var(--white);background:rgba(255,255,255,.12)}
.topbar-nav a .badge{
  display:inline-flex;align-items:center;justify-content:center;
  min-width:18px;height:18px;padding:0 5px;
  background:var(--claret);color:var(--white);
  border-radius:9px;font-size:11px;font-weight:700;
  margin-left:6px;line-height:1;
}
.topbar-user{color:rgba(255,255,255,.6);font-size:12px}

/* ═══ PAGE HEADER ═════════════════════════════════════════ */
.page-header{
  background:var(--navy);padding:28px 32px 24px;
  border-bottom:1px solid rgba(255,255,255,.06);
}
.page-header-inner{max-width:1280px;margin:0 auto}
.page-title{font-size:1.5rem;font-weight:700;color:var(--white);letter-spacing:-.02em}
.page-sub{font-size:13px;color:rgba(255,255,255,.6);margin-top:6px;line-height:1.45}

/* ═══ MAIN ════════════════════════════════════════════════ */
.main{max-width:1280px;margin:0 auto;padding:32px 24px 64px}

/* ═══ FLASH ═══════════════════════════════════════════════ */
.flash-list{list-style:none;margin-bottom:20px}
.flash-msg{
  padding:12px 18px;border-radius:6px;font-size:14px;font-weight:500;
  background:#f0fdf4;color:#166534;border:1px solid #bbf7d0;
}
.flash-msg.error{background:#fef2f2;color:#b91c1c;border-color:#fecaca}

/* ═══ SECTION HEADERS ═════════════════════════════════════ */
.section-header{
  display:flex;align-items:baseline;gap:12px;
  margin-bottom:16px;padding-bottom:10px;
  border-bottom:2px solid var(--border);
}
.section-title{font-size:1.05rem;font-weight:700;color:var(--navy)}
.section-count{
  font-size:12px;font-weight:600;padding:2px 8px;border-radius:10px;
}
.section-count.ready{background:#dcfce7;color:#15803d}
.section-count.blocked{background:#fef3c7;color:#92400e}
.section-empty{
  color:var(--stone);font-size:14px;font-style:italic;
  padding:20px 0;text-align:center;
}

/* ═══ CARD GRID ═══════════════════════════════════════════ */
.card-grid{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(380px,1fr));
  gap:20px;margin-bottom:40px;
}

/* ═══ INTAKE CARD ═════════════════════════════════════════ */
.intake-card{
  background:var(--white);border-radius:8px;
  border:1px solid var(--border);
  box-shadow:0 1px 4px rgba(0,0,0,.04);
  overflow:hidden;
}
.intake-card--ready{border-left:4px solid var(--green-border)}
.intake-card--blocked{border-left:4px solid var(--amber-border)}

.card-top{
  padding:18px 20px 14px;
  border-bottom:1px solid var(--border);
}
.card-address{
  font-size:15px;font-weight:700;color:var(--navy);
  line-height:1.3;margin-bottom:8px;
}
.card-meta{
  display:flex;flex-wrap:wrap;gap:6px;
}
.meta-chip{
  font-size:11px;font-weight:600;padding:3px 9px;border-radius:10px;
  background:#eef2f7;color:var(--navy);
}
.meta-chip.ready{background:#dcfce7;color:#15803d}
.meta-chip.blocked{background:#fef3c7;color:#92400e}
.meta-chip.chain{background:#f0f4ff;color:#3730a3}

.card-body{padding:14px 20px}
.card-row{
  display:flex;justify-content:space-between;align-items:baseline;
  padding:4px 0;border-bottom:1px solid #f3f4f6;font-size:13px;
}
.card-row:last-child{border-bottom:none}
.card-label{color:var(--stone);font-weight:500;min-width:110px}
.card-value{color:var(--txt);font-weight:500;text-align:right;max-width:240px;word-break:break-word}

/* Missing fields list */
.missing-list{
  margin:10px 20px 0;padding:10px 14px;
  background:var(--amber-light);border:1px solid #fde68a;border-radius:6px;
  font-size:12px;color:#92400e;
}
.missing-list strong{display:block;margin-bottom:4px;font-size:12px}
.missing-list ul{padding-left:16px}
.missing-list li{margin-bottom:2px;line-height:1.4}

/* Failed tiers */
.failed-tiers{
  display:flex;flex-wrap:wrap;gap:4px;margin:8px 20px 0;
}
.tier-chip{
  font-size:11px;font-weight:600;padding:3px 8px;border-radius:4px;
  background:#fef3c7;color:#92400e;border:1px solid #fde68a;
}

/* Time in queue */
.time-in-queue{
  padding:8px 20px 10px;font-size:12px;color:var(--stone);
  border-top:1px solid #f3f4f6;
}

/* Approve button */
.card-actions{padding:14px 20px 18px;border-top:1px solid var(--border)}
.btn-approve{
  display:inline-flex;align-items:center;gap:8px;
  background:var(--navy);color:var(--white);
  border:none;border-radius:6px;
  padding:10px 20px;font-size:14px;font-weight:600;
  cursor:pointer;transition:background .15s;width:100%;justify-content:center;
}
.btn-approve:hover{background:#2a4a6e}
.approve-note{
  font-size:11px;color:var(--stone);margin-top:8px;line-height:1.4;text-align:center;
}
</style>
</head>
<body>

<!-- ═══ TOPBAR ══════════════════════════════════════════════ -->
<div class="topbar">
  <a class="topbar-logo" href="/">
    <img src="/static/logo.png" alt="NUVU">
    <span>NUVU</span>
  </a>
  <nav class="topbar-nav">
    <a href="/">Dashboard</a>
    <a href="/intake-queue" class="active">
      Intake Queue
      {% if ready_count > 0 %}
      <span class="badge">{{ ready_count }}</span>
      {% endif %}
    </a>
  </nav>
  <div class="topbar-user">{{ current_user }}</div>
</div>

<!-- ═══ PAGE HEADER ═════════════════════════════════════════ -->
<div class="page-header">
  <div class="page-header-inner">
    <div class="page-title">Intake Queue</div>
    <div class="page-sub">
      Properties awaiting human approval before the welcome email is sent, and
      those blocked due to missing data. The completeness gate re-runs every 15
      minutes — missing data entered in EATOC will clear automatically.
    </div>
  </div>
</div>

<!-- ═══ MAIN ════════════════════════════════════════════════ -->
<div class="main">

  {% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
  <ul class="flash-list">
    {% for category, message in messages %}
    <li class="flash-msg {{ 'error' if category == 'error' else '' }}">{{ message }}</li>
    {% endfor %}
  </ul>
  {% endif %}
  {% endwith %}

  <!-- Section A: Awaiting Approval -->
  <div class="section-header">
    <div class="section-title">Awaiting Approval</div>
    <span class="section-count ready">{{ ready_items|length }} propert{{ 'y' if ready_items|length == 1 else 'ies' }}</span>
  </div>

  {% if ready_items %}
  <div class="card-grid">
    {% for item in ready_items %}
    <div class="intake-card intake-card--ready">
      <div class="card-top">
        <div class="card-address">{{ item.property_address }}</div>
        <div class="card-meta">
          <span class="meta-chip ready">All checks passed</span>
          <span class="meta-chip chain">Chain-free</span>
        </div>
      </div>
      <div class="card-body">
        {% if item.sale_price %}
        <div class="card-row">
          <span class="card-label">Sale price</span>
          <span class="card-value">&pound;{{ "{:,.0f}".format(item.sale_price) }}</span>
        </div>
        {% endif %}
        {% if item.buyer_name %}
        <div class="card-row">
          <span class="card-label">Buyer</span>
          <span class="card-value">{{ item.buyer_name }}</span>
        </div>
        {% endif %}
        {% if item.vendor_name %}
        <div class="card-row">
          <span class="card-label">Seller</span>
          <span class="card-value">{{ item.vendor_name }}</span>
        </div>
        {% endif %}
        {% if item.buyer_solicitor_firm %}
        <div class="card-row">
          <span class="card-label">Buyer's solicitor</span>
          <span class="card-value">{{ item.buyer_solicitor_firm }}</span>
        </div>
        {% endif %}
        {% if item.seller_solicitor_firm %}
        <div class="card-row">
          <span class="card-label">Seller's solicitor</span>
          <span class="card-value">{{ item.seller_solicitor_firm }}</span>
        </div>
        {% endif %}
        {% if item.completion_target %}
        <div class="card-row">
          <span class="card-label">Completion target</span>
          <span class="card-value">{{ item.completion_target }}</span>
        </div>
        {% endif %}
        {% if item.special_conditions %}
        <div class="card-row">
          <span class="card-label">Special conditions</span>
          <span class="card-value">{{ item.special_conditions }}</span>
        </div>
        {% endif %}
      </div>
      <div class="time-in-queue">In queue {{ item._time_in_queue }}</div>
      <div class="card-actions">
        <form method="POST" action="/intake-queue/approve/{{ item.property_address | urlencode }}">
          <button type="submit" class="btn-approve">
            Approve &amp; Send Welcome Email
          </button>
        </form>
        <div class="approve-note">
          By approving you confirm all details are accurate.
          The welcome email will send immediately.
        </div>
      </div>
    </div>
    {% endfor %}
  </div>
  {% else %}
  <p class="section-empty">No properties awaiting approval.</p>
  {% endif %}

  <!-- Section B: Blocked -->
  <div class="section-header" style="margin-top:16px">
    <div class="section-title">Blocked — Data Incomplete</div>
    <span class="section-count blocked">{{ blocked_items|length }} propert{{ 'y' if blocked_items|length == 1 else 'ies' }}</span>
  </div>

  {% if blocked_items %}
  <div class="card-grid">
    {% for item in blocked_items %}
    <div class="intake-card intake-card--blocked">
      <div class="card-top">
        <div class="card-address">{{ item.property_address }}</div>
        <div class="card-meta">
          <span class="meta-chip blocked">Data incomplete</span>
          {% if not item.tier_1a_pass %}<span class="meta-chip">Tier 1A</span>{% endif %}
          {% if not item.tier_1b_pass %}<span class="meta-chip">Tier 1B</span>{% endif %}
          {% if not item.tier_1c_pass %}<span class="meta-chip">Tier 1C</span>{% endif %}
          {% if not item.tier_1d_pass %}<span class="meta-chip">Tier 1D</span>{% endif %}
        </div>
      </div>
      {% if item.missing_fields %}
      <div class="missing-list">
        <strong>Missing fields:</strong>
        <ul>
          {% for label in item.missing_field_labels %}
          <li>{{ label }}</li>
          {% endfor %}
        </ul>
      </div>
      {% endif %}
      <div class="time-in-queue" style="margin-top:10px">Blocked {{ item._time_in_queue }}</div>
    </div>
    {% endfor %}
  </div>
  {% else %}
  <p class="section-empty">No blocked properties.</p>
  {% endif %}

</div><!-- /main -->
</body>
</html>"""


# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────

def _time_ago(dt_str: str | None) -> str:
    """Human-readable 'X days ago' from an ISO timestamp string."""
    if not dt_str:
        return "unknown time"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        days = delta.days
        if days == 0:
            hours = delta.seconds // 3600
            if hours == 0:
                mins = delta.seconds // 60
                return f"{mins} minute{'s' if mins != 1 else ''} ago"
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        return f"{days} day{'s' if days != 1 else ''} ago"
    except Exception:
        return "unknown time"


def _enrich_items(items: list[dict], pipeline_map: dict) -> list[dict]:
    """Merge pipeline data into intake_queue items for display."""
    for item in items:
        addr = item.get("property_address", "")
        prop = pipeline_map.get(addr, {})
        item["buyer_name"]           = prop.get("buyer_name", "")
        item["vendor_name"]          = prop.get("vendor_name", "")
        item["buyer_solicitor_firm"] = prop.get("buyer_solicitor_firm") or prop.get("buyers_solicitor", "")
        item["seller_solicitor_firm"]= prop.get("seller_solicitor_firm") or prop.get("vendors_solicitor", "")
        item["_time_in_queue"]       = _time_ago(item.get("created_at"))
        item["missing_field_labels"] = labels_for_fields(item.get("missing_fields"))
    return items


# ─────────────────────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────────────────────

@intake_queue_bp.route("/intake-queue")
def intake_queue_page():
    client = supabase_for_backend()

    # Fetch all non-approved, non-rejected records ordered oldest first
    result = (
        client.table("intake_queue")
        .select("*")
        .in_("gate_status", ["ready", "blocked"])
        .order("created_at", desc=False)
        .execute()
    )
    all_items = result.data or []

    ready_items   = [i for i in all_items if i["gate_status"] == "ready"]
    blocked_items = [i for i in all_items if i["gate_status"] == "blocked"]

    # Fetch pipeline data for name / solicitor enrichment
    try:
        pipeline_result = client.table("sales_pipeline").select("*").execute()
        pipeline_map = {r["property_address"]: r for r in (pipeline_result.data or []) if r.get("property_address")}
    except Exception:
        pipeline_map = {}

    ready_items   = _enrich_items(ready_items, pipeline_map)
    blocked_items = _enrich_items(blocked_items, pipeline_map)

    current_user = session.get("nuvu_email", "")

    return render_template_string(
        INTAKE_QUEUE_HTML,
        ready_items=ready_items,
        blocked_items=blocked_items,
        ready_count=len(ready_items),
        current_user=current_user,
    )


@intake_queue_bp.route("/intake-queue/approve/<path:property_address>", methods=["POST"])
def intake_queue_approve(property_address: str):
    property_address = property_address.strip()
    approver = session.get("nuvu_email", "staff")
    client = supabase_for_backend()

    # Fetch the intake_queue record
    result = (
        client.table("intake_queue")
        .select("*")
        .eq("property_address", property_address)
        .execute()
    )
    record = (result.data or [None])[0]

    if not record:
        flash(f"Property not found in intake queue: {property_address}", "error")
        return redirect("/intake-queue")

    if record.get("gate_status") != "ready":
        flash(
            f"{property_address} is not in 'ready' state — cannot approve.",
            "error",
        )
        return redirect("/intake-queue")

    now_iso = datetime.now(timezone.utc).isoformat()

    # Update intake_queue
    client.table("intake_queue").update({
        "gate_status":  "approved",
        "approved_by":  approver,
        "approved_at":  now_iso,
        "updated_at":   now_iso,
    }).eq("property_address", property_address).execute()

    # Emit human_decision event
    emit_event(
        event_type="human_decision",
        property_address=property_address,
        actor=approver,
        summary="Completeness gate approved — welcome email queued",
        payload={
            "decision":     "approved",
            "approved_by":  approver,
            "approved_at":  now_iso,
            "tiers":        {"1a": True, "1b": True, "1c": True, "1d": True},
        },
    )

    # Trigger welcome email using pipeline data
    try:
        pipeline_result = (
            client.table("sales_pipeline")
            .select("*")
            .eq("property_address", property_address)
            .execute()
        )
        pipeline_row = (pipeline_result.data or [None])[0]
        if pipeline_row:
            from routes.progression import _send_welcome_emails
            _send_welcome_emails(pipeline_row)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "[intake_queue] welcome email trigger failed for '%s': %s",
            property_address, exc,
        )

    flash(f"{property_address} approved. Welcome email queued.", "success")
    return redirect("/intake-queue")
