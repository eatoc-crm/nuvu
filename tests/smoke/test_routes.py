"""Smoke: Core routes return 200, not 500."""


def test_dashboard_loads(app_client):
    """Dashboard route returns 200 or 302 (redirect to login when unauthenticated)."""
    resp = app_client.get("/dashboard")
    assert resp.status_code in (200, 302), f"Dashboard returned {resp.status_code}"


def test_health_endpoint(app_client):
    """Health check returns 200 or 302 (redirect to login when unauthenticated)."""
    resp = app_client.get("/health")
    assert resp.status_code in (200, 302)
