from flask import Blueprint, jsonify, request

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

    try:
        from db_supabase import supabase_for_backend

        res = (
            supabase_for_backend()
            .table("sales_pipeline")
            .update(updates)
            .eq("id", pipe_id)
            .select("id")
            .execute()
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not (res.data or []):
        return (
            jsonify(
                {
                    "error": (
                        "No sales_pipeline row was updated. "
                        "Check id and SUPABASE_SERVICE_ROLE_KEY."
                    )
                }
            ),
            409,
        )

    return jsonify({"ok": True, "updated": list(updates.keys())})
