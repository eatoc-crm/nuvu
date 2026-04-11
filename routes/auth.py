from datetime import datetime, timedelta
import secrets
import os

from flask import Blueprint, redirect, render_template_string, request, session

import shared  # ensures shared config (e.g. resend.api_key) is loaded
import resend

auth_bp = Blueprint("auth", __name__)

# ─────────────────────────────────────────────────────────────
#  MAGIC LINK AUTH
# ─────────────────────────────────────────────────────────────

NUVU_ALLOWED_EMAILS = [
    e.strip().lower()
    for e in os.environ.get("NUVU_ALLOWED_EMAILS", "").split(",")
    if e.strip()
]

AUTH_FROM = "David Britton Estates, powered by NUVU <salesprog@brittonestates.co.uk>"
AUTH_BASE_URL = os.environ.get(
    "NUVU_BASE_URL", "https://nuvu-production.up.railway.app"
)

# In-memory stores (reset on redeploy — acceptable for magic links)
_magic_tokens = {}  # token -> {"email": str, "expires": datetime}
_login_attempts = {}  # ip -> [(timestamp, ...), ...]
_RATE_LIMIT = 10  # max attempts per IP
_RATE_WINDOW = timedelta(hours=1)

LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NUVU — Log In</title>
<link rel="icon" href="/static/logo.png">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--navy:#0f1b2d;--lime:#c4e233;--lime-dk:#a3bf1a;--white:#ffffff;--txt:#1e293b;--txt-light:#94a3b8;--red:#e25555;--green:#27ae60}
html{font-size:15px}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--navy);min-height:100vh;display:flex;align-items:center;justify-content:center}
.login-card{background:var(--white);border-radius:18px;padding:48px 40px;width:100%;max-width:420px;box-shadow:0 30px 80px rgba(0,0,0,.3);text-align:center}
.login-logo{display:flex;align-items:center;justify-content:center;gap:14px;margin-bottom:8px}
.login-logo img{width:48px;height:48px;border-radius:10px}
.login-logo h1{font-size:2rem;font-weight:900;color:var(--navy);letter-spacing:12px;text-indent:12px}
.login-strapline{font-size:.6rem;color:var(--txt-light);text-transform:uppercase;letter-spacing:3px;font-weight:600;margin-bottom:32px}
.login-label{font-size:.88rem;color:var(--txt);font-weight:600;margin-bottom:12px;display:block;text-align:left}
.login-input{width:100%;padding:14px 16px;font-size:1rem;font-family:inherit;border:1px solid #d1d5db;border-radius:10px;outline:none;transition:border .2s,box-shadow .2s;margin-bottom:20px}
.login-input:focus{border-color:var(--lime);box-shadow:0 0 0 3px rgba(196,226,51,.25)}
.login-btn{width:100%;padding:14px;background:var(--navy);color:var(--white);font-size:1rem;font-weight:700;border:none;border-radius:10px;cursor:pointer;transition:background .2s}
.login-btn:hover{background:#1c2e4a}
.login-msg{margin-top:16px;font-size:.88rem;padding:10px 14px;border-radius:8px;line-height:1.45}
.msg-ok{background:#f0fdf4;color:#166534;border:1px solid #bbf7d0}
.msg-err{background:#fef2f2;color:#b91c1c;border:1px solid #fecaca}
</style>
</head>
<body>
<div class="login-card">
  <div class="login-logo">
    <img src="/static/logo.png" alt="NUVU">
    <h1>NUVU</h1>
  </div>
  <div class="login-strapline">Live Sales Progression</div>
  <form method="POST" action="/login">
    <label class="login-label">Enter your email to log in</label>
    <input class="login-input" type="email" name="email" placeholder="you@brittonestates.co.uk" required autofocus>
    <button class="login-btn" type="submit">Send Login Link</button>
  </form>
  {% if msg %}
  <div class="login-msg {{ 'msg-ok' if msg_ok else 'msg-err' }}">{{ msg }}</div>
  {% endif %}
</div>
</body>
</html>"""


@auth_bp.route("/login", methods=["GET"])
def login_page():
    if session.get("nuvu_email"):
        return redirect("/")
    return render_template_string(LOGIN_HTML, msg=None, msg_ok=False)


@auth_bp.route("/login", methods=["POST"])
def login_submit():
    ip = request.remote_addr or "unknown"

    # Rate limiting
    now = datetime.utcnow()
    attempts = _login_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < _RATE_WINDOW]
    if len(attempts) >= _RATE_LIMIT:
        return render_template_string(
            LOGIN_HTML, msg="Too many requests — please try again later.", msg_ok=False
        ), 429
    attempts.append(now)
    _login_attempts[ip] = attempts

    email = (request.form.get("email") or "").strip().lower()
    if email not in NUVU_ALLOWED_EMAILS:
        return render_template_string(LOGIN_HTML, msg="Email not recognised.", msg_ok=False)

    # Generate token
    token = secrets.token_urlsafe(32)
    _magic_tokens[token] = {
        "email": email,
        "expires": now + timedelta(minutes=15),
    }

    # Send magic link email
    link = f"{AUTH_BASE_URL}/auth/verify?token={token}"
    try:
        resend.Emails.send(
            {
                "from": AUTH_FROM,
                "to": [email],
                "subject": "Your NUVU login link",
                "html": (
                    "<p>Click the link below to log in to NUVU. "
                    "This link expires in 15 minutes and can only be used once.</p>"
                    f'<p><a href="{link}" style="display:inline-block;padding:12px 28px;'
                    "background:#0f1b2d;color:#ffffff;border-radius:8px;text-decoration:none;"
                    'font-weight:700;font-size:1rem;">Log in to NUVU</a></p>'
                    "<p style=\"color:#94a3b8;font-size:.85rem;\">If you didn’t request this, ignore this email.</p>"
                    "<p style=\"color:#94a3b8;font-size:.85rem;\">David Britton Estates, powered by NUVU</p>"
                ),
            }
        )
        print(f"Magic link sent to {email}")
    except Exception as e:
        print(f"Magic link send FAILED for {email}: {e}")
        return render_template_string(
            LOGIN_HTML, msg="Failed to send login link — please try again.", msg_ok=False
        )

    return render_template_string(
        LOGIN_HTML,
        msg="Check your email — your login link expires in 15 minutes.",
        msg_ok=True,
    )


@auth_bp.route("/auth/verify")
def auth_verify():
    token = request.args.get("token", "")
    entry = _magic_tokens.pop(token, None)

    if not entry or datetime.utcnow() > entry["expires"]:
        # Token missing, already used, or expired
        return render_template_string(
            LOGIN_HTML,
            msg="This link has expired — please request a new one.",
            msg_ok=False,
        )

    session.permanent = True
    session["nuvu_email"] = entry["email"]
    return redirect("/")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ─────────────────────────────────────────────────────────────
#  LOGIN GUARD — session check on all routes
# ─────────────────────────────────────────────────────────────

AUTH_EXEMPT_PREFIXES = (
    "/login",
    "/auth/",
    "/logout",
    "/static/",
    "/crm",
    "/api/crm/",
    "/api/intake",
    "/api/update",
)


@auth_bp.before_app_request
def require_login():
    for prefix in AUTH_EXEMPT_PREFIXES:
        if request.path.startswith(prefix):
            return
    if not session.get("nuvu_email"):
        return redirect("/login")

