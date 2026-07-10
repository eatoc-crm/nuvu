"""Rendering tests for the completeness gate digest email."""

from __future__ import annotations

import re

from utils.field_labels import FIELD_LABELS
from utils.intake_notifications import render_gate_digest


def _candidate(address: str, missing_fields: list[str]) -> dict:
    return {
        "property_address": address,
        "gate_status": "blocked",
        "property_data": {},
        "missing_fields": missing_fields,
        "tiers": {"1a": False, "1b": True, "1c": True, "1d": True},
    }


def test_digest_renders_full_partial_and_empty_missing_lists():
    cases = [
        [_candidate("1 High Street", ["buyer_email", "sale_price"])],
        [_candidate("2 Low Road", ["buyer_phone"])],
        [_candidate("3 Park Lane", [])],
    ]
    for candidates in cases:
        subject, body = render_gate_digest(candidates)
        assert subject
        assert "<html" in body.lower()
        assert "NUVU checks continuously" in body


def test_digest_uses_human_labels_not_raw_column_names():
    raw_fields = ["buyer_email", "seller_solicitor_phone", "sale_price"]
    _, body = render_gate_digest([_candidate("1 High Street", raw_fields)])

    for field in raw_fields:
        assert field not in body

    assert "Buyer email" in body
    assert "Seller solicitor phone" in body
    assert "Sale price" in body


def test_digest_never_leaks_none_or_collection_literals():
    _, body = render_gate_digest(
        [
            _candidate("1 High Street", ["buyer_email"]),
            _candidate("2 Low Road", ["incomplete chain — 1 of 5 links populated"]),
        ]
    )

    assert "None" not in body
    assert "{" not in body
    assert "}" not in body
    assert "[" not in body
    assert "]" not in body


def test_digest_html_escapes_special_characters_in_address():
    address = "Flat 1 <Rose & Crown>, Penrith"
    _, body = render_gate_digest([_candidate(address, ["buyer_email"])])

    assert address not in body
    assert "Flat 1 &lt;Rose &amp; Crown&gt;, Penrith" in body


def test_digest_subject_count_matches_property_count():
    candidates = [
        _candidate(f"{idx} Example Street", ["buyer_email"])
        for idx in range(1, 4)
    ]
    subject, body = render_gate_digest(candidates)

    assert subject == "NUVU — 3 properties need attention"
    assert body.count("<strong>") == 3
    match = re.search(r"(\d+) properties need attention", body)
    assert match is not None
    assert int(match.group(1)) == 3


def test_field_labels_cover_every_gate_checked_field():
    gate_fields = {
        "buyer_name",
        "buyer_email",
        "buyer_phone",
        "vendor_name",
        "vendor_email",
        "vendor_phone",
        "buyer_solicitor_firm",
        "buyer_solicitor_email",
        "buyer_solicitor_phone",
        "seller_solicitor_firm",
        "seller_solicitor_email",
        "seller_solicitor_phone",
        "sale_price",
    }
    assert gate_fields.issubset(set(FIELD_LABELS))
