"""
Shared test fixtures for NUVU test suite.
Uses the real NUVU Supabase project (same env vars as production).
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

NUVU_PROJECT_ID = "xhxgqbjrgqyrrazmvufh"


def _check_supabase_url(url: str) -> None:
    """Raise ValueError if url is configured but points at the wrong Supabase project.

    An empty url (no database configured for this run) is allowed.
    A non-empty url that does not contain NUVU_PROJECT_ID is never allowed.
    """
    if url and NUVU_PROJECT_ID not in url:
        raise ValueError(
            f"SUPABASE_URL targets the wrong Supabase project.\n"
            f"  Required project:  {NUVU_PROJECT_ID}\n"
            f"  Configured URL:    {url!r}\n"
            f"  This run is targeting the wrong database — aborting."
        )


@pytest.fixture(scope="session", autouse=True)
def guard_supabase_target():
    """Session-scoped guard: abort the entire test run if SUPABASE_URL points at
    any project other than the NUVU production project (xhxgqbjrgqyrrazmvufh).
    Wrong-database test runs are structurally impossible, not just currently absent."""
    url = os.environ.get("SUPABASE_URL", "")
    try:
        _check_supabase_url(url)
    except ValueError as exc:
        pytest.exit(f"ABORT — wrong database: {exc}", returncode=3)


@pytest.fixture(scope="session")
def supabase_client():
    """Reusable Supabase client for tests."""
    from db_supabase import supabase
    return supabase


@pytest.fixture(scope="session")
def app_client():
    """Flask test client for route testing."""
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
