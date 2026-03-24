"""
NUVU — Supabase Database Connection
====================================
Connects to the Supabase PostgreSQL database using credentials
from environment variables (loaded via .env for local dev).

Usage:
    from db_supabase import get_connection, fetch_sales_progression
"""

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Return a psycopg2 connection to the Supabase database."""
    return psycopg2.connect(
        host=os.environ.get("SUPABASE_DB_HOST", "db.grosqsxnwhuvazgbjwan.supabase.co"),
        port=os.environ.get("SUPABASE_DB_PORT", "5432"),
        dbname=os.environ.get("SUPABASE_DB_NAME", "postgres"),
        user=os.environ.get("SUPABASE_DB_USER", "postgres"),
        password=os.environ.get("SUPABASE_DB_PASSWORD", ""),
        sslmode="require",
    )


def fetch_sales_progression(status_filter=None):
    """Fetch sales progression records from Supabase.

    Args:
        status_filter: Optional status string or list of statuses to filter by.
                      e.g. 'active' or ['active', 'exchanged', 'problem']

    Returns:
        List of dicts, one per row.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if status_filter:
                if isinstance(status_filter, str):
                    status_filter = [status_filter]
                cur.execute(
                    "SELECT * FROM sales_progression WHERE status IN %s ORDER BY created_at DESC",
                    (tuple(status_filter),),
                )
            else:
                cur.execute("SELECT * FROM sales_progression ORDER BY created_at DESC")
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def fetch_pipeline_data():
    """Fetch pipeline table data for fee/value forecasting."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM pipeline ORDER BY created_at DESC")
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def fetch_solicitors():
    """Fetch all solicitors."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM solicitors ORDER BY firm_name")
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
