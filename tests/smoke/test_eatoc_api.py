"""Smoke: EATOC adapter API is reachable."""
import os
import requests


def test_eatoc_properties_endpoint():
    """GET /api/nuvu/properties returns 200."""
    base = os.environ.get("EATOC_API_BASE", "https://app.eatoc.co.uk")
    key = os.environ.get("NUVU_API_KEY", "dbe-nuvu-2026")
    resp = requests.get(
        f"{base}/api/nuvu/properties",
        headers={"x-api-key": key},
        timeout=10,
    )
    assert resp.status_code == 200, f"EATOC API returned {resp.status_code}"


def test_eatoc_chain_links_endpoint():
    """GET /api/nuvu/chain-links returns 200."""
    base = os.environ.get("EATOC_API_BASE", "https://app.eatoc.co.uk")
    key = os.environ.get("NUVU_API_KEY", "dbe-nuvu-2026")
    resp = requests.get(
        f"{base}/api/nuvu/chain-links",
        headers={"x-api-key": key},
        timeout=10,
    )
    assert resp.status_code == 200, f"EATOC chain-links returned {resp.status_code}"
