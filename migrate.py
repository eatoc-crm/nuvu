"""
NUVU — Migration Script
========================
Imports the hardcoded PROPERTIES list from app.py into the SQLite database.

Usage:
    python migrate.py          # migrate data
    python migrate.py --fresh  # drop & recreate DB first

This script is idempotent — it skips properties whose slug already exists.
"""

import sys
import os
import json

# Add project root so we can import app and database
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db, init_db, DB_PATH
from app import PROPERTIES


# ─────────────────────────────────────────────────────────────
#  MILESTONE STAGE MAPPING
#  Stage 1 = Pre-contract (early legal groundwork)
#  Stage 2 = Mid-progression (survey, enquiries, mortgage)
#  Stage 3 = Final (exchange & completion)
# ─────────────────────────────────────────────────────────────
MILESTONE_STAGES = {
    "Offer Accepted":       1,
    "Memorandum Sent":      1,
    "Searches Ordered":     1,
    "Searches Received":    1,
    "Survey Complete":      2,
    "Enquiries Raised":     2,
    "Enquiries Answered":   2,
    "Mortgage Offer":       2,
    "Exchange":             3,
    "Completion":           3,
}


def get_or_create_solicitor(db, name_with_location, phone):
    """Find or insert a solicitor, return the solicitor id."""
    if not name_with_location:
        return None

    # Split "Harper & Lane, Kendal" into firm + location
    parts = name_with_location.split(", ", 1)
    firm = parts[0].strip()
    location = parts[1].strip() if len(parts) > 1 else None

    row = db.execute(
        "SELECT id FROM solicitors WHERE name = ? AND phone = ?",
        (name_with_location, phone),
    ).fetchone()

    if row:
        return row["id"]

    cur = db.execute(
        "INSERT INTO solicitors (name, phone, firm, location) VALUES (?, ?, ?, ?)",
        (name_with_location, phone, firm, location),
    )
    return cur.lastrowid


def migrate_property(db, prop):
    """Insert a single property and its related records."""

    slug = prop["id"]

    # Skip if already migrated
    existing = db.execute(
        "SELECT id FROM properties WHERE slug = ?", (slug,)
    ).fetchone()
    if existing:
        print(f"  SKIP  {slug} (already exists)")
        return

    # ── Insert property ──────────────────────────────────────
    cur = db.execute(
        """INSERT INTO properties (
            slug, address, location, price, status,
            progress_percentage, duration_days, target_days, days_since_update,
            chain_position, alert, next_action,
            hero_image, image_bg, card_checks,
            offer_accepted_date, memo_sent_date,
            searches_ordered, searches_received,
            enquiries_raised, enquiries_answered,
            mortgage_offered, survey_booked, survey_complete,
            exchange_date, completion_date
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?,
            ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?
        )""",
        (
            slug,
            prop["address"],
            prop.get("location"),
            prop.get("price"),
            prop.get("status", "on-track"),
            prop.get("progress", 0),
            prop.get("duration_days", 0),
            prop.get("target_days", 60),
            prop.get("days_since_update", 0),
            prop.get("chain"),
            prop.get("alert"),
            prop.get("next_action"),
            prop.get("image_url"),
            prop.get("image_bg"),
            json.dumps(prop.get("card_checks", [])),
            prop.get("offer_date"),
            prop.get("memo_sent"),
            prop.get("searches_ordered"),
            prop.get("searches_received"),
            prop.get("enquiries_raised"),
            prop.get("enquiries_answered"),
            prop.get("mortgage_offered"),
            prop.get("survey_booked"),
            prop.get("survey_complete"),
            prop.get("exchange_target"),
            prop.get("completion_target"),
        ),
    )
    property_id = cur.lastrowid

    # ── Buyer solicitor ──────────────────────────────────────
    buyer_sol_id = get_or_create_solicitor(
        db, prop.get("buyer_solicitor"), prop.get("buyer_sol_phone")
    )

    # ── Insert buyer ─────────────────────────────────────────
    db.execute(
        """INSERT INTO buyers (property_id, name, phone, solicitor_id)
           VALUES (?, ?, ?, ?)""",
        (property_id, prop.get("buyer"), prop.get("buyer_phone"), buyer_sol_id),
    )

    # ── Seller solicitor ─────────────────────────────────────
    seller_sol_id = get_or_create_solicitor(
        db, prop.get("seller_solicitor"), prop.get("seller_sol_phone")
    )

    # ── Insert seller (name not in current data, placeholder) ─
    db.execute(
        """INSERT INTO sellers (property_id, solicitor_id)
           VALUES (?, ?)""",
        (property_id, seller_sol_id),
    )

    # ── Milestones ───────────────────────────────────────────
    for idx, ms in enumerate(prop.get("milestones", [])):
        label = ms["label"]
        done = ms["done"]
        stage = MILESTONE_STAGES.get(label, 2)

        # is_complete: True=1, False=0, None=NULL (N/A like cash buyer mortgage)
        if done is True:
            is_complete = 1
        elif done is None:
            is_complete = None
        else:
            is_complete = 0

        db.execute(
            """INSERT INTO milestones
               (property_id, milestone_name, milestone_stage, is_complete, sort_order)
               VALUES (?, ?, ?, ?, ?)""",
            (property_id, label, stage, is_complete, idx),
        )

    # ── Notes — seed from alert if present ───────────────────
    if prop.get("alert"):
        db.execute(
            """INSERT INTO notes (property_id, note_text, source)
               VALUES (?, ?, 'manual')""",
            (property_id, prop["alert"]),
        )

    print(f"  OK    {slug} — {prop['address']}, {prop.get('location', '')}")


def main():
    fresh = "--fresh" in sys.argv

    if fresh and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing database: {DB_PATH}")

    # Create tables
    init_db()
    print(f"Database ready at {DB_PATH}\n")

    db = get_db()

    print(f"Migrating {len(PROPERTIES)} properties...\n")

    for prop in PROPERTIES:
        migrate_property(db, prop)

    db.commit()

    # ── Summary ──────────────────────────────────────────────
    counts = {}
    for table in ["properties", "buyers", "sellers", "solicitors", "milestones", "notes"]:
        row = db.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()
        counts[table] = row["c"]

    print(f"\nMigration complete:")
    print(f"  Properties:  {counts['properties']}")
    print(f"  Buyers:      {counts['buyers']}")
    print(f"  Sellers:     {counts['sellers']}")
    print(f"  Solicitors:  {counts['solicitors']}")
    print(f"  Milestones:  {counts['milestones']}")
    print(f"  Notes:       {counts['notes']}")

    db.close()


if __name__ == "__main__":
    main()
