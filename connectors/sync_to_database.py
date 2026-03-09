"""
NUVU — Sync to Database
=========================
Takes mapped property data from any connector and writes it into the
SQLite database.  Handles upserts (create or update) for properties,
buyers, sellers, solicitors, and milestones.

This module is connector-agnostic — it only cares about the NUVU
database schema.  The connector is responsible for mapping its
CRM-native fields to our schema before calling write_sync_data().
"""

import json
from datetime import datetime


# ─────────────────────────────────────────────────────────────
#  MILESTONE STAGE MAPPING (same as migrate.py)
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


def get_or_create_solicitor(db, name, phone):
    """Find or insert a solicitor, return the solicitor id.

    Deduplicates on (name, phone) — same logic as migrate.py.
    """
    if not name:
        return None

    parts = name.split(", ", 1)
    firm = parts[0].strip()
    location = parts[1].strip() if len(parts) > 1 else None

    row = db.execute(
        "SELECT id FROM solicitors WHERE name = ? AND phone = ?",
        (name, phone),
    ).fetchone()

    if row:
        return row["id"]

    cur = db.execute(
        "INSERT INTO solicitors (name, phone, firm, location) VALUES (?, ?, ?, ?)",
        (name, phone, firm, location),
    )
    return cur.lastrowid


def _upsert_property(db, prop):
    """Insert or update a property row.  Returns (property_db_id, is_new)."""
    slug = prop["slug"]

    existing = db.execute(
        "SELECT id FROM properties WHERE slug = ?", (slug,)
    ).fetchone()

    if existing:
        # Update existing property
        db.execute(
            """UPDATE properties SET
                address = ?, location = ?, price = ?, bedrooms = ?,
                status = ?, progress_percentage = ?,
                duration_days = ?, target_days = ?, days_since_update = ?,
                chain_position = ?, alert = ?, next_action = ?,
                hero_image = ?, image_bg = ?, card_checks = ?,
                offer_accepted_date = ?, memo_sent_date = ?,
                searches_ordered = ?, searches_received = ?,
                enquiries_raised = ?, enquiries_answered = ?,
                mortgage_offered = ?, survey_booked = ?, survey_complete = ?,
                exchange_date = ?, completion_date = ?,
                source_connector = ?, source_crm_id = ?,
                updated_at = datetime('now')
            WHERE slug = ?""",
            (
                prop.get("address"), prop.get("location"),
                prop.get("price"), prop.get("bedrooms"),
                prop.get("status", "on-track"), prop.get("progress_percentage", 0),
                prop.get("duration_days", 0), prop.get("target_days", 60),
                prop.get("days_since_update", 0),
                prop.get("chain_position"), prop.get("alert"), prop.get("next_action"),
                prop.get("hero_image"), prop.get("image_bg"), prop.get("card_checks"),
                prop.get("offer_accepted_date"), prop.get("memo_sent_date"),
                prop.get("searches_ordered"), prop.get("searches_received"),
                prop.get("enquiries_raised"), prop.get("enquiries_answered"),
                prop.get("mortgage_offered"), prop.get("survey_booked"),
                prop.get("survey_complete"),
                prop.get("exchange_date"), prop.get("completion_date"),
                prop.get("source_connector"), prop.get("source_crm_id"),
                slug,
            ),
        )
        return existing["id"], False
    else:
        # Insert new property
        cur = db.execute(
            """INSERT INTO properties (
                slug, address, location, price, bedrooms,
                status, progress_percentage,
                duration_days, target_days, days_since_update,
                chain_position, alert, next_action,
                hero_image, image_bg, card_checks,
                offer_accepted_date, memo_sent_date,
                searches_ordered, searches_received,
                enquiries_raised, enquiries_answered,
                mortgage_offered, survey_booked, survey_complete,
                exchange_date, completion_date,
                source_connector, source_crm_id
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?
            )""",
            (
                slug, prop.get("address"), prop.get("location"),
                prop.get("price"), prop.get("bedrooms"),
                prop.get("status", "on-track"), prop.get("progress_percentage", 0),
                prop.get("duration_days", 0), prop.get("target_days", 60),
                prop.get("days_since_update", 0),
                prop.get("chain_position"), prop.get("alert"), prop.get("next_action"),
                prop.get("hero_image"), prop.get("image_bg"), prop.get("card_checks"),
                prop.get("offer_accepted_date"), prop.get("memo_sent_date"),
                prop.get("searches_ordered"), prop.get("searches_received"),
                prop.get("enquiries_raised"), prop.get("enquiries_answered"),
                prop.get("mortgage_offered"), prop.get("survey_booked"),
                prop.get("survey_complete"),
                prop.get("exchange_date"), prop.get("completion_date"),
                prop.get("source_connector"), prop.get("source_crm_id"),
            ),
        )
        return cur.lastrowid, True


def _upsert_buyer(db, property_id, buyer_data, solicitor_id):
    """Insert or update the buyer for a property."""
    if not buyer_data:
        return

    existing = db.execute(
        "SELECT id FROM buyers WHERE property_id = ?", (property_id,)
    ).fetchone()

    if existing:
        db.execute(
            """UPDATE buyers SET name = ?, phone = ?, email = ?, solicitor_id = ?
               WHERE property_id = ?""",
            (
                buyer_data.get("name"), buyer_data.get("phone"),
                buyer_data.get("email"), solicitor_id,
                property_id,
            ),
        )
    else:
        db.execute(
            """INSERT INTO buyers (property_id, name, phone, email, solicitor_id)
               VALUES (?, ?, ?, ?, ?)""",
            (
                property_id, buyer_data.get("name"),
                buyer_data.get("phone"), buyer_data.get("email"),
                solicitor_id,
            ),
        )


def _upsert_seller(db, property_id, seller_data, solicitor_id):
    """Insert or update the seller for a property."""
    if not seller_data:
        return

    existing = db.execute(
        "SELECT id FROM sellers WHERE property_id = ?", (property_id,)
    ).fetchone()

    if existing:
        db.execute(
            """UPDATE sellers SET name = ?, phone = ?, email = ?, solicitor_id = ?
               WHERE property_id = ?""",
            (
                seller_data.get("name"), seller_data.get("phone"),
                seller_data.get("email"), solicitor_id,
                property_id,
            ),
        )
    else:
        db.execute(
            """INSERT INTO sellers (property_id, name, phone, email, solicitor_id)
               VALUES (?, ?, ?, ?, ?)""",
            (
                property_id, seller_data.get("name"),
                seller_data.get("phone"), seller_data.get("email"),
                solicitor_id,
            ),
        )


def _replace_milestones(db, property_id, milestones):
    """Delete existing milestones and re-insert from sync data."""
    if not milestones:
        return

    db.execute("DELETE FROM milestones WHERE property_id = ?", (property_id,))

    for idx, ms in enumerate(milestones):
        label = ms["label"]
        done = ms.get("done")
        stage = MILESTONE_STAGES.get(label, 2)

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


# ─────────────────────────────────────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────

def write_sync_data(db, properties_data):
    """Write a list of mapped property dicts into the database.

    Args:
        db:               sqlite3 connection (from database.get_db())
        properties_data:  list of dicts using NUVU DB column names,
                          as returned by a connector's sync_all().

    Returns:
        dict: {"created": N, "updated": N, "errors": [str]}
    """
    created = 0
    updated = 0
    errors = []

    for prop in properties_data:
        try:
            # 1. Upsert the property
            property_id, is_new = _upsert_property(db, prop)
            if is_new:
                created += 1
            else:
                updated += 1

            # 2. Get-or-create solicitors
            buyer_sol = prop.get("buyer_solicitor", {})
            buyer_sol_id = get_or_create_solicitor(
                db, buyer_sol.get("name"), buyer_sol.get("phone")
            )

            seller_sol = prop.get("seller_solicitor", {})
            seller_sol_id = get_or_create_solicitor(
                db, seller_sol.get("name"), seller_sol.get("phone")
            )

            # 3. Upsert buyer and seller
            _upsert_buyer(db, property_id, prop.get("buyer"), buyer_sol_id)
            _upsert_seller(db, property_id, prop.get("seller"), seller_sol_id)

            # 4. Replace milestones
            _replace_milestones(db, property_id, prop.get("milestones"))

            # 5. Add sync note
            db.execute(
                """INSERT INTO notes (property_id, note_text, source)
                   VALUES (?, ?, 'api')""",
                (property_id, f"Synced from CRM at {datetime.now().strftime('%Y-%m-%d %H:%M')}"),
            )

        except Exception as e:
            slug = prop.get("slug", "unknown")
            errors.append(f"{slug}: {str(e)}")

    db.commit()

    return {"created": created, "updated": updated, "errors": errors}
