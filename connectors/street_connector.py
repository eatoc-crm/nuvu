"""
NUVU — Street.co.uk Connector
================================
Connects to the Street CRM API to pull property and contact data
into NUVU's database, and push progression updates back.

Street API Docs:     https://api.street.co.uk/docs
Developer Portal:    https://street.co.uk/developer
OpenAPI Spec:        https://api.street.co.uk/openapi.json

KEY ENDPOINTS:
  Authentication:   API key via Settings > Account Administration > Applications
  Properties:       GET /v1/properties
  Contacts:         GET /v1/contacts
  Progression:      GET /v1/sales/{id}/progression
  Notes:            POST /v1/sales/{id}/notes
  Webhooks:         POST /v1/webhooks (real-time event notifications)

Street is a modern, developer-friendly CRM with a free open API.
Good for NUVU because it has:
  - Dedicated sales progression endpoints
  - Webhook support for real-time sync
  - OpenAPI specification for auto-generated clients
  - No per-call pricing (free with Street subscription)

Currently STUBBED — all methods return realistic sample data.

To get credentials:
  1. Log into Street CRM as admin
  2. Go to Settings > Account Administration > Applications
  3. Create a new application and copy the API key
  4. Pass it to StreetConnector(api_key)
"""

import json
from connectors.base_connector import BaseConnector


class StreetConnector(BaseConnector):
    """Street.co.uk CRM connector.

    Attrs:
        api_key:        API key from Street developer settings
        base_url:       Street API base URL
    """

    # ─── Street status → NUVU status mapping ──────────────
    STREET_STATUS_MAP = {
        "under_offer":    "on-track",
        "sstc":           "on-track",
        "exchanged":      "on-track",
        "chain_delay":    "at-risk",
        "survey_issue":   "at-risk",
        "renegotiating":  "at-risk",
        "fallen_through": "stalled",
        "withdrawn":      "stalled",
        "on_hold":        "stalled",
    }

    def __init__(self, api_key=None,
                 base_url="https://api.street.co.uk"):
        super().__init__()
        self.name = "street"
        self.display_name = "Street.co.uk"
        self.api_key = api_key
        self.base_url = base_url
        self.supports_writeback = True  # Street supports full two-way sync

    # ─────────────────────────────────────────────────────────
    #  AUTHENTICATION
    # ─────────────────────────────────────────────────────────

    def authenticate(self):
        """Authenticate with Street's API.

        REAL IMPLEMENTATION:
        ─────────────────────
        Street uses API key authentication. Include in all requests:
        Headers:
            X-Api-Key: {api_key}
            Content-Type: application/json

        No OAuth flow needed — just validate the key works:
        GET {base_url}/v1/me
        → Returns agency details if key is valid.
        """
        # ── STUB: simulate successful auth ───────────────────
        print(f"  [street] Authenticating with {self.base_url}/v1/me ...")
        self.is_connected = True
        self.last_error = None
        print(f"  [street] Authenticated (stub mode)")
        return True

    # ─────────────────────────────────────────────────────────
    #  GET PROPERTIES
    # ─────────────────────────────────────────────────────────

    def get_properties(self):
        """Fetch all properties from Street.

        REAL IMPLEMENTATION:
        ─────────────────────
        GET {base_url}/v1/properties
        Headers:
            X-Api-Key: {api_key}
        Query params:
            status=under_offer,sstc,exchanged
            per_page=100
            include=sales

        Then for each sale:
        GET {base_url}/v1/sales/{sale_id}/progression
        → Full progression milestones
        """
        # ── STUB: return 2 realistic properties ─────────────
        return [
            {
                "property_id": "STR-60001",
                "address_line_1": "Ivy Bank",
                "address_line_2": "Church Lane",
                "town": "Keswick",
                "county": "Cumbria",
                "postcode": "CA12 4RT",
                "asking_price": 550000,
                "property_type": "Detached",
                "bedrooms": 5,
                "status": "sstc",
                "offer_date": "2026-01-10",
                "target_completion": "2026-04-10",
            },
            {
                "property_id": "STR-60002",
                "address_line_1": "3 River Walk",
                "address_line_2": "Bridge Street",
                "town": "Cockermouth",
                "county": "Cumbria",
                "postcode": "CA13 9NB",
                "asking_price": 235000,
                "property_type": "Flat",
                "bedrooms": 2,
                "status": "under_offer",
                "offer_date": "2026-02-05",
                "target_completion": "2026-05-05",
            },
        ]

    # ─────────────────────────────────────────────────────────
    #  GET PROPERTY DETAILS
    # ─────────────────────────────────────────────────────────

    def get_property_details(self, property_id):
        """Fetch full details for a single property.

        REAL IMPLEMENTATION:
        ─────────────────────
        GET {base_url}/v1/sales/{sale_id}/progression
        Headers:
            X-Api-Key: {api_key}

        Street's progression endpoint returns milestone dates
        and current status. Also supports custom progression steps.
        """
        # ── STUB: return details per property ───────────────
        details = {
            "STR-60001": {
                "memo_sent": "2026-01-14",
                "searches_ordered": "2026-01-16",
                "searches_received": "2026-02-02",
                "enquiries_raised": "2026-02-03",
                "enquiries_answered": "2026-02-08",
                "mortgage_offered": "2026-02-05",
                "survey_booked": "2026-01-18",
                "survey_complete": "2026-01-30",
                "exchange_target": "2026-03-20",
                "chain_info": "Chain of 3 — seller buying in Borrowdale.",
                "alert": None,
                "next_action": "Draft contract for exchange review.",
                "image_url": "https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=800&h=400&fit=crop",
                "progress": 78,
                "duration_days": 31,
                "milestones": [
                    {"label": "Offer Accepted",     "done": True},
                    {"label": "Memorandum Sent",     "done": True},
                    {"label": "Searches Ordered",    "done": True},
                    {"label": "Searches Received",   "done": True},
                    {"label": "Survey Complete",     "done": True},
                    {"label": "Enquiries Raised",    "done": True},
                    {"label": "Enquiries Answered",  "done": True},
                    {"label": "Mortgage Offer",      "done": True},
                    {"label": "Exchange",            "done": False},
                    {"label": "Completion",          "done": False},
                ],
            },
            "STR-60002": {
                "memo_sent": "2026-02-07",
                "searches_ordered": None,
                "searches_received": None,
                "enquiries_raised": None,
                "enquiries_answered": None,
                "mortgage_offered": None,
                "survey_booked": None,
                "survey_complete": None,
                "exchange_target": "2026-04-20",
                "chain_info": "No chain — vacant flat.",
                "alert": None,
                "next_action": "Order searches and instruct survey.",
                "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&h=400&fit=crop",
                "progress": 15,
                "duration_days": 5,
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
        """Fetch contacts for a property.

        REAL IMPLEMENTATION:
        ─────────────────────
        GET {base_url}/v1/sales/{sale_id}?include=contacts
        → Buyer, seller, and solicitor contact references

        GET {base_url}/v1/contacts/{contact_id}
        → Full contact details for each party
        """
        # ── STUB: return contacts per property ───────────────
        contacts = {
            "STR-60001": {
                "buyer": {
                    "name": "Mr & Mrs Crawford",
                    "phone": "07700 901111",
                    "email": "crawford@example.com",
                },
                "seller": {
                    "name": "Dr L. Saunders",
                    "phone": "07700 901222",
                },
                "buyer_solicitor": {
                    "name": "Oglethorpe Sturton & Gillibrand, Lancaster",
                    "phone": "01524 386500",
                },
                "seller_solicitor": {
                    "name": "Arnison Heelis, Penrith",
                    "phone": "01768 862135",
                },
            },
            "STR-60002": {
                "buyer": {
                    "name": "Miss R. Khan",
                    "phone": "07700 901333",
                    "email": "khan@example.com",
                },
                "seller": {
                    "name": "Mr T. Robinson",
                    "phone": "07700 901444",
                },
                "buyer_solicitor": {
                    "name": "JW Dickinson, Penrith",
                    "phone": "01768 862631",
                },
                "seller_solicitor": {
                    "name": "Bendles, Carlisle",
                    "phone": "01228 522215",
                },
            },
        }
        return contacts.get(property_id, {})

    # ─────────────────────────────────────────────────────────
    #  SYNC ALL — maps Street data → NUVU schema
    # ─────────────────────────────────────────────────────────

    def sync_all(self):
        """Full sync: authenticate, fetch, map to NUVU schema."""
        if not self.authenticate():
            raise ConnectionError(f"Street authentication failed: {self.last_error}")

        raw_properties = self.get_properties()
        mapped = []

        for raw in raw_properties:
            pid = raw["property_id"]
            details = self.get_property_details(pid)
            contacts = self.get_contacts(pid)

            nuvu_status = self.STREET_STATUS_MAP.get(
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
                "slug": f"street-{pid.lower().replace('-', '')}",
                "source_connector": "street",
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

        print(f"  [street] Mapped {len(mapped)} properties to NUVU schema")
        return mapped

    # ─────────────────────────────────────────────────────────
    #  WRITE-BACK (OUTBOUND — NUVU → Street)
    # ─────────────────────────────────────────────────────────

    def push_note(self, crm_property_id, note_text, author, timestamp):
        """Push a note back to Street.

        REAL IMPLEMENTATION:
        ─────────────────────
        POST {base_url}/v1/sales/{sale_id}/notes
        Headers:
            X-Api-Key: {api_key}
            Content-Type: application/json
        Body:
            {
                "body": note_text,
                "author": author,
                "created_at": timestamp
            }

        Street supports notes on sales records, which appear in the
        activity timeline within the CRM.
        """
        print(f"  [street] STUB push_note → {crm_property_id}: {note_text[:50]}...")
        return {"success": True, "crm_ref": None, "error": None}

    def push_milestone_update(self, crm_property_id, milestone_name,
                               is_complete, completed_date):
        """Push a milestone update back to Street.

        REAL IMPLEMENTATION:
        ─────────────────────
        PATCH {base_url}/v1/sales/{sale_id}/progression
        Headers:
            X-Api-Key: {api_key}
            Content-Type: application/json
        Body:
            {
                "step": milestone_key,
                "completed": true/false,
                "completed_at": completed_date
            }

        Street progression step keys (map from NUVU milestone names):
            "Memorandum Sent"    → "memo_sent"
            "Searches Ordered"   → "searches_ordered"
            "Searches Received"  → "searches_received"
            "Survey Complete"    → "survey_complete"
            "Enquiries Raised"   → "enquiries_raised"
            "Enquiries Answered" → "enquiries_answered"
            "Mortgage Offer"     → "mortgage_offer"
            "Exchange"           → "exchange"
            "Completion"         → "completion"
        """
        status = "complete" if is_complete else "pending"
        print(f"  [street] STUB push_milestone → {crm_property_id}: {milestone_name} = {status}")
        return {"success": True, "crm_ref": None, "error": None}

    def push_status_change(self, crm_property_id, new_status, reason):
        """Push a status change back to Street.

        REAL IMPLEMENTATION:
        ─────────────────────
        PATCH {base_url}/v1/sales/{sale_id}
        Headers:
            X-Api-Key: {api_key}
            Content-Type: application/json
        Body:
            {
                "status": street_status,
                "note": reason
            }

        Reverse mapping: NUVU → Street:
            "on-track" → "sstc"
            "at-risk"  → "chain_delay"
            "stalled"  → "on_hold"
        """
        print(f"  [street] STUB push_status → {crm_property_id}: {new_status} ({reason})")
        return {"success": True, "crm_ref": None, "error": None}

    def push_completion_summary(self, crm_property_id, summary):
        """Push a completion handback to Street.

        REAL IMPLEMENTATION:
        ─────────────────────
        POST {base_url}/v1/sales/{sale_id}/notes
        Body:
            {
                "body": formatted_summary,
                "author": "NUVU",
                "tags": ["completion_handback"]
            }

        Street supports tags on notes for easy filtering.
        """
        duration = summary.get("duration_days", "?")
        print(f"  [street] STUB push_completion_summary → {crm_property_id}: {duration} days")
        return {"success": True, "crm_ref": None, "error": None}
