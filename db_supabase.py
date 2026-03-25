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

_url = os.environ.get("SUPABASE_URL", "")
_key = os.environ.get("SUPABASE_ANON_KEY", "")
supabase = create_client(_url, _key)


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


def fetch_solicitors():
    """Fetch all solicitors."""
    return (
        supabase.table("solicitors")
        .select("*")
        .order("firm_name")
        .execute()
        .data
    )
