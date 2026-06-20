"""Thin HTTP helper for EATOC write-side API endpoints.

Pattern mirrors utils/eatoc_live_map.py (GET adapter).
URL and key come from env vars; defaults match Brief 1 deployment.
"""

import logging
import os

import requests as http_requests

EATOC_API_BASE = os.environ.get("EATOC_API_BASE", "https://app.eatoc.co.uk")
NUVU_API_KEY = os.environ.get("NUVU_API_KEY", "dbe-nuvu-2026")

log = logging.getLogger(__name__)


def _headers():
    return {"x-api-key": NUVU_API_KEY, "Content-Type": "application/json"}


def eatoc_post(path: str, body: dict) -> dict:
    """POST to EATOC API. Returns parsed JSON on success; raises on HTTP error."""
    url = f"{EATOC_API_BASE}{path}"
    resp = http_requests.post(url, json=body, headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def eatoc_patch(path: str, body: dict) -> dict:
    """PATCH to EATOC API. Returns parsed JSON on success; raises on HTTP error."""
    url = f"{EATOC_API_BASE}{path}"
    resp = http_requests.patch(url, json=body, headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()
