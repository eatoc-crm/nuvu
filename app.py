"""
NUVU Sales Progression Dashboard
==================================
A complete Flask-based sales progression tracker for NUVU Estate Agency.

Run:
    pip install flask
    python app.py

Then open http://127.0.0.1:5000 in your browser.
"""

from flask import Flask, render_template_string, jsonify, session, redirect, url_for, request
import json
import os
import requests
from database import get_db, init_db
from connectors.connector_manager import ConnectorManager
from ai_parser import parse_note, apply_ai_results
from email_engine import suggest_emails, generate_email, TEMPLATES, TONE_CONFIG
from connectors.sync_outbound import push_note_to_crm, push_milestone_to_crm, push_status_to_crm
from email_parser import process_email, SAMPLE_EMAILS
from completion_engine import calculate_completion, recalculate_property, recalculate_all

app = Flask(__name__, static_folder="static")
app.secret_key = "nuvu-sales-progression-2026-temp-key"

# Ensure DB tables exist (including sync_log)
init_db()

# Connector manager — Alto auto-registered in stub mode
sync_manager = ConnectorManager()


# ─────────────────────────────────────────────────────────────
#  PROPERTY DATA — loaded from SQLite database
# ─────────────────────────────────────────────────────────────

STATUS_LABELS = {"on-track": "ON TRACK", "at-risk": "AT RISK", "stalled": "STALLED"}


def load_properties():
    """Load all properties from the database, returning a list of dicts
    matching the exact structure the templates expect."""
    db = get_db()

    rows = db.execute("""
        SELECT
            p.*,
            b.name   AS buyer_name,
            b.phone  AS buyer_phone,
            bs.name  AS buyer_solicitor,
            bs.phone AS buyer_sol_phone,
            ss.name  AS seller_solicitor,
            ss.phone AS seller_sol_phone
        FROM properties p
        LEFT JOIN buyers  b  ON b.property_id  = p.id
        LEFT JOIN sellers se ON se.property_id  = p.id
        LEFT JOIN solicitors bs ON b.solicitor_id  = bs.id
        LEFT JOIN solicitors ss ON se.solicitor_id = ss.id
        ORDER BY p.id
    """).fetchall()

    # Pre-fetch all milestones grouped by property_id
    all_milestones = db.execute(
        "SELECT * FROM milestones ORDER BY property_id, sort_order"
    ).fetchall()
    ms_by_prop = {}
    for m in all_milestones:
        ms_by_prop.setdefault(m["property_id"], []).append(m)

    properties = []
    for r in rows:
        milestones = []
        for m in ms_by_prop.get(r["id"], []):
            if m["is_complete"] == 1:
                done = True
            elif m["is_complete"] is None:
                done = None
            else:
                done = False
            milestones.append({"label": m["milestone_name"], "done": done, "stage": m["milestone_stage"], "completed_date": m["completed_date"]})

        card_checks = json.loads(r["card_checks"]) if r["card_checks"] else []

        # ── Completion engine calculation ─────────────────────
        ce = calculate_completion(r["slug"])
        if "error" in ce:
            # Fallback to DB values if engine can't calculate
            ce_progress = r["progress_percentage"]
            ce_days_remaining = r["target_days"]
            ce_status = r["status"]
            ce_expected = r["completion_date"] or ""
            ce_adjustments = []
            ce_days_elapsed = r["duration_days"]
        else:
            ce_progress = ce["progress_percentage"]
            ce_days_remaining = ce["days_remaining"]
            ce_status = ce["status"]
            ce_expected = ce["expected_completion_date"]
            ce_adjustments = ce["adjustments_applied"]
            ce_days_elapsed = ce["days_elapsed"]

        prop = {
            "db_id": r["id"],
            "id": r["slug"],
            "address": r["address"],
            "location": r["location"],
            "price": r["price"],
            "status": ce_status,
            "status_label": STATUS_LABELS.get(ce_status, "ON TRACK"),
            "progress": ce_progress,
            "duration_days": ce_days_elapsed,
            "target_days": ce_days_remaining,
            "days_since_update": r["days_since_update"],
            "card_checks": card_checks,
            "buyer": r["buyer_name"],
            "buyer_phone": r["buyer_phone"],
            "buyer_solicitor": r["buyer_solicitor"],
            "buyer_sol_phone": r["buyer_sol_phone"],
            "seller_solicitor": r["seller_solicitor"],
            "seller_sol_phone": r["seller_sol_phone"],
            "offer_date": r["offer_accepted_date"],
            "memo_sent": r["memo_sent_date"],
            "searches_ordered": r["searches_ordered"],
            "searches_received": r["searches_received"],
            "enquiries_raised": r["enquiries_raised"],
            "enquiries_answered": r["enquiries_answered"],
            "mortgage_offered": r["mortgage_offered"],
            "survey_booked": r["survey_booked"],
            "survey_complete": r["survey_complete"],
            "exchange_target": r["exchange_date"],
            "completion_target": r["completion_date"],
            "chain": r["chain_position"],
            "alert": r["alert"],
            "next_action": r["next_action"],
            "image_bg": r["image_bg"],
            "image_url": r["hero_image"],
            "milestones": milestones,
            # Completion engine fields
            "ce_days_remaining": ce_days_remaining,
            "ce_expected_completion": ce_expected,
            "ce_adjustments": ce_adjustments,
            "ce_adjustment_count": len(ce_adjustments),
        }
        properties.append(prop)

    db.close()
    return properties


def get_props_by_id():
    """Return a dict of properties indexed by their slug (id)."""
    return {p["id"]: p for p in load_properties()}


# Keep the original PROPERTIES name available for migrate.py import compatibility
PROPERTIES = [
    # ── NEEDS ACTION ────────────────────────────────────────
    {
        "id": "stalled",
        "address": "Regis Garth",
        "location": "Great Salkeld",
        "price": 425000,
        "status": "stalled",
        "status_label": "STALLED",
        "progress": 42,
        "duration_days": 47,
        "target_days": 60,
        "days_since_update": 18,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": False}
        ],
        "buyer": "Mr & Mrs Thornton",
        "buyer_phone": "07712 345678",
        "buyer_solicitor": "Harper & Lane, Kendal",
        "buyer_sol_phone": "01539 720400",
        "seller_solicitor": "JW Dickinson, Penrith",
        "seller_sol_phone": "01768 862631",
        "offer_date": "2025-12-24",
        "memo_sent": "2025-12-31",
        "searches_ordered": "2026-01-06",
        "searches_received": "2026-01-22",
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-01-10",
        "survey_complete": "2026-01-24",
        "exchange_target": "2026-03-14",
        "completion_target": "2026-03-28",
        "chain": "Thorntons selling 8 Wordsworth St (buyer found). Onward purchase: none.",
        "alert": "Buyer solicitor unresponsive for 18 days. Enquiries not yet raised. Mortgage offer still outstanding.",
        "next_action": "Chase Harper & Lane for enquiry responses and mortgage update.",
        "image_bg": "linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%)",
        "image_url": "https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "at-risk-1",
        "address": "Mill Brow",
        "location": "Armathwaite",
        "price": 375000,
        "status": "at-risk",
        "status_label": "AT RISK",
        "progress": 65,
        "duration_days": 39,
        "target_days": 60,
        "days_since_update": 9,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": True}
        ],
        "buyer": "Dr Patel",
        "buyer_phone": "07891 234567",
        "buyer_solicitor": "Cartmell Shepherd, Carlisle",
        "buyer_sol_phone": "01228 516666",
        "seller_solicitor": "JW Dickinson, Penrith",
        "seller_sol_phone": "01768 862631",
        "offer_date": "2026-01-01",
        "memo_sent": "2026-01-07",
        "searches_ordered": "2026-01-10",
        "searches_received": "2026-01-28",
        "enquiries_raised": "2026-01-30",
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-01-12",
        "survey_complete": "2026-01-26",
        "exchange_target": "2026-03-07",
        "completion_target": "2026-03-21",
        "chain": "Dr Patel is a first-time buyer (no chain below). Sellers relocating to France \u2014 need completion before April.",
        "alert": "Survey flagged damp in west gable wall. Buyer requesting \u00a312,000 price reduction \u2014 sellers have not responded.",
        "next_action": "Call sellers to discuss retention or price adjustment before buyer walks.",
        "image_bg": "linear-gradient(135deg,#2d3436 0%,#636e72 100%)",
        "image_url": "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": True},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "at-risk-2",
        "address": "Maulds Meaburn",
        "location": "Nr Appleby",
        "price": 595000,
        "status": "at-risk",
        "status_label": "AT RISK",
        "progress": 38,
        "duration_days": 23,
        "target_days": 60,
        "days_since_update": 12,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": False},
            {"label": "Enquiries Raised", "done": False}
        ],
        "buyer": "Mr & Mrs Hewitson",
        "buyer_phone": "07456 789012",
        "buyer_solicitor": "Oglethorpe Sturton & Gillibrand, Lancaster",
        "buyer_sol_phone": "01524 386500",
        "seller_solicitor": "Burnetts, Penrith",
        "seller_sol_phone": "01768 890570",
        "offer_date": "2026-01-17",
        "memo_sent": "2026-01-23",
        "searches_ordered": "2026-01-27",
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": "2026-03-28",
        "completion_target": "2026-04-11",
        "chain": "Hewitsons selling in Kirkby Stephen (under offer). Upward chain: vendor moving to rented.",
        "alert": "Local authority searches delayed \u2014 Eden DC backlog estimated 4 more weeks. Survey not yet booked.",
        "next_action": "Escalate search delay with Eden DC planning. Chase buyer solicitor to book survey.",
        "image_bg": "linear-gradient(135deg,#355c7d 0%,#6c5b7b 50%,#c06c84 100%)",
        "image_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": False},
            {"label": "Survey Complete", "done": False},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "kirk-thore",
        "address": "Kirkby Thore",
        "location": "Nr Appleby",
        "price": 285000,
        "status": "stalled",
        "status_label": "STALLED",
        "progress": 30,
        "duration_days": 52,
        "target_days": 60,
        "days_since_update": 21,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": False},
            {"label": "Enquiries Raised", "done": False}
        ],
        "buyer": "Mr Henderson",
        "buyer_phone": "07654 321098",
        "buyer_solicitor": "Cartmell Shepherd, Carlisle",
        "buyer_sol_phone": "01228 516666",
        "seller_solicitor": "Burnetts, Penrith",
        "seller_sol_phone": "01768 890570",
        "offer_date": "2025-12-19",
        "memo_sent": "2025-12-24",
        "searches_ordered": "2026-01-02",
        "searches_received": "2026-01-20",
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": "2026-03-07",
        "completion_target": "2026-03-21",
        "chain": "Henderson selling in Brough (chain free). Vendor moving to son\u2019s property.",
        "alert": "No survey booked after 52 days. Buyer solicitor not responding to chaser calls.",
        "next_action": "Direct call to Mr Henderson to confirm continued interest and chase survey.",
        "image_bg": "linear-gradient(135deg,#2c3e50 0%,#3498db 100%)",
        "image_url": "https://images.unsplash.com/photo-1605276374104-dee2a0ed3cd6?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": False},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "temple-sowerby",
        "address": "Temple Sowerby",
        "location": "Nr Penrith",
        "price": 340000,
        "status": "at-risk",
        "status_label": "AT RISK",
        "progress": 50,
        "duration_days": 35,
        "target_days": 60,
        "days_since_update": 10,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": False}
        ],
        "buyer": "Mrs Campbell",
        "buyer_phone": "07789 012345",
        "buyer_solicitor": "Bendles, Carlisle",
        "buyer_sol_phone": "01228 522215",
        "seller_solicitor": "JW Dickinson, Penrith",
        "seller_sol_phone": "01768 862631",
        "offer_date": "2026-01-05",
        "memo_sent": "2026-01-12",
        "searches_ordered": "2026-01-15",
        "searches_received": "2026-02-02",
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-01-18",
        "survey_complete": "2026-02-01",
        "exchange_target": "2026-03-14",
        "completion_target": "2026-03-28",
        "chain": "Mrs Campbell downsizing from family home. No onward chain \u2014 moving to rented.",
        "alert": "Buyer\u2019s mortgage valuation came in \u00a315,000 below asking. Lender may reduce offer.",
        "next_action": "Negotiate with buyer on bridging the valuation gap or reducing price.",
        "image_bg": "linear-gradient(135deg,#667eea 0%,#764ba2 100%)",
        "image_url": "https://images.unsplash.com/photo-1582268611958-ebfd161ef9cf?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    # ── THIS WEEK ───────────────────────────────────────────
    {
        "id": "on-track-1",
        "address": "South Esk",
        "location": "Culgaith",
        "price": 310000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 78,
        "duration_days": 47,
        "target_days": 60,
        "days_since_update": 2,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": True}
        ],
        "buyer": "Miss Routledge",
        "buyer_phone": "07734 567890",
        "buyer_solicitor": "Cartmell Shepherd, Carlisle",
        "buyer_sol_phone": "01228 516666",
        "seller_solicitor": "JW Dickinson, Penrith",
        "seller_sol_phone": "01768 862631",
        "offer_date": "2025-12-24",
        "memo_sent": "2025-12-31",
        "searches_ordered": "2026-01-03",
        "searches_received": "2026-01-20",
        "enquiries_raised": "2026-01-23",
        "enquiries_answered": "2026-02-04",
        "mortgage_offered": "2026-02-06",
        "survey_booked": "2026-01-06",
        "survey_complete": "2026-01-18",
        "exchange_target": "2026-02-21",
        "completion_target": "2026-03-07",
        "chain": "Miss Routledge is a first-time buyer, no chain below. Vendors moving to The Limes (exchange agreed).",
        "alert": None,
        "next_action": "Confirm exchange date with both solicitors \u2014 target 21 Feb.",
        "image_bg": "linear-gradient(135deg,#c9d6ff 0%,#e2e2e2 100%)",
        "image_url": "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": True},
            {"label": "Enquiries Answered", "done": True},
            {"label": "Mortgage Offer", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "on-track-2",
        "address": "Brougham Street",
        "location": "Penrith",
        "price": 215000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 55,
        "duration_days": 33,
        "target_days": 60,
        "days_since_update": 3,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": True}
        ],
        "buyer": "Mr Atkinson",
        "buyer_phone": "07823 456789",
        "buyer_solicitor": "Bendles, Carlisle",
        "buyer_sol_phone": "01228 522215",
        "seller_solicitor": "JW Dickinson, Penrith",
        "seller_sol_phone": "01768 862631",
        "offer_date": "2026-01-07",
        "memo_sent": "2026-01-13",
        "searches_ordered": "2026-01-16",
        "searches_received": "2026-02-01",
        "enquiries_raised": "2026-02-03",
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-01-18",
        "survey_complete": "2026-01-30",
        "exchange_target": "2026-03-07",
        "completion_target": "2026-03-21",
        "chain": "Mr Atkinson is a cash buyer (no mortgage required). Vendor downsizing to sheltered housing \u2014 place confirmed.",
        "alert": None,
        "next_action": "Chase Bendles for contract approval \u2014 all enquiries answered.",
        "image_bg": "linear-gradient(135deg,#e8cbc0 0%,#636fa4 100%)",
        "image_url": "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": True},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": None},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "on-track-3",
        "address": "Ousby",
        "location": "Penrith",
        "price": 289000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 45,
        "duration_days": 27,
        "target_days": 60,
        "days_since_update": 1,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": False}
        ],
        "buyer": "Mr & Mrs Fallowfield",
        "buyer_phone": "07567 890123",
        "buyer_solicitor": "Burnetts, Penrith",
        "buyer_sol_phone": "01768 890570",
        "seller_solicitor": "JW Dickinson, Penrith",
        "seller_sol_phone": "01768 862631",
        "offer_date": "2026-01-13",
        "memo_sent": "2026-01-20",
        "searches_ordered": "2026-01-23",
        "searches_received": "2026-02-06",
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-01-25",
        "survey_complete": "2026-02-07",
        "exchange_target": "2026-03-14",
        "completion_target": "2026-03-28",
        "chain": "Chain-free both sides. Fallowfields currently renting. Vendor moving to family abroad.",
        "alert": None,
        "next_action": "Chase Burnetts to raise enquiries now searches and survey are back.",
        "image_bg": "linear-gradient(135deg,#11998e 0%,#38ef7d 100%)",
        "image_url": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "langwathby",
        "address": "Langwathby Lane",
        "location": "Langwathby",
        "price": 268000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 92,
        "duration_days": 55,
        "target_days": 60,
        "days_since_update": 1,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": True}
        ],
        "buyer": "Mr & Mrs Dixon",
        "buyer_phone": "07890 123456",
        "buyer_solicitor": "Cartmell Shepherd, Carlisle",
        "buyer_sol_phone": "01228 516666",
        "seller_solicitor": "Burnetts, Penrith",
        "seller_sol_phone": "01768 890570",
        "offer_date": "2025-12-16",
        "memo_sent": "2025-12-20",
        "searches_ordered": "2025-12-23",
        "searches_received": "2026-01-10",
        "enquiries_raised": "2026-01-14",
        "enquiries_answered": "2026-01-28",
        "mortgage_offered": "2026-01-30",
        "survey_booked": "2025-12-28",
        "survey_complete": "2026-01-12",
        "exchange_target": "2026-02-10",
        "completion_target": "2026-02-14",
        "chain": "Dixons are first-time buyers. Vendor moving to sheltered accommodation \u2014 place confirmed.",
        "alert": None,
        "next_action": "Exchange expected this week. Confirm completion date with all parties.",
        "image_bg": "linear-gradient(135deg,#a8e6cf 0%,#dcedc1 100%)",
        "image_url": "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": True},
            {"label": "Enquiries Answered", "done": True},
            {"label": "Mortgage Offer", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "clifton",
        "address": "Clifton Dykes",
        "location": "Nr Penrith",
        "price": 445000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 88,
        "duration_days": 50,
        "target_days": 60,
        "days_since_update": 2,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": True}
        ],
        "buyer": "Miss Armstrong",
        "buyer_phone": "07456 098765",
        "buyer_solicitor": "JW Dickinson, Penrith",
        "buyer_sol_phone": "01768 862631",
        "seller_solicitor": "Harper & Lane, Kendal",
        "seller_sol_phone": "01539 720400",
        "offer_date": "2025-12-21",
        "memo_sent": "2025-12-28",
        "searches_ordered": "2026-01-02",
        "searches_received": "2026-01-17",
        "enquiries_raised": "2026-01-20",
        "enquiries_answered": "2026-02-03",
        "mortgage_offered": "2026-02-05",
        "survey_booked": "2026-01-05",
        "survey_complete": "2026-01-19",
        "exchange_target": "2026-02-12",
        "completion_target": "2026-02-14",
        "chain": "Miss Armstrong relocating from Manchester (renting). Vendor buying in France \u2014 no UK chain.",
        "alert": None,
        "next_action": "Final contract review underway. Chase for exchange date confirmation.",
        "image_bg": "linear-gradient(135deg,#ffecd2 0%,#fcb69f 100%)",
        "image_url": "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": True},
            {"label": "Enquiries Answered", "done": True},
            {"label": "Mortgage Offer", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    # ── THIS MONTH ──────────────────────────────────────────
    {
        "id": "lazonby",
        "address": "Lazonby",
        "location": "Eden Valley",
        "price": 320000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 72,
        "duration_days": 40,
        "target_days": 60,
        "days_since_update": 3,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": True}
        ],
        "buyer": "Dr & Mrs Mitchell",
        "buyer_phone": "07345 678901",
        "buyer_solicitor": "Oglethorpe Sturton & Gillibrand, Lancaster",
        "buyer_sol_phone": "01524 386500",
        "seller_solicitor": "JW Dickinson, Penrith",
        "seller_sol_phone": "01768 862631",
        "offer_date": "2025-12-31",
        "memo_sent": "2026-01-07",
        "searches_ordered": "2026-01-10",
        "searches_received": "2026-01-28",
        "enquiries_raised": "2026-01-31",
        "enquiries_answered": "2026-02-07",
        "mortgage_offered": None,
        "survey_booked": "2026-01-14",
        "survey_complete": "2026-01-28",
        "exchange_target": "2026-02-28",
        "completion_target": "2026-03-14",
        "chain": "Mitchells selling in Lancaster (exchange agreed). Vendor moving to daughter\u2019s annexe.",
        "alert": None,
        "next_action": "Chase mortgage offer \u2014 valuation was last week, should be imminent.",
        "image_bg": "linear-gradient(135deg,#e0c3fc 0%,#8ec5fc 100%)",
        "image_url": "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": True},
            {"label": "Enquiries Answered", "done": True},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "melmerby",
        "address": "Melmerby",
        "location": "Nr Penrith",
        "price": 485000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 65,
        "duration_days": 35,
        "target_days": 60,
        "days_since_update": 4,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": False}
        ],
        "buyer": "Mr Nicholson",
        "buyer_phone": "07678 901234",
        "buyer_solicitor": "Bendles, Carlisle",
        "buyer_sol_phone": "01228 522215",
        "seller_solicitor": "Burnetts, Penrith",
        "seller_sol_phone": "01768 890570",
        "offer_date": "2026-01-05",
        "memo_sent": "2026-01-12",
        "searches_ordered": "2026-01-15",
        "searches_received": "2026-02-03",
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-01-20",
        "survey_complete": "2026-02-03",
        "exchange_target": "2026-03-07",
        "completion_target": "2026-03-21",
        "chain": "Mr Nicholson is a cash buyer (no chain). Vendor buying in Keswick \u2014 offer accepted.",
        "alert": None,
        "next_action": "Bendles to raise enquiries this week now searches are back.",
        "image_bg": "linear-gradient(135deg,#f5f7fa 0%,#c3cfe2 100%)",
        "image_url": "https://images.unsplash.com/photo-1600585154526-990dced4db0d?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": None},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "glassonby",
        "address": "Glassonby",
        "location": "Eden Valley",
        "price": 275000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 68,
        "duration_days": 38,
        "target_days": 60,
        "days_since_update": 2,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": True}
        ],
        "buyer": "Mr & Mrs Scott",
        "buyer_phone": "07234 567890",
        "buyer_solicitor": "Cartmell Shepherd, Carlisle",
        "buyer_sol_phone": "01228 516666",
        "seller_solicitor": "JW Dickinson, Penrith",
        "seller_sol_phone": "01768 862631",
        "offer_date": "2026-01-02",
        "memo_sent": "2026-01-09",
        "searches_ordered": "2026-01-12",
        "searches_received": "2026-01-28",
        "enquiries_raised": "2026-01-30",
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-01-15",
        "survey_complete": "2026-01-29",
        "exchange_target": "2026-03-02",
        "completion_target": "2026-03-16",
        "chain": "Scotts selling flat in Carlisle (completed). Vendor retiring to Spain \u2014 flexible on dates.",
        "alert": None,
        "next_action": "Chase enquiry answers from seller solicitor. Mortgage application submitted.",
        "image_bg": "linear-gradient(135deg,#89f7fe 0%,#66a6ff 100%)",
        "image_url": "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": True},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    # ── THIS QUARTER ────────────────────────────────────────
    {
        "id": "skirwith",
        "address": "Skirwith",
        "location": "Eden Valley",
        "price": 195000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 48,
        "duration_days": 20,
        "target_days": 60,
        "days_since_update": 5,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": False},
            {"label": "Enquiries Raised", "done": False}
        ],
        "buyer": "Mr & Mrs Bell",
        "buyer_phone": "07567 234567",
        "buyer_solicitor": "JW Dickinson, Penrith",
        "buyer_sol_phone": "01768 862631",
        "seller_solicitor": "Cartmell Shepherd, Carlisle",
        "seller_sol_phone": "01228 516666",
        "offer_date": "2026-01-20",
        "memo_sent": "2026-01-27",
        "searches_ordered": "2026-01-30",
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-02-05",
        "survey_complete": None,
        "exchange_target": "2026-04-01",
        "completion_target": "2026-04-15",
        "chain": "Bells are first-time buyers. Vendor moving abroad \u2014 wants completion by Easter.",
        "alert": None,
        "next_action": "Await search results. Survey booked for next week.",
        "image_bg": "linear-gradient(135deg,#fbc2eb 0%,#a6c1ee 100%)",
        "image_url": "https://images.unsplash.com/photo-1600573472592-401b489a3cdc?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": False},
            {"label": "Survey Complete", "done": False},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "blencarn",
        "address": "Blencarn",
        "location": "Nr Penrith",
        "price": 350000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 42,
        "duration_days": 18,
        "target_days": 60,
        "days_since_update": 3,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": False},
            {"label": "Enquiries Raised", "done": False}
        ],
        "buyer": "Miss Thompson",
        "buyer_phone": "07678 345678",
        "buyer_solicitor": "Burnetts, Penrith",
        "buyer_sol_phone": "01768 890570",
        "seller_solicitor": "Bendles, Carlisle",
        "seller_sol_phone": "01228 522215",
        "offer_date": "2026-01-22",
        "memo_sent": "2026-01-29",
        "searches_ordered": "2026-02-02",
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": "2026-04-10",
        "completion_target": "2026-04-24",
        "chain": "Miss Thompson selling flat in Newcastle (sale agreed). Vendor buying locally \u2014 chain of two.",
        "alert": None,
        "next_action": "Book survey this week. Await Eden DC search results.",
        "image_bg": "linear-gradient(135deg,#d4fc79 0%,#96e6a1 100%)",
        "image_url": "https://images.unsplash.com/photo-1600585154363-67eb9e2e2099?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": False},
            {"label": "Survey Complete", "done": False},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "newbiggin",
        "address": "Newbiggin",
        "location": "Stainmore",
        "price": 225000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 45,
        "duration_days": 22,
        "target_days": 60,
        "days_since_update": 2,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": False},
            {"label": "Enquiries Raised", "done": False}
        ],
        "buyer": "Mr Jackson",
        "buyer_phone": "07789 456789",
        "buyer_solicitor": "Oglethorpe Sturton & Gillibrand, Lancaster",
        "buyer_sol_phone": "01524 386500",
        "seller_solicitor": "JW Dickinson, Penrith",
        "seller_sol_phone": "01768 862631",
        "offer_date": "2026-01-18",
        "memo_sent": "2026-01-25",
        "searches_ordered": "2026-01-28",
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-02-06",
        "survey_complete": None,
        "exchange_target": "2026-04-05",
        "completion_target": "2026-04-19",
        "chain": "Mr Jackson is a cash buyer from London. Vendor retiring \u2014 no upward chain.",
        "alert": None,
        "next_action": "Survey scheduled this week. Chase search results.",
        "image_bg": "linear-gradient(135deg,#fdcbf1 0%,#e6dee9 100%)",
        "image_url": "https://images.unsplash.com/photo-1600047509358-9dc75507daeb?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": False},
            {"label": "Survey Complete", "done": False},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },

    # ── NEEDS ACTION — additional ───────────────────────────
    {
        "id": "whitehaven-cottage",
        "address": "Whitehaven Cottage",
        "location": "Whitehaven",
        "price": 450000,
        "status": "stalled",
        "status_label": "STALLED",
        "progress": 28,
        "duration_days": 52,
        "target_days": 60,
        "days_since_update": 14,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Mortgage", "done": False},
            {"label": "Enquiries Raised", "done": False}
        ],
        "buyer": "Mr & Mrs Cartwright",
        "buyer_phone": "07734 112233",
        "buyer_solicitor": "Brockbank Curwen, Whitehaven",
        "buyer_sol_phone": "01946 692194",
        "seller_solicitor": "Burnetts, Cockermouth",
        "seller_sol_phone": "01900 823105",
        "offer_date": "2025-12-19",
        "memo_sent": "2025-12-28",
        "searches_ordered": "2026-01-04",
        "searches_received": "2026-01-20",
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-01-12",
        "survey_complete": "2026-01-25",
        "exchange_target": "2026-03-06",
        "completion_target": "2026-03-20",
        "chain": "Cartwrights are first-time buyers. Seller relocating to Scotland, no onward chain.",
        "alert": "Buyer mortgage declined by NatWest. Seeking new buyer or alternative lender. Sale at risk of collapse.",
        "next_action": "Contact Cartwrights re: alternative mortgage applications. Consider remarketing if no progress by Friday.",
        "image_bg": "linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%)",
        "image_url": "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "appleby-manor",
        "address": "Appleby Manor",
        "location": "Appleby-in-Westmorland",
        "price": 890000,
        "status": "at-risk",
        "status_label": "AT RISK",
        "progress": 58,
        "duration_days": 41,
        "target_days": 75,
        "days_since_update": 7,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": True}
        ],
        "buyer": "Mr & Mrs Hamilton-Forbes",
        "buyer_phone": "07812 998877",
        "buyer_solicitor": "Oglethorpe Sturton & Gillibrand, Lancaster",
        "buyer_sol_phone": "01524 63511",
        "seller_solicitor": "JW Dickinson, Penrith",
        "seller_sol_phone": "01768 862631",
        "offer_date": "2025-12-30",
        "memo_sent": "2026-01-06",
        "searches_ordered": "2026-01-08",
        "searches_received": "2026-01-24",
        "enquiries_raised": "2026-01-27",
        "enquiries_answered": None,
        "mortgage_offered": "2026-01-20",
        "survey_booked": "2026-01-14",
        "survey_complete": "2026-01-28",
        "exchange_target": "2026-03-14",
        "completion_target": "2026-04-11",
        "chain": "Hamilton-Forbes selling country house in Yorkshire (buyer found, exchange imminent). Seller purchasing bungalow in Penrith — chain break risk if Yorkshire sale falls through.",
        "alert": "Chain break risk — seller's onward purchase in Penrith delayed by 3 weeks. Seller may pull out if not resolved.",
        "next_action": "Call seller's solicitor for update on Penrith purchase. Escalate chain break risk to both parties.",
        "image_bg": "linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%)",
        "image_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": True},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },

    # ── THIS WEEK — additional ──────────────────────────────
    {
        "id": "kirkby-stephen",
        "address": "Kirkby Stephen House",
        "location": "Kirkby Stephen",
        "price": 195000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 92,
        "duration_days": 8,
        "target_days": 14,
        "days_since_update": 1,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Exchange", "done": True}
        ],
        "buyer": "Miss Rowlandson",
        "buyer_phone": "07456 334455",
        "buyer_solicitor": "Cartmell Shepherd, Carlisle",
        "buyer_sol_phone": "01228 516666",
        "seller_solicitor": "Harrison Drury, Kendal",
        "seller_sol_phone": "01539 735251",
        "offer_date": "2026-01-15",
        "memo_sent": "2026-01-16",
        "searches_ordered": "2026-01-17",
        "searches_received": "2026-01-24",
        "enquiries_raised": "2026-01-25",
        "enquiries_answered": "2026-01-30",
        "mortgage_offered": "2026-01-22",
        "survey_booked": "2026-01-20",
        "survey_complete": "2026-01-27",
        "exchange_target": "2026-02-05",
        "completion_target": "2026-02-12",
        "chain": "Miss Rowlandson is a first-time buyer. No onward chain from seller.",
        "alert": None,
        "next_action": "Exchange expected Wednesday. Confirm completion date with both solicitors.",
        "image_bg": "linear-gradient(135deg,#0a2647 0%,#144272 50%,#205295 100%)",
        "image_url": "https://images.unsplash.com/photo-1583608205776-bfd35f0d9f83?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": True},
            {"label": "Enquiries Answered", "done": True},
            {"label": "Mortgage Offer", "done": True},
            {"label": "Exchange", "done": True},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "sedbergh-terrace",
        "address": "Sedbergh Terrace",
        "location": "Sedbergh",
        "price": 165000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 88,
        "duration_days": 12,
        "target_days": 21,
        "days_since_update": 2,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Contracts Out", "done": True}
        ],
        "buyer": "Mr Hodgson",
        "buyer_phone": "07899 223344",
        "buyer_solicitor": "Oglethorpe Sturton & Gillibrand, Lancaster",
        "buyer_sol_phone": "01524 63511",
        "seller_solicitor": "JW Dickinson, Penrith",
        "seller_sol_phone": "01768 862631",
        "offer_date": "2026-01-20",
        "memo_sent": "2026-01-21",
        "searches_ordered": "2026-01-22",
        "searches_received": "2026-01-28",
        "enquiries_raised": "2026-01-29",
        "enquiries_answered": "2026-02-03",
        "mortgage_offered": None,
        "survey_booked": "2026-01-24",
        "survey_complete": "2026-01-30",
        "exchange_target": "2026-02-10",
        "completion_target": "2026-02-13",
        "chain": "Cash buyer, no mortgage. Seller downsizing locally — onward purchase agreed.",
        "alert": None,
        "next_action": "Cash buyer, contracts out. Chase exchange signatures from both parties.",
        "image_bg": "linear-gradient(135deg,#0a2647 0%,#144272 50%,#205295 100%)",
        "image_url": "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": True},
            {"label": "Enquiries Answered", "done": True},
            {"label": "Mortgage Offer", "done": None},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },

    # ── THIS MONTH — additional ─────────────────────────────
    {
        "id": "brough-farmhouse",
        "address": "Brough Farmhouse",
        "location": "Brough",
        "price": 525000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 72,
        "duration_days": 21,
        "target_days": 42,
        "days_since_update": 3,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": True}
        ],
        "buyer": "Mr & Mrs Allinson",
        "buyer_phone": "07811 445566",
        "buyer_solicitor": "Harrison Drury, Kendal",
        "buyer_sol_phone": "01539 735251",
        "seller_solicitor": "Burnetts, Penrith",
        "seller_sol_phone": "01768 890800",
        "offer_date": "2026-01-19",
        "memo_sent": "2026-01-22",
        "searches_ordered": "2026-01-23",
        "searches_received": "2026-02-03",
        "enquiries_raised": "2026-02-04",
        "enquiries_answered": None,
        "mortgage_offered": "2026-01-30",
        "survey_booked": "2026-01-27",
        "survey_complete": "2026-02-03",
        "exchange_target": "2026-02-28",
        "completion_target": "2026-03-14",
        "chain": "Allinsons selling semi in Penrith (exchanged). Seller relocating abroad, no onward purchase.",
        "alert": None,
        "next_action": "Chase enquiry responses from seller solicitor. Target exchange end of month.",
        "image_bg": "linear-gradient(135deg,#0a2647 0%,#144272 50%,#205295 100%)",
        "image_url": "https://images.unsplash.com/photo-1605146769289-440113cc3d00?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": True},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "tebay-cottage",
        "address": "Tebay Cottage",
        "location": "Tebay",
        "price": 285000,
        "status": "at-risk",
        "status_label": "AT RISK",
        "progress": 48,
        "duration_days": 18,
        "target_days": 42,
        "days_since_update": 6,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": False},
            {"label": "Mortgage", "done": False}
        ],
        "buyer": "Ms Kendrick",
        "buyer_phone": "07788 667788",
        "buyer_solicitor": "Cartmell Shepherd, Carlisle",
        "buyer_sol_phone": "01228 516666",
        "seller_solicitor": "JW Dickinson, Penrith",
        "seller_sol_phone": "01768 862631",
        "offer_date": "2026-01-22",
        "memo_sent": "2026-01-24",
        "searches_ordered": "2026-01-25",
        "searches_received": "2026-02-04",
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-02-01",
        "survey_complete": None,
        "exchange_target": "2026-03-06",
        "completion_target": "2026-03-20",
        "chain": "Ms Kendrick selling flat in Manchester (under offer). Seller no chain.",
        "alert": "Survey cancelled twice due to access issues. Mortgage application delayed pending survey.",
        "next_action": "Rebook survey urgently. Contact seller to confirm access dates.",
        "image_bg": "linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%)",
        "image_url": "https://images.unsplash.com/photo-1598228723793-52759bba239c?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": False},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "shap-villa",
        "address": "Shap Villa",
        "location": "Shap",
        "price": 340000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 65,
        "duration_days": 25,
        "target_days": 42,
        "days_since_update": 2,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": True}
        ],
        "buyer": "Mr & Mrs Wharton",
        "buyer_phone": "07922 445566",
        "buyer_solicitor": "Harper & Lane, Kendal",
        "buyer_sol_phone": "01539 720400",
        "seller_solicitor": "Burnetts, Penrith",
        "seller_sol_phone": "01768 890800",
        "offer_date": "2026-01-15",
        "memo_sent": "2026-01-17",
        "searches_ordered": "2026-01-18",
        "searches_received": "2026-01-30",
        "enquiries_raised": "2026-02-02",
        "enquiries_answered": None,
        "mortgage_offered": "2026-01-28",
        "survey_booked": "2026-01-22",
        "survey_complete": "2026-02-01",
        "exchange_target": "2026-02-28",
        "completion_target": "2026-03-14",
        "chain": "Whartons are first-time buyers. Seller moving to sheltered accommodation.",
        "alert": None,
        "next_action": "Await enquiry answers. Mortgage offer in hand — progressing smoothly.",
        "image_bg": "linear-gradient(135deg,#0a2647 0%,#144272 50%,#205295 100%)",
        "image_url": "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": True},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "crosby-lodge",
        "address": "Crosby Lodge",
        "location": "Crosby Ravensworth",
        "price": 415000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 70,
        "duration_days": 19,
        "target_days": 42,
        "days_since_update": 1,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Mortgage", "done": True}
        ],
        "buyer": "Dr & Mrs Faulkner",
        "buyer_phone": "07766 889900",
        "buyer_solicitor": "Oglethorpe Sturton & Gillibrand, Lancaster",
        "buyer_sol_phone": "01524 63511",
        "seller_solicitor": "JW Dickinson, Penrith",
        "seller_sol_phone": "01768 862631",
        "offer_date": "2026-01-21",
        "memo_sent": "2026-01-23",
        "searches_ordered": "2026-01-24",
        "searches_received": "2026-02-03",
        "enquiries_raised": "2026-02-04",
        "enquiries_answered": None,
        "mortgage_offered": "2026-01-31",
        "survey_booked": "2026-01-28",
        "survey_complete": "2026-02-04",
        "exchange_target": "2026-03-06",
        "completion_target": "2026-03-20",
        "chain": "Faulkners selling detached in Lancaster (exchanged). Seller downsizing to Penrith bungalow (agreed).",
        "alert": None,
        "next_action": "Enquiries raised — await answers. All on track for March exchange.",
        "image_bg": "linear-gradient(135deg,#0a2647 0%,#144272 50%,#205295 100%)",
        "image_url": "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": True},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "ravenstonedale-end",
        "address": "Ravenstonedale End",
        "location": "Ravenstonedale",
        "price": 298000,
        "status": "at-risk",
        "status_label": "AT RISK",
        "progress": 45,
        "duration_days": 23,
        "target_days": 42,
        "days_since_update": 8,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": False}
        ],
        "buyer": "Mr Teasdale",
        "buyer_phone": "07633 112244",
        "buyer_solicitor": "Brockbank Curwen, Whitehaven",
        "buyer_sol_phone": "01946 692194",
        "seller_solicitor": "Harrison Drury, Kendal",
        "seller_sol_phone": "01539 735251",
        "offer_date": "2026-01-17",
        "memo_sent": "2026-01-20",
        "searches_ordered": "2026-01-21",
        "searches_received": "2026-02-03",
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-01-24",
        "survey_complete": "2026-02-02",
        "exchange_target": "2026-03-06",
        "completion_target": "2026-03-20",
        "chain": "Mr Teasdale first-time buyer. Seller in rented, no chain.",
        "alert": "Buyer solicitor slow to raise enquiries. 8 days without progress since searches received.",
        "next_action": "Chase Brockbank Curwen to raise enquiries immediately. Mortgage application also needs pushing.",
        "image_bg": "linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%)",
        "image_url": "https://images.unsplash.com/photo-1600585154526-990dced4db0d?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },

    # ── THIS QUARTER — additional ───────────────────────────
    {
        "id": "kendal-heights",
        "address": "Kendal Heights",
        "location": "Kendal",
        "price": 380000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 52,
        "duration_days": 35,
        "target_days": 60,
        "days_since_update": 3,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": False}
        ],
        "buyer": "Mr & Mrs Bell",
        "buyer_phone": "07855 667788",
        "buyer_solicitor": "Harrison Drury, Kendal",
        "buyer_sol_phone": "01539 735251",
        "seller_solicitor": "JW Dickinson, Penrith",
        "seller_sol_phone": "01768 862631",
        "offer_date": "2026-01-05",
        "memo_sent": "2026-01-08",
        "searches_ordered": "2026-01-09",
        "searches_received": "2026-01-23",
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": "2026-01-20",
        "survey_booked": "2026-01-15",
        "survey_complete": "2026-01-24",
        "exchange_target": "2026-03-20",
        "completion_target": "2026-04-03",
        "chain": "Bells selling flat in Kendal (buyer found). Seller retiring to coast.",
        "alert": None,
        "next_action": "Chase enquiry raising from buyer solicitor. Mortgage offer received — good progress.",
        "image_bg": "linear-gradient(135deg,#0a2647 0%,#144272 50%,#205295 100%)",
        "image_url": "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "windermere-view",
        "address": "Windermere View",
        "location": "Windermere",
        "price": 650000,
        "status": "at-risk",
        "status_label": "AT RISK",
        "progress": 38,
        "duration_days": 42,
        "target_days": 75,
        "days_since_update": 11,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": False},
            {"label": "Mortgage", "done": False}
        ],
        "buyer": "Mr & Mrs Ashworth",
        "buyer_phone": "07944 556677",
        "buyer_solicitor": "Oglethorpe Sturton & Gillibrand, Lancaster",
        "buyer_sol_phone": "01524 63511",
        "seller_solicitor": "Burnetts, Penrith",
        "seller_sol_phone": "01768 890800",
        "offer_date": "2025-12-29",
        "memo_sent": "2026-01-03",
        "searches_ordered": "2026-01-06",
        "searches_received": "2026-01-22",
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-01-20",
        "survey_complete": None,
        "exchange_target": "2026-03-27",
        "completion_target": "2026-04-10",
        "chain": "Ashworths selling in Manchester (under offer, slow). Seller has onward purchase in Lakes.",
        "alert": "Survey delayed — listed building survey required. Specialist surveyor booked for next week. 11 days since last update.",
        "next_action": "Confirm listed building survey date. Chase mortgage application status.",
        "image_bg": "linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%)",
        "image_url": "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": False},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "ambleside-cottage",
        "address": "Ambleside Cottage",
        "location": "Ambleside",
        "price": 475000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 35,
        "duration_days": 28,
        "target_days": 60,
        "days_since_update": 4,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": False},
            {"label": "Mortgage", "done": False}
        ],
        "buyer": "Dr Patterson",
        "buyer_phone": "07811 223344",
        "buyer_solicitor": "Cartmell Shepherd, Carlisle",
        "buyer_sol_phone": "01228 516666",
        "seller_solicitor": "JW Dickinson, Penrith",
        "seller_sol_phone": "01768 862631",
        "offer_date": "2026-01-12",
        "memo_sent": "2026-01-14",
        "searches_ordered": "2026-01-15",
        "searches_received": "2026-01-29",
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-02-05",
        "survey_complete": None,
        "exchange_target": "2026-03-27",
        "completion_target": "2026-04-10",
        "chain": "Cash buyer relocating from Edinburgh. Seller purchasing in Grasmere (chain of 2).",
        "alert": None,
        "next_action": "Survey booked for next week. Chase mortgage application — cash buyer so N/A.",
        "image_bg": "linear-gradient(135deg,#0a2647 0%,#144272 50%,#205295 100%)",
        "image_url": "https://images.unsplash.com/photo-1600573472591-ee6b68d14c68?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": False},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": None},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "grasmere-lodge",
        "address": "Grasmere Lodge",
        "location": "Grasmere",
        "price": 720000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 30,
        "duration_days": 20,
        "target_days": 60,
        "days_since_update": 2,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": False},
            {"label": "Mortgage", "done": False}
        ],
        "buyer": "Mr & Mrs Clarkson",
        "buyer_phone": "07900 112233",
        "buyer_solicitor": "Harper & Lane, Kendal",
        "buyer_sol_phone": "01539 720400",
        "seller_solicitor": "Burnetts, Penrith",
        "seller_sol_phone": "01768 890800",
        "offer_date": "2026-01-20",
        "memo_sent": "2026-01-22",
        "searches_ordered": "2026-01-23",
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-02-10",
        "survey_complete": None,
        "exchange_target": "2026-04-03",
        "completion_target": "2026-04-17",
        "chain": "Clarksons selling detached in York (under offer). Seller no chain — executor sale.",
        "alert": None,
        "next_action": "Searches ordered, awaiting results. Survey booked for 10th Feb.",
        "image_bg": "linear-gradient(135deg,#0a2647 0%,#144272 50%,#205295 100%)",
        "image_url": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": False},
            {"label": "Survey Complete", "done": False},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "penrith-mews",
        "address": "Penrith Mews",
        "location": "Penrith",
        "price": 245000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 42,
        "duration_days": 16,
        "target_days": 42,
        "days_since_update": 1,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": True},
            {"label": "Enquiries Raised", "done": False}
        ],
        "buyer": "Miss Tomlinson",
        "buyer_phone": "07422 998877",
        "buyer_solicitor": "JW Dickinson, Penrith",
        "buyer_sol_phone": "01768 862631",
        "seller_solicitor": "Harrison Drury, Kendal",
        "seller_sol_phone": "01539 735251",
        "offer_date": "2026-01-24",
        "memo_sent": "2026-01-27",
        "searches_ordered": "2026-01-28",
        "searches_received": "2026-02-05",
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": "2026-02-03",
        "survey_booked": "2026-01-31",
        "survey_complete": "2026-02-06",
        "exchange_target": "2026-03-13",
        "completion_target": "2026-03-27",
        "chain": "First-time buyer. Seller moving to family home, no chain.",
        "alert": None,
        "next_action": "Searches received. Raise enquiries this week. All progressing well.",
        "image_bg": "linear-gradient(135deg,#0a2647 0%,#144272 50%,#205295 100%)",
        "image_url": "https://images.unsplash.com/photo-1600585153490-76fb20a32601?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": True},
            {"label": "Survey Complete", "done": True},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "keswick-crescent",
        "address": "Keswick Crescent",
        "location": "Keswick",
        "price": 395000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 25,
        "duration_days": 10,
        "target_days": 60,
        "days_since_update": 2,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": False},
            {"label": "Mortgage", "done": False}
        ],
        "buyer": "Mr Bainbridge",
        "buyer_phone": "07555 443322",
        "buyer_solicitor": "Brockbank Curwen, Whitehaven",
        "buyer_sol_phone": "01946 692194",
        "seller_solicitor": "Burnetts, Cockermouth",
        "seller_sol_phone": "01900 823105",
        "offer_date": "2026-01-30",
        "memo_sent": "2026-02-02",
        "searches_ordered": "2026-02-03",
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-02-12",
        "survey_complete": None,
        "exchange_target": "2026-04-10",
        "completion_target": "2026-04-24",
        "chain": "Cash buyer downsizing. Seller purchasing cottage in Borrowdale (under offer).",
        "alert": None,
        "next_action": "Early stages — searches ordered, survey booked 12th Feb. Mortgage application submitted.",
        "image_bg": "linear-gradient(135deg,#0a2647 0%,#144272 50%,#205295 100%)",
        "image_url": "https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": False},
            {"label": "Survey Complete", "done": False},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "cockermouth-place",
        "address": "Cockermouth Place",
        "location": "Cockermouth",
        "price": 310000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 20,
        "duration_days": 7,
        "target_days": 60,
        "days_since_update": 1,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Searches", "done": False},
            {"label": "Survey", "done": False}
        ],
        "buyer": "Mr & Mrs Routledge",
        "buyer_phone": "07677 889900",
        "buyer_solicitor": "Burnetts, Cockermouth",
        "buyer_sol_phone": "01900 823105",
        "seller_solicitor": "JW Dickinson, Penrith",
        "seller_sol_phone": "01768 862631",
        "offer_date": "2026-02-02",
        "memo_sent": "2026-02-04",
        "searches_ordered": "2026-02-05",
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": "2026-04-17",
        "completion_target": "2026-05-01",
        "chain": "Routledges selling terraced in Workington (exchanged). Seller moving abroad, no onward chain.",
        "alert": None,
        "next_action": "Very early stage — searches just ordered. Book survey and submit mortgage application.",
        "image_bg": "linear-gradient(135deg,#0a2647 0%,#144272 50%,#205295 100%)",
        "image_url": "https://images.unsplash.com/photo-1600047509782-20d39509f26d?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": False},
            {"label": "Survey Complete", "done": False},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": "ullswater-house",
        "address": "Ullswater House",
        "location": "Pooley Bridge",
        "price": 580000,
        "status": "on-track",
        "status_label": "ON TRACK",
        "progress": 28,
        "duration_days": 14,
        "target_days": 60,
        "days_since_update": 3,
        "card_checks": [
            {"label": "Searches", "done": True},
            {"label": "Survey", "done": False},
            {"label": "Mortgage", "done": False}
        ],
        "buyer": "Mr & Mrs Harrison",
        "buyer_phone": "07833 445566",
        "buyer_solicitor": "Harper & Lane, Kendal",
        "buyer_sol_phone": "01539 720400",
        "seller_solicitor": "Cartmell Shepherd, Carlisle",
        "seller_sol_phone": "01228 516666",
        "offer_date": "2026-01-26",
        "memo_sent": "2026-01-28",
        "searches_ordered": "2026-01-29",
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": "2026-02-08",
        "survey_complete": None,
        "exchange_target": "2026-04-03",
        "completion_target": "2026-04-17",
        "chain": "Harrisons selling in Leeds (under offer). Seller executor sale, no onward chain.",
        "alert": None,
        "next_action": "Searches ordered, awaiting results. Survey booked 8th Feb. Mortgage application in.",
        "image_bg": "linear-gradient(135deg,#0a2647 0%,#144272 50%,#205295 100%)",
        "image_url": "https://images.unsplash.com/photo-1600563438938-a9a27216b4f5?w=800&h=400&fit=crop",
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Searches Ordered", "done": True},
            {"label": "Searches Received", "done": False},
            {"label": "Survey Complete", "done": False},
            {"label": "Enquiries Raised", "done": False},
            {"label": "Enquiries Answered", "done": False},
            {"label": "Mortgage Offer", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
]


# ─────────────────────────────────────────────────────────────
#  SECTIONS — define the 4 dashboard sections
# ─────────────────────────────────────────────────────────────

SECTIONS = [
    {
        "id": "needs-action",
        "icon": "\U0001F6A8",
        "title": "Needs Action",
        "subtitle": "3 transactions requiring immediate attention",
        "avg_progress": 55,
        "avg_color": "#f97316",
        "border_class": "stalled-banner",
        "visible_ids": ["stalled", "at-risk-1", "at-risk-2"],
        "hidden_ids": ["kirk-thore", "temple-sowerby", "whitehaven-cottage", "appleby-manor"],
        "extra_count": 0,
    },
    {
        "id": "this-week",
        "icon": "\U0001F4C5",
        "title": "This Week",
        "subtitle": "5 expected completions",
        "avg_progress": 82,
        "avg_color": "#16a34a",
        "border_class": "green-banner",
        "visible_ids": ["on-track-1", "on-track-2", "on-track-3"],
        "hidden_ids": ["langwathby", "clifton", "kirkby-stephen", "sedbergh-terrace"],
        "extra_count": 0,
    },
    {
        "id": "this-month",
        "icon": "\U0001F4CA",
        "title": "This Month",
        "subtitle": "12 expected completions",
        "avg_progress": 68,
        "avg_color": "#16a34a",
        "border_class": "blue-banner",
        "visible_ids": ["lazonby", "melmerby", "glassonby"],
        "hidden_ids": ["brough-farmhouse", "tebay-cottage", "shap-villa", "crosby-lodge", "ravenstonedale-end"],
        "extra_count": 4,
    },
    {
        "id": "this-quarter",
        "icon": "\U0001F4C8",
        "title": "This Quarter",
        "subtitle": "28 expected completions",
        "avg_progress": 45,
        "avg_color": "#f97316",
        "border_class": "amber-banner",
        "visible_ids": ["skirwith", "blencarn", "newbiggin"],
        "hidden_ids": ["kendal-heights", "windermere-view", "ambleside-cottage", "grasmere-lodge", "penrith-mews", "keswick-crescent", "cockermouth-place", "ullswater-house"],
        "extra_count": 17,
    },
]

PIPELINE = {
    "this_week":    {"count": 5,  "value": 1200000, "confidence": 95},
    "this_month":   {"count": 12, "value": 2900000, "confidence": 80},
    "this_quarter": {"count": 28, "value": 6800000, "confidence": 70},
}

STATS = {
    "active": 24,
    "on_track": 16,
    "at_risk": 5,
    "action": 3,
    "avg_days": 14.2,
    "pipeline": 2900000,
}


# ─────────────────────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────────────────────

@app.before_request
def require_login():
    if request.endpoint and request.endpoint not in ("login", "static"):
        if not session.get("authenticated"):
            return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == "NUVU2026":
            session["authenticated"] = True
            return redirect(url_for("dashboard"))
        else:
            error = "Incorrect password"
    return render_template_string(LOGIN_HTML, error=error)


@app.route("/")
def dashboard():
    all_props = load_properties()

    # Sort all properties by days_remaining (most urgent first)
    all_props_sorted = sorted(all_props, key=lambda p: p.get("ce_days_remaining", 9999))

    props_by_id = {p["id"]: p for p in all_props}

    sections_data = []
    for sec in SECTIONS:
        s = dict(sec)
        s["visible"] = [props_by_id[pid] for pid in sec["visible_ids"] if pid in props_by_id]
        s["hidden"] = [props_by_id[pid] for pid in sec["hidden_ids"] if pid in props_by_id]
        # Re-sort each section's visible + hidden by urgency
        s["visible"] = sorted(s["visible"], key=lambda p: p.get("ce_days_remaining", 9999))
        s["hidden"] = sorted(s["hidden"], key=lambda p: p.get("ce_days_remaining", 9999))
        sections_data.append(s)

    # Live stats from completion engine
    live_stats = dict(STATS)
    live_stats["active"] = len(all_props)
    live_stats["on_track"] = sum(1 for p in all_props if p["status"] == "on-track")
    live_stats["at_risk"] = sum(1 for p in all_props if p["status"] == "at-risk")
    live_stats["action"] = sum(1 for p in all_props if p["status"] == "stalled")

    return render_template_string(
        DASHBOARD_HTML,
        sections=sections_data,
        stats=live_stats,
        pipeline=PIPELINE,
        properties_json=json.dumps(all_props),
    )


@app.route("/api/property/<prop_id>")
def api_property(prop_id):
    prop = get_props_by_id().get(prop_id)
    if not prop:
        return jsonify({"error": "Not found"}), 404
    return jsonify(prop)


# ── INDIVIDUAL PROPERTY PAGE ───────────────────────────────

@app.route("/property/<prop_id>")
def property_page(prop_id):
    prop = get_props_by_id().get(prop_id)
    if not prop:
        return "Property not found", 404

    # Fetch notes for this property (newest first)
    db = get_db()
    notes_rows = db.execute(
        """SELECT id, note_text, author, is_urgent, created_date, source
           FROM notes WHERE property_id = ?
           ORDER BY created_date DESC""",
        (prop["db_id"],),
    ).fetchall()

    # Read email tone preference
    pref = db.execute(
        "SELECT preference_value FROM email_preferences WHERE preference_key = 'default_tone'"
    ).fetchone()
    current_tone = pref["preference_value"] if pref else "professional"

    db.close()
    notes = [dict(r) for r in notes_rows]

    # Generate AI-recommended emails based on property state
    email_suggestions = suggest_emails(prop, tone=current_tone)

    # Pull AI feedback from query string (one-shot — only present on redirect)
    ai_feedback = None
    ai_param = request.args.get("ai")
    if ai_param:
        ai_feedback = ai_param.split("|")

    return render_template_string(
        PROPERTY_PAGE_HTML,
        prop=prop,
        stats=STATS,
        notes=notes,
        ai_feedback=ai_feedback,
        email_suggestions=email_suggestions,
    )


# ── DETAIL PAGES ────────────────────────────────────────────

@app.route("/active")
def page_active():
    props = load_properties()
    return render_template_string(
        DETAIL_HTML,
        page_title="All Active Properties",
        page_subtitle="{} properties currently in progression".format(len(props)),
        page_accent="var(--lime)",
        properties=props,
        properties_json=json.dumps(props),
        stats=STATS,
    )


@app.route("/on-track")
def page_on_track():
    props = [p for p in load_properties() if p["status"] == "on-track"]
    return render_template_string(
        DETAIL_HTML,
        page_title="On Track Properties",
        page_subtitle="{} properties progressing well".format(len(props)),
        page_accent="var(--green)",
        properties=props,
        properties_json=json.dumps(props),
        stats=STATS,
    )


@app.route("/at-risk")
def page_at_risk():
    props = [p for p in load_properties() if p["status"] == "at-risk"]
    return render_template_string(
        DETAIL_HTML,
        page_title="At Risk Properties",
        page_subtitle="{} properties requiring attention".format(len(props)),
        page_accent="var(--amber)",
        properties=props,
        properties_json=json.dumps(props),
        stats=STATS,
    )


@app.route("/action")
def page_action():
    props = [p for p in load_properties() if p["status"] == "stalled"]
    return render_template_string(
        DETAIL_HTML,
        page_title="Needs Immediate Action",
        page_subtitle="{} stalled transactions requiring urgent action".format(len(props)),
        page_accent="var(--red)",
        properties=props,
        properties_json=json.dumps(props),
        stats=STATS,
    )


@app.route("/by-days")
def page_by_days():
    props = sorted(load_properties(), key=lambda p: p["duration_days"], reverse=True)
    return render_template_string(
        DETAIL_HTML,
        page_title="Properties by Duration",
        page_subtitle="All {} properties sorted by days (highest first)".format(len(props)),
        page_accent="var(--blue)",
        properties=props,
        properties_json=json.dumps(props),
        stats=STATS,
    )


@app.route("/by-value")
def page_by_value():
    props = sorted(load_properties(), key=lambda p: p["price"], reverse=True)
    return render_template_string(
        DETAIL_HTML,
        page_title="Properties by Value",
        page_subtitle="All {} properties sorted by price (highest first)".format(len(props)),
        page_accent="var(--lime)",
        properties=props,
        properties_json=json.dumps(props),
        stats=STATS,
    )


# ─────────────────────────────────────────────────────────────
#  LOGIN PAGE TEMPLATE
# ─────────────────────────────────────────────────────────────

LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Login — NUVU</title>
<link rel="icon" href="/static/logo.png">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{
  font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
  min-height:100vh;display:flex;align-items:center;justify-content:center;
  background:linear-gradient(135deg,#0f1b2d 0%,#1c2e4a 50%,#2a2a2a 100%);
}
.login-card{
  width:100%;max-width:400px;padding:48px 40px;
  background:rgba(15,27,45,.92);backdrop-filter:blur(20px);
  border-radius:20px;border:1px solid rgba(255,255,255,.08);
  box-shadow:0 24px 64px rgba(0,0,0,.4);
  text-align:center;
}
.logo-section{margin-bottom:36px}
.logo-section img{width:56px;height:56px;border-radius:12px;margin-bottom:16px}
.logo-section h1{
  font-size:2.2rem;font-weight:900;color:#ffffff;
  letter-spacing:14px;text-indent:14px;margin-bottom:8px;
}
.tagline{
  font-size:.62rem;color:#c4e233;text-transform:uppercase;
  letter-spacing:3.5px;font-weight:600;
}
.form-group{margin-bottom:20px;text-align:left}
.form-group label{
  display:block;font-size:.72rem;text-transform:uppercase;
  letter-spacing:1.2px;color:rgba(255,255,255,.5);font-weight:600;
  margin-bottom:8px;
}
.form-group input{
  width:100%;height:48px;padding:0 16px;
  background:rgba(255,255,255,.06);border:1.5px solid rgba(255,255,255,.12);
  border-radius:10px;color:#ffffff;font-size:.92rem;font-family:inherit;
  outline:none;transition:border-color .3s ease,box-shadow .3s ease;
}
.form-group input::placeholder{color:rgba(255,255,255,.3)}
.form-group input:focus{
  border-color:#c4e233;
  box-shadow:0 0 0 3px rgba(196,226,51,.15);
}
.submit-btn{
  width:100%;height:48px;border:none;border-radius:10px;
  background:#c4e233;color:#0f1b2d;
  font-size:.92rem;font-weight:700;letter-spacing:.5px;
  cursor:pointer;transition:all .2s ease;
  text-transform:uppercase;margin-top:4px;
}
.submit-btn:hover{background:#d4e640;transform:translateY(-1px);box-shadow:0 4px 16px rgba(196,226,51,.3)}
.submit-btn:active{transform:translateY(0)}
.error-msg{
  background:rgba(225,29,72,.12);color:#fb7185;
  border:1px solid rgba(225,29,72,.25);border-radius:8px;
  padding:10px 14px;font-size:.82rem;font-weight:600;
  margin-bottom:20px;
}
@media(max-width:480px){
  .login-card{margin:16px;padding:36px 28px}
  .logo-section h1{font-size:1.6rem;letter-spacing:10px;text-indent:10px}
}
</style>
</head>
<body>
<div class="login-card">
  <div class="logo-section">
    <img src="/static/logo.png" alt="NUVU">
    <h1>NUVU</h1>
    <div class="tagline">Progression Not Updates</div>
  </div>
  {% if error %}
  <div class="error-msg">{{ error }}</div>
  {% endif %}
  <form method="POST" action="/login">
    <div class="form-group">
      <label for="password">Password</label>
      <input type="password" id="password" name="password" placeholder="Enter access password" autofocus required>
    </div>
    <button type="submit" class="submit-btn">Access Dashboard</button>
  </form>
</div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────
#  DASHBOARD TEMPLATE
# ─────────────────────────────────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NUVU Sales Progression</title>
<link rel="icon" href="/static/logo.png">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --navy:#0f1b2d;--navy-lt:#162236;--navy-md:#1c2e4a;--navy-card:#182842;
  --lime:#c4e233;--lime-dk:#a3bf1a;
  --red:#e11d48;--red-chip:#e11d48;
  --amber:#f97316;--amber-chip:#f97316;
  --green:#16a34a;--green-chip:#16a34a;
  --blue:#3b82f6;
  --white:#ffffff;--off-white:#f4f6f9;
  --txt:#1e293b;--txt-mid:#475569;--txt-light:#94a3b8;
  --card-shadow:0 2px 12px rgba(0,0,0,.08);
  --t:.22s ease;
}
html{font-size:15px;scroll-behavior:smooth}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--off-white);color:var(--txt);min-height:100vh}

/* ═══ HERO ════════════════════════════════════════════════ */
.hero{position:relative;width:100%;height:480px;overflow:hidden;background:var(--navy)}
.hero-img{width:100%;height:100%;object-fit:cover;display:block}
.hero-badge{
  position:absolute;top:28px;right:32px;
  background:rgba(15,27,45,.88);backdrop-filter:blur(12px);
  border-radius:14px;padding:18px 28px 14px;
  display:flex;flex-direction:column;align-items:center;
  border:1px solid rgba(255,255,255,.08);
}
.hero-badge-top{display:flex;align-items:center;gap:14px}
.hero-badge img{width:48px;height:48px;border-radius:10px}
.hero-badge-top h1{font-size:2rem;font-weight:900;color:var(--white);letter-spacing:12px;line-height:1;margin:0;text-indent:12px}
.hero-badge-strapline{font-size:.6rem;color:var(--lime);text-transform:uppercase;letter-spacing:3px;font-weight:600;margin-top:8px;text-align:center;white-space:nowrap}
.hero-stats{
  position:absolute;bottom:24px;left:50%;transform:translateX(-50%);
  width:calc(100% - 64px);max-width:1400px;
  background:#1a2332;border-radius:16px;
  box-shadow:0 8px 32px rgba(0,0,0,.3);
  border:1px solid rgba(255,255,255,.08);
  display:flex;justify-content:center;padding:0;
}
.hs{
  flex:1;max-width:220px;text-align:center;padding:22px 16px;
  border-right:1px solid rgba(255,255,255,.08);
  cursor:pointer;transition:all .25s ease;
  text-decoration:none;display:block;
}
.hs:last-child{border-right:none}
.hs:hover{background:rgba(196,214,0,.12);border-radius:8px;transform:scale(1.04);box-shadow:0 0 16px rgba(196,214,0,.2)}
.hs-val{font-size:2.1rem;font-weight:900;color:var(--white);line-height:1}
.hs-lbl{font-size:.68rem;text-transform:uppercase;letter-spacing:1.8px;color:rgba(255,255,255,.55);margin-top:6px;font-weight:600}

/* ═══ SEARCH BAR — centered with autocomplete ═══════════ */
.search-bar-wrap{display:flex;flex-direction:column;align-items:center;padding:24px 40px 12px;position:relative}
.search-bar{position:relative;width:500px;height:44px}
.search-bar input{
  width:100%;height:100%;
  background:var(--white);border:1px solid #e2e8f0;border-radius:10px;
  padding:0 40px 0 42px;font-size:.88rem;font-weight:500;color:var(--txt);
  outline:none;transition:border-color .3s ease,box-shadow .3s ease;font-family:inherit;
}
.search-bar input::placeholder{color:#94a3b8;font-weight:400}
.search-bar input:focus{border-color:var(--lime);box-shadow:0 0 0 3px rgba(196,214,0,.18)}
.search-bar-icon{position:absolute;left:14px;top:50%;transform:translateY(-50%);font-size:.85rem;color:#94a3b8;pointer-events:none}
.search-clear{position:absolute;right:12px;top:50%;transform:translateY(-50%);background:none;border:none;font-size:1.1rem;color:#94a3b8;cursor:pointer;padding:0 4px;line-height:1;display:none}
.search-clear:hover{color:var(--txt)}
.search-clear.visible{display:block}
.search-dropdown{
  width:500px;background:var(--white);border:1px solid #e2e8f0;border-radius:12px;
  box-shadow:0 8px 32px rgba(0,0,0,.12);margin-top:4px;
  max-height:0;overflow:hidden;transition:max-height .25s ease,opacity .2s ease;
  opacity:0;position:absolute;top:100%;z-index:100;
}
.search-dropdown.open{max-height:360px;opacity:1;overflow-y:auto}
.search-result{display:flex;align-items:center;gap:14px;padding:12px 18px;cursor:pointer;border-bottom:1px solid #f1f5f9;transition:background .15s ease;text-decoration:none;color:inherit}
.search-result:last-child{border-bottom:none}
.search-result:hover{background:#f8fafc}
.sr-info{flex:1}
.sr-addr{font-size:.88rem;font-weight:700;color:var(--txt)}
.sr-detail{font-size:.75rem;color:var(--txt-light);margin-top:2px}
.sr-chip{display:inline-block;padding:3px 10px;border-radius:5px;font-size:.62rem;font-weight:800;letter-spacing:.5px;color:var(--white)}
.sr-chip.chip-stalled{background:var(--red)}
.sr-chip.chip-at-risk{background:var(--amber)}
.sr-chip.chip-on-track{background:var(--green)}
.search-no-result{padding:16px 18px;text-align:center;color:var(--txt-light);font-size:.84rem;font-weight:500}

/* ═══ PIPELINE FORECAST ═══════════════════════════════════ */
.pipeline-section{background:var(--navy);padding:36px 40px 40px}
.pipeline-header{
  display:flex;justify-content:space-between;align-items:flex-start;
  max-width:1280px;margin:0 auto 24px;
}
.pipeline-title{font-size:1.25rem;font-weight:800;color:var(--white);display:flex;align-items:center;gap:10px}
.pipeline-sub{font-size:.82rem;color:rgba(255,255,255,.45);margin-top:4px}
.ahead-badge{
  background:rgba(196,226,51,.12);color:var(--lime);
  padding:7px 16px;border-radius:20px;font-size:.82rem;font-weight:700;
  display:flex;align-items:center;gap:6px;
}
.pipeline-grid{
  display:grid;grid-template-columns:repeat(3,1fr);gap:20px;
  max-width:1280px;margin:0 auto;
}
.pipe-card{
  background:var(--navy-lt);border:1px solid rgba(255,255,255,.06);
  border-radius:14px;padding:22px 24px;
}
.pipe-period{font-size:.68rem;text-transform:uppercase;letter-spacing:1.5px;color:rgba(255,255,255,.45);font-weight:600;margin-bottom:10px}
.pipe-count{font-size:2rem;font-weight:900;color:var(--white);line-height:1}
.pipe-value{font-size:1.05rem;font-weight:800;color:var(--lime);margin-top:4px}
.pipe-bar{width:100%;height:6px;border-radius:3px;background:rgba(255,255,255,.1);margin-top:14px;overflow:hidden}
.pipe-bar-fill{height:100%;border-radius:3px;background:var(--lime)}
.pipe-confidence{font-size:.75rem;color:rgba(255,255,255,.4);margin-top:8px}

/* ═══ MAIN CONTENT ════════════════════════════════════════ */
.content{max-width:1280px;margin:0 auto;padding:0 32px 60px}

/* ═══ SECTION HEADERS ═════════════════════════════════════ */
.section-banner{
  display:flex;justify-content:space-between;align-items:center;
  padding:28px 0 20px;border-left:4px solid transparent;
  padding-left:20px;margin-left:-24px;
}
.section-banner.stalled-banner{border-left-color:var(--red)}
.section-banner.risk-banner{border-left-color:var(--amber)}
.section-banner.green-banner{border-left-color:var(--green)}
.section-banner.blue-banner{border-left-color:var(--blue)}
.section-banner.amber-banner{border-left-color:var(--amber)}
.section-banner-left h2{font-size:1.3rem;font-weight:800;color:var(--txt);display:flex;align-items:center;gap:10px}
.section-banner-left p{font-size:.88rem;color:var(--txt-light);margin-top:2px}
.section-avg{display:flex;align-items:center;gap:12px}
.avg-label{font-size:.68rem;text-transform:uppercase;letter-spacing:1px;color:var(--txt-light);font-weight:600;white-space:nowrap}
.avg-bar-wrap{display:flex;align-items:center;gap:8px}
.avg-bar{width:120px;height:8px;border-radius:4px;background:#e8ecf1;overflow:hidden}
.avg-bar-fill{height:100%;border-radius:4px;transition:width .4s ease}
.avg-pct{font-size:.85rem;font-weight:800;color:var(--txt);min-width:35px}

/* ═══ CARD GRID ═══════════════════════════════════════════ */
.card-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-bottom:12px}

/* ═══ PROPERTY CARD LINK ═════════════════════════════════ */
.prop-card-link{text-decoration:none;color:inherit;display:block}

/* ═══ PROPERTY CARD ═══════════════════════════════════════ */
.prop-card{
  background:var(--white);border-radius:16px;overflow:hidden;
  box-shadow:var(--card-shadow);cursor:pointer;
  transition:all var(--t);border:1px solid #e8ecf1;
}
.prop-card:hover{transform:translateY(-4px);box-shadow:0 12px 32px rgba(0,0,0,.12)}
.card-photo{height:160px;position:relative;overflow:hidden;display:flex;align-items:center;justify-content:center}
.card-photo-bg{width:100%;height:100%;object-fit:cover}
.card-chip{
  position:absolute;top:12px;right:12px;
  padding:5px 14px;border-radius:6px;
  font-size:.68rem;font-weight:800;letter-spacing:.8px;color:var(--white);
}
.chip-stalled{background:var(--red-chip)}
.chip-at-risk{background:var(--amber-chip)}
.chip-on-track{background:var(--green-chip)}
.card-body{padding:18px 22px 20px}
.card-name{font-size:1.05rem;font-weight:700;color:var(--txt);margin-bottom:14px}
.card-progress-row{display:flex;align-items:center;gap:16px;margin-bottom:16px}
.ring-wrap{position:relative;width:64px;height:64px;flex-shrink:0}
.ring-wrap svg{width:64px;height:64px;transform:rotate(-90deg)}
.ring-bg{fill:none;stroke:#e2e8f0;stroke-width:5}
.ring-fg{fill:none;stroke-width:5;stroke-linecap:round}
.ring-fg.clr-stalled{stroke:var(--red)}
.ring-fg.clr-at-risk{stroke:var(--amber)}
.ring-fg.clr-on-track{stroke:var(--lime)}
.ring-pct{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:.8rem;font-weight:800;color:var(--txt)}
.ring-inner{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.ring-days{font-size:1.05rem;font-weight:900;color:var(--txt);line-height:1}
.ring-unit{font-size:.42rem;font-weight:700;color:var(--txt-light);text-transform:uppercase;letter-spacing:.8px;margin-top:1px}
.card-duration .dur-label{font-size:.65rem;text-transform:uppercase;letter-spacing:1.2px;color:var(--txt-light);font-weight:600}
.card-duration .dur-val{font-size:1.3rem;font-weight:800;color:var(--txt);line-height:1.2}
.card-duration .dur-target{font-size:.78rem;color:var(--txt-light)}
.card-checks{display:flex;flex-direction:column;gap:6px}
.chk{display:flex;align-items:center;gap:8px;font-size:.85rem}
.chk-done{color:var(--green);font-weight:600}
.chk-pending{color:var(--txt-light)}
.chk-icon{width:20px;height:20px;border-radius:4px;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:.7rem}
.chk-icon.done{background:var(--green);color:#fff}
.chk-icon.pending{background:#e8ecf1;border:1.5px solid #cbd5e1;color:transparent}

/* ═══ SHOW MORE ═══════════════════════════════════════════ */
.show-more-btn{
  display:flex;align-items:center;justify-content:center;gap:8px;
  width:100%;padding:14px;margin:8px 0 24px;
  background:var(--white);border:1px dashed #cbd5e1;border-radius:12px;
  color:var(--txt-mid);font-size:.88rem;font-weight:600;cursor:pointer;
  transition:all var(--t);
}
.show-more-btn:hover{border-color:var(--green);color:var(--green);background:#f0fdf4}
.show-more-btn svg{transition:transform var(--t)}
.show-more-btn.expanded svg{transform:rotate(180deg)}
.show-more-panel{display:none;margin-bottom:24px}
.show-more-panel.open{display:block}
.extra-summary{
  display:flex;align-items:center;justify-content:space-between;
  padding:16px 20px;margin-top:16px;
  background:var(--white);border:1px solid #e8ecf1;border-radius:12px;
  color:var(--txt-mid);font-size:.88rem;
}
.extra-note{font-size:.78rem;color:var(--txt-light);font-style:italic}

/* ═══ PIPELINE CLICKABLE ═════════════════════════════════ */
.pipeline-section{cursor:pointer;transition:box-shadow .3s ease}
.pipeline-section:hover{box-shadow:inset 0 0 60px rgba(196,226,51,.08),0 0 30px rgba(196,226,51,.06)}
.pipe-card{transition:all .25s ease}
.pipeline-section:hover .pipe-card{border-color:rgba(196,226,51,.15);transform:translateY(-2px)}

/* ═══ ANALYTICS MODAL ════════════════════════════════════ */
.modal-overlay{
  position:fixed;inset:0;background:rgba(0,0,0,.6);backdrop-filter:blur(4px);
  z-index:1000;display:none;align-items:center;justify-content:center;
  opacity:0;transition:opacity .25s ease;
}
.modal-overlay.open{display:flex;opacity:1}
.modal{
  background:var(--navy);border-radius:20px;width:90%;max-width:800px;
  max-height:85vh;overflow-y:auto;
  box-shadow:0 24px 64px rgba(0,0,0,.5);
  border:1px solid rgba(255,255,255,.08);
  animation:modalIn .3s ease;
}
@keyframes modalIn{from{transform:translateY(20px) scale(.97);opacity:0}to{transform:translateY(0) scale(1);opacity:1}}
.modal-header{
  display:flex;justify-content:space-between;align-items:center;
  padding:24px 28px 0;
}
.modal-title{font-size:1.3rem;font-weight:800;color:var(--white);display:flex;align-items:center;gap:10px}
.modal-close{
  width:36px;height:36px;border-radius:50%;border:none;
  background:rgba(255,255,255,.08);color:var(--white);
  font-size:1.2rem;cursor:pointer;transition:all .15s ease;
  display:flex;align-items:center;justify-content:center;
}
.modal-close:hover{background:rgba(255,255,255,.16);transform:scale(1.1)}
.modal-body{padding:20px 28px 28px}
.modal-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:24px}
.m-card{
  background:var(--navy-lt);border:1px solid rgba(255,255,255,.06);
  border-radius:12px;padding:18px 20px;text-align:center;
}
.m-card-period{font-size:.65rem;text-transform:uppercase;letter-spacing:1.5px;color:rgba(255,255,255,.45);font-weight:600;margin-bottom:8px}
.m-card-count{font-size:1.8rem;font-weight:900;color:var(--white);line-height:1}
.m-card-value{font-size:.95rem;font-weight:800;color:var(--lime);margin-top:4px}
.m-card-conf{font-size:.72rem;color:rgba(255,255,255,.4);margin-top:8px}
.m-card-bar{width:100%;height:5px;border-radius:3px;background:rgba(255,255,255,.1);margin-top:6px;overflow:hidden}
.m-card-bar-fill{height:100%;border-radius:3px;background:var(--lime)}
.chart-block{
  background:var(--navy-lt);border:1px solid rgba(255,255,255,.06);
  border-radius:12px;padding:24px;margin-bottom:24px;position:relative;
}
.chart-block-title{
  font-size:.72rem;text-transform:uppercase;letter-spacing:1.5px;
  color:rgba(255,255,255,.45);font-weight:600;margin-bottom:16px;
  display:flex;align-items:center;gap:8px;
}
.chart-canvas-wrap{position:relative;width:100%}
.chart-canvas-wrap.h250{height:250px}
.chart-canvas-wrap.h200{height:200px}
.chart-row{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:24px}
.doughnut-center{
  position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  text-align:center;pointer-events:none;
}
.doughnut-center-label{font-size:.65rem;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,.45);font-weight:600}
.doughnut-center-val{font-size:1.1rem;font-weight:900;color:var(--lime)}
.chart-legend{display:flex;gap:16px;margin-top:12px;justify-content:center;flex-wrap:wrap}
.chart-legend-item{display:flex;align-items:center;gap:6px;font-size:.72rem;color:rgba(255,255,255,.6);font-weight:600}
.chart-legend-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.insights-title{font-size:.72rem;text-transform:uppercase;letter-spacing:1.5px;color:rgba(255,255,255,.45);font-weight:600;margin-bottom:12px}
.insight-item{
  display:flex;align-items:flex-start;gap:10px;
  padding:10px 14px;margin-bottom:8px;
  background:rgba(255,255,255,.04);border-radius:8px;
}
.insight-icon{font-size:1rem;flex-shrink:0;margin-top:1px}
.insight-text{font-size:.82rem;color:rgba(255,255,255,.75);line-height:1.4}
.insight-text strong{color:var(--lime);font-weight:700}

/* Modal responsive */
@media(max-width:768px){
  .modal{width:95%;max-height:90vh;border-radius:16px}
  .modal-header{padding:18px 20px 0}
  .modal-body{padding:16px 20px 24px}
  .modal-cards{grid-template-columns:1fr;gap:10px}
  .chart-row{grid-template-columns:1fr;gap:16px}
  .chart-block{padding:18px}
  .chart-canvas-wrap.h250{height:200px}
  .chart-canvas-wrap.h200{height:180px}
  .chart-legend{gap:10px}
}

/* ═══ RESPONSIVE ══════════════════════════════════════════ */

/* Remove hover on touch devices, add active states */
@media(hover:none){
  .prop-card:hover{transform:none;box-shadow:var(--card-shadow)}
  .hs:hover{background:transparent;border-radius:0;transform:none;box-shadow:none}
  .show-more-btn:hover{border-color:#cbd5e1;color:var(--txt-mid);background:var(--white)}
  .prop-card:active{transform:scale(.97);box-shadow:0 2px 8px rgba(0,0,0,.1)}
  .hs:active{background:rgba(196,214,0,.18);border-radius:8px}
  .show-more-btn:active{border-color:var(--green);color:var(--green);background:#f0fdf4}
  .pipeline-section:hover{box-shadow:none}
  .pipeline-section:active{box-shadow:inset 0 0 40px rgba(196,226,51,.12)}
}

/* Tablet: 769px – 1024px */
@media(max-width:1024px){
  .hero{height:400px}
  .hero-badge{top:20px;right:20px;padding:14px 20px}
  .hero-badge img{width:40px;height:40px}
  .hero-badge-top h1{font-size:1.6rem;letter-spacing:10px;text-indent:10px}
  .hero-badge-strapline{font-size:.55rem;letter-spacing:2.5px}
  .hero-stats{width:calc(100% - 48px);display:grid;grid-template-columns:repeat(3,1fr);padding:0;border-radius:14px}
  .hs{max-width:none;padding:16px 12px;border-right:1px solid rgba(255,255,255,.08);border-bottom:1px solid rgba(255,255,255,.08)}
  .hs:nth-child(3n){border-right:none}
  .hs:nth-child(n+4){border-bottom:none}
  .hs-val{font-size:1.6rem}
  .pipeline-grid{grid-template-columns:repeat(3,1fr)}
  .card-grid{grid-template-columns:repeat(2,1fr);gap:20px}
  .search-bar,.search-dropdown{width:100%;max-width:500px}
  .content{padding:0 24px 48px}
  .pipeline-section{padding:28px 24px 32px}
}

/* Mobile: max-width 768px */
@media(max-width:768px){
  html{font-size:12px}
  body{overflow-x:hidden}
  .hero{height:auto;overflow:visible}
  .hero-img{height:300px}
  .hero-badge{
    position:absolute;top:12px;left:50%;transform:translateX(-50%);right:auto;
    padding:10px 16px;border-radius:10px;
  }
  .hero-badge img{width:30px;height:30px;border-radius:6px}
  .hero-badge-top{gap:8px}
  .hero-badge-top h1{font-size:1.2rem;letter-spacing:6px;text-indent:6px}
  .hero-badge-strapline{font-size:.5rem;letter-spacing:2px;margin-top:4px}
  .hero-stats{
    position:relative;bottom:auto;left:auto;transform:none;
    width:100%;max-width:100%;
    flex-direction:column;
    border-radius:0 0 12px 12px;margin:0;
  }
  .hs{
    max-width:none;padding:12px 20px;
    border-right:none;border-bottom:1px solid rgba(255,255,255,.08);
    display:flex;align-items:center;justify-content:space-between;
    min-height:48px;
  }
  .hs:last-child{border-bottom:none}
  .hs-val{font-size:1.3rem;order:2}
  .hs-lbl{margin-top:0;font-size:.7rem;order:1}
  .search-bar-wrap{padding:16px 16px 8px}
  .search-bar{width:100%;max-width:100%;height:48px}
  .search-dropdown{width:100%;max-width:100%}
  .search-bar input{padding:0 44px 0 44px;font-size:1rem}
  .pipeline-section{padding:20px 16px 24px}
  .pipeline-header{flex-direction:column;gap:8px;margin-bottom:16px}
  .ahead-badge{align-self:flex-start}
  .pipeline-grid{grid-template-columns:1fr;gap:12px}
  .pipe-card{padding:16px 18px}
  .content{padding:0 16px 40px}
  .section-banner{
    flex-direction:column;align-items:flex-start;gap:8px;
    padding:20px 0 16px;margin-left:-16px;padding-left:16px;
  }
  .section-banner-left h2{font-size:1.15rem}
  .section-avg{margin-top:4px}
  .card-grid{grid-template-columns:1fr;gap:16px}
  .card-photo{height:180px}
  .show-more-btn{min-height:48px;font-size:.92rem}
}
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>

{# ═══ PROPERTY CARD MACRO ═══════════════════════════════ #}
{% macro prop_card(p) %}
<a href="/property/{{ p.id }}" class="prop-card-link" id="card-{{ p.id }}">
<div class="prop-card">
  <div class="card-photo">
    <img class="card-photo-bg" src="{{ p.image_url|safe }}" alt="{{ p.address }}" style="background:{{ p.image_bg }}">
    <span class="card-chip chip-{{ p.status }}">{{ p.status_label }}</span>
  </div>
  <div class="card-body">
    <div class="card-name">{{ p.address }}, {{ p.location }}</div>
    <div class="card-progress-row">
      <div class="ring-wrap">
        <svg viewBox="0 0 64 64">
          <circle class="ring-bg" cx="32" cy="32" r="27"/>
          <circle class="ring-fg clr-{{ p.status }}" cx="32" cy="32" r="27"
            stroke-dasharray="{{ (2 * 3.14159 * 27) | round(1) }}"
            stroke-dashoffset="{{ ((100 - p.progress) / 100 * 2 * 3.14159 * 27) | round(1) }}"/>
        </svg>
        <div class="ring-inner">
          <span class="ring-days">{{ p.ce_days_remaining }}</span>
          <span class="ring-unit">days</span>
        </div>
      </div>
      <div class="card-duration">
        <div class="dur-label">Time Remaining</div>
        <div class="dur-val">{{ p.ce_days_remaining }} working days</div>
        <div class="dur-target">Expected: {{ p.ce_expected_completion }}</div>
      </div>
    </div>
    <div class="card-checks">
      {% for c in p.card_checks %}
      <div class="chk {{ 'chk-done' if c.done else 'chk-pending' }}">
        <span class="chk-icon {{ 'done' if c.done else 'pending' }}">{% if c.done %}&#x2713;{% endif %}</span>
        {{ c.label }}
      </div>
      {% endfor %}
    </div>
  </div>
</div>
</a>
{% endmacro %}

<!-- ═══ HERO ══════════════════════════════════════════════ -->
<div class="hero">
  <img class="hero-img" src="/static/street-scene.PNG" alt="NUVU sold boards">
  <div class="hero-badge">
    <div class="hero-badge-top">
      <img src="/static/logo.png" alt="NUVU">
      <h1>NUVU</h1>
    </div>
    <div class="hero-badge-strapline">Progression Not Updates</div>
  </div>
  <div class="hero-stats">
    <a href="/active" class="hs" id="stat-active"><div class="hs-val">{{ stats.active }}</div><div class="hs-lbl">Active</div></a>
    <a href="/on-track" class="hs" id="stat-on-track"><div class="hs-val">{{ stats.on_track }}</div><div class="hs-lbl">On Track</div></a>
    <a href="/at-risk" class="hs" id="stat-at-risk"><div class="hs-val">{{ stats.at_risk }}</div><div class="hs-lbl">At Risk</div></a>
    <a href="/action" class="hs" id="stat-action"><div class="hs-val">{{ stats.action }}</div><div class="hs-lbl">Action</div></a>
    <a href="/by-days" class="hs" id="stat-avg-days"><div class="hs-val">{{ stats.avg_days }}</div><div class="hs-lbl">Avg Days</div></a>
    <a href="/by-value" class="hs" id="stat-pipeline"><div class="hs-val">&pound;{{ "%.1f" | format(stats.pipeline / 1000000) }}M</div><div class="hs-lbl">Pipeline</div></a>
  </div>
</div>

<!-- ═══ SEARCH BAR — centered with autocomplete ══════════ -->
<div class="search-bar-wrap">
  <div class="search-bar" id="searchBar">
    <span class="search-bar-icon">&#x1F50D;</span>
    <input type="text" id="searchInput" placeholder="Search properties..." autocomplete="off">
    <button class="search-clear" id="searchClear">&times;</button>
  </div>
  <div class="search-dropdown" id="searchDropdown"></div>
</div>

<!-- ═══ PIPELINE FORECAST ════════════════════════════════ -->
<div class="pipeline-section" id="pipelineSection">
  <div class="pipeline-header">
    <div>
      <div class="pipeline-title">&#x1F4CA; Pipeline Forecast</div>
      <div class="pipeline-sub">Completion predictions &bull; Manager access only</div>
    </div>
    <div class="ahead-badge">&#x26A1; 15% ahead of target</div>
  </div>
  <div class="pipeline-grid">
    <div class="pipe-card">
      <div class="pipe-period">This Week</div>
      <div class="pipe-count">{{ pipeline.this_week.count }}</div>
      <div class="pipe-value">&pound;{{ "%.1f" | format(pipeline.this_week.value / 1000000) }}M</div>
      <div class="pipe-bar"><div class="pipe-bar-fill" style="width:{{ pipeline.this_week.confidence }}%"></div></div>
      <div class="pipe-confidence">{{ pipeline.this_week.confidence }}% Confidence</div>
    </div>
    <div class="pipe-card">
      <div class="pipe-period">This Month</div>
      <div class="pipe-count">{{ pipeline.this_month.count }}</div>
      <div class="pipe-value">&pound;{{ "%.1f" | format(pipeline.this_month.value / 1000000) }}M</div>
      <div class="pipe-bar"><div class="pipe-bar-fill" style="width:{{ pipeline.this_month.confidence }}%"></div></div>
      <div class="pipe-confidence">{{ pipeline.this_month.confidence }}% Confidence</div>
    </div>
    <div class="pipe-card">
      <div class="pipe-period">This Quarter</div>
      <div class="pipe-count">{{ pipeline.this_quarter.count }}</div>
      <div class="pipe-value">&pound;{{ "%.1f" | format(pipeline.this_quarter.value / 1000000) }}M</div>
      <div class="pipe-bar"><div class="pipe-bar-fill" style="width:{{ pipeline.this_quarter.confidence }}%"></div></div>
      <div class="pipe-confidence">{{ pipeline.this_quarter.confidence }}% Confidence</div>
    </div>
  </div>
</div>

<!-- ═══ MAIN CONTENT — 4 SECTIONS ═══════════════════════ -->
<div class="content">
  {% for sec in sections %}
  <div id="section-{{ sec.id }}">
    <div class="section-banner {{ sec.border_class }}">
      <div class="section-banner-left">
        <h2>{{ sec.icon }} {{ sec.title }}</h2>
        <p>{{ sec.subtitle }}</p>
      </div>
      <div class="section-banner-right">
        <div class="section-avg">
          <div class="avg-label">Avg Completion</div>
          <div class="avg-bar-wrap">
            <div class="avg-bar"><div class="avg-bar-fill" style="width:{{ sec.avg_progress }}%;background:{{ sec.avg_color }}"></div></div>
            <span class="avg-pct">{{ sec.avg_progress }}%</span>
          </div>
        </div>
      </div>
    </div>
    <div class="card-grid">
      {% for p in sec.visible %}
      {{ prop_card(p) }}
      {% endfor %}
    </div>
    {% set total_extra = sec.hidden|length + sec.extra_count %}
    {% if total_extra > 0 %}
    <button class="show-more-btn" id="showMore-{{ sec.id }}">
      Show More ({{ total_extra }})
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
    </button>
    <div class="show-more-panel" id="morePanel-{{ sec.id }}">
      {% if sec.hidden %}
      <div class="card-grid">
        {% for p in sec.hidden %}
        {{ prop_card(p) }}
        {% endfor %}
      </div>
      {% endif %}
      {% if sec.extra_count > 0 %}
      <div class="extra-summary">
        <span>+ {{ sec.extra_count }} more properties</span>
        <span class="extra-note">Connect to your CRM for full pipeline view</span>
      </div>
      {% endif %}
    </div>
    {% endif %}
  </div>
  {% endfor %}
</div>

<!-- ═══ ANALYTICS MODAL ═════════════════════════════════ -->
<div class="modal-overlay" id="analyticsModal">
  <div class="modal">
    <div class="modal-header">
      <div class="modal-title">&#x1F4CA; Pipeline Analytics</div>
      <button class="modal-close" id="modalClose">&times;</button>
    </div>
    <div class="modal-body">
      <!-- Summary Cards -->
      <div class="modal-cards">
        <div class="m-card">
          <div class="m-card-period">This Week</div>
          <div class="m-card-count">{{ pipeline.this_week.count }}</div>
          <div class="m-card-value">&pound;{{ "%.1f" | format(pipeline.this_week.value / 1000000) }}M</div>
          <div class="m-card-bar"><div class="m-card-bar-fill" style="width:{{ pipeline.this_week.confidence }}%"></div></div>
          <div class="m-card-conf">{{ pipeline.this_week.confidence }}% Confidence</div>
        </div>
        <div class="m-card">
          <div class="m-card-period">This Month</div>
          <div class="m-card-count">{{ pipeline.this_month.count }}</div>
          <div class="m-card-value">&pound;{{ "%.1f" | format(pipeline.this_month.value / 1000000) }}M</div>
          <div class="m-card-bar"><div class="m-card-bar-fill" style="width:{{ pipeline.this_month.confidence }}%"></div></div>
          <div class="m-card-conf">{{ pipeline.this_month.confidence }}% Confidence</div>
        </div>
        <div class="m-card">
          <div class="m-card-period">This Quarter</div>
          <div class="m-card-count">{{ pipeline.this_quarter.count }}</div>
          <div class="m-card-value">&pound;{{ "%.1f" | format(pipeline.this_quarter.value / 1000000) }}M</div>
          <div class="m-card-bar"><div class="m-card-bar-fill" style="width:{{ pipeline.this_quarter.confidence }}%"></div></div>
          <div class="m-card-conf">{{ pipeline.this_quarter.confidence }}% Confidence</div>
        </div>
      </div>

      <!-- Completion Trend Line Chart -->
      <div class="chart-block">
        <div class="chart-block-title">&#x1F4C8; Completion Trend — Last 12 Weeks</div>
        <div class="chart-canvas-wrap h250">
          <canvas id="trendChart"></canvas>
        </div>
      </div>

      <!-- Confidence Doughnut + Forecast Accuracy side by side -->
      <div class="chart-row">
        <div class="chart-block">
          <div class="chart-block-title">&#x1F3AF; Pipeline Confidence</div>
          <div class="chart-canvas-wrap h200" style="position:relative">
            <canvas id="confidenceChart"></canvas>
            <div class="doughnut-center">
              <div class="doughnut-center-label">Pipeline</div>
              <div class="doughnut-center-val">Health</div>
            </div>
          </div>
          <div class="chart-legend">
            <div class="chart-legend-item"><span class="chart-legend-dot" style="background:#16a34a"></span>High (60%)</div>
            <div class="chart-legend-item"><span class="chart-legend-dot" style="background:#eab308"></span>Medium (30%)</div>
            <div class="chart-legend-item"><span class="chart-legend-dot" style="background:#dc2626"></span>Low (10%)</div>
          </div>
        </div>
        <div class="chart-block">
          <div class="chart-block-title">&#x1F4CA; Forecast vs Actual</div>
          <div class="chart-canvas-wrap h200">
            <canvas id="forecastChart"></canvas>
          </div>
        </div>
      </div>

      <!-- Key Insights -->
      <div class="insights-section">
        <div class="insights-title">Key Insights</div>
        <div class="insight-item">
          <span class="insight-icon">&#x26A1;</span>
          <span class="insight-text"><strong>15% ahead of target</strong> — Pipeline performance is exceeding quarterly projections</span>
        </div>
        <div class="insight-item">
          <span class="insight-icon">&#x1F4C8;</span>
          <span class="insight-text"><strong>{{ pipeline.this_week.count }} completions expected this week</strong> — valued at &pound;{{ "%.1f" | format(pipeline.this_week.value / 1000000) }}M</span>
        </div>
        <div class="insight-item">
          <span class="insight-icon">&#x26A0;&#xFE0F;</span>
          <span class="insight-text"><strong>{{ stats.at_risk }} properties at risk</strong> — Review these for potential delays impacting pipeline forecast</span>
        </div>
        <div class="insight-item">
          <span class="insight-icon">&#x1F3AF;</span>
          <span class="insight-text"><strong>&pound;{{ "%.1f" | format(pipeline.this_quarter.value / 1000000) }}M quarterly pipeline</strong> — {{ pipeline.this_quarter.count }} properties projected for completion</span>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ═══ JAVASCRIPT ═══════════════════════════════════════ -->
<script>
(function(){
  "use strict";
  var PROPS = {{ properties_json|safe }};

  /* ── SHOW MORE TOGGLE ─────────────────────────── */
  var sectionIds=["needs-action","this-week","this-month","this-quarter"];
  for(var s=0;s<sectionIds.length;s++){
    (function(sid){
      var btn=document.getElementById("showMore-"+sid);
      var panel=document.getElementById("morePanel-"+sid);
      if(btn&&panel){
        btn.onclick=function(){
          var isOpen=panel.classList.contains("open");
          if(isOpen){panel.classList.remove("open");btn.classList.remove("expanded");}
          else{panel.classList.add("open");btn.classList.add("expanded");}
        };
      }
    })(sectionIds[s]);
  }

  /* ── SEARCH AUTOCOMPLETE ──────────────────────── */
  var searchInput=document.getElementById("searchInput");
  var searchClear=document.getElementById("searchClear");
  var searchDropdown=document.getElementById("searchDropdown");
  var searchTimeout=null;

  function clearSearch(){
    searchInput.value="";
    searchClear.classList.remove("visible");
    searchDropdown.classList.remove("open");
    searchDropdown.innerHTML="";
  }

  function doSearch(query){
    if(!query||query.length<1){
      searchDropdown.classList.remove("open");
      searchDropdown.innerHTML="";
      searchClear.classList.remove("visible");
      return;
    }
    searchClear.classList.add("visible");
    var q=query.toLowerCase();
    var matches=[];
    for(var i=0;i<PROPS.length;i++){
      var p=PROPS[i];
      var haystack=(p.address+" "+p.location+" "+p.buyer+" "+(p.status_label||"")+" "+p.price).toLowerCase();
      if(haystack.indexOf(q)!==-1){
        matches.push(p);
        if(matches.length>=5) break;
      }
    }
    if(matches.length===0){
      searchDropdown.innerHTML='<div class="search-no-result">No properties found</div>';
      searchDropdown.classList.add("open");
      return;
    }
    var html="";
    for(var m=0;m<matches.length;m++){
      var mp=matches[m];
      html+='<a href="/property/'+mp.id+'" class="search-result">';
      html+='<div class="sr-info"><div class="sr-addr">'+mp.address+', '+mp.location+'</div>';
      html+='<div class="sr-detail">\u00a3'+mp.price.toLocaleString()+' \u2022 '+mp.duration_days+' days</div></div>';
      html+='<span class="sr-chip chip-'+mp.status+'">'+mp.status_label+'</span>';
      html+='</a>';
    }
    searchDropdown.innerHTML=html;
    searchDropdown.classList.add("open");
  }

  if(searchInput){
    searchInput.oninput=function(){
      clearTimeout(searchTimeout);
      var val=searchInput.value;
      searchTimeout=setTimeout(function(){doSearch(val);},150);
    };
    searchInput.onkeydown=function(e){
      if(e.key==="Escape"){clearSearch();searchInput.blur();}
    };
  }
  if(searchClear){
    searchClear.onclick=function(){clearSearch();searchInput.focus();};
  }

  /* dismiss dropdown when clicking outside */
  document.addEventListener("click",function(e){
    var wrap=document.getElementById("searchBar");
    var dd=document.getElementById("searchDropdown");
    if(wrap && dd && !wrap.contains(e.target) && !dd.contains(e.target)){
      dd.classList.remove("open");
    }
  });

  /* ── ANALYTICS MODAL ──────────────────────────── */
  var pipelineSection=document.getElementById("pipelineSection");
  var analyticsModal=document.getElementById("analyticsModal");
  var modalClose=document.getElementById("modalClose");
  var chartsInitialized=false;
  var trendChartInstance=null,confChartInstance=null,forecastChartInstance=null;

  function initCharts(){
    if(chartsInitialized) return;
    chartsInitialized=true;

    var chartDefaults=Chart.defaults;
    chartDefaults.color="rgba(255,255,255,.5)";
    chartDefaults.font.family="'Segoe UI',system-ui,sans-serif";

    /* ─── COMPLETION TREND (line) ─── */
    var trendCtx=document.getElementById("trendChart");
    if(trendCtx){
      trendChartInstance=new Chart(trendCtx,{
        type:"line",
        data:{
          labels:["Wk 1","Wk 2","Wk 3","Wk 4","Wk 5","Wk 6","Wk 7","Wk 8","Wk 9","Wk 10","Wk 11","Wk 12"],
          datasets:[{
            label:"Completions",
            data:[2,3,4,3,5,6,4,7,5,8,9,12],
            borderColor:"#84cc16",
            backgroundColor:function(ctx){
              var c=ctx.chart.ctx;
              var g=c.createLinearGradient(0,0,0,ctx.chart.height);
              g.addColorStop(0,"rgba(132,204,22,.35)");
              g.addColorStop(1,"rgba(132,204,22,.02)");
              return g;
            },
            fill:true,
            tension:.4,
            borderWidth:2.5,
            pointRadius:4,
            pointBackgroundColor:"#84cc16",
            pointBorderColor:"#0f1b2d",
            pointBorderWidth:2,
            pointHoverRadius:7,
            pointHoverBackgroundColor:"#c4e233"
          }]
        },
        options:{
          responsive:true,
          maintainAspectRatio:false,
          interaction:{mode:"index",intersect:false},
          plugins:{
            legend:{display:false},
            tooltip:{
              backgroundColor:"rgba(15,27,45,.95)",
              titleColor:"#c4e233",
              bodyColor:"#fff",
              borderColor:"rgba(255,255,255,.1)",
              borderWidth:1,
              cornerRadius:8,
              padding:12,
              displayColors:false,
              callbacks:{
                title:function(items){return items[0].label;},
                label:function(item){return item.parsed.y+" completions";}
              }
            }
          },
          scales:{
            x:{
              grid:{color:"rgba(255,255,255,.06)",drawBorder:false},
              ticks:{font:{size:10,weight:"600"},maxRotation:0}
            },
            y:{
              beginAtZero:true,
              grid:{color:"rgba(255,255,255,.06)",drawBorder:false},
              ticks:{font:{size:10,weight:"600"},stepSize:2}
            }
          }
        }
      });
    }

    /* ─── CONFIDENCE DOUGHNUT ─── */
    var confCtx=document.getElementById("confidenceChart");
    if(confCtx){
      confChartInstance=new Chart(confCtx,{
        type:"doughnut",
        data:{
          labels:["High Confidence","Medium Confidence","Low Confidence"],
          datasets:[{
            data:[60,30,10],
            backgroundColor:["#16a34a","#eab308","#dc2626"],
            borderColor:"#162236",
            borderWidth:3,
            hoverBorderColor:"#0f1b2d",
            hoverOffset:6
          }]
        },
        options:{
          responsive:true,
          maintainAspectRatio:false,
          cutout:"68%",
          plugins:{
            legend:{display:false},
            tooltip:{
              backgroundColor:"rgba(15,27,45,.95)",
              titleColor:"#c4e233",
              bodyColor:"#fff",
              borderColor:"rgba(255,255,255,.1)",
              borderWidth:1,
              cornerRadius:8,
              padding:12,
              callbacks:{
                label:function(item){return item.label+": "+item.parsed+"%";}
              }
            }
          },
          animation:{animateRotate:true,duration:800}
        }
      });
    }

    /* ─── FORECAST VS ACTUAL (bar) ─── */
    var foreCtx=document.getElementById("forecastChart");
    if(foreCtx){
      forecastChartInstance=new Chart(foreCtx,{
        type:"bar",
        data:{
          labels:["Sep","Oct","Nov","Dec","Jan","Feb"],
          datasets:[
            {
              label:"Forecast",
              data:[8,10,9,12,11,14],
              backgroundColor:"rgba(28,46,74,.9)",
              borderColor:"rgba(255,255,255,.1)",
              borderWidth:1,
              borderRadius:4,
              barPercentage:.4,
              categoryPercentage:.7
            },
            {
              label:"Actual",
              data:[6,9,10,11,12,13],
              backgroundColor:"rgba(132,204,22,.8)",
              borderColor:"rgba(132,204,22,1)",
              borderWidth:1,
              borderRadius:4,
              barPercentage:.4,
              categoryPercentage:.7
            }
          ]
        },
        options:{
          responsive:true,
          maintainAspectRatio:false,
          interaction:{mode:"index",intersect:false},
          plugins:{
            legend:{
              display:true,
              position:"top",
              align:"end",
              labels:{
                boxWidth:10,boxHeight:10,borderRadius:2,
                font:{size:10,weight:"600"},
                padding:12,
                usePointStyle:true,pointStyle:"rectRounded"
              }
            },
            tooltip:{
              backgroundColor:"rgba(15,27,45,.95)",
              titleColor:"#c4e233",
              bodyColor:"#fff",
              borderColor:"rgba(255,255,255,.1)",
              borderWidth:1,
              cornerRadius:8,
              padding:12
            }
          },
          scales:{
            x:{
              grid:{display:false},
              ticks:{font:{size:10,weight:"600"}}
            },
            y:{
              beginAtZero:true,
              grid:{color:"rgba(255,255,255,.06)",drawBorder:false},
              ticks:{font:{size:10,weight:"600"},stepSize:3}
            }
          }
        }
      });
    }
  }

  function openModal(){
    if(analyticsModal){
      analyticsModal.classList.add("open");
      document.body.style.overflow="hidden";
      setTimeout(initCharts,100);
    }
  }
  function closeModal(){
    if(analyticsModal){
      analyticsModal.classList.remove("open");
      document.body.style.overflow="";
    }
  }

  if(pipelineSection){
    pipelineSection.onclick=function(){openModal();};
  }
  if(modalClose){
    modalClose.onclick=function(e){e.stopPropagation();closeModal();};
  }
  if(analyticsModal){
    analyticsModal.onclick=function(e){
      if(e.target===analyticsModal){closeModal();}
    };
  }
  document.addEventListener("keydown",function(e){
    if(e.key==="Escape"&&analyticsModal&&analyticsModal.classList.contains("open")){
      closeModal();
    }
  });
})();
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────
#  DETAIL PAGE TEMPLATE (no modals, cards link to property pages)
# ─────────────────────────────────────────────────────────────

DETAIL_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ page_title }} — NUVU</title>
<link rel="icon" href="/static/logo.png">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --navy:#0f1b2d;--navy-lt:#162236;--navy-md:#1c2e4a;--navy-card:#182842;
  --lime:#c4e233;--lime-dk:#a3bf1a;
  --red:#e11d48;--red-chip:#e11d48;
  --amber:#f97316;--amber-chip:#f97316;
  --green:#16a34a;--green-chip:#16a34a;
  --blue:#3b82f6;
  --white:#ffffff;--off-white:#f4f6f9;
  --txt:#1e293b;--txt-mid:#475569;--txt-light:#94a3b8;
  --card-shadow:0 2px 12px rgba(0,0,0,.08);
  --t:.22s ease;
}
html{font-size:15px;scroll-behavior:smooth}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--off-white);color:var(--txt);min-height:100vh}
.hero{position:relative;width:100%;height:300px;overflow:hidden;background:var(--navy)}
.hero-img{width:100%;height:100%;object-fit:cover;display:block}
.hero-badge{
  position:absolute;top:20px;right:24px;
  background:rgba(15,27,45,.88);backdrop-filter:blur(12px);
  border-radius:12px;padding:14px 22px 10px;
  display:flex;flex-direction:column;align-items:center;
  border:1px solid rgba(255,255,255,.08);
}
.hero-badge-top{display:flex;align-items:center;gap:10px}
.hero-badge img{width:36px;height:36px;border-radius:8px}
.hero-badge-top h1{font-size:1.4rem;font-weight:900;color:var(--white);letter-spacing:10px;line-height:1;margin:0;text-indent:10px}
.hero-badge-strapline{font-size:.52rem;color:var(--lime);text-transform:uppercase;letter-spacing:2.5px;font-weight:600;margin-top:6px;text-align:center;white-space:nowrap}
.hero-stats{
  position:absolute;bottom:16px;left:50%;transform:translateX(-50%);
  width:calc(100% - 48px);max-width:1200px;
  background:#1a2332;border-radius:14px;
  box-shadow:0 8px 32px rgba(0,0,0,.3);
  border:1px solid rgba(255,255,255,.08);
  display:flex;justify-content:center;padding:0;
}
.hs{
  flex:1;max-width:200px;text-align:center;padding:16px 12px;
  border-right:1px solid rgba(255,255,255,.08);
  cursor:pointer;transition:all .25s ease;
  text-decoration:none;display:block;
}
.hs:last-child{border-right:none}
.hs:hover{background:rgba(196,214,0,.12);border-radius:8px;transform:scale(1.04);box-shadow:0 0 16px rgba(196,214,0,.2)}
.hs-val{font-size:1.6rem;font-weight:900;color:var(--white);line-height:1}
.hs-lbl{font-size:.6rem;text-transform:uppercase;letter-spacing:1.5px;color:rgba(255,255,255,.55);margin-top:4px;font-weight:600}
.back-btn{
  display:inline-flex;align-items:center;gap:8px;
  background:#c4d600;color:#0f1b2d;
  border:none;border-radius:10px;
  padding:10px 22px;font-size:.82rem;font-weight:700;
  letter-spacing:.5px;text-transform:uppercase;
  cursor:pointer;transition:all .2s ease;
  text-decoration:none;margin:28px 0 0 40px;
}
.back-btn:hover{background:#d4e640;transform:translateY(-1px);box-shadow:0 4px 12px rgba(196,214,0,.3)}
.detail-header{padding:20px 40px 8px;text-align:center}
.detail-header h2{font-size:2rem;font-weight:900;color:var(--txt);margin-bottom:4px}
.detail-header .accent-bar{width:60px;height:4px;border-radius:2px;margin:0 auto 8px;background:{{ page_accent }}}
.detail-header p{font-size:.92rem;color:var(--txt-mid);font-weight:500}
.prop-card-link{text-decoration:none;color:inherit;display:block}
.card-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;padding:20px 40px 40px;max-width:1440px;margin:0 auto}
.prop-card{
  background:var(--white);border-radius:16px;overflow:hidden;
  box-shadow:var(--card-shadow);cursor:pointer;
  transition:all var(--t);border:1px solid #e8ecf1;
}
.prop-card:hover{transform:translateY(-4px);box-shadow:0 12px 32px rgba(0,0,0,.12)}
.card-photo{height:160px;position:relative;overflow:hidden;display:flex;align-items:center;justify-content:center}
.card-photo-bg{width:100%;height:100%;object-fit:cover}
.card-chip{
  position:absolute;top:12px;right:12px;
  padding:5px 14px;border-radius:6px;
  font-size:.68rem;font-weight:800;letter-spacing:.8px;color:var(--white);
}
.chip-stalled{background:var(--red-chip)}
.chip-at-risk{background:var(--amber-chip)}
.chip-on-track{background:var(--green-chip)}
.card-body{padding:18px 22px 20px}
.card-name{font-weight:800;font-size:1.02rem;color:var(--txt);margin-bottom:10px}
.card-progress-row{display:flex;align-items:center;gap:16px;margin-bottom:14px}
.ring-wrap{position:relative;width:56px;height:56px;flex-shrink:0}
.ring-wrap svg{width:100%;height:100%;transform:rotate(-90deg)}
.ring-bg{fill:none;stroke:#e8ecf1;stroke-width:5}
.ring-fg{fill:none;stroke-width:5;stroke-linecap:round;transition:stroke-dashoffset .6s ease}
.clr-stalled{stroke:var(--red)}
.clr-at-risk{stroke:var(--amber)}
.clr-on-track{stroke:var(--green)}
.ring-pct{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:800;color:var(--txt)}
.ring-inner{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.ring-days{font-size:.95rem;font-weight:900;color:var(--txt);line-height:1}
.ring-unit{font-size:.38rem;font-weight:700;color:var(--txt-light);text-transform:uppercase;letter-spacing:.8px;margin-top:1px}
.dur-label{font-size:.68rem;color:var(--txt-light);text-transform:uppercase;letter-spacing:.8px;font-weight:600}
.dur-val{font-size:1.06rem;font-weight:800;color:var(--txt);margin:2px 0}
.dur-target{font-size:.72rem;color:var(--txt-light)}
.card-checks{display:flex;flex-direction:column;gap:6px}
.chk{display:flex;align-items:center;gap:8px;font-size:.78rem;font-weight:600}
.chk-done{color:var(--green)}
.chk-pending{color:var(--txt-light)}
.chk-icon{width:20px;height:20px;border-radius:5px;display:flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:700}
.chk-icon.done{background:rgba(22,163,74,.15);color:var(--green)}
.chk-icon.pending{background:#f1f3f5;color:transparent;border:1.5px dashed #cbd5e1}
/* Remove hover on touch devices */
@media(hover:none){
  .prop-card:hover{transform:none;box-shadow:var(--card-shadow)}
  .hs:hover{background:transparent;transform:none;box-shadow:none}
  .back-btn:hover{background:#c4d600;transform:none}
  .prop-card:active{transform:scale(.97)}
  .hs:active{background:rgba(196,214,0,.18);border-radius:8px}
  .back-btn:active{background:var(--lime-dk)}
}

/* Tablet: 769px – 1024px */
@media(max-width:1024px){
  .hero{height:260px}
  .hero-badge{top:16px;right:16px;padding:10px 16px}
  .hero-badge img{width:30px;height:30px}
  .hero-badge-top h1{font-size:1.2rem;letter-spacing:8px;text-indent:8px}
  .hero-badge-strapline{font-size:.48rem}
  .hero-stats{width:calc(100% - 40px);display:grid;grid-template-columns:repeat(3,1fr);padding:0;border-radius:12px}
  .hs{max-width:none;padding:12px 8px;border-right:1px solid rgba(255,255,255,.08);border-bottom:1px solid rgba(255,255,255,.08)}
  .hs:nth-child(3n){border-right:none}
  .hs:nth-child(n+4){border-bottom:none}
  .card-grid{grid-template-columns:repeat(2,1fr);padding:20px 24px 40px}
}

/* Mobile: max-width 768px */
@media(max-width:768px){
  html{font-size:12px}
  body{overflow-x:hidden}
  .hero{height:auto;overflow:visible}
  .hero-img{height:220px}
  .hero-badge{
    position:absolute;top:10px;left:50%;transform:translateX(-50%);right:auto;
    padding:8px 14px;border-radius:8px;
  }
  .hero-badge img{width:26px;height:26px;border-radius:6px}
  .hero-badge-top{gap:8px}
  .hero-badge-top h1{font-size:1rem;letter-spacing:6px;text-indent:6px}
  .hero-badge-strapline{font-size:.44rem;letter-spacing:1.5px;margin-top:4px}
  .hero-stats{
    position:relative;bottom:auto;left:auto;transform:none;
    width:100%;max-width:100%;
    flex-direction:column;
    border-radius:0 0 10px 10px;margin:0;
  }
  .hs{
    max-width:none;padding:10px 16px;
    border-right:none;border-bottom:1px solid rgba(255,255,255,.08);
    display:flex;align-items:center;justify-content:space-between;
    min-height:44px;
  }
  .hs:last-child{border-bottom:none}
  .hs-val{font-size:1.2rem;order:2}
  .hs-lbl{margin-top:0;font-size:.65rem;order:1}
  .back-btn{margin:16px 0 0 16px;padding:10px 18px;min-height:44px}
  .detail-header{padding:16px 16px 8px}
  .detail-header h2{font-size:1.5rem}
  .card-grid{grid-template-columns:1fr;padding:16px 16px 32px;gap:16px}
  .card-photo{height:180px}
}
</style>
</head>
<body>
<div class="hero">
  <img class="hero-img" src="/static/street-scene.PNG" alt="NUVU sold boards">
  <div class="hero-badge">
    <div class="hero-badge-top">
      <img src="/static/logo.png" alt="NUVU">
      <h1>NUVU</h1>
    </div>
    <div class="hero-badge-strapline">Progression Not Updates</div>
  </div>
  <div class="hero-stats">
    <a href="/active" class="hs"><div class="hs-val">{{ stats.active }}</div><div class="hs-lbl">Active</div></a>
    <a href="/on-track" class="hs"><div class="hs-val">{{ stats.on_track }}</div><div class="hs-lbl">On Track</div></a>
    <a href="/at-risk" class="hs"><div class="hs-val">{{ stats.at_risk }}</div><div class="hs-lbl">At Risk</div></a>
    <a href="/action" class="hs"><div class="hs-val">{{ stats.action }}</div><div class="hs-lbl">Action</div></a>
    <a href="/by-days" class="hs"><div class="hs-val">{{ stats.avg_days }}</div><div class="hs-lbl">Avg Days</div></a>
    <a href="/by-value" class="hs"><div class="hs-val">&pound;{{ "%.1f" | format(stats.pipeline / 1000000) }}M</div><div class="hs-lbl">Pipeline</div></a>
  </div>
</div>
<a href="/" class="back-btn">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
  Back to Dashboard
</a>
<div class="detail-header">
  <div class="accent-bar"></div>
  <h2>{{ page_title }}</h2>
  <p>{{ page_subtitle }}</p>
</div>
<div class="card-grid">
  {% for p in properties %}
  <a href="/property/{{ p.id }}" class="prop-card-link">
  <div class="prop-card" id="card-{{ p.id }}">
    <div class="card-photo">
      <img class="card-photo-bg" src="{{ p.image_url|safe }}" alt="{{ p.address }}" style="background:{{ p.image_bg }}">
      <span class="card-chip chip-{{ p.status }}">{{ p.status_label }}</span>
    </div>
    <div class="card-body">
      <div class="card-name">{{ p.address }}, {{ p.location }}</div>
      <div class="card-progress-row">
        <div class="ring-wrap">
          <svg viewBox="0 0 64 64">
            <circle class="ring-bg" cx="32" cy="32" r="27"/>
            <circle class="ring-fg clr-{{ p.status }}" cx="32" cy="32" r="27"
              stroke-dasharray="{{ (2 * 3.14159 * 27) | round(1) }}"
              stroke-dashoffset="{{ ((100 - p.progress) / 100 * 2 * 3.14159 * 27) | round(1) }}"/>
          </svg>
          <div class="ring-inner">
            <span class="ring-days">{{ p.ce_days_remaining }}</span>
            <span class="ring-unit">days</span>
          </div>
        </div>
        <div>
          <div class="dur-label">Time Remaining</div>
          <div class="dur-val">{{ p.ce_days_remaining }} working days</div>
          <div class="dur-target">Expected: {{ p.ce_expected_completion }}</div>
        </div>
      </div>
      <div class="card-checks">
        {% for c in p.card_checks %}
        <div class="chk {{ 'chk-done' if c.done else 'chk-pending' }}">
          <span class="chk-icon {{ 'done' if c.done else 'pending' }}">{% if c.done %}&#x2713;{% endif %}</span>
          {{ c.label }}
        </div>
        {% endfor %}
      </div>
    </div>
  </div>
  </a>
  {% endfor %}
</div>
<script>(function(){"use strict";})();</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────
#  INDIVIDUAL PROPERTY PAGE TEMPLATE
# ─────────────────────────────────────────────────────────────

PROPERTY_PAGE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ prop.address }} — NUVU</title>
<link rel="icon" href="/static/logo.png">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --navy:#0f1b2d;--navy-lt:#162236;--navy-md:#1c2e4a;--navy-card:#182842;
  --lime:#c4e233;--lime-dk:#a3bf1a;
  --red:#e11d48;--amber:#f97316;--green:#16a34a;--blue:#3b82f6;
  --white:#ffffff;--off-white:#f4f6f9;
  --txt:#1e293b;--txt-mid:#475569;--txt-light:#94a3b8;
  --card-shadow:0 2px 12px rgba(0,0,0,.08);
}
html{font-size:15px;scroll-behavior:smooth}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--off-white);color:var(--txt);min-height:100vh}

/* ═══ TOP BAR ════════════════════════════════════════════ */
.top-bar{
  background:var(--navy);padding:14px 28px;
  display:flex;align-items:center;justify-content:space-between;
}
.logo-link{display:flex;align-items:center;gap:10px;text-decoration:none}
.logo-link img{width:32px;height:32px;border-radius:8px}
.logo-link span{font-size:1rem;font-weight:900;color:var(--white);letter-spacing:8px}
.back-btn{
  display:inline-flex;align-items:center;gap:8px;
  background:rgba(196,226,51,.2);color:var(--lime);border:1.5px solid rgba(196,226,51,.4);
  border-radius:8px;padding:8px 18px;font-size:.88rem;font-weight:800;
  text-decoration:none;transition:all .2s ease;letter-spacing:.3px;
}
.back-btn:hover{background:var(--lime);color:var(--navy);border-color:var(--lime)}

/* ═══ S1: PROGRESS OVERVIEW ═════════════════════════════ */
.overview{
  background:var(--navy);padding:0 28px 24px;
}
.ov-header{display:flex;align-items:flex-start;gap:24px;margin-bottom:18px}
.ov-info{flex:1}
.ov-address{font-size:1.6rem;font-weight:900;color:var(--white);line-height:1.2;margin-bottom:2px}
.ov-location{font-size:.82rem;color:rgba(255,255,255,.5);margin-bottom:6px}
.ov-meta{display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.ov-price{font-size:1.1rem;font-weight:800;color:var(--lime)}
.ov-pill{
  padding:4px 12px;border-radius:14px;font-size:.65rem;font-weight:800;
  letter-spacing:.6px;color:var(--white);text-transform:uppercase;
}
.ov-pill.on-track{background:var(--green)}
.ov-pill.at-risk{background:var(--amber)}
.ov-pill.stalled{background:var(--red)}
.ov-days{font-size:.72rem;color:rgba(255,255,255,.45);font-weight:600}

/* Progress circle — Completion Engine (time-based) */
.ov-prog-wrap{display:flex;align-items:center;gap:14px;flex-shrink:0}
.ov-prog{flex-shrink:0;position:relative;width:82px;height:82px}
.ov-prog svg{width:82px;height:82px;transform:rotate(-90deg)}
.ov-prog-bg{fill:none;stroke:rgba(255,255,255,.1);stroke-width:5}
.ov-prog-fg{fill:none;stroke-width:5;stroke-linecap:round;transition:stroke-dashoffset .8s ease}
.ov-prog-fg.on-track{stroke:var(--lime)}
.ov-prog-fg.at-risk{stroke:var(--amber)}
.ov-prog-fg.stalled{stroke:var(--red)}
.ov-prog-inner{
  position:absolute;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;
}
.ov-prog-days{font-size:1.4rem;font-weight:900;color:var(--white);line-height:1}
.ov-prog-unit{font-size:.55rem;font-weight:700;color:rgba(255,255,255,.45);
  text-transform:uppercase;letter-spacing:1px;margin-top:1px}
.ov-prog-pct{
  position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  font-size:1.1rem;font-weight:900;color:var(--white);
}
.ov-prog-meta{display:flex;flex-direction:column;gap:3px}
.ov-prog-expected{font-size:.72rem;font-weight:700;color:rgba(255,255,255,.7)}
.ov-prog-adj-toggle{
  font-size:.65rem;color:var(--lime);font-weight:700;cursor:pointer;
  display:inline-flex;align-items:center;gap:4px;
  transition:color .2s;
}
.ov-prog-adj-toggle:hover{color:var(--white)}
.ov-prog-adj-toggle svg{transition:transform .2s}

/* Completion Engine adjustments panel */
.ce-adjustments{
  background:rgba(255,255,255,.04);border-radius:10px;padding:0;
  max-height:0;overflow:hidden;transition:all .3s ease;
  margin-top:0;
}
.ce-adjustments.ce-show{
  max-height:600px;padding:16px 20px;margin-top:14px;
  border:1px solid rgba(255,255,255,.08);
}
.ce-adj-title{
  font-size:.68rem;font-weight:800;text-transform:uppercase;
  letter-spacing:1.2px;color:rgba(255,255,255,.4);margin-bottom:8px;
}
.ce-adj-baseline{
  font-size:.72rem;color:rgba(255,255,255,.35);margin-bottom:12px;
}
.ce-adj-list{display:flex;flex-direction:column;gap:6px}
.ce-adj-item{
  display:flex;align-items:center;gap:10px;padding:6px 10px;
  border-radius:6px;font-size:.78rem;
}
.ce-adj-item.static{background:rgba(59,130,246,.08)}
.ce-adj-item.positive{background:rgba(22,163,74,.08)}
.ce-adj-item.negative{background:rgba(249,115,22,.08)}
.ce-adj-item.critical{background:rgba(225,29,72,.12)}
.ce-adj-days{
  min-width:42px;text-align:center;font-weight:900;font-size:.82rem;
  padding:2px 6px;border-radius:4px;
}
.ce-adj-days.positive{color:var(--green);background:rgba(22,163,74,.12)}
.ce-adj-days.negative{color:var(--amber);background:rgba(249,115,22,.12)}
.ce-adj-days.neutral{color:var(--txt-light);background:rgba(148,163,184,.12)}
.ce-adj-reason{flex:1;color:rgba(255,255,255,.75);font-weight:500}
.ce-adj-cat{
  font-size:.58rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.8px;color:rgba(255,255,255,.3);
}
.ce-adj-empty{font-size:.78rem;color:rgba(255,255,255,.35);font-style:italic}

/* Milestone grid — named list (enlarged for readability) */
.ms-panel{
  background:rgba(255,255,255,.05);border-radius:12px;padding:18px 22px;
}
.ms-panel-head{
  display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;
}
.ms-panel-title{
  font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:1.2px;
  color:rgba(255,255,255,.35);
}
.ms-panel-count{
  font-size:.75rem;font-weight:700;color:rgba(255,255,255,.4);
}
.ms-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:0}
.ms-group{padding:0 14px}
.ms-group:first-child{padding-left:0}
.ms-group:last-child{padding-right:0}
.ms-group:not(:last-child){border-right:1px solid rgba(255,255,255,.08)}
.ms-group-label{
  font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;
  color:rgba(255,255,255,.28);margin-bottom:10px;
}
.ms-item{
  display:flex;align-items:center;gap:9px;padding:5px 0;
  font-size:.92rem;line-height:1.4;
}
.ms-icon{flex-shrink:0;width:20px;text-align:center;font-size:.88rem}
.ms-icon.done{color:var(--green)}
.ms-icon.pending{color:rgba(255,255,255,.25)}
.ms-icon.na{color:rgba(255,255,255,.18);font-size:.7rem;font-style:italic}
.ms-name{color:rgba(255,255,255,.75);font-weight:600}
.ms-name.done{color:rgba(255,255,255,.4);text-decoration:line-through}
.ms-name.na{color:rgba(255,255,255,.22);font-style:italic}

/* ═══ CONTENT ════════════════════════════════════════════ */
.content{max-width:860px;margin:0 auto;padding:20px 28px 60px}

.block{
  background:var(--white);border-radius:12px;padding:20px 24px;
  box-shadow:var(--card-shadow);margin-bottom:16px;border:1px solid #e8ecf1;
}
.block-title{
  font-size:.65rem;text-transform:uppercase;letter-spacing:1.5px;
  color:var(--txt-light);font-weight:700;margin-bottom:12px;
  display:flex;align-items:center;gap:6px;
}
.block-title svg{color:var(--green);width:14px;height:14px}

/* ═══ AI FEEDBACK BANNER ═════════════════════════════════ */
.ai-banner{
  padding:12px 18px;border-radius:10px;margin-bottom:16px;
  background:linear-gradient(135deg,#0f2027 0%,#162236 100%);
  border:1px solid rgba(196,226,51,.2);display:flex;gap:10px;align-items:flex-start;
}
.ai-banner-icon{
  flex-shrink:0;width:28px;height:28px;border-radius:50%;
  background:rgba(196,226,51,.12);display:flex;align-items:center;justify-content:center;
  font-size:.8rem;
}
.ai-banner-body{flex:1;min-width:0}
.ai-banner-title{
  font-size:.62rem;text-transform:uppercase;letter-spacing:1px;
  color:var(--lime);font-weight:800;margin-bottom:4px;
}
.ai-banner-items{display:flex;flex-wrap:wrap;gap:4px 8px}
.ai-tag{
  font-size:.72rem;font-weight:600;color:rgba(255,255,255,.85);
  padding:2px 0;
}
.ai-tag .tick{color:var(--green);font-weight:800}
.ai-tag .warn{color:var(--amber);font-weight:800}
.ai-banner-dismiss{
  background:none;border:none;color:rgba(255,255,255,.3);
  cursor:pointer;font-size:1rem;line-height:1;padding:0 0 0 8px;flex-shrink:0;
}
.ai-banner-dismiss:hover{color:rgba(255,255,255,.6)}

/* ═══ S2: ALERT ══════════════════════════════════════════ */
.alert-bar{
  padding:14px 20px;border-radius:10px;margin-bottom:16px;
  font-size:.85rem;font-weight:600;line-height:1.45;display:flex;gap:10px;align-items:center;
}
.alert-bar svg{flex-shrink:0}
.alert-red{background:#fee2e2;color:#be123c;border:1px solid #fca5a5}
.alert-amber{background:#fef3c7;color:#c2410c;border:1px solid #fdba74}

/* ═══ S3: NEXT ACTION ════════════════════════════════════ */
.next-block{border-left:3px solid var(--lime);padding-left:22px}
.next-label{font-size:.6rem;text-transform:uppercase;letter-spacing:1.4px;color:var(--lime-dk);font-weight:800;margin-bottom:4px}
.next-text{font-size:.95rem;font-weight:600;color:var(--txt);line-height:1.5;margin-bottom:12px}
.action-row{display:flex;gap:8px;flex-wrap:wrap}
.act-btn{
  display:inline-flex;align-items:center;gap:5px;
  padding:8px 16px;border-radius:8px;font-size:.78rem;font-weight:700;
  border:none;cursor:pointer;transition:all .15s ease;text-decoration:none;
}
.act-btn:hover{transform:translateY(-1px)}
.act-btn svg{width:14px;height:14px}
.act-lime{background:var(--lime);color:var(--navy)}
.act-lime:hover{background:var(--lime-dk)}
.act-wa{background:#25D366;color:#fff}
.act-wa:hover{background:#1da851}

/* ═══ S4: NOTES ══════════════════════════════════════════ */
.note-form{display:flex;gap:8px;align-items:flex-start}
.note-form textarea{
  flex:1;min-height:44px;max-height:120px;padding:10px 14px;
  border:1.5px solid #e2e8f0;border-radius:10px;font-family:inherit;
  font-size:.85rem;color:var(--txt);resize:vertical;background:var(--off-white);
  transition:border-color .2s;
}
.note-form textarea:focus{outline:none;border-color:var(--lime-dk);min-height:80px}
.note-form-submit{
  background:var(--lime);color:var(--navy);border:none;border-radius:10px;
  padding:10px 18px;font-size:.78rem;font-weight:800;cursor:pointer;
  transition:all .15s;white-space:nowrap;flex-shrink:0;height:44px;
}
.note-form-submit:hover{background:var(--lime-dk);transform:translateY(-1px)}
.note-author-row{margin-top:6px}
.note-author-input{
  padding:6px 12px;border:1px solid #e2e8f0;border-radius:8px;
  font-size:.75rem;font-family:inherit;color:var(--txt-mid);width:180px;
  background:var(--off-white);
}
.note-author-input:focus{outline:none;border-color:var(--lime-dk)}

/* Previous notes - collapsible */
.notes-toggle{
  display:flex;align-items:center;gap:6px;margin-top:14px;padding:8px 0;
  cursor:pointer;user-select:none;border:none;background:none;
  font-size:.72rem;font-weight:700;color:var(--txt-light);
  text-transform:uppercase;letter-spacing:.8px;
}
.notes-toggle svg{transition:transform .2s;width:14px;height:14px}
.notes-toggle.open svg{transform:rotate(90deg)}
.notes-toggle:hover{color:var(--txt-mid)}
.notes-prev{display:none;margin-top:8px}
.notes-prev.open{display:block}

.note-item{
  padding:12px 14px;border-radius:8px;border:1px solid #f1f5f9;
  background:var(--off-white);margin-bottom:8px;
}
.note-item.urgent{border-color:var(--red);background:#fef2f2}
.note-head{display:flex;align-items:center;gap:6px;margin-bottom:4px;flex-wrap:wrap}
.note-date{font-size:.68rem;color:var(--txt-light);font-weight:600}
.note-author-tag{font-size:.6rem;font-weight:700;color:var(--navy);background:#e2e8f0;padding:1px 7px;border-radius:8px}
.note-src{font-size:.55rem;font-weight:700;text-transform:uppercase;letter-spacing:.6px;padding:1px 7px;border-radius:8px}
.note-src.manual{background:#dbeafe;color:#1e40af}
.note-src.api{background:#d1fae5;color:#065f46}
.note-src.email{background:#fef3c7;color:#c2410c}
.note-urgent-tag{font-size:.55rem;font-weight:800;text-transform:uppercase;letter-spacing:.6px;padding:1px 7px;border-radius:8px;background:var(--red);color:#fff}
.note-body{font-size:.84rem;color:var(--txt);line-height:1.5;white-space:pre-wrap}
.note-flag{
  background:none;border:1px solid #e2e8f0;border-radius:6px;padding:3px 10px;
  font-size:.65rem;font-weight:700;color:var(--txt-light);cursor:pointer;
  margin-top:6px;transition:all .15s;display:inline-flex;align-items:center;gap:3px;
}
.note-flag:hover{border-color:var(--red);color:var(--red)}
.note-flag.on{border-color:var(--red);color:var(--red);background:#fef2f2}
.note-empty{font-size:.8rem;color:var(--txt-light);padding:12px 0;text-align:center}

/* ═══ S5: CONTACTS ═══════════════════════════════════════ */
.contacts-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.contact-card{
  padding:14px 16px;border-radius:10px;background:var(--off-white);
  border:1px solid #f1f5f9;
}
.contact-role{font-size:.58rem;text-transform:uppercase;letter-spacing:1px;color:var(--txt-light);font-weight:700;margin-bottom:6px}
.contact-name{font-size:.88rem;font-weight:700;color:var(--txt);margin-bottom:2px}
.contact-detail{font-size:.76rem;color:var(--txt-mid);margin-bottom:8px}
.contact-btns{display:flex;gap:6px;flex-wrap:wrap}
.c-btn{
  display:inline-flex;align-items:center;gap:4px;padding:5px 12px;
  border-radius:6px;font-size:.7rem;font-weight:700;text-decoration:none;
  transition:all .15s;border:none;cursor:pointer;
}
.c-btn:hover{transform:translateY(-1px)}
.c-btn svg{width:12px;height:12px}
.c-phone{background:var(--navy);color:var(--lime)}
.c-phone:hover{background:var(--navy-md)}
.c-wa{background:#25D366;color:#fff}
.c-wa:hover{background:#1da851}
.c-empty{font-size:.76rem;color:var(--txt-light);font-style:italic;padding:10px 0}

/* ═══ S6: CHAIN ══════════════════════════════════════════ */
.chain-vis{
  padding:18px 22px;background:var(--navy-card);border-radius:12px;
  border:1px solid rgba(255,255,255,.06);
}
.chain-title{font-size:.6rem;text-transform:uppercase;letter-spacing:1.2px;color:var(--lime);font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:6px}
.chain-title svg{width:14px;height:14px;color:var(--lime)}
.chain-pipe{display:flex;align-items:center;gap:0;flex-wrap:wrap}
.chain-node{
  padding:10px 16px;border-radius:8px;background:rgba(255,255,255,.06);
  border:1px solid rgba(255,255,255,.08);min-width:140px;
}
.chain-node-addr{font-size:.78rem;font-weight:700;color:var(--white);margin-bottom:3px}
.chain-node-meta{display:flex;align-items:center;gap:6px}
.chain-node-status{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.chain-node-status.on-track{background:var(--green)}
.chain-node-status.at-risk{background:var(--amber)}
.chain-node-status.stalled{background:var(--red)}
.chain-node-pct{font-size:.68rem;color:rgba(255,255,255,.5);font-weight:600}
.chain-node.current{border-color:var(--lime);background:rgba(196,226,51,.08)}
.chain-arrow{color:rgba(255,255,255,.2);font-size:1.2rem;padding:0 8px;flex-shrink:0}
.chain-solo{font-size:.82rem;color:rgba(255,255,255,.5);font-style:italic}

/* ═══ S6.5: SUGGESTED EMAILS (Beta) ═════════════════════ */
.email-section{
  background:var(--white);border-radius:14px;padding:22px 24px;
  box-shadow:var(--card-shadow);margin-bottom:16px;border:1px solid #e8ecf1;
}
.email-section-head{
  display:flex;align-items:center;gap:8px;margin-bottom:4px;
}
.email-section-title{
  font-size:.65rem;text-transform:uppercase;letter-spacing:1.5px;
  color:var(--txt-light);font-weight:700;
  display:flex;align-items:center;gap:6px;
}
.email-section-title svg{color:var(--blue);width:14px;height:14px}
.email-beta-tag{
  display:inline-block;font-size:.55rem;background:var(--blue);color:var(--white);
  padding:2px 8px;border-radius:8px;font-weight:800;letter-spacing:.5px;
  vertical-align:middle;
}
.email-section-sub{
  font-size:.78rem;color:var(--txt-light);margin-bottom:16px;
}
.email-card{
  border:1px solid #e8ecf1;border-radius:10px;padding:14px 18px;
  margin-bottom:10px;background:#fafbfc;transition:all .15s;
}
.email-card:last-child{margin-bottom:0}
.email-card:hover{border-color:var(--blue);background:#f0f7ff}
.email-card-head{
  display:flex;justify-content:space-between;align-items:center;
  margin-bottom:6px;flex-wrap:wrap;gap:6px;
}
.email-card-recipient{
  font-size:.82rem;font-weight:700;color:var(--txt);
}
.email-card-type{
  font-size:.6rem;text-transform:uppercase;letter-spacing:.8px;
  padding:3px 10px;border-radius:6px;font-weight:800;
}
.email-card-type.chaser{background:#fef3c7;color:#92400e}
.email-card-type.update{background:#dcfce7;color:#166534}
.email-card-type.nudge{background:#e0f2fe;color:#075985}
.email-card-type.escalation{background:#fee2e2;color:#be123c}
.email-card-subject{
  font-size:.84rem;color:var(--txt-mid);margin-bottom:8px;
}
.email-card-reason{
  font-size:.72rem;color:var(--txt-light);font-style:italic;
  margin-bottom:10px;
}
.email-card-actions{display:flex;gap:8px;flex-wrap:wrap}
.email-preview-btn,.email-copy-btn{
  display:inline-flex;align-items:center;gap:5px;
  padding:6px 14px;border-radius:6px;font-size:.72rem;font-weight:700;
  border:none;cursor:pointer;transition:all .15s;
}
.email-preview-btn{
  background:var(--navy);color:var(--lime);
}
.email-preview-btn:hover{background:var(--navy-md)}
.email-copy-btn{
  background:var(--lime);color:var(--navy);
}
.email-copy-btn:hover{background:var(--lime-dk)}
.email-copy-btn.copied{background:var(--green);color:var(--white)}
.email-body-preview{
  display:none;margin-top:10px;padding:12px 16px;
  background:var(--white);border:1px solid #e8ecf1;border-radius:8px;
  font-size:.82rem;color:var(--txt);line-height:1.6;
  white-space:pre-wrap;font-family:inherit;
}
.email-body-preview.open{display:block}

/* ═══ S7: TIMELINE (collapsible) ═════════════════════════ */
.timeline-toggle{
  display:flex;align-items:center;gap:8px;width:100%;
  cursor:pointer;user-select:none;border:none;background:none;padding:0;
}
.timeline-toggle svg{transition:transform .2s;color:var(--txt-light)}
.timeline-toggle.open svg{transform:rotate(90deg)}
.tl-body{display:none;margin-top:14px}
.tl-body.open{display:block}
.tl-item{
  display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #f1f5f9;
  font-size:.78rem;
}
.tl-item:last-child{border-bottom:none}
.tl-date{color:var(--txt-light);font-weight:600;white-space:nowrap;min-width:90px}
.tl-label{color:var(--txt);font-weight:600}
.tl-val{color:var(--txt-mid);margin-left:auto;font-weight:500;text-align:right}

/* ═══ RESPONSIVE ═════════════════════════════════════════ */
@media(hover:none){
  .act-btn:hover{transform:none}
  .act-lime:hover{background:var(--lime)}
  .act-wa:hover{background:#25D366}
  .back-btn:hover{background:rgba(196,226,51,.15);color:var(--lime)}
  .c-btn:hover{transform:none}
  .act-btn:active,.c-btn:active{transform:scale(.96);opacity:.85}
  .back-btn:active{background:var(--lime);color:var(--navy)}
}

@media(max-width:1024px){
  .overview{padding:0 20px 20px}
  .top-bar{padding:12px 20px}
  .content{padding:16px 20px 48px}
  .ms-grid{grid-template-columns:1fr 1fr}
  .ms-group:last-child{border-right:none}
  .ms-group:nth-child(2){border-right:none}
  .ms-group{padding:0 12px}
}

@media(max-width:768px){
  html{font-size:13px}
  body{overflow-x:hidden}
  .top-bar{padding:10px 16px}
  .logo-link img{width:28px;height:28px}
  .logo-link span{font-size:.9rem;letter-spacing:6px}
  .overview{padding:0 16px 18px}
  .ov-header{flex-direction:column;gap:14px}
  .ov-prog{align-self:flex-start}
  .ov-address{font-size:1.3rem}
  .ms-grid{grid-template-columns:1fr}
  .ms-group{padding:0;border-right:none!important;padding-bottom:10px;margin-bottom:10px;border-bottom:1px solid rgba(255,255,255,.07)}
  .ms-group:last-child{border-bottom:none;margin-bottom:0;padding-bottom:0}
  .ms-item{font-size:.88rem;gap:8px;padding:4px 0}
  .ms-icon{width:18px;font-size:.84rem}
  .content{padding:12px 16px 40px}
  .block{padding:16px 18px;border-radius:10px;margin-bottom:12px}
  .contacts-grid{grid-template-columns:1fr}
  .note-form{flex-direction:column}
  .note-form textarea{width:100%}
  .note-form-submit{width:100%;height:44px}
  .note-author-input{width:100%}
  .action-row{flex-direction:column}
  .act-btn{justify-content:center;min-height:44px;width:100%}
  .chain-pipe{flex-direction:column;align-items:stretch}
  .chain-arrow{transform:rotate(90deg);text-align:center;padding:4px 0}
  .chain-node{min-width:auto}
}
</style>
</head>
<body>

<!-- ═══ TOP BAR ══════════════════════════════════════════ -->
<div class="top-bar">
  <a href="/" class="back-btn">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
    Dashboard
  </a>
  <a href="/" class="logo-link">
    <img src="/static/logo.png" alt="NUVU"><span>NUVU</span>
  </a>
</div>

<!-- ═══ S1: PROGRESS OVERVIEW ════════════════════════════ -->
<div class="overview">
  <div class="ov-header">
    <div class="ov-info">
      <div class="ov-address">{{ prop.address }}</div>
      <div class="ov-location">{{ prop.location }}</div>
      <div class="ov-meta">
        <span class="ov-price">&pound;{{ "{:,}".format(prop.price) }}</span>
        <span class="ov-pill {{ prop.status }}">{{ prop.status_label }}</span>
        <span class="ov-days">{{ prop.duration_days }}d elapsed &middot; {{ prop.ce_days_remaining }}d remaining</span>
      </div>
    </div>
    <!-- Completion Engine progress wheel — TIME-BASED not milestone-based -->
    <div class="ov-prog-wrap">
      <div class="ov-prog">
        <svg viewBox="0 0 100 100">
          <circle class="ov-prog-bg" cx="50" cy="50" r="42"/>
          <circle class="ov-prog-fg {{ prop.status }}" cx="50" cy="50" r="42"
            stroke-dasharray="{{ (2 * 3.14159 * 42) | round(1) }}"
            stroke-dashoffset="{{ ((100 - prop.progress) / 100 * 2 * 3.14159 * 42) | round(1) }}"/>
        </svg>
        <div class="ov-prog-inner">
          <span class="ov-prog-days">{{ prop.ce_days_remaining }}</span>
          <span class="ov-prog-unit">days</span>
        </div>
      </div>
      <div class="ov-prog-meta">
        <div class="ov-prog-expected">Expected: {{ prop.ce_expected_completion }}</div>
        <div class="ov-prog-adj-toggle" onclick="document.getElementById('ce-adjustments').classList.toggle('ce-show')">
          Based on {{ prop.ce_adjustment_count }} adjustment{{ 's' if prop.ce_adjustment_count != 1 else '' }}
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="6 9 12 15 18 9"/></svg>
        </div>
      </div>
    </div>
  </div>

  <!-- Completion Engine adjustments panel (hidden by default) -->
  <div class="ce-adjustments" id="ce-adjustments">
    <div class="ce-adj-title">&#x23F1; Completion Engine Adjustments</div>
    <div class="ce-adj-baseline">Baseline: 16 weeks (80 working days) from offer accepted</div>
    {% if prop.ce_adjustments %}
    <div class="ce-adj-list">
      {% for adj in prop.ce_adjustments %}
      <div class="ce-adj-item {{ adj.category }}">
        <span class="ce-adj-days {% if adj.days < 0 %}positive{% elif adj.days > 0 %}negative{% else %}neutral{% endif %}">
          {{ '+' if adj.days > 0 else '' }}{{ adj.days }}d
        </span>
        <span class="ce-adj-reason">{{ adj.reason }}</span>
        <span class="ce-adj-cat">{{ adj.category }}</span>
      </div>
      {% endfor %}
    </div>
    {% else %}
    <div class="ce-adj-empty">No adjustments — using baseline timeline</div>
    {% endif %}
  </div>

  <!-- Milestones — compact named grid -->
  {% set done_total = prop.milestones|selectattr('done', 'equalto', true)|list|length %}
  {% set applicable = prop.milestones|rejectattr('done', 'none')|list|length %}
  {% set stage_names = {1: 'Initial Setup', 2: 'Legal Process', 3: 'Exchange & Completion'} %}
  <div class="ms-panel">
    <div class="ms-panel-head">
      <span class="ms-panel-title">Milestones</span>
      <span class="ms-panel-count">{{ done_total }}/{{ applicable }} complete</span>
    </div>
    <div class="ms-grid">
      {% for stage_num in [1, 2, 3] %}
      <div class="ms-group">
        <div class="ms-group-label">{{ stage_names[stage_num] }}</div>
        {% for m in prop.milestones if m.stage == stage_num %}
        <div class="ms-item">
          {% if m.done == true %}
            <span class="ms-icon done">&#x2713;</span>
            <span class="ms-name done">{{ m.label }}</span>
          {% elif m.done is none %}
            <span class="ms-icon na">n/a</span>
            <span class="ms-name na">{{ m.label }}</span>
          {% else %}
            <span class="ms-icon pending">&#x25CB;</span>
            <span class="ms-name">{{ m.label }}</span>
          {% endif %}
        </div>
        {% endfor %}
      </div>
      {% endfor %}
    </div>
  </div>
</div>

<!-- ═══ CONTENT ══════════════════════════════════════════ -->
<div class="content">

  <!-- AI FEEDBACK (one-shot after note submission) -->
  {% if ai_feedback %}
  <div class="ai-banner" id="ai-banner">
    <div class="ai-banner-icon">&#x1F916;</div>
    <div class="ai-banner-body">
      <div class="ai-banner-title">AI Detected</div>
      <div class="ai-banner-items">
        {% for line in ai_feedback %}
          {% if '\u2713' in line %}
            <span class="ai-tag"><span class="tick">&#x2713;</span> {{ line.replace('\u2713','').strip() }}</span>
          {% elif '\u26A0' in line %}
            <span class="ai-tag"><span class="warn">&#x26A0;</span> {{ line.replace('\u26A0','').strip() }}</span>
          {% else %}
            <span class="ai-tag">{{ line }}</span>
          {% endif %}
        {% endfor %}
      </div>
    </div>
    <button class="ai-banner-dismiss" onclick="document.getElementById('ai-banner').remove()">&times;</button>
  </div>
  {% endif %}

  <!-- S2: ALERT -->
  {% if prop.alert %}
  <div class="alert-bar {{ 'alert-red' if prop.status == 'stalled' else 'alert-amber' }}">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
    <span>{{ prop.alert }}</span>
  </div>
  {% endif %}

  <!-- S3: NEXT ACTION -->
  <div class="block next-block">
    <div class="next-label">Next Action</div>
    <div class="next-text">{{ prop.next_action }}</div>
    {% set clean_phone = prop.buyer_phone | replace(' ', '') | replace('-', '') | replace('(', '') | replace(')', '') | replace('+', '') %}
    {% set wa_phone = '44' ~ clean_phone[1:] if clean_phone[0:1] == '0' else clean_phone %}
    <div class="action-row">
      <a href="tel:{{ clean_phone }}" class="act-btn act-lime">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6A19.79 19.79 0 012.12 4.18 2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z"/></svg>
        Call {{ prop.buyer.split(' ')[-1] }}
      </a>
      <a href="https://wa.me/{{ wa_phone }}?text={{ ('Hi, regarding ' ~ prop.address ~ ' — ' ~ prop.status_label) | urlencode }}" target="_blank" class="act-btn act-wa">
        <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
        WhatsApp
      </a>
    </div>
  </div>

  <!-- S4: NOTES -->
  <div class="block">
    <div class="block-title">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
      Agent Notes
    </div>
    <form class="note-form" method="POST" action="/property/{{ prop.id }}/notes">
      <textarea name="note_text" placeholder="What happened?" required></textarea>
      <button type="submit" class="note-form-submit">Save Note</button>
      <input type="hidden" name="author" id="note-author-val" value="Agent">
    </form>
    <div class="note-author-row">
      <input class="note-author-input" type="text" placeholder="Your name" value="" oninput="document.getElementById('note-author-val').value=this.value||'Agent'">
    </div>

    {% if notes %}
    <button class="notes-toggle" onclick="this.classList.toggle('open');this.nextElementSibling.classList.toggle('open')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
      Previous notes ({{ notes|length }})
    </button>
    <div class="notes-prev">
      {% for n in notes %}
      <div class="note-item {{ 'urgent' if n.is_urgent }}">
        <div class="note-head">
          <span class="note-date">{{ n.created_date[:16].replace('T',' ') }}</span>
          <span class="note-author-tag">{{ n.author }}</span>
          <span class="note-src {{ n.source }}">{{ n.source }}</span>
          {% if n.is_urgent %}<span class="note-urgent-tag">&#x26A0; Urgent</span>{% endif %}
        </div>
        <div class="note-body">{{ n.note_text }}</div>
        <form method="POST" action="/property/{{ prop.id }}/notes/{{ n.id }}/urgent" style="display:inline">
          <button type="submit" class="note-flag {{ 'on' if n.is_urgent }}">
            &#x1F6A9; {{ 'Unflag' if n.is_urgent else 'Flag Issue' }}
          </button>
        </form>
      </div>
      {% endfor %}
    </div>
    {% else %}
    <div class="note-empty">No notes yet — add one after your next contact.</div>
    {% endif %}
  </div>

  <!-- S5: CONTACTS -->
  <div class="block">
    <div class="block-title">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
      Contacts
    </div>
    <div class="contacts-grid">
      <!-- Buyer -->
      {% if prop.buyer %}
      <div class="contact-card">
        <div class="contact-role">Buyer</div>
        <div class="contact-name">{{ prop.buyer }}</div>
        {% if prop.buyer_phone %}<div class="contact-detail">{{ prop.buyer_phone }}</div>{% endif %}
        <div class="contact-btns">
          {% if prop.buyer_phone %}
            {% set bp_clean = prop.buyer_phone | replace(' ', '') | replace('-', '') | replace('(', '') | replace(')', '') | replace('+', '') %}
            {% set bp_wa = '44' ~ bp_clean[1:] if bp_clean[0:1] == '0' else bp_clean %}
            <a href="tel:{{ bp_clean }}" class="c-btn c-phone"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6A19.79 19.79 0 012.12 4.18 2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z"/></svg> Call</a>
            <a href="https://wa.me/{{ bp_wa }}" target="_blank" class="c-btn c-wa"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/></svg> WA</a>
          {% endif %}
        </div>
      </div>
      {% endif %}

      <!-- Buyer's Solicitor -->
      {% if prop.buyer_solicitor %}
      <div class="contact-card">
        <div class="contact-role">Buyer's Solicitor</div>
        <div class="contact-name">{{ prop.buyer_solicitor }}</div>
        {% if prop.buyer_sol_phone %}<div class="contact-detail">{{ prop.buyer_sol_phone }}</div>{% endif %}
        <div class="contact-btns">
          {% if prop.buyer_sol_phone %}
            {% set bsp_clean = prop.buyer_sol_phone | replace(' ', '') | replace('-', '') | replace('(', '') | replace(')', '') | replace('+', '') %}
            <a href="tel:{{ bsp_clean }}" class="c-btn c-phone"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6A19.79 19.79 0 012.12 4.18 2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z"/></svg> Call</a>
          {% endif %}
        </div>
      </div>
      {% endif %}

      <!-- Seller's Solicitor -->
      {% if prop.seller_solicitor %}
      <div class="contact-card">
        <div class="contact-role">Seller's Solicitor</div>
        <div class="contact-name">{{ prop.seller_solicitor }}</div>
        {% if prop.seller_sol_phone %}<div class="contact-detail">{{ prop.seller_sol_phone }}</div>{% endif %}
        <div class="contact-btns">
          {% if prop.seller_sol_phone %}
            {% set ssp_clean = prop.seller_sol_phone | replace(' ', '') | replace('-', '') | replace('(', '') | replace(')', '') | replace('+', '') %}
            <a href="tel:{{ ssp_clean }}" class="c-btn c-phone"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6A19.79 19.79 0 012.12 4.18 2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z"/></svg> Call</a>
          {% endif %}
        </div>
      </div>
      {% endif %}

      <!-- Mortgage Broker (if data exists) -->
      {% if prop.mortgage_offered %}
      <div class="contact-card">
        <div class="contact-role">Mortgage</div>
        <div class="contact-name">Mortgage Offer</div>
        <div class="contact-detail">{{ prop.mortgage_offered }}</div>
      </div>
      {% endif %}
    </div>
  </div>

  <!-- S6: CHAIN VISUALIZATION -->
  <div class="chain-vis">
    <div class="chain-title">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>
      Chain
    </div>
    {% if prop.chain %}
    <div class="chain-pipe">
      <div class="chain-node current">
        <div class="chain-node-addr">{{ prop.address }}</div>
        <div class="chain-node-meta">
          <span class="chain-node-status {{ prop.status }}"></span>
          <span class="chain-node-pct">{{ prop.progress }}% — This property</span>
        </div>
      </div>
    </div>
    <div style="margin-top:10px;font-size:.82rem;color:rgba(255,255,255,.6);line-height:1.5">{{ prop.chain }}</div>
    {% else %}
    <div class="chain-solo">No chain — standalone transaction</div>
    {% endif %}
  </div>

  <!-- ═══ S6.5: SUGGESTED EMAILS (Beta) ═════════════════════ -->
  {% if email_suggestions %}
  <div class="email-section">
    <div class="email-section-head">
      <div class="email-section-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
        Suggested Emails
      </div>
      <span class="email-beta-tag">BETA</span>
    </div>
    <div class="email-section-sub">AI-recommended emails based on this property's status. Review before sending.</div>

    {% for em in email_suggestions %}
    <div class="email-card" id="email-card-{{ loop.index }}">
      <div class="email-card-head">
        <span class="email-card-recipient">To: {{ em.recipient_name }}</span>
        {% if 'escalation' in em.email_type %}
        <span class="email-card-type escalation">ESCALATION</span>
        {% elif 'chaser' in em.email_type %}
        <span class="email-card-type chaser">CHASER</span>
        {% elif 'nudge' in em.email_type %}
        <span class="email-card-type nudge">NUDGE</span>
        {% else %}
        <span class="email-card-type update">UPDATE</span>
        {% endif %}
      </div>
      <div class="email-card-subject">{{ em.preview_subject }}</div>
      <div class="email-card-reason">{{ em.reason }}</div>
      <div class="email-card-actions">
        <button class="email-preview-btn" onclick="toggleEmailPreview({{ loop.index }})">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          Preview
        </button>
        <button class="email-copy-btn" id="copy-btn-{{ loop.index }}"
                onclick="copyEmail({{ loop.index }})">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
          Copy to Clipboard
        </button>
      </div>
      <div class="email-body-preview" id="email-preview-{{ loop.index }}">{{ em.preview_body }}</div>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- S7: TIMELINE (collapsible, collapsed by default) -->
  <div class="block" style="margin-top:16px">
    <button class="timeline-toggle block-title" style="margin-bottom:0;cursor:pointer;border:none;background:none;width:100%"
            onclick="this.classList.toggle('open');this.nextElementSibling.classList.toggle('open')">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      Timeline
    </button>
    <div class="tl-body">
      {% if prop.offer_date %}<div class="tl-item"><span class="tl-date">{{ prop.offer_date }}</span><span class="tl-label">Offer Accepted</span></div>{% endif %}
      {% if prop.memo_sent %}<div class="tl-item"><span class="tl-date">{{ prop.memo_sent }}</span><span class="tl-label">Memorandum Sent</span></div>{% endif %}
      {% if prop.searches_ordered %}<div class="tl-item"><span class="tl-date">{{ prop.searches_ordered }}</span><span class="tl-label">Searches Ordered</span></div>{% endif %}
      {% if prop.searches_received %}<div class="tl-item"><span class="tl-date">{{ prop.searches_received }}</span><span class="tl-label">Searches Received</span></div>{% endif %}
      {% if prop.survey_booked %}<div class="tl-item"><span class="tl-date">{{ prop.survey_booked }}</span><span class="tl-label">Survey Booked</span></div>{% endif %}
      {% if prop.survey_complete %}<div class="tl-item"><span class="tl-date">{{ prop.survey_complete }}</span><span class="tl-label">Survey Complete</span></div>{% endif %}
      {% if prop.enquiries_raised %}<div class="tl-item"><span class="tl-date">{{ prop.enquiries_raised }}</span><span class="tl-label">Enquiries Raised</span></div>{% endif %}
      {% if prop.enquiries_answered %}<div class="tl-item"><span class="tl-date">{{ prop.enquiries_answered }}</span><span class="tl-label">Enquiries Answered</span></div>{% endif %}
      {% if prop.mortgage_offered %}<div class="tl-item"><span class="tl-date">{{ prop.mortgage_offered }}</span><span class="tl-label">Mortgage Offered</span></div>{% endif %}
      {% if prop.exchange_target %}<div class="tl-item"><span class="tl-date">{{ prop.exchange_target }}</span><span class="tl-label">Exchange Target</span><span class="tl-val">target</span></div>{% endif %}
      {% if prop.completion_target %}<div class="tl-item"><span class="tl-date">{{ prop.completion_target }}</span><span class="tl-label">Completion Target</span><span class="tl-val">target</span></div>{% endif %}
      {% if not prop.offer_date and not prop.memo_sent %}
      <div class="tl-item"><span class="tl-date">—</span><span class="tl-label" style="color:var(--txt-light)">No timeline events recorded yet</span></div>
      {% endif %}
    </div>
  </div>

</div>

{% if email_suggestions %}
<script>
var emailData = [
  {% for em in email_suggestions %}
  {
    "subject": {{ em.preview_subject | tojson }},
    "body": {{ em.preview_body | tojson }},
    "email_type": {{ em.email_type | tojson }},
    "recipient_type": {{ em.recipient_type | tojson }},
    "recipient_name": {{ em.recipient_name | tojson }},
    "tone": {{ em.tone | tojson }}
  }{{ "," if not loop.last else "" }}
  {% endfor %}
];

function toggleEmailPreview(idx) {
  var el = document.getElementById('email-preview-' + idx);
  if (el) el.classList.toggle('open');
}

function copyEmail(idx) {
  var d = emailData[idx - 1];
  if (!d) return;
  var fullText = 'Subject: ' + d.subject + '\n\n' + d.body;
  var btn = document.getElementById('copy-btn-' + idx);

  navigator.clipboard.writeText(fullText).then(function() {
    if (btn) {
      btn.classList.add('copied');
      btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> Copied!';
      setTimeout(function() {
        btn.classList.remove('copied');
        btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg> Copy to Clipboard';
      }, 2000);
    }

    fetch('/property/{{ prop.id }}/email-log', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        email_type: d.email_type,
        recipient_type: d.recipient_type,
        recipient_name: d.recipient_name,
        subject: d.subject,
        body: d.body,
        tone: d.tone,
        status: 'copied'
      })
    });
  });
}
</script>
{% endif %}

</body>
</html>"""


# ─────────────────────────────────────────────────────────────
#  ADMIN SYNC PAGE TEMPLATE
# ─────────────────────────────────────────────────────────────

ADMIN_SYNC_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sync Admin — NUVU</title>
<link rel="icon" href="/static/logo.png">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --navy:#0f1b2d;--navy-lt:#162236;--navy-md:#1c2e4a;
  --lime:#c4e233;--lime-dk:#a3bf1a;
  --red:#e11d48;--green:#16a34a;--amber:#f97316;--blue:#3b82f6;
  --white:#ffffff;--off-white:#f4f6f9;
  --txt:#1e293b;--txt-mid:#475569;--txt-light:#94a3b8;
  --card-shadow:0 2px 12px rgba(0,0,0,.08);
}
html{font-size:15px}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--off-white);color:var(--txt);min-height:100vh}

/* ═══ HEADER ═════════════════════════════════════════════ */
.sync-header{
  background:var(--navy);padding:28px 40px;
  display:flex;justify-content:space-between;align-items:center;
}
.sync-header-left{display:flex;align-items:center;gap:16px}
.sync-header-left img{width:40px;height:40px;border-radius:10px}
.sync-header-left h1{font-size:1.4rem;font-weight:900;color:var(--white);letter-spacing:6px}
.sync-header-left .tag{
  font-size:.65rem;color:var(--lime);text-transform:uppercase;
  letter-spacing:2px;font-weight:700;margin-left:8px;
  background:rgba(196,226,51,.12);padding:4px 12px;border-radius:12px;
}
.back-btn{
  display:inline-flex;align-items:center;gap:8px;
  background:var(--lime);color:var(--navy);border:none;border-radius:8px;
  padding:8px 18px;font-size:.82rem;font-weight:700;
  text-decoration:none;transition:all .2s ease;cursor:pointer;
}
.back-btn:hover{background:var(--lime-dk);transform:translateY(-1px)}

/* ═══ CONTENT ════════════════════════════════════════════ */
.sync-content{max-width:960px;margin:0 auto;padding:32px 32px 60px}

/* ═══ FLASH MESSAGE ══════════════════════════════════════ */
.flash{
  padding:14px 20px;border-radius:10px;margin-bottom:24px;
  font-size:.88rem;font-weight:600;display:flex;align-items:center;gap:10px;
}
.flash-success{background:#dcfce7;color:#166534;border:1px solid #86efac}
.flash-error{background:#fee2e2;color:#be123c;border:1px solid #fca5a5}

/* ═══ CONNECTOR CARDS ════════════════════════════════════ */
.section-title{
  font-size:.7rem;text-transform:uppercase;letter-spacing:1.5px;
  color:var(--txt-light);font-weight:700;margin-bottom:16px;
}
.connector-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px;margin-bottom:40px}
.conn-card{
  background:var(--white);border-radius:14px;padding:24px;
  box-shadow:var(--card-shadow);border:1px solid #e8ecf1;
}
.conn-card-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
.conn-name{font-size:1.1rem;font-weight:800;color:var(--txt)}
.conn-status{
  padding:4px 12px;border-radius:12px;font-size:.68rem;
  font-weight:800;letter-spacing:.5px;
}
.conn-status.connected{background:#dcfce7;color:#166534}
.conn-status.disconnected{background:#fee2e2;color:#be123c}
.conn-status.stub{background:#fef3c7;color:#92400e}
.conn-detail{font-size:.82rem;color:var(--txt-light);margin-bottom:4px}
.conn-detail strong{color:var(--txt-mid)}
.conn-actions{margin-top:18px;display:flex;gap:10px}
.sync-btn{
  display:inline-flex;align-items:center;gap:6px;
  background:var(--lime);color:var(--navy);border:none;border-radius:8px;
  padding:10px 20px;font-size:.82rem;font-weight:700;
  cursor:pointer;transition:all .15s ease;
}
.sync-btn:hover{background:var(--lime-dk);transform:translateY(-1px)}
.sync-btn:active{transform:translateY(0)}
.sync-btn svg{width:16px;height:16px}

/* ═══ HISTORY TABLE ══════════════════════════════════════ */
.history-card{
  background:var(--white);border-radius:14px;padding:24px;
  box-shadow:var(--card-shadow);border:1px solid #e8ecf1;
}
.history-table{width:100%;border-collapse:collapse;font-size:.84rem}
.history-table th{
  text-align:left;padding:10px 14px;
  font-size:.68rem;text-transform:uppercase;letter-spacing:1px;
  color:var(--txt-light);font-weight:700;border-bottom:2px solid #e8ecf1;
}
.history-table td{padding:10px 14px;border-bottom:1px solid #f1f5f9;color:var(--txt-mid)}
.history-table tr:last-child td{border-bottom:none}
.badge{
  display:inline-block;padding:3px 10px;border-radius:5px;
  font-size:.68rem;font-weight:800;letter-spacing:.5px;color:var(--white);
}
.badge-success{background:var(--green)}
.badge-error{background:var(--red)}
.badge-running{background:var(--blue)}
.badge-inbound{background:var(--blue)}
.badge-outbound{background:#8b5cf6}
.writeback-tag{
  display:inline-block;padding:2px 8px;border-radius:4px;
  font-size:.6rem;font-weight:700;letter-spacing:.5px;
  margin-left:6px;
}
.writeback-yes{background:#dcfce7;color:#166534}
.writeback-no{background:#f1f5f9;color:#94a3b8}
.empty-state{
  text-align:center;padding:40px 20px;color:var(--txt-light);
  font-size:.92rem;font-weight:500;
}
.empty-state .icon{font-size:2rem;margin-bottom:12px;display:block}

/* ═══ RESPONSIVE ═════════════════════════════════════════ */
@media(max-width:768px){
  html{font-size:12px}
  .sync-header{flex-direction:column;gap:16px;align-items:flex-start;padding:20px 16px}
  .sync-content{padding:20px 16px 40px}
  .connector-grid{grid-template-columns:1fr}
  .history-table{font-size:.78rem}
  .history-table th,.history-table td{padding:8px 10px}
}
</style>
</head>
<body>

<!-- ═══ HEADER ═══════════════════════════════════════════ -->
<div class="sync-header">
  <div class="sync-header-left">
    <img src="/static/logo.png" alt="NUVU">
    <h1>NUVU</h1>
    <span class="tag">Sync Admin</span>
  </div>
  <a href="/" class="back-btn">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
    Back to Dashboard
  </a>
</div>

<div class="sync-content">

  <!-- ═══ FLASH MESSAGE ═══════════════════════════════════ -->
  {% if sync_result %}
  <div class="flash {{ 'flash-success' if sync_result.status == 'success' else 'flash-error' }}">
    {% if sync_result.status == 'success' %}
    &#x2705; Sync complete — {{ sync_result.total }} properties ({{ sync_result.created }} new, {{ sync_result.updated }} updated) in {{ "%.1f"|format(sync_result.duration_seconds) }}s
    {% else %}
    &#x274C; Sync failed — {{ sync_result.error_message }}
    {% endif %}
  </div>
  {% endif %}

  <!-- ═══ CONNECTORS ══════════════════════════════════════ -->
  <div class="section-title">&#x1F50C; Registered Connectors</div>
  <div class="connector-grid">
    {% for conn in connectors %}
    <div class="conn-card">
      <div class="conn-card-top">
        <span class="conn-name">{{ conn.display_name }}</span>
        {% if conn.connected %}
        <span class="conn-status connected">&#x2705; Connected</span>
        {% else %}
        <span class="conn-status stub">&#x1F6A7; Stub Mode</span>
        {% endif %}
      </div>
      <div class="conn-detail">Last sync: <strong>{{ conn.last_sync or 'Never' }}</strong></div>
      {% if conn.last_status %}
      <div class="conn-detail">Last status: <strong>{{ conn.last_status }}</strong></div>
      {% endif %}
      <div class="conn-detail">Writeback:
        {% if conn.supports_writeback %}
        <span class="writeback-tag writeback-yes">&#x2194;&#xFE0F; TWO-WAY</span>
        {% else %}
        <span class="writeback-tag writeback-no">&#x2B07;&#xFE0F; INBOUND ONLY</span>
        {% endif %}
      </div>
      {% if conn.last_error %}
      <div class="conn-detail" style="color:var(--red)">Error: {{ conn.last_error }}</div>
      {% endif %}
      <div class="conn-actions">
        <form method="POST" action="/admin/sync" style="display:inline">
          <input type="hidden" name="connector_name" value="{{ conn.name }}">
          <button type="submit" class="sync-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>
            Run Sync
          </button>
        </form>
      </div>
    </div>
    {% endfor %}
  </div>

  <!-- ═══ SYNC HISTORY ════════════════════════════════════ -->
  <div class="section-title">&#x1F4CB; Sync History</div>
  <div class="history-card">
    {% if history %}
    <table class="history-table">
      <thead>
        <tr>
          <th>Connector</th>
          <th>Direction</th>
          <th>Started</th>
          <th>Status</th>
          <th>Properties</th>
          <th>New</th>
          <th>Updated</th>
          <th>Errors</th>
        </tr>
      </thead>
      <tbody>
        {% for h in history %}
        <tr>
          <td><strong>{{ h.connector_name }}</strong></td>
          <td>
            {% if h.get('direction') == 'outbound' %}
            <span class="badge badge-outbound">&#x2B06;&#xFE0F; OUT</span>
            {% else %}
            <span class="badge badge-inbound">&#x2B07;&#xFE0F; IN</span>
            {% endif %}
          </td>
          <td>{{ h.started_at }}</td>
          <td>
            {% if h.status == 'success' %}
            <span class="badge badge-success">SUCCESS</span>
            {% elif h.status == 'error' %}
            <span class="badge badge-error">ERROR</span>
            {% else %}
            <span class="badge badge-running">RUNNING</span>
            {% endif %}
          </td>
          <td>{{ h.properties_synced or 0 }}</td>
          <td>{{ h.properties_created or 0 }}</td>
          <td>{{ h.properties_updated or 0 }}</td>
          <td>{{ h.error_message or '—' }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <div class="empty-state">
      <span class="icon">&#x1F4E1;</span>
      No syncs have been run yet.<br>Click "Run Sync" on a connector above to get started.
    </div>
    {% endif %}
  </div>

</div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────
#  ADMIN SYNC ROUTES
# ─────────────────────────────────────────────────────────────

# ── NOTES API ──────────────────────────────────────────────

@app.route("/property/<prop_id>/notes", methods=["POST"])
def add_note(prop_id):
    """Save a new note for a property, then run AI parser."""
    prop = get_props_by_id().get(prop_id)
    if not prop:
        return "Property not found", 404

    note_text = request.form.get("note_text", "").strip()
    author = request.form.get("author", "Agent").strip() or "Agent"

    if not note_text:
        return redirect(f"/property/{prop_id}")

    db = get_db()
    db.execute(
        """INSERT INTO notes (property_id, note_text, author, source)
           VALUES (?, ?, ?, 'manual')""",
        (prop["db_id"], note_text, author),
    )
    db.commit()

    # ── AI Note Parsing ──────────────────────────────────────
    ai_result = parse_note(note_text)
    ai_changes = None
    if ai_result["summary"]:
        ai_changes = apply_ai_results(db, prop["db_id"], ai_result)

    db.close()

    # ── Completion Engine Recalculation ───────────────────────
    recalculate_property(prop["db_id"])

    # ── Outbound Sync (NUVU → CRM) ─────────────────────────
    # Push note back to the originating CRM
    try:
        push_note_to_crm(prop["db_id"], note_text, author)
        # If AI updated milestones, push those too
        if ai_changes and ai_changes.get("milestones_updated"):
            from datetime import datetime as _dt
            today = _dt.now().strftime("%Y-%m-%d")
            for ms_name in ai_result.get("milestones_completed", []):
                push_milestone_to_crm(prop["db_id"], ms_name, True, today)
        # If AI detected issues (status change), push that
        if ai_changes and ai_changes.get("status_changed"):
            push_status_to_crm(prop["db_id"], "at-risk", "Issue detected by AI parser")
    except Exception as outbound_err:
        print(f"  [outbound] Non-critical error: {outbound_err}")

    # Pass AI feedback via query string so it's truly one-shot
    if ai_result["summary"]:
        import urllib.parse
        fb_str = "|".join(ai_result["summary"])
        return redirect(f"/property/{prop_id}?ai={urllib.parse.quote(fb_str)}")

    return redirect(f"/property/{prop_id}")


@app.route("/property/<prop_id>/notes/<int:note_id>/urgent", methods=["POST"])
def toggle_urgent(prop_id, note_id):
    """Toggle the is_urgent flag on a note."""
    db = get_db()
    note = db.execute("SELECT is_urgent FROM notes WHERE id = ?", (note_id,)).fetchone()
    if note:
        new_val = 0 if note["is_urgent"] else 1
        db.execute("UPDATE notes SET is_urgent = ? WHERE id = ?", (new_val, note_id))
        db.commit()
    db.close()

    return redirect(f"/property/{prop_id}")


@app.route("/property/<prop_id>/email-log", methods=["POST"])
def log_email(prop_id):
    """Log an email action (copied to clipboard, drafted, etc.) for audit trail."""
    prop = get_props_by_id().get(prop_id)
    if not prop:
        return jsonify({"error": "Property not found"}), 404

    data = request.get_json() or {}

    db = get_db()
    db.execute(
        """INSERT INTO email_log
           (property_id, email_type, recipient_type, recipient_name,
            subject, body_text, tone, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            prop["db_id"],
            data.get("email_type", "unknown"),
            data.get("recipient_type", "solicitor"),
            data.get("recipient_name", ""),
            data.get("subject", ""),
            data.get("body", ""),
            data.get("tone", "professional"),
            data.get("status", "copied"),
        ),
    )
    db.commit()
    db.close()

    return jsonify({"ok": True})


@app.route("/admin/sync", methods=["GET"])
def admin_sync():
    return render_template_string(
        ADMIN_SYNC_HTML,
        connectors=sync_manager.list_connectors(),
        history=sync_manager.get_sync_history(),
        sync_result=None,
    )


@app.route("/admin/sync", methods=["POST"])
def admin_sync_run():
    connector_name = request.form.get("connector_name", "")
    result = sync_manager.run_sync(connector_name)
    return render_template_string(
        ADMIN_SYNC_HTML,
        connectors=sync_manager.list_connectors(),
        history=sync_manager.get_sync_history(),
        sync_result=result,
    )


# ─────────────────────────────────────────────────────────────
#  ADMIN EMAIL TEMPLATES PAGE
# ─────────────────────────────────────────────────────────────

ADMIN_EMAIL_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NUVU — Email Templates</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f4f6f9;color:#1e293b}
:root{--navy:#0f1b2d;--navy-lt:#162236;--lime:#c4e233;--lime-dk:#a3bf1a;--green:#16a34a;--blue:#3b82f6;--red:#e11d48;--white:#fff;--txt:#1e293b;--txt-mid:#475569;--txt-light:#94a3b8}
.header{background:var(--navy);padding:20px 32px;display:flex;align-items:center;justify-content:space-between}
.header-left{display:flex;align-items:center;gap:14px}
.header-left img{width:32px;height:32px;border-radius:8px}
.header-left span{font-size:1rem;font-weight:900;color:var(--white);letter-spacing:8px}
.header-tag{font-size:.65rem;background:var(--blue);color:var(--white);padding:4px 12px;border-radius:6px;font-weight:700;text-transform:uppercase;letter-spacing:1px}
.header-right a{color:var(--lime);text-decoration:none;font-size:.82rem;font-weight:700;display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border:1px solid rgba(196,226,51,.3);border-radius:8px;background:rgba(196,226,51,.1)}
.header-right a:hover{background:var(--lime);color:var(--navy);border-color:var(--lime)}
.content{max-width:960px;margin:0 auto;padding:28px 32px 60px}
.flash{padding:14px 20px;border-radius:10px;font-size:.84rem;font-weight:600;margin-bottom:20px;display:flex;align-items:center;gap:8px}
.flash.success{background:#dcfce7;color:#166534;border:1px solid #bbf7d0}
.section-title{font-size:.65rem;text-transform:uppercase;letter-spacing:1.5px;color:var(--txt-light);font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.tone-card{background:var(--white);border-radius:14px;padding:22px 28px;box-shadow:0 2px 12px rgba(0,0,0,.06);border:1px solid #e8ecf1;margin-bottom:24px}
.tone-options{display:flex;gap:16px;flex-wrap:wrap;margin:12px 0 16px}
.tone-option{display:flex;align-items:center;gap:8px;cursor:pointer}
.tone-option input[type="radio"]{accent-color:var(--blue);width:16px;height:16px}
.tone-option label{font-size:.88rem;font-weight:600;cursor:pointer;color:var(--txt)}
.tone-desc{font-size:.75rem;color:var(--txt-light);margin-left:24px;margin-top:2px}
.save-btn{background:var(--blue);color:var(--white);border:none;padding:8px 24px;border-radius:8px;font-size:.82rem;font-weight:700;cursor:pointer;transition:all .15s}
.save-btn:hover{background:#2563eb}
.tmpl-card{background:var(--white);border-radius:14px;padding:20px 24px;box-shadow:0 2px 12px rgba(0,0,0,.06);border:1px solid #e8ecf1;margin-bottom:14px}
.tmpl-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px}
.tmpl-name{font-size:.95rem;font-weight:700;color:var(--txt)}
.tmpl-recipient{font-size:.6rem;text-transform:uppercase;letter-spacing:.8px;padding:3px 10px;border-radius:6px;font-weight:800;background:#e0f2fe;color:#075985}
.tmpl-label{font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--txt-light);margin:10px 0 4px}
.tmpl-subject{font-size:.88rem;color:var(--txt-mid);padding:8px 12px;background:#f8fafc;border-radius:6px;border:1px solid #e8ecf1;font-family:inherit}
.tmpl-body{font-size:.8rem;color:var(--txt-mid);padding:10px 14px;background:#f8fafc;border-radius:6px;border:1px solid #e8ecf1;white-space:pre-wrap;line-height:1.6;font-family:inherit;max-height:200px;overflow-y:auto}
.tmpl-placeholders{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}
.tmpl-placeholder{font-size:.6rem;background:#f0f7ff;color:var(--blue);padding:2px 8px;border-radius:4px;font-weight:600;font-family:'SF Mono',Monaco,Consolas,monospace}
.history-section{margin-top:32px}
.history-table{width:100%;border-collapse:collapse;background:var(--white);border-radius:14px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.06);border:1px solid #e8ecf1}
.history-table th{background:#f8fafc;font-size:.62rem;text-transform:uppercase;letter-spacing:1px;color:var(--txt-light);padding:10px 14px;text-align:left;font-weight:700}
.history-table td{padding:10px 14px;font-size:.8rem;color:var(--txt-mid);border-top:1px solid #f1f3f5}
.history-table tr:hover td{background:#fafbfc}
.status-badge{font-size:.6rem;padding:2px 8px;border-radius:4px;font-weight:700;text-transform:uppercase}
.status-badge.copied{background:#dcfce7;color:#166534}
.status-badge.drafted{background:#fef3c7;color:#92400e}
.status-badge.sent{background:#e0f2fe;color:#075985}
.empty-state{text-align:center;padding:32px;color:var(--txt-light);font-size:.88rem}
@media(max-width:768px){
  .header{padding:14px 16px;flex-direction:column;gap:12px}
  .content{padding:16px 16px 40px}
  .tone-options{flex-direction:column;gap:10px}
}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <img src="/static/logo.png" alt="NUVU">
    <span>NUVU</span>
    <span class="header-tag">Email Templates</span>
  </div>
  <div class="header-right">
    <a href="/">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
      Dashboard
    </a>
  </div>
</div>

<div class="content">

  {% if save_result %}
  <div class="flash success">✓ Tone preference saved to "{{ save_result.tone }}"</div>
  {% endif %}

  <!-- TONE PREFERENCE -->
  <div class="section-title">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
    Tone of Voice
  </div>
  <div class="tone-card">
    <form method="POST" action="/admin/email-templates">
      <div class="tone-options">
        <div>
          <div class="tone-option">
            <input type="radio" name="default_tone" value="friendly" id="tone-friendly"
                   {{ 'checked' if current_tone == 'friendly' else '' }}>
            <label for="tone-friendly">Friendly</label>
          </div>
          <div class="tone-desc">"Hi Sarah" — casual, warm, approachable</div>
        </div>
        <div>
          <div class="tone-option">
            <input type="radio" name="default_tone" value="professional" id="tone-professional"
                   {{ 'checked' if current_tone == 'professional' else '' }}>
            <label for="tone-professional">Professional</label>
          </div>
          <div class="tone-desc">"Dear Sarah" — formal, courteous, business-standard</div>
        </div>
        <div>
          <div class="tone-option">
            <input type="radio" name="default_tone" value="firm" id="tone-firm"
                   {{ 'checked' if current_tone == 'firm' else '' }}>
            <label for="tone-firm">Firm</label>
          </div>
          <div class="tone-desc">"Dear Sarah" — direct, urgent, no-nonsense</div>
        </div>
      </div>
      <button type="submit" class="save-btn">Save Tone Preference</button>
    </form>
  </div>

  <!-- TEMPLATES -->
  <div class="section-title" style="margin-top:28px">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
    Email Templates ({{ templates|length }})
  </div>

  {% for key, tmpl in templates.items() %}
  <div class="tmpl-card">
    <div class="tmpl-head">
      <span class="tmpl-name">{{ tmpl.display_name }}</span>
      <span class="tmpl-recipient">To: {{ tmpl.recipient_type }}</span>
    </div>
    <div class="tmpl-label">Subject</div>
    <div class="tmpl-subject">{{ tmpl.subject }}</div>
    <div class="tmpl-label">Body</div>
    <div class="tmpl-body">{{ tmpl.body }}</div>
    <div class="tmpl-label">Available Placeholders</div>
    <div class="tmpl-placeholders">
      {% for p in tmpl.placeholders %}
      <span class="tmpl-placeholder">{{ '{' }}{{ p }}{{ '}' }}</span>
      {% endfor %}
    </div>
  </div>
  {% endfor %}

  <!-- EMAIL HISTORY -->
  <div class="history-section">
    <div class="section-title">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      Email History (last 20)
    </div>

    {% if email_history %}
    <table class="history-table">
      <thead>
        <tr>
          <th>Date</th>
          <th>Property</th>
          <th>Type</th>
          <th>Recipient</th>
          <th>Subject</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {% for h in email_history %}
        <tr>
          <td>{{ h.created_at[:16] }}</td>
          <td>{{ h.address }}</td>
          <td>{{ h.email_type | replace('_', ' ') | title }}</td>
          <td>{{ h.recipient_name or h.recipient_type }}</td>
          <td>{{ h.subject[:50] }}{{ '...' if h.subject|length > 50 else '' }}</td>
          <td><span class="status-badge {{ h.status }}">{{ h.status }}</span></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <div class="empty-state">No emails logged yet. Copy an email from a property page to see it here.</div>
    {% endif %}
  </div>

</div>
</body>
</html>"""


@app.route("/admin/email-templates", methods=["GET"])
def admin_email_templates():
    db = get_db()

    # Get current tone preference
    pref = db.execute(
        "SELECT preference_value FROM email_preferences WHERE preference_key = 'default_tone'"
    ).fetchone()
    current_tone = pref["preference_value"] if pref else "professional"

    # Get recent email log entries
    email_history = db.execute(
        """SELECT el.*, p.address
           FROM email_log el
           JOIN properties p ON p.id = el.property_id
           ORDER BY el.created_at DESC LIMIT 20"""
    ).fetchall()
    email_history = [dict(r) for r in email_history]
    db.close()

    return render_template_string(
        ADMIN_EMAIL_HTML,
        templates=TEMPLATES,
        current_tone=current_tone,
        tone_options=list(TONE_CONFIG.keys()),
        email_history=email_history,
        save_result=None,
    )


@app.route("/admin/email-templates", methods=["POST"])
def admin_email_templates_save():
    new_tone = request.form.get("default_tone", "professional")
    if new_tone not in TONE_CONFIG:
        new_tone = "professional"

    db = get_db()
    db.execute(
        """INSERT INTO email_preferences (preference_key, preference_value, updated_at)
           VALUES ('default_tone', ?, datetime('now'))
           ON CONFLICT(preference_key) DO UPDATE SET
           preference_value = excluded.preference_value,
           updated_at = datetime('now')""",
        (new_tone,),
    )
    db.commit()

    # Refresh data
    pref = db.execute(
        "SELECT preference_value FROM email_preferences WHERE preference_key = 'default_tone'"
    ).fetchone()
    current_tone = pref["preference_value"] if pref else "professional"

    email_history = db.execute(
        """SELECT el.*, p.address
           FROM email_log el
           JOIN properties p ON p.id = el.property_id
           ORDER BY el.created_at DESC LIMIT 20"""
    ).fetchall()
    email_history = [dict(r) for r in email_history]
    db.close()

    return render_template_string(
        ADMIN_EMAIL_HTML,
        templates=TEMPLATES,
        current_tone=current_tone,
        tone_options=list(TONE_CONFIG.keys()),
        email_history=email_history,
        save_result={"status": "success", "tone": new_tone},
    )


# ─────────────────────────────────────────────────────────────
#  ADMIN EMAIL INBOX (email parser test interface)
# ─────────────────────────────────────────────────────────────

ADMIN_EMAIL_INBOX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Email Inbox — NUVU</title>
<link rel="icon" href="/static/logo.png">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --navy:#0f1b2d;--navy-lt:#162236;--navy-md:#1c2e4a;
  --lime:#c4e233;--lime-dk:#a3bf1a;
  --red:#e11d48;--green:#16a34a;--amber:#f97316;--blue:#3b82f6;--purple:#8b5cf6;
  --white:#ffffff;--off-white:#f4f6f9;
  --txt:#1e293b;--txt-mid:#475569;--txt-light:#94a3b8;
  --card-shadow:0 2px 12px rgba(0,0,0,.08);
}
html{font-size:15px}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--off-white);color:var(--txt);min-height:100vh}

.inbox-header{
  background:var(--navy);padding:28px 40px;
  display:flex;justify-content:space-between;align-items:center;
}
.inbox-header-left{display:flex;align-items:center;gap:16px}
.inbox-header-left img{width:40px;height:40px;border-radius:10px}
.inbox-header-left h1{font-size:1.4rem;font-weight:900;color:var(--white);letter-spacing:6px}
.inbox-header-left .tag{
  font-size:.65rem;color:var(--lime);text-transform:uppercase;
  letter-spacing:2px;font-weight:700;margin-left:8px;
  background:rgba(196,226,51,.12);padding:4px 12px;border-radius:12px;
}
.back-link{
  display:inline-flex;align-items:center;gap:8px;
  background:var(--lime);color:var(--navy);border:none;border-radius:8px;
  padding:8px 18px;font-size:.82rem;font-weight:700;
  text-decoration:none;transition:all .2s ease;cursor:pointer;
}
.back-link:hover{background:var(--lime-dk);transform:translateY(-1px)}

.inbox-content{max-width:1100px;margin:0 auto;padding:32px 32px 60px}
.section-title{
  font-size:.7rem;text-transform:uppercase;letter-spacing:1.5px;
  color:var(--txt-light);font-weight:700;margin-bottom:16px;
}

/* ═══ EMAIL FORM ════════════════════════════════════════════ */
.form-card{
  background:var(--white);border-radius:14px;padding:28px;
  box-shadow:var(--card-shadow);border:1px solid #e8ecf1;
  margin-bottom:32px;
}
.form-row{margin-bottom:16px}
.form-label{display:block;font-size:.76rem;font-weight:700;color:var(--txt-mid);
  text-transform:uppercase;letter-spacing:.8px;margin-bottom:6px}
.form-input{
  width:100%;padding:10px 14px;border:1.5px solid #e2e8f0;border-radius:8px;
  font-size:.88rem;font-family:inherit;transition:border-color .2s;
  background:var(--white);color:var(--txt);
}
.form-input:focus{outline:none;border-color:var(--lime);box-shadow:0 0 0 3px rgba(196,226,51,.15)}
textarea.form-input{resize:vertical;min-height:160px;line-height:1.6}
.submit-btn{
  display:inline-flex;align-items:center;gap:8px;
  background:var(--navy);color:var(--white);border:none;border-radius:10px;
  padding:12px 28px;font-size:.88rem;font-weight:700;letter-spacing:.3px;
  cursor:pointer;transition:all .15s ease;
}
.submit-btn:hover{background:var(--navy-md);transform:translateY(-1px)}
.submit-btn svg{width:18px;height:18px}

/* ═══ SAMPLE EMAILS ═════════════════════════════════════════ */
.sample-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;margin-bottom:36px}
.sample-card{
  background:var(--white);border-radius:12px;padding:18px 20px;
  box-shadow:var(--card-shadow);border:1px solid #e8ecf1;
  cursor:pointer;transition:all .2s ease;position:relative;
}
.sample-card:hover{transform:translateY(-2px);box-shadow:0 4px 20px rgba(0,0,0,.12);border-color:var(--lime)}
.sample-tag{
  display:inline-block;padding:3px 10px;border-radius:5px;
  font-size:.62rem;font-weight:800;letter-spacing:.5px;color:var(--white);
  margin-bottom:10px;text-transform:uppercase;
}
.sample-subject{font-size:.88rem;font-weight:700;color:var(--txt);margin-bottom:6px;line-height:1.4}
.sample-sender{font-size:.76rem;color:var(--txt-light)}
.sample-load{
  position:absolute;top:18px;right:18px;
  font-size:.65rem;color:var(--lime-dk);font-weight:700;
  text-transform:uppercase;letter-spacing:.5px;opacity:0;transition:opacity .2s;
}
.sample-card:hover .sample-load{opacity:1}

/* ═══ PARSE RESULT ══════════════════════════════════════════ */
.result-card{
  background:var(--white);border-radius:14px;padding:28px;
  box-shadow:var(--card-shadow);border:1px solid #e8ecf1;margin-bottom:32px;
}
.result-section{margin-bottom:20px}
.result-label{
  font-size:.68rem;text-transform:uppercase;letter-spacing:1px;
  color:var(--txt-light);font-weight:700;margin-bottom:8px;
}
.result-match{
  display:flex;align-items:center;gap:14px;padding:14px 18px;
  border-radius:10px;margin-bottom:6px;
}
.result-match.high{background:#dcfce7;border:1px solid #86efac}
.result-match.medium{background:#fef3c7;border:1px solid #fde68a}
.result-match.low{background:#fee2e2;border:1px solid #fca5a5}
.result-match.none{background:#f1f5f9;border:1px solid #e2e8f0}
.match-conf{
  font-size:1.6rem;font-weight:900;min-width:60px;text-align:center;
}
.match-conf.high{color:var(--green)}
.match-conf.medium{color:var(--amber)}
.match-conf.low{color:var(--red)}
.match-conf.none{color:var(--txt-light)}
.match-info{flex:1}
.match-property{font-size:1rem;font-weight:800;color:var(--txt)}
.match-reason{font-size:.78rem;color:var(--txt-mid);margin-top:2px}

.result-list{list-style:none;padding:0}
.result-list li{
  padding:8px 14px;font-size:.86rem;border-radius:6px;
  margin-bottom:4px;display:flex;align-items:center;gap:8px;
}
.result-list .milestone{background:#dcfce7;color:#166534}
.result-list .date{background:#dbeafe;color:#1e40af}
.result-list .issue{background:#fef3c7;color:#92400e}
.result-list .critical{background:#fee2e2;color:#991b1b;font-weight:700}
.result-list .info{background:#f1f5f9;color:var(--txt-mid)}

.badge{
  display:inline-block;padding:3px 10px;border-radius:5px;
  font-size:.68rem;font-weight:800;letter-spacing:.5px;color:var(--white);
}
.badge-green{background:var(--green)}
.badge-amber{background:var(--amber)}
.badge-red{background:var(--red)}
.badge-blue{background:var(--blue)}
.badge-purple{background:var(--purple)}

.applied-banner{
  padding:16px 20px;border-radius:10px;margin-top:20px;
  font-size:.88rem;font-weight:600;display:flex;align-items:center;gap:10px;
}
.applied-banner.success{background:#dcfce7;color:#166534;border:1px solid #86efac}
.applied-banner.warning{background:#fef3c7;color:#92400e;border:1px solid #fde68a}
.applied-banner.error{background:#fee2e2;color:#be123c;border:1px solid #fca5a5}

/* ═══ HISTORY ═══════════════════════════════════════════════ */
.history-table{width:100%;border-collapse:collapse;font-size:.82rem}
.history-table th{
  text-align:left;padding:10px 14px;
  font-size:.66rem;text-transform:uppercase;letter-spacing:1px;
  color:var(--txt-light);font-weight:700;border-bottom:2px solid #e8ecf1;
}
.history-table td{padding:10px 14px;border-bottom:1px solid #f1f5f9;color:var(--txt-mid)}
.history-table tr:last-child td{border-bottom:none}
.empty-state{text-align:center;padding:40px;color:var(--txt-light);font-size:.92rem}

@media(max-width:768px){
  html{font-size:12px}
  .inbox-header{flex-direction:column;gap:16px;align-items:flex-start;padding:20px 16px}
  .inbox-content{padding:20px 16px 40px}
  .sample-grid{grid-template-columns:1fr}
}
</style>
</head>
<body>

<!-- ═══ HEADER ═══════════════════════════════════════════ -->
<div class="inbox-header">
  <div class="inbox-header-left">
    <img src="/static/logo.png" alt="NUVU">
    <h1>NUVU</h1>
    <span class="tag">Email Inbox</span>
  </div>
  <a href="/" class="back-link">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
    Dashboard
  </a>
</div>

<div class="inbox-content">

  {% if parse_result %}
  <!-- ═══ PARSE RESULT ══════════════════════════════════════ -->
  <div class="section-title">&#x1F4E8; Parse Result</div>
  <div class="result-card">

    <!-- Property Match -->
    <div class="result-section">
      <div class="result-label">Property Match</div>
      {% if parse_result.matched_property %}
        {% set conf = parse_result.match_confidence %}
        {% set level = 'high' if conf >= 70 else ('medium' if conf >= 50 else 'low') %}
        <div class="result-match {{ level }}">
          <div class="match-conf {{ level }}">{{ conf }}%</div>
          <div class="match-info">
            <div class="match-property">{{ parse_result.matched_property.address }}, {{ parse_result.matched_property.location }}</div>
            <div class="match-reason">{{ parse_result.match_reason }}</div>
          </div>
          <a href="/property/{{ parse_result.matched_property.id }}" style="font-size:.78rem;color:var(--blue);font-weight:600;text-decoration:none">View &rarr;</a>
        </div>
      {% else %}
        <div class="result-match none">
          <div class="match-conf none">0%</div>
          <div class="match-info">
            <div class="match-property">No matching property found</div>
            <div class="match-reason">Could not match email to any property in the database</div>
          </div>
        </div>
      {% endif %}
    </div>

    <!-- Summary -->
    <div class="result-section">
      <div class="result-label">AI Analysis</div>
      <ul class="result-list">
        {% for line in parse_result.summary %}
          {% if 'CRITICAL' in line %}
          <li class="critical">&#x1F6A8; {{ line }}</li>
          {% elif '⚠' in line or 'Issue' in line or 'issue' in line %}
          <li class="issue">&#x26A0;&#xFE0F; {{ line }}</li>
          {% elif '✅' in line or '✓' in line %}
          <li class="milestone">{{ line }}</li>
          {% elif '📅' in line or 'Date' in line %}
          <li class="date">{{ line }}</li>
          {% else %}
          <li class="info">{{ line }}</li>
          {% endif %}
        {% endfor %}
      </ul>
    </div>

    <!-- Milestones -->
    {% if parse_result.milestones_to_update %}
    <div class="result-section">
      <div class="result-label">Milestones Updated</div>
      <ul class="result-list">
        {% for ms in parse_result.milestones_to_update %}
        <li class="milestone">&#x2705; {{ ms }}</li>
        {% endfor %}
      </ul>
    </div>
    {% endif %}

    <!-- Issues -->
    {% if parse_result.issues %}
    <div class="result-section">
      <div class="result-label">Issues Detected</div>
      <ul class="result-list">
        {% for iss in parse_result.issues %}
          {% if iss.critical %}
          <li class="critical">&#x1F6A8; {{ iss.description }}<br><small>Action: {{ iss.suggested_action }}</small></li>
          {% else %}
          <li class="issue">&#x26A0;&#xFE0F; {{ iss.description }}<br><small>Action: {{ iss.suggested_action }}</small></li>
          {% endif %}
        {% endfor %}
      </ul>
    </div>
    {% endif %}

    <!-- Dates -->
    {% if parse_result.dates_found %}
    <div class="result-section">
      <div class="result-label">Dates Extracted</div>
      <ul class="result-list">
        {% for d in parse_result.dates_found %}
        <li class="date">&#x1F4C5; {{ d[0] }}</li>
        {% endfor %}
      </ul>
    </div>
    {% endif %}

    <!-- Applied actions -->
    {% if parse_result.applied %}
    <div class="applied-banner success">
      &#x2705; <strong>Changes applied:</strong>&nbsp;
      Note created (source: email)
      {% if parse_result.milestones_updated > 0 %} &middot; {{ parse_result.milestones_updated }} milestone{{ 's' if parse_result.milestones_updated > 1 }} updated{% endif %}
      {% if parse_result.dates_updated > 0 %} &middot; {{ parse_result.dates_updated }} date{{ 's' if parse_result.dates_updated > 1 }} set{% endif %}
      {% if parse_result.status_changed %} &middot; Status changed{% endif %}
      &middot; Outbound CRM sync triggered
    </div>
    {% elif parse_result.matched_property %}
    <div class="applied-banner warning">
      &#x26A0;&#xFE0F; Property matched but no changes could be applied
    </div>
    {% else %}
    <div class="applied-banner error">
      &#x274C; No property match — email could not be processed automatically
    </div>
    {% endif %}

  </div>
  {% endif %}

  <!-- ═══ SAMPLE EMAILS ═════════════════════════════════════ -->
  <div class="section-title">&#x1F4EC; Sample Test Emails (click to load)</div>
  <div class="sample-grid">
    {% for sample in samples %}
    <div class="sample-card" onclick="loadSample('{{ sample.id }}')">
      <span class="sample-tag" style="background:{{ sample.tag_color }}">{{ sample.tag }}</span>
      <span class="sample-load">&#x2197; Load</span>
      <div class="sample-subject">{{ sample.subject }}</div>
      <div class="sample-sender">{{ sample.sender }}</div>
    </div>
    {% endfor %}
  </div>

  <!-- ═══ EMAIL FORM ════════════════════════════════════════ -->
  <div class="section-title">&#x2709;&#xFE0F; Paste an Email</div>
  <div class="form-card">
    <form method="POST" action="/admin/email-inbox">
      <div class="form-row">
        <label class="form-label" for="sender">From (sender)</label>
        <input type="text" id="sender" name="sender" class="form-input"
               placeholder="e.g. conveyancing@burnetts.co.uk"
               value="{{ form_sender or '' }}">
      </div>
      <div class="form-row">
        <label class="form-label" for="subject">Subject</label>
        <input type="text" id="subject" name="subject" class="form-input"
               placeholder="e.g. RE: Rose Cottage — Search Results"
               value="{{ form_subject or '' }}">
      </div>
      <div class="form-row">
        <label class="form-label" for="body">Email Body</label>
        <textarea id="body" name="body" class="form-input"
                  placeholder="Paste the full email body text here...">{{ form_body or '' }}</textarea>
      </div>
      <button type="submit" class="submit-btn">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>
        Parse &amp; Process Email
      </button>
    </form>
  </div>

  <!-- ═══ RECENT PARSED EMAILS ══════════════════════════════ -->
  <div class="section-title">&#x1F4CB; Recent Parsed Emails</div>
  <div class="result-card">
    {% if history %}
    <table class="history-table">
      <thead>
        <tr>
          <th>Time</th>
          <th>Sender</th>
          <th>Subject</th>
          <th>Property</th>
          <th>Milestones</th>
          <th>Issues</th>
        </tr>
      </thead>
      <tbody>
        {% for h in history %}
        <tr>
          <td>{{ h.created_date }}</td>
          <td>{{ h.author }}</td>
          <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ h.subject }}</td>
          <td>
            {% if h.address %}
            <a href="/property/{{ h.slug }}" style="color:var(--blue);text-decoration:none;font-weight:600">{{ h.address }}</a>
            {% else %}—{% endif %}
          </td>
          <td>{{ h.milestone_count or 0 }}</td>
          <td>
            {% if h.is_urgent %}
            <span class="badge badge-red">URGENT</span>
            {% elif h.issue_count %}
            <span class="badge badge-amber">{{ h.issue_count }}</span>
            {% else %}—{% endif %}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <div class="empty-state">
      &#x1F4EC; No emails have been parsed yet. Try a sample above or paste your own.
    </div>
    {% endif %}
  </div>

</div>

<script>
const SAMPLES = {{ samples | tojson }};

function loadSample(sampleId) {
  const sample = SAMPLES.find(s => s.id === sampleId);
  if (!sample) return;
  document.getElementById('sender').value = sample.sender;
  document.getElementById('subject').value = sample.subject;
  document.getElementById('body').value = sample.body;
  document.getElementById('sender').scrollIntoView({behavior:'smooth',block:'center'});
  document.getElementById('sender').focus();
}
</script>
</body>
</html>"""


@app.route("/admin/email-inbox", methods=["GET"])
def admin_email_inbox():
    db = get_db()
    # Get recent email-sourced notes for history display
    history_rows = db.execute(
        """SELECT n.*, p.address, p.slug,
                  (SELECT COUNT(*) FROM notes n2
                   WHERE n2.property_id = n.property_id AND n2.source = 'email'
                   AND n2.created_date = n.created_date) as milestone_count
           FROM notes n
           LEFT JOIN properties p ON p.id = n.property_id
           WHERE n.source = 'email'
           ORDER BY n.created_date DESC LIMIT 20"""
    ).fetchall()
    history = []
    for r in history_rows:
        h = dict(r)
        # Extract subject from note text
        lines = h.get("note_text", "").split("\n")
        h["subject"] = ""
        h["issue_count"] = 0
        for line in lines:
            if line.startswith("Subject:"):
                h["subject"] = line[8:].strip()
            if line.startswith("Issue:"):
                h["issue_count"] += 1
        history.append(h)
    db.close()

    return render_template_string(
        ADMIN_EMAIL_INBOX_HTML,
        samples=SAMPLE_EMAILS,
        history=history,
        parse_result=None,
        form_sender="",
        form_subject="",
        form_body="",
    )


@app.route("/admin/email-inbox", methods=["POST"])
def admin_email_inbox_process():
    sender = request.form.get("sender", "").strip()
    subject = request.form.get("subject", "").strip()
    body = request.form.get("body", "").strip()

    parse_result = None
    if subject or body:
        parse_result = process_email(subject, body, sender)

        # ── Completion Engine Recalculation after email parse ──
        if parse_result and parse_result.get("matched_property"):
            recalculate_property(parse_result["matched_property"]["db_id"])

    # Get history
    db = get_db()
    history_rows = db.execute(
        """SELECT n.*, p.address, p.slug
           FROM notes n
           LEFT JOIN properties p ON p.id = n.property_id
           WHERE n.source = 'email'
           ORDER BY n.created_date DESC LIMIT 20"""
    ).fetchall()
    history = []
    for r in history_rows:
        h = dict(r)
        lines = h.get("note_text", "").split("\n")
        h["subject"] = ""
        h["issue_count"] = 0
        for line in lines:
            if line.startswith("Subject:"):
                h["subject"] = line[8:].strip()
            if line.startswith("Issue:"):
                h["issue_count"] += 1
        history.append(h)
    db.close()

    return render_template_string(
        ADMIN_EMAIL_INBOX_HTML,
        samples=SAMPLE_EMAILS,
        history=history,
        parse_result=parse_result,
        form_sender=sender,
        form_subject=subject,
        form_body=body,
    )


# ─────────────────────────────────────────────────────────────
#  COMPLETION ENGINE API
# ─────────────────────────────────────────────────────────────

@app.route("/api/completion-engine/<prop_id>")
def api_completion_engine(prop_id):
    """Return the full completion engine calculation as JSON for debugging."""
    result = calculate_completion(prop_id)
    return jsonify(result)


@app.route("/api/completion-engine/recalculate-all", methods=["POST"])
def api_recalculate_all():
    """Recalculate and persist completion engine data for all properties."""
    results = recalculate_all()
    summary = {
        "total": len(results),
        "on_track": sum(1 for r in results if r.get("status") == "on-track"),
        "at_risk": sum(1 for r in results if r.get("status") == "at-risk"),
        "stalled": sum(1 for r in results if r.get("status") == "stalled"),
        "errors": sum(1 for r in results if "error" in r),
    }
    return jsonify({"status": "ok", "summary": summary})


# ─────────────────────────────────────────────────────────────
#  EATOC CRM LIVE PROPERTY CARDS
# ─────────────────────────────────────────────────────────────

EATOC_API_URL = "https://etoc-crm-production-688d.up.railway.app/api/nuvu/properties"
NUVU_API_KEY = os.environ.get("NUVU_API_KEY", "dbe-nuvu-2026")


def fetch_eatoc_properties():
    """Fetch live sales progression data from the EATOC CRM API."""
    try:
        resp = requests.get(
            EATOC_API_URL,
            headers={"x-api-key": NUVU_API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json(), None
    except requests.RequestException as e:
        return [], str(e)


def build_ai_panel(prop):
    """Generate AI insight panel from property milestone state."""
    done = []
    todo = []
    human = []

    if prop.get("offer_accepted"):
        done.append("Offer accepted and recorded")
    else:
        todo.append("Chase offer acceptance confirmation")

    if prop.get("memo_sent"):
        done.append("Memorandum of sale sent to all parties")
    else:
        todo.append("Send memorandum of sale")

    if prop.get("buyer_solicitor"):
        done.append("Buyer solicitor instructed")
    else:
        todo.append("Confirm buyer solicitor instruction")

    if prop.get("vendor_solicitor"):
        done.append("Vendor solicitor instructed")
    else:
        todo.append("Confirm vendor solicitor instruction")

    if prop.get("exchange_date"):
        done.append("Exchange completed")
    elif prop.get("memo_sent"):
        todo.append("Progress to exchange — chase solicitors for contract pack")

    if prop.get("completion_date"):
        done.append("Completion achieved")
    elif prop.get("exchange_date"):
        todo.append("Prepare for completion — confirm move date and key handover")

    status = (prop.get("status") or "").lower()
    if status == "problem":
        human.append("Property flagged as PROBLEM — review and resolve before progressing")
    if status == "incomplete_chain":
        human.append("Incomplete chain detected — identify and resolve chain break")
    if not prop.get("buyer_solicitor") and not prop.get("vendor_solicitor"):
        human.append("No solicitors on file — contact buyer and vendor for solicitor details")
    if not prop.get("mortgage_broker") and prop.get("sale_price"):
        human.append("No mortgage broker recorded — confirm buyer's funding position")

    return {"done": done, "todo": todo, "human": human}


CRM_CARDS_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NUVU — Live CRM Properties</title>
<link rel="icon" href="/static/logo.png">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --navy:#0f1b2d;--navy-lt:#162236;--navy-md:#1c2e4a;--navy-card:#182842;
  --lime:#c4e233;--lime-dk:#a3bf1a;
  --red:#e11d48;--amber:#f97316;--green:#16a34a;--blue:#3b82f6;--purple:#8b5cf6;
  --white:#ffffff;--off-white:#f4f6f9;
  --txt:#1e293b;--txt-mid:#475569;--txt-light:#94a3b8;
  --card-shadow:0 2px 12px rgba(0,0,0,.08);
}
html{font-size:15px;scroll-behavior:smooth}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--off-white);color:var(--txt);min-height:100vh}

/* ═══ HERO ═══ */
.hero{background:linear-gradient(135deg,var(--navy) 0%,var(--navy-md) 50%,#1a3a5c 100%);padding:40px 40px 32px;position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;top:-50%;right:-20%;width:80%;height:200%;background:radial-gradient(circle,rgba(196,226,51,.06) 0%,transparent 70%);pointer-events:none}
.hero-inner{max-width:1400px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;position:relative;z-index:1}
.hero-left{display:flex;align-items:center;gap:20px}
.hero-left img{width:52px;height:52px;border-radius:12px}
.hero-title{font-size:2rem;font-weight:900;color:var(--white);letter-spacing:8px}
.hero-sub{font-size:.72rem;color:var(--lime);text-transform:uppercase;letter-spacing:3px;font-weight:600;margin-top:4px}
.hero-stats{display:flex;gap:24px}
.hs{text-align:center;padding:12px 20px;background:rgba(255,255,255,.06);border-radius:12px;min-width:100px}
.hs-val{font-size:1.8rem;font-weight:900;color:var(--white)}
.hs-lbl{font-size:.62rem;text-transform:uppercase;letter-spacing:1.5px;color:rgba(255,255,255,.5);font-weight:600;margin-top:2px}

/* ═══ FILTERS ═══ */
.filter-bar{max-width:1400px;margin:0 auto;padding:20px 40px 8px;display:flex;gap:10px;flex-wrap:wrap}
.filter-btn{
  padding:8px 18px;border-radius:8px;border:1px solid #e2e8f0;
  background:var(--white);color:var(--txt-mid);font-size:.82rem;font-weight:600;
  cursor:pointer;transition:all .2s ease;
}
.filter-btn:hover,.filter-btn.active{background:var(--navy);color:var(--white);border-color:var(--navy)}
.filter-btn .count{margin-left:6px;font-size:.72rem;opacity:.6}

/* ═══ CARD GRID ═══ */
.card-grid{max-width:1400px;margin:0 auto;padding:24px 40px 60px;display:grid;grid-template-columns:1fr;gap:28px}

/* ═══ PROPERTY CARD ═══ */
.prop-card{background:var(--white);border-radius:16px;overflow:hidden;box-shadow:var(--card-shadow);border:1px solid #e8ecf1;transition:all .22s ease}
.prop-card:hover{box-shadow:0 8px 28px rgba(0,0,0,.1)}

/* Header */
.card-header{display:flex;align-items:flex-start;justify-content:space-between;padding:24px 28px 16px;border-bottom:1px solid #f1f5f9}
.card-address{font-size:1.3rem;font-weight:800;color:var(--txt);line-height:1.3}
.card-header-right{display:flex;align-items:center;gap:14px}
.card-price{font-size:1.15rem;font-weight:800;color:var(--navy)}
.status-badge{
  padding:5px 14px;border-radius:6px;
  font-size:.68rem;font-weight:800;letter-spacing:.8px;color:var(--white);text-transform:uppercase;
}
.badge-active{background:var(--green)}
.badge-exchanged{background:var(--blue)}
.badge-problem{background:var(--red)}
.badge-incomplete_chain{background:var(--amber)}
.badge-development{background:var(--purple)}
.badge-default{background:var(--txt-light)}

/* ═══ MILESTONE TRACKER ═══ */
.milestone-bar{display:flex;align-items:center;padding:20px 28px;gap:0;background:#fafbfc;border-bottom:1px solid #f1f5f9}
.ms-step{flex:1;display:flex;flex-direction:column;align-items:center;position:relative;z-index:1}
.ms-dot{
  width:28px;height:28px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:.7rem;font-weight:700;color:var(--white);
  border:3px solid #e2e8f0;background:var(--white);
  transition:all .3s ease;position:relative;z-index:2;
}
.ms-dot.done{background:var(--green);border-color:var(--green)}
.ms-dot.done::after{content:'✓'}
.ms-dot.current{border-color:var(--lime);background:var(--lime);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(196,226,51,.4)}50%{box-shadow:0 0 0 8px rgba(196,226,51,0)}}
.ms-label{font-size:.68rem;font-weight:600;color:var(--txt-mid);margin-top:8px;text-align:center;line-height:1.2}
.ms-label.done-label{color:var(--green);font-weight:700}
.ms-connector{flex:1;height:3px;background:#e2e8f0;margin:0 -4px;position:relative;top:-14px;z-index:0}
.ms-connector.done-conn{background:var(--green)}

/* ═══ TWO COLUMN CONTACTS ═══ */
.card-contacts{display:grid;grid-template-columns:1fr 1fr;gap:0;border-bottom:1px solid #f1f5f9}
.contact-col{padding:20px 28px}
.contact-col:first-child{border-right:1px solid #f1f5f9}
.contact-role{font-size:.62rem;text-transform:uppercase;letter-spacing:1.5px;color:var(--txt-light);font-weight:700;margin-bottom:10px}
.contact-name{font-size:.95rem;font-weight:700;color:var(--txt);margin-bottom:4px}
.contact-detail{font-size:.82rem;color:var(--txt-mid);margin-bottom:2px;display:flex;align-items:center;gap:6px}
.contact-detail a{color:var(--blue);text-decoration:none}
.contact-detail a:hover{text-decoration:underline}
.contact-solicitor{margin-top:12px;padding-top:10px;border-top:1px solid #f1f5f9}
.contact-solicitor .sol-label{font-size:.6rem;text-transform:uppercase;letter-spacing:1.2px;color:var(--txt-light);font-weight:600;margin-bottom:4px}
.contact-solicitor .sol-name{font-size:.85rem;font-weight:600;color:var(--txt)}

/* ═══ BOTTOM ROW ═══ */
.card-bottom{display:flex;flex-wrap:wrap;gap:0;border-bottom:1px solid #f1f5f9}
.bottom-item{
  flex:1;min-width:120px;padding:14px 20px;
  border-right:1px solid #f1f5f9;
  display:flex;flex-direction:column;gap:2px;
}
.bottom-item:last-child{border-right:none}
.bi-label{font-size:.58rem;text-transform:uppercase;letter-spacing:1.2px;color:var(--txt-light);font-weight:700}
.bi-value{font-size:.85rem;font-weight:600;color:var(--txt)}

/* ═══ NOTES ═══ */
.card-notes{padding:16px 28px;border-bottom:1px solid #f1f5f9}
.notes-header{font-size:.62rem;text-transform:uppercase;letter-spacing:1.5px;color:var(--txt-light);font-weight:700;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between}
.note-text{font-size:.88rem;color:var(--txt-mid);line-height:1.5;min-height:24px}
.note-text[contenteditable]{outline:none;border:1px solid transparent;border-radius:6px;padding:6px 10px;transition:border-color .2s}
.note-text[contenteditable]:focus{border-color:var(--lime);background:var(--white)}
.note-save{display:none;padding:4px 14px;border-radius:6px;border:none;background:var(--lime);color:var(--navy);font-size:.75rem;font-weight:700;cursor:pointer;margin-top:8px}
.note-save.visible{display:inline-block}

/* ═══ AI PANEL ═══ */
.ai-panel{background:var(--navy);padding:24px 28px;border-radius:0 0 16px 16px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:24px}
.ai-section h4{font-size:.65rem;text-transform:uppercase;letter-spacing:1.5px;font-weight:700;margin-bottom:10px;display:flex;align-items:center;gap:6px}
.ai-done h4{color:var(--green)}
.ai-todo h4{color:var(--lime)}
.ai-human h4{color:var(--red)}
.ai-list{list-style:none;padding:0}
.ai-list li{font-size:.8rem;color:rgba(255,255,255,.7);margin-bottom:6px;padding-left:16px;position:relative;line-height:1.4}
.ai-list li::before{content:'›';position:absolute;left:0;color:rgba(255,255,255,.3);font-weight:700}
.ai-done .ai-list li::before{color:var(--green)}
.ai-todo .ai-list li::before{color:var(--lime)}
.ai-human .ai-list li::before{color:var(--red)}
.ai-empty{font-size:.78rem;color:rgba(255,255,255,.3);font-style:italic}

/* ═══ ERROR BANNER ═══ */
.error-banner{max-width:1400px;margin:20px auto 0;padding:16px 28px;background:#fef2f2;border:1px solid #fecaca;border-radius:12px;color:var(--red);font-size:.88rem;font-weight:600}

/* ═══ EMPTY STATE ═══ */
.empty-state{max-width:1400px;margin:60px auto;text-align:center;color:var(--txt-light);font-size:1.1rem}

/* ═══ BACK LINK ═══ */
.back-link{display:inline-flex;align-items:center;gap:6px;color:var(--txt-light);text-decoration:none;font-size:.82rem;font-weight:600;padding:16px 40px 0;max-width:1400px;margin:0 auto;display:block}
.back-link:hover{color:var(--txt)}

/* ═══ RESPONSIVE ═══ */
@media(max-width:900px){
  .hero-inner{flex-direction:column;gap:20px;text-align:center}
  .hero-stats{justify-content:center}
  .card-contacts{grid-template-columns:1fr}
  .contact-col:first-child{border-right:none;border-bottom:1px solid #f1f5f9}
  .ai-panel{grid-template-columns:1fr}
  .card-grid{padding:16px}
  .milestone-bar{overflow-x:auto;padding:16px}
  .filter-bar{padding:16px}
  .card-bottom{flex-direction:column}
  .bottom-item{border-right:none;border-bottom:1px solid #f1f5f9}
  .bottom-item:last-child{border-bottom:none}
}
</style>
</head>
<body>

<!-- HERO -->
<div class="hero">
  <div class="hero-inner">
    <div class="hero-left">
      <img src="/static/logo.png" alt="NUVU">
      <div>
        <div class="hero-title">NUVU</div>
        <div class="hero-sub">Live Sales Progression — EATOC CRM</div>
      </div>
    </div>
    <div class="hero-stats">
      <div class="hs"><div class="hs-val">{{ properties|length }}</div><div class="hs-lbl">Active</div></div>
      <div class="hs"><div class="hs-val">{{ properties|selectattr('status','equalto','exchanged')|list|length }}</div><div class="hs-lbl">Exchanged</div></div>
      <div class="hs"><div class="hs-val">{{ properties|selectattr('status','equalto','problem')|list|length }}</div><div class="hs-lbl">Problems</div></div>
    </div>
  </div>
</div>

{% if error %}
<div class="error-banner">⚠ Could not fetch live data: {{ error }}</div>
{% endif %}

<!-- FILTER BAR -->
<div class="filter-bar">
  <button class="filter-btn active" data-filter="all">All <span class="count">({{ properties|length }})</span></button>
  <button class="filter-btn" data-filter="active">Active</button>
  <button class="filter-btn" data-filter="exchanged">Exchanged</button>
  <button class="filter-btn" data-filter="problem">Problem</button>
  <button class="filter-btn" data-filter="incomplete_chain">Incomplete Chain</button>
  <button class="filter-btn" data-filter="development">Development</button>
</div>

<!-- BACK LINK -->
<a href="/" class="back-link">← Back to Dashboard</a>

<!-- CARDS -->
<div class="card-grid">
{% for p in properties %}
<div class="prop-card" data-status="{{ p.status|lower }}">

  <!-- HEADER -->
  <div class="card-header">
    <div>
      <div class="card-address">{{ p.property_address or 'Unknown Address' }}</div>
    </div>
    <div class="card-header-right">
      {% if p.sale_price %}
      <div class="card-price">£{{ "{:,.0f}".format(p.sale_price|float) }}</div>
      {% endif %}
      {% set st = p.status|lower if p.status else 'active' %}
      <span class="status-badge badge-{{ st if st in ['active','exchanged','problem','incomplete_chain','development'] else 'default' }}">{{ p.status or 'Active' }}</span>
    </div>
  </div>

  <!-- MILESTONE TRACKER -->
  {% set milestones = [
    ('Offer Accepted', p.offer_accepted),
    ('Memo Sent', p.memo_sent),
    ('Searches', p.buyer_solicitor),
    ('Survey', p.surveyor),
    ('Exchange', p.exchange_date),
    ('Completion', p.completion_date)
  ] %}
  <div class="milestone-bar">
    {% for label, val in milestones %}
      {% if not loop.first %}
        <div class="ms-connector {{ 'done-conn' if val else '' }}"></div>
      {% endif %}
      {% set is_done = val is not none and val != '' and val %}
      {% set is_current = not is_done and (loop.index0 == 0 or milestones[loop.index0-1][1]) %}
      <div class="ms-step">
        <div class="ms-dot {{ 'done' if is_done else ('current' if is_current else '') }}">
          {% if not is_done and not is_current %}
            <span style="color:var(--txt-light);font-size:.6rem">{{ loop.index }}</span>
          {% endif %}
        </div>
        <div class="ms-label {{ 'done-label' if is_done else '' }}">{{ label }}</div>
      </div>
    {% endfor %}
  </div>

  <!-- TWO COLUMN CONTACTS -->
  <div class="card-contacts">
    <div class="contact-col">
      <div class="contact-role">Buyer</div>
      <div class="contact-name">{{ p.buyer_name or '—' }}</div>
      {% if p.buyer_phone %}<div class="contact-detail">📞 <a href="tel:{{ p.buyer_phone }}">{{ p.buyer_phone }}</a></div>{% endif %}
      {% if p.buyer_email %}<div class="contact-detail">✉ <a href="mailto:{{ p.buyer_email }}">{{ p.buyer_email }}</a></div>{% endif %}
      {% if p.buyer_solicitor %}
      <div class="contact-solicitor">
        <div class="sol-label">Solicitor</div>
        <div class="sol-name">{{ p.buyer_solicitor }}</div>
      </div>
      {% endif %}
    </div>
    <div class="contact-col">
      <div class="contact-role">Vendor</div>
      <div class="contact-name">{{ p.vendor_name or '—' }}</div>
      {% if p.vendor_phone %}<div class="contact-detail">📞 <a href="tel:{{ p.vendor_phone }}">{{ p.vendor_phone }}</a></div>{% endif %}
      {% if p.vendor_email %}<div class="contact-detail">✉ <a href="mailto:{{ p.vendor_email }}">{{ p.vendor_email }}</a></div>{% endif %}
      {% if p.vendor_solicitor %}
      <div class="contact-solicitor">
        <div class="sol-label">Solicitor</div>
        <div class="sol-name">{{ p.vendor_solicitor }}</div>
      </div>
      {% endif %}
    </div>
  </div>

  <!-- BOTTOM ROW -->
  <div class="card-bottom">
    <div class="bottom-item">
      <span class="bi-label">Mortgage Broker</span>
      <span class="bi-value">{{ p.mortgage_broker or '—' }}</span>
    </div>
    <div class="bottom-item">
      <span class="bi-label">Surveyor</span>
      <span class="bi-value">{{ p.surveyor or '—' }}</span>
    </div>
    <div class="bottom-item">
      <span class="bi-label">Sewage</span>
      <span class="bi-value">{{ p.sewage_type or '—' }}</span>
    </div>
    <div class="bottom-item">
      <span class="bi-label">Staff</span>
      <span class="bi-value">{{ p.staff_initials or '—' }}</span>
    </div>
    <div class="bottom-item">
      <span class="bi-label">Fee</span>
      <span class="bi-value">{% if p.fee %}£{{ "{:,.0f}".format(p.fee|float) }}{% else %}—{% endif %}</span>
    </div>
  </div>

  <!-- NOTES -->
  <div class="card-notes">
    <div class="notes-header">
      <span>Progression Notes</span>
      <button class="note-save" id="save-{{ p.id }}" onclick="saveNote({{ p.id }})">Save</button>
    </div>
    <div class="note-text"
         contenteditable="true"
         data-id="{{ p.id }}"
         onfocus="this.parentNode.querySelector('.note-save').classList.add('visible')"
         onblur="setTimeout(()=>this.parentNode.querySelector('.note-save').classList.remove('visible'),200)">{{ p.nuvu_notes or p.notes or 'No notes yet — click to add.' }}</div>
  </div>

  <!-- AI PANEL -->
  {% set ai = ai_panels[p.id|string] if ai_panels else {} %}
  <div class="ai-panel">
    <div class="ai-section ai-done">
      <h4>✓ What We've Done</h4>
      {% if ai.done %}
      <ul class="ai-list">{% for item in ai.done %}<li>{{ item }}</li>{% endfor %}</ul>
      {% else %}<div class="ai-empty">No actions recorded yet</div>{% endif %}
    </div>
    <div class="ai-section ai-todo">
      <h4>→ What To Do Next</h4>
      {% if ai.todo %}
      <ul class="ai-list">{% for item in ai.todo %}<li>{{ item }}</li>{% endfor %}</ul>
      {% else %}<div class="ai-empty">All caught up</div>{% endif %}
    </div>
    <div class="ai-section ai-human">
      <h4>⚑ Needs Human Input</h4>
      {% if ai.human %}
      <ul class="ai-list">{% for item in ai.human %}<li>{{ item }}</li>{% endfor %}</ul>
      {% else %}<div class="ai-empty">No issues flagged</div>{% endif %}
    </div>
  </div>

</div>
{% endfor %}

{% if not properties %}
<div class="empty-state">No properties found. Check the API connection.</div>
{% endif %}
</div>

<script>
// ── Filter buttons ──
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const f = btn.dataset.filter;
    document.querySelectorAll('.prop-card').forEach(card => {
      card.style.display = (f === 'all' || card.dataset.status === f) ? '' : 'none';
    });
  });
});

// ── Save note (PATCH to EATOC CRM) ──
function saveNote(propId) {
  const el = document.querySelector(`.note-text[data-id="${propId}"]`);
  if (!el) return;
  const text = el.innerText.trim();
  fetch(`/api/crm/notes/${propId}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({nuvu_notes: text})
  })
  .then(r => r.json())
  .then(d => {
    const btn = document.getElementById(`save-${propId}`);
    if (btn) { btn.textContent = '✓ Saved'; setTimeout(() => btn.textContent = 'Save', 2000); }
  })
  .catch(e => alert('Save failed: ' + e));
}
</script>
</body>
</html>"""


@app.route("/crm")
def crm_cards():
    """Live property cards pulled from the EATOC CRM API."""
    properties, error = fetch_eatoc_properties()

    # Build AI insight panels for each property
    ai_panels = {}
    for p in properties:
        pid = str(p.get("id", ""))
        ai_panels[pid] = build_ai_panel(p)

    return render_template_string(
        CRM_CARDS_HTML,
        properties=properties,
        ai_panels=ai_panels,
        error=error,
    )


@app.route("/api/crm/notes/<int:prop_id>", methods=["POST"])
def save_crm_note(prop_id):
    """Save a NUVU note back to the EATOC CRM."""
    data = request.get_json(force=True)
    nuvu_notes = data.get("nuvu_notes", "")
    try:
        resp = requests.patch(
            f"{EATOC_API_URL}/{prop_id}",
            headers={"x-api-key": NUVU_API_KEY, "Content-Type": "application/json"},
            json={"nuvu_notes": nuvu_notes},
            timeout=10,
        )
        resp.raise_for_status()
        return jsonify({"ok": True})
    except requests.RequestException as e:
        return jsonify({"ok": False, "error": str(e)}), 502


# ─────────────────────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("  NUVU Sales Progression Dashboard")
    print("  " + "\u2500" * 34)
    print("  http://127.0.0.1:5000")
    print()
    app.run(debug=True, port=5000)
