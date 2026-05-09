import os

import resend

# Centralised config used by multiple blueprints.
resend.api_key = os.environ.get("RESEND_API_KEY", "")

# Chase Engine (Phase A): set CHASE_ENGINE_ENABLED=true to send outbound chases.
# Default false = cadence + inbound classification run, but only dry-run logs for sends.

# Shared Supabase client (initialised inside db_supabase.py).
from db_supabase import supabase as sb  # noqa: E402


def require_nuvu_api_key():
    """Return None if authorised, or (jsonify body, status_code) if not."""
    from flask import jsonify, request

    expected_key = os.environ.get("NUVU_API_KEY", "dbe-nuvu-2026")
    provided_key = request.headers.get("X-NUVU-API-KEY") or request.headers.get(
        "X-API-Key", ""
    )
    if not provided_key or provided_key != expected_key:
        return jsonify({"error": "Unauthorized"}), 401
    return None

