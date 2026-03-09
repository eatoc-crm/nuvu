"""
NUVU Sales Progression — Database Schema
==========================================
SQLite database with tables for properties, buyers, sellers,
solicitors, milestones, and notes.

Usage:
    from database import get_db, init_db

    # Create tables (safe to call multiple times)
    init_db()

    # Get a connection for queries
    db = get_db()
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nuvu.db")


def get_db(path=None):
    """Return a sqlite3 connection with foreign keys enabled."""
    db = sqlite3.connect(path or DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    db.row_factory = sqlite3.Row
    return db


def init_db(path=None):
    """Create all tables if they don't already exist."""
    db = get_db(path)
    cur = db.cursor()

    cur.executescript("""

    -- ─────────────────────────────────────────────────────────
    --  SOLICITORS
    -- ─────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS solicitors (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL,
        phone       TEXT,
        email       TEXT,
        firm        TEXT,
        location    TEXT,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
        UNIQUE(name, phone)
    );

    -- ─────────────────────────────────────────────────────────
    --  PROPERTIES
    -- ─────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS properties (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        slug                TEXT    NOT NULL UNIQUE,
        address             TEXT    NOT NULL,
        location            TEXT,
        price               INTEGER,
        bedrooms            INTEGER,
        status              TEXT    NOT NULL DEFAULT 'on-track'
                            CHECK (status IN ('on-track', 'at-risk', 'stalled')),
        progress_percentage INTEGER DEFAULT 0,
        duration_days       INTEGER DEFAULT 0,
        target_days         INTEGER DEFAULT 60,
        days_since_update   INTEGER DEFAULT 0,
        chain_position      TEXT,
        alert               TEXT,
        next_action         TEXT,
        hero_image          TEXT,
        image_bg            TEXT,
        card_checks         TEXT,
        offer_accepted_date TEXT,
        memo_sent_date      TEXT,
        searches_ordered    TEXT,
        searches_received   TEXT,
        enquiries_raised    TEXT,
        enquiries_answered  TEXT,
        mortgage_offered    TEXT,
        survey_booked       TEXT,
        survey_complete     TEXT,
        exchange_date       TEXT,
        completion_date     TEXT,
        created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
        updated_at          TEXT    NOT NULL DEFAULT (datetime('now'))
    );

    -- ─────────────────────────────────────────────────────────
    --  BUYERS
    -- ─────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS buyers (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id     INTEGER NOT NULL,
        name            TEXT    NOT NULL,
        phone           TEXT,
        email           TEXT,
        solicitor_id    INTEGER,
        mortgage_broker TEXT,
        created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (property_id)  REFERENCES properties(id) ON DELETE CASCADE,
        FOREIGN KEY (solicitor_id) REFERENCES solicitors(id) ON DELETE SET NULL
    );

    -- ─────────────────────────────────────────────────────────
    --  SELLERS
    -- ─────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS sellers (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id     INTEGER NOT NULL,
        name            TEXT,
        phone           TEXT,
        email           TEXT,
        solicitor_id    INTEGER,
        created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (property_id)  REFERENCES properties(id) ON DELETE CASCADE,
        FOREIGN KEY (solicitor_id) REFERENCES solicitors(id) ON DELETE SET NULL
    );

    -- ─────────────────────────────────────────────────────────
    --  MILESTONES
    -- ─────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS milestones (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id     INTEGER NOT NULL,
        milestone_name  TEXT    NOT NULL,
        milestone_stage INTEGER NOT NULL CHECK (milestone_stage BETWEEN 1 AND 3),
        is_complete     INTEGER DEFAULT 0,
        completed_date  TEXT,
        sort_order      INTEGER NOT NULL DEFAULT 0,
        created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    );

    -- ─────────────────────────────────────────────────────────
    --  NOTES
    -- ─────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS notes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id     INTEGER NOT NULL,
        note_text       TEXT    NOT NULL,
        author          TEXT    NOT NULL DEFAULT 'Agent',
        is_urgent       INTEGER NOT NULL DEFAULT 0,
        created_date    TEXT    NOT NULL DEFAULT (datetime('now')),
        source          TEXT    NOT NULL DEFAULT 'manual'
                        CHECK (source IN ('manual', 'api', 'email')),
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    );

    -- ─────────────────────────────────────────────────────────
    --  SYNC LOG (inbound + outbound)
    -- ─────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS sync_log (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        connector_name      TEXT    NOT NULL,
        direction           TEXT    NOT NULL DEFAULT 'inbound'
                            CHECK (direction IN ('inbound', 'outbound')),
        started_at          TEXT    NOT NULL DEFAULT (datetime('now')),
        finished_at         TEXT,
        status              TEXT    NOT NULL DEFAULT 'running'
                            CHECK (status IN ('running', 'success', 'error')),
        properties_synced   INTEGER DEFAULT 0,
        properties_created  INTEGER DEFAULT 0,
        properties_updated  INTEGER DEFAULT 0,
        error_message       TEXT,
        created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
    );

    -- ─────────────────────────────────────────────────────────
    --  OUTBOUND SYNC QUEUE
    -- ─────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS outbound_sync_queue (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id     INTEGER NOT NULL,
        event_type      TEXT    NOT NULL
                        CHECK (event_type IN ('note','milestone','status','completion')),
        payload         TEXT    NOT NULL,
        status          TEXT    NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','sent','failed','skipped')),
        connector_name  TEXT,
        error_message   TEXT,
        created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
        processed_at    TEXT,
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    );

    -- ─────────────────────────────────────────────────────────
    --  EMAIL LOG
    -- ─────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS email_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id     INTEGER NOT NULL,
        email_type      TEXT    NOT NULL,
        recipient_type  TEXT    NOT NULL
                        CHECK (recipient_type IN ('solicitor','buyer','seller','broker')),
        recipient_name  TEXT,
        subject         TEXT    NOT NULL,
        body_text       TEXT    NOT NULL,
        tone            TEXT    NOT NULL DEFAULT 'professional'
                        CHECK (tone IN ('friendly','professional','firm')),
        status          TEXT    NOT NULL DEFAULT 'drafted'
                        CHECK (status IN ('drafted','copied','sent')),
        created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    );

    -- ─────────────────────────────────────────────────────────
    --  EMAIL PREFERENCES
    -- ─────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS email_preferences (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        preference_key   TEXT    NOT NULL UNIQUE,
        preference_value TEXT    NOT NULL,
        updated_at       TEXT    NOT NULL DEFAULT (datetime('now'))
    );

    -- ─────────────────────────────────────────────────────────
    --  INDEXES
    -- ─────────────────────────────────────────────────────────
    CREATE INDEX IF NOT EXISTS idx_properties_status   ON properties(status);
    CREATE INDEX IF NOT EXISTS idx_properties_slug     ON properties(slug);
    CREATE INDEX IF NOT EXISTS idx_buyers_property     ON buyers(property_id);
    CREATE INDEX IF NOT EXISTS idx_sellers_property    ON sellers(property_id);
    CREATE INDEX IF NOT EXISTS idx_milestones_property ON milestones(property_id);
    CREATE INDEX IF NOT EXISTS idx_notes_property      ON notes(property_id);
    CREATE INDEX IF NOT EXISTS idx_notes_created       ON notes(created_date);
    CREATE INDEX IF NOT EXISTS idx_sync_log_connector  ON sync_log(connector_name);
    CREATE INDEX IF NOT EXISTS idx_outbound_queue_status ON outbound_sync_queue(status);
    CREATE INDEX IF NOT EXISTS idx_outbound_queue_property ON outbound_sync_queue(property_id);
    CREATE INDEX IF NOT EXISTS idx_email_log_property  ON email_log(property_id);
    CREATE INDEX IF NOT EXISTS idx_email_log_type      ON email_log(email_type);

    """)

    # ─────────────────────────────────────────────────────────
    #  ADD NEW COLUMNS (safe ALTER TABLE — SQLite ignores if exists)
    # ─────────────────────────────────────────────────────────
    # These add source tracking columns to the properties table
    # so we know which CRM each property came from.
    _safe_add_column(cur, "properties", "source_connector", "TEXT")
    _safe_add_column(cur, "properties", "source_crm_id", "TEXT")

    # Completion engine fields on properties table
    _safe_add_column(cur, "properties", "buyer_type", "TEXT")
    _safe_add_column(cur, "properties", "chain_length", "INTEGER")
    _safe_add_column(cur, "properties", "property_type",
                     "TEXT DEFAULT 'freehold'")
    _safe_add_column(cur, "properties", "mortgage_type", "TEXT")
    _safe_add_column(cur, "properties", "solicitor_type", "TEXT")

    # Add direction column to sync_log if migrating from old schema
    _safe_add_column(cur, "sync_log", "direction",
                     "TEXT NOT NULL DEFAULT 'inbound'")

    # Create index on direction (must be after column is added)
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sync_log_direction ON sync_log(direction)")
    except Exception:
        pass

    db.commit()
    db.close()


def _safe_add_column(cursor, table, column, col_type):
    """Add a column to a table if it doesn't already exist.

    SQLite doesn't support IF NOT EXISTS on ALTER TABLE ADD COLUMN,
    so we check the pragma first.
    """
    cols = [row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except Exception:
            pass  # Column may already exist in some edge cases


if __name__ == "__main__":
    init_db()
    print(f"Database created at {DB_PATH}")
