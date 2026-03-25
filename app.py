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
from db_supabase import fetch_sales_progression, fetch_pipeline_data, fetch_sales_pipeline, fetch_property_images, supabase as sb

app = Flask(__name__, static_folder="static", template_folder="templates")


# ─────────────────────────────────────────────────────────────
#  HARDCODED SAMPLE DATA REMOVED — now using live Supabase queries
# ─────────────────────────────────────────────────────────────

_REMOVED_PROPERTIES = [
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
        ],
        "activity": [
            {"date": "9 Mar 2026 · 14:22", "text": "Chased Harper & Lane by phone — no answer, left voicemail"},
            {"date": "4 Mar 2026 · 09:15", "text": "Vendor solicitor confirmed title pack sent 3 weeks ago"},
            {"date": "25 Feb 2026 · 16:40", "text": "Buyer mortgage broker says application stalled — awaiting valuation"},
            {"date": "18 Feb 2026 · 11:03", "text": "Emailed Harper & Lane again requesting update on enquiries"}
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
        ],
        "activity": [
            {"date": "8 Mar 2026 · 10:35", "text": "Survey flagged damp in west gable wall — awaiting contractor quote"},
            {"date": "2 Mar 2026 · 15:48", "text": "Buyer requested \u00a312,000 reduction following survey findings"},
            {"date": "22 Feb 2026 · 09:12", "text": "Called sellers to discuss — they want to see contractor report first"},
            {"date": "14 Feb 2026 · 13:27", "text": "Sellers relocating to France, need resolution this week or buyer may walk"}
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
        ],
        "activity": [
            {"date": "7 Mar 2026 · 16:10", "text": "Local authority searches delayed \u2014 Eden DC backlog estimated 4 weeks"},
            {"date": "28 Feb 2026 · 11:33", "text": "Chased Oglethorpe Sturton to book survey — awaiting buyer availability"},
            {"date": "19 Feb 2026 · 14:55", "text": "Chain above has lost their buyer \u2014 monitoring situation closely"}
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
        ],
        "activity": [
            {"date": "7 Mar 2026 · 16:10", "text": "No survey booked after 52 days \u2014 escalated to branch manager"},
            {"date": "28 Feb 2026 · 11:33", "text": "Called Mr Henderson directly — confirmed still interested but busy with work"},
            {"date": "19 Feb 2026 · 14:55", "text": "Buyer solicitor not responding to chaser calls \u2014 sent formal letter"}
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
        ],
        "activity": [
            {"date": "6 Mar 2026 · 11:42", "text": "Mortgage valuation came in \u00a315,000 below asking price"},
            {"date": "1 Mar 2026 · 09:58", "text": "Lender may reduce offer \u2014 discussing with buyer's broker"},
            {"date": "23 Feb 2026 · 15:30", "text": "Buyer willing to bridge \u00a35,000 if vendor meets halfway"},
            {"date": "16 Feb 2026 · 10:15", "text": "Vendor considering \u2014 awaiting response by Friday"}
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
        ],
        "activity": [
            {"date": "6 Mar 2026 · 11:42", "text": "Mortgage offer received, all parties notified"},
            {"date": "1 Mar 2026 · 09:58", "text": "Searches came back clean, no issues"},
            {"date": "23 Feb 2026 · 15:30", "text": "Completion date provisionally agreed \u2014 7th March"},
            {"date": "16 Feb 2026 · 10:15", "text": "Confirm exchange date with both solicitors \u2014 target 21 Feb"}
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
        ],
        "activity": [
            {"date": "5 Mar 2026 · 15:18", "text": "Memorandum of sale issued to all parties"},
            {"date": "27 Feb 2026 · 10:45", "text": "Mr Atkinson confirmed as cash buyer \u2014 no mortgage required"},
            {"date": "20 Feb 2026 · 14:22", "text": "Enquiries raised by buyer solicitor \u2014 14 questions outstanding"},
            {"date": "12 Feb 2026 · 09:33", "text": "Chase Bendles for contract approval"}
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
        ],
        "activity": [
            {"date": "8 Mar 2026 · 14:30", "text": "Searches came back clean, no issues flagged"},
            {"date": "1 Mar 2026 · 11:15", "text": "Survey completed \u2014 no significant defects found"},
            {"date": "22 Feb 2026 · 16:48", "text": "Chase Burnetts to raise enquiries now survey is back"}
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
        ],
        "activity": [
            {"date": "7 Mar 2026 · 09:25", "text": "Exchange expected this week \u2014 both sides confirmed ready"},
            {"date": "28 Feb 2026 · 14:52", "text": "Completion date agreed \u2014 14th February"},
            {"date": "21 Feb 2026 · 11:05", "text": "Buyers confirmed they want to complete by Valentine's Day"},
            {"date": "13 Feb 2026 · 16:38", "text": "Final check with Burnetts on completion statement"}
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
        ],
        "activity": [
            {"date": "10 Mar 2026 · 11:15", "text": "Final contract review underway with both solicitors"},
            {"date": "4 Mar 2026 · 09:47", "text": "Miss Armstrong relocating from Manchester \u2014 removal firm booked"},
            {"date": "26 Feb 2026 · 15:30", "text": "Chase Harper & Lane for exchange date confirmation"}
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
        ],
        "activity": [
            {"date": "6 Mar 2026 · 16:05", "text": "Enquiries answered \u2014 all parties satisfied"},
            {"date": "27 Feb 2026 · 11:22", "text": "Chase mortgage offer \u2014 valuation was last week"},
            {"date": "20 Feb 2026 · 09:40", "text": "Mitchells' Lancaster sale exchanged \u2014 chain clear below"},
            {"date": "11 Feb 2026 · 14:55", "text": "Vendor confirmed annexe ready for move-in"}
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
        ],
        "activity": [
            {"date": "5 Mar 2026 · 09:33", "text": "Searches received \u2014 clean, no issues"},
            {"date": "26 Feb 2026 · 14:18", "text": "Survey complete \u2014 minor pointing work noted, not material"},
            {"date": "18 Feb 2026 · 11:50", "text": "Bendles to raise enquiries this week now searches are back"}
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
        ],
        "activity": [
            {"date": "5 Mar 2026 · 09:33", "text": "Enquiries raised \u2014 chasing seller solicitor for answers"},
            {"date": "26 Feb 2026 · 14:18", "text": "Mortgage application submitted by Scotts"},
            {"date": "18 Feb 2026 · 11:50", "text": "Vendor retiring to Spain \u2014 flexible on completion date"}
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
        ],
        "activity": [
            {"date": "9 Mar 2026 · 15:42", "text": "Survey booked for next week with local surveyor"},
            {"date": "2 Mar 2026 · 10:28", "text": "Awaiting search results from Eden DC"},
            {"date": "23 Feb 2026 · 14:05", "text": "Vendor wants completion by Easter \u2014 timeline tight but achievable"}
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
        ],
        "activity": [
            {"date": "8 Mar 2026 · 11:18", "text": "Memorandum of sale issued to all parties"},
            {"date": "1 Mar 2026 · 15:45", "text": "Searches ordered with Eden DC \u2014 expect 3-4 week turnaround"},
            {"date": "24 Feb 2026 · 09:22", "text": "Miss Thompson's Newcastle flat sale progressing well"}
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
        ],
        "activity": [
            {"date": "10 Mar 2026 · 14:38", "text": "Mr Jackson confirmed as cash buyer from London \u2014 no chain"},
            {"date": "5 Mar 2026 · 11:22", "text": "Survey scheduled for this week"},
            {"date": "25 Feb 2026 · 15:05", "text": "Chasing search results from Eden DC"},
            {"date": "15 Feb 2026 · 09:48", "text": "Vendor retiring \u2014 no upward chain, flexible on dates"}
        ]
    },
]


# ─────────────────────────────────────────────────────────────
#  SECTIONS — define the 4 dashboard sections
# ─────────────────────────────────────────────────────────────

PROPS_BY_ID = {p["id"]: p for p in _REMOVED_PROPERTIES}

_REMOVED_SECTIONS = [
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

_REMOVED_PIPELINE = {
    "this_week":    {"count": 5,  "value": 1200000, "confidence": 95},
    "this_month":   {"count": 12, "value": 2900000, "confidence": 80},
    "this_quarter": {"count": 28, "value": 6800000, "confidence": 70},
}

_REMOVED_STATS = {
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

def _normalize_addr(addr):
    """Normalize address for fuzzy matching between tables."""
    return " ".join(addr.lower().replace(",", " ").replace(".", " ").split())


def _match_pipeline(prog_addr, pipe_lookup, pipe_norm_keys):
    """Find matching pipeline record for a progression address."""
    norm = _normalize_addr(prog_addr)
    # Exact match
    if norm in pipe_lookup:
        return pipe_lookup[norm]
    # Substring: progression addr contained in pipeline addr or vice versa
    for key in pipe_norm_keys:
        if norm in key or key in norm:
            return pipe_lookup[key]
    # First-word match (e.g. "Greyber" vs "The Farmhouse  Grayber")
    words = norm.split()
    first = words[0] if words else ""
    if len(first) > 3:
        for key in pipe_norm_keys:
            if first in key:
                return pipe_lookup[key]
    # Try second word if first is a number (e.g. "14 howard park")
    if len(words) > 1 and words[0].isdigit():
        fragment = " ".join(words[:2])
        for key in pipe_norm_keys:
            if fragment in key:
                return pipe_lookup[key]
    return None


def _build_live_dashboard_data():
    """Query Supabase and build PROPERTIES, SECTIONS, PIPELINE, STATS for the dashboard.

    Starts from sales_pipeline (source of truth) and joins sales_progression
    for milestone/status detail. Only properties in sales_pipeline appear.
    """
    from datetime import date as _date

    # 1. Fetch all three tables
    pipe_rows = fetch_sales_pipeline()
    prog_rows = fetch_sales_progression()  # all rows, no status filter
    img_rows = fetch_property_images()

    # 1b. Build image lookup — keyed by alto ref AND normalized address
    _img_by_ref = {}
    _img_by_addr = {}
    for row in img_rows:
        # Resolve best URL: image_url first, then photo_urls[1] (skip index 0)
        url = (row.get("image_url") or "").strip() or None
        if not url:
            urls = row.get("photo_urls") or []
            if isinstance(urls, list) and len(urls) > 1:
                url = (urls[1] or "").strip() or None
        if not url:
            continue
        ref = (row.get("ref") or "").strip()
        if ref:
            _img_by_ref[ref] = url
        addr = _normalize_addr(row.get("address") or "")
        if addr:
            _img_by_addr[addr] = url

    def _resolve_image(pipe_row):
        """Find the best image URL for a pipeline property."""
        ref = (pipe_row.get("alto_ref") or "").strip()
        if ref and ref in _img_by_ref:
            return _img_by_ref[ref]
        addr = _normalize_addr(pipe_row.get("property_address") or "")
        return _img_by_addr.get(addr, "")

    # 2. Build progression lookup by normalized address
    prog_lookup = {}
    for pr in prog_rows:
        key = _normalize_addr(pr.get("property_address", ""))
        prog_lookup[key] = pr
    prog_norm_keys = list(prog_lookup.keys())

    today = _date.today()

    # Map pipeline status strings to progression-style statuses
    PIPE_STATUS_MAP = {
        "Under Offer (SSTC)": "active",
        "Under Offer": "active",
        "Exchanged": "exchanged",
    }

    # 3. Build property list — iterate over pipeline, join progression
    properties = []
    for i, pipe in enumerate(pipe_rows):
        addr = pipe.get("property_address", "")

        # Find matching progression row
        prog = _match_pipeline(addr, prog_lookup, prog_norm_keys)

        # Status: from pipeline only
        raw_status = PIPE_STATUS_MAP.get(pipe.get("status", ""), "active")

        # Price from pipeline.current_price
        price = float(pipe.get("current_price") or 0)

        # Duration = today - pipeline.date_agreed
        duration = 0
        date_agreed_str = pipe.get("date_agreed")
        if date_agreed_str:
            try:
                agreed = datetime.strptime(str(date_agreed_str), "%Y-%m-%d").date()
                duration = (today - agreed).days
            except Exception:
                pass

        # est_completion from pipeline
        est_comp_str = pipe.get("est_completion")
        est_comp_date = None
        if est_comp_str:
            try:
                est_comp_date = datetime.strptime(str(est_comp_str), "%Y-%m-%d").date()
            except Exception:
                pass

        status = STATUS_MAP.get(raw_status, "on-track")
        progress = _progress_from_record(prog) if prog else 10
        prop_id = str(prog.get("id", f"prop-{i}")) if prog else f"pipe-{i}"

        # Use progression fields where available, fall back to pipeline
        r = prog or {}

        properties.append({
            "id": prop_id,
            "address": addr or "Unknown",
            "location": (r.get("branch") or "").title() or "Eden Valley",
            "price": price,
            "status": status,
            "status_label": STATUS_LABELS.get(status, "ON TRACK"),
            "progress": progress,
            "duration_days": duration,
            "target_days": 60,
            "days_since_update": 0,
            "card_checks": _card_checks_from_record(r),
            "milestones": _milestones_from_record(r),
            "buyer": r.get("buyer_name") or "\u2014",
            "buyer_phone": r.get("buyer_phone") or "\u2014",
            "buyer_solicitor": r.get("buyer_solicitor") or pipe.get("buyers_solicitor") or "\u2014",
            "buyer_sol_phone": "\u2014",
            "seller_solicitor": r.get("vendor_solicitor") or pipe.get("vendors_solicitor") or "\u2014",
            "seller_sol_phone": "\u2014",
            "offer_date": r.get("offer_accepted"),
            "memo_sent": r.get("memo_sent"),
            "searches_ordered": r.get("searches_ordered"),
            "searches_received": r.get("searches_received"),
            "enquiries_raised": r.get("enquiries_raised"),
            "enquiries_answered": r.get("enquiries_answered"),
            "mortgage_offered": r.get("mortgage_offered"),
            "survey_booked": r.get("survey_booked"),
            "survey_complete": r.get("survey_complete"),
            "exchange_target": r.get("exchange_date"),
            "completion_target": r.get("completion_date"),
            "chain": "\u2014",
            "alert": r.get("notes") if raw_status == "problem" else None,
            "next_action": r.get("notes") or "\u2014",
            "image_bg": FALLBACK_GRADIENTS[i % len(FALLBACK_GRADIENTS)],
            "image_url": _resolve_image(pipe),
            "activity": [],
            # Notes for modal display
            "notes": r.get("notes") or "",
            "nuvu_notes": r.get("nuvu_notes") or "",
            "buyer_solicitor_notes": r.get("buyer_solicitor_notes") or "",
            "seller_solicitor_notes": r.get("seller_solicitor_notes") or "",
            # Internal fields
            "_progression_id": r.get("id"),
            "_raw_status": raw_status,
            "_fee": r.get("fee"),
            "_pipe_fee": float(pipe.get("fee") or 0),
            "_staff_initials": r.get("staff_initials") or pipe.get("negotiator") or "\u2014",
            "_est_comp_date": est_comp_date.isoformat() if est_comp_date else None,
            "_date_agreed": str(date_agreed_str) if date_agreed_str else None,
            "_mortgage_broker": r.get("mortgage_broker") or "\u2014",
            "_surveyor": r.get("surveyor") or "\u2014",
            "_buyer_email": r.get("buyer_email") or "\u2014",
            "_vendor_name": r.get("vendor_name") or "\u2014",
            "_vendor_phone": r.get("vendor_phone") or "\u2014",
            "_vendor_email": r.get("vendor_email") or "\u2014",
            "_sewage_type": r.get("sewage_type") or "\u2014",
            "_invoice_status": r.get("invoice_status") or "\u2014",
            "_nuvu_notes": r.get("nuvu_notes") or "\u2014",
            "_property_type": r.get("property_type") or "\u2014",
            "_beds": r.get("beds"),
            "_baths": r.get("baths"),
        })

    # 4. Classify into sections
    needs_action = []
    sec_this_month = []
    sec_two_months = []
    sec_this_quarter = []
    sec_active_pipeline = []
    exchanged_count = 0

    for p in properties:
        raw = p["_raw_status"]

        # Exchanged: count only, not shown in sections
        if raw == "exchanged":
            exchanged_count += 1
            continue

        est = p.get("_est_comp_date")
        est_date = datetime.strptime(est, "%Y-%m-%d").date() if est else None
        days_to_comp = (est_date - today).days if est_date else None

        # Needs Action check
        is_needs_action = False
        if raw in ("problem", "incomplete_chain"):
            is_needs_action = True
        elif raw == "active" and p.get("offer_date") and not p.get("memo_sent"):
            if p.get("_date_agreed"):
                try:
                    agreed = datetime.strptime(p["_date_agreed"], "%Y-%m-%d").date()
                    if (today - agreed).days > 7:
                        is_needs_action = True
                except Exception:
                    pass

        if is_needs_action:
            needs_action.append(p)
        elif raw in ("active", "development") and days_to_comp is not None and days_to_comp <= 30:
            sec_this_month.append(p)
        elif raw in ("active", "development") and days_to_comp is not None and days_to_comp <= 60:
            sec_two_months.append(p)
        elif raw in ("active", "development") and days_to_comp is not None and days_to_comp <= 90:
            sec_this_quarter.append(p)
        else:
            sec_active_pipeline.append(p)

    # 5. Build section dicts
    def _make_section(sid, icon, title, subtitle, border, items):
        visible = items[:3]
        hidden = items[3:]
        avg = int(sum(p["progress"] for p in items) / len(items)) if items else 0
        color = "#e25555" if border == "stalled-banner" else "#e88a3a" if border == "amber-banner" else "#27ae60"
        return {
            "id": sid, "icon": icon, "title": title, "subtitle": subtitle,
            "avg_progress": avg, "avg_color": color, "border_class": border,
            "visible_ids": [], "hidden_ids": [],
            "visible": visible, "hidden": hidden,
            "extra_count": 0,
        }

    sections = []
    if needs_action:
        sections.append(_make_section(
            "needs-action", "\U0001F6A8", "Needs Action",
            f"{len(needs_action)} transactions requiring attention", "stalled-banner", needs_action))
    if sec_this_month:
        sections.append(_make_section(
            "this-month", "\U0001F4C5", "This Month",
            f"{len(sec_this_month)} completing within 30 days", "green-banner", sec_this_month))
    if sec_two_months:
        sections.append(_make_section(
            "two-months", "\U0001F4CA", "Two Months",
            f"{len(sec_two_months)} completing in 31\u201360 days", "blue-banner", sec_two_months))
    if sec_this_quarter:
        sections.append(_make_section(
            "this-quarter", "\U0001F4C8", "This Quarter",
            f"{len(sec_this_quarter)} completing in 61\u201390 days", "amber-banner", sec_this_quarter))
    if sec_active_pipeline:
        sections.append(_make_section(
            "active-pipeline", "\U0001F3E0", "Active Pipeline",
            f"{len(sec_active_pipeline)} active transactions", "blue-banner", sec_active_pipeline))

    # 6. Stats
    active_props = [p for p in properties if p["_raw_status"] == "active"]
    active_count = len(active_props)
    on_track_count = sum(
        1 for p in active_props
        if p.get("_est_comp_date")
        and (datetime.strptime(p["_est_comp_date"], "%Y-%m-%d").date() - today).days > 30
    )
    at_risk_count = sum(1 for p in properties if p["_raw_status"] == "problem")
    action_count = len(needs_action)
    # All non-completed, non-exchanged properties for pipeline totals
    pipeline_props = [p for p in properties if p["_raw_status"] not in ("exchanged",)]
    property_pipeline = sum(p["price"] for p in pipeline_props if p["price"])
    fee_pipeline = sum(p["_pipe_fee"] for p in pipeline_props if p["_pipe_fee"])

    stats = {
        "active": active_count,
        "on_track": on_track_count,
        "at_risk": at_risk_count,
        "action": action_count,
        "exchanged": exchanged_count,
        "fee_pipeline": fee_pipeline,
        "property_pipeline": property_pipeline,
    }

    # 7. Pipeline forecast (using section counts)
    pipeline = {
        "this_week": {"count": len(sec_this_month), "value": sum(p["price"] for p in sec_this_month),
                      "fee": sum(p["_pipe_fee"] for p in sec_this_month), "confidence": 90},
        "this_month": {"count": len(sec_two_months), "value": sum(p["price"] for p in sec_two_months),
                       "fee": sum(p["_pipe_fee"] for p in sec_two_months), "confidence": 75},
        "this_quarter": {"count": len(sec_this_quarter) + len(sec_active_pipeline),
                         "value": property_pipeline,
                         "fee": fee_pipeline, "confidence": 60},
    }

    return properties, sections, stats, pipeline


@app.route("/")
def dashboard():
    try:
        properties, sections, stats, pipeline = _build_live_dashboard_data()
    except Exception as e:
        # Fallback: show error
        return f"<h2>Error loading live data</h2><pre>{e}</pre>", 500

    return render_template_string(
        DASHBOARD_HTML,
        sections=sections,
        stats=stats,
        pipeline=pipeline,
        properties_json=json.dumps(properties, default=str),
    )


@app.route("/api/property/<prop_id>")
def api_property(prop_id):
    try:
        properties, _, _, _ = _build_live_dashboard_data()
        props_by_id = {p["id"]: p for p in properties}
        prop = props_by_id.get(prop_id)
        if not prop:
            return jsonify({"error": "Not found"}), 404
        return jsonify(prop)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
.ms-lb{color:var(--txt);flex:1}
.ms-lb.done-lb{color:var(--txt-light);text-decoration:line-through}
.ms-date{font-size:.7rem;color:var(--txt-light);margin-left:auto;white-space:nowrap}
.ms-edit-btn{background:none;border:1px solid #d1d5db;border-radius:5px;padding:2px 8px;font-size:.65rem;color:var(--txt-mid);cursor:pointer;transition:all var(--t);flex-shrink:0}
.ms-edit-btn:hover{border-color:var(--green);color:var(--green)}
.ms-edit-form{display:flex;align-items:center;gap:6px;margin-left:auto;flex-shrink:0}
.ms-edit-form input[type=date]{font-size:.72rem;padding:2px 6px;border:1px solid #d1d5db;border-radius:5px;color:var(--txt)}
.ms-edit-form button{padding:2px 8px;border-radius:5px;font-size:.65rem;font-weight:600;cursor:pointer;border:none}
.ms-save-btn{background:var(--green);color:#fff}
.ms-cancel-btn{background:#f1f5f9;color:var(--txt-mid)}
.ms-pending-lb{color:var(--txt-light);font-style:italic}

/* note editor */
.note-block{background:#f8fafc;border:1px solid #e8ecf1;border-radius:8px;padding:10px 14px;margin-bottom:8px}
.note-block-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.note-block-lbl{font-size:.68rem;text-transform:uppercase;letter-spacing:.8px;color:var(--txt-light);font-weight:600}
.note-edit-btn{background:none;border:1px solid #d1d5db;border-radius:5px;padding:2px 10px;font-size:.65rem;color:var(--txt-mid);cursor:pointer;transition:all var(--t)}
.note-edit-btn:hover{border-color:var(--green);color:var(--green)}
.note-block-txt{font-size:.82rem;line-height:1.5;color:var(--txt);white-space:pre-wrap}
.note-block-txt.empty{color:var(--txt-light);font-style:italic}
.note-textarea{width:100%;min-height:60px;font-size:.82rem;font-family:inherit;line-height:1.5;border:1px solid #d1d5db;border-radius:6px;padding:8px 10px;resize:vertical;color:var(--txt)}
.note-textarea:focus{outline:none;border-color:var(--green)}
.note-actions{display:flex;gap:6px;margin-top:6px}
.note-save-btn{background:var(--green);color:#fff;border:none;border-radius:5px;padding:4px 14px;font-size:.72rem;font-weight:600;cursor:pointer}
.note-cancel-btn{background:#f1f5f9;color:var(--txt-mid);border:none;border-radius:5px;padding:4px 14px;font-size:.72rem;cursor:pointer}

/* activity notes */
.act-item{background:#f8fafc;border:1px solid #e8ecf1;border-radius:8px;padding:8px 12px;margin-bottom:6px;font-size:.8rem;line-height:1.45;color:var(--txt)}
.act-idx{font-size:.65rem;text-transform:uppercase;letter-spacing:1px;color:var(--txt-light);font-weight:600}

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
  .search-wrap{padding:10px 16px}
  .search-input{font-size:.95rem;padding:12px 14px 12px 48px}
}

/* ── Search bar ─────────────────────────────────────────── */
.search-wrap{
  position:sticky;top:0;z-index:90;
  background:var(--navy);
  padding:12px 40px;
  border-bottom:1px solid rgba(255,255,255,.08);
}
.search-input{
  width:100%;box-sizing:border-box;
  padding:14px 16px 14px 48px;
  font-size:1rem;font-family:inherit;
  background:var(--navy-lt);color:#fff;
  border:1px solid rgba(255,255,255,.12);border-radius:10px;
  outline:none;transition:border var(--t),box-shadow var(--t);
}
.search-input::placeholder{color:var(--txt-light)}
.search-input:focus{border-color:var(--lime);box-shadow:0 0 0 3px rgba(196,226,51,.15)}
.search-icon{
  position:absolute;left:14px;top:50%;transform:translateY(-50%);
  pointer-events:none;color:var(--txt-light);
}
.search-no-match{
  text-align:center;padding:32px 0;color:var(--txt-light);font-style:italic;display:none;
}
</style>
</head>
<body>

{# ═══ PROPERTY CARD MACRO ═══════════════════════════════ #}
{% macro prop_card(p) %}
<div class="prop-card" id="card-{{ p.id }}">
  <div class="card-photo">
    {% if p.image_url %}<img class="card-photo-bg" src="{{ p.image_url|safe }}" alt="{{ p.address }}" style="background:{{ p.image_bg }}" onerror="this.style.display='none';this.nextElementSibling.style.display='block'"><div class="card-photo-bg" style="background:var(--navy-md);display:none"></div>{% else %}<div class="card-photo-bg" style="background:var(--navy-md)"></div>{% endif %}
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
    <div class="hs" id="stat-exchanged"><div class="hs-val">{{ stats.exchanged }}</div><div class="hs-lbl">Exchanged</div></div>
    <div class="hs" id="stat-fee-pipeline"><div class="hs-val">&pound;{{ "{:,.0f}".format(stats.fee_pipeline) }}</div><div class="hs-lbl">Fee Pipeline</div></div>
    <div class="hs" id="stat-pipeline"><div class="hs-val">&pound;{{ "%.1f" | format(stats.property_pipeline / 1000000) }}M</div><div class="hs-lbl">Property Pipeline</div></div>
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
      <div class="pipe-confidence" style="color:var(--lime);font-weight:700">Fee: &pound;{{ "{:,.0f}".format(pipeline.this_week.fee) }}</div>
      <div class="pipe-bar"><div class="pipe-bar-fill" style="width:{{ pipeline.this_week.confidence }}%"></div></div>
      <div class="pipe-confidence">{{ pipeline.this_week.confidence }}% Confidence</div>
    </div>
    <div class="pipe-card">
      <div class="pipe-period">This Month</div>
      <div class="pipe-count">{{ pipeline.this_month.count }}</div>
      <div class="pipe-value">&pound;{{ "%.1f" | format(pipeline.this_month.value / 1000000) }}M</div>
      <div class="pipe-confidence" style="color:var(--lime);font-weight:700">Fee: &pound;{{ "{:,.0f}".format(pipeline.this_month.fee) }}</div>
      <div class="pipe-bar"><div class="pipe-bar-fill" style="width:{{ pipeline.this_month.confidence }}%"></div></div>
      <div class="pipe-confidence">{{ pipeline.this_month.confidence }}% Confidence</div>
    </div>
    <div class="pipe-card">
      <div class="pipe-period">This Quarter</div>
      <div class="pipe-count">{{ pipeline.this_quarter.count }}</div>
      <div class="pipe-value">&pound;{{ "%.1f" | format(pipeline.this_quarter.value / 1000000) }}M</div>
      <div class="pipe-confidence" style="color:var(--lime);font-weight:700">Fee: &pound;{{ "{:,.0f}".format(pipeline.this_quarter.fee) }}</div>
      <div class="pipe-bar"><div class="pipe-bar-fill" style="width:{{ pipeline.this_quarter.confidence }}%"></div></div>
      <div class="pipe-confidence">{{ pipeline.this_quarter.confidence }}% Confidence</div>
    </div>
  </div>
</div>

<!-- ═══ SEARCH BAR (sticky) ════════════════════════════════ -->
<div class="search-wrap" id="searchWrap">
  <div style="position:relative;max-width:640px;margin:0 auto">
    <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    <input class="search-input" id="searchInput" type="text" placeholder="Search by address, buyer or solicitor..." autocomplete="off">
  </div>
</div>

<!-- ═══ MAIN CONTENT — 4 SECTIONS ═══════════════════════ -->
<div class="content">
<div class="search-no-match" id="searchNoMatch">No properties found</div>

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
      <div class="m-ms">
        <h3>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--txt-mid)" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          Notes &amp; Activity
        </h3>
        <div id="mActivityList"></div>
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
  function patchProgression(progId,field,value,onSuccess){
    var body={};body[field]=value;
    fetch("/api/progression/"+progId,{
      method:"PATCH",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify(body)
    }).then(function(r){return r.json();}).then(function(j){
      if(j.ok){if(onSuccess)onSuccess();}
      else{alert("Save failed: "+(j.error||"Unknown error"));}
    }).catch(function(e){alert("Network error: "+e.message);});
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
      else{ic="ms-ic pending";tx="";lc="ms-lb ms-pending-lb";}
      var dateStr=ms.date?' <span class="ms-date">'+fmt(ms.date)+'</span>':"";
      var editBtn=p._progression_id?'<button class="ms-edit-btn" data-field="'+ms.field+'" data-idx="'+m+'">Edit</button>':"";
      h+='<div class="ms-item" id="ms-row-'+m+'"><span class="'+ic+'">'+tx+'</span><span class="'+lc+'">'+ms.label+'</span>'+dateStr+editBtn+'</div>';
    }
    mMsList.innerHTML=h;

    /* milestone edit button handlers */
    var editBtns=mMsList.querySelectorAll(".ms-edit-btn");
    for(var eb=0;eb<editBtns.length;eb++){
      (function(btn){
        btn.onclick=function(e){
          e.stopPropagation();
          var field=btn.getAttribute("data-field");
          var idx=btn.getAttribute("data-idx");
          var row=document.getElementById("ms-row-"+idx);
          var ms=currentProp.milestones[idx];
          var curVal=ms.date||"";
          row.innerHTML='<span class="ms-ic pending"></span><span class="ms-lb">'+ms.label+'</span>'+
            '<div class="ms-edit-form"><input type="date" id="ms-date-'+idx+'" value="'+curVal+'">'+
            '<button class="ms-save-btn" id="ms-sv-'+idx+'">Save</button>'+
            '<button class="ms-cancel-btn" id="ms-cn-'+idx+'">Cancel</button></div>';
          document.getElementById("ms-sv-"+idx).onclick=function(ev){
            ev.stopPropagation();
            var val=document.getElementById("ms-date-"+idx).value;
            patchProgression(currentProp._progression_id,field,val,function(){
              ms.date=val||"";
              ms.done=!!val;
              openModal(currentProp.id);
            });
          };
          document.getElementById("ms-cn-"+idx).onclick=function(ev){
            ev.stopPropagation();
            openModal(currentProp.id);
          };
        };
      })(editBtns[eb]);
    }

    /* notes section */
    var noteFields=[
      {key:"notes",label:"General Notes"},
      {key:"nuvu_notes",label:"NUVU Notes"},
      {key:"buyer_solicitor_notes",label:"Buyer Solicitor Notes"},
      {key:"seller_solicitor_notes",label:"Seller Solicitor Notes"}
    ];
    var ah="";
    for(var nf=0;nf<noteFields.length;nf++){
      var n=noteFields[nf];
      var val=p[n.key]||"";
      var editBtn2=p._progression_id?'<button class="note-edit-btn" data-nkey="'+n.key+'" data-nidx="'+nf+'">Edit</button>':"";
      ah+='<div class="note-block" id="note-blk-'+nf+'">'+
        '<div class="note-block-hdr"><span class="note-block-lbl">'+n.label+'</span>'+editBtn2+'</div>'+
        '<div class="note-block-txt'+(val?'':' empty')+'" id="note-txt-'+nf+'">'+(val||'No notes yet')+'</div></div>';
    }
    if(p.activity&&p.activity.length){
      for(var a=0;a<p.activity.length;a++){
        ah+='<div class="act-item"><div class="act-idx">'+p.activity[a].date+'</div>'+p.activity[a].text+'</div>';
      }
    }
    document.getElementById("mActivityList").innerHTML=ah;

    /* note edit handlers */
    var noteBtns=document.querySelectorAll(".note-edit-btn");
    for(var nb=0;nb<noteBtns.length;nb++){
      (function(btn){
        btn.onclick=function(e){
          e.stopPropagation();
          var nkey=btn.getAttribute("data-nkey");
          var nidx=btn.getAttribute("data-nidx");
          var blk=document.getElementById("note-blk-"+nidx);
          var curVal=currentProp[nkey]||"";
          var nfObj=noteFields[nidx];
          blk.innerHTML='<div class="note-block-hdr"><span class="note-block-lbl">'+nfObj.label+'</span></div>'+
            '<textarea class="note-textarea" id="note-ta-'+nidx+'">'+curVal+'</textarea>'+
            '<div class="note-actions"><button class="note-save-btn" id="note-sv-'+nidx+'">Save</button>'+
            '<button class="note-cancel-btn" id="note-cn-'+nidx+'">Cancel</button></div>';
          document.getElementById("note-sv-"+nidx).onclick=function(ev){
            ev.stopPropagation();
            var val=document.getElementById("note-ta-"+nidx).value;
            patchProgression(currentProp._progression_id,nkey,val,function(){
              currentProp[nkey]=val;
              openModal(currentProp.id);
            });
          };
          document.getElementById("note-cn-"+nidx).onclick=function(ev){
            ev.stopPropagation();
            openModal(currentProp.id);
          };
        };
      })(noteBtns[nb]);
    }

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
  var sectionIds=["needs-action","this-month","two-months","this-quarter","active-pipeline"];
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
    "stat-active":"section-active-pipeline",
    "stat-on-track":"section-this-month",
    "stat-at-risk":"section-needs-action",
    "stat-action":"section-needs-action",
    "stat-exchanged":"section-this-month",
    "stat-fee-pipeline":"section-active-pipeline",
    "stat-pipeline":"section-active-pipeline"
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

  /* ── SEARCH — client-side filter ──────────────────────── */
  var searchInput=document.getElementById("searchInput");
  var searchNoMatch=document.getElementById("searchNoMatch");
  var allCards=document.querySelectorAll(".prop-card");
  var allSections=document.querySelectorAll(".content > div[id^='section-']");
  var allShowMoreBtns=document.querySelectorAll(".show-more-btn");
  var allShowMorePanels=document.querySelectorAll(".show-more-panel");

  function doSearch(){
    var q=searchInput.value.trim().toLowerCase();
    if(q.length>0&&q.length<2){return;}

    if(q.length<2){
      /* restore full view */
      for(var i=0;i<allCards.length;i++) allCards[i].style.display="";
      for(var i=0;i<allSections.length;i++) allSections[i].style.display="";
      for(var i=0;i<allShowMoreBtns.length;i++){allShowMoreBtns[i].style.display="";allShowMoreBtns[i].classList.remove("expanded");}
      for(var i=0;i<allShowMorePanels.length;i++){allShowMorePanels[i].style.display="";allShowMorePanels[i].classList.remove("open");}
      searchNoMatch.style.display="none";
      return;
    }

    var matchIds={};
    for(var i=0;i<PROPS.length;i++){
      var p=PROPS[i];
      var hay=(p.address||"")+" "+(p.buyer||"")+" "+(p.buyer_solicitor||"");
      if(hay.toLowerCase().indexOf(q)!==-1) matchIds[p.id]=true;
    }

    var anyVisible=false;
    for(var i=0;i<allCards.length;i++){
      var cid=allCards[i].id.replace("card-","");
      if(matchIds[cid]){allCards[i].style.display="";anyVisible=true;}
      else{allCards[i].style.display="none";}
    }

    /* hide section banners that have zero visible cards */
    for(var i=0;i<allSections.length;i++){
      var cards=allSections[i].querySelectorAll(".prop-card");
      var hasVisible=false;
      for(var j=0;j<cards.length;j++){
        if(cards[j].style.display!=="none"){hasVisible=true;break;}
      }
      allSections[i].style.display=hasVisible?"":"none";
    }

    /* hide show-more buttons and expand panels so all matches are visible */
    for(var i=0;i<allShowMoreBtns.length;i++) allShowMoreBtns[i].style.display="none";
    for(var i=0;i<allShowMorePanels.length;i++){allShowMorePanels[i].style.display="";allShowMorePanels[i].classList.add("open");}

    searchNoMatch.style.display=anyVisible?"none":"block";
  }

  searchInput.addEventListener("input",doSearch);

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
#  LIVE CRM — map API data to DASHBOARD_HTML template shape
# ─────────────────────────────────────────────────────────────

STATUS_MAP = {
    "active": "on-track",
    "exchanged": "on-track",
    "development": "on-track",
    "problem": "at-risk",
    "incomplete_chain": "stalled",
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


def _progress_from_record(r):
    """Estimate progress % from which milestone fields are populated."""
    steps = [
        r.get("offer_accepted"),
        r.get("memo_sent"),
        r.get("searches_ordered"),
        r.get("mortgage_offered"),
        r.get("enquiries_raised"),
        r.get("enquiries_answered"),
        r.get("exchange_date"),
        r.get("completion_date"),
    ]
    done = sum(1 for s in steps if s)
    if r.get("status") == "exchanged":
        return 90
    return max(10, int(done / len(steps) * 80))


def _card_checks_from_record(r):
    return [
        {"label": "Memo Sent", "done": bool(r.get("memo_sent"))},
        {"label": "Exchange", "done": bool(r.get("exchange_date"))},
        {"label": "Completion", "done": bool(r.get("completion_date"))},
    ]


def _milestones_from_record(r):
    return [
        {"label": "Offer Accepted", "field": "offer_accepted", "done": bool(r.get("offer_accepted")), "date": r.get("offer_accepted") or ""},
        {"label": "Memo Sent", "field": "memo_sent", "done": bool(r.get("memo_sent")), "date": r.get("memo_sent") or ""},
        {"label": "Searches Ordered", "field": "searches_ordered", "done": bool(r.get("searches_ordered")), "date": r.get("searches_ordered") or ""},
        {"label": "Mortgage Offer Received", "field": "mortgage_offered", "done": bool(r.get("mortgage_offered")), "date": r.get("mortgage_offered") or ""},
        {"label": "Enquiries Raised", "field": "enquiries_raised", "done": bool(r.get("enquiries_raised")), "date": r.get("enquiries_raised") or ""},
        {"label": "Enquiries Satisfied", "field": "enquiries_answered", "done": bool(r.get("enquiries_answered")), "date": r.get("enquiries_answered") or ""},
        {"label": "Exchange", "field": "exchange_date", "done": bool(r.get("exchange_date")), "date": r.get("exchange_date") or ""},
        {"label": "Completion", "field": "completion_date", "done": bool(r.get("completion_date")), "date": r.get("completion_date") or ""},
    ]


def _map_live_properties():
    """Fetch from EATOC API and map to the dict shape DASHBOARD_HTML expects."""
    raw, error = fetch_eatoc_properties()
    if error:
        return [], error
    mapped = []
    for i, r in enumerate(raw):
        status = STATUS_MAP.get(r.get("status", "active"), "on-track")
        progress = _progress_from_record(r)
        mapped.append({
            "id": r["id"],
            "address": r.get("property_address", "Unknown"),
            "location": (r.get("branch") or "").title(),
            "price": r.get("sale_price") or r.get("fee") or 0,
            "status": status,
            "status_label": STATUS_LABELS.get(status, "ON TRACK"),
            "progress": progress,
            "duration_days": (datetime.utcnow() - datetime.strptime(r["created_at"][:19], "%Y-%m-%dT%H:%M:%S")).days if r.get("created_at") else 0,
            "target_days": 60,
            "days_since_update": 0,
            "card_checks": _card_checks_from_record(r),
            "milestones": _milestones_from_record(r),
            "buyer": r.get("buyer_name") or "\u2014",
            "buyer_phone": r.get("buyer_phone") or "\u2014",
            "buyer_solicitor": r.get("buyer_solicitor") or "\u2014",
            "buyer_sol_phone": "\u2014",
            "seller_solicitor": r.get("vendor_solicitor") or "\u2014",
            "seller_sol_phone": "\u2014",
            "offer_date": r.get("offer_accepted"),
            "memo_sent": r.get("memo_sent"),
            "searches_ordered": r.get("searches_ordered"),
            "searches_received": r.get("searches_received"),
            "enquiries_raised": r.get("enquiries_raised"),
            "enquiries_answered": r.get("enquiries_answered"),
            "mortgage_offered": r.get("mortgage_offered"),
            "survey_booked": r.get("survey_booked"),
            "survey_complete": r.get("survey_complete"),
            "exchange_target": r.get("exchange_date"),
            "completion_target": r.get("completion_date"),
            "chain": "\u2014",
            "alert": r.get("notes") if r.get("status") == "problem" else None,
            "next_action": r.get("notes") or "\u2014",
            "notes": r.get("notes") or "",
            "nuvu_notes": r.get("nuvu_notes") or "",
            "buyer_solicitor_notes": r.get("buyer_solicitor_notes") or "",
            "seller_solicitor_notes": r.get("seller_solicitor_notes") or "",
            "image_bg": FALLBACK_GRADIENTS[i % len(FALLBACK_GRADIENTS)],
            "image_url": r.get("image_url") or "",
            # extra fields for detail page
            "_progression_id": r.get("id"),
            "_raw_status": r.get("status"),
            "_sewage_type": r.get("sewage_type") or "\u2014",
            "_mortgage_broker": r.get("mortgage_broker") or "\u2014",
            "_surveyor": r.get("surveyor") or "\u2014",
            "_buyer_email": r.get("buyer_email") or "\u2014",
            "_vendor_name": r.get("vendor_name") or "\u2014",
            "_vendor_phone": r.get("vendor_phone") or "\u2014",
            "_vendor_email": r.get("vendor_email") or "\u2014",
            "_nuvu_notes": r.get("nuvu_notes") or "\u2014",
            "_staff_initials": r.get("staff_initials") or "\u2014",
            "_fee": r.get("fee"),
            "_invoice_status": r.get("invoice_status") or "\u2014",
            "_beds": r.get("beds"),
            "_baths": r.get("baths"),
            "_property_type": r.get("property_type") or "\u2014",
        })
    return mapped, None


def _crm_stats(props):
    """Compute live stats from mapped properties."""
    total = len(props)
    exchanged = sum(1 for p in props if p.get("_raw_status") == "exchanged")
    problems = sum(1 for p in props if p.get("_raw_status") == "problem")
    incomplete = sum(1 for p in props if p.get("_raw_status") == "incomplete_chain")
    active = total - exchanged
    property_pipeline = sum(p["price"] for p in props if p["price"])
    fee_pipeline = sum(p.get("_fee") or 0 for p in props if p.get("_fee"))
    return {
        "active": active,
        "on_track": exchanged,
        "at_risk": problems,
        "action": incomplete,
        "exchanged": exchanged,
        "fee_pipeline": fee_pipeline,
        "property_pipeline": property_pipeline,
    }


def _crm_sections(props):
    """Group live properties into sections for the dashboard template."""
    problems = [p for p in props if p["_raw_status"] == "problem"]
    incomplete = [p for p in props if p["_raw_status"] == "incomplete_chain"]
    exchanged = [p for p in props if p["_raw_status"] == "exchanged"]
    active = [p for p in props if p["_raw_status"] in ("active", "development")]

    def _section(sid, icon, title, subtitle, border, items):
        visible = items[:3]
        hidden = items[3:]
        avg = int(sum(p["progress"] for p in items) / len(items)) if items else 0
        color = "#e25555" if border == "stalled-banner" else "#e88a3a" if border == "amber-banner" else "#27ae60"
        return {
            "id": sid, "icon": icon, "title": title, "subtitle": subtitle,
            "avg_progress": avg, "avg_color": color, "border_class": border,
            "visible_ids": [], "hidden_ids": [],
            "visible": visible, "hidden": hidden,
            "extra_count": 0,
        }

    sections = []
    if problems or incomplete:
        needs = problems + incomplete
        sections.append(_section("needs-action", "\U0001F6A8", "Needs Action",
                                 f"{len(needs)} transactions requiring attention", "stalled-banner", needs))
    if exchanged:
        sections.append(_section("exchanged", "\u2705", "Exchanged",
                                 f"{len(exchanged)} exchanged", "green-banner", exchanged))
    if active:
        sections.append(_section("active", "\U0001F4C5", "Active Pipeline",
                                 f"{len(active)} active transactions", "blue-banner", active))
    return sections


# JS snippet appended after DASHBOARD_HTML to redirect card clicks to detail page
CRM_OVERRIDE_JS = r"""
<script>
(function(){
  var base = "{{ detail_base_url }}";
  if (!base) return;
  var PROPS = {{ properties_json|safe }};
  for (var i = 0; i < PROPS.length; i++) {
    (function(pid){
      var card = document.getElementById("card-" + pid);
      if (card) {
        card.onclick = function(e) {
          e.stopPropagation();
          window.location.href = base + "/" + pid;
        };
      }
    })(PROPS[i].id);
  }

  /* Update stats bar labels for CRM view */
  var labels = {
    "stat-on-track": "Exchanged",
    "stat-at-risk": "Problems",
    "stat-action": "Inc. Chain"
  };
  for (var id in labels) {
    var el = document.getElementById(id);
    if (el) {
      var lbl = el.querySelector(".hs-lbl");
      if (lbl) lbl.textContent = labels[id];
    }
  }
})();
</script>
"""


@app.route("/crm")
def crm_dashboard():
    """Live CRM dashboard using NUVU design with real property data."""
    props, error = _map_live_properties()
    if error:
        return f"<h2>Error fetching live data</h2><pre>{error}</pre>", 500

    stats = _crm_stats(props)
    sections = _crm_sections(props)

    pipeline = {
        "this_week": {"count": stats["on_track"], "value": stats["property_pipeline"], "fee": stats["fee_pipeline"], "confidence": 90},
        "this_month": {"count": stats["active"], "value": stats["property_pipeline"], "fee": stats["fee_pipeline"], "confidence": 75},
        "this_quarter": {"count": len(props), "value": stats["property_pipeline"], "fee": stats["fee_pipeline"], "confidence": 60},
    }

    html = render_template_string(
        DASHBOARD_HTML + CRM_OVERRIDE_JS,
        sections=sections,
        stats=stats,
        pipeline=pipeline,
        properties_json=json.dumps(props),
        detail_base_url="/crm/property",
    )
    return html


@app.route("/crm/property/<prop_id>")
def crm_property_detail(prop_id):
    """Full-page detail view for a single CRM property."""
    props, error = _map_live_properties()
    if error:
        return f"<h2>Error fetching live data</h2><pre>{error}</pre>", 500

    prop = None
    for p in props:
        if p["id"] == prop_id:
            prop = p
            break
    if not prop:
        return "<h2>Property not found</h2>", 404

    return render_template_string(DETAIL_HTML, p=prop)


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
#  PATCH API — update milestone dates and notes on progression
# ─────────────────────────────────────────────────────────────

ALLOWED_PATCH_FIELDS = {
    "offer_accepted", "memo_sent", "searches_ordered", "mortgage_offered",
    "enquiries_raised", "enquiries_answered", "exchange_date", "completion_date",
    "notes", "nuvu_notes", "buyer_solicitor_notes", "seller_solicitor_notes",
}


@app.route("/api/progression/<prog_id>", methods=["PATCH"])
def patch_progression(prog_id):
    """Update one or more fields on a sales_progression row."""
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No data provided"}), 400

    updates = {}
    for key, val in data.items():
        if key in ALLOWED_PATCH_FIELDS:
            updates[key] = val if val else None

    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    try:
        sb.table("sales_progression").update(updates).eq("id", prog_id).execute()
        return jsonify({"ok": True, "updated": list(updates.keys())})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
#  INTAKE API — external CRM pushes Under Offer properties
# ─────────────────────────────────────────────────────────────

@app.route("/api/intake", methods=["POST"])
def api_intake():
    """Receive a property payload when it goes Under Offer."""
    # --- Auth ---
    expected_key = os.environ.get("NUVU_API_KEY", "dbe-nuvu-2026")
    provided_key = request.headers.get("X-NUVU-API-KEY", "")
    if not provided_key or provided_key != expected_key:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True)
    if not data or not data.get("property_address", "").strip():
        return jsonify({"error": "property_address is required"}), 400

    addr = data["property_address"].strip()
    date_agreed = data.get("date_agreed") or None
    alto_ref = (data.get("alto_ref") or "").strip() or None

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
        sb.table("sales_pipeline").upsert(
            pipeline_row, on_conflict=conflict_col
        ).execute()
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

    return jsonify({"success": True, "property": addr}), 200


# ─────────────────────────────────────────────────────────────
#  DETAIL PAGE TEMPLATE — same CSS vars / fonts as DASHBOARD
# ─────────────────────────────────────────────────────────────

DETAIL_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ p.address }} — NUVU</title>
<link rel="icon" href="/static/logo.png">
<style>
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

/* back bar */
.back-bar{background:var(--navy);padding:16px 32px;display:flex;align-items:center;gap:12px}
.back-btn{
  display:inline-flex;align-items:center;gap:8px;
  color:var(--lime);font-size:.88rem;font-weight:700;text-decoration:none;
  padding:8px 18px;border-radius:8px;border:1px solid rgba(196,226,51,.3);
  transition:all var(--t);
}
.back-btn:hover{background:rgba(196,226,51,.12);border-color:var(--lime)}

/* hero photo */
.detail-hero{position:relative;width:100%;height:320px;overflow:hidden;background:var(--navy)}
.detail-hero img{width:100%;height:100%;object-fit:cover}
.detail-hero-overlay{
  position:absolute;bottom:0;left:0;right:0;
  background:linear-gradient(transparent,rgba(15,27,45,.85));
  padding:40px 32px 24px;
}
.detail-hero-overlay h1{font-size:1.6rem;font-weight:800;color:var(--white);margin-bottom:4px}
.detail-hero-overlay .detail-loc{font-size:.88rem;color:rgba(255,255,255,.6)}
.detail-hero-overlay .detail-price{font-size:1.4rem;font-weight:900;color:var(--lime);margin-top:8px}
.detail-chip{
  position:absolute;top:20px;right:24px;
  padding:6px 16px;border-radius:6px;
  font-size:.72rem;font-weight:800;letter-spacing:.8px;color:var(--white);
}
.chip-stalled{background:var(--red-chip)}
.chip-at-risk{background:var(--amber-chip)}
.chip-on-track{background:var(--green-chip)}

/* content */
.detail-content{max-width:900px;margin:0 auto;padding:32px}

/* progress */
.detail-prog{margin-bottom:28px}
.detail-prog-bar{width:100%;height:10px;border-radius:5px;background:#e8ecf1;overflow:hidden}
.detail-prog-fill{height:100%;border-radius:5px}
.detail-prog-fill.clr-stalled{background:var(--red)}
.detail-prog-fill.clr-at-risk{background:var(--amber)}
.detail-prog-fill.clr-on-track{background:var(--green)}
.detail-prog-labels{display:flex;justify-content:space-between;font-size:.72rem;color:var(--txt-light);margin-top:6px}

/* cards */
.detail-card{
  background:var(--white);border-radius:14px;border:1px solid #e8ecf1;
  box-shadow:var(--card-shadow);padding:24px;margin-bottom:20px;
}
.detail-card h3{font-size:.92rem;font-weight:700;color:var(--txt);margin-bottom:14px;display:flex;align-items:center;gap:8px}

/* milestones */
.ms-list{display:flex;flex-direction:column}
.ms-item{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #f1f5f9;font-size:.85rem}
.ms-item:last-child{border-bottom:none}
.ms-ic{width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:.65rem}
.ms-ic.done{background:var(--green);color:#fff}
.ms-ic.pending{background:#f1f5f9;border:2px solid #cbd5e1;color:transparent}
.ms-lb{color:var(--txt);flex:1}
.ms-lb.done-lb{color:var(--txt-light);text-decoration:line-through}
.ms-pending-lb{color:var(--txt-light);font-style:italic}
.ms-date{margin-left:auto;font-size:.78rem;color:var(--txt-light);font-weight:600;white-space:nowrap}
.ms-edit-btn{background:none;border:1px solid #d1d5db;border-radius:5px;padding:2px 8px;font-size:.65rem;color:var(--txt-mid);cursor:pointer;transition:all var(--t);flex-shrink:0}
.ms-edit-btn:hover{border-color:var(--green);color:var(--green)}
.ms-edit-form{display:flex;align-items:center;gap:6px;margin-left:auto;flex-shrink:0}
.ms-edit-form input[type=date]{font-size:.72rem;padding:2px 6px;border:1px solid #d1d5db;border-radius:5px;color:var(--txt)}
.ms-edit-form button{padding:2px 8px;border-radius:5px;font-size:.65rem;font-weight:600;cursor:pointer;border:none}
.ms-save-btn{background:var(--green);color:#fff}
.ms-cancel-btn{background:#f1f5f9;color:var(--txt-mid)}
.note-block{background:#f8fafc;border:1px solid #e8ecf1;border-radius:8px;padding:10px 14px;margin-bottom:8px}
.note-block-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.note-block-lbl{font-size:.68rem;text-transform:uppercase;letter-spacing:.8px;color:var(--txt-light);font-weight:600}
.note-edit-btn{background:none;border:1px solid #d1d5db;border-radius:5px;padding:2px 10px;font-size:.65rem;color:var(--txt-mid);cursor:pointer;transition:all var(--t)}
.note-edit-btn:hover{border-color:var(--green);color:var(--green)}
.note-block-txt{font-size:.82rem;line-height:1.5;color:var(--txt);white-space:pre-wrap}
.note-block-txt.empty{color:var(--txt-light);font-style:italic}
.note-textarea{width:100%;min-height:60px;font-size:.82rem;font-family:inherit;line-height:1.5;border:1px solid #d1d5db;border-radius:6px;padding:8px 10px;resize:vertical;color:var(--txt)}
.note-textarea:focus{outline:none;border-color:var(--green)}
.note-actions{display:flex;gap:6px;margin-top:6px}
.note-save-btn{background:var(--green);color:#fff;border:none;border-radius:5px;padding:4px 14px;font-size:.72rem;font-weight:600;cursor:pointer}
.note-cancel-btn{background:#f1f5f9;color:var(--txt-mid);border:none;border-radius:5px;padding:4px 14px;font-size:.72rem;cursor:pointer}

/* alert box */
.alert-box{
  padding:14px 18px;border-radius:10px;margin-bottom:20px;
  font-size:.88rem;line-height:1.5;display:flex;gap:10px;align-items:flex-start;
}
.alert-red{background:#fef2f2;color:#b91c1c;border:1px solid #fecaca}
.alert-amber{background:#fffbeb;color:#92400e;border:1px solid #fde68a}
.alert-green{background:#f0fdf4;color:#166534;border:1px solid #bbf7d0}

/* next action */
.next-box{background:#f8fafc;border:1px solid #e8ecf1;border-radius:10px;padding:14px 18px;margin-bottom:20px}
.next-lbl{font-size:.68rem;text-transform:uppercase;letter-spacing:1.2px;color:var(--green);font-weight:700;margin-bottom:4px}
.next-txt{font-size:.88rem;color:var(--txt);line-height:1.5}

/* detail grid */
.det-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 20px}
.d-r{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f1f5f9;font-size:.85rem}
.d-r:last-child{border-bottom:none}
.d-l{color:var(--txt-light)}
.d-v{font-weight:600;color:var(--txt);text-align:right}

/* two col layout */
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:20px}

@media(max-width:700px){
  .detail-hero{height:220px}
  .detail-content{padding:20px 16px}
  .det-grid,.two-col{grid-template-columns:1fr}
  .back-bar{padding:12px 16px}
}
</style>
</head>
<body>

<div class="back-bar">
  <a class="back-btn" href="/crm">&larr; Back to Dashboard</a>
</div>

<div class="detail-hero">
  {% if p.image_url %}
  <img src="{{ p.image_url }}" alt="{{ p.address }}" style="background:{{ p.image_bg }}">
  {% else %}
  <div style="width:100%;height:100%;background:{{ p.image_bg }}"></div>
  {% endif %}
  <span class="detail-chip chip-{{ p.status }}">{{ p.status_label }}</span>
  <div class="detail-hero-overlay">
    <h1>{{ p.address }}</h1>
    <div class="detail-loc">{{ p.location }}{% if p._property_type and p._property_type != '\u2014' %} &bull; {{ p._property_type }}{% endif %}{% if p._beds %} &bull; {{ p._beds }} bed{% endif %}{% if p._baths %} &bull; {{ p._baths }} bath{% endif %}</div>
    {% if p.price %}<div class="detail-price">&pound;{{ "{:,.0f}".format(p.price) }}</div>{% endif %}
  </div>
</div>

<div class="detail-content">

  <!-- Progress bar -->
  <div class="detail-prog">
    <div class="detail-prog-bar"><div class="detail-prog-fill clr-{{ p.status }}" style="width:{{ p.progress }}%"></div></div>
    <div class="detail-prog-labels"><span>Offer Accepted</span><span>{{ p.progress }}% complete</span><span>Completion</span></div>
  </div>

  <!-- Alert -->
  {% if p.alert %}
  <div class="alert-box {% if p.status == 'stalled' %}alert-red{% elif p.status == 'at-risk' %}alert-amber{% else %}alert-green{% endif %}">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
    <span>{{ p.alert }}</span>
  </div>
  {% endif %}

  <!-- Next Action -->
  <div class="next-box">
    <div class="next-lbl">Next Action</div>
    <div class="next-txt">{{ p.next_action }}</div>
  </div>

  <div class="two-col">
    <!-- Milestones -->
    <div class="detail-card">
      <h3>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>
        Milestones
      </h3>
      <div class="ms-list">
        {% for ms in p.milestones %}
        <div class="ms-item" id="dms-row-{{ loop.index0 }}">
          <span class="ms-ic {{ 'done' if ms.done else 'pending' }}">{% if ms.done %}&#x2713;{% endif %}</span>
          <span class="ms-lb {{ 'done-lb' if ms.done else 'ms-pending-lb' }}">{{ ms.label }}</span>
          {% if ms.date %}<span class="ms-date">{{ ms.date }}</span>{% endif %}
          {% if p._progression_id %}<button class="ms-edit-btn" data-field="{{ ms.field }}" data-idx="{{ loop.index0 }}">Edit</button>{% endif %}
        </div>
        {% endfor %}
      </div>
    </div>

    <!-- Contacts & details -->
    <div class="detail-card">
      <h3>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--blue)" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        Contacts &amp; Details
      </h3>
      <div class="det-grid">
        <div class="d-r"><span class="d-l">Buyer</span><span class="d-v">{{ p.buyer }}</span></div>
        <div class="d-r"><span class="d-l">Buyer Phone</span><span class="d-v">{{ p.buyer_phone }}</span></div>
        <div class="d-r"><span class="d-l">Buyer Solicitor</span><span class="d-v">{{ p.buyer_solicitor }}</span></div>
        <div class="d-r"><span class="d-l">Vendor</span><span class="d-v">{{ p._vendor_name }}</span></div>
        <div class="d-r"><span class="d-l">Vendor Phone</span><span class="d-v">{{ p._vendor_phone }}</span></div>
        <div class="d-r"><span class="d-l">Vendor Solicitor</span><span class="d-v">{{ p.seller_solicitor }}</span></div>
        <div class="d-r"><span class="d-l">Mortgage Broker</span><span class="d-v">{{ p._mortgage_broker }}</span></div>
        <div class="d-r"><span class="d-l">Surveyor</span><span class="d-v">{{ p._surveyor }}</span></div>
        <div class="d-r"><span class="d-l">Sewage Type</span><span class="d-v">{{ p._sewage_type }}</span></div>
        <div class="d-r"><span class="d-l">Staff</span><span class="d-v">{{ p._staff_initials }}</span></div>
      </div>
    </div>
  </div>

  <!-- Dates & timeline -->
  <div class="detail-card">
    <h3>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--amber)" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
      Timeline
    </h3>
    <div class="det-grid">
      <div class="d-r"><span class="d-l">Offer Accepted</span><span class="d-v">{{ p.offer_date or '\u2014' }}</span></div>
      <div class="d-r"><span class="d-l">Memo Sent</span><span class="d-v">{{ p.memo_sent or '\u2014' }}</span></div>
      <div class="d-r"><span class="d-l">Exchange Date</span><span class="d-v">{{ p.exchange_target or '\u2014' }}</span></div>
      <div class="d-r"><span class="d-l">Completion Date</span><span class="d-v">{{ p.completion_target or '\u2014' }}</span></div>
      <div class="d-r"><span class="d-l">Fee</span><span class="d-v">&pound;{{ "{:,.2f}".format(p._fee) if p._fee else '\u2014' }}</span></div>
      <div class="d-r"><span class="d-l">Invoice Status</span><span class="d-v">{{ p._invoice_status }}</span></div>
    </div>
  </div>

  <!-- Notes -->
  <div class="detail-card">
    <h3>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--txt-mid)" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
      Notes
    </h3>
    <div id="d-notes-list">
      {% set note_fields = [("notes","General Notes"),("nuvu_notes","NUVU Notes"),("buyer_solicitor_notes","Buyer Solicitor Notes"),("seller_solicitor_notes","Seller Solicitor Notes")] %}
      {% for key, label in note_fields %}
      <div class="note-block" id="d-note-blk-{{ loop.index0 }}">
        <div class="note-block-hdr"><span class="note-block-lbl">{{ label }}</span>{% if p._progression_id %}<button class="note-edit-btn" data-nkey="{{ key }}" data-nidx="{{ loop.index0 }}">Edit</button>{% endif %}</div>
        <div class="note-block-txt{{ ' empty' if not p[key] }}" id="d-note-txt-{{ loop.index0 }}">{{ p[key] or 'No notes yet' }}</div>
      </div>
      {% endfor %}
    </div>
  </div>

</div>

<script>
(function(){
  var progId = "{{ p._progression_id or '' }}";
  if (!progId) return;

  function patchField(field, value, onSuccess) {
    var body = {}; body[field] = value;
    fetch("/api/progression/" + progId, {
      method: "PATCH",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body)
    }).then(function(r){ return r.json(); }).then(function(j){
      if (j.ok) { if (onSuccess) onSuccess(); }
      else { alert("Save failed: " + (j.error || "Unknown error")); }
    }).catch(function(e){ alert("Network error: " + e.message); });
  }

  /* milestone edit */
  var msBtns = document.querySelectorAll(".ms-edit-btn");
  for (var i = 0; i < msBtns.length; i++) {
    (function(btn){
      btn.onclick = function() {
        var field = btn.getAttribute("data-field");
        var idx = btn.getAttribute("data-idx");
        var row = document.getElementById("dms-row-" + idx);
        var label = row.querySelector(".ms-lb").textContent;
        var dateEl = row.querySelector(".ms-date");
        var curVal = dateEl ? dateEl.textContent : "";
        row.innerHTML = '<span class="ms-ic pending"></span><span class="ms-lb">' + label + '</span>' +
          '<div class="ms-edit-form"><input type="date" id="dms-date-' + idx + '" value="' + curVal + '">' +
          '<button class="ms-save-btn" id="dms-sv-' + idx + '">Save</button>' +
          '<button class="ms-cancel-btn" id="dms-cn-' + idx + '">Cancel</button></div>';
        document.getElementById("dms-sv-" + idx).onclick = function() {
          var val = document.getElementById("dms-date-" + idx).value;
          patchField(field, val, function(){ location.reload(); });
        };
        document.getElementById("dms-cn-" + idx).onclick = function() { location.reload(); };
      };
    })(msBtns[i]);
  }

  /* note edit */
  var noteBtns = document.querySelectorAll(".note-edit-btn");
  for (var n = 0; n < noteBtns.length; n++) {
    (function(btn){
      btn.onclick = function() {
        var nkey = btn.getAttribute("data-nkey");
        var nidx = btn.getAttribute("data-nidx");
        var blk = document.getElementById("d-note-blk-" + nidx);
        var txtEl = document.getElementById("d-note-txt-" + nidx);
        var curVal = txtEl.classList.contains("empty") ? "" : txtEl.textContent;
        var label = blk.querySelector(".note-block-lbl").textContent;
        blk.innerHTML = '<div class="note-block-hdr"><span class="note-block-lbl">' + label + '</span></div>' +
          '<textarea class="note-textarea" id="d-note-ta-' + nidx + '">' + curVal + '</textarea>' +
          '<div class="note-actions"><button class="note-save-btn" id="d-note-sv-' + nidx + '">Save</button>' +
          '<button class="note-cancel-btn" id="d-note-cn-' + nidx + '">Cancel</button></div>';
        document.getElementById("d-note-sv-" + nidx).onclick = function() {
          var val = document.getElementById("d-note-ta-" + nidx).value;
          patchField(nkey, val, function(){ location.reload(); });
        };
        document.getElementById("d-note-cn-" + nidx).onclick = function() { location.reload(); };
      };
    })(noteBtns[n]);
  }
})();
</script>

</body>
</html>"""


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
