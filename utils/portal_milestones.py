"""Sales progression milestone updates for the TA portal (Window 3)."""

from __future__ import annotations

from datetime import datetime, timezone

from db_supabase import fetch_sales_progression_overlay_by_addresses, supabase_for_backend
from utils.address import normalise_address


def augment_protocol_forms_returned(property_address: str) -> None:
    """Set protocol_forms_returned on sales_progression only when currently null."""
    addr = (property_address or "").strip()
    if not addr:
        return
    key = normalise_address(addr)
    if not key:
        return
    by_addr = fetch_sales_progression_overlay_by_addresses([addr])
    row = by_addr.get(key)
    if not row:
        return
    if row.get("protocol_forms_returned"):
        return
    pid = row.get("id")
    if not pid:
        return
    stamp = datetime.now(timezone.utc).isoformat()
    try:
        supabase_for_backend().table("sales_progression").update(
            {"protocol_forms_returned": stamp}
        ).eq("id", pid).execute()
    except Exception:
        pass
