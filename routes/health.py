"""
NUVU Health Check Endpoint

GET /health -> JSON status of all critical dependencies.
200 = all healthy. 503 = one or more checks failed.

Public endpoint — no auth required. Returns system status only;
no sensitive data, no property information, no API keys.
"""
import time
import logging
from datetime import datetime
from flask import Blueprint, jsonify
from db_supabase import supabase
from utils.eatoc_api import eatoc_get_status

logger = logging.getLogger(__name__)
health_bp = Blueprint("health", __name__)


def _check_supabase():
    """Can we query the events table?"""
    try:
        start = time.time()
        supabase.table("events").select("id").limit(1).execute()
        return {"status": "ok", "ms": round((time.time() - start) * 1000)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _check_eatoc_api():
    """Can we reach the EATOC adapter API?"""
    try:
        start = time.time()
        status_code = eatoc_get_status("/api/nuvu/properties", timeout=10)
        return {
            "status": "ok" if status_code == 200 else "error",
            "http_status": status_code,
            "ms": round((time.time() - start) * 1000),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _check_health_probe_writable():
    """Can we write to and delete from the health_probe table?"""
    try:
        start = time.time()
        row = {
            "probed_at": datetime.utcnow().isoformat(),
        }
        result = supabase.table("health_probe").insert(row).execute()
        if result.data:
            supabase.table("health_probe").delete().eq(
                "id", result.data[0]["id"]
            ).execute()
        return {"status": "ok", "ms": round((time.time() - start) * 1000)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@health_bp.route("/health")
def health():
    checks = {
        "supabase": _check_supabase(),
        "eatoc_api": _check_eatoc_api(),
        "health_probe_writable": _check_health_probe_writable(),
    }

    all_ok = all(c["status"] == "ok" for c in checks.values())

    return jsonify({
        "status": "healthy" if all_ok else "degraded",
        "checks": checks,
    }), 200 if all_ok else 503
