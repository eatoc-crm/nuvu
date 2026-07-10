#!/usr/bin/env python3
"""Render gate digest HTML samples for David's approval.

Read-only: evaluates current pipeline data in memory, writes local HTML files.
No Resend calls, no intake_queue writes.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.completeness_gate import PROGRESSION_STATUSES, evaluate_property_readonly
from utils.intake_notifications import render_gate_digest

SAMPLES_DIR = ROOT / "samples"

VALID_CONTACT = {
    "buyer_name": "John Smith",
    "buyer_email": "john@example.com",
    "buyer_phone": "07712 345678",
    "vendor_name": "Jane Doe",
    "vendor_email": "jane@example.com",
    "vendor_phone": "07900 111222",
    "buyer_solicitor_firm": "Green & Co Solicitors",
    "buyer_solicitor_email": "alice@greenco.com",
    "buyer_solicitor_phone": "01234 567890",
    "seller_solicitor_firm": "White Legal LLP",
    "seller_solicitor_email": "bob@whitelegal.com",
    "seller_solicitor_phone": "01234 098765",
    "sale_price": 275000,
}


def _write_sample(filename: str, subject: str, html_body: str) -> Path:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    path = SAMPLES_DIR / filename
    path.write_text(
        f"<!-- Subject: {subject} -->\n{html_body}",
        encoding="utf-8",
    )
    return path


def _blocked_candidates_from_pipeline() -> list[dict]:
    from db_supabase import supabase_for_backend

    client = supabase_for_backend()
    result = (
        client.table("sales_pipeline")
        .select("*")
        .in_("status", PROGRESSION_STATUSES)
        .eq("do_not_chase", False)
        .execute()
    )
    blocked: list[dict] = []
    for prop in result.data or []:
        candidate = evaluate_property_readonly(prop)
        if candidate and candidate["gate_status"] == "blocked":
            blocked.append(candidate)
    return blocked


def _synthetic_all_missing() -> dict:
    candidate = evaluate_property_readonly({"property_address": "Synthetic — all fields missing"})
    assert candidate is not None
    return candidate


def _synthetic_one_missing() -> dict:
    data = {
        **VALID_CONTACT,
        "property_address": "Synthetic — one field missing",
        "buyer_email": None,
    }
    candidate = evaluate_property_readonly(data)
    assert candidate is not None
    return candidate


def main() -> int:
    paths: list[Path] = []

    real_blocked = _blocked_candidates_from_pipeline()
    subject, body = render_gate_digest(real_blocked)
    paths.append(_write_sample("gate_digest_real_data.html", subject, body))

    all_missing = _synthetic_all_missing()
    subject, body = render_gate_digest([all_missing])
    paths.append(_write_sample("gate_digest_all_missing.html", subject, body))

    one_missing = _synthetic_one_missing()
    subject, body = render_gate_digest([one_missing])
    paths.append(_write_sample("gate_digest_one_missing.html", subject, body))

    print(f"Rendered {len(paths)} sample(s):")
    for path in paths:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
