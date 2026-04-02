import os

from flask import Blueprint, jsonify, request

import shared  # loads shared config and provides `sb`
from shared import sb
from routes.progression import _send_welcome_emails

intake_bp = Blueprint("intake", __name__)


@intake_bp.route("/api/intake", methods=["POST"])
def api_intake():
    """Receive a property payload when status changes (Under Offer or reversal)."""
    # --- Auth ---
    expected_key = os.environ.get("NUVU_API_KEY", "dbe-nuvu-2026")
    provided_key = request.headers.get("X-NUVU-API-KEY", "")
    if not provided_key or provided_key != expected_key:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True)
    if not data or not data.get("property_address", "").strip():
        return jsonify({"error": "property_address is required"}), 400

    addr = data["property_address"].strip()
    alto_ref = (data.get("alto_ref") or "").strip() or None
    incoming_status = (data.get("status") or "").strip()

    # --- Handle reversal: For Sale = sale fell through ---
    if incoming_status == "For Sale":
        update_row = {"status": "For Sale"}
        try:
            if alto_ref:
                sb.table("sales_pipeline").update(update_row).eq(
                    "alto_ref", alto_ref
                ).execute()
            else:
                sb.table("sales_pipeline").update(update_row).eq(
                    "property_address", addr
                ).execute()
        except Exception as e:
            return jsonify({"error": f"sales_pipeline reversal failed: {e}"}), 500
        return (
            jsonify({"success": True, "property": addr, "action": "reversed"}),
            200,
        )

    # --- Under Offer flow (existing behaviour) ---
    date_agreed = data.get("date_agreed") or None

    # --- Upsert sales_pipeline ---
    pipeline_row = {
        "property_address": addr,
        "postcode": data.get("postcode") or None,
        "current_price": data.get("current_price") or None,
        "fee": data.get("fee") or None,
        "fee_pct": data.get("fee_pct") or None,
        "date_agreed": date_agreed,
        "buyers_solicitor": data.get("buyers_solicitor") or None,
        "vendors_solicitor": data.get("vendors_solicitor") or None,
        "negotiator": data.get("negotiator") or None,
        "agreed_by": data.get("agreed_by") or None,
        "our_ref": data.get("our_ref") or None,
        "alto_ref": alto_ref,
        "status": "Under Offer",
    }

    conflict_col = "alto_ref" if alto_ref else "property_address"
    try:
        sb.table("sales_pipeline").upsert(pipeline_row, on_conflict=conflict_col).execute()
    except Exception as e:
        return jsonify({"error": f"sales_pipeline upsert failed: {e}"}), 500

    # --- Upsert sales_progression ---
    progression_row = {
        "property_address": addr,
        "status": "Under Offer",
        "offer_accepted": date_agreed,
        "buyer_name": data.get("buyer_name") or None,
        "buyer_email": data.get("buyer_email") or None,
        "buyer_phone": data.get("buyer_phone") or None,
        "vendor_name": data.get("vendor_name") or None,
        "vendor_email": data.get("vendor_email") or None,
        "vendor_phone": data.get("vendor_phone") or None,
        "notes": data.get("notes") or None,
    }

    try:
        sb.table("sales_progression").upsert(
            progression_row, on_conflict="property_address"
        ).execute()
    except Exception as e:
        return jsonify({"error": f"sales_progression upsert failed: {e}"}), 500

    # ── Welcome Engine: send 5 outbound emails ──────────────
    _send_welcome_emails(data)

    return jsonify({"success": True, "property": addr}), 200

