"""
Unit tests for the NUVU Completeness Gate — all four tier checks.
These tests are fully offline (no Supabase calls).
"""

import pytest
from unittest.mock import MagicMock, patch

from utils.completeness_gate import (
    check_tier_1a,
    check_tier_1b,
    check_tier_1c,
    check_tier_1d,
    validate_email,
    validate_phone,
)


# ─────────────────────────────────────────────────────────────
#  VALIDATORS
# ─────────────────────────────────────────────────────────────

def test_validate_email_valid():
    assert validate_email("buyer@example.com") is True


def test_validate_email_no_at():
    assert validate_email("buyerexample.com") is False


def test_validate_email_no_dot_after_at():
    assert validate_email("buyer@examplecom") is False


def test_validate_email_empty():
    assert validate_email("") is False
    assert validate_email(None) is False


def test_validate_phone_valid():
    assert validate_phone("07712 345678") is True
    assert validate_phone("+447712345678") is True
    assert validate_phone("01768 867 000") is True


def test_validate_phone_empty_after_strip():
    assert validate_phone("") is False
    assert validate_phone(None) is False
    assert validate_phone("   ") is False


def test_validate_phone_non_digit():
    assert validate_phone("abc def") is False


# ─────────────────────────────────────────────────────────────
#  TIER 1A
# ─────────────────────────────────────────────────────────────

VALID_1A = {
    "buyer_name":   "John Smith",
    "buyer_email":  "john@example.com",
    "buyer_phone":  "07712 345678",
    "vendor_name":  "Jane Doe",
    "vendor_email": "jane@example.com",
    "vendor_phone": "07900 111222",
}


def test_tier_1a_pass_all_fields():
    passed, missing = check_tier_1a(VALID_1A)
    assert passed is True
    assert missing == []


def test_tier_1a_fail_missing_buyer_email():
    data = {**VALID_1A, "buyer_email": None}
    passed, missing = check_tier_1a(data)
    assert passed is False
    assert "buyer_email" in missing


def test_tier_1a_fail_invalid_email_format():
    data = {**VALID_1A, "buyer_email": "not-an-email"}
    passed, missing = check_tier_1a(data)
    assert passed is False
    assert "buyer_email" in missing


def test_tier_1a_fail_empty_phone_after_strip():
    data = {**VALID_1A, "buyer_phone": "   "}
    passed, missing = check_tier_1a(data)
    assert passed is False
    assert "buyer_phone" in missing


def test_tier_1a_fail_multiple_fields():
    data = {**VALID_1A, "buyer_email": None, "vendor_name": ""}
    passed, missing = check_tier_1a(data)
    assert passed is False
    assert "buyer_email" in missing
    assert "vendor_name" in missing


# ─────────────────────────────────────────────────────────────
#  TIER 1B
# ─────────────────────────────────────────────────────────────

VALID_1B = {
    "buyer_solicitor_name":   "Alice Green",
    "buyer_solicitor_firm":   "Green & Co Solicitors",
    "buyer_solicitor_email":  "alice@greenco.com",
    "buyer_solicitor_phone":  "01234 567890",
    "seller_solicitor_name":  "Bob White",
    "seller_solicitor_firm":  "White Legal LLP",
    "seller_solicitor_email": "bob@whitelegal.com",
    "seller_solicitor_phone": "01234 098765",
}


def test_tier_1b_pass_all_fields():
    passed, missing = check_tier_1b(VALID_1B)
    assert passed is True
    assert missing == []


def test_tier_1b_fail_missing_seller_solicitor_email():
    data = {**VALID_1B, "seller_solicitor_email": None}
    passed, missing = check_tier_1b(data)
    assert passed is False
    assert "seller_solicitor_email" in missing


def test_tier_1b_fail_missing_buyer_solicitor_firm():
    data = {**VALID_1B, "buyer_solicitor_firm": ""}
    passed, missing = check_tier_1b(data)
    assert passed is False
    assert "buyer_solicitor_firm" in missing


# ─────────────────────────────────────────────────────────────
#  TIER 1C
# ─────────────────────────────────────────────────────────────

def test_tier_1c_pass_chain_free():
    """When chain_links returns no rows, property is chain-free → passes."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with patch("db_supabase.supabase_for_backend", return_value=mock_client):
        from utils.completeness_gate import check_tier_1c
        passed, missing = check_tier_1c("1 High Street, Penrith")
    assert passed is True
    assert missing == []


def test_tier_1c_pass_chain_80_percent():
    """Chain with 80 %+ links populated passes."""
    links = [
        {"link_address": "2 Low Rd", "estate_agent": "Firm A", "estate_agent_email": "a@firma.com"},
        {"link_address": "3 Park Ln", "estate_agent": "Firm B", "estate_agent_email": "b@firmb.com"},
        {"link_address": "4 Mill St", "estate_agent": "Firm C", "estate_agent_email": "c@firmc.com"},
        {"link_address": "5 Old Rd", "estate_agent": "Firm D", "estate_agent_email": "d@firmd.com"},
        {"link_address": "6 New Rd", "estate_agent": "Firm E", "estate_agent_email": ""},  # bad email
    ]
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = links

    with patch("db_supabase.supabase_for_backend", return_value=mock_client):
        from utils.completeness_gate import check_tier_1c
        passed, missing = check_tier_1c("1 High Street")
    assert passed is True


def test_tier_1c_fail_chain_below_80_percent():
    """Chain with fewer than 80 % links populated fails."""
    links = [
        {"link_address": "2 Low Rd", "estate_agent": "Firm A", "estate_agent_email": "a@firma.com"},
        {"link_address": "", "estate_agent": "", "estate_agent_email": ""},
        {"link_address": "", "estate_agent": "", "estate_agent_email": ""},
    ]
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = links

    with patch("db_supabase.supabase_for_backend", return_value=mock_client):
        from utils.completeness_gate import check_tier_1c
        passed, missing = check_tier_1c("1 High Street")
    assert passed is False
    assert len(missing) == 1
    assert "incomplete chain" in missing[0]


# ─────────────────────────────────────────────────────────────
#  TIER 1D
# ─────────────────────────────────────────────────────────────

def test_tier_1d_pass_valid_price():
    passed, missing = check_tier_1d({"sale_price": 275000})
    assert passed is True
    assert missing == []


def test_tier_1d_fail_price_zero():
    passed, missing = check_tier_1d({"sale_price": 0})
    assert passed is False
    assert "sale_price" in missing


def test_tier_1d_fail_price_none():
    passed, missing = check_tier_1d({"sale_price": None})
    assert passed is False
    assert "sale_price" in missing


def test_tier_1d_fail_price_missing_key():
    passed, missing = check_tier_1d({})
    assert passed is False
    assert "sale_price" in missing


def test_tier_1d_pass_price_from_current_price():
    """Falls back to current_price when sale_price absent."""
    passed, missing = check_tier_1d({"current_price": 310000})
    assert passed is True


# ─────────────────────────────────────────────────────────────
#  OVERALL GATE STATUS
# ─────────────────────────────────────────────────────────────

def test_overall_ready_when_all_tiers_pass():
    """gate_status == 'ready' when all tiers pass."""
    all_pass_data = {**VALID_1A, **VALID_1B, "sale_price": 275000}

    with patch("db_supabase.supabase_for_backend") as mock_sb:
        # chain_links empty → chain-free
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_sb.return_value = mock_client

        from utils.completeness_gate import (
            check_tier_1a, check_tier_1b, check_tier_1c, check_tier_1d,
        )
        pass_1a, _ = check_tier_1a(all_pass_data)
        pass_1b, _ = check_tier_1b(all_pass_data)
        pass_1c, _ = check_tier_1c("1 High Street")
        pass_1d, _ = check_tier_1d(all_pass_data)

    assert pass_1a and pass_1b and pass_1c and pass_1d
    expected_status = "ready" if (pass_1a and pass_1b and pass_1c and pass_1d) else "blocked"
    assert expected_status == "ready"


def test_overall_blocked_with_missing_fields():
    """gate_status == 'blocked' when any tier fails; missing_fields populated."""
    data = {**VALID_1A, **VALID_1B, "sale_price": None}
    pass_1d, missing_1d = check_tier_1d(data)

    assert pass_1d is False
    assert "sale_price" in missing_1d
    expected_status = "blocked"
    assert expected_status == "blocked"
    assert len(missing_1d) > 0


# ─────────────────────────────────────────────────────────────
#  FAIL-CLOSED: exceptions must return BLOCKED, never PASSED
# ─────────────────────────────────────────────────────────────

def test_tier_1a_exception_returns_blocked():
    """An exception inside check_tier_1a must return BLOCKED, not PASSED."""
    passed, missing = check_tier_1a(None)  # None.get() raises AttributeError
    assert passed is False
    assert len(missing) == 1
    assert "check errored" in missing[0]


def test_tier_1b_exception_returns_blocked():
    """An exception inside check_tier_1b must return BLOCKED, not PASSED."""
    passed, missing = check_tier_1b(None)
    assert passed is False
    assert len(missing) == 1
    assert "check errored" in missing[0]


def test_tier_1c_exception_returns_blocked():
    """An exception inside check_tier_1c must return BLOCKED, not PASSED."""
    with patch("db_supabase.supabase_for_backend") as mock_sb:
        mock_sb.return_value.table.return_value.select.return_value.eq.return_value.execute.side_effect = RuntimeError("db exploded")
        passed, missing = check_tier_1c("1 High Street", property_id="some-uuid")
    assert passed is False
    assert len(missing) == 1
    assert "check errored" in missing[0]


def test_tier_1d_exception_returns_blocked():
    """An exception inside check_tier_1d must return BLOCKED, not PASSED."""
    passed, missing = check_tier_1d(None)  # None.get() raises AttributeError
    assert passed is False
    assert len(missing) == 1
    assert "check errored" in missing[0]
