#!/usr/bin/env python3
"""
Brief 4 — NUVU data migration: old shared project → new standalone project.

Old project:  reads via PostgREST REST API (anon key, RLS disabled)
New project:  writes via PostgREST REST API (secret key, full access)

FK-safe migration order; paginates large tables in batches of 500.
"""

import json
import sys
import time
import urllib.request
import urllib.error

# ── Credentials ───────────────────────────────────────────────────────────────
# Set these environment variables before running this script:
#   OLD_SUPABASE_URL, OLD_SUPABASE_KEY  — source (read) project
#   NEW_SUPABASE_URL, NEW_SUPABASE_KEY  — destination (write) project
import os

OLD_URL  = os.environ["OLD_SUPABASE_URL"]
OLD_KEY  = os.environ["OLD_SUPABASE_KEY"]

NEW_URL  = os.environ["NEW_SUPABASE_URL"]
NEW_KEY  = os.environ["NEW_SUPABASE_KEY"]

BATCH    = 500
# ─────────────────────────────────────────────────────────────────────────────


def _request(method, url, key, payload=None, extra_headers=None):
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read()
            return json.loads(body) if body else []
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} {method} {url}: {body}") from e


def fetch_rows(table: str, offset: int, limit: int) -> list[dict]:
    url = (
        f"{OLD_URL}/rest/v1/{table}"
        f"?select=*&order=id&limit={limit}&offset={offset}"
    )
    return _request("GET", url, OLD_KEY)


def insert_rows(table: str, rows: list[dict]) -> None:
    if not rows:
        return
    url = f"{NEW_URL}/rest/v1/{table}"
    payload = json.dumps(rows).encode()
    _request(
        "POST", url, NEW_KEY, payload,
        extra_headers={"Prefer": "resolution=ignore-duplicates,return=minimal"},
    )


def migrate_table(table: str) -> int:
    """Returns number of rows migrated."""
    offset = 0
    migrated = 0
    while True:
        rows = fetch_rows(table, offset, BATCH)
        if not rows:
            break
        insert_rows(table, rows)
        migrated += len(rows)
        offset += len(rows)
        print(".", end="", flush=True)
        if len(rows) < BATCH:
            break
        time.sleep(0.15)
    return migrated


# ── Tables that exist in old project (11 of 13; form_responses/completions new)
# Ordered by FK dependency
TABLES = [
    "sales_progression",
    "sales_pipeline",
    "chain_links",
    "solicitors",
    "local_authority_search_times",
    "preferred_surveyors",
    "inbound_emails",
    "chase_messages",
    "chase_confirmations",
    "portal_sessions",
    "chain_chase_state",
]

EXPECTED = {
    "sales_progression": 114,
    "sales_pipeline": 134,
    "chain_links": 0,
    "solicitors": 1394,
    "local_authority_search_times": 4,
    "preferred_surveyors": 0,
    "inbound_emails": 12,
    "chase_messages": 0,
    "chase_confirmations": 0,
    "portal_sessions": 1,
    "chain_chase_state": 0,
}


def main():
    print("=== NUVU Brief 4 — Data Migration ===")
    print(f"  OLD: {OLD_URL}")
    print(f"  NEW: {NEW_URL}\n")

    results = {}
    for table in TABLES:
        expected = EXPECTED.get(table, "?")
        if expected == 0:
            print(f"  {table}: 0 rows — skip")
            results[table] = 0
            continue
        print(f"  {table} (expected {expected}): ", end="", flush=True)
        try:
            n = migrate_table(table)
            results[table] = n
            print(f" {n} rows migrated")
        except RuntimeError as exc:
            print(f"\n  ERROR: {exc}", file=sys.stderr)
            sys.exit(1)

    print("\n=== Done ===")
    for t, n in results.items():
        status = "✓" if n == EXPECTED.get(t, n) else "!"
        print(f"  {status} {t}: {n}")


if __name__ == "__main__":
    main()
