"""
NUVU Completeness Gate — utils/completeness_gate.py

Runs after every adapter sync cycle.  For each property in sales_pipeline,
evaluates four tiers of completeness and upserts the result into intake_queue.

Kill switch: COMPLETENESS_GATE_ENABLED env var (default: true).
If set to "false" the gate exits immediately — adapter sync continues normally.

Tier summary
────────────
1A  Buyer & seller contact details (name, email, phone × 2)
1B  Both solicitors (name, firm, email, phone × 2)
1C  Chain completeness — chain-free always passes; chains need ≥80 % links
1D  Sale price required (> 0); other transaction details captured if present
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
#  VALIDATORS
# ─────────────────────────────────────────────────────────────

def validate_email(value) -> bool:
    """Basic email format check: must contain @ and a dot after @."""
    if not value or not isinstance(value, str):
        return False
    v = value.strip()
    if "@" not in v:
        return False
    parts = v.split("@", 1)
    return "." in parts[1] if len(parts) == 2 else False


def validate_phone(value) -> bool:
    """Non-empty after stripping spaces, dashes, parens, and +44 prefix."""
    if not value or not isinstance(value, str):
        return False
    stripped = re.sub(r"[\s\-\(\)\+]", "", value)
    stripped = re.sub(r"^44", "", stripped)
    return len(stripped) >= 7 and stripped.isdigit()


def _non_empty(value) -> bool:
    return bool(value and str(value).strip())


# ─────────────────────────────────────────────────────────────
#  TIER CHECKS
# ─────────────────────────────────────────────────────────────

def check_tier_1a(property_data: dict) -> tuple[bool, list[str]]:
    """Tier 1A: buyer & seller name, email, phone."""
    missing: list[str] = []

    checks = [
        ("buyer_name",    _non_empty,    property_data.get("buyer_name")),
        ("buyer_email",   validate_email, property_data.get("buyer_email")),
        ("buyer_phone",   validate_phone, property_data.get("buyer_phone")),
        ("vendor_name",   _non_empty,    property_data.get("vendor_name")),
        ("vendor_email",  validate_email, property_data.get("vendor_email")),
        ("vendor_phone",  validate_phone, property_data.get("vendor_phone")),
    ]

    for field, validator, value in checks:
        if not validator(value):
            missing.append(field)

    return (len(missing) == 0, missing)


def check_tier_1b(property_data: dict) -> tuple[bool, list[str]]:
    """Tier 1B: buyer's and seller's solicitor details.

    Firm name: buyer_solicitor / vendor_solicitor (text name field).
    Email:     buyer_solicitor_email / seller_solicitor_email.
    Phone:     buyer_solicitor_phone / seller_solicitor_phone.
    Contact person (buyer_solicitor_contact_name / seller_solicitor_contact_name) is
    stored when available but does NOT block the gate.
    """
    missing: list[str] = []

    checks = [
        (
            "buyer_solicitor_firm",
            _non_empty,
            property_data.get("buyer_solicitor_firm")
            or property_data.get("buyer_solicitor")
            or property_data.get("buyers_solicitor"),
        ),
        ("buyer_solicitor_email",  validate_email,  property_data.get("buyer_solicitor_email")),
        ("buyer_solicitor_phone",  validate_phone,  property_data.get("buyer_solicitor_phone")),
        (
            "seller_solicitor_firm",
            _non_empty,
            property_data.get("seller_solicitor_firm")
            or property_data.get("vendor_solicitor")
            or property_data.get("vendors_solicitor"),
        ),
        ("seller_solicitor_email", validate_email,  property_data.get("seller_solicitor_email")),
        ("seller_solicitor_phone", validate_phone,  property_data.get("seller_solicitor_phone")),
    ]

    for field, validator, value in checks:
        if not validator(value):
            missing.append(field)

    return (len(missing) == 0, missing)


def check_tier_1c(property_address: str) -> tuple[bool, list[str]]:
    """Tier 1C: chain completeness.

    Chain-free → always passes.
    Chain exists → require ≥ 80 % of links to have: link_address, estate_agent, estate_agent_email.
    Currently chain_links is always empty, so all properties pass as chain-free.
    """
    try:
        from db_supabase import supabase_for_backend

        client = supabase_for_backend()
        result = (
            client.table("chain_links")
            .select("id,link_address,estate_agent,estate_agent_email")
            .eq("property_id", property_address)
            .execute()
        )
        links = result.data or []

        if not links:
            return (True, [])

        total = len(links)
        populated = sum(
            1 for link in links
            if _non_empty(link.get("link_address"))
            and _non_empty(link.get("estate_agent"))
            and validate_email(link.get("estate_agent_email"))
        )

        pct = populated / total if total > 0 else 1.0
        if pct >= 0.80:
            return (True, [])
        else:
            missing_msg = f"incomplete chain — {populated} of {total} links populated"
            return (False, [missing_msg])

    except Exception as exc:
        log.warning("[completeness_gate] check_tier_1c error for '%s': %s", property_address, exc)
        return (True, [])  # fail open — do not block on chain data errors


def check_tier_1d(property_data: dict) -> tuple[bool, list[str]]:
    """Tier 1D: sale_price required; other transaction details captured but optional."""
    missing: list[str] = []

    sale_price = (
        property_data.get("sale_price")
        or property_data.get("agreed_price")
        or property_data.get("current_price")
    )

    try:
        price_val = float(sale_price) if sale_price is not None else 0
    except (TypeError, ValueError):
        price_val = 0

    if price_val <= 0:
        missing.append("sale_price")

    return (len(missing) == 0, missing)


# ─────────────────────────────────────────────────────────────
#  ORCHESTRATOR
# ─────────────────────────────────────────────────────────────

def run_completeness_gate() -> None:
    """Main entry point. Called from adapter_sync after every sync cycle.

    Kill switch: COMPLETENESS_GATE_ENABLED=false → returns immediately.
    All exceptions are caught; a gate failure must never crash the sync.
    """
    if os.environ.get("COMPLETENESS_GATE_ENABLED", "true").lower() != "true":
        log.debug("[completeness_gate] disabled — skipping")
        return

    try:
        from db_supabase import supabase_for_backend
        from utils.events import emit_event
        from utils.intake_notifications import send_intake_notification

        client = supabase_for_backend()

        result = client.table("sales_pipeline").select("*").eq("status", "active").execute()
        properties = result.data or []

        if not properties:
            log.info("[completeness_gate] no properties in sales_pipeline — nothing to check")
            return

        log.info("[completeness_gate] evaluating %d properties", len(properties))

        for prop in properties:
            try:
                _evaluate_property(prop, client, emit_event, send_intake_notification)
            except Exception as exc:
                addr = prop.get("property_address", "unknown")
                log.warning("[completeness_gate] error evaluating '%s': %s", addr, exc)

        log.info("[completeness_gate] gate evaluation complete")

    except Exception as exc:
        log.warning("[completeness_gate] run_completeness_gate unexpected error: %s", exc)


def _evaluate_property(prop: dict, client, emit_event_fn, notify_fn) -> None:
    addr = (prop.get("property_address") or "").strip()
    if not addr:
        return

    # Run tiers
    pass_1a, miss_1a = check_tier_1a(prop)
    pass_1b, miss_1b = check_tier_1b(prop)
    pass_1c, miss_1c = check_tier_1c(addr)
    pass_1d, miss_1d = check_tier_1d(prop)

    all_pass = pass_1a and pass_1b and pass_1c and pass_1d
    new_status = "ready" if all_pass else "blocked"
    all_missing = miss_1a + miss_1b + miss_1c + miss_1d

    # Capture optional transaction details regardless of gate outcome
    sale_price = (
        prop.get("sale_price")
        or prop.get("agreed_price")
        or prop.get("current_price")
    )
    completion_target = prop.get("est_completion") or prop.get("completion_target")
    special_conditions = prop.get("special_conditions")

    # Fetch current record (if any)
    existing = (
        client.table("intake_queue")
        .select("gate_status,notification_sent,approved_at")
        .eq("property_address", addr)
        .execute()
    )
    current = (existing.data or [None])[0]
    prev_status = current["gate_status"] if current else None

    # If approved, never regress — skip further processing
    if prev_status in ("approved", "rejected"):
        return

    # Determine whether to emit events / notifications
    status_changed = (prev_status != new_status)
    is_new = (prev_status is None)

    # Upsert
    row = {
        "property_address":  addr,
        "gate_status":       new_status,
        "tier_1a_pass":      pass_1a,
        "tier_1b_pass":      pass_1b,
        "tier_1c_pass":      pass_1c,
        "tier_1d_pass":      pass_1d,
        "missing_fields":    all_missing if all_missing else None,
        "sale_price":        float(sale_price) if sale_price else None,
        "completion_target": str(completion_target) if completion_target else None,
        "special_conditions": str(special_conditions) if special_conditions else None,
        "updated_at":        datetime.now(timezone.utc).isoformat(),
    }

    # Reset notification flag on status change so the new status notifies
    if status_changed:
        row["notification_sent"] = False

    client.table("intake_queue").upsert(row, on_conflict="property_address").execute()

    # Emit event only on first appearance or status change (avoids spam)
    if is_new or status_changed:
        tiers = {"1a": pass_1a, "1b": pass_1b, "1c": pass_1c, "1d": pass_1d}
        if all_pass:
            summary = f"Completeness gate PASSED — awaiting approval"
        else:
            summary = f"Completeness gate BLOCKED — missing: {all_missing}"

        emit_event_fn(
            event_type="gate_raised",
            property_address=addr,
            actor="system",
            summary=summary,
            payload={"tiers": tiers, "gate_status": new_status, "missing_fields": all_missing},
        )

        # Send notification (fail silently inside notify_fn)
        try:
            notify_fn(addr, new_status, prop, all_missing, tiers)
        except Exception as exc:
            log.warning("[completeness_gate] notification failed for '%s': %s", addr, exc)
