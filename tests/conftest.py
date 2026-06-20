"""
Shared test fixtures for NUVU test suite.
Uses the real NUVU Supabase project (same env vars as production).
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
