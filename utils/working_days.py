"""UK-style Mon–Fri working-day arithmetic for chase / needs-attention."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any


def _to_date(val: Any) -> date | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            return None
    return None


def add_working_days(start: date | datetime | Any, working_days: int) -> date | None:
    """Return the date after adding `working_days` Mon–Fri days (0 = start date)."""
    d0 = _to_date(start)
    if d0 is None:
        return None
    n = int(working_days)
    if n <= 0:
        return d0
    d = d0
    added = 0
    while added < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            added += 1
    return d
