"""Adapter sync: keeps NUVU's local sales_pipeline and chain_links tables
up to date from the EATOC read API.

Runs on server startup (once, after a short delay) and then every 15 minutes
inside the same background thread as the chase cadence (see chase_scheduler.py).

Design:
  - GET /api/nuvu/properties  → upsert into sales_pipeline
  - GET /api/nuvu/chain-links → upsert into chain_links
  - If either API call fails, log a warning; don't raise — partial syncs are OK.
  - EATOC API is source of truth. Local tables are read caches only.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

LOCAL_ONLY_PIPELINE_FIELDS = {"do_not_chase"}


def _enrich_solicitor_fields(rows: list) -> None:
    """Mutate each row in-place with solicitor contact/company data from EATOC.

    Collects unique company and contact UUIDs across the batch, makes one lookup
    per unique ID, then applies the results — avoiding duplicate calls when multiple
    properties share the same solicitor firm.

    Failures are silently logged; a lookup error never blocks the sync.
    """
    from utils.eatoc_api import eatoc_get_company, eatoc_get_contact

    # Collect unique UUIDs
    company_ids: set[str] = set()
    contact_ids: set[str] = set()
    for r in rows:
        for field in ("buyer_solicitor_firm_id", "seller_solicitor_firm_id"):
            val = (r.get(field) or "").strip()
            if val:
                company_ids.add(val)
        for field in ("buyer_solicitor_contact_id", "seller_solicitor_contact_id"):
            val = (r.get(field) or "").strip()
            if val:
                contact_ids.add(val)

    # Batch lookup (one call per unique ID)
    company_cache: dict[str, dict] = {}
    for cid in company_ids:
        result = eatoc_get_company(cid)
        if result:
            company_cache[cid] = result

    contact_cache: dict[str, dict] = {}
    for cid in contact_ids:
        result = eatoc_get_contact(cid)
        if result:
            contact_cache[cid] = result

    log.info(
        "[adapter_sync] solicitor enrichment: %d companies, %d contacts fetched",
        len(company_cache), len(contact_cache),
    )

    # Apply to each row
    for r in rows:
        for side, firm_field, contact_field, email_key, phone_key, addr_key, contact_name_key in (
            (
                "buyer",
                "buyer_solicitor_firm_id",
                "buyer_solicitor_contact_id",
                "buyer_solicitor_email",
                "buyer_solicitor_phone",
                "buyer_solicitor_address",
                "buyer_solicitor_contact_name",
            ),
            (
                "seller",
                "seller_solicitor_firm_id",
                "seller_solicitor_contact_id",
                "seller_solicitor_email",
                "seller_solicitor_phone",
                "seller_solicitor_address",
                "seller_solicitor_contact_name",
            ),
        ):
            firm_id = (r.get(firm_field) or "").strip()
            contact_id = (r.get(contact_field) or "").strip()

            company = company_cache.get(firm_id) if firm_id else None
            contact = contact_cache.get(contact_id) if contact_id else None

            r[email_key] = (
                (contact or {}).get("email")
                or (company or {}).get("email")
                or r.get(email_key)
                or None
            )
            r[phone_key] = (
                (contact or {}).get("phone")
                or (company or {}).get("phone")
                or None
            )
            r[addr_key] = (company or {}).get("address") or None
            r[contact_name_key] = (contact or {}).get("name") or None


def _build_pipeline_row(r: dict) -> dict:
    """Map a raw EATOC property dict to a sales_pipeline upsert row."""
    addr = (r.get("property_address") or "").strip()
    return {
        "property_address":              addr,
        "alto_ref":                      r.get("alto_ref") or None,
        "our_ref":                       r.get("our_ref") or None,
        "postcode":                      r.get("postcode") or None,
        "status":                        r.get("status") or None,
        "date_agreed":                   r.get("date_agreed") or r.get("offer_accepted") or None,
        "current_price":                 r.get("current_price") or r.get("sale_price") or None,
        "est_exchange":                  r.get("est_exchange") or None,
        "exchange_date":                 r.get("exchange_date") or None,
        "est_completion":                r.get("est_completion") or r.get("completion_target") or None,
        "fee":                           r.get("fee") or None,
        "fee_pct":                       r.get("fee_pct") or None,
        "agreed_fee":                    r.get("agreed_fee") or None,
        "buyers_solicitor":              r.get("buyers_solicitor") or r.get("buyer_solicitor") or None,
        "vendors_solicitor":             r.get("vendors_solicitor") or r.get("vendor_solicitor") or None,
        "negotiator":                    r.get("negotiator") or r.get("negotiator_name") or None,
        "agreed_by":                     r.get("agreed_by") or None,
        "buyer_name":                    r.get("buyer_name") or None,
        "buyer_phone":                   r.get("buyer_phone") or None,
        "buyer_email":                   r.get("buyer_email") or None,
        "vendor_name":                   r.get("vendor_name") or None,
        "vendor_phone":                  r.get("vendor_phone") or None,
        "vendor_email":                  r.get("vendor_email") or None,
        "mortgage_broker":               r.get("mortgage_broker") or None,
        "surveyor":                      r.get("surveyor") or None,
        # Solicitor email (enriched by _enrich_solicitor_fields or raw EATOC fallback)
        "buyer_solicitor_email":         r.get("buyer_solicitor_email") or None,
        "seller_solicitor_email":        r.get("seller_solicitor_email") or None,
        # Enriched solicitor contact fields
        "buyer_solicitor_contact_name":  r.get("buyer_solicitor_contact_name") or None,
        "buyer_solicitor_phone":         r.get("buyer_solicitor_phone") or None,
        "buyer_solicitor_address":       r.get("buyer_solicitor_address") or None,
        "seller_solicitor_contact_name": r.get("seller_solicitor_contact_name") or None,
        "seller_solicitor_phone":        r.get("seller_solicitor_phone") or None,
        "seller_solicitor_address":      r.get("seller_solicitor_address") or None,
    }


def _strip_local_only_pipeline_fields(row: dict) -> dict:
    """Keep NUVU-owned flags out of EATOC cache upserts."""
    for field in LOCAL_ONLY_PIPELINE_FIELDS:
        row.pop(field, None)
    return row


def sync_sales_pipeline() -> None:
    """Fetch all properties from EATOC and upsert into local sales_pipeline."""
    try:
        from utils.eatoc_live_map import fetch_eatoc_properties

        rows, error = fetch_eatoc_properties()
        if error:
            log.warning("[adapter_sync] fetch_eatoc_properties error: %s", error)
            return
        if not rows:
            log.info("[adapter_sync] sales_pipeline sync: no rows returned from EATOC")
            return

        # Enrich each property with solicitor firm/contact details from EATOC
        try:
            _enrich_solicitor_fields(rows)
        except Exception as exc:
            log.warning("[adapter_sync] solicitor enrichment failed (continuing): %s", exc)

        from db_supabase import supabase_for_backend

        client = supabase_for_backend()
        upserted = 0
        skipped = 0
        for r in rows:
            addr = (r.get("property_address") or "").strip()
            if not addr:
                skipped += 1
                continue
            row = _strip_local_only_pipeline_fields(_build_pipeline_row(r))
            try:
                client.table("sales_pipeline").upsert(
                    row, on_conflict="property_address"
                ).execute()
                upserted += 1
            except Exception as exc:
                log.warning(
                    "[adapter_sync] sales_pipeline upsert failed for '%s': %s", addr, exc
                )
        log.info(
            "[adapter_sync] sales_pipeline sync complete — %d upserted, %d skipped",
            upserted, skipped,
        )
    except Exception as exc:
        log.warning("[adapter_sync] sync_sales_pipeline unexpected error: %s", exc)


def sync_single_property(property_address: str) -> None:
    """Fetch one property from EATOC and upsert it into sales_pipeline.

    Called by the webhook receiver when EATOC fires a real-time notification.
    Does NOT trigger a full pipeline sync — only the changed property is touched.
    After upsert, runs the completeness gate for that property only.
    """
    property_address = property_address.strip()
    if not property_address:
        log.warning("[adapter_sync] sync_single_property called with empty address")
        return

    try:
        from utils.eatoc_live_map import fetch_eatoc_properties

        rows, error = fetch_eatoc_properties()
        if error:
            log.warning(
                "[adapter_sync] sync_single_property fetch error for '%s': %s",
                property_address, error,
            )
            return

        target = next(
            (r for r in (rows or [])
             if (r.get("property_address") or "").strip() == property_address),
            None,
        )
        if target is None:
            log.info(
                "[adapter_sync] sync_single_property: '%s' not found in EATOC response",
                property_address,
            )
            return

        try:
            _enrich_solicitor_fields([target])
        except Exception as exc:
            log.warning(
                "[adapter_sync] solicitor enrichment failed for '%s' (continuing): %s",
                property_address, exc,
            )

        from db_supabase import supabase_for_backend

        client = supabase_for_backend()
        row = _strip_local_only_pipeline_fields(_build_pipeline_row(target))
        client.table("sales_pipeline").upsert(row, on_conflict="property_address").execute()
        log.info("[adapter_sync] sync_single_property: upserted '%s'", property_address)

        # Run completeness gate for this property only
        try:
            from utils.completeness_gate import run_completeness_gate_for_address
            run_completeness_gate_for_address(property_address)
        except Exception as exc:
            log.warning(
                "[adapter_sync] completeness gate error for '%s': %s", property_address, exc
            )

    except Exception as exc:
        log.warning(
            "[adapter_sync] sync_single_property unexpected error for '%s': %s",
            property_address, exc,
        )


def sync_chain_links() -> None:
    """Fetch chain links from EATOC and upsert into local chain_links."""
    try:
        from utils.eatoc_api import eatoc_get
        import os

        base = os.environ.get("EATOC_API_BASE", "https://app.eatoc.co.uk")
        rows = eatoc_get("/api/nuvu/chain-links")
        if not isinstance(rows, list):
            rows = rows.get("chain_links") or rows.get("data") or []
        if not rows:
            log.info("[adapter_sync] chain_links sync: no rows returned from EATOC")
            return

        from db_supabase import supabase_for_backend

        client = supabase_for_backend()
        upserted = 0
        skipped = 0
        for r in rows:
            row_id = (r.get("id") or "").strip()
            if not row_id:
                skipped += 1
                continue
            row = {
                "id":                       row_id,
                "property_id":              r.get("property_id") or None,
                "link_address":             r.get("link_address") or None,
                "chain_position":           r.get("chain_position") or None,
                "buyer_name":               r.get("buyer_name") or None,
                "buyer_phone":              r.get("buyer_phone") or None,
                "buyer_email":              r.get("buyer_email") or None,
                "seller_name":              r.get("seller_name") or None,
                "seller_phone":             r.get("seller_phone") or None,
                "seller_email":             r.get("seller_email") or None,
                "estate_agent":             r.get("estate_agent") or None,
                "buyer_solicitor":          r.get("buyer_solicitor") or None,
                "seller_solicitor":         r.get("seller_solicitor") or None,
                "status":                   r.get("status") or None,
                "notes":                    r.get("notes") or None,
                "estate_agent_email":       r.get("estate_agent_email") or None,
                "estate_agent_phone":       r.get("estate_agent_phone") or None,
                "solicitor_details_requested": r.get("solicitor_details_requested") or False,
                "solicitor_details_received":  r.get("solicitor_details_received") or False,
                "nuvu_introduced":          r.get("nuvu_introduced") or False,
                "price":                    r.get("price") or None,
                "solicitor_firm":           r.get("solicitor_firm") or None,
                "solicitor_phone":          r.get("solicitor_phone") or None,
                "solicitor_email":          r.get("solicitor_email") or None,
                "solicitor_status":         r.get("solicitor_status") or "not_set",
            }
            try:
                client.table("chain_links").upsert(
                    row, on_conflict="id"
                ).execute()
                upserted += 1
            except Exception as exc:
                log.warning(
                    "[adapter_sync] chain_links upsert failed for id '%s': %s", row_id, exc
                )
        log.info(
            "[adapter_sync] chain_links sync complete — %d upserted, %d skipped",
            upserted, skipped,
        )
    except Exception as exc:
        log.warning("[adapter_sync] sync_chain_links unexpected error: %s", exc)


def run_adapter_sync() -> None:
    """Run both property and chain-link syncs, then evaluate the completeness gate.
    Called by chase_scheduler on the 15-minute loop and once at startup."""
    log.info("[adapter_sync] starting adapter sync")
    sync_sales_pipeline()
    sync_chain_links()
    log.info("[adapter_sync] adapter sync complete")

    # Completeness gate — runs after every sync; fail silently
    try:
        from utils.completeness_gate import run_completeness_gate
        run_completeness_gate()
    except Exception as exc:
        log.warning("[adapter_sync] completeness gate error: %s", exc)
