"""
NUVU — Reapit Foundations Connector
=====================================
Connects to the Reapit Foundations API to pull property and contact data
into NUVU's database, and push progression updates back.

Reapit API Docs:     https://foundations-documentation.reapit.cloud/
Developer Portal:    https://developers.reapit.cloud/
Conveyancing API:    https://foundations-documentation.reapit.cloud/api/api-documentation#conveyancing

KEY ENDPOINTS:
  Authentication:   POST https://connect.reapit.cloud/token (OpenID Connect)
  Properties:       GET /properties
  Contacts:         GET /contacts
  Offers:           GET /offers
  Conveyancing:     GET /conveyancing  (purpose-built for sales progression!)
  Journal:          POST /journalEntries

Reapit is the BEST CRM for NUVU integration because it has a dedicated
Conveyancing API with built-in progression tracking, milestone support,
and chain management.

Pricing: Per-call basis (~£0.01/call), no monthly minimums.

Currently STUBBED — all methods return realistic sample data.
Replace stubs with real API calls once Reapit developer credentials are obtained.

To get credentials:
  1. Register at https://developers.reapit.cloud/
  2. Create a new app, request 'Conveyancing' and 'Properties' scopes
  3. You'll receive a Client ID and Client Secret (OpenID Connect)
  4. Pass them to ReapitConnector(client_id, client_secret)
"""

import json
from connectors.base_connector import BaseConnector


class ReapitConnector(BaseConnector):
    """Reapit Foundations CRM connector.

    Attrs:
        client_id:      OpenID Connect Client ID from Reapit developer portal
        client_secret:  OpenID Connect Client Secret
        base_url:       Reapit Foundations API base URL
        access_token:   Set after successful authenticate()
    """

    # ─── Reapit status → NUVU status mapping ───────────────
    # Reapit Conveyancing uses statuses like:
    # "preAppraisal", "underOffer", "exchanged", "completed", etc.
    REAPIT_STATUS_MAP = {
        "underOffer":        "on-track",
        "instructed":        "on-track",
        "exchanged":         "on-track",
        "readyToExchange":   "on-track",
        "underNegotiation":  "at-risk",
        "chainDelays":       "at-risk",
        "surveyIssues":      "at-risk",
        "withdrawn":         "stalled",
        "fallen":            "stalled",
        "onHold":            "stalled",
    }

    def __init__(self, client_id=None, client_secret=None,
                 base_url="https://platform.reapit.cloud"):
        super().__init__()
        self.name = "reapit"
        self.display_name = "Reapit Foundations"
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self.access_token = None
        self.supports_writeback = True  # Reapit supports full two-way sync

    # ─────────────────────────────────────────────────────────
    #  AUTHENTICATION
    # ─────────────────────────────────────────────────────────

    def authenticate(self):
        """Authenticate with Reapit's OpenID Connect endpoint.

        REAL IMPLEMENTATION:
        ─────────────────────
        POST https://connect.reapit.cloud/token
        Headers:
            Content-Type: application/x-www-form-urlencoded
        Body:
            grant_type=client_credentials
            &client_id={client_id}
            &client_secret={client_secret}

        Response:
            {
                "access_token": "eyJ...",
                "token_type": "Bearer",
                "expires_in": 3600
            }

        Then include in all subsequent requests:
            Authorization: Bearer {access_token}
            api-version: 2023-10-01
        """
        # ── STUB: simulate successful auth ───────────────────
        print(f"  [reapit] Authenticating with connect.reapit.cloud ...")
        self.access_token = "stub-reapit-token"
        self.is_connected = True
        self.last_error = None
        print(f"  [reapit] Authenticated (stub mode)")
        return True

    # ─────────────────────────────────────────────────────────
    #  GET PROPERTIES
    # ─────────────────────────────────────────────────────────

    def get_properties(self):
        """Fetch all properties from Reapit.

        REAL IMPLEMENTATION:
        ─────────────────────
        GET {base_url}/properties
        Headers:
            Authorization: Bearer {access_token}
            api-version: 2023-10-01
        Query params:
            sellingStatus=underOffer,exchanged
            pageSize=100
            embed=selling

        Then for each property with an active offer:
        GET {base_url}/conveyancing?propertyId={id}
        to get the full progression/conveyancing data.
        """
        # ── STUB: return 2 realistic properties ─────────────
        return [
            {
                "property_id": "RPT-50001",
                "address_line_1": "Bracken House",
                "address_line_2": "Windermere Road",
                "town": "Kendal",
                "county": "Cumbria",
                "postcode": "LA9 5EP",
                "asking_price": 425000,
                "property_type": "Detached",
                "bedrooms": 4,
                "status": "underOffer",
                "offer_date": "2026-01-20",
                "target_completion": "2026-04-20",
            },
            {
                "property_id": "RPT-50002",
                "address_line_1": "The Old Smithy",
                "address_line_2": "Market Square",
                "town": "Penrith",
                "county": "Cumbria",
                "postcode": "CA11 7HZ",
                "asking_price": 289000,
                "property_type": "Terraced",
                "bedrooms": 2,
                "status": "underOffer",
                "offer_date": "2026-02-01",
                "target_completion": "2026-05-01",
            },
        ]

    # ─────────────────────────────────────────────────────────
    #  GET PROPERTY DETAILS
    # ─────────────────────────────────────────────────────────

    def get_property_details(self, property_id):
        """Fetch full details for a single property.

        REAL IMPLEMENTATION:
        ─────────────────────
        GET {base_url}/conveyancing?propertyId={property_id}
        Headers:
            Authorization: Bearer {access_token}
            api-version: 2023-10-01

        Reapit's Conveyancing API returns:
            - Progression chain data
            - Milestones with dates
            - Solicitor/conveyancer references
            - Downward/upward chain links
            - Exchange and completion targets
        """
        # ── STUB: return details per property ───────────────
        details = {
            "RPT-50001": {
                "memo_sent": "2026-01-25",
                "searches_ordered": "2026-01-27",
                "searches_received": None,
                "enquiries_raised": None,
                "enquiries_answered": None,
                "mortgage_offered": None,
                "survey_booked": "2026-02-01",
                "survey_complete": None,
                "exchange_target": "2026-04-01",
                "chain_info": "Downward chain of 2. Seller purchasing in Ambleside.",
                "alert": None,
                "next_action": "Chase local authority for search results.",
                "image_url": "https://images.unsplash.com/photo-1576941089067-2de3c901e126?w=800&h=400&fit=crop",
                "progress": 28,
                "duration_days": 21,
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
            "RPT-50002": {
                "memo_sent": "2026-02-04",
                "searches_ordered": "2026-02-05",
                "searches_received": "2026-02-08",
                "enquiries_raised": "2026-02-09",
                "enquiries_answered": None,
                "mortgage_offered": None,
                "survey_booked": "2026-02-06",
                "survey_complete": "2026-02-08",
                "exchange_target": "2026-04-15",
                "chain_info": "First-time buyer. Cash purchase — no mortgage.",
                "alert": None,
                "next_action": "Await enquiry responses from seller's solicitor.",
                "image_url": "https://images.unsplash.com/photo-1558036117-15d82a90b9b1?w=800&h=400&fit=crop",
                "progress": 52,
                "duration_days": 9,
                "milestones": [
                    {"label": "Offer Accepted",     "done": True},
                    {"label": "Memorandum Sent",     "done": True},
                    {"label": "Searches Ordered",    "done": True},
                    {"label": "Searches Received",   "done": True},
                    {"label": "Survey Complete",     "done": True},
                    {"label": "Enquiries Raised",    "done": True},
                    {"label": "Enquiries Answered",  "done": False},
                    {"label": "Mortgage Offer",      "done": None},  # Cash buyer — N/A
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
        GET {base_url}/offers?propertyId={property_id}&status=accepted
        → Gets buyer contact ID from the accepted offer
        GET {base_url}/contacts/{buyerContactId}
        → Gets buyer details

        GET {base_url}/conveyancing?propertyId={property_id}
        → Gets solicitor/conveyancer IDs
        GET {base_url}/contacts/{solicitorId}
        → Gets solicitor details

        Seller info from the property vendor/landlord contact.
        """
        # ── STUB: return contacts per property ───────────────
        contacts = {
            "RPT-50001": {
                "buyer": {
                    "name": "Mrs P. Henderson",
                    "phone": "07700 900555",
                    "email": "henderson@example.com",
                },
                "seller": {
                    "name": "Mr & Mrs Dalton",
                    "phone": "07700 900666",
                },
                "buyer_solicitor": {
                    "name": "Milne Moser, Kendal",
                    "phone": "01539 729786",
                },
                "seller_solicitor": {
                    "name": "Harrison Drury, Kendal",
                    "phone": "01539 735251",
                },
            },
            "RPT-50002": {
                "buyer": {
                    "name": "Mr J. Patel",
                    "phone": "07700 900777",
                    "email": "patel@example.com",
                },
                "seller": {
                    "name": "Miss A. Thompson",
                    "phone": "07700 900888",
                },
                "buyer_solicitor": {
                    "name": "Burnetts, Penrith",
                    "phone": "01768 890570",
                },
                "seller_solicitor": {
                    "name": "Cartmell Shepherd, Carlisle",
                    "phone": "01228 516666",
                },
            },
        }
        return contacts.get(property_id, {})

    # ─────────────────────────────────────────────────────────
    #  SYNC ALL — maps Reapit data → NUVU schema
    # ─────────────────────────────────────────────────────────

    def sync_all(self):
        """Full sync: authenticate, fetch, map to NUVU schema.

        Returns:
            list[dict]: Property dicts using NUVU DB column names.
        """
        if not self.authenticate():
            raise ConnectionError(f"Reapit authentication failed: {self.last_error}")

        raw_properties = self.get_properties()
        mapped = []

        for raw in raw_properties:
            pid = raw["property_id"]
            details = self.get_property_details(pid)
            contacts = self.get_contacts(pid)

            nuvu_status = self.REAPIT_STATUS_MAP.get(
                raw.get("status", "underOffer"), "on-track"
            )

            # Build card_checks from key milestones
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
                "slug": f"reapit-{pid.lower().replace('-', '')}",
                "source_connector": "reapit",
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

        print(f"  [reapit] Mapped {len(mapped)} properties to NUVU schema")
        return mapped

    # ─────────────────────────────────────────────────────────
    #  WRITE-BACK (OUTBOUND — NUVU → Reapit)
    # ─────────────────────────────────────────────────────────

    def push_note(self, crm_property_id, note_text, author, timestamp):
        """Push a note back to Reapit.

        REAL IMPLEMENTATION:
        ─────────────────────
        POST {base_url}/journalEntries
        Headers:
            Authorization: Bearer {access_token}
            api-version: 2023-10-01
            Content-Type: application/json
        Body:
            {
                "propertyId": crm_property_id,
                "typeId": "progression",
                "description": note_text,
                "negotiatorId": author_id
            }

        Reapit uses journal entries for notes — they appear in the
        property's activity feed within the CRM.
        """
        print(f"  [reapit] STUB push_note → {crm_property_id}: {note_text[:50]}...")
        return {"success": True, "crm_ref": None, "error": None}

    def push_milestone_update(self, crm_property_id, milestone_name,
                               is_complete, completed_date):
        """Push a milestone update back to Reapit.

        REAL IMPLEMENTATION:
        ─────────────────────
        PATCH {base_url}/conveyancing/{conveyancingId}
        Headers:
            Authorization: Bearer {access_token}
            api-version: 2023-10-01
            Content-Type: application/json-patch+json
            If-Match: {etag}
        Body:
            [
                {
                    "op": "replace",
                    "path": "/searchesApplied",
                    "value": completed_date
                }
            ]

        Reapit Conveyancing fields map to NUVU milestones:
            "Memorandum Sent"    → /instructionDate
            "Searches Ordered"   → /searchesApplied
            "Searches Received"  → /searchesReceived
            "Survey Complete"    → /surveyDate
            "Enquiries Raised"   → /enquiryRaised
            "Enquiries Answered" → /enquiryAnswered
            "Mortgage Offer"     → /mortgageOfferReceived
            "Exchange"           → /exchangeDate
            "Completion"         → /completionDate
        """
        status = "complete" if is_complete else "pending"
        print(f"  [reapit] STUB push_milestone → {crm_property_id}: {milestone_name} = {status}")
        return {"success": True, "crm_ref": None, "error": None}

    def push_status_change(self, crm_property_id, new_status, reason):
        """Push a status change back to Reapit.

        REAL IMPLEMENTATION:
        ─────────────────────
        PATCH {base_url}/properties/{crm_property_id}
        Headers:
            Authorization: Bearer {access_token}
            api-version: 2023-10-01
            Content-Type: application/json-patch+json
            If-Match: {etag}
        Body:
            [
                {
                    "op": "replace",
                    "path": "/selling/status",
                    "value": reapit_status
                }
            ]

        Reverse mapping: NUVU → Reapit:
            "on-track" → "underOffer"
            "at-risk"  → "underNegotiation"
            "stalled"  → "onHold"
        """
        print(f"  [reapit] STUB push_status → {crm_property_id}: {new_status} ({reason})")
        return {"success": True, "crm_ref": None, "error": None}

    def push_completion_summary(self, crm_property_id, summary):
        """Push a completion handback to Reapit.

        REAL IMPLEMENTATION:
        ─────────────────────
        POST {base_url}/journalEntries
        Body:
            {
                "propertyId": crm_property_id,
                "typeId": "completionSummary",
                "description": formatted_summary
            }

        Then also:
        PATCH {base_url}/conveyancing/{conveyancingId}
        Body:
            [{"op": "replace", "path": "/completionDate", "value": date}]

        The full NUVU progression history is posted as a journal entry
        and the conveyancing record is marked as completed.
        """
        duration = summary.get("duration_days", "?")
        print(f"  [reapit] STUB push_completion_summary → {crm_property_id}: {duration} days")
        return {"success": True, "crm_ref": None, "error": None}
