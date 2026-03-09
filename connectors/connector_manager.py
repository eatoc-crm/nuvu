"""
NUVU — Connector Manager
==========================
Orchestrates CRM connectors: registration, sync execution, logging,
and error handling.  Supports both inbound (CRM → NUVU) and outbound
(NUVU → CRM) sync operations.

Five CRM connectors are auto-registered:
  - Alto (Zoopla)
  - Reapit Foundations
  - Street.co.uk
  - Dezrez (Rezi)
  - Loop (placeholder)

Usage:
    from connectors.connector_manager import ConnectorManager

    manager = ConnectorManager()
    # All 5 connectors auto-registered on init (stub mode)

    result = manager.run_sync("alto")
    print(result)  # {"status": "success", "created": 3, ...}
"""

import traceback
from datetime import datetime

from database import get_db, init_db
from connectors.alto_connector import AltoConnector
from connectors.reapit_connector import ReapitConnector
from connectors.street_connector import StreetConnector
from connectors.dezrez_connector import DezrezConnector
from connectors.loop_connector import LoopConnector
from connectors.sync_to_database import write_sync_data


class ConnectorManager:
    """Manages all CRM connectors and sync operations."""

    def __init__(self):
        self._connectors = {}

        # Auto-register all 5 connectors in stub mode (no credentials)
        self.register("alto", AltoConnector())
        self.register("reapit", ReapitConnector())
        self.register("street", StreetConnector())
        self.register("dezrez", DezrezConnector())
        self.register("loop", LoopConnector())

    # ─────────────────────────────────────────────────────────
    #  CONNECTOR REGISTRATION
    # ─────────────────────────────────────────────────────────

    def register(self, name, connector):
        """Register a connector instance under a name.

        Args:
            name:       Short identifier (e.g. "alto", "reapit")
            connector:  Instance of a BaseConnector subclass
        """
        self._connectors[name] = connector

    def get_connector(self, name):
        """Get a registered connector by name, or None."""
        return self._connectors.get(name)

    def list_connectors(self):
        """List all registered connectors with their status.

        Returns:
            list[dict]: Each dict has keys:
                name, display_name, connected, supports_writeback,
                last_sync, last_error
        """
        db = get_db()
        result = []

        for name, conn in self._connectors.items():
            # Get the most recent sync for this connector
            last = db.execute(
                """SELECT finished_at, status, error_message, direction
                   FROM sync_log
                   WHERE connector_name = ?
                   ORDER BY id DESC LIMIT 1""",
                (name,),
            ).fetchone()

            result.append({
                "name": name,
                "display_name": getattr(conn, "display_name", name.replace("-", " ").title()),
                "connected": conn.is_connected,
                "supports_writeback": getattr(conn, "supports_writeback", False),
                "last_sync": last["finished_at"] if last else None,
                "last_status": last["status"] if last else None,
                "last_direction": last["direction"] if last else None,
                "last_error": last["error_message"] if last else conn.last_error,
            })

        db.close()
        return result

    # ─────────────────────────────────────────────────────────
    #  SYNC EXECUTION (INBOUND)
    # ─────────────────────────────────────────────────────────

    def run_sync(self, connector_name):
        """Run a full inbound sync for the named connector.

        Steps:
          1. Create a sync_log entry (status=running, direction=inbound)
          2. Call connector.sync_all() to get mapped data
          3. Write data to DB via sync_to_database
          4. Update sync_log with results
          5. Return summary dict

        Returns:
            dict: {
                "status": "success" | "error",
                "connector": str,
                "created": int,
                "updated": int,
                "total": int,
                "errors": list[str],
                "error_message": str | None,
                "duration_seconds": float,
            }
        """
        connector = self._connectors.get(connector_name)
        if not connector:
            return {
                "status": "error",
                "connector": connector_name,
                "error_message": f"Unknown connector: {connector_name}",
                "created": 0, "updated": 0, "total": 0, "errors": [],
            }

        db = get_db()
        start_time = datetime.now()

        # 1. Create sync_log entry
        cur = db.execute(
            """INSERT INTO sync_log (connector_name, direction, status)
               VALUES (?, 'inbound', 'running')""",
            (connector_name,),
        )
        log_id = cur.lastrowid
        db.commit()

        try:
            # 2. Run the connector's full sync
            print(f"\n  Sync started: {connector_name}")
            properties_data = connector.sync_all()

            # 3. Write to database
            result = write_sync_data(db, properties_data)
            total = result["created"] + result["updated"]

            elapsed = (datetime.now() - start_time).total_seconds()

            # 4. Update sync_log — success
            status = "success" if not result["errors"] else "error"
            error_msg = "; ".join(result["errors"]) if result["errors"] else None

            db.execute(
                """UPDATE sync_log SET
                    finished_at = datetime('now'),
                    status = ?,
                    properties_synced = ?,
                    properties_created = ?,
                    properties_updated = ?,
                    error_message = ?
                   WHERE id = ?""",
                (status, total, result["created"], result["updated"],
                 error_msg, log_id),
            )
            db.commit()

            print(f"  Sync complete: {total} properties ({result['created']} new, {result['updated']} updated) in {elapsed:.1f}s")

            return {
                "status": status,
                "connector": connector_name,
                "created": result["created"],
                "updated": result["updated"],
                "total": total,
                "errors": result["errors"],
                "error_message": error_msg,
                "duration_seconds": elapsed,
            }

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            error_msg = f"{type(e).__name__}: {str(e)}"

            # Update sync_log — error
            db.execute(
                """UPDATE sync_log SET
                    finished_at = datetime('now'),
                    status = 'error',
                    error_message = ?
                   WHERE id = ?""",
                (error_msg, log_id),
            )
            db.commit()

            print(f"  Sync FAILED: {error_msg}")
            traceback.print_exc()

            return {
                "status": "error",
                "connector": connector_name,
                "created": 0, "updated": 0, "total": 0,
                "errors": [error_msg],
                "error_message": error_msg,
                "duration_seconds": elapsed,
            }

        finally:
            db.close()

    # ─────────────────────────────────────────────────────────
    #  OUTBOUND SUPPORT
    # ─────────────────────────────────────────────────────────

    def get_connector_for_property(self, property_id):
        """Look up which connector a property came from.

        Args:
            property_id: NUVU property DB id (integer)

        Returns:
            tuple: (connector_name, connector_instance, source_crm_id) or (None, None, None)
        """
        db = get_db()
        row = db.execute(
            "SELECT source_connector, source_crm_id FROM properties WHERE id = ?",
            (property_id,),
        ).fetchone()
        db.close()

        if row and row["source_connector"]:
            connector = self._connectors.get(row["source_connector"])
            return row["source_connector"], connector, row["source_crm_id"]

        return None, None, None

    # ─────────────────────────────────────────────────────────
    #  SYNC HISTORY
    # ─────────────────────────────────────────────────────────

    def get_sync_history(self, limit=20):
        """Get recent sync log entries (both inbound and outbound).

        Returns:
            list[dict]: Most recent syncs, newest first.
        """
        db = get_db()
        rows = db.execute(
            """SELECT * FROM sync_log
               ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        db.close()

        return [dict(r) for r in rows]

    def get_outbound_queue(self, limit=50):
        """Get recent outbound sync queue entries.

        Returns:
            list[dict]: Most recent queue entries, newest first.
        """
        db = get_db()
        rows = db.execute(
            """SELECT oq.*, p.address, p.slug
               FROM outbound_sync_queue oq
               LEFT JOIN properties p ON oq.property_id = p.id
               ORDER BY oq.id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        db.close()

        return [dict(r) for r in rows]
