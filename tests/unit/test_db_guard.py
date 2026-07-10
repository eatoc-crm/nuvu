"""Unit tests for the wrong-database guard in tests/conftest.py."""

import pytest
from tests.conftest import _check_supabase_url, NUVU_PROJECT_ID


def test_guard_passes_when_url_is_empty():
    _check_supabase_url("")


def test_guard_passes_for_correct_project():
    _check_supabase_url(f"https://{NUVU_PROJECT_ID}.supabase.co")


def test_guard_fails_for_eatoc_project():
    with pytest.raises(ValueError, match=NUVU_PROJECT_ID):
        _check_supabase_url("https://grosqsxnwhuvazgbjwan.supabase.co")


def test_guard_fails_for_any_wrong_project():
    with pytest.raises(ValueError, match=NUVU_PROJECT_ID):
        _check_supabase_url("https://someotherproject.supabase.co")


def test_guard_message_contains_wrong_url():
    bad_url = "https://wrongproject.supabase.co"
    with pytest.raises(ValueError, match="wrongproject"):
        _check_supabase_url(bad_url)
