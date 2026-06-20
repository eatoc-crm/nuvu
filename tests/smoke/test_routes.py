"""Smoke: Core routes return 200, not 500."""


def test_dashboard_loads(app_client):
    """Dashboard route returns 200."""
    resp = app_client.get("/dashboard")
    assert resp.status_code == 200, f"Dashboard returned {resp.status_code}"


def test_health_endpoint(app_client):
    """Health check returns 200."""
    resp = app_client.get("/health")
    assert resp.status_code == 200
