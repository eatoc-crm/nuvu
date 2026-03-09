"""
NUVU Sales Progression Dashboard
==================================
A complete Flask-based sales progression tracker for NUVU Estate Agency.

Run:
    pip install flask
    python app.py

Then open http://127.0.0.1:5000 in your browser.
"""

from flask import Flask, render_template_string, render_template, jsonify, request
import json
import os
import requests as http_requests
from datetime import datetime

app = Flask(__name__, static_folder="static", template_folder="templates")


# ─────────────────────────────────────────────────────────────
#  PROPERTY DATA — Sales Progression Pipeline
# ─────────────────────────────────────────────────────────────

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
]


# ─────────────────────────────────────────────────────────────
#  SECTIONS — define the 4 dashboard sections
# ─────────────────────────────────────────────────────────────

PROPS_BY_ID = {p["id"]: p for p in PROPERTIES}

SECTIONS = [
    {
        "id": "needs-action",
        "icon": "\U0001F6A8",
        "title": "Needs Action",
        "subtitle": "3 transactions requiring immediate attention",
        "avg_progress": 55,
        "avg_color": "#e88a3a",
        "border_class": "stalled-banner",
        "visible_ids": ["stalled", "at-risk-1", "at-risk-2"],
        "hidden_ids": ["kirk-thore", "temple-sowerby"],
        "extra_count": 0,
    },
    {
        "id": "this-week",
        "icon": "\U0001F4C5",
        "title": "This Week",
        "subtitle": "5 expected completions",
        "avg_progress": 82,
        "avg_color": "#27ae60",
        "border_class": "green-banner",
        "visible_ids": ["on-track-1", "on-track-2", "on-track-3"],
        "hidden_ids": ["langwathby", "clifton"],
        "extra_count": 0,
    },
    {
        "id": "this-month",
        "icon": "\U0001F4CA",
        "title": "This Month",
        "subtitle": "12 expected completions",
        "avg_progress": 68,
        "avg_color": "#27ae60",
        "border_class": "blue-banner",
        "visible_ids": ["lazonby", "melmerby", "glassonby"],
        "hidden_ids": [],
        "extra_count": 9,
    },
    {
        "id": "this-quarter",
        "icon": "\U0001F4C8",
        "title": "This Quarter",
        "subtitle": "28 expected completions",
        "avg_progress": 45,
        "avg_color": "#e88a3a",
        "border_class": "amber-banner",
        "visible_ids": ["skirwith", "blencarn", "newbiggin"],
        "hidden_ids": [],
        "extra_count": 25,
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

@app.route("/")
def dashboard():
    sections_data = []
    for sec in SECTIONS:
        s = dict(sec)
        s["visible"] = [PROPS_BY_ID[pid] for pid in sec["visible_ids"] if pid in PROPS_BY_ID]
        s["hidden"] = [PROPS_BY_ID[pid] for pid in sec["hidden_ids"] if pid in PROPS_BY_ID]
        sections_data.append(s)

    return render_template_string(
        DASHBOARD_HTML,
        sections=sections_data,
        stats=STATS,
        pipeline=PIPELINE,
        properties_json=json.dumps(PROPERTIES),
    )


@app.route("/api/property/<prop_id>")
def api_property(prop_id):
    prop = PROPS_BY_ID.get(prop_id)
    if not prop:
        return jsonify({"error": "Not found"}), 404
    return jsonify(prop)


# ─────────────────────────────────────────────────────────────
#  TEMPLATE
# ─────────────────────────────────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NUVU Sales Progression</title>
<link rel="icon" href="/static/logo.png">
<style>
/* ═══ RESET ═══════════════════════════════════════════════ */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --navy:#0f1b2d;--navy-lt:#162236;--navy-md:#1c2e4a;--navy-card:#182842;
  --lime:#c4e233;--lime-dk:#a3bf1a;
  --red:#e25555;--red-chip:#e84545;
  --amber:#e88a3a;--amber-chip:#e8873a;
  --green:#27ae60;--green-chip:#2fa868;
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

/* NUVU badge — top right */
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

/* Stats overlay — floating rounded card over hero */
.hero-stats{
  position:absolute;bottom:24px;left:50%;transform:translateX(-50%);
  width:calc(100% - 64px);max-width:1400px;
  background:#1a2332;
  border-radius:16px;
  box-shadow:0 8px 32px rgba(0,0,0,.3);
  border:1px solid rgba(255,255,255,.08);
  display:flex;justify-content:center;padding:0;
}
.hs{
  flex:1;max-width:220px;text-align:center;padding:22px 16px;
  border-right:1px solid rgba(255,255,255,.08);
  cursor:pointer;transition:background var(--t);
}
.hs:last-child{border-right:none}
.hs:hover{background:rgba(255,255,255,.05);border-radius:4px}
.hs-val{font-size:2.1rem;font-weight:900;color:var(--white);line-height:1}
.hs-lbl{font-size:.68rem;text-transform:uppercase;letter-spacing:1.8px;color:rgba(255,255,255,.55);margin-top:6px;font-weight:600}

/* ═══ PIPELINE FORECAST ═══════════════════════════════════ */
.pipeline-section{
  background:var(--navy);padding:36px 40px 40px;cursor:pointer;
  transition:background .2s ease;
}
.pipeline-section:hover{background:#0d1826}
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
  padding:28px 0 20px;
  border-left:4px solid transparent;
  padding-left:20px;margin-left:-24px;
}
.section-banner.stalled-banner{border-left-color:var(--red)}
.section-banner.risk-banner{border-left-color:var(--amber)}
.section-banner.green-banner{border-left-color:var(--green)}
.section-banner.blue-banner{border-left-color:var(--blue)}
.section-banner.amber-banner{border-left-color:var(--amber)}
.section-banner-left h2{font-size:1.3rem;font-weight:800;color:var(--txt);display:flex;align-items:center;gap:10px}
.section-banner-left p{font-size:.88rem;color:var(--txt-light);margin-top:2px}

/* Section avg progress bar */
.section-avg{display:flex;align-items:center;gap:12px}
.avg-label{font-size:.68rem;text-transform:uppercase;letter-spacing:1px;color:var(--txt-light);font-weight:600;white-space:nowrap}
.avg-bar-wrap{display:flex;align-items:center;gap:8px}
.avg-bar{width:120px;height:8px;border-radius:4px;background:#e8ecf1;overflow:hidden}
.avg-bar-fill{height:100%;border-radius:4px;transition:width .4s ease}
.avg-pct{font-size:.85rem;font-weight:800;color:var(--txt);min-width:35px}

/* ═══ CARD GRID ═══════════════════════════════════════════ */
.card-grid{
  display:grid;grid-template-columns:repeat(3,1fr);gap:24px;
  margin-bottom:12px;
}

/* ═══ PROPERTY CARD — white, photo top ════════════════════ */
.prop-card{
  background:var(--white);border-radius:16px;overflow:hidden;
  box-shadow:var(--card-shadow);cursor:pointer;
  transition:all var(--t);border:1px solid #e8ecf1;
}
.prop-card:hover{
  transform:translateY(-4px);
  box-shadow:0 12px 32px rgba(0,0,0,.12);
}

/* photo area */
.card-photo{
  height:160px;position:relative;overflow:hidden;
  display:flex;align-items:center;justify-content:center;
}
.card-photo-bg{width:100%;height:100%;object-fit:cover}
.card-chip{
  position:absolute;top:12px;right:12px;
  padding:5px 14px;border-radius:6px;
  font-size:.68rem;font-weight:800;letter-spacing:.8px;color:var(--white);
}
.chip-stalled{background:var(--red-chip)}
.chip-at-risk{background:var(--amber-chip)}
.chip-on-track{background:var(--green-chip)}

/* card body */
.card-body{padding:18px 22px 20px}
.card-name{font-size:1.05rem;font-weight:700;color:var(--txt);margin-bottom:14px}

/* progress + duration row */
.card-progress-row{display:flex;align-items:center;gap:16px;margin-bottom:16px}

/* SVG progress ring */
.ring-wrap{position:relative;width:64px;height:64px;flex-shrink:0}
.ring-wrap svg{width:64px;height:64px;transform:rotate(-90deg)}
.ring-bg{fill:none;stroke:#e2e8f0;stroke-width:5}
.ring-fg{fill:none;stroke-width:5;stroke-linecap:round}
.ring-fg.clr-stalled{stroke:var(--red)}
.ring-fg.clr-at-risk{stroke:var(--amber)}
.ring-fg.clr-on-track{stroke:var(--lime)}
.ring-pct{
  position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  font-size:.8rem;font-weight:800;color:var(--txt);
}

/* duration block */
.card-duration .dur-label{font-size:.65rem;text-transform:uppercase;letter-spacing:1.2px;color:var(--txt-light);font-weight:600}
.card-duration .dur-val{font-size:1.3rem;font-weight:800;color:var(--txt);line-height:1.2}
.card-duration .dur-target{font-size:.78rem;color:var(--txt-light)}

/* checklist */
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

/* extra summary (for larger counts) */
.extra-summary{
  display:flex;align-items:center;justify-content:space-between;
  padding:16px 20px;margin-top:16px;
  background:var(--white);border:1px solid #e8ecf1;border-radius:12px;
  color:var(--txt-mid);font-size:.88rem;
}
.extra-note{font-size:.78rem;color:var(--txt-light);font-style:italic}

/* ═══ MODAL ═══════════════════════════════════════════════ */
.modal-overlay{
  display:none;position:fixed;inset:0;
  background:rgba(0,0,0,.55);backdrop-filter:blur(4px);
  z-index:2000;align-items:center;justify-content:center;padding:20px;
}
.modal-overlay.open{display:flex}
.modal{
  background:var(--white);border-radius:18px;
  width:100%;max-width:620px;max-height:85vh;overflow-y:auto;
  box-shadow:0 30px 80px rgba(0,0,0,.3);animation:modalIn .25s ease;
  color:var(--txt);
}
@keyframes modalIn{from{opacity:0;transform:translateY(20px) scale(.97)}to{opacity:1;transform:translateY(0) scale(1)}}
.modal::-webkit-scrollbar{width:5px}
.modal::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:3px}

/* modal header */
.m-hdr{padding:18px 22px 0;display:flex;justify-content:space-between;align-items:flex-start}
.m-hdr h2{font-size:1.15rem;font-weight:800}
.m-hdr .m-loc{font-size:.8rem;color:var(--txt-light);margin-top:2px}
.m-price{font-size:1.2rem;font-weight:800;color:var(--green)}
.m-close{
  width:34px;height:34px;border-radius:50%;
  background:#f1f5f9;border:1px solid #e2e8f0;
  color:var(--txt-mid);font-size:1rem;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  transition:all var(--t);margin-left:10px;flex-shrink:0;
}
.m-close:hover{background:var(--red);color:#fff;border-color:var(--red)}

/* progress bar */
.m-prog{padding:12px 22px 0}
.m-prog-bar{width:100%;height:6px;border-radius:3px;background:#e8ecf1;overflow:hidden}
.m-prog-fill{height:100%;border-radius:4px;transition:width .4s ease}
.m-prog-fill.clr-stalled{background:var(--red)}
.m-prog-fill.clr-at-risk{background:var(--amber)}
.m-prog-fill.clr-on-track{background:var(--green)}
.m-prog-labels{display:flex;justify-content:space-between;font-size:.65rem;color:var(--txt-light);margin-top:4px}

/* body */
.m-body{padding:10px 22px 0}
.m-div{border:none;border-top:1px solid #e8ecf1;margin:10px 0}

/* alert */
.m-alert{padding:10px 14px;border-radius:8px;margin-bottom:10px;font-size:.82rem;line-height:1.45;display:flex;gap:8px;align-items:flex-start}
.m-alert svg{flex-shrink:0;margin-top:2px}
.m-alert-red{background:#fef2f2;color:#b91c1c;border:1px solid #fecaca}
.m-alert-amber{background:#fffbeb;color:#92400e;border:1px solid #fde68a}
.m-alert-green{background:#f0fdf4;color:#166534;border:1px solid #bbf7d0}

/* next action */
.m-next{background:#f8fafc;border:1px solid #e8ecf1;border-radius:8px;padding:10px 14px;margin-bottom:10px}
.m-next-lbl{font-size:.65rem;text-transform:uppercase;letter-spacing:1px;color:var(--green);font-weight:700;margin-bottom:3px}
.m-next-txt{font-size:.82rem;color:var(--txt);line-height:1.45}

/* action buttons */
.m-actions{display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap}
.m-btn{flex:1;min-width:100px;padding:9px 12px;border-radius:8px;font-size:.78rem;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px;transition:all var(--t);border:none}
.m-btn svg{width:15px;height:15px}
.m-btn-call{background:var(--lime);color:var(--navy)}
.m-btn-call:hover{background:var(--lime-dk)}
.m-btn-done{background:var(--green);color:#fff}
.m-btn-done:hover{background:#219a52}
.m-btn-outline{background:transparent;color:var(--txt);border:1px solid #d1d5db}
.m-btn-outline:hover{border-color:var(--green);color:var(--green)}

/* milestones */
.m-ms h3{font-size:.82rem;font-weight:700;margin-bottom:6px;display:flex;align-items:center;gap:8px}
.ms-list{display:flex;flex-direction:column}
.ms-item{display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid #f1f5f9;font-size:.78rem}
.ms-item:last-child{border-bottom:none}
.ms-ic{width:18px;height:18px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:.6rem}
.ms-ic.done{background:var(--green);color:#fff}
.ms-ic.pending{background:#f1f5f9;border:2px solid #cbd5e1;color:transparent}
.ms-ic.na{background:#f1f5f9;color:var(--txt-light);font-size:.55rem;font-weight:700}
.ms-lb{color:var(--txt)}
.ms-lb.done-lb{color:var(--txt-light);text-decoration:line-through}

/* expandable details */
.m-det-toggle{
  width:100%;background:#f8fafc;border:1px solid #e8ecf1;
  border-radius:8px;padding:10px 14px;margin-bottom:4px;
  color:var(--txt);font-size:.82rem;font-weight:600;cursor:pointer;
  display:flex;align-items:center;justify-content:space-between;transition:all var(--t);
}
.m-det-toggle:hover{border-color:var(--green)}
.m-det-toggle svg{transition:transform var(--t)}
.m-det-toggle.expanded svg{transform:rotate(180deg)}
.m-det-panel{max-height:0;overflow:hidden;transition:max-height .35s ease}
.m-det-panel.expanded{max-height:650px}
.m-det-inner{padding:14px 0 4px}
.det-grid{display:grid;grid-template-columns:1fr 1fr;gap:4px 14px}
.d-r{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #f1f5f9;font-size:.75rem}
.d-r:last-child{border-bottom:none}
.d-l{color:var(--txt-light)}
.d-v{font-weight:600;color:var(--txt);text-align:right}
.d-full{grid-column:1/-1;padding:10px 0 2px}
.d-full-l{font-size:.7rem;text-transform:uppercase;letter-spacing:1px;color:var(--txt-light);margin-bottom:3px}
.d-full-v{font-size:.82rem;color:var(--txt);line-height:1.5}

.m-footer{padding:6px 22px 16px}

/* ═══ ANALYTICS MODAL ════════════════════════════════════ */
.analytics-chart{
  height:200px;background:linear-gradient(135deg,var(--navy-lt),var(--navy-md));
  border-radius:12px;display:flex;align-items:flex-end;justify-content:center;
  gap:20px;padding:24px 32px;margin-bottom:16px;
}
.analytics-chart .bar{
  width:40px;border-radius:6px 6px 0 0;background:var(--lime);opacity:.8;
  transition:opacity .2s;position:relative;
}
.analytics-chart .bar:hover{opacity:1}
.analytics-chart .bar span{
  position:absolute;top:-20px;left:50%;transform:translateX(-50%);
  font-size:.65rem;color:var(--lime);font-weight:700;white-space:nowrap;
}
.analytics-coming{text-align:center;color:var(--txt-light);font-size:.88rem;margin:12px 0 16px;font-style:italic}
.analytics-rows{display:flex;flex-direction:column;gap:8px}
.anal-row{
  display:flex;justify-content:space-between;align-items:center;
  padding:10px 14px;background:#f8fafc;border-radius:8px;border:1px solid #e8ecf1;
}
.anal-row-label{font-size:.85rem;font-weight:600;color:var(--txt)}
.anal-row-value{font-size:.82rem;color:var(--txt-mid)}

/* ═══ RESPONSIVE ══════════════════════════════════════════ */
@media(max-width:960px){.card-grid{grid-template-columns:repeat(2,1fr)}.pipeline-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:640px){
  .hero{height:320px}
  .hero-badge{top:16px;right:16px;padding:12px 18px}
  .hero-badge img{width:36px;height:36px}
  .hero-badge-text h1{font-size:1.3rem}
  .hs{padding:14px 10px}.hs-val{font-size:1.4rem}
  .pipeline-section{padding:24px 20px}
  .pipeline-grid,.card-grid{grid-template-columns:1fr}
  .content{padding:0 16px 40px}
  .section-banner{flex-direction:column;align-items:flex-start;gap:8px}
  .section-avg{margin-top:4px}
  .modal{border-radius:14px}
  .m-hdr,.m-body,.m-prog,.m-footer{padding-left:16px;padding-right:16px}
  .det-grid{grid-template-columns:1fr}
}
</style>
</head>
<body>

{# ═══ PROPERTY CARD MACRO ═══════════════════════════════ #}
{% macro prop_card(p) %}
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
        <span class="ring-pct">{{ p.progress }}%</span>
      </div>
      <div class="card-duration">
        <div class="dur-label">Duration</div>
        <div class="dur-val">{{ p.duration_days }} days</div>
        <div class="dur-target">Target: {{ p.target_days }} days</div>
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
    <div class="hs" id="stat-active"><div class="hs-val">{{ stats.active }}</div><div class="hs-lbl">Active</div></div>
    <div class="hs" id="stat-on-track"><div class="hs-val">{{ stats.on_track }}</div><div class="hs-lbl">On Track</div></div>
    <div class="hs" id="stat-at-risk"><div class="hs-val">{{ stats.at_risk }}</div><div class="hs-lbl">At Risk</div></div>
    <div class="hs" id="stat-action"><div class="hs-val">{{ stats.action }}</div><div class="hs-lbl">Action</div></div>
    <div class="hs" id="stat-avg-days"><div class="hs-val">{{ stats.avg_days }}</div><div class="hs-lbl">Avg Days</div></div>
    <div class="hs" id="stat-pipeline"><div class="hs-val">&pound;{{ "%.1f" | format(stats.pipeline / 1000000) }}M</div><div class="hs-lbl">Pipeline</div></div>
  </div>
</div>

<!-- ═══ PIPELINE FORECAST (clickable) ═══════════════════ -->
<div class="pipeline-section" id="pipelineSection">
  <div class="pipeline-header">
    <div>
      <div class="pipeline-title">&#x1F4CA; Pipeline Forecast</div>
      <div class="pipeline-sub">Click to view full analytics &bull; Manager access only</div>
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

<!-- ═══ PROPERTY MODAL ══════════════════════════════════ -->
<div class="modal-overlay" id="modalOverlay">
  <div class="modal" id="modalBox">
    <div class="m-hdr">
      <div>
        <h2 id="mAddr"></h2>
        <div class="m-loc" id="mLoc"></div>
      </div>
      <div style="display:flex;align-items:flex-start;gap:8px">
        <div class="m-price" id="mPrice"></div>
        <button class="m-close" id="mCloseBtn">&times;</button>
      </div>
    </div>

    <div class="m-prog">
      <div class="m-prog-bar"><div class="m-prog-fill" id="mProgFill"></div></div>
      <div class="m-prog-labels"><span>Offer Accepted</span><span id="mProgPct"></span><span>Completion</span></div>
    </div>

    <div class="m-body">
      <hr class="m-div">
      <div id="mAlertBox" class="m-alert" style="display:none">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <span id="mAlertTxt"></span>
      </div>
      <div class="m-next">
        <div class="m-next-lbl">Next Action</div>
        <div class="m-next-txt" id="mNextAction"></div>
      </div>
      <div class="m-actions">
        <button class="m-btn m-btn-call" id="mBtnCall">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6A19.79 19.79 0 012.12 4.18 2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z"/></svg>
          <span id="mCallLbl">Call Buyer</span>
        </button>
        <button class="m-btn m-btn-done" id="mBtnDone">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
          Mark Done
        </button>
        <button class="m-btn m-btn-outline" id="mBtnEmail">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
          Email
        </button>
      </div>
      <hr class="m-div">
      <div class="m-ms">
        <h3>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>
          Milestones
        </h3>
        <div class="ms-list" id="mMsList"></div>
      </div>
      <hr class="m-div">
      <button class="m-det-toggle" id="mDetToggle">
        Full Details
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
      </button>
      <div class="m-det-panel" id="mDetPanel">
        <div class="m-det-inner">
          <div class="det-grid" id="mDetGrid"></div>
          <div class="d-full" id="mChain"></div>
        </div>
      </div>
    </div>
    <div class="m-footer"></div>
  </div>
</div>

<!-- ═══ ANALYTICS MODAL ═════════════════════════════════ -->
<div class="modal-overlay" id="analyticsOverlay">
  <div class="modal" style="max-width:700px">
    <div class="m-hdr">
      <div>
        <h2>Pipeline Analytics</h2>
        <div class="m-loc">Full analytics dashboard</div>
      </div>
      <button class="m-close" id="analyticsCloseBtn">&times;</button>
    </div>
    <div class="m-body" style="padding-bottom:20px">
      <hr class="m-div">
      <div class="analytics-chart">
        <div class="bar" style="height:30%"><span>Oct</span></div>
        <div class="bar" style="height:45%"><span>Nov</span></div>
        <div class="bar" style="height:60%"><span>Dec</span></div>
        <div class="bar" style="height:75%"><span>Jan</span></div>
        <div class="bar" style="height:95%;background:var(--lime);opacity:1"><span>Feb</span></div>
        <div class="bar" style="height:55%;opacity:.4"><span>Mar</span></div>
        <div class="bar" style="height:40%;opacity:.3"><span>Apr</span></div>
      </div>
      <div class="analytics-coming">Full analytics coming soon</div>
      <div class="analytics-rows">
        <div class="anal-row">
          <span class="anal-row-label">This Week</span>
          <span class="anal-row-value">5 completions &bull; &pound;1.2M</span>
        </div>
        <div class="anal-row">
          <span class="anal-row-label">This Month</span>
          <span class="anal-row-value">12 completions &bull; &pound;2.9M</span>
        </div>
        <div class="anal-row">
          <span class="anal-row-label">This Quarter</span>
          <span class="anal-row-value">28 completions &bull; &pound;6.8M</span>
        </div>
        <div class="anal-row">
          <span class="anal-row-label">Average Days to Completion</span>
          <span class="anal-row-value">14.2 days</span>
        </div>
        <div class="anal-row">
          <span class="anal-row-label">Target Performance</span>
          <span class="anal-row-value" style="color:var(--green);font-weight:700">15% ahead</span>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ═══ JAVASCRIPT — all getElementById, zero inline onclick ═ -->
<script>
(function(){
  "use strict";

  var PROPS = {{ properties_json|safe }};
  var currentProp = null;

  /* ── DOM refs ─────────────────────────────────────── */
  var overlay   = document.getElementById("modalOverlay");
  var modalBox  = document.getElementById("modalBox");
  var closeBtn  = document.getElementById("mCloseBtn");
  var mAddr     = document.getElementById("mAddr");
  var mLoc      = document.getElementById("mLoc");
  var mPrice    = document.getElementById("mPrice");
  var mProgFill = document.getElementById("mProgFill");
  var mProgPct  = document.getElementById("mProgPct");
  var mAlertBox = document.getElementById("mAlertBox");
  var mAlertTxt = document.getElementById("mAlertTxt");
  var mNextAction = document.getElementById("mNextAction");
  var mCallLbl  = document.getElementById("mCallLbl");
  var mBtnCall  = document.getElementById("mBtnCall");
  var mBtnDone  = document.getElementById("mBtnDone");
  var mBtnEmail = document.getElementById("mBtnEmail");
  var mMsList   = document.getElementById("mMsList");
  var mDetToggle = document.getElementById("mDetToggle");
  var mDetPanel  = document.getElementById("mDetPanel");
  var mDetGrid   = document.getElementById("mDetGrid");
  var mChain     = document.getElementById("mChain");

  function fmt(d){
    if(!d) return "\u2014";
    var dt=new Date(d);
    return dt.toLocaleDateString("en-GB",{day:"numeric",month:"short",year:"numeric"});
  }
  function price(n){ return "\u00a3"+n.toLocaleString(); }
  function fillCls(s){ return s==="stalled"?"clr-stalled":s==="at-risk"?"clr-at-risk":"clr-on-track"; }
  function alertCls(s){ return s==="stalled"?"m-alert-red":s==="at-risk"?"m-alert-amber":"m-alert-green"; }

  /* ── open modal ───────────────────────────────────── */
  function openModal(id){
    var p=null;
    for(var i=0;i<PROPS.length;i++){if(PROPS[i].id===id){p=PROPS[i];break;}}
    if(!p)return;
    currentProp=p;

    mAddr.textContent=p.address;
    mLoc.textContent=p.location;
    mPrice.textContent=price(p.price);

    mProgFill.style.width=p.progress+"%";
    mProgFill.className="m-prog-fill "+fillCls(p.status);
    mProgPct.textContent=p.progress+"% complete";

    if(p.alert){
      mAlertBox.style.display="flex";
      mAlertBox.className="m-alert "+alertCls(p.status);
      mAlertTxt.textContent=p.alert;
    }else{
      mAlertBox.style.display="none";
    }

    mNextAction.textContent=p.next_action;
    mCallLbl.textContent="Call "+p.buyer.split(" ").pop();

    var h="";
    for(var m=0;m<p.milestones.length;m++){
      var ms=p.milestones[m];
      var ic,tx,lc;
      if(ms.done===true){ic="ms-ic done";tx="\u2713";lc="ms-lb done-lb";}
      else if(ms.done===null){ic="ms-ic na";tx="N/A";lc="ms-lb";}
      else{ic="ms-ic pending";tx="";lc="ms-lb";}
      h+='<div class="ms-item"><span class="'+ic+'">'+tx+'</span><span class="'+lc+'">'+ms.label+'</span></div>';
    }
    mMsList.innerHTML=h;

    var rows=[
      ["Buyer",p.buyer],["Buyer Phone",p.buyer_phone],
      ["Buyer Solicitor",p.buyer_solicitor],["Buyer Sol. Phone",p.buyer_sol_phone],
      ["Seller Solicitor",p.seller_solicitor],["Seller Sol. Phone",p.seller_sol_phone],
      ["Offer Accepted",fmt(p.offer_date)],["Memo Sent",fmt(p.memo_sent)],
      ["Searches Ordered",fmt(p.searches_ordered)],["Searches Received",fmt(p.searches_received)],
      ["Enquiries Raised",fmt(p.enquiries_raised)],["Enquiries Answered",fmt(p.enquiries_answered)],
      ["Mortgage Offered",fmt(p.mortgage_offered)],["Survey Booked",fmt(p.survey_booked)],
      ["Survey Complete",fmt(p.survey_complete)],["Exchange Target",fmt(p.exchange_target)],
      ["Completion Target",fmt(p.completion_target)],["Duration",p.duration_days+" of "+p.target_days+" days"]
    ];
    var dh="";
    for(var r=0;r<rows.length;r++){
      dh+='<div class="d-r"><span class="d-l">'+rows[r][0]+'</span><span class="d-v">'+rows[r][1]+'</span></div>';
    }
    mDetGrid.innerHTML=dh;
    mChain.innerHTML='<div class="d-full-l">Chain Information</div><div class="d-full-v">'+p.chain+'</div>';

    mDetPanel.classList.remove("expanded");
    mDetToggle.classList.remove("expanded");

    overlay.classList.add("open");
    document.body.style.overflow="hidden";
  }

  function closeModal(){
    overlay.classList.remove("open");
    document.body.style.overflow="";
    currentProp=null;
  }

  /* ── PROPERTY MODAL — event handlers ──────────────── */
  closeBtn.onclick=function(e){e.stopPropagation();closeModal();};
  overlay.onclick=function(e){if(e.target===overlay)closeModal();};
  modalBox.onclick=function(e){e.stopPropagation();};
  document.onkeydown=function(e){
    if(e.key==="Escape"){closeModal();closeAnalytics();}
  };
  mDetToggle.onclick=function(){mDetPanel.classList.toggle("expanded");mDetToggle.classList.toggle("expanded");};
  mBtnCall.onclick=function(){if(currentProp)alert("Calling "+currentProp.buyer+" on "+currentProp.buyer_phone);};
  mBtnDone.onclick=function(){if(currentProp)alert("Marked done for "+currentProp.address+".\n\nAction: "+currentProp.next_action);};
  mBtnEmail.onclick=function(){if(currentProp)alert("Opening email for "+currentProp.address+" progression.");};

  /* ── CARD CLICK HANDLERS ──────────────────────────── */
  for(var i=0;i<PROPS.length;i++){
    (function(pid){
      var card=document.getElementById("card-"+pid);
      if(card){card.onclick=function(){openModal(pid);};}
    })(PROPS[i].id);
  }

  /* ── SHOW MORE TOGGLE HANDLERS ────────────────────── */
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

  /* ── ANALYTICS MODAL ──────────────────────────────── */
  var analyticsOverlay=document.getElementById("analyticsOverlay");
  var analyticsCloseBtn=document.getElementById("analyticsCloseBtn");
  var pipelineSection=document.getElementById("pipelineSection");

  function closeAnalytics(){
    analyticsOverlay.classList.remove("open");
    document.body.style.overflow="";
  }

  pipelineSection.onclick=function(){
    analyticsOverlay.classList.add("open");
    document.body.style.overflow="hidden";
  };
  analyticsCloseBtn.onclick=function(e){e.stopPropagation();closeAnalytics();};
  analyticsOverlay.onclick=function(e){if(e.target===analyticsOverlay)closeAnalytics();};

  /* ── STATS BAR — scroll to sections ───────────────── */
  var statMap={
    "stat-active":"section-this-quarter",
    "stat-on-track":"section-this-week",
    "stat-at-risk":"section-needs-action",
    "stat-action":"section-needs-action",
    "stat-avg-days":"section-this-month",
    "stat-pipeline":"section-this-quarter"
  };
  var statKeys=Object.keys(statMap);
  for(var k=0;k<statKeys.length;k++){
    (function(statId,targetId){
      var el=document.getElementById(statId);
      if(el){
        el.onclick=function(){
          var target=document.getElementById(targetId);
          if(target)target.scrollIntoView({behavior:"smooth",block:"start"});
        };
      }
    })(statKeys[k],statMap[statKeys[k]]);
  }

})();
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────
#  LOGIN GUARD — exempt /crm routes (external EATOC integration)
# ─────────────────────────────────────────────────────────────

@app.before_request
def require_login():
    if request.path.startswith("/crm") or request.path.startswith("/api/crm/"):
        return
    # All other routes are open in this version (no login system)


# ─────────────────────────────────────────────────────────────
#  EATOC CRM LIVE PROPERTY CARDS
# ─────────────────────────────────────────────────────────────

EATOC_API_URL = "https://etoc-crm-production-688d.up.railway.app/api/nuvu/properties"
NUVU_API_KEY = os.environ.get("NUVU_API_KEY", "dbe-nuvu-2026")


def fetch_eatoc_properties():
    """Fetch live sales progression data from the EATOC CRM API."""
    try:
        resp = http_requests.get(
            EATOC_API_URL,
            headers={"x-api-key": NUVU_API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json(), None
    except http_requests.RequestException as e:
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


# ─────────────────────────────────────────────────────────────
#  LIVE CRM — map API data to DASHBOARD_HTML variable shape
# ─────────────────────────────────────────────────────────────

STATUS_MAP = {
    "active": "on-track",
    "development": "on-track",
    "problem": "at-risk",
    "incomplete_chain": "stalled",
    "exchanged": "on-track",
}
STATUS_LABELS = {"on-track": "ON TRACK", "at-risk": "AT RISK", "stalled": "STALLED"}

FALLBACK_GRADIENTS = [
    "linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%)",
    "linear-gradient(135deg,#2d3436 0%,#636e72 100%)",
    "linear-gradient(135deg,#355c7d 0%,#6c5b7b 50%,#c06c84 100%)",
    "linear-gradient(135deg,#667eea 0%,#764ba2 100%)",
    "linear-gradient(135deg,#11998e 0%,#38ef7d 100%)",
    "linear-gradient(135deg,#e0c3fc 0%,#8ec5fc 100%)",
    "linear-gradient(135deg,#89f7fe 0%,#66a6ff 100%)",
    "linear-gradient(135deg,#fbc2eb 0%,#a6c1ee 100%)",
]


def _progress_pct(r):
    """Estimate progress % from which milestone fields are populated."""
    steps = [r.get("offer_accepted"), r.get("memo_sent"),
             r.get("exchange_date"), r.get("completion_date")]
    done = sum(1 for s in steps if s)
    if r.get("status") == "exchanged":
        return 90
    return max(10, int(done / len(steps) * 80))


def _map_property(r, idx):
    """Map one API record to the exact dict shape DASHBOARD_HTML expects."""
    status = STATUS_MAP.get(r.get("status", "active"), "on-track")
    progress = _progress_pct(r)
    return {
        "id": r["id"],
        "address": r.get("property_address", "Unknown"),
        "location": (r.get("branch") or "").title(),
        "price": r.get("sale_price") or r.get("fee") or 0,
        "status": status,
        "status_label": STATUS_LABELS.get(status, "ON TRACK"),
        "progress": progress,
        "duration_days": (datetime.utcnow() - datetime.strptime(
            r["created_at"][:19], "%Y-%m-%dT%H:%M:%S")).days if r.get("created_at") else 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": bool(r.get("memo_sent"))},
            {"label": "Exchange", "done": bool(r.get("exchange_date"))},
            {"label": "Completion", "done": bool(r.get("completion_date"))},
        ],
        "milestones": [
            {"label": "Offer Accepted", "done": bool(r.get("offer_accepted"))},
            {"label": "Memorandum Sent", "done": bool(r.get("memo_sent"))},
            {"label": "Exchange", "done": bool(r.get("exchange_date"))},
            {"label": "Completion", "done": bool(r.get("completion_date"))},
        ],
        "buyer": r.get("buyer_name") or "\u2014",
        "buyer_phone": r.get("buyer_phone") or "\u2014",
        "buyer_solicitor": r.get("buyer_solicitor") or "\u2014",
        "buyer_sol_phone": "\u2014",
        "seller_solicitor": r.get("vendor_solicitor") or "\u2014",
        "seller_sol_phone": "\u2014",
        "offer_date": r.get("offer_accepted"),
        "memo_sent": r.get("memo_sent"),
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": r.get("exchange_date"),
        "completion_target": r.get("completion_date"),
        "chain": "\u2014",
        "alert": r.get("notes") if r.get("status") == "problem" else None,
        "next_action": r.get("notes") or "\u2014",
        "image_bg": FALLBACK_GRADIENTS[idx % len(FALLBACK_GRADIENTS)],
        "image_url": r.get("image_url") or "",
    }


def _build_crm_data():
    """Fetch live API data and return (properties, sections, stats, pipeline)
    matching the exact variable shapes the / route passes to DASHBOARD_HTML."""
    raw, error = fetch_eatoc_properties()
    if error:
        return None, None, None, None, error

    props = [_map_property(r, i) for i, r in enumerate(raw)]

    # Group by status — problems first, then active, then exchanged
    problems = [p for p in props if p["status"] == "at-risk"]
    stalled = [p for p in props if p["status"] == "stalled"]
    on_track = [p for p in props if p["status"] == "on-track"]

    def _sec(sid, icon, title, border, items):
        visible = items[:3]
        hidden = items[3:]
        avg = int(sum(p["progress"] for p in items) / len(items)) if items else 0
        clr = "#e25555" if border == "stalled-banner" else "#e88a3a" if border == "amber-banner" else "#27ae60"
        return {
            "id": sid, "icon": icon, "title": title,
            "subtitle": f"{len(items)} transactions",
            "avg_progress": avg, "avg_color": clr, "border_class": border,
            "visible_ids": [], "hidden_ids": [],
            "visible": visible, "hidden": hidden,
            "extra_count": 0,
        }

    sections = []
    if problems or stalled:
        needs = problems + stalled
        sections.append(_sec("needs-action", "\U0001F6A8", "Needs Action",
                             "stalled-banner", needs))
    if on_track:
        sections.append(_sec("this-week", "\U0001F4C5", "Active Pipeline",
                             "green-banner", on_track))

    # Stats — same keys as STATS dict used by /
    total = len(props)
    pipeline_val = sum(p["price"] for p in props if p["price"])
    stats = {
        "active": total,
        "on_track": sum(1 for r in raw if r.get("status") == "exchanged"),
        "at_risk": sum(1 for r in raw if r.get("status") == "problem"),
        "action": sum(1 for r in raw if r.get("status") == "incomplete_chain"),
        "avg_days": 0,
        "pipeline": pipeline_val,
    }

    # Pipeline — same keys as PIPELINE dict used by /
    pipeline = {
        "this_week":    {"count": stats["on_track"], "value": pipeline_val, "confidence": 95},
        "this_month":   {"count": stats["active"], "value": pipeline_val, "confidence": 80},
        "this_quarter": {"count": total, "value": pipeline_val, "confidence": 70},
    }

    return props, sections, stats, pipeline, None


@app.route("/crm")
def crm_dashboard():
    """Render DASHBOARD_HTML with live EATOC data — identical layout to /."""
    props, sections, stats, pipeline, error = _build_crm_data()
    if error:
        return f"<h2>Error fetching live data</h2><pre>{error}</pre>", 500

    return render_template_string(
        DASHBOARD_HTML,
        sections=sections,
        stats=stats,
        pipeline=pipeline,
        properties_json=json.dumps(props),
    )


@app.route("/api/crm/notes/<prop_id>", methods=["POST"])
def save_crm_note(prop_id):
    """Save a NUVU note back to the EATOC CRM."""
    data = request.get_json(force=True)
    nuvu_notes = data.get("nuvu_notes", "")
    try:
        resp = http_requests.patch(
            f"{EATOC_API_URL}/{prop_id}",
            headers={"x-api-key": NUVU_API_KEY, "Content-Type": "application/json"},
            json={"nuvu_notes": nuvu_notes},
            timeout=10,
        )
        resp.raise_for_status()
        return jsonify({"ok": True})
    except http_requests.RequestException as e:
        return jsonify({"error": str(e)}), 502


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
