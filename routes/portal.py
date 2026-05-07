"""Buyer / vendor portal (demo login, live Supabase property snapshot).

Staff review/dispatch (TA6/TA10) lives on the same ``portal`` Blueprint (``/portal/...``).
"""

import json
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    render_template_string,
    request,
    session,
    url_for,
)

from db_supabase import fetch_property_images, fetch_sales_pipeline, fetch_sales_progression_recent
from routes.crm import (
    FALLBACK_GRADIENTS,
    STATUS_LABELS,
    STATUS_MAP,
    _milestones_from_record,
    _progress_from_record,
)
from db_portal import (
    fetch_form_completion_by_session,
    fetch_form_responses,
    fetch_portal_session,
    record_form_completion_dispatch,
)
from routes.dashboard import _match_pipeline, _normalize_addr
from routes.portal_notify import send_solicitor_dispatch_email
from routes.portal_forms import load_form
from utils.portal_config import portal_dispatch_enabled
from utils.portal_milestones import augment_protocol_forms_returned
from utils.pdf_filler import ROOT, fill_ta_form

portal_bp = Blueprint("portal", __name__, url_prefix="/portal")

_SESSION_KEY = "portal_demo"
_INACTIVE = frozenset(
    {
        "available",
        "withdrawn",
        "for sale",
        "fallen through",
        "completed",
        "let agreed",
        "let",
    }
)


def _pick_progression_row(rows):
    """Prefer an in-flight progression row; otherwise first row."""
    if not rows:
        return None
    active = []
    for r in rows:
        st = (r.get("status") or "").strip().lower()
        if st not in _INACTIVE:
            active.append(r)
    return active[0] if active else rows[0]


def _image_url_for_address(addr, img_rows):
    norm = _normalize_addr(addr or "")
    for row in img_rows:
        row_norm = _normalize_addr(row.get("address") or "")
        if not row_norm or row_norm != norm:
            continue
        url = (row.get("image_url") or "").strip() or None
        if not url:
            urls = row.get("photo_urls") or []
            if isinstance(urls, list) and len(urls) > 1:
                url = (urls[1] or "").strip() or None
        if url:
            return url
    return ""


def _build_portal_property():
    """Single property view model from Supabase (progression + pipeline + images)."""
    try:
        rows = fetch_sales_progression_recent(80)
        r = _pick_progression_row(rows)
        if not r:
            return None

        addr = (r.get("property_address") or "").strip() or "Property"
        pipe_rows = fetch_sales_pipeline()
        pipe_lookup = {}
        for row in pipe_rows:
            pa = row.get("property_address") or ""
            key = _normalize_addr(pa)
            if key:
                pipe_lookup[key] = row
        pipe_keys = list(pipe_lookup.keys())
        pipe = _match_pipeline(addr, pipe_lookup, pipe_keys)

        price = 0
        if pipe:
            try:
                cp = pipe.get("current_price")
                price = int(float(cp)) if cp is not None else 0
            except (TypeError, ValueError):
                price = 0

        img_rows = fetch_property_images()
        image_url = _image_url_for_address(addr, img_rows)

        raw_status = (r.get("status") or "active").lower().replace(" ", "_")
        if raw_status == "under_offer":
            raw_status = "active"
        if raw_status not in STATUS_MAP:
            raw_status = "active"
        status = STATUS_MAP[raw_status]
        status_label = STATUS_LABELS.get(status, "ON TRACK")
        progress = _progress_from_record(r)
        milestones = _milestones_from_record(r)

        return {
            "address": addr,
            "price": price,
            "image_url": image_url,
            "image_bg": FALLBACK_GRADIENTS[hash(addr) % len(FALLBACK_GRADIENTS)],
            "progress": progress,
            "milestones": milestones,
            "status": status,
            "status_label": status_label,
            "_progression_id": r.get("id"),
        }
    except Exception:
        return None


PORTAL_LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NUVU — Portal</title>
<link rel="icon" href="/static/logo.png">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --navy:#0f1b2d;--navy-lt:#162236;--navy-md:#1c2e4a;
  --lime:#c4e233;--white:#ffffff;--muted:rgba(255,255,255,.55);
  --txt-dim:rgba(255,255,255,.42);
}
html{font-size:15px}
body{
  font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
  min-height:100vh;background:radial-gradient(ellipse 120% 80% at 50% -20%,#1c2e4a 0%,var(--navy) 55%);
  color:var(--white);display:flex;align-items:center;justify-content:center;padding:24px;
}
.panel{
  width:100%;max-width:440px;
  background:var(--navy-lt);border:1px solid rgba(255,255,255,.08);
  border-radius:18px;padding:40px 36px 36px;
  box-shadow:0 24px 64px rgba(0,0,0,.45);
}
.brand{display:flex;align-items:center;justify-content:center;gap:14px;margin-bottom:6px}
.brand img{width:48px;height:48px;border-radius:10px}
.brand h1{font-size:2rem;font-weight:900;letter-spacing:12px;text-indent:12px;line-height:1}
.strap{font-size:.62rem;text-transform:uppercase;letter-spacing:3px;font-weight:600;color:var(--lime);text-align:center;margin-bottom:6px}
.sub{font-size:.88rem;color:var(--muted);text-align:center;margin-bottom:28px;line-height:1.45}
.lbl{font-size:.78rem;font-weight:600;color:var(--muted);margin-bottom:8px;display:block}
.inp{
  width:100%;padding:13px 14px;font-size:1rem;font-family:inherit;
  border-radius:10px;border:1px solid rgba(255,255,255,.12);
  background:rgba(15,27,45,.55);color:var(--white);outline:none;margin-bottom:18px;
  transition:border .2s,box-shadow .2s;
}
.inp::placeholder{color:var(--txt-dim)}
.inp:focus{border-color:rgba(196,226,51,.55);box-shadow:0 0 0 3px rgba(196,226,51,.12)}
.btn{
  width:100%;padding:14px 16px;border:none;border-radius:10px;cursor:pointer;
  font-size:1rem;font-weight:700;background:var(--lime);color:var(--navy);
  transition:filter .2s,transform .15s;
}
.btn:hover{filter:brightness(1.05)}
.btn:active{transform:scale(.99)}
.demo-note{
  margin-top:20px;font-size:.72rem;color:var(--txt-dim);text-align:center;line-height:1.5;
  border-top:1px solid rgba(255,255,255,.06);padding-top:16px;
}
</style>
</head>
<body>
<div class="panel">
  <div class="brand">
    <img src="/static/logo.png" alt="">
    <h1>NUVU</h1>
  </div>
  <div class="strap">Buyer &amp; Vendor Portal</div>
  <p class="sub">Sign in to view your sale progression in one place. Demo access — authentication is not enforced yet.</p>
  <form method="post" action="{{ url_for('portal.portal_login') }}">
    <label class="lbl" for="email">Email</label>
    <input class="inp" id="email" name="email" type="email" autocomplete="username" placeholder="you@example.com" required>
    <label class="lbl" for="password">Password</label>
    <input class="inp" id="password" name="password" type="password" autocomplete="current-password" placeholder="••••••••" required>
    <button class="btn" type="submit">Sign in</button>
  </form>
  <p class="demo-note">This is a preview environment. Use any email and password to continue.</p>
</div>
</body>
</html>"""


PORTAL_HOME_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Your property — NUVU Portal</title>
<link rel="icon" href="/static/logo.png">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --navy:#0f1b2d;--navy-lt:#162236;--navy-card:#182842;
  --lime:#c4e233;--green:#27ae60;--amber:#e88a3a;--red:#e25555;--blue:#3b82f6;
  --white:#ffffff;--muted:rgba(255,255,255,.55);--dim:rgba(255,255,255,.38);
}
html{font-size:15px}
body{
  font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
  background:var(--navy);color:var(--white);min-height:100vh;
}
.top{
  display:flex;align-items:center;justify-content:space-between;
  padding:16px 28px;border-bottom:1px solid rgba(255,255,255,.08);
  background:rgba(15,27,45,.92);backdrop-filter:blur(10px);
}
.top-left{display:flex;align-items:center;gap:12px}
.top-left img{width:40px;height:40px;border-radius:8px}
.top-left span{font-weight:800;letter-spacing:10px;font-size:1.35rem}
.top-right{display:flex;align-items:center;gap:14px}
.top-right a{
  font-size:.82rem;font-weight:600;color:var(--lime);text-decoration:none;
  padding:8px 14px;border-radius:8px;border:1px solid rgba(196,226,51,.35);
}
.top-right a:hover{background:rgba(196,226,51,.1)}
.hero{position:relative;height:min(38vh,360px);overflow:hidden;background:var(--navy-card)}
.hero img{width:100%;height:100%;object-fit:cover;display:block}
.hero-fallback{width:100%;height:100%}
.hero-grad{
  position:absolute;inset:0;
  background:linear-gradient(transparent 20%,rgba(15,27,45,.92));
}
.hero-inner{position:absolute;left:0;right:0;bottom:0;padding:28px 28px 22px;max-width:1100px;margin:0 auto}
.hero-inner h1{font-size:clamp(1.25rem,3vw,1.75rem);font-weight:800;line-height:1.25;margin-bottom:8px}
.chip{
  position:absolute;top:18px;right:22px;padding:6px 14px;border-radius:6px;
  font-size:.68rem;font-weight:800;letter-spacing:.6px;
}
.chip-on-track{background:var(--green)}.chip-at-risk{background:var(--amber)}
.chip-stalled{background:var(--red)}.chip-exchanged{background:var(--blue)}
.price{font-size:1.35rem;font-weight:900;color:var(--lime);margin-top:4px}
.wrap{max-width:1100px;margin:0 auto;padding:28px 28px 48px}
.empty{
  background:var(--navy-lt);border:1px solid rgba(255,255,255,.08);
  border-radius:14px;padding:28px;color:var(--muted);line-height:1.55;font-size:.95rem;
}
.prog{margin-bottom:28px}
.prog-head{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:10px}
.prog-head span:first-child{font-size:.72rem;text-transform:uppercase;letter-spacing:1.4px;color:var(--dim);font-weight:600}
.prog-pct{font-size:1.1rem;font-weight:800;color:var(--lime)}
.prog-bar{height:10px;border-radius:5px;background:rgba(255,255,255,.1);overflow:hidden}
.prog-fill{height:100%;border-radius:5px;background:var(--lime);transition:width .4s ease}
.ms-wrap{
  background:var(--navy-lt);border:1px solid rgba(255,255,255,.08);
  border-radius:14px;padding:22px 24px;margin-bottom:26px;
}
.ms-wrap h2{font-size:.95rem;font-weight:700;margin-bottom:14px;color:var(--white)}
.ms-row{display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.06);font-size:.86rem}
.ms-row:last-child{border-bottom:none}
.ms-ic{width:22px;height:22px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:.62rem}
.ms-ic.ok{background:var(--green);color:#fff}.ms-ic.no{border:2px solid rgba(255,255,255,.2);background:transparent}
.ms-name{flex:1}.ms-name.done{opacity:.65;text-decoration:line-through}
.ms-name.todo{color:var(--muted);font-style:italic}
.ms-date{color:var(--dim);font-size:.78rem;font-weight:600;white-space:nowrap}
.grid{
  display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:18px;
}
.tile{
  background:var(--navy-card);border:1px solid rgba(255,255,255,.07);
  border-radius:14px;padding:20px 20px 18px;min-height:120px;
  display:flex;flex-direction:column;gap:8px;
}
.tile h3{font-size:1rem;font-weight:700}
.tile p{font-size:.8rem;color:var(--muted);line-height:1.45;flex:1}
.badge{
  align-self:flex-start;font-size:.62rem;font-weight:800;letter-spacing:.8px;
  text-transform:uppercase;padding:5px 10px;border-radius:20px;
  background:rgba(196,226,51,.14);color:var(--lime);border:1px solid rgba(196,226,51,.28);
}
.sec-title{font-size:.82rem;font-weight:700;text-transform:uppercase;letter-spacing:1.6px;color:var(--dim);margin:8px 0 16px}
@media(max-width:640px){
  .top{padding:12px 16px;flex-wrap:wrap;gap:12px}
  .wrap{padding:20px 16px 40px}
  .hero-inner{padding:20px 16px 18px}
}
</style>
</head>
<body>
<header class="top">
  <div class="top-left">
    <img src="/static/logo.png" alt="">
    <span>NUVU</span>
  </div>
  <div class="top-right">
    <a href="{{ url_for('portal.portal_logout') }}">Sign out</a>
  </div>
</header>

{% if prop %}
<div class="hero">
  {% if prop.image_url %}
  <img src="{{ prop.image_url }}" alt="">
  {% else %}
  <div class="hero-fallback" style="background:{{ prop.image_bg }}"></div>
  {% endif %}
  <span class="chip chip-{{ prop.status }}">{{ prop.status_label }}</span>
  <div class="hero-grad"></div>
  <div class="hero-inner">
    <h1>{{ prop.address }}</h1>
    {% if prop.price %}<div class="price">&pound;{{ "{:,.0f}".format(prop.price) }}</div>{% endif %}
  </div>
</div>

<div class="wrap">
  <div class="prog">
    <div class="prog-head">
      <span>Milestone progress</span>
      <span class="prog-pct">{{ prop.progress }}%</span>
    </div>
    <div class="prog-bar"><div class="prog-fill" style="width:{{ prop.progress }}%"></div></div>
  </div>

  <div class="ms-wrap">
    <h2>Your milestones</h2>
    {% for ms in prop.milestones %}
    <div class="ms-row">
      <span class="ms-ic {{ 'ok' if ms.done else 'no' }}">{% if ms.done %}&#10003;{% endif %}</span>
      <span class="ms-name {{ 'done' if ms.done else 'todo' }}">{{ ms.label }}</span>
      {% if ms.date %}<span class="ms-date">{{ (ms.date|string)[:10] }}</span>{% endif %}
    </div>
    {% endfor %}
  </div>

  <div class="sec-title">More soon</div>
  <div class="grid">
    <div class="tile"><span class="badge">Coming Soon</span><h3>Documents</h3><p>Secure uploads and your key paperwork in one place.</p></div>
    <div class="tile"><span class="badge">Coming Soon</span><h3>Messages</h3><p>Threaded updates from your negotiator and progression team.</p></div>
    <div class="tile"><span class="badge">Coming Soon</span><h3>Your Solicitor</h3><p>Contact details and instruction status at a glance.</p></div>
    <div class="tile"><span class="badge">Coming Soon</span><h3>Survey Status</h3><p>Booking, report, and any follow-up actions.</p></div>
  </div>
</div>
{% else %}
<div class="wrap">
  <div class="empty">
    No active property was found in Supabase yet. When sales progression data is available, your overview will appear here.
  </div>
  <div class="sec-title" style="margin-top:28px">More soon</div>
  <div class="grid">
    <div class="tile"><span class="badge">Coming Soon</span><h3>Documents</h3><p>Secure uploads and your key paperwork in one place.</p></div>
    <div class="tile"><span class="badge">Coming Soon</span><h3>Messages</h3><p>Threaded updates from your negotiator and progression team.</p></div>
    <div class="tile"><span class="badge">Coming Soon</span><h3>Your Solicitor</h3><p>Contact details and instruction status at a glance.</p></div>
    <div class="tile"><span class="badge">Coming Soon</span><h3>Survey Status</h3><p>Booking, report, and any follow-up actions.</p></div>
  </div>
</div>
{% endif %}
</body>
</html>"""


@portal_bp.route("", strict_slashes=False)
@portal_bp.route("/", strict_slashes=False)
def portal_root():
    if session.get(_SESSION_KEY):
        return redirect(url_for("portal.portal_home"))
    return render_template_string(PORTAL_LOGIN_HTML)


@portal_bp.route("/login", methods=["POST"])
def portal_login():
    session.permanent = True
    session[_SESSION_KEY] = True
    session["portal_email"] = (request.form.get("email") or "").strip()
    return redirect(url_for("portal.portal_home"))


@portal_bp.route("/home")
def portal_home():
    if not session.get(_SESSION_KEY):
        return redirect(url_for("portal.portal_root"))
    prop = _build_portal_property()
    return render_template_string(PORTAL_HOME_HTML, prop=prop)


@portal_bp.route("/logout")
def portal_logout():
    session.pop(_SESSION_KEY, None)
    session.pop("portal_email", None)
    return redirect(url_for("portal.portal_root"))


# ─────────────────────────────────────────────────────────────
#  Staff — TA6/TA10 review & dispatch (Window 3, NUVU dashboard auth)
# ─────────────────────────────────────────────────────────────


def _require_nuvu_staff():
    if not session.get("nuvu_email"):
        return redirect("/login")
    return None


def _require_staff(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        redir = _require_nuvu_staff()
        if redir is not None:
            return redir
        return view(*args, **kwargs)

    return wrapped


@portal_bp.route("/review/<session_id>")
@_require_staff
def portal_review_page(session_id: str):
    session_id = (session_id or "").strip()
    sess = fetch_portal_session(session_id)
    if not sess:
        return render_template(
            "portal/portal_error.html",
            message="Unknown or invalid session.",
        ), 404
    form_type = (sess.get("form_type") or "ta6").lower()
    form = load_form(form_type)
    rows = fetch_form_responses(session_id)
    by_q: dict[tuple[str, str], dict] = {
        (r.get("section_key"), r.get("question_key")): r for r in rows
    }

    def _fmt_answer(val):
        if val is None:
            return ""
        if isinstance(val, str):
            return val
        return json.dumps(val, ensure_ascii=False)

    sections_out = []
    for sec in form.get("sections") or []:
        sk = sec.get("key") or ""
        items = []
        for q in sec.get("questions") or []:
            qk = q.get("key") or ""
            row = by_q.get((sk, qk))
            st = (row or {}).get("status") or "pending"
            raw_ans = (row or {}).get("answer")
            items.append(
                {
                    "question_text": q.get("text") or qk,
                    "status": st,
                    "answer": raw_ans,
                    "display_answer": _fmt_answer(raw_ans),
                }
            )
        sections_out.append(
            {
                "title": sec.get("title") or sk,
                "key": sk,
                "items": items,
            }
        )
    completion = fetch_form_completion_by_session(session_id)
    return render_template(
        "portal/portal_review.html",
        session_id=session_id,
        property_address=sess.get("property_address") or "",
        seller_name=sess.get("seller_name") or "",
        form_title=form.get("title") or form_type.upper(),
        sections=sections_out,
        completion=completion,
        dispatch_enabled=portal_dispatch_enabled(),
    )


@portal_bp.route("/api/dispatch", methods=["POST"])
@_require_staff
def api_portal_dispatch():
    if not portal_dispatch_enabled():
        return jsonify({"error": "Dispatch is disabled (PORTAL_DISPATCH_ENABLED)."}), 403
    body = request.get_json(silent=True) or {}
    session_id = (body.get("session_id") or "").strip()
    solicitor_email = (body.get("solicitor_email") or "").strip()
    if not session_id or not solicitor_email:
        return jsonify({"error": "session_id and solicitor_email required"}), 400

    sess = fetch_portal_session(session_id)
    if not sess:
        return jsonify({"error": "Unknown session"}), 404
    comp = fetch_form_completion_by_session(session_id)
    if not comp or (comp.get("status") or "").lower() != "completed":
        return jsonify({"error": "Form is not in completed / awaiting review state."}), 400

    form_type = (sess.get("form_type") or "ta6").lower()
    form_label = "TA6" if form_type == "ta6" else "TA10"
    addr = sess.get("property_address") or ""
    seller = sess.get("seller_name") or "the seller"

    try:
        pdf_path_str = fill_ta_form(form_type, addr, session_id)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"PDF generation failed: {e}"}), 500

    pdf_path = Path(pdf_path_str)
    if not pdf_path.is_file():
        return jsonify({"error": "Generated PDF not found on disk."}), 500
    pdf_bytes = pdf_path.read_bytes()
    _dt = datetime.now(timezone.utc)
    completed_on = f"{_dt.day} {_dt.strftime('%B %Y')}"
    fname = pdf_path.name

    try:
        send_solicitor_dispatch_email(
            to_email=solicitor_email,
            form_label=form_label,
            property_address=addr,
            seller_name=seller,
            completed_on=completed_on,
            pdf_path=str(pdf_path),
            pdf_bytes=pdf_bytes,
            filename=fname,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Email send failed: {e}"}), 502

    reviewer = (session.get("nuvu_email") or "").strip() or "unknown"
    record_form_completion_dispatch(
        session_id, reviewed_by=reviewer, dispatched_to=solicitor_email
    )
    augment_protocol_forms_returned(addr)

    return jsonify({"ok": True, "pdf_path": str(pdf_path.relative_to(ROOT))})
