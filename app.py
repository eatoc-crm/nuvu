"""
NUVU Sales Progression Dashboard
==================================
A complete Flask-based sales progression tracker for NUVU Estate Agency.

Run:
    pip install flask
    python app.py

Then open http://127.0.0.1:5000 in your browser.
"""

from flask import Flask
import os
import secrets
from datetime import timedelta

import shared

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_urlsafe(32))
app.permanent_session_lifetime = timedelta(hours=8)

from routes.auth import auth_bp

app.register_blueprint(auth_bp)

from routes.progression import progression_bp
from routes.intake import intake_bp

app.register_blueprint(progression_bp)
app.register_blueprint(intake_bp)

from routes.crm import crm_bp

app.register_blueprint(crm_bp)

from routes.dashboard import dashboard_bp

app.register_blueprint(dashboard_bp)

from routes.property_api import property_api_bp

app.register_blueprint(property_api_bp)

if __name__ == "__main__":
    _port = int(os.environ.get("PORT", "5000"))
    print()
    print("  NUVU Sales Progression Dashboard")
    print("  " + "\u2500" * 34)
    print(f"  http://127.0.0.1:{_port}")
    print()
    app.run(debug=True, port=_port)
