from flask import Blueprint, jsonify, request

import shared  # loads shared config and provides `sb`
from shared import sb, require_nuvu_api_key
from routes.progression import _send_welcome_emails

intake_bp = Blueprint("intake", __name__)


# Status values that must not receive EATOC note feed items (not in active progression).
_INACTIVE_PROGRESSION_STATUSES = frozenset(
    {
        "available",
        "withdrawn",
        "for sale",
        "fallen through",
        "completed",
    }
)


@intake_bp.route("/api/intake", methods=["POST"])
def api_intake():
    """Receive a property payload when status changes (Under Offer or reversal)."""
    # --- Auth ---
    auth_err = require_nuvu_api_key()
    if auth_err:
        return auth_err

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


@intake_bp.route("/api/update", methods=["POST"])
def api_update():
    """Receive real-time EATOC buyer/seller card notes; store as inbound channel 3."""
    auth_err = require_nuvu_api_key()
    if auth_err:
        return auth_err

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    addr = (data.get("property_address") or "").strip()
    alto_ref = (data.get("alto_ref") or "").strip()
    note_text = (data.get("note_text") or "").strip()
    note_source = (data.get("note_source") or "").strip()
    note_date = (data.get("note_date") or "").strip()
    staff_initials = (data.get("staff_initials") or "").strip()

    if not note_text:
        return jsonify({"error": "note_text is required"}), 400
    if not note_source:
        return jsonify({"error": "note_source is required"}), 400
    if not note_date:
        return jsonify({"error": "note_date is required"}), 400
    if not addr and not alto_ref:
        return jsonify(
            {"error": "property_address or alto_ref is required for lookup"}
        ), 400

    def _select_progression_row():
        if addr:
            r = (
                sb.table("sales_progression")
                .select("id,status,property_address")
                .eq("property_address", addr)
                .limit(1)
                .execute()
            )
            if r.data:
                return r.data[0]
        if alto_ref:
            pipe = (
                sb.table("sales_pipeline")
                .select("property_address")
                .eq("alto_ref", alto_ref)
                .limit(1)
                .execute()
            )
            if not pipe.data:
                return None
            resolved_addr = (pipe.data[0].get("property_address") or "").strip()
            if not resolved_addr:
                return None
            r = (
                sb.table("sales_progression")
                .select("id,status,property_address")
                .eq("property_address", resolved_addr)
                .limit(1)
                .execute()
            )
            if r.data:
                return r.data[0]
        return None

    try:
        prog = _select_progression_row()
    except Exception as e:
        return jsonify({"error": f"lookup failed: {e}"}), 500

    if not prog:
        return (
            jsonify(
                {
                    "error": "Property not found",
                    "property_address": addr or None,
                    "alto_ref": alto_ref or None,
                }
            ),
            404,
        )

    st = (prog.get("status") or "").strip().lower()
    if not st or st in _INACTIVE_PROGRESSION_STATUSES:
        return (
            jsonify({"error": "Property not in active progression"}),
            403,
        )

    body_preview = note_text[:500]
    subject = f"EATOC Note — {note_source}"

    insert_row = {
        "channel": 3,
        "sender_name": staff_initials or None,
        "subject": subject,
        "body_preview": body_preview,
        "received_at": note_date,
        "property_id": prog["id"],
        "matched_by": "eatoc_feed",
        "match_confidence": "confirmed",
        "human_confirmed": False,
        "raw_payload": data,
    }

    try:
        ins = sb.table("inbound_emails").insert(insert_row).execute()
    except Exception as e:
        return jsonify({"error": f"insert failed: {e}"}), 500

    rows = ins.data or []
    if not rows:
        return jsonify({"error": "insert returned no row"}), 500

    email_id = rows[0].get("id")
    return jsonify({"status": "received", "email_id": str(email_id)}), 200


_DUPLICATE_RESOLUTIONS = frozenset({"ignore", "keep_both", "merge"})


@intake_bp.route("/api/duplicates", methods=["GET"])
def api_duplicates_list():
    """List inbound emails flagged as duplicates and awaiting human resolution."""
    auth_err = require_nuvu_api_key()
    if auth_err:
        return auth_err

    try:
        r = (
            sb.table("inbound_emails")
            .select(
                "id,channel,sender_email,sender_name,subject,body_preview,"
                "received_at,property_id,duplicate_of,created_at"
            )
            .eq("is_duplicate", True)
            .is_("duplicate_resolution", "null")
            .order("received_at", desc=True)
            .execute()
        )
    except Exception as e:
        return jsonify({"error": f"query failed: {e}"}), 500

    rows = r.data or []
    duplicates = []
    for row in rows:
        duplicates.append(
            {
                "id": str(row["id"]),
                "channel": row.get("channel"),
                "sender_email": row.get("sender_email"),
                "sender_name": row.get("sender_name"),
                "subject": row.get("subject"),
                "body_preview": row.get("body_preview"),
                "received_at": row.get("received_at"),
                "property_id": str(row["property_id"])
                if row.get("property_id") is not None
                else None,
                "duplicate_of": str(row["duplicate_of"])
                if row.get("duplicate_of") is not None
                else None,
                "created_at": row.get("created_at"),
            }
        )

    return jsonify({"duplicates": duplicates, "count": len(duplicates)}), 200


@intake_bp.route("/api/duplicates/<email_id>/resolve", methods=["POST"])
def api_duplicates_resolve(email_id):
    """Record human resolution for a flagged duplicate inbound email."""
    auth_err = require_nuvu_api_key()
    if auth_err:
        return auth_err

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    resolution = (data.get("resolution") or "").strip()
    if resolution not in _DUPLICATE_RESOLUTIONS:
        return jsonify({"error": "Invalid resolution"}), 400

    try:
        r = (
            sb.table("inbound_emails")
            .select("id,is_duplicate,duplicate_resolution")
            .eq("id", email_id)
            .limit(1)
            .execute()
        )
    except Exception as e:
        return jsonify({"error": f"lookup failed: {e}"}), 500

    if not r.data:
        return jsonify({"error": "Not found"}), 404

    row = r.data[0]
    if row.get("is_duplicate") is not True:
        return jsonify({"error": "Not a duplicate"}), 400
    if row.get("duplicate_resolution") is not None:
        return jsonify({"error": "Already resolved"}), 400

    try:
        sb.table("inbound_emails").update(
            {"duplicate_resolution": resolution}
        ).eq("id", email_id).execute()
    except Exception as e:
        return jsonify({"error": f"update failed: {e}"}), 500

    return (
        jsonify(
            {
                "status": "resolved",
                "id": str(row["id"]),
                "resolution": resolution,
            }
        ),
        200,
    )

