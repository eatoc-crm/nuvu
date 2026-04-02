from flask import Blueprint, jsonify

property_api_bp = Blueprint("property_api", __name__)


@property_api_bp.route("/api/property/<prop_id>")
def api_property(prop_id):
    from routes.dashboard import _build_live_dashboard_data

    try:
        properties, _, _, _ = _build_live_dashboard_data()
        props_by_id = {p["id"]: p for p in properties}
        prop = props_by_id.get(prop_id)
        if not prop:
            return jsonify({"error": "Not found"}), 404
        return jsonify(prop)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

