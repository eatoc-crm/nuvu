"""Smoke: EATOC adapter API is reachable."""
from utils.eatoc_api import eatoc_get_status


def test_eatoc_properties_endpoint():
    """GET /api/nuvu/properties returns 200."""
    status_code = eatoc_get_status("/api/nuvu/properties", timeout=10)
    assert status_code == 200, f"EATOC API returned {status_code}"


def test_eatoc_chain_links_endpoint():
    """GET /api/nuvu/chain-links returns 200."""
    status_code = eatoc_get_status("/api/nuvu/chain-links", timeout=10)
    assert status_code == 200, f"EATOC chain-links returned {status_code}"
