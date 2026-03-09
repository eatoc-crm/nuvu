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
    {
        "id": '14-howard-park',
        "address": '14 Howard Park',
        "location": 'Penrith',
        "price": 3518.75,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 90,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": True},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": '—',
        "buyer_sol_phone": "—",
        "seller_solicitor": '—',
        "seller_sol_phone": "—",
        "offer_date": '20th Oct',
        "memo_sent": '21st Oct',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": '26th Feb',
        "completion_target": '6th Mar',
        "chain": "—",
        "alert": None,
        "next_action": 'Exchanged',
        "image_bg": 'linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34243924/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": True},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'saddle-house',
        "address": 'Saddle House',
        "location": 'Penrith',
        "price": 189000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 80,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": True},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Tilly, Bailey & Irvine law firm',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Ramsdens Solicitors LLP',
        "seller_sol_phone": "—",
        "offer_date": '20th Oct',
        "memo_sent": '23rd Oct',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": '6th March',
        "completion_target": 'March 13th Completion',
        "chain": "—",
        "alert": None,
        "next_action": '23/1 sols said almost there - waiting for septic tank permit and surveyor to draw up a plan',
        "image_bg": 'linear-gradient(135deg,#2d3436 0%,#636e72 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33788119/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": True},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'the-limes',
        "address": 'The Limes',
        "location": 'Penrith',
        "price": 545000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Birchall Blackburn',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Arnison Heelis',
        "seller_sol_phone": "—",
        "offer_date": '8th Sept',
        "memo_sent": '9th Sept',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'Aiming for 18th March',
        "chain": "—",
        "alert": None,
        "next_action": '5/1 sols asked for fee but not ready to discuss dates',
        "image_bg": 'linear-gradient(135deg,#355c7d 0%,#6c5b7b 50%,#c06c84 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34143429/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'barnfauld',
        "address": 'Barnfauld',
        "location": 'Penrith',
        "price": 347500,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 80,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": True},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Stephen Wilmot',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Burnetts Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '11th Nov',
        "memo_sent": '11th Nov',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": '27th Feb',
        "completion_target": '26th March',
        "chain": "—",
        "alert": None,
        "next_action": '31/1 DV chased - 12/1 searches back, have mortgage offer, raising enqs',
        "image_bg": 'linear-gradient(135deg,#667eea 0%,#764ba2 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34252902/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": True},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'station-house-cliburn',
        "address": 'Station House, Cliburn',
        "location": 'Penrith',
        "price": 1250000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Adam Douglas Legal LLP',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Bell Park Kerridge',
        "seller_sol_phone": "—",
        "offer_date": '15th Aug',
        "memo_sent": '19th Aug',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": '26th March',
        "chain": "—",
        "alert": None,
        "next_action": '31/1 DV Chased',
        "image_bg": 'linear-gradient(135deg,#11998e 0%,#38ef7d 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33888204/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'the-cottage-murton',
        "address": 'The Cottage, Murton',
        "location": 'Penrith',
        "price": 230000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Potter Owtram & Peck LLP',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Cartmel Shepherd',
        "seller_sol_phone": "—",
        "offer_date": '1st Nov',
        "memo_sent": '1st Nov',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'End March',
        "chain": "—",
        "alert": None,
        "next_action": '19/2 dv chased 31/1 Mortgage offer received',
        "image_bg": 'linear-gradient(135deg,#e0c3fc 0%,#8ec5fc 100%)',
        "image_url": '',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'plot-14-swallows-rise',
        "address": 'Plot 14 Swallows Rise',
        "location": 'Penrith',
        "price": 295000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Newtons Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Kilvington Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '15th Nov',
        "memo_sent": '15th Nov',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'End March',
        "chain": "—",
        "alert": None,
        "next_action": '29/1 MTG VAL',
        "image_bg": 'linear-gradient(135deg,#89f7fe 0%,#66a6ff 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34466001/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'plot-15-swallows-rise',
        "address": 'Plot 15 Swallows Rise',
        "location": 'Penrith',
        "price": 280000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Arnison Heelis Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Kilvington Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '9th May',
        "memo_sent": '9th May',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'End March',
        "chain": "—",
        "alert": None,
        "next_action": '31/1 DV CHASED',
        "image_bg": 'linear-gradient(135deg,#fbc2eb 0%,#a6c1ee 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34466001/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'unity-terrace',
        "address": 'Unity Terrace',
        "location": 'Penrith',
        "price": 125000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Arnison Heelis',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Napthens',
        "seller_sol_phone": "—",
        "offer_date": '18th Nov',
        "memo_sent": '18th Nov',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'Poss 26th March',
        "chain": "—",
        "alert": None,
        "next_action": '31/1 DV chased - not having survey',
        "image_bg": 'linear-gradient(135deg,#c9d6ff 0%,#e2e2e2 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33683254/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'force-bank',
        "address": 'Force Bank',
        "location": 'Penrith',
        "price": 400000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'GD Property Solicitors.',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Wragg Mark Bell Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '23rd Dec',
        "memo_sent": '5th Jan',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'Aiming for March',
        "chain": "—",
        "alert": None,
        "next_action": 'dealing with last enquiries',
        "image_bg": 'linear-gradient(135deg,#e8cbc0 0%,#636fa4 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34237472/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'rosedale-house',
        "address": 'Rosedale House',
        "location": 'Penrith',
        "price": 237500,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Arnison Heelis Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Cartmell Shepherd',
        "seller_sol_phone": "—",
        "offer_date": '13th Aug',
        "memo_sent": '13th Aug',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'Buyer aiming for March',
        "chain": "—",
        "alert": None,
        "next_action": '17/2 buyer & seller trying to resolve lack of building regs issues',
        "image_bg": 'linear-gradient(135deg,#ffecd2 0%,#fcb69f 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33756668/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": '19-low-byer-park',
        "address": '19 Low Byer Park',
        "location": 'Penrith',
        "price": 340000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Newtons Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Level Law',
        "seller_sol_phone": "—",
        "offer_date": '26th Nov',
        "memo_sent": '26th Nov',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'march?',
        "chain": "—",
        "alert": None,
        "next_action": '17/2 TR chased',
        "image_bg": 'linear-gradient(135deg,#a8e6cf 0%,#dcedc1 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34466001/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": '22-church-road',
        "address": '22 Church Road',
        "location": 'Penrith',
        "price": 138000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'EMG Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Newtons Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '17th Nov',
        "memo_sent": '26th Nov',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'march?',
        "chain": "—",
        "alert": None,
        "next_action": '17/2 TR chased',
        "image_bg": 'linear-gradient(135deg,#d4fc79 0%,#96e6a1 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34023722/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'wheatsheaf-house',
        "address": 'Wheatsheaf House',
        "location": 'Penrith',
        "price": 340000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'AFG Law',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Taylor Rose Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '14th Aug',
        "memo_sent": '27th Aug',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'April',
        "chain": "—",
        "alert": None,
        "next_action": '15/1 one outstanding query with the council - 8/1 TR chasing',
        "image_bg": 'linear-gradient(135deg,#fdcbf1 0%,#e6dee9 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33965964/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'ghyll-bank-farm',
        "address": 'Ghyll Bank Farm',
        "location": 'Penrith',
        "price": 498000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Milnemoser',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Poole Townsend Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '14th Aug',
        "memo_sent": '26th Aug',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'April',
        "chain": "—",
        "alert": None,
        "next_action": '21/2 septic tank getting installed w/c 23/2',
        "image_bg": 'linear-gradient(135deg,#f5f7fa 0%,#c3cfe2 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33233873/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": '5-parklands-crescent',
        "address": '5 Parklands Crescent',
        "location": 'Penrith',
        "price": 155000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Scott Duff and Co',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Newtons Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '22nd Oct',
        "memo_sent": '29th Oct',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'April',
        "chain": "—",
        "alert": None,
        "next_action": '6/1 Searches ordered today. REQ UPDATE FROM BOTH BUYER AND SELLER SOLS. 5/12 Survey completed',
        "image_bg": 'linear-gradient(135deg,#2c3e50 0%,#3498db 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34054028/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'croft-house-lodge',
        "address": 'Croft House Lodge',
        "location": 'Penrith',
        "price": 535000,
        "status": 'at-risk',
        "status_label": 'AT RISK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Arnison Heelis',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Napthens',
        "seller_sol_phone": "—",
        "offer_date": '12th Nov',
        "memo_sent": '12th Nov',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": 'delayed - buyer lost buyer - waiting for chain to catch up',
        "next_action": 'delayed - buyer lost buyer - waiting for chain to catch up',
        "image_bg": 'linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33776303/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": '98-skinburness-road',
        "address": '98 Skinburness Road',
        "location": 'Penrith',
        "price": 410000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Wilson Davies & co Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Berladgraham solicitor',
        "seller_sol_phone": "—",
        "offer_date": '13th Jan',
        "memo_sent": '14th Jan',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'Initial enquiries raised 17/2',
        "image_bg": 'linear-gradient(135deg,#2d3436 0%,#636e72 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34205792/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'sunny-cottage',
        "address": 'Sunny Cottage',
        "location": 'Penrith',
        "price": 117000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Milburns Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Coopers Burnetts',
        "seller_sol_phone": "—",
        "offer_date": '13th Jan',
        "memo_sent": '23rd Jan',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'Roof survey booked 28/2',
        "image_bg": 'linear-gradient(135deg,#355c7d 0%,#6c5b7b 50%,#c06c84 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34376752/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'knotts-mill',
        "address": 'Knotts Mill',
        "location": 'Penrith',
        "price": 1150000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Cooper Stott Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Kilvington Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '13th Jan',
        "memo_sent": '14th Jan',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'Searches ordered 18th Feb. Survey due back then seller will send draft contracts',
        "image_bg": 'linear-gradient(135deg,#667eea 0%,#764ba2 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33888204/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": '27-otters-holt',
        "address": '27 Otters Holt',
        "location": 'Penrith',
        "price": 462000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Arnison Heelis Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Scott & Duff',
        "seller_sol_phone": "—",
        "offer_date": '15th Jan',
        "memo_sent": '16th Jan',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'Survey 20th Feb SWH',
        "image_bg": 'linear-gradient(135deg,#11998e 0%,#38ef7d 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34254604/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": '3-rectory-road',
        "address": '3 Rectory Road',
        "location": 'Penrith',
        "price": 195000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Wragg Mark-Bell Solicitors Ltd',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Kilvington Solictors',
        "seller_sol_phone": "—",
        "offer_date": '19th Jan',
        "memo_sent": '29th Jan',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'Survey completed 18/02',
        "image_bg": 'linear-gradient(135deg,#e0c3fc 0%,#8ec5fc 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34264323/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'st-martins-gamblesby',
        "address": 'St Martins Gamblesby',
        "location": 'Penrith',
        "price": 305000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'EMG Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Gaynham King and Mellor',
        "seller_sol_phone": "—",
        "offer_date": '23rd Jan',
        "memo_sent": '23rd Jan',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": '23/2 Timber and damp survey booked for 02/03',
        "image_bg": 'linear-gradient(135deg,#89f7fe 0%,#66a6ff 100%)',
        "image_url": '',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'south-view',
        "address": 'South View',
        "location": 'Penrith',
        "price": 340000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Wragg Mark Bell Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Bendles Solicitor',
        "seller_sol_phone": "—",
        "offer_date": '28th Jan',
        "memo_sent": '28th Jan',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": '16/2 Searches ordered this week, expected back in 2 weeks',
        "image_bg": 'linear-gradient(135deg,#fbc2eb 0%,#a6c1ee 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/32964391/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'alrigg-bank',
        "address": 'Alrigg Bank',
        "location": 'Penrith',
        "price": 345000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Milne Moser',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Brockbanks',
        "seller_sol_phone": "—",
        "offer_date": '3rd Feb',
        "memo_sent": '6th Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'mortgage val w/c 23/2',
        "image_bg": 'linear-gradient(135deg,#c9d6ff 0%,#e2e2e2 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33865960/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": '9-rectory-road',
        "address": '9 Rectory Road',
        "location": 'Penrith',
        "price": 380000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Lowick McKay Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Gaynham King and Mellor',
        "seller_sol_phone": "—",
        "offer_date": '3rd Feb',
        "memo_sent": '10th Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'Initial enquiries raised 17/2',
        "image_bg": 'linear-gradient(135deg,#e8cbc0 0%,#636fa4 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34427610/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'cloudbase',
        "address": 'Cloudbase',
        "location": 'Penrith',
        "price": 655000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Warners Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'BLC Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '4th Feb',
        "memo_sent": '6th Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'Survey completed 22/02',
        "image_bg": 'linear-gradient(135deg,#ffecd2 0%,#fcb69f 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34086673/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": '22-fairhill-road',
        "address": '22 Fairhill Road',
        "location": 'Penrith',
        "price": 186750,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Scott Duff & Co',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Gaynham King Mellor',
        "seller_sol_phone": "—",
        "offer_date": '13th Feb',
        "memo_sent": '17th Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'Searches paid 16/02',
        "image_bg": 'linear-gradient(135deg,#a8e6cf 0%,#dcedc1 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34292480/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": '1-south-esk',
        "address": '1 South Esk',
        "location": 'Penrith',
        "price": 225000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Wragg Mark Bell',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Cartmel Shepherd',
        "seller_sol_phone": "—",
        "offer_date": '8th Feb',
        "memo_sent": '8th Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'Survey took place 16/02',
        "image_bg": 'linear-gradient(135deg,#d4fc79 0%,#96e6a1 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34447780/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": '52-primrose-drive',
        "address": '52 Primrose Drive',
        "location": 'Penrith',
        "price": 260000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Napthens',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Arnison Heelis Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '13th Feb',
        "memo_sent": '16th Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'Searches ordered 22/2',
        "image_bg": 'linear-gradient(135deg,#fdcbf1 0%,#e6dee9 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34430420/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": '1-anvil-close',
        "address": '1 Anvil Close',
        "location": 'Penrith',
        "price": 299995,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Arnison Heelis Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Cartmel Shepherd',
        "seller_sol_phone": "—",
        "offer_date": '13th Feb',
        "memo_sent": '16th Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'Searches ordered 19/2',
        "image_bg": 'linear-gradient(135deg,#f5f7fa 0%,#c3cfe2 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/18287340/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'thornleigh',
        "address": 'Thornleigh',
        "location": 'Penrith',
        "price": 375000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Kilvington Solictors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Scott Duff & Co',
        "seller_sol_phone": "—",
        "offer_date": '17th Feb',
        "memo_sent": '17th Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'Searches paid for 23/2',
        "image_bg": 'linear-gradient(135deg,#2c3e50 0%,#3498db 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34152045/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'greyber',
        "address": 'Greyber',
        "location": 'Penrith',
        "price": 482500,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Arnold Greenwood',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'EMG Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '18th Feb',
        "memo_sent": '18th Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'EB Survey on 2/3, vendor completing paperwork, buyers paid for searches, emailed sols',
        "image_bg": 'linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%)',
        "image_url": '',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'southwaite-house',
        "address": 'Southwaite House',
        "location": 'Penrith',
        "price": 942500,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Burnetts',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Bendles Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '19th Feb',
        "memo_sent": '19th Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'searches ordered, survey 27/2',
        "image_bg": 'linear-gradient(135deg,#2d3436 0%,#636e72 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33119008/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": '1-fenton-house',
        "address": '1 Fenton House',
        "location": 'Penrith',
        "price": 127000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Napthens',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Scott Duff & Co',
        "seller_sol_phone": "—",
        "offer_date": '19th Feb',
        "memo_sent": '20th Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'Mortgage meeting with bank booking survey 23/2',
        "image_bg": 'linear-gradient(135deg,#355c7d 0%,#6c5b7b 50%,#c06c84 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34466001/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": '4-valley-view-drive',
        "address": '4 Valley View Drive',
        "location": 'Penrith',
        "price": 510000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Scott Duff & Co',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'EMG Solicitors Ltd',
        "seller_sol_phone": "—",
        "offer_date": '20th Feb',
        "memo_sent": '21st Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": '—',
        "image_bg": 'linear-gradient(135deg,#667eea 0%,#764ba2 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34286214/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'balwmacara',
        "address": 'Balwmacara',
        "location": 'Penrith',
        "price": 372500,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Wragg Mark Bell',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Key Conveyancers',
        "seller_sol_phone": "—",
        "offer_date": '9th Feb',
        "memo_sent": '23rd Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'buyer selling an affordable house through the council',
        "image_bg": 'linear-gradient(135deg,#11998e 0%,#38ef7d 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33895817/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'maple-house',
        "address": 'Maple House',
        "location": 'Penrith',
        "price": 565000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'EMG Solicitors Ltd',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'HFT Gough & Co',
        "seller_sol_phone": "—",
        "offer_date": '21st Feb',
        "memo_sent": '21st Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": '—',
        "image_bg": 'linear-gradient(135deg,#e0c3fc 0%,#8ec5fc 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/18573089/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": '36-norfolk-place',
        "address": '36 Norfolk Place',
        "location": 'Penrith',
        "price": 90000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Newtons Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Scott Duff & Co',
        "seller_sol_phone": "—",
        "offer_date": '25th Feb',
        "memo_sent": '25th Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": '—',
        "image_bg": 'linear-gradient(135deg,#89f7fe 0%,#66a6ff 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34264323/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": '2-croft-view',
        "address": '2 Croft View',
        "location": 'Penrith',
        "price": 185000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Arnison Heelis Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'EMG Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '27th Feb',
        "memo_sent": '27th Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": '—',
        "image_bg": 'linear-gradient(135deg,#fbc2eb 0%,#a6c1ee 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33922675/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'edenlea-appleby',
        "address": 'Edenlea, Appleby',
        "location": 'Penrith',
        "price": 315000,
        "status": 'stalled',
        "status_label": 'STALLED',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Kilvington Solictors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Gaynham King and Mellor',
        "seller_sol_phone": "—",
        "offer_date": '18th Nov',
        "memo_sent": '21st Nov',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": '18/2 related chain - buyer lost buyer - giving them a month to sell otherwise ready to go',
        "image_bg": 'linear-gradient(135deg,#c9d6ff 0%,#e2e2e2 100%)',
        "image_url": '',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'westgate-house',
        "address": 'Westgate House',
        "location": 'Penrith',
        "price": 449950,
        "status": 'stalled',
        "status_label": 'STALLED',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Lings Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Kilvington Solictors',
        "seller_sol_phone": "—",
        "offer_date": '17th Nov',
        "memo_sent": '18th Nov',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": '18/2 buyer lost buyer - giving them a month to sell',
        "image_bg": 'linear-gradient(135deg,#e8cbc0 0%,#636fa4 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34107639/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": '5-carleton-place',
        "address": '5 Carleton Place',
        "location": 'Penrith',
        "price": 285000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Elite Conveyancing',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Gaynham King and Mellor',
        "seller_sol_phone": "—",
        "offer_date": '3rd March',
        "memo_sent": '3rd March',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": '—',
        "image_bg": 'linear-gradient(135deg,#ffecd2 0%,#fcb69f 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34167855/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'woodlands',
        "address": 'Woodlands',
        "location": 'Penrith',
        "price": 915000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Arnison Heelis Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Stamp Jackson & Procter Limited',
        "seller_sol_phone": "—",
        "offer_date": '4th March',
        "memo_sent": '4th March',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": '—',
        "image_bg": 'linear-gradient(135deg,#a8e6cf 0%,#dcedc1 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33362501/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'squirrel-cottage',
        "address": 'Squirrel Cottage',
        "location": 'Penrith',
        "price": 5062.5,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 20,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": '—',
        "buyer_sol_phone": "—",
        "seller_solicitor": '—',
        "seller_sol_phone": "—",
        "offer_date": '4th March',
        "memo_sent": None,
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'memo not sent yet',
        "image_bg": 'linear-gradient(135deg,#d4fc79 0%,#96e6a1 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33724327/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": '9-loughrigg-park',
        "address": '9 Loughrigg Park',
        "location": 'Penrith',
        "price": 4875,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 20,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": '—',
        "buyer_sol_phone": "—",
        "seller_solicitor": '—',
        "seller_sol_phone": "—",
        "offer_date": '5th March',
        "memo_sent": None,
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'memo not sent yet',
        "image_bg": 'linear-gradient(135deg,#fdcbf1 0%,#e6dee9 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34473683/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'aster-cottage',
        "address": 'Aster Cottage',
        "location": 'Penrith',
        "price": 2175,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 20,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": '—',
        "buyer_sol_phone": "—",
        "seller_solicitor": '—',
        "seller_sol_phone": "—",
        "offer_date": '6th March',
        "memo_sent": None,
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": 'memo not sent yet',
        "image_bg": 'linear-gradient(135deg,#f5f7fa 0%,#c3cfe2 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/18955260/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'hill-top-barn',
        "address": 'Hill Top Barn',
        "location": 'Penrith',
        "price": 535000,
        "status": 'stalled',
        "status_label": 'STALLED',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Butterworths Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Kilvington Solictors',
        "seller_sol_phone": "—",
        "offer_date": '27th Nov',
        "memo_sent": '5th Dec',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": "31/1 Vendor still looking for a house - won't move into rented",
        "image_bg": 'linear-gradient(135deg,#2c3e50 0%,#3498db 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34266070/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'chapel-farm',
        "address": 'Chapel Farm',
        "location": 'Penrith',
        "price": 250000,
        "status": 'at-risk',
        "status_label": 'AT RISK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Asserson Law Offices',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Arnison Heelis',
        "seller_sol_phone": "—",
        "offer_date": '11th Dec',
        "memo_sent": '11th Dec',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": '31/1 DV Chased',
        "next_action": '31/1 DV Chased',
        "image_bg": 'linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/32964584/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'town-head-chippy',
        "address": 'Town Head Chippy',
        "location": 'Penrith',
        "price": 196000,
        "status": 'at-risk',
        "status_label": 'AT RISK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Newtons Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Napthens',
        "seller_sol_phone": "—",
        "offer_date": '25th July',
        "memo_sent": '5th Aug',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": '14/1 TR Chased 11/11 land reg issue being sorted',
        "next_action": '14/1 TR Chased 11/11 land reg issue being sorted',
        "image_bg": 'linear-gradient(135deg,#2d3436 0%,#636e72 100%)',
        "image_url": '',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'caroline-cottage',
        "address": 'Caroline Cottage',
        "location": 'Penrith',
        "price": 451000,
        "status": 'at-risk',
        "status_label": 'AT RISK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Newtons Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Arnison Heelis',
        "seller_sol_phone": "—",
        "offer_date": '27th June',
        "memo_sent": '1st July',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": '7/10 SH 16/9 SH chased. Draft Contract issued awaiting enq. 1/9 DV Buyers waiting for searches',
        "next_action": '7/10 SH 16/9 SH chased. Draft Contract issued awaiting enq. 1/9 DV Buyers waiting for searches',
        "image_bg": 'linear-gradient(135deg,#355c7d 0%,#6c5b7b 50%,#c06c84 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33928539/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'romanway',
        "address": 'Romanway',
        "location": 'Penrith',
        "price": 4187.5,
        "status": 'at-risk',
        "status_label": 'AT RISK',
        "progress": 10,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": '—',
        "buyer_sol_phone": "—",
        "seller_solicitor": '—',
        "seller_sol_phone": "—",
        "offer_date": None,
        "memo_sent": None,
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": 'TO INVOICE IN 8 WEEKS',
        "next_action": 'TO INVOICE IN 8 WEEKS',
        "image_bg": 'linear-gradient(135deg,#667eea 0%,#764ba2 100%)',
        "image_url": '',
        "milestones": [
            {"label": "Offer Accepted", "done": False},
            {"label": "Memorandum Sent", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": '2-regis-garth',
        "address": '2 Regis Garth',
        "location": 'Penrith',
        "price": 775000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 20,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": '—',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Scotts, Hall and Birtles solicitors',
        "seller_sol_phone": "—",
        "offer_date": '5th March',
        "memo_sent": None,
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": '8/3 waiting for sols',
        "image_bg": 'linear-gradient(135deg,#11998e 0%,#38ef7d 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34439527/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": '3-regis-garth',
        "address": '3 Regis Garth',
        "location": 'Penrith',
        "price": 725000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 90,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": True},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Downs Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Scotts, Hall and Birtles solicitors',
        "seller_sol_phone": "—",
        "offer_date": '14th Jan',
        "memo_sent": '14th Jan',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": '3rd Oct',
        "completion_target": 'MAY/JUNE',
        "chain": "—",
        "alert": None,
        "next_action": 'Exchanged - Invoice to be sent nearer the completion',
        "image_bg": 'linear-gradient(135deg,#e0c3fc 0%,#8ec5fc 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34264323/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": True},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": '4-regis-garth',
        "address": '4 Regis Garth',
        "location": 'Penrith',
        "price": 425000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 90,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": True},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Scott Duff & Co',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Scotts, Hall and Birtles solicitors',
        "seller_sol_phone": "—",
        "offer_date": '28th Nov',
        "memo_sent": '29th Nov',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": '23rd Feb',
        "completion_target": 'April',
        "chain": "—",
        "alert": None,
        "next_action": 'Exchanged - Invoice to be sent nearer the completion',
        "image_bg": 'linear-gradient(135deg,#89f7fe 0%,#66a6ff 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33511339/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": True},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": '5-regis-garth',
        "address": '5 Regis Garth',
        "location": 'Penrith',
        "price": 425000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 90,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": True},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Kilvington Solictors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Scotts, Hall and Birtles solicitors',
        "seller_sol_phone": "—",
        "offer_date": '14th Mar',
        "memo_sent": '14th Mar',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": '28th Aug',
        "completion_target": 'MAY/JUNE',
        "chain": "—",
        "alert": None,
        "next_action": 'Exchanged - Invoice to be sent nearer the completion',
        "image_bg": 'linear-gradient(135deg,#fbc2eb 0%,#a6c1ee 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33511339/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": True},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'plot-5-swallows-rise',
        "address": 'Plot 5 Swallows Rise',
        "location": 'Penrith',
        "price": 470000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Napthens',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Kilvington Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '17th Oct',
        "memo_sent": None,
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'Not proceedable yet',
        "chain": "—",
        "alert": None,
        "next_action": '—',
        "image_bg": 'linear-gradient(135deg,#c9d6ff 0%,#e2e2e2 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33165740/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'plot-16-swallows-rise',
        "address": 'Plot 16 Swallows Rise',
        "location": 'Penrith',
        "price": 925000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Napthens Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Kilvington Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '19th June',
        "memo_sent": '13th Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'APRIL',
        "chain": "—",
        "alert": None,
        "next_action": '31/1 DV CHASED',
        "image_bg": 'linear-gradient(135deg,#e8cbc0 0%,#636fa4 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/18289422/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'plot-17-swallows-rise',
        "address": 'Plot 17 Swallows Rise',
        "location": 'Penrith',
        "price": 895000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": '—',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Kilvington Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '7th Feb',
        "memo_sent": '7th Feb',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'Not proceedable yet',
        "chain": "—",
        "alert": None,
        "next_action": 'NO MEMO SENT',
        "image_bg": 'linear-gradient(135deg,#ffecd2 0%,#fcb69f 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34466001/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'plot-18-swallows-rise',
        "address": 'Plot 18 Swallows Rise',
        "location": 'Penrith',
        "price": 895000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 20,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Rogers & Norton Solicitors',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Kilvington Solicitors',
        "seller_sol_phone": "—",
        "offer_date": None,
        "memo_sent": None,
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'Not proceedable yet',
        "chain": "—",
        "alert": None,
        "next_action": '—',
        "image_bg": 'linear-gradient(135deg,#a8e6cf 0%,#dcedc1 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34466001/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": False},
            {"label": "Memorandum Sent", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'plot-19-swallows-rise',
        "address": 'Plot 19 Swallows Rise',
        "location": 'Penrith',
        "price": 895000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Napthens',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Kilvington Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '17th Oct',
        "memo_sent": '17th Oct',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'April',
        "chain": "—",
        "alert": None,
        "next_action": '31/1 searches back, raising enqs - buyer aiming for April',
        "image_bg": 'linear-gradient(135deg,#d4fc79 0%,#96e6a1 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/34466001/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'plot-22-swallows-rise',
        "address": 'Plot 22 Swallows Rise',
        "location": 'Penrith',
        "price": 895000,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 60,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Scott Duff & Co',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Kilvington Solicitors',
        "seller_sol_phone": "—",
        "offer_date": '4th Dec',
        "memo_sent": '4th Dec',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": 'Not proceedable yet',
        "chain": "—",
        "alert": None,
        "next_action": '—',
        "image_bg": 'linear-gradient(135deg,#fdcbf1 0%,#e6dee9 100%)',
        "image_url": 'https://cdns3.estateweb.com/assets/9893/of/4/pro/33530078/main/1.jpg',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": True}
        ]
    },
    {
        "id": 'school-house-cliburn',
        "address": 'School House, Cliburn',
        "location": 'Penrith',
        "price": 300000,
        "status": 'at-risk',
        "status_label": 'AT RISK',
        "progress": 40,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": 'Arnison Heelis',
        "buyer_sol_phone": "—",
        "seller_solicitor": 'Napthens LLP',
        "seller_sol_phone": "—",
        "offer_date": '13th Sep',
        "memo_sent": '17th Sep',
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": '31/1 charge on property - lender liquidated, sols trying to prove charge was paid',
        "next_action": '31/1 charge on property - lender liquidated, sols trying to prove charge was paid',
        "image_bg": 'linear-gradient(135deg,#f5f7fa 0%,#c3cfe2 100%)',
        "image_url": '',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": True},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ]
    },
    {
        "id": 'plot-4-waverton',
        "address": 'Plot 4 Waverton',
        "location": 'Penrith',
        "price": 7062.5,
        "status": 'on-track',
        "status_label": 'ON TRACK',
        "progress": 20,
        "duration_days": 0,
        "target_days": 60,
        "days_since_update": 0,
        "card_checks": [
            {"label": "Memo Sent", "done": False},
            {"label": "Exchange", "done": False},
            {"label": "Completion", "done": False}
        ],
        "buyer": '—',
        "buyer_phone": '—',
        "buyer_solicitor": '—',
        "buyer_sol_phone": "—",
        "seller_solicitor": '—',
        "seller_sol_phone": "—",
        "offer_date": '25th Feb',
        "memo_sent": None,
        "searches_ordered": None,
        "searches_received": None,
        "enquiries_raised": None,
        "enquiries_answered": None,
        "mortgage_offered": None,
        "survey_booked": None,
        "survey_complete": None,
        "exchange_target": None,
        "completion_target": None,
        "chain": "—",
        "alert": None,
        "next_action": '—',
        "image_bg": 'linear-gradient(135deg,#2c3e50 0%,#3498db 100%)',
        "image_url": '',
        "milestones": [
            {"label": "Offer Accepted", "done": True},
            {"label": "Memorandum Sent", "done": False},
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
        "subtitle": "9 transactions requiring attention",
        "avg_progress": 36,
        "avg_color": "#e88a3a",
        "border_class": "stalled-banner",
        "visible_ids": ['croft-house-lodge', 'edenlea-appleby', 'westgate-house'],
        "hidden_ids": ['hill-top-barn', 'chapel-farm', 'town-head-chippy', 'caroline-cottage', 'romanway', 'school-house-cliburn'],
        "extra_count": 0,
    },
    {
        "id": "exchanged",
        "icon": "\u2705",
        "title": "Exchanged",
        "subtitle": "4 exchanged",
        "avg_progress": 90,
        "avg_color": "#27ae60",
        "border_class": "green-banner",
        "visible_ids": ['14-howard-park', '3-regis-garth', '4-regis-garth'],
        "hidden_ids": ['5-regis-garth'],
        "extra_count": 0,
    },
    {
        "id": "this-week",
        "icon": "\U0001F4C5",
        "title": "Active Pipeline",
        "subtitle": "51 active transactions",
        "avg_progress": 45,
        "avg_color": "#27ae60",
        "border_class": "blue-banner",
        "visible_ids": ['saddle-house', 'the-limes', 'barnfauld'],
        "hidden_ids": ['station-house-cliburn', 'the-cottage-murton', 'plot-14-swallows-rise', 'plot-15-swallows-rise', 'unity-terrace', 'force-bank', 'rosedale-house', '19-low-byer-park', '22-church-road', 'wheatsheaf-house', 'ghyll-bank-farm', '5-parklands-crescent', '98-skinburness-road', 'sunny-cottage', 'knotts-mill', '27-otters-holt', '3-rectory-road', 'st-martins-gamblesby', 'south-view', 'alrigg-bank', '9-rectory-road', 'cloudbase', '22-fairhill-road', '1-south-esk', '52-primrose-drive', '1-anvil-close', 'thornleigh', 'greyber', 'southwaite-house', '1-fenton-house', '4-valley-view-drive', 'balwmacara', 'maple-house', '36-norfolk-place', '2-croft-view', '5-carleton-place', 'woodlands', 'squirrel-cottage', '9-loughrigg-park', 'aster-cottage', '2-regis-garth', 'plot-5-swallows-rise', 'plot-16-swallows-rise', 'plot-17-swallows-rise', 'plot-18-swallows-rise', 'plot-19-swallows-rise', 'plot-22-swallows-rise', 'plot-4-waverton'],
        "extra_count": 0,
    },
]

PIPELINE = {
    "this_week":    {"count": 4,  "value": 25934076, "confidence": 95},
    "this_month":   {"count": 51, "value": 25934076, "confidence": 80},
    "this_quarter": {"count": 64, "value": 25934076, "confidence": 70},
}

STATS = {
    "active": 64,
    "on_track": 4,
    "at_risk": 6,
    "action": 3,
    "avg_days": 0,
    "pipeline": 25934076,
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
