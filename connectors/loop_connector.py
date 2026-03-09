"""
NUVU — Loop Connector (Placeholder)
======================================
Placeholder connector for the Loop CRM platform.

Loop is a newer CRM for UK estate agents. API documentation is
not yet publicly available. This connector follows the same
BaseConnector interface and is ready for real implementation
when the Loop API becomes accessible.

Currently STUBBED — all methods return minimal sample data.

To get credentials:
  1. Contact Loop support to request API access
  2. Credentials and endpoints will be provided by Loop directly
  3. Pass them to LoopConnector(api_key)
"""

import json
from connectors.base_connector import BaseConnector


class LoopConnector(BaseConnector):
    """Loop CRM connector (placeholder).

    Attrs:
        api_key:    API key (when available from Loop)
        base_url:   Loop API base URL (TBD)
    """

    # ─── Loop status → NUVU status mapping (placeholder) ──
    LOOP_STATUS_MAP = {
        "under_offer":    "on-track",
        "exchanged":      "on-track",
        "at_risk":        "at-risk",
        "stalled":        "stalled",
    }

    def __init__(self, api_key=None,
                 base_url="https://api.loop.co.uk"):
        super().__init__()
        self.name = "loop"
        self.display_name = "Loop"
        self.api_key = api_key
        self.base_url = base_url
        self.supports_writeback = False  # Not yet — API not available

    # ─────────────────────────────────────────────────────────
    #  AUTHENTICATION
    # ─────────────────────────────────────────────────────────

    def authenticate(self):
        """Authenticate with Loop's API (placeholder).

        REAL IMPLEMENTATION: TBD — awaiting Loop API documentation.
        """
        # ── STUB: simulate successful auth ───────────────────
        print(f"  [loop] Authenticating (placeholder) ...")
        self.is_connected = True
        self.last_error = None
        print(f"  [loop] Authenticated (stub mode)")
        return True

    # ─────────────────────────────────────────────────────────
    #  GET PROPERTIES
    # ─────────────────────────────────────────────────────────

    def get_properties(self):
        """Fetch properties from Loop (placeholder)."""
        # ── STUB: return 1 minimal property ──────────────────
        return [
            {
                "property_id": "LOOP-80001",
                "address_line_1": "Derwent House",
                "address_line_2": "Lake Road",
                "town": "Ambleside",
                "county": "Cumbria",
                "postcode": "LA22 0DB",
                "asking_price": 485000,
                "property_type": "Detached",
                "bedrooms": 4,
                "status": "under_offer",
                "offer_date": "2026-02-01",
                "target_completion": "2026-05-01",
            },
        ]

    # ─────────────────────────────────────────────────────────
    #  GET PROPERTY DETAILS
    # ─────────────────────────────────────────────────────────

    def get_property_details(self, property_id):
        """Fetch property details from Loop (placeholder)."""
        # ── STUB ────────────────────────────────────────────
        details = {
            "LOOP-80001": {
                "memo_sent": "2026-02-04",
                "searches_ordered": None,
                "searches_received": None,
                "enquiries_raised": None,
                "enquiries_answered": None,
                "mortgage_offered": None,
                "survey_booked": None,
                "survey_complete": None,
                "exchange_target": "2026-04-15",
                "chain_info": "No chain — relocating from London.",
                "alert": None,
                "next_action": "Order searches and instruct survey.",
                "image_url": "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&h=400&fit=crop",
                "progress": 12,
                "duration_days": 9,
                "milestones": [
                    {"label": "Offer Accepted",     "done": True},
                    {"label": "Memorandum Sent",     "done": True},
                    {"label": "Searches Ordered",    "done": False},
                    {"label": "Searches Received",   "done": False},
                    {"label": "Survey Complete",     "done": False},
                    {"label": "Enquiries Raised",    "done": False},
                    {"label": "Enquiries Answered",  "done": False},
                    {"label": "Mortgage Offer",      "done": False},
                    {"label": "Exchange",            "done": False},
                    {"label": "Completion",          "done": False},
                ],
            },
        }
        return details.get(property_id, {})

    # ─────────────────────────────────────────────────────────
    #  GET CONTACTS
    # ─────────────────────────────────────────────────────────

    def get_contacts(self, property_id):
        """Fetch contacts from Loop (placeholder)."""
        # ── STUB ────────────────────────────────────────────
        contacts = {
            "LOOP-80001": {
                "buyer": {
                    "name": "Mr & Mrs Bennett",
                    "phone": "07700 903111",
                    "email": "bennett@example.com",
                },
                "seller": {
                    "name": "Mrs K. Irwin",
                    "phone": "07700 903222",
                },
                "buyer_solicitor": {
                    "name": "Harrison Drury, Kendal",
                    "phone": "01539 735251",
                },
                "seller_solicitor": {
                    "name": "Oglethorpe Sturton & Gillibrand, Lancaster",
                    "phone": "01524 386500",
                },
            },
        }
        return contacts.get(property_id, {})

    # ─────────────────────────────────────────────────────────
    #  SYNC ALL — maps Loop data → NUVU schema
    # ─────────────────────────────────────────────────────────

    def sync_all(self):
        """Full sync: authenticate, fetch, map to NUVU schema."""
        if not self.authenticate():
            raise ConnectionError(f"Loop authentication failed: {self.last_error}")

        raw_properties = self.get_properties()
        mapped = []

        for raw in raw_properties:
            pid = raw["property_id"]
            details = self.get_property_details(pid)
            contacts = self.get_contacts(pid)

            nuvu_status = self.LOOP_STATUS_MAP.get(
                raw.get("status", "under_offer"), "on-track"
            )

            milestones = details.get("milestones", [])
            card_checks = []
            check_labels = ["Searches", "Survey", "Enquiries Raised"]
            milestone_label_map = {
                "Searches": "Searches Received",
                "Survey": "Survey Complete",
                "Enquiries Raised": "Enquiries Raised",
            }
            for cl in check_labels:
                ml = milestone_label_map[cl]
                ms_match = next((m for m in milestones if m["label"] == ml), None)
                card_checks.append({
                    "label": cl,
                    "done": ms_match["done"] if ms_match else False,
                })

            prop = {
                "slug": f"loop-{pid.lower().replace('-', '')}",
                "source_connector": "loop",
                "source_crm_id": pid,
                "address": raw["address_line_1"],
                "location": raw["town"],
                "price": raw["asking_price"],
                "bedrooms": raw.get("bedrooms"),
                "status": nuvu_status,
                "progress_percentage": details.get("progress", 0),
                "duration_days": details.get("duration_days", 0),
                "target_days": 60,
                "days_since_update": 0,
                "chain_position": details.get("chain_info"),
                "alert": details.get("alert"),
                "next_action": details.get("next_action"),
                "hero_image": details.get("image_url"),
                "image_bg": "linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%)",
                "card_checks": json.dumps(card_checks),
                "offer_accepted_date": raw.get("offer_date"),
                "memo_sent_date": details.get("memo_sent"),
                "searches_ordered": details.get("searches_ordered"),
                "searches_received": details.get("searches_received"),
                "enquiries_raised": details.get("enquiries_raised"),
                "enquiries_answered": details.get("enquiries_answered"),
                "mortgage_offered": details.get("mortgage_offered"),
                "survey_booked": details.get("survey_booked"),
                "survey_complete": details.get("survey_complete"),
                "exchange_date": details.get("exchange_target"),
                "completion_date": raw.get("target_completion"),
                "buyer": contacts.get("buyer", {}),
                "seller": contacts.get("seller", {}),
                "buyer_solicitor": contacts.get("buyer_solicitor", {}),
                "seller_solicitor": contacts.get("seller_solicitor", {}),
                "milestones": milestones,
            }
            mapped.append(prop)

        print(f"  [loop] Mapped {len(mapped)} properties to NUVU schema")
        return mapped

    # ─────────────────────────────────────────────────────────
    #  WRITE-BACK (OUTBOUND — NUVU → Loop) — Placeholder
    # ─────────────────────────────────────────────────────────

    def push_note(self, crm_property_id, note_text, author, timestamp):
        """Push a note back to Loop (placeholder — not yet supported)."""
        print(f"  [loop] STUB push_note → {crm_property_id}: {note_text[:50]}...")
        return {"success": False, "crm_ref": None, "error": "Loop API not yet available"}

    def push_milestone_update(self, crm_property_id, milestone_name,
                               is_complete, completed_date):
        """Push a milestone update back to Loop (placeholder)."""
        print(f"  [loop] STUB push_milestone → {crm_property_id}: {milestone_name}")
        return {"success": False, "crm_ref": None, "error": "Loop API not yet available"}

    def push_status_change(self, crm_property_id, new_status, reason):
        """Push a status change back to Loop (placeholder)."""
        print(f"  [loop] STUB push_status → {crm_property_id}: {new_status}")
        return {"success": False, "crm_ref": None, "error": "Loop API not yet available"}

    def push_completion_summary(self, crm_property_id, summary):
        """Push a completion handback to Loop (placeholder)."""
        print(f"  [loop] STUB push_completion_summary → {crm_property_id}")
        return {"success": False, "crm_ref": None, "error": "Loop API not yet available"}
