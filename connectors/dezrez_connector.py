"""
NUVU — Dezrez / Rezi Connector
=================================
Connects to the Dezrez (Rezi) CRM API to pull property and contact data
into NUVU's database, and push progression updates back.

Dezrez API Docs:    https://api.dezrez.com/swagger
Auth Docs:          OAuth2 + JWT (POST to dezrez-core-auth)
Developer Access:   Email api@dezrez.com to register

KEY ENDPOINTS:
  Authentication:   POST https://dezrez-core-auth.dezrez.com/oauth/token
  Properties:       GET /api/property
  Contacts:         GET /api/contact
  Progression:      GET /api/progression/{roleId}
  Notes:            POST /api/note
  Sales Roles:      GET /api/role/sales

Dezrez has 40+ API modules including a Progression API that tracks
milestones through the sales process. It uses "Roles" to represent
sales/lettings/buying activities on a property.

Pricing: Included with Dezrez/Rezi subscription. API access may
require separate registration.

Currently STUBBED — all methods return realistic sample data.

To get credentials:
  1. Email api@dezrez.com to request API access
  2. You'll receive OAuth2 client_id + client_secret
  3. Auth flow: POST to dezrez-core-auth with JWT
  4. Pass them to DezrezConnector(client_id, client_secret)
"""

import json
from connectors.base_connector import BaseConnector


class DezrezConnector(BaseConnector):
    """Dezrez/Rezi CRM connector.

    Attrs:
        client_id:      OAuth2 Client ID from Dezrez
        client_secret:  OAuth2 Client Secret
        base_url:       Dezrez API base URL
        access_token:   Set after successful authenticate()
    """

    # ─── Dezrez status → NUVU status mapping ──────────────
    DEZREZ_STATUS_MAP = {
        "UnderOffer":     "on-track",
        "SoldSTC":        "on-track",
        "Exchanged":      "on-track",
        "Instructed":     "on-track",
        "ChainDelay":     "at-risk",
        "SurveyIssue":    "at-risk",
        "Renegotiating":  "at-risk",
        "FallenThrough":  "stalled",
        "Withdrawn":      "stalled",
        "OnHold":         "stalled",
    }

    def __init__(self, client_id=None, client_secret=None,
                 base_url="https://api.dezrez.com"):
        super().__init__()
        self.name = "dezrez"
        self.display_name = "Dezrez (Rezi)"
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self.access_token = None
        self.supports_writeback = True  # Dezrez supports two-way via Progression API

    # ─────────────────────────────────────────────────────────
    #  AUTHENTICATION
    # ─────────────────────────────────────────────────────────

    def authenticate(self):
        """Authenticate with Dezrez's OAuth2 + JWT endpoint.

        REAL IMPLEMENTATION:
        ─────────────────────
        POST https://dezrez-core-auth.dezrez.com/oauth/token
        Headers:
            Content-Type: application/x-www-form-urlencoded
        Body:
            grant_type=client_credentials
            &client_id={client_id}
            &client_secret={client_secret}

        Response:
            {
                "access_token": "eyJ...",    (JWT)
                "token_type": "Bearer",
                "expires_in": 3600
            }

        Dezrez tokens are JWTs — they contain agency ID and permissions.
        Include in all subsequent requests:
            Authorization: Bearer {access_token}
            Rezi-Api-Version: 1.0
        """
        # ── STUB: simulate successful auth ───────────────────
        print(f"  [dezrez] Authenticating with dezrez-core-auth ...")
        self.access_token = "stub-dezrez-jwt-token"
        self.is_connected = True
        self.last_error = None
        print(f"  [dezrez] Authenticated (stub mode)")
        return True

    # ─────────────────────────────────────────────────────────
    #  GET PROPERTIES
    # ─────────────────────────────────────────────────────────

    def get_properties(self):
        """Fetch all properties from Dezrez.

        REAL IMPLEMENTATION:
        ─────────────────────
        GET {base_url}/api/role/sales
        Headers:
            Authorization: Bearer {access_token}
            Rezi-Api-Version: 1.0
        Query params:
            status=UnderOffer,SoldSTC,Exchanged
            pageSize=100

        Dezrez uses "Roles" (sales role, letting role, etc.) rather
        than properties directly. A sales role links a property to
        contacts and progression data.

        Then for each role:
        GET {base_url}/api/progression/{roleId}
        → Full progression milestones
        """
        # ── STUB: return 2 realistic properties ─────────────
        return [
            {
                "property_id": "DZR-70001",
                "address_line_1": "Helm View",
                "address_line_2": "Natland Road",
                "town": "Kendal",
                "county": "Cumbria",
                "postcode": "LA9 7QQ",
                "asking_price": 375000,
                "property_type": "Semi-Detached",
                "bedrooms": 3,
                "status": "SoldSTC",
                "offer_date": "2026-01-25",
                "target_completion": "2026-04-25",
            },
            {
                "property_id": "DZR-70002",
                "address_line_1": "Beck Cottage",
                "address_line_2": "Tirril",
                "town": "Penrith",
                "county": "Cumbria",
                "postcode": "CA10 2JF",
                "asking_price": 310000,
                "property_type": "Cottage",
                "bedrooms": 2,
                "status": "UnderOffer",
                "offer_date": "2026-02-03",
                "target_completion": "2026-05-03",
            },
        ]

    # ─────────────────────────────────────────────────────────
    #  GET PROPERTY DETAILS
    # ─────────────────────────────────────────────────────────

    def get_property_details(self, property_id):
        """Fetch full details for a single property.

        REAL IMPLEMENTATION:
        ─────────────────────
        GET {base_url}/api/progression/{roleId}
        Headers:
            Authorization: Bearer {access_token}
            Rezi-Api-Version: 1.0

        Dezrez Progression API returns milestone steps with:
            - Step name and category
            - Completion status and date
            - Responsible party
            - Notes and comments
        """
        # ── STUB: return details per property ───────────────
        details = {
            "DZR-70001": {
                "memo_sent": "2026-01-28",
                "searches_ordered": "2026-01-30",
                "searches_received": "2026-02-07",
                "enquiries_raised": "2026-02-08",
                "enquiries_answered": None,
                "mortgage_offered": "2026-02-05",
                "survey_booked": "2026-02-01",
                "survey_complete": "2026-02-06",
                "exchange_target": "2026-04-01",
                "chain_info": "Seller downsizing — buying flat in Windermere.",
                "alert": None,
                "next_action": "Chase seller solicitor for enquiry answers.",
                "image_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&h=400&fit=crop",
                "progress": 65,
                "duration_days": 16,
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
            "DZR-70002": {
                "memo_sent": None,
                "searches_ordered": None,
                "searches_received": None,
                "enquiries_raised": None,
                "enquiries_answered": None,
                "mortgage_offered": None,
                "survey_booked": None,
                "survey_complete": None,
                "exchange_target": "2026-04-20",
                "chain_info": "No chain — empty cottage.",
                "alert": None,
                "next_action": "Send memorandum and instruct solicitors.",
                "image_url": "https://images.unsplash.com/photo-1605146769289-440113cc3d00?w=800&h=400&fit=crop",
                "progress": 8,
                "duration_days": 7,
                "milestones": [
                    {"label": "Offer Accepted",     "done": True},
                    {"label": "Memorandum Sent",     "done": False},
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
        GET {base_url}/api/role/{roleId}?include=contacts
        → Gets contact IDs for buyer, seller, solicitors

        GET {base_url}/api/contact/{contactId}
        → Full contact details

        Dezrez links contacts via "GroupMembership" relationships.
        """
        # ── STUB: return contacts per property ───────────────
        contacts = {
            "DZR-70001": {
                "buyer": {
                    "name": "Mr C. Wright",
                    "phone": "07700 902111",
                    "email": "wright@example.com",
                },
                "seller": {
                    "name": "Mrs D. Metcalfe",
                    "phone": "07700 902222",
                },
                "buyer_solicitor": {
                    "name": "Cartmell Shepherd, Carlisle",
                    "phone": "01228 516666",
                },
                "seller_solicitor": {
                    "name": "Milne Moser, Kendal",
                    "phone": "01539 729786",
                },
            },
            "DZR-70002": {
                "buyer": {
                    "name": "Miss F. Nguyen",
                    "phone": "07700 902333",
                    "email": "nguyen@example.com",
                },
                "seller": {
                    "name": "Mr & Mrs Hodgson",
                    "phone": "07700 902444",
                },
                "buyer_solicitor": {
                    "name": "Burnetts, Penrith",
                    "phone": "01768 890570",
                },
                "seller_solicitor": {
                    "name": "Arnison Heelis, Penrith",
                    "phone": "01768 862135",
                },
            },
        }
        return contacts.get(property_id, {})

    # ─────────────────────────────────────────────────────────
    #  SYNC ALL — maps Dezrez data → NUVU schema
    # ─────────────────────────────────────────────────────────

    def sync_all(self):
        """Full sync: authenticate, fetch, map to NUVU schema."""
        if not self.authenticate():
            raise ConnectionError(f"Dezrez authentication failed: {self.last_error}")

        raw_properties = self.get_properties()
        mapped = []

        for raw in raw_properties:
            pid = raw["property_id"]
            details = self.get_property_details(pid)
            contacts = self.get_contacts(pid)

            nuvu_status = self.DEZREZ_STATUS_MAP.get(
                raw.get("status", "UnderOffer"), "on-track"
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
                "slug": f"dezrez-{pid.lower().replace('-', '')}",
                "source_connector": "dezrez",
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

        print(f"  [dezrez] Mapped {len(mapped)} properties to NUVU schema")
        return mapped

    # ─────────────────────────────────────────────────────────
    #  WRITE-BACK (OUTBOUND — NUVU → Dezrez)
    # ─────────────────────────────────────────────────────────

    def push_note(self, crm_property_id, note_text, author, timestamp):
        """Push a note back to Dezrez.

        REAL IMPLEMENTATION:
        ─────────────────────
        POST {base_url}/api/note
        Headers:
            Authorization: Bearer {access_token}
            Rezi-Api-Version: 1.0
            Content-Type: application/json
        Body:
            {
                "roleId": role_id,
                "text": note_text,
                "authorName": author,
                "noteType": "Progression"
            }
        """
        print(f"  [dezrez] STUB push_note → {crm_property_id}: {note_text[:50]}...")
        return {"success": True, "crm_ref": None, "error": None}

    def push_milestone_update(self, crm_property_id, milestone_name,
                               is_complete, completed_date):
        """Push a milestone update back to Dezrez.

        REAL IMPLEMENTATION:
        ─────────────────────
        PATCH {base_url}/api/progression/{roleId}/step/{stepId}
        Headers:
            Authorization: Bearer {access_token}
            Rezi-Api-Version: 1.0
            Content-Type: application/json
        Body:
            {
                "isComplete": true/false,
                "completedDate": completed_date
            }

        Dezrez progression steps are identified by stepId. Need to
        look up the step ID from the progression chain first.
        """
        status = "complete" if is_complete else "pending"
        print(f"  [dezrez] STUB push_milestone → {crm_property_id}: {milestone_name} = {status}")
        return {"success": True, "crm_ref": None, "error": None}

    def push_status_change(self, crm_property_id, new_status, reason):
        """Push a status change back to Dezrez.

        REAL IMPLEMENTATION:
        ─────────────────────
        PATCH {base_url}/api/role/{roleId}/status
        Headers:
            Authorization: Bearer {access_token}
            Rezi-Api-Version: 1.0
            Content-Type: application/json
        Body:
            {
                "status": dezrez_status,
                "note": reason
            }

        Reverse mapping: NUVU → Dezrez:
            "on-track" → "SoldSTC"
            "at-risk"  → "ChainDelay"
            "stalled"  → "OnHold"
        """
        print(f"  [dezrez] STUB push_status → {crm_property_id}: {new_status} ({reason})")
        return {"success": True, "crm_ref": None, "error": None}

    def push_completion_summary(self, crm_property_id, summary):
        """Push a completion handback to Dezrez.

        REAL IMPLEMENTATION:
        ─────────────────────
        POST {base_url}/api/note
        Body:
            {
                "roleId": role_id,
                "text": formatted_summary,
                "noteType": "CompletionHandback"
            }
        """
        duration = summary.get("duration_days", "?")
        print(f"  [dezrez] STUB push_completion_summary → {crm_property_id}: {duration} days")
        return {"success": True, "crm_ref": None, "error": None}
