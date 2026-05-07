#!/usr/bin/env python3
"""
Batch-parse Alto property screenshots with Claude vision, match rows in
Supabase `sales_progression` by `property_address`, and upsert populated fields.

Environment (load from repo-root `.env` via python-dotenv):
  SUPABASE_URL, SUPABASE_ANON_KEY — same as NUVU (`db_supabase.py`)
  ANTHROPIC_API_KEY — set locally; Railway uses ANTHROPIC_KEY_FOR_RAILWAY (copy value into .env as ANTHROPIC_API_KEY)

Usage:
  python scripts/parse-alto-screenshots.py /path/to/screenshots
  python scripts/parse-alto-screenshots.py /path/to/screenshots --dry-run
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import re
import sys
from datetime import date, datetime
from difflib import get_close_matches
from pathlib import Path
from typing import Any

# Parsed / written milestone-style dates must fall in this inclusive year range.
DATE_SANE_YEAR_MIN = 2025
DATE_SANE_YEAR_MAX = 2027

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from utils.address import normalise_address

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}

# Columns we may set from Alto screenshots (subset of public.sales_progression).
# `status` is intentionally omitted (human-set in NUVU).
UPDATABLE_COLUMNS = frozenset(
    {
        "buyer_name",
        "buyer_phone",
        "buyer_email",
        "vendor_name",
        "vendor_phone",
        "vendor_email",
        "buyer_solicitor",
        "vendor_solicitor",
        "mortgage_broker",
        "surveyor",
        "notes",
        "offer_accepted",
        "memo_sent",
        "exchange_date",
        "completion_date",
        "searches_ordered",
        "searches_received",
        "mortgage_offered",
        "enquiries_raised",
        "enquiries_answered",
        "survey_instructed",
        "protocol_forms_sent",
        "protocol_forms_returned",
        "searches_paid",
        "completion_target",
        "exchange_agreed",
        "draft_contract_sent",
    }
)

DATE_COLUMNS = frozenset(
    {
        "searches_ordered",
        "searches_received",
        "mortgage_offered",
        "enquiries_raised",
        "enquiries_answered",
        "survey_instructed",
        "protocol_forms_sent",
        "protocol_forms_returned",
        "searches_paid",
        "completion_target",
        "exchange_agreed",
        "draft_contract_sent",
    }
)

TEXT_DATE_COLUMNS = frozenset(
    {"offer_accepted", "memo_sent", "exchange_date", "completion_date"}
)

EXTRACTION_SCHEMA_HINT = """
Return a single JSON object only (no markdown), with these keys. Use null for anything not clearly visible.
{
  "property_address": "full address string as shown, including postcode",
  "buyer_name": null,
  "buyer_solicitor": "firm or contact line as shown",
  "vendor_solicitor": null,
  "mortgage_broker": null,
  "surveyor": null,
  "buyer_phone": null,
  "buyer_email": null,
  "vendor_name": null,
  "vendor_phone": null,
  "vendor_email": null,
  "dates": {
    "offer_accepted": null,
    "memo_sent": null,
    "searches_ordered": null,
    "searches_received": null,
    "survey_instructed": null,
    "mortgage_offered": null,
    "exchange_date": null,
    "completion_date": null,
    "completion_target": null,
    "exchange_agreed": null,
    "enquiries_raised": null,
    "enquiries_answered": null,
    "protocol_forms_sent": null,
    "protocol_forms_returned": null,
    "searches_paid": null,
    "draft_contract_sent": null
  },
  "notes": "any other visible free-text notes on the progression screen, concatenated sensibly; null if none"
}
Date values must be ISO 8601 dates only (YYYY-MM-DD) when you can read a calendar date; otherwise null.
Map an on-screen "survey date" / survey booked / survey instructed field to dates.survey_instructed.
"""


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(message)s",
    )


def _is_sane_transaction_iso(iso: str) -> bool:
    if not iso or len(iso) < 10:
        return False
    try:
        y = int(iso[:4])
        return DATE_SANE_YEAR_MIN <= y <= DATE_SANE_YEAR_MAX
    except ValueError:
        return False


def _parse_iso_date(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return None
    s = str(val).strip()
    if not s or s.lower() in ("null", "none", "n/a", "—", "-"):
        return None
    s = s[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
        try:
            dt = datetime.strptime(s if fmt != "%Y-%m-%d" else s[:10], fmt)
            return dt.date().isoformat()
        except ValueError:
            continue
    try:
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            date.fromisoformat(s[:10])
            return s[:10]
    except ValueError:
        pass
    return None


def _coerce_for_column(
    col: str,
    raw: Any,
    *,
    rejected_dates: list[dict[str, Any]] | None = None,
) -> Any:
    if raw is None:
        return None
    if isinstance(raw, str) and not raw.strip():
        return None
    if col in DATE_COLUMNS:
        parsed = _parse_iso_date(raw)
        if not parsed:
            return None
        if not _is_sane_transaction_iso(parsed):
            logging.warning(
                "Suspicious date rejected (not written): column=%s raw=%r parsed=%s "
                "(expected year %s–%s)",
                col,
                raw,
                parsed,
                DATE_SANE_YEAR_MIN,
                DATE_SANE_YEAR_MAX,
            )
            if rejected_dates is not None:
                rejected_dates.append(
                    {"column": col, "raw": raw, "parsed": parsed, "reason": "year_out_of_range"}
                )
            return None
        return parsed
    if col in TEXT_DATE_COLUMNS:
        parsed = _parse_iso_date(raw)
        if parsed:
            if not _is_sane_transaction_iso(parsed):
                logging.warning(
                    "Suspicious date rejected (not written): column=%s raw=%r parsed=%s "
                    "(expected year %s–%s)",
                    col,
                    raw,
                    parsed,
                    DATE_SANE_YEAR_MIN,
                    DATE_SANE_YEAR_MAX,
                )
                if rejected_dates is not None:
                    rejected_dates.append(
                        {
                            "column": col,
                            "raw": raw,
                            "parsed": parsed,
                            "reason": "year_out_of_range",
                        }
                    )
                return None
            return parsed
        text = str(raw).strip() or None
        if text and len(text) >= 4 and text[:4].isdigit():
            try:
                y = int(text[:4])
                if y < DATE_SANE_YEAR_MIN or y > DATE_SANE_YEAR_MAX:
                    logging.warning(
                        "Suspicious date rejected (not written): column=%s raw=%r "
                        "(expected year %s–%s)",
                        col,
                        raw,
                        DATE_SANE_YEAR_MIN,
                        DATE_SANE_YEAR_MAX,
                    )
                    if rejected_dates is not None:
                        rejected_dates.append(
                            {
                                "column": col,
                                "raw": raw,
                                "parsed": None,
                                "reason": "year_out_of_range",
                            }
                        )
                    return None
            except ValueError:
                pass
        return text
    return str(raw).strip() or None


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(_ROOT / ".env")


def _anthropic_api_key() -> str:
    return (
        os.environ.get("ANTHROPIC_API_KEY", "").strip()
        or os.environ.get("ANTHROPIC_KEY_FOR_RAILWAY", "").strip()
    )


def _image_media_type(path: Path) -> str:
    suf = path.suffix.lower()
    if suf == ".png":
        return "image/png"
    if suf in (".jpg", ".jpeg"):
        return "image/jpeg"
    if suf == ".webp":
        return "image/webp"
    return "application/octet-stream"


def _collect_images(folder: Path) -> list[Path]:
    out = []
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES:
            out.append(p)
    return out


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    m = re.search(r"\{[\s\S]*\}\s*$", text)
    if not m:
        raise ValueError("No JSON object found in model response")
    return json.loads(m.group(0))


def _call_vision(
    client: Any,
    model: str,
    image_path: Path,
) -> dict[str, Any]:
    b64 = base64.standard_b64encode(image_path.read_bytes()).decode("ascii")
    media_type = _image_media_type(image_path)
    prompt = (
        "You are extracting structured data from an Alto CRM property / sales progression screen capture.\n"
        + EXTRACTION_SCHEMA_HINT
        + "\nRespond with the JSON object only."
    )
    msg = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    parts = []
    for block in msg.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return _extract_json_object("".join(parts))


def _flatten_extracted(raw: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    addr = raw.get("property_address")
    if addr is not None:
        flat["property_address"] = str(addr).strip() or None
    for key in (
        "buyer_name",
        "buyer_solicitor",
        "vendor_solicitor",
        "mortgage_broker",
        "surveyor",
        "buyer_phone",
        "buyer_email",
        "vendor_name",
        "vendor_phone",
        "vendor_email",
        "notes",
    ):
        if key in raw:
            flat[key] = raw.get(key)
    dates = raw.get("dates") or {}
    if isinstance(dates, dict):
        for dk, dv in dates.items():
            if dk in UPDATABLE_COLUMNS:
                flat[dk] = dv
    return flat


def _build_update_payload(
    canonical_address: str,
    flat: dict[str, Any],
    existing: dict[str, Any] | None,
    rejected_dates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"property_address": canonical_address}
    for col in UPDATABLE_COLUMNS:
        if col not in flat:
            continue
        coerced = _coerce_for_column(col, flat[col], rejected_dates=rejected_dates)
        if coerced is None:
            continue
        if existing is not None:
            prev = existing.get(col)
            if prev is not None and str(prev).strip() == str(coerced).strip():
                continue
        payload[col] = coerced
    return payload


def _lcs_length(a: str, b: str) -> int:
    """Length of longest common contiguous substring (DP)."""
    if not a or not b:
        return 0
    na, nb = len(a), len(b)
    best = 0
    dp = [0] * (nb + 1)
    for i in range(1, na + 1):
        prev = 0
        for j in range(1, nb + 1):
            cur = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev + 1
                if dp[j] > best:
                    best = dp[j]
            else:
                dp[j] = 0
            prev = cur
    return best


def _unique_addresses(rows: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for r in rows:
        addr = (r.get("property_address") or "").strip()
        if not addr or addr in seen:
            continue
        seen.add(addr)
        out.append(addr)
    return out


def _resolve_address(
    extracted: str,
    all_addresses: list[str],
) -> tuple[str | None, list[str]]:
    """Match extracted label to Supabase property_address.

    After :func:`normalise_address` (lowercase, no punctuation, single spaces),
    normalized extracted must appear as a substring of normalized DB address.
    If several rows match, prefer the longest common substring, then the
    longest full DB address, then lexicographic order for stability.
    """
    ex = extracted.strip()
    if not ex:
        return None, []
    ex_n = normalise_address(ex)
    candidates: list[str] = []
    for addr in all_addresses:
        addr_n = normalise_address(addr)
        if ex_n in addr_n:
            candidates.append(addr)
    if candidates:

        def sort_key(addr: str) -> tuple[int, int, str]:
            addr_n = normalise_address(addr)
            lcs = _lcs_length(ex_n, addr_n)
            return (-lcs, -len(addr_n), addr)

        candidates.sort(key=sort_key)
        return candidates[0], []

    norms = [normalise_address(a) for a in all_addresses]
    suggestions_raw = get_close_matches(ex_n, norms, n=5, cutoff=0.75)
    canon = []
    for s in suggestions_raw:
        for addr in all_addresses:
            if normalise_address(addr) == s:
                canon.append(addr)
                break
    return None, canon


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Parse Alto screenshots with Claude, upsert sales_progression in Supabase.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Environment: set SUPABASE_URL, SUPABASE_ANON_KEY, and ANTHROPIC_API_KEY in repo-root .env.\n"
            "Copy the Railway secret ANTHROPIC_KEY_FOR_RAILWAY into .env as ANTHROPIC_API_KEY."
        ),
    )
    ap.add_argument(
        "folder",
        type=Path,
        help="Directory containing PNG/JPG Alto screenshots",
    )
    ap.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="Anthropic model id (default: claude-sonnet-4-20250514)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and log only; do not write to Supabase",
    )
    ap.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Debug logging",
    )
    args = ap.parse_args()
    _setup_logging(args.verbose)

    folder = args.folder.expanduser().resolve()
    if not folder.is_dir():
        logging.error("Not a directory: %s", folder)
        return 1

    _load_dotenv()
    key = _anthropic_api_key()
    if not key:
        logging.error(
            "Missing Anthropic API key. Set ANTHROPIC_API_KEY in .env "
            "(copy the value from Railway variable ANTHROPIC_KEY_FOR_RAILWAY)."
        )
        return 1

    try:
        from anthropic import Anthropic
    except ImportError:
        logging.error("Install dependencies: pip install anthropic")
        return 1

    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    supabase_key = os.environ.get("SUPABASE_ANON_KEY", "").strip()
    if not supabase_url or not supabase_key:
        if not args.dry_run:
            logging.error("SUPABASE_URL and SUPABASE_ANON_KEY are required unless --dry-run")
            return 1
        logging.warning(
            "Supabase env not set — dry-run will parse images only (no address matching)."
        )

    images = _collect_images(folder)
    if not images:
        logging.error("No PNG/JPG images found in %s", folder)
        return 1

    logging.info("Found %d image(s) in %s", len(images), folder)

    address_list: list[str] = []
    sb = None
    if supabase_url and supabase_key:
        from supabase import create_client

        sb = create_client(supabase_url, supabase_key)
        res = sb.table("sales_progression").select("property_address").execute()
        address_list = _unique_addresses(res.data or [])
        logging.info("Loaded %d property_address value(s) from Supabase", len(address_list))

    client = Anthropic(api_key=key)
    summary_rows: list[dict[str, Any]] = []

    for img in images:
        logging.info("--- %s", img.name)
        try:
            raw = _call_vision(client, args.model, img)
        except Exception as e:
            logging.exception("Vision parse failed: %s", e)
            summary_rows.append(
                {
                    "file": img.name,
                    "error": str(e),
                    "matched": None,
                    "updated_fields": [],
                }
            )
            continue

        flat = _flatten_extracted(raw)
        extracted_addr = flat.get("property_address") or ""
        logging.info("Extracted address: %s", extracted_addr or "(empty)")

        matched, suggestions = _resolve_address(extracted_addr, address_list)
        if not matched:
            logging.warning(
                "No sales_progression row for address %r. Close DB matches: %s",
                extracted_addr,
                suggestions or "(none)",
            )
            summary_rows.append(
                {
                    "file": img.name,
                    "extracted_address": extracted_addr,
                    "matched": None,
                    "suggestions": suggestions,
                    "extracted": {k: v for k, v in flat.items() if k != "property_address"},
                    "updated_fields": [],
                }
            )
            continue

        assert matched is not None

        if args.dry_run:
            existing = None
            if sb is not None:
                cols = ",".join(sorted(UPDATABLE_COLUMNS))
                existing_res = (
                    sb.table("sales_progression")
                    .select(cols)
                    .eq("property_address", matched)
                    .limit(1)
                    .execute()
                )
                existing = (existing_res.data or [None])[0]
            rejected_dates: list[dict[str, Any]] = []
            payload = _build_update_payload(
                matched, flat, existing, rejected_dates=rejected_dates
            )
            updated_keys = [k for k in payload if k != "property_address"]
            logging.info("[dry-run] Matched %r -> %r", extracted_addr, matched)
            logging.info(
                "[dry-run] Would upsert fields: %s",
                ", ".join(updated_keys) if updated_keys else "(none — unchanged or empty)",
            )
            if updated_keys:
                logging.info(
                    "[dry-run] Payload: %s",
                    json.dumps({k: payload[k] for k in updated_keys}, indent=2, default=str),
                )
            row_out: dict[str, Any] = {
                "file": img.name,
                "extracted_address": extracted_addr,
                "matched": matched,
                "updated_fields": updated_keys,
                "values": {k: payload[k] for k in updated_keys},
            }
            if rejected_dates:
                row_out["sanity_rejected_dates"] = rejected_dates
            summary_rows.append(row_out)
            continue

        assert sb is not None
        existing_res = (
            sb.table("sales_progression")
            .select(",".join(sorted(UPDATABLE_COLUMNS)))
            .eq("property_address", matched)
            .limit(1)
            .execute()
        )
        existing = (existing_res.data or [None])[0]

        rejected_dates = []
        payload = _build_update_payload(
            matched, flat, existing, rejected_dates=rejected_dates
        )
        updated_keys = [k for k in payload if k != "property_address"]

        if len(payload) <= 1:
            logging.info("No new values to write for %s (all empty or unchanged)", matched)
            row_done: dict[str, Any] = {
                "file": img.name,
                "matched": matched,
                "extracted_address": extracted_addr,
                "updated_fields": [],
            }
            if rejected_dates:
                row_done["sanity_rejected_dates"] = rejected_dates
            summary_rows.append(row_done)
            continue

        try:
            sb.table("sales_progression").upsert(
                payload,
                on_conflict="property_address",
            ).execute()
        except Exception as e:
            logging.exception("Upsert failed for %s: %s", matched, e)
            summary_rows.append(
                {
                    "file": img.name,
                    "matched": matched,
                    "error": str(e),
                    "updated_fields": updated_keys,
                    "sanity_rejected_dates": rejected_dates or None,
                }
            )
            continue

        logging.info(
            "Updated %s fields: %s",
            matched,
            ", ".join(updated_keys) if updated_keys else "(none)",
        )
        for k in updated_keys:
            logging.info("  %s = %r", k, payload[k])
        row_ok: dict[str, Any] = {
            "file": img.name,
            "matched": matched,
            "extracted_address": extracted_addr,
            "updated_fields": updated_keys,
            "values": {k: payload[k] for k in updated_keys},
        }
        if rejected_dates:
            row_ok["sanity_rejected_dates"] = rejected_dates
        summary_rows.append(row_ok)

    print("\n========== BATCH SUMMARY ==========")
    print(json.dumps(summary_rows, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
