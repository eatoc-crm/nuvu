"""CRM-agnostic address normalisation for matching EATOC ↔ Supabase rows."""

from __future__ import annotations

import re


def normalise_address(addr: str) -> str:
    """Normalise for address matching: lowercase, strip punctuation, collapse whitespace.

    Punctuation (commas, periods, hyphens, apostrophes, etc.) is removed; only
    letters and digits are kept, separated by single spaces. Used so e.g.
    ``36, Norfolk Place`` matches ``36 Norfolk Place, Penrith, CA11 7UQ``.
    """
    if not addr:
        return ""
    lowered = addr.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", " ", lowered)
    return " ".join(cleaned.split())
