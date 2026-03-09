"""
NUVU — Outbound Sync Engine
==============================
Queues and sends updates from NUVU back to the originating CRM.

When an agent adds a note, the AI parser updates milestones, or a
status changes — these events are queued and pushed back to the
CRM connector that originally supplied the property.

Flow:
  1. NUVU action (add note, update milestone, change status, complete)
  2. queue_outbound() → inserts into outbound_sync_queue table
  3. push_*_to_crm() → looks up source connector, calls write-back method
  4. Result logged to sync_log with direction='outbound'

Beta mode: All write-back methods are stubbed in the connectors.
The queue still works end-to-end, so when real credentials are
added the outbound sync will activate automatically.

Usage:
    from connectors.sync_outbound import push_note_to_crm, push_milestone_to_crm

    push_note_to_crm(property_db_id, "Searches received today", "Agent")
    push_milestone_to_crm(property_db_id, "Searches Received", True, "2026-02-10")
"""

import json
import traceback
from datetime import datetime

from database import get_db


# ─────────────────────────────────────────────────────────────
#  QUEUE MANAGEMENT
# ─────────────────────────────────────────────────────────────

def queue_outbound(db, property_id, event_type, payload):
    """Insert an event into the outbound_sync_queue table.

    Args:
        db:           sqlite3 connection
        property_id:  NUVU property DB id (integer)
        event_type:   One of: 'note', 'milestone', 'status', 'completion'
        payload:      dict of event data (will be JSON-serialised)

    Returns:
        int: The queue entry ID
    """
    # Look up source connector for this property
    row = db.execute(
        "SELECT source_connector FROM properties WHERE id = ?",
        (property_id,)
    ).fetchone()
    connector_name = row["source_connector"] if row and row["source_connector"] else None

    cur = db.execute(
        """INSERT INTO outbound_sync_queue
           (property_id, event_type, payload, connector_name)
           VALUES (?, ?, ?, ?)""",
        (property_id, event_type, json.dumps(payload), connector_name),
    )
    db.commit()
    return cur.lastrowid


def _get_property_source(db, property_id):
    """Look up the source connector and CRM ID for a property.

    Returns:
        tuple: (source_connector, source_crm_id) or (None, None)
    """
    row = db.execute(
        "SELECT source_connector, source_crm_id FROM properties WHERE id = ?",
        (property_id,)
    ).fetchone()
    if row:
        return row["source_connector"], row["source_crm_id"]
    return None, None


def _get_connector_manager():
    """Get the global ConnectorManager instance.

    Lazy import to avoid circular imports.
    """
    from connectors.connector_manager import ConnectorManager
    return ConnectorManager()


def _log_outbound_sync(db, connector_name, status, error_message=None):
    """Write an outbound sync entry to sync_log."""
    db.execute(
        """INSERT INTO sync_log
           (connector_name, direction, status, finished_at, error_message)
           VALUES (?, 'outbound', ?, datetime('now'), ?)""",
        (connector_name or "unknown", status, error_message),
    )
    db.commit()


# ─────────────────────────────────────────────────────────────
#  PUSH FUNCTIONS (called from app.py)
# ─────────────────────────────────────────────────────────────

def push_note_to_crm(property_id, note_text, author="Agent"):
    """Push a note back to the originating CRM connector.

    Args:
        property_id:  NUVU property DB id (integer)
        note_text:    The note content
        author:       Who wrote the note

    This function:
      1. Queues the event in outbound_sync_queue
      2. Looks up the source connector and CRM property ID
      3. Calls connector.push_note()
      4. Updates the queue entry status
      5. Logs to sync_log
    """
    db = get_db()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # 1. Queue the event
        payload = {"note_text": note_text, "author": author, "timestamp": timestamp}
        queue_id = queue_outbound(db, property_id, "note", payload)

        # 2. Look up source
        source_connector, source_crm_id = _get_property_source(db, property_id)

        if not source_connector or not source_crm_id:
            # Property doesn't have a CRM source (e.g. migrated from hardcoded data)
            db.execute(
                """UPDATE outbound_sync_queue SET status = 'skipped',
                   processed_at = datetime('now'),
                   error_message = 'No source connector'
                   WHERE id = ?""",
                (queue_id,),
            )
            db.commit()
            print(f"  [outbound] Skipped note push — no source connector for property {property_id}")
            return

        # 3. Get connector and push
        manager = _get_connector_manager()
        connector = manager.get_connector(source_connector)

        if not connector:
            _mark_queue_failed(db, queue_id, f"Connector '{source_connector}' not registered")
            return

        result = connector.push_note(source_crm_id, note_text, author, timestamp)

        # 4. Update queue entry
        if result.get("success"):
            db.execute(
                """UPDATE outbound_sync_queue SET status = 'sent',
                   processed_at = datetime('now')
                   WHERE id = ?""",
                (queue_id,),
            )
            _log_outbound_sync(db, source_connector, "success")
        else:
            _mark_queue_failed(db, queue_id, result.get("error", "Unknown error"))
            _log_outbound_sync(db, source_connector, "error", result.get("error"))

        db.commit()

    except Exception as e:
        print(f"  [outbound] Error pushing note: {e}")
        traceback.print_exc()
    finally:
        db.close()


def push_milestone_to_crm(property_id, milestone_name, is_complete, completed_date=None):
    """Push a milestone update back to the originating CRM connector.

    Args:
        property_id:     NUVU property DB id (integer)
        milestone_name:  e.g. "Searches Received"
        is_complete:     True/False/None
        completed_date:  Date string (YYYY-MM-DD) or None
    """
    db = get_db()

    try:
        payload = {
            "milestone_name": milestone_name,
            "is_complete": is_complete,
            "completed_date": completed_date,
        }
        queue_id = queue_outbound(db, property_id, "milestone", payload)

        source_connector, source_crm_id = _get_property_source(db, property_id)

        if not source_connector or not source_crm_id:
            db.execute(
                """UPDATE outbound_sync_queue SET status = 'skipped',
                   processed_at = datetime('now'),
                   error_message = 'No source connector'
                   WHERE id = ?""",
                (queue_id,),
            )
            db.commit()
            print(f"  [outbound] Skipped milestone push — no source connector for property {property_id}")
            return

        manager = _get_connector_manager()
        connector = manager.get_connector(source_connector)

        if not connector:
            _mark_queue_failed(db, queue_id, f"Connector '{source_connector}' not registered")
            return

        result = connector.push_milestone_update(
            source_crm_id, milestone_name, is_complete, completed_date
        )

        if result.get("success"):
            db.execute(
                """UPDATE outbound_sync_queue SET status = 'sent',
                   processed_at = datetime('now')
                   WHERE id = ?""",
                (queue_id,),
            )
            _log_outbound_sync(db, source_connector, "success")
        else:
            _mark_queue_failed(db, queue_id, result.get("error", "Unknown error"))
            _log_outbound_sync(db, source_connector, "error", result.get("error"))

        db.commit()

    except Exception as e:
        print(f"  [outbound] Error pushing milestone: {e}")
        traceback.print_exc()
    finally:
        db.close()


def push_status_to_crm(property_id, new_status, reason="Status changed by NUVU"):
    """Push a status change back to the originating CRM connector.

    Args:
        property_id:  NUVU property DB id (integer)
        new_status:   "on-track", "at-risk", or "stalled"
        reason:       Human-readable reason
    """
    db = get_db()

    try:
        payload = {"new_status": new_status, "reason": reason}
        queue_id = queue_outbound(db, property_id, "status", payload)

        source_connector, source_crm_id = _get_property_source(db, property_id)

        if not source_connector or not source_crm_id:
            db.execute(
                """UPDATE outbound_sync_queue SET status = 'skipped',
                   processed_at = datetime('now'),
                   error_message = 'No source connector'
                   WHERE id = ?""",
                (queue_id,),
            )
            db.commit()
            return

        manager = _get_connector_manager()
        connector = manager.get_connector(source_connector)

        if not connector:
            _mark_queue_failed(db, queue_id, f"Connector '{source_connector}' not registered")
            return

        result = connector.push_status_change(source_crm_id, new_status, reason)

        if result.get("success"):
            db.execute(
                """UPDATE outbound_sync_queue SET status = 'sent',
                   processed_at = datetime('now')
                   WHERE id = ?""",
                (queue_id,),
            )
            _log_outbound_sync(db, source_connector, "success")
        else:
            _mark_queue_failed(db, queue_id, result.get("error", "Unknown error"))
            _log_outbound_sync(db, source_connector, "error", result.get("error"))

        db.commit()

    except Exception as e:
        print(f"  [outbound] Error pushing status: {e}")
        traceback.print_exc()
    finally:
        db.close()


def push_completion_handback(property_id):
    """Package entire transaction history and send back to CRM.

    Called when a property reaches Completion milestone.

    Gathers all milestones, notes, and timeline data from NUVU's
    database, packages it into a summary, and pushes to the CRM.
    """
    db = get_db()

    try:
        # Gather property data
        prop = db.execute("SELECT * FROM properties WHERE id = ?", (property_id,)).fetchone()
        if not prop:
            print(f"  [outbound] Completion handback — property {property_id} not found")
            return

        # Gather milestones
        milestones = db.execute(
            """SELECT milestone_name, milestone_stage, is_complete, completed_date, sort_order
               FROM milestones WHERE property_id = ? ORDER BY sort_order""",
            (property_id,)
        ).fetchall()

        # Gather notes
        notes = db.execute(
            """SELECT note_text, author, created_date, source
               FROM notes WHERE property_id = ? ORDER BY created_date""",
            (property_id,)
        ).fetchall()

        # Build summary
        summary = {
            "property_address": prop["address"],
            "property_slug": prop["slug"],
            "duration_days": prop["duration_days"],
            "final_status": prop["status"],
            "milestones": [
                {
                    "name": m["milestone_name"],
                    "stage": m["milestone_stage"],
                    "complete": bool(m["is_complete"]),
                    "completed_date": m["completed_date"],
                }
                for m in milestones
            ],
            "notes": [
                {
                    "text": n["note_text"],
                    "author": n["author"],
                    "date": n["created_date"],
                    "source": n["source"],
                }
                for n in notes
            ],
            "timeline": [],  # Could be enhanced with status change history
            "status_history": [],  # Could be enhanced with status tracking
            "handback_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        payload = summary
        queue_id = queue_outbound(db, property_id, "completion", payload)

        source_connector, source_crm_id = _get_property_source(db, property_id)

        if not source_connector or not source_crm_id:
            db.execute(
                """UPDATE outbound_sync_queue SET status = 'skipped',
                   processed_at = datetime('now'),
                   error_message = 'No source connector'
                   WHERE id = ?""",
                (queue_id,),
            )
            db.commit()
            print(f"  [outbound] Skipped completion handback — no source connector")
            return

        manager = _get_connector_manager()
        connector = manager.get_connector(source_connector)

        if not connector:
            _mark_queue_failed(db, queue_id, f"Connector '{source_connector}' not registered")
            return

        result = connector.push_completion_summary(source_crm_id, summary)

        if result.get("success"):
            db.execute(
                """UPDATE outbound_sync_queue SET status = 'sent',
                   processed_at = datetime('now')
                   WHERE id = ?""",
                (queue_id,),
            )
            _log_outbound_sync(db, source_connector, "success")
        else:
            _mark_queue_failed(db, queue_id, result.get("error", "Unknown error"))
            _log_outbound_sync(db, source_connector, "error", result.get("error"))

        db.commit()
        print(f"  [outbound] Completion handback queued for property {property_id}")

    except Exception as e:
        print(f"  [outbound] Error pushing completion handback: {e}")
        traceback.print_exc()
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
#  QUEUE PROCESSING (for future background worker)
# ─────────────────────────────────────────────────────────────

def process_outbound_queue():
    """Process all pending items in the outbound_sync_queue.

    This function is for future use as a background worker or cron job.
    Currently, items are processed inline when push_*_to_crm() is called.

    Returns:
        dict: {"processed": int, "sent": int, "failed": int, "skipped": int}
    """
    db = get_db()
    stats = {"processed": 0, "sent": 0, "failed": 0, "skipped": 0}

    try:
        pending = db.execute(
            """SELECT id, property_id, event_type, payload, connector_name
               FROM outbound_sync_queue
               WHERE status = 'pending'
               ORDER BY created_at ASC
               LIMIT 100"""
        ).fetchall()

        for item in pending:
            stats["processed"] += 1
            # For now, mark as skipped — real processing would
            # deserialise payload and call the appropriate push function
            db.execute(
                """UPDATE outbound_sync_queue SET status = 'skipped',
                   processed_at = datetime('now'),
                   error_message = 'Background processing not yet implemented'
                   WHERE id = ?""",
                (item["id"],),
            )
            stats["skipped"] += 1

        db.commit()

    except Exception as e:
        print(f"  [outbound] Error processing queue: {e}")
        traceback.print_exc()
    finally:
        db.close()

    return stats


# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────

def _mark_queue_failed(db, queue_id, error_message):
    """Mark a queue entry as failed."""
    db.execute(
        """UPDATE outbound_sync_queue SET status = 'failed',
           processed_at = datetime('now'),
           error_message = ?
           WHERE id = ?""",
        (error_message, queue_id),
    )
    db.commit()
    print(f"  [outbound] Queue entry {queue_id} failed: {error_message}")
