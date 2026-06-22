"""Thin HTTP helper for EATOC write-side API endpoints.

Pattern mirrors utils/eatoc_live_map.py (GET adapter).
URL and key come from env vars; defaults match Brief 1 deployment.
"""

import logging
import os
from typing import Dict, List, Optional, Union

import requests as http_requests

EATOC_API_BASE = os.environ.get("EATOC_API_BASE", "https://app.eatoc.co.uk")
NUVU_API_KEY = os.environ.get("NUVU_API_KEY", "dbe-nuvu-2026")

log = logging.getLogger(__name__)


def _headers():
    return {"x-api-key": NUVU_API_KEY, "Content-Type": "application/json"}


def eatoc_get(path: str, params: Optional[Dict] = None) -> Union[Dict, List]:
    """GET from EATOC API. Returns parsed JSON on success; raises on HTTP error."""
    url = f"{EATOC_API_BASE}{path}"
    resp = http_requests.get(url, params=params, headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


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


def eatoc_get_company(company_id: str) -> Optional[Dict]:
    """Fetch a solicitor firm from GET /api/nuvu/companies/<company_id>.

    Returns the JSON dict on success, or None on 404 / any error (fail silently).
    """
    if not company_id:
        return None
    try:
        return eatoc_get(f"/api/nuvu/companies/{company_id}")
    except http_requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            log.debug("[eatoc_api] company %s not found (404)", company_id)
        else:
            log.warning("[eatoc_api] eatoc_get_company(%s) error: %s", company_id, exc)
        return None
    except Exception as exc:
        log.warning("[eatoc_api] eatoc_get_company(%s) unexpected error: %s", company_id, exc)
        return None


def eatoc_get_contact(contact_id: str) -> Optional[Dict]:
    """Fetch a solicitor contact from GET /api/nuvu/contacts/<contact_id>.

    Returns the JSON dict on success, or None on 404 / any error (fail silently).
    """
    if not contact_id:
        return None
    try:
        return eatoc_get(f"/api/nuvu/contacts/{contact_id}")
    except http_requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            log.debug("[eatoc_api] contact %s not found (404)", contact_id)
        else:
            log.warning("[eatoc_api] eatoc_get_contact(%s) error: %s", contact_id, exc)
        return None
    except Exception as exc:
        log.warning("[eatoc_api] eatoc_get_contact(%s) unexpected error: %s", contact_id, exc)
        return None
