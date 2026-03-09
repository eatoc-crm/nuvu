"""
NUVU — Base Connector
======================
Abstract base class that all CRM connectors must implement.

Every estate agency CRM (Alto, Reapit, Street, Dezrez, Loop, etc.) will
have its own connector class inheriting from BaseConnector.  The interface
is standardised so the sync pipeline doesn't care which CRM is behind it.

Two-way sync:
  INBOUND  (CRM → NUVU):  sync_all() pulls property data into NUVU
  OUTBOUND (NUVU → CRM):  push_note / push_milestone_update /
                           push_status_change / push_completion_summary
"""

from abc import ABC, abstractmethod


class BaseConnector(ABC):
    """Standard interface for CRM connectors.

    Subclasses must implement all abstract methods.  The connector is
    responsible for:
      1. Authenticating with the CRM's API
      2. Fetching property and contact data (inbound)
      3. Mapping CRM-specific fields to NUVU's database schema
      4. Returning data in the format expected by sync_to_database.py
      5. Writing notes, milestones, status changes back to the CRM (outbound)
    """

    def __init__(self):
        self.name = "base"
        self.display_name = "Base Connector"
        self.is_connected = False
        self.last_error = None
        self.supports_writeback = False  # Set True when CRM supports outbound

    # ─────────────────────────────────────────────────────────
    #  AUTHENTICATION
    # ─────────────────────────────────────────────────────────

    @abstractmethod
    def authenticate(self):
        """Connect to the CRM API and obtain an auth token.

        Returns:
            bool: True if authentication succeeded, False otherwise.

        On failure, should set self.last_error with a description.
        """
        pass

    # ─────────────────────────────────────────────────────────
    #  DATA RETRIEVAL (INBOUND — CRM → NUVU)
    # ─────────────────────────────────────────────────────────

    @abstractmethod
    def get_properties(self):
        """Fetch a list of all properties from the CRM.

        Returns:
            list[dict]: Each dict contains CRM-native property fields.
                        The connector's sync_all() is responsible for
                        mapping these to NUVU's schema.
        """
        pass

    @abstractmethod
    def get_property_details(self, property_id):
        """Fetch full details for a single property.

        Args:
            property_id: The CRM's identifier for the property.

        Returns:
            dict: Full property details in CRM-native format.
        """
        pass

    @abstractmethod
    def get_contacts(self, property_id):
        """Fetch buyer, seller, and solicitor contacts for a property.

        Args:
            property_id: The CRM's identifier for the property.

        Returns:
            dict: With keys 'buyer', 'seller', 'buyer_solicitor',
                  'seller_solicitor' — each a dict of contact fields.
        """
        pass

    # ─────────────────────────────────────────────────────────
    #  FULL SYNC (INBOUND)
    # ─────────────────────────────────────────────────────────

    @abstractmethod
    def sync_all(self):
        """Run a full sync: authenticate, fetch all data, and return
        property dicts mapped to NUVU's database schema.

        This is the main entry point called by ConnectorManager.

        Each property dict MUST include:
            source_connector:  connector name (e.g. "alto", "reapit")
            source_crm_id:     the property's ID in the originating CRM

        Returns:
            list[dict]: Property dicts using NUVU DB field names:
                slug, address, location, price, status,
                progress_percentage, duration_days, target_days,
                chain_position, alert, next_action,
                hero_image, image_bg, card_checks (JSON string),
                offer_accepted_date, memo_sent_date, ...
                source_connector, source_crm_id,
                Plus nested 'buyer', 'seller', 'milestones' keys.
        """
        pass

    # ─────────────────────────────────────────────────────────
    #  WRITE-BACK (OUTBOUND — NUVU → CRM)
    # ─────────────────────────────────────────────────────────

    @abstractmethod
    def push_note(self, crm_property_id, note_text, author, timestamp):
        """Push a note/journal entry back to the CRM.

        Args:
            crm_property_id:  The property's ID in the CRM system
            note_text:        The note content to push
            author:           Who wrote the note (e.g. "Agent", "AI Parser")
            timestamp:        When the note was created (ISO format string)

        Returns:
            dict: {"success": bool, "crm_ref": str|None, "error": str|None}
        """
        pass

    @abstractmethod
    def push_milestone_update(self, crm_property_id, milestone_name,
                               is_complete, completed_date):
        """Push a milestone completion update back to the CRM.

        Args:
            crm_property_id:  The property's ID in the CRM system
            milestone_name:   NUVU milestone name (e.g. "Searches Received")
            is_complete:      True/False/None
            completed_date:   Date string (YYYY-MM-DD) or None

        Returns:
            dict: {"success": bool, "crm_ref": str|None, "error": str|None}
        """
        pass

    @abstractmethod
    def push_status_change(self, crm_property_id, new_status, reason):
        """Push a status change back to the CRM.

        Args:
            crm_property_id:  The property's ID in the CRM system
            new_status:       NUVU status: "on-track", "at-risk", "stalled"
            reason:           Human-readable reason for the change

        Returns:
            dict: {"success": bool, "crm_ref": str|None, "error": str|None}
        """
        pass

    @abstractmethod
    def push_completion_summary(self, crm_property_id, summary):
        """Push a completion handback package to the CRM.

        Called when a property reaches Completion.  Packages the entire
        NUVU transaction history (milestones, notes, timeline) and sends
        it back to the CRM as a final handback.

        Args:
            crm_property_id:  The property's ID in the CRM system
            summary:          dict with keys:
                - milestones:   list of milestone dicts with dates
                - notes:        list of note dicts
                - timeline:     list of key events with dates
                - duration_days: total days from offer to completion
                - status_history: list of status changes

        Returns:
            dict: {"success": bool, "crm_ref": str|None, "error": str|None}
        """
        pass
