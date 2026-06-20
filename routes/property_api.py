import requests as http_requests
from flask import Blueprint, jsonify, request

from utils.eatoc_api import eatoc_patch

property_api_bp = Blueprint("property_api", __name__)

_PIPELINE_PATCH_FIELDS = frozenset({"chain_status", "local_authority"})


@property_api_bp.route("/api/property/<prop_id>")
def api_property(prop_id):
    from routes.dashboard import _build_live_dashboard_data

    try:
        properties, _, _, _, _, _ = _build_live_dashboard_data()
        props_by_id = {p["id"]: p for p in properties}
        prop = props_by_id.get(prop_id)
        if not prop:
            return jsonify({"error": "Not found"}), 404
        return jsonify(prop)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@property_api_bp.route("/api/sales-pipeline/<pipe_id>", methods=["PATCH"])
def patch_sales_pipeline(pipe_id):
    """Update chain_status and/or local_authority on sales_pipeline (by row UUID)."""
    pipe_id = (pipe_id or "").strip()
    if not pipe_id:
        return jsonify({"error": "Invalid pipeline id"}), 400

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No data provided"}), 400

    updates = {}
    for key, val in data.items():
        if key not in _PIPELINE_PATCH_FIELDS:
            continue
        if key == "chain_status":
            v = (val or "stable").strip().lower()
            if v not in ("stable", "at_risk", "broken"):
                return jsonify({"error": "chain_status must be stable, at_risk, or broken"}), 400
            updates[key] = v
        elif key == "local_authority":
            updates[key] = (str(val).strip() or None) if val is not None else None

    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    # Resolve property_address from local sales_pipeline (read still OK per Brief 3).
    try:
        from db_supabase import supabase_for_backend

        row_res = (
            supabase_for_backend()
            .table("sales_pipeline")
            .select("property_address")
            .eq("id", pipe_id)
            .limit(1)
            .execute()
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not (row_res.data or []):
        return jsonify({"error": "Pipeline row not found"}), 404

    property_address = (row_res.data[0].get("property_address") or "").strip()
    if not property_address:
        return jsonify({"error": "Pipeline row has no property_address"}), 500

    patch_body = {"property_address": property_address, **updates}
    try:
        eatoc_patch("/api/nuvu/pipeline", patch_body)
    except http_requests.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else 500
        return jsonify({"error": str(e)}), status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"ok": True, "updated": list(updates.keys())})
