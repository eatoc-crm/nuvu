"""
NUVU — Supabase Database Connection
====================================
Connects to Supabase via the supabase-py HTTPS client.

Usage:
    from db_supabase import fetch_sales_progression, fetch_pipeline_data
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

_url = os.environ.get("SUPABASE_URL", "").strip()
_key = os.environ.get("SUPABASE_ANON_KEY", "").strip()
_service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

supabase = create_client(_url, _key)

# Columns PATCHable via /api/progression — keep aligned with routes/progression.py ALLOWED_PATCH_FIELDS
SALES_PROGRESSION_OVERLAY_COLS = (
    "offer_accepted",
    "memo_sent",
    "searches_ordered",
    "mortgage_offered",
    "enquiries_raised",
    "enquiries_answered",
    "exchange_date",
    "completion_date",
    "notes",
    "nuvu_notes",
    "buyer_solicitor_notes",
    "seller_solicitor_notes",
)


def supabase_for_backend():
    """Server-only client: prefer service role so RLS cannot silently block PATCH/SELECT.

    Never expose SUPABASE_SERVICE_ROLE_KEY to the browser — Flask env only.
    """
    if _url and _service_role_key:
        return create_client(_url, _service_role_key)
    return supabase


def fetch_sales_progression_overlay_by_ids(ids):
    """Return id -> row dict for merging milestone/note fields over EATOC API payloads."""
    seen = set()
    unique = []
    for i in ids or []:
        if i is None:
            continue
        s = str(i).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        unique.append(s)
    if not unique:
        return {}
    client = supabase_for_backend()
    select_cols = "id," + ",".join(SALES_PROGRESSION_OVERLAY_COLS)
    out = {}
    chunk_size = 80
    for off in range(0, len(unique), chunk_size):
        part = unique[off : off + chunk_size]
        try:
            res = (
                client.table("sales_progression")
                .select(select_cols)
                .in_("id", part)
                .execute()
            )
        except Exception:
            continue
        for row in res.data or []:
            rid = row.get("id")
            if rid is not None:
                out[str(rid)] = row
    return out


def fetch_sales_progression(status_filter=None):
    """Fetch sales progression records from Supabase.

    Args:
        status_filter: Optional status string or list of statuses to filter by.

    Returns:
        List of dicts, one per row.
    """
    query = supabase.table("sales_progression").select("*")
    if status_filter:
        if isinstance(status_filter, str):
            status_filter = [status_filter]
        query = query.in_("status", status_filter)
    query = query.order("created_at", desc=True)
    return query.execute().data


def fetch_pipeline_data():
    """Fetch pipeline table data for fee/value forecasting."""
    return (
        supabase.table("pipeline")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
    )


def fetch_sales_pipeline():
    """Fetch all records from sales_pipeline table."""
    return (
        supabase.table("sales_pipeline")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
    )


def fetch_solicitors():
    """Fetch all solicitors."""
    return (
        supabase.table("solicitors")
        .select("*")
        .order("firm_name")
        .execute()
        .data
    )


def fetch_property_images():
    """Fetch image columns from properties table for card thumbnails."""
    return (
        supabase.table("properties")
        .select("id,ref,address,image_url,photo_urls")
        .execute()
        .data
    )


def fetch_chain_links():
    """Fetch all chain link records from Supabase."""
    return (
        supabase.table("chain_links")
        .select("*")
        .limit(1000)
        .execute()
        .data
    )


def fetch_sales_progression_recent(limit=80):
    """Recent sales_progression rows (Supabase) for portal and similar views."""
    return (
        supabase.table("sales_progression")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )
