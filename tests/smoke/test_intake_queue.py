"""Smoke tests for the Intake Queue routes."""


def test_intake_queue_get(app_client):
    """GET /intake-queue returns 200 (logged in) or 302 (auth redirect)."""
    resp = app_client.get("/intake-queue")
    assert resp.status_code in (200, 302), f"/intake-queue returned {resp.status_code}"


def test_intake_queue_approve_post(app_client):
    """POST /intake-queue/approve/<address> returns 302 (redirect after action)."""
    resp = app_client.post(
        "/intake-queue/approve/test-address-smoke",
        follow_redirects=False,
    )
    assert resp.status_code in (302, 401, 403), (
        f"/intake-queue/approve returned {resp.status_code}"
    )
