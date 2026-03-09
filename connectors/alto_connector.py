"""
NUVU — Alto / Zoopla Connector
================================
Connects to the Alto CRM API (owned by Zoopla) to pull property
and contact data into NUVU's database.

Alto API Docs:  https://developers.zoopla.co.uk/docs/alto-apis-zoopla-apis
Auth Docs:      https://developers.zoopla.co.uk/docs/authentication-tech-documentation

Currently STUBBED — all methods return realistic sample data so the
sync pipeline can be tested end-to-end.  Replace the stubs with real
API calls once you have client credentials from Zoopla.

To get credentials:
  1. Register at https://developers.zoopla.co.uk/
  2. Request Alto API access for your agency
  3. You'll receive a Client ID and Client Secret
  4. Pass them to AltoConnector(client_id, client_secret)
"""

import json
from connectors.base_connector import BaseConnector


class AltoConnector(BaseConnector):
    """Alto/Zoopla CRM connector.

    Attrs:
        client_id:      OAuth Client ID from Zoopla developer portal
        client_secret:  OAuth Client Secret
        base_url:       Alto API base URL
        access_token:   Set after successful authenticate()
    """

    # ─── Alto status → NUVU status mapping ───────────────────
    # Alto uses statuses like "Under Offer", "SSTC", "Exchanged"
    # We map them to our three-tier system.
    ALTO_STATUS_MAP = {
        "Under Offer":       "on-track",
        "SSTC":              "on-track",    # Sold Subject To Contract
        "Exchanged":         "on-track",
        "For Sale":          "on-track",
        "Under Negotiation": "at-risk",
        "Chain Issues":      "at-risk",
        "Survey Issues":     "at-risk",
        "Awaiting Contract":  "at-risk",
        "Withdrawn":         "stalled",
        "Fall Through":      "stalled",
        "On Hold":           "stalled",
    }

    NUVU_STATUS_LABELS = {
        "on-track": "ON TRACK",
        "at-risk":  "AT RISK",
        "stalled":  "STALLED",
    }

    def __init__(self, client_id=None, client_secret=None,
                 base_url="https://api.alto.zoopladev.co.uk"):
        super().__init__()
        self.name = "alto"
        self.display_name = "Alto (Zoopla)"
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self.access_token = None
        self.supports_writeback = True  # Alto supports outbound (when credentials available)

    # ─────────────────────────────────────────────────────────
    #  AUTHENTICATION
    # ─────────────────────────────────────────────────────────

    def authenticate(self):
        """Authenticate with Alto's OAuth token endpoint.

        REAL IMPLEMENTATION (when credentials available):
        ─────────────────────────────────────────────────
        POST {base_url}/token
        Headers:
            Authorization: Basic base64(client_id:client_secret)
            Content-Type: application/x-www-form-urlencoded
        Body:
            grant_type=client_credentials

        Response:
            {
                "access_token": "eyJ...",
                "token_type": "Bearer",
                "expires_in": 3600
            }

        Then set self.access_token and include it in all subsequent
        requests as:  Authorization: Bearer {access_token}
        """
        # ── STUB: simulate successful auth ───────────────────
        print(f"  [alto] Authenticating with {self.base_url}/token ...")
        self.access_token = "stub-token-for-testing"
        self.is_connected = True
        self.last_error = None
        print(f"  [alto] Authenticated (stub mode)")
        return True

    # ─────────────────────────────────────────────────────────
    #  GET PROPERTIES
    # ─────────────────────────────────────────────────────────

    def get_properties(self):
        """Fetch all properties from Alto's property listing endpoint.

        REAL IMPLEMENTATION:
        ─────────────────────
        GET {base_url}/v2/properties
        Headers:
            Authorization: Bearer {access_token}
        Query params:
            status=Under+Offer,SSTC,Exchanged
            page=1
            page_size=100
            include=address,price,status,dates

        Response:
            {
                "data": [
                    {
                        "property_id": "ALT-12345",
                        "address_line_1": "Rose Cottage",
                        "address_line_2": "Main Street",
                        "town": "Appleby-in-Westmorland",
                        "county": "Cumbria",
                        "postcode": "CA16 6QN",
                        "asking_price": 325000,
                        "property_type": "Detached",
                        "bedrooms": 3,
                        "status": "SSTC",
                        "offer_date": "2026-01-15",
                        ...
                    },
                    ...
                ],
                "pagination": {"page": 1, "total_pages": 1, "total": 3}
            }

        Would paginate through all pages if total_pages > 1.
        """
        # ── STUB: return 3 realistic Cumbria properties ──────
        return [
            {
                "property_id": "ALT-40001",
                "address_line_1": "Rose Cottage",
                "address_line_2": "Main Street",
                "town": "Appleby-in-Westmorland",
                "county": "Cumbria",
                "postcode": "CA16 6QN",
                "asking_price": 325000,
                "property_type": "Detached",
                "bedrooms": 3,
                "status": "SSTC",
                "offer_date": "2026-01-15",
                "target_completion": "2026-04-15",
            },
            {
                "property_id": "ALT-40002",
                "address_line_1": "Fell View",
                "address_line_2": "Station Road",
                "town": "Kirkby Stephen",
                "county": "Cumbria",
                "postcode": "CA17 4RH",
                "asking_price": 475000,
                "property_type": "Semi-Detached",
                "bedrooms": 4,
                "status": "Under Offer",
                "offer_date": "2026-01-28",
                "target_completion": "2026-05-01",
            },
            {
                "property_id": "ALT-40003",
                "address_line_1": "Lakeside Barn",
                "address_line_2": "Howtown Road",
                "town": "Pooley Bridge",
                "county": "Cumbria",
                "postcode": "CA10 2NA",
                "asking_price": 695000,
                "property_type": "Barn Conversion",
                "bedrooms": 5,
                "status": "Chain Issues",
                "offer_date": "2025-12-10",
                "target_completion": "2026-03-20",
            },
        ]

    # ─────────────────────────────────────────────────────────
    #  GET PROPERTY DETAILS
    # ─────────────────────────────────────────────────────────

    def get_property_details(self, property_id):
        """Fetch full details for a single property.

        REAL IMPLEMENTATION:
        ─────────────────────
        GET {base_url}/v2/properties/{property_id}
        Headers:
            Authorization: Bearer {access_token}
        Query params:
            include=dates,milestones,chain,images

        Response includes all dates (memo sent, searches ordered,
        survey dates, exchange/completion targets), chain info,
        property images, and progression milestones.
        """
        # ── STUB: return detail based on property_id ─────────
        details = {
            "ALT-40001": {
                "memo_sent": "2026-01-20",
                "searches_ordered": "2026-01-22",
                "searches_received": "2026-02-05",
                "enquiries_raised": "2026-02-06",
                "enquiries_answered": None,
                "mortgage_offered": "2026-02-01",
                "survey_booked": "2026-01-25",
                "survey_complete": "2026-02-03",
                "exchange_target": "2026-03-28",
                "chain_info": "First-time buyer. No chain below.",
                "alert": None,
                "next_action": "Chase buyer solicitor for enquiry responses.",
                "image_url": "https://images.unsplash.com/photo-1518780664697-55e3ad937233?w=800&h=400&fit=crop",
                "progress": 72,
                "duration_days": 26,
                "milestones": [
                    {"label": "Offer Accepted",     "done": True},
                    {"label": "Memorandum Sent",     "done": True},
                    {"label": "Searches Ordered",    "done": True},
                    {"label": "Searches Received",   "done": True},
                    {"label": "Survey Complete",     "done": True},
                    {"label": "Enquiries Raised",    "done": True},
                    {"label": "Enquiries Answered",  "done": False},
                    {"label": "Mortgage Offer",      "done": True},
                    {"label": "Exchange",            "done": False},
                    {"label": "Completion",          "done": False},
                ],
            },
            "ALT-40002": {
                "memo_sent": "2026-02-01",
                "searches_ordered": "2026-02-03",
                "searches_received": None,
                "enquiries_raised": None,
                "enquiries_answered": None,
                "mortgage_offered": None,
                "survey_booked": "2026-02-05",
                "survey_complete": None,
                "exchange_target": "2026-04-15",
                "chain_info": "Seller relocating to Scotland. No upward chain.",
                "alert": None,
                "next_action": "Monitor search turnaround — ordered 3 Feb.",
                "image_url": "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800&h=400&fit=crop",
                "progress": 35,
                "duration_days": 13,
                "milestones": [
                    {"label": "Offer Accepted",     "done": True},
                    {"label": "Memorandum Sent",     "done": True},
                    {"label": "Searches Ordered",    "done": True},
                    {"label": "Searches Received",   "done": False},
                    {"label": "Survey Complete",     "done": False},
                    {"label": "Enquiries Raised",    "done": False},
                    {"label": "Enquiries Answered",  "done": False},
                    {"label": "Mortgage Offer",      "done": False},
                    {"label": "Exchange",            "done": False},
                    {"label": "Completion",          "done": False},
                ],
            },
            "ALT-40003": {
                "memo_sent": "2025-12-16",
                "searches_ordered": "2025-12-18",
                "searches_received": "2026-01-08",
                "enquiries_raised": "2026-01-10",
                "enquiries_answered": "2026-01-24",
                "mortgage_offered": None,
                "survey_booked": "2025-12-20",
                "survey_complete": "2026-01-06",
                "exchange_target": "2026-03-01",
                "chain_info": "Buyer has property to sell in Penrith (not yet sold). Seller purchasing in Lake District (chain of 3).",
                "alert": "Chain delay — buyer's property sale has fallen through. Seeking new buyer urgently.",
                "next_action": "Escalate chain situation — contact buyer re: Penrith sale status.",
                "image_url": "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=800&h=400&fit=crop",
                "progress": 58,
                "duration_days": 62,
                "milestones": [
                    {"label": "Offer Accepted",     "done": True},
                    {"label": "Memorandum Sent",     "done": True},
                    {"label": "Searches Ordered",    "done": True},
                    {"label": "Searches Received",   "done": True},
                    {"label": "Survey Complete",     "done": True},
                    {"label": "Enquiries Raised",    "done": True},
                    {"label": "Enquiries Answered",  "done": True},
                    {"label": "Mortgage Offer",      "done": None},
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
        """Fetch contacts (buyer, seller, solicitors) for a property.

        REAL IMPLEMENTATION:
        ─────────────────────
        GET {base_url}/v2/properties/{property_id}/contacts
        Headers:
            Authorization: Bearer {access_token}

        Response:
            {
                "buyer": {
                    "name": "...", "phone": "...", "email": "..."
                },
                "seller": {
                    "name": "...", "phone": "...", "email": "..."
                },
                "buyer_solicitor": {
                    "firm": "...", "contact": "...", "phone": "..."
                },
                "seller_solicitor": {
                    "firm": "...", "contact": "...", "phone": "..."
                }
            }
        """
        # ── STUB: return contacts per property ───────────────
        contacts = {
            "ALT-40001": {
                "buyer": {
                    "name": "Mr & Mrs Hartley",
                    "phone": "07700 900123",
                    "email": "hartley@example.com",
                },
                "seller": {
                    "name": "Mrs J. Atkinson",
                    "phone": "07700 900456",
                },
                "buyer_solicitor": {
                    "name": "Oglethorpe Sturton & Gillibrand, Lancaster",
                    "phone": "01524 386500",
                },
                "seller_solicitor": {
                    "name": "Burnetts, Penrith",
                    "phone": "01768 890570",
                },
            },
            "ALT-40002": {
                "buyer": {
                    "name": "Dr S. Kapoor",
                    "phone": "07700 900789",
                    "email": "kapoor@example.com",
                },
                "seller": {
                    "name": "Mr R. Bell",
                    "phone": "07700 900012",
                },
                "buyer_solicitor": {
                    "name": "Cartmell Shepherd, Carlisle",
                    "phone": "01228 516666",
                },
                "seller_solicitor": {
                    "name": "JW Dickinson, Penrith",
                    "phone": "01768 862631",
                },
            },
            "ALT-40003": {
                "buyer": {
                    "name": "Mr & Mrs Greenwood",
                    "phone": "07700 900345",
                    "email": "greenwood@example.com",
                },
                "seller": {
                    "name": "Estate of Mrs B. Walker",
                    "phone": None,
                },
                "buyer_solicitor": {
                    "name": "Harrison Drury, Kendal",
                    "phone": "01539 735251",
                },
                "seller_solicitor": {
                    "name": "Bendles, Carlisle",
                    "phone": "01228 522215",
                },
            },
        }
        return contacts.get(property_id, {})

    # ─────────────────────────────────────────────────────────
    #  SYNC ALL — maps Alto data → NUVU schema
    # ─────────────────────────────────────────────────────────

    def sync_all(self):
        """Full sync: authenticate, fetch, map to NUVU schema.

        Returns:
            list[dict]: Property dicts using NUVU DB column names,
                        ready to be passed to sync_to_database.write_sync_data().
        """
        if not self.authenticate():
            raise ConnectionError(f"Alto authentication failed: {self.last_error}")

        raw_properties = self.get_properties()
        mapped = []

        for raw in raw_properties:
            pid = raw["property_id"]
            details = self.get_property_details(pid)
            contacts = self.get_contacts(pid)

            nuvu_status = self._map_status(raw.get("status", "Under Offer"))

            # Build card_checks from first 3 key milestones
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
                "slug": f"alto-{pid.lower().replace('-', '')}",
                "source_connector": "alto",
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
                # Nested data for sync_to_database
                "buyer": contacts.get("buyer", {}),
                "seller": contacts.get("seller", {}),
                "buyer_solicitor": contacts.get("buyer_solicitor", {}),
                "seller_solicitor": contacts.get("seller_solicitor", {}),
                "milestones": milestones,
            }
            mapped.append(prop)

        print(f"  [alto] Mapped {len(mapped)} properties to NUVU schema")
        return mapped

    # ─────────────────────────────────────────────────────────
    #  WRITE-BACK (OUTBOUND — NUVU → Alto)
    # ─────────────────────────────────────────────────────────

    def push_note(self, crm_property_id, note_text, author, timestamp):
        """Push a note back to Alto.

        REAL IMPLEMENTATION:
        ─────────────────────
        POST {base_url}/v2/properties/{crm_property_id}/events
        Headers:
            Authorization: Bearer {access_token}
            Content-Type: application/json
        Body:
            {
                "event_type": "note",
                "description": note_text,
                "created_by": author,
                "event_date": timestamp
            }

        Alto uses "management events" for notes/journal entries.
        Each event appears in the property's activity timeline.
        """
        # ── STUB: log and return success ───────────────────
        print(f"  [alto] STUB push_note → {crm_property_id}: {note_text[:50]}...")
        return {"success": True, "crm_ref": None, "error": None}

    def push_milestone_update(self, crm_property_id, milestone_name,
                               is_complete, completed_date):
        """Push a milestone update back to Alto.

        REAL IMPLEMENTATION:
        ─────────────────────
        PATCH {base_url}/v2/properties/{crm_property_id}/progression
        Headers:
            Authorization: Bearer {access_token}
            Content-Type: application/json
        Body:
            {
                "milestone": milestone_name,
                "status": "complete" | "pending",
                "completed_date": completed_date
            }

        Alto's progression endpoint handles sales milestone updates.
        Milestone names may need mapping from NUVU → Alto format:
            "Searches Received" → "searches_received"
            "Survey Complete" → "survey_completed"
            etc.
        """
        # ── STUB: log and return success ───────────────────
        status = "complete" if is_complete else "pending"
        print(f"  [alto] STUB push_milestone → {crm_property_id}: {milestone_name} = {status}")
        return {"success": True, "crm_ref": None, "error": None}

    def push_status_change(self, crm_property_id, new_status, reason):
        """Push a status change back to Alto.

        REAL IMPLEMENTATION:
        ─────────────────────
        PATCH {base_url}/v2/properties/{crm_property_id}
        Headers:
            Authorization: Bearer {access_token}
            Content-Type: application/json
        Body:
            {
                "status": alto_status_string,
                "status_note": reason
            }

        Would need to reverse-map NUVU status → Alto status:
            "on-track" → "SSTC"
            "at-risk"  → "Chain Issues" or "Under Negotiation"
            "stalled"  → "On Hold"
        """
        # ── STUB: log and return success ───────────────────
        print(f"  [alto] STUB push_status → {crm_property_id}: {new_status} ({reason})")
        return {"success": True, "crm_ref": None, "error": None}

    def push_completion_summary(self, crm_property_id, summary):
        """Push a completion handback to Alto.

        REAL IMPLEMENTATION:
        ─────────────────────
        POST {base_url}/v2/properties/{crm_property_id}/events
        Headers:
            Authorization: Bearer {access_token}
            Content-Type: application/json
        Body:
            {
                "event_type": "completion_summary",
                "description": "NUVU Completion Handback: [formatted summary]",
                "metadata": summary
            }

        Packages the entire NUVU transaction history and posts it as a
        management event to Alto, so the full progression record is
        available in the CRM after NUVU's involvement ends.
        """
        # ── STUB: log and return success ───────────────────
        duration = summary.get("duration_days", "?")
        print(f"  [alto] STUB push_completion_summary → {crm_property_id}: {duration} days")
        return {"success": True, "crm_ref": None, "error": None}

    # ─────────────────────────────────────────────────────────
    #  HELPERS
    # ─────────────────────────────────────────────────────────

    def _map_status(self, alto_status):
        """Map an Alto property status string to a NUVU status.

        Falls back to 'on-track' for unknown statuses.
        """
        return self.ALTO_STATUS_MAP.get(alto_status, "on-track")
