"""
NUVU Completion Engine
=======================
Calculates a REAL expected completion date for every property based on
TIME, not milestones ticked.

Philosophy: Every other tool counts milestones (8 of 10 = 80%). That's a
lie. A property with 8 milestones done but a 6-month land registry delay
is NOT 80% complete. NUVU calculates progress based on TIME — how far
through the adjusted timeline are we?

Usage:
    from completion_engine import calculate_completion, recalculate_property

    # Full calculation for one property
    result = calculate_completion("stalled")

    # Recalculate and persist to DB (called after note/email)
    recalculate_property(property_db_id)
"""

import re
from datetime import datetime, date, timedelta

from database import get_db


# ─────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────

BASELINE_WEEKS = 16          # 16 weeks = 80 working days
WORKING_DAYS_PER_WEEK = 5

# ─────────────────────────────────────────────────────────────
#  STEP 2 — STATIC ADJUSTMENTS
# ─────────────────────────────────────────────────────────────
# Each returns (adjustment_days, reason) or None

def _adjust_buyer_type(buyer_type):
    """Adjust timeline based on buyer type."""
    if not buyer_type:
        return None
    bt = buyer_type.lower().strip()
    if bt in ("cash", "cash buyer"):
        return (-20, "Cash buyer — no mortgage process")
    elif bt in ("ftb", "first time buyer", "first-time buyer", "first_time_buyer"):
        return (-10, "First-time buyer — no property to sell")
    elif bt in ("investor", "btl", "buy to let", "buy-to-let"):
        return (-10, "Investor/BTL — experienced, streamlined process")
    # Standard residential with mortgage — no change
    return None


def _adjust_chain(chain_length, chain_text):
    """Adjust timeline based on chain complexity."""
    # If explicit chain_length field is set, use it
    if chain_length is not None:
        if chain_length == 0:
            return (-15, "No chain — straightforward transaction")
        elif chain_length == 1:
            return (-15, "No chain — single transaction")
        elif chain_length == 2:
            return None  # baseline
        else:
            return None  # Chain 3+ — NUVU manages it
    # Otherwise, try to infer from chain_text
    if chain_text:
        ct = chain_text.lower()
        if any(p in ct for p in [
            "no chain", "chain-free", "chain free", "first-time buyer",
            "first time buyer", "cash buyer", "no property to sell",
            "renting", "currently renting", "no onward"
        ]):
            return (-15, "No chain detected — straightforward transaction")
    return None


def _adjust_property_type(property_type):
    """Adjust timeline based on property type (freehold/leasehold etc)."""
    if not property_type:
        return None
    pt = property_type.lower().strip()
    if pt == "leasehold":
        return (25, "Leasehold — management pack & additional enquiries")
    elif pt in ("new build", "new_build", "newbuild", "new build completed"):
        return (-10, "New build (completed) — standardised documentation")
    elif pt in ("shared ownership", "shared_ownership"):
        return (15, "Shared ownership — housing association involvement")
    # Freehold — no change
    return None


def _adjust_mortgage(mortgage_type):
    """Adjust timeline based on mortgage complexity."""
    if not mortgage_type:
        return None
    mt = mortgage_type.lower().strip()
    if mt in ("complex", "self-employed", "self_employed", "complex income"):
        return (15, "Complex income/self-employed — extended underwriting")
    # Standard with AIP — no change
    return None


def _adjust_solicitor(solicitor_type):
    """Adjust timeline based on solicitor quality."""
    if not solicitor_type:
        return None
    st = solicitor_type.lower().strip()
    if st in ("online", "panel", "online conveyancer", "panel conveyancer"):
        return (10, "Online/panel conveyancer — typically slower responses")
    # Both decent high street — no change
    return None


# ─────────────────────────────────────────────────────────────
#  STEP 3 — DYNAMIC ADJUSTMENTS (notes & emails scanning)
# ─────────────────────────────────────────────────────────────

# Positive adjustments (pull completion date forward)
POSITIVE_PATTERNS = [
    (r"searches?\s+(?:received|returned|came\s+back|clear|back|satisfactor)",
     -3, "Searches returned on time"),
    (r"search\s+results?\s+(?:received|satisfactor|available|returned|back)",
     -3, "Search results received"),
    (r"survey\s+complete[d]?\s*(?:—|-)?\s*no\s+(?:issues?|problems?|concerns?)",
     -5, "Survey completed — no issues"),
    (r"survey\s+(?:came\s+back|returned?|report)\s*(?:—|-)?\s*(?:clear|clean|satisfactor|no\s+(?:issues?|problems?))",
     -5, "Survey clear — no issues"),
    (r"(?:building|homebuyer)\s+survey\s+(?:no\s+(?:issues?|problems?|concerns?)|satisfactor|clear)",
     -5, "Survey satisfactory"),
    (r"mortgage\s+offer\s+(?:received|issued|confirmed|in)\s*(?:—|-)?\s*(?:ahead|early|before)",
     -5, "Mortgage offer received ahead of schedule"),
    (r"mortgage\s+(?:approved|confirmed|offer\s+received|offer\s+issued)",
     -5, "Mortgage offer received"),
    (r"draft\s+contracts?\s+(?:issued|sent|received)\s*(?:—|-)?\s*(?:early|ahead|prompt)",
     -3, "Draft contracts issued early"),
    (r"draft\s+contracts?\s+(?:issued|sent|received)",
     -3, "Draft contracts issued"),
    (r"(?:all\s+)?enquir(?:ies|ys|es)\s+(?:answered|resolved|dealt\s+with|satisfied|cleared)\s+(?:within|in)\s+(?:a\s+)?(?:week|7\s+days|5\s+days)",
     -5, "Enquiries answered promptly"),
    (r"(?:all\s+)?enquir(?:ies|ys|es)\s+(?:answered|resolved|dealt\s+with|satisfied|cleared)",
     -5, "Enquiries answered"),
    (r"completion\s+(?:date\s+)?(?:agreed|confirmed|set)\s+(?:by|with)\s+all\s+parties",
     0, "Completion date agreed by all parties"),  # 0 = triggers exact date logic
    (r"chain\s+(?:party|buyer|seller)\s+(?:complete[ds]?\s+early|ahead\s+of\s+schedule)",
     -3, "Chain party completed early"),
]

# Negative adjustments (push completion date back)
NEGATIVE_PATTERNS = [
    (r"searches?\s+delayed",
     10, "Searches delayed"),
    (r"(?:local\s+authority|la)\s+search(?:es)?\s+(?:delayed|backlog|slow)",
     10, "Local authority search backlog"),
    (r"(?:adverse|damp|subsidence|structural|underpinning|crack|movement)\s+(?:in\s+)?(?:survey|report|found|issue|flagg)",
     30, "Adverse survey — structural/damp issue"),
    (r"survey\s+(?:flagg|reveal|show|found|identif|highlight)(?:ed|s|ing)?\s+(?:damp|subsidence|structural|crack|movement|asbestos|japanese\s+knotweed|rot)",
     30, "Adverse survey findings"),
    (r"(?:down[-\s]?valuation|valu(?:ation|ed)\s+(?:below|under|short|lower)|shortfall\s+of\s+£?\d)",
     15, "Mortgage down-valuation"),
    (r"(?:buyer|purchaser)\s+(?:renegotiat|request(?:ing|ed)\s+(?:a\s+)?(?:price\s+)?(?:reduction|discount))",
     10, "Buyer renegotiating after survey"),
    (r"solicitor\s+(?:not\s+respond|unresponsive|no\s+response|gone\s+quiet|not\s+replied|no\s+contact)",
     10, "Solicitor not responding"),
    (r"(?:buyer|seller)\s+(?:solicitor|sol)\s+unresponsive",
     10, "Solicitor unresponsive"),
    (r"enquir(?:ies|ys|es)\s+(?:unanswered|outstanding|not\s+(?:yet\s+)?(?:answered|resolved|dealt\s+with))\s+(?:after|for)\s+(?:2|two|14\s+days|a\s+fortnight)",
     10, "Enquiries unanswered after 2 weeks"),
    (r"enquir(?:ies|ys|es)\s+(?:not\s+yet\s+raised|still\s+outstanding|still\s+unanswered)",
     10, "Enquiries still outstanding"),
    (r"(?:leasehold\s+)?management\s+pack\s+(?:delayed|not\s+(?:yet\s+)?received|outstanding|waiting)",
     15, "Leasehold management pack delayed"),
    (r"(?:lpe1|management\s+pack|service\s+charge)\s+(?:delayed|not\s+received|awaiting|outstanding)",
     15, "Leasehold management pack delayed"),
    (r"indemnity\s+(?:insurance|policy)\s+(?:needed|required|necessary|requested)",
     10, "Indemnity insurance needed"),
    (r"deed\s+of\s+variation\s+(?:required|needed|necessary)",
     15, "Deed of variation required"),
    (r"boundary\s+(?:dispute|issue|problem|disagreement)",
     20, "Boundary dispute"),
    (r"(?:missing|no)\s+(?:planning\s+permission|building\s+reg(?:ulation)?s?|completion\s+certificate|planning\s+consent)",
     20, "Missing planning permission or building regs"),
    (r"chain\s+(?:party|buyer|seller)\s+(?:fall(?:s|en)?\s+through|pull(?:s|ed)?\s+out|withdraw)",
     25, "Chain party fallen through"),
    (r"(?:divorce|matrimonial|separation)\s+(?:involved|proceedings|settlement|order)",
     20, "Divorce/matrimonial involvement"),
    (r"probate\s+(?:grant\s+)?(?:not\s+(?:yet\s+)?received|outstanding|awaiting|pending|delayed)",
     30, "Probate grant not received"),
    (r"probate\s+(?:required|needed|necessary|involved)",
     30, "Probate involvement"),
]

# Critical adjustments (major recalculation)
CRITICAL_PATTERNS = [
    (r"buyer\s+(?:has\s+)?withdraw(?:n|s)",
     "fallen_through", "Buyer has withdrawn"),
    (r"buyer\s+pull(?:s|ed)?\s+out",
     "fallen_through", "Buyer has pulled out"),
    (r"seller\s+(?:has\s+)?(?:pull(?:s|ed)?\s+out|withdraw)",
     "fallen_through", "Seller has pulled out"),
    (r"sale\s+(?:has\s+)?(?:fallen\s+through|collapsed)",
     "fallen_through", "Sale fallen through"),
    (r"no\s+longer\s+(?:wish(?:es)?|intend(?:s)?)\s+to\s+proceed",
     "fallen_through", "Party no longer proceeding"),
    (r"chain\s+(?:has\s+)?(?:collapsed|broken)",
     "chain_collapse", "Chain collapsed"),
    (r"chain\s+break",
     "chain_collapse", "Chain break detected"),
    (r"gazump(?:ed|ing)",
     "gazumped", "Gazumping detected"),
    (r"gazunder(?:ed|ing)",
     "gazundered", "Gazundering detected"),
    (r"mortgage\s+(?:application|offer)\s+(?:has\s+been\s+)?(?:declined|refused|rejected|withdrawn)",
     "mortgage_declined", "Mortgage declined"),
]


def _scan_text_for_adjustments(text):
    """Scan a single text (note or email body) for dynamic adjustments.

    Returns:
        list of (days, reason, category) tuples
        category is 'positive', 'negative', or 'critical'
    """
    adjustments = []
    text_lower = text.lower()

    # Positive
    for pattern, days, reason in POSITIVE_PATTERNS:
        if re.search(pattern, text_lower):
            adjustments.append((days, reason, "positive"))

    # Negative
    for pattern, days, reason in NEGATIVE_PATTERNS:
        if re.search(pattern, text_lower):
            adjustments.append((days, reason, "negative"))

    # Critical
    for pattern, event_type, reason in CRITICAL_PATTERNS:
        if re.search(pattern, text_lower):
            # Map critical events to day adjustments
            if event_type == "fallen_through":
                adjustments.append((0, reason, "critical_fallen_through"))
            elif event_type == "chain_collapse":
                adjustments.append((30, reason, "critical_chain"))
            elif event_type == "gazumped":
                adjustments.append((0, reason, "critical_gazumped"))
            elif event_type == "gazundered":
                adjustments.append((15, reason, "critical_gazundered"))
            elif event_type == "mortgage_declined":
                adjustments.append((25, reason, "critical_mortgage"))

    return adjustments


# ─────────────────────────────────────────────────────────────
#  HELPER: working days calculation
# ─────────────────────────────────────────────────────────────

def _working_days_between(start_date, end_date):
    """Count working days (Mon-Fri) between two dates, inclusive of start."""
    if start_date > end_date:
        return -_working_days_between(end_date, start_date)
    count = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # Mon=0 .. Fri=4
            count += 1
        current += timedelta(days=1)
    return count


def _add_working_days(start_date, working_days):
    """Add N working days to a date."""
    if working_days == 0:
        return start_date
    direction = 1 if working_days > 0 else -1
    remaining = abs(working_days)
    current = start_date
    while remaining > 0:
        current += timedelta(days=direction)
        if current.weekday() < 5:
            remaining -= 1
    return current


def _parse_date(date_str):
    """Parse a date string to a date object."""
    if not date_str:
        return None
    if isinstance(date_str, date):
        return date_str
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


# ─────────────────────────────────────────────────────────────
#  STEP 3 HELPER: infer static fields from chain_position text
# ─────────────────────────────────────────────────────────────

def _infer_buyer_type_from_chain(chain_text):
    """Try to infer buyer type from chain_position text."""
    if not chain_text:
        return None
    ct = chain_text.lower()
    if "cash buyer" in ct or "cash purchase" in ct or "no mortgage" in ct:
        return "cash"
    if "first-time buyer" in ct or "first time buyer" in ct:
        return "ftb"
    if "investor" in ct or "buy to let" in ct or "btl" in ct:
        return "investor"
    return None


def _infer_chain_from_text(chain_text):
    """Try to infer chain length from chain_position text."""
    if not chain_text:
        return None
    ct = chain_text.lower()
    if any(p in ct for p in ["no chain", "chain-free", "chain free",
                              "first-time buyer", "first time buyer",
                              "cash buyer", "currently renting",
                              "no onward chain", "no property to sell",
                              "no uk chain", "moving to rented",
                              "moving to family", "moving abroad",
                              "relocating from"]):
        return 1
    # Look for mentions of specific chain properties
    chain_mentions = re.findall(r"selling\s+(?:in\s+)?(?:\w+)", ct)
    if len(chain_mentions) >= 2:
        return 3
    if len(chain_mentions) == 1:
        return 2
    return 2  # default assumption


def _check_last_activity(db, property_id):
    """Check days since last note/activity for staleness detection."""
    row = db.execute(
        """SELECT MAX(created_date) as last_note
           FROM notes WHERE property_id = ?""",
        (property_id,),
    ).fetchone()
    if row and row["last_note"]:
        try:
            last = datetime.strptime(row["last_note"][:19], "%Y-%m-%d %H:%M:%S").date()
            return (date.today() - last).days
        except (ValueError, TypeError):
            pass
    return None


# ─────────────────────────────────────────────────────────────
#  MAIN CALCULATION
# ─────────────────────────────────────────────────────────────

def calculate_completion(property_slug):
    """Calculate the time-based completion estimate for a property.

    Args:
        property_slug: The property slug (e.g. 'stalled', 'on-track-1')

    Returns:
        dict with keys:
            property_id, property_slug, address,
            offer_date, baseline_weeks, adjusted_total_days,
            adjusted_total_weeks, expected_completion_date,
            days_elapsed, days_remaining,
            progress_percentage, status,
            adjustments_applied (list of dicts),
            is_fallen_through, critical_alerts
    """
    db = get_db()

    # ── Fetch property ────────────────────────────────────────
    prop = db.execute(
        """SELECT p.*,
                  b.name AS buyer_name
           FROM properties p
           LEFT JOIN buyers b ON b.property_id = p.id
           WHERE p.slug = ?""",
        (property_slug,),
    ).fetchone()

    if not prop:
        db.close()
        return {"error": f"Property '{property_slug}' not found"}

    property_id = prop["id"]
    offer_date = _parse_date(prop["offer_accepted_date"])

    if not offer_date:
        db.close()
        return {
            "error": f"No offer accepted date for '{property_slug}'",
            "property_slug": property_slug,
            "address": prop["address"],
        }

    # ── STEP 1: Baseline ──────────────────────────────────────
    baseline_days = BASELINE_WEEKS * WORKING_DAYS_PER_WEEK  # 80 working days
    adjustments = []

    # ── STEP 2: Static adjustments ─────────────────────────────

    # Buyer type — use DB field or infer from chain text
    buyer_type = prop["buyer_type"] if prop["buyer_type"] else _infer_buyer_type_from_chain(prop["chain_position"])
    adj = _adjust_buyer_type(buyer_type)
    if adj:
        adjustments.append({
            "category": "static",
            "type": "buyer_type",
            "days": adj[0],
            "reason": adj[1],
        })

    # Chain
    chain_length = prop["chain_length"]
    if chain_length is None:
        chain_length = _infer_chain_from_text(prop["chain_position"])
    adj = _adjust_chain(chain_length, prop["chain_position"])
    if adj:
        adjustments.append({
            "category": "static",
            "type": "chain",
            "days": adj[0],
            "reason": adj[1],
        })

    # Property type
    adj = _adjust_property_type(prop["property_type"])
    if adj:
        adjustments.append({
            "category": "static",
            "type": "property_type",
            "days": adj[0],
            "reason": adj[1],
        })

    # Mortgage complexity
    adj = _adjust_mortgage(prop["mortgage_type"])
    if adj:
        adjustments.append({
            "category": "static",
            "type": "mortgage",
            "days": adj[0],
            "reason": adj[1],
        })

    # Solicitor quality
    adj = _adjust_solicitor(prop["solicitor_type"])
    if adj:
        adjustments.append({
            "category": "static",
            "type": "solicitor",
            "days": adj[0],
            "reason": adj[1],
        })

    # ── STEP 3: Dynamic adjustments from notes & emails ────────
    notes = db.execute(
        """SELECT note_text, source, created_date
           FROM notes WHERE property_id = ?
           ORDER BY created_date ASC""",
        (property_id,),
    ).fetchall()

    # Track which adjustments we've already applied to avoid double-counting
    # e.g. if 3 notes mention "searches delayed", only count once
    applied_reasons = set()
    is_fallen_through = False
    critical_alerts = []

    for note in notes:
        text_adjustments = _scan_text_for_adjustments(note["note_text"])
        for days, reason, category in text_adjustments:
            if reason in applied_reasons:
                continue  # Don't double-count
            applied_reasons.add(reason)

            if category == "critical_fallen_through":
                is_fallen_through = True
                critical_alerts.append(reason)
                adjustments.append({
                    "category": "critical",
                    "type": "fallen_through",
                    "days": 0,
                    "reason": reason,
                    "source": note["source"],
                })
            elif category == "critical_gazumped":
                critical_alerts.append(reason)
                adjustments.append({
                    "category": "critical",
                    "type": "gazumped",
                    "days": 0,
                    "reason": reason,
                    "source": note["source"],
                })
            elif category.startswith("critical_"):
                critical_alerts.append(reason)
                adjustments.append({
                    "category": "critical",
                    "type": category.replace("critical_", ""),
                    "days": days,
                    "reason": reason,
                    "source": note["source"],
                })
            else:
                adjustments.append({
                    "category": category,
                    "type": "dynamic",
                    "days": days,
                    "reason": reason,
                    "source": note["source"],
                })

    # ── Check for explicit completion date in DB ───────────────
    explicit_completion = _parse_date(prop["completion_date"])
    explicit_exchange = _parse_date(prop["exchange_date"])

    # ── STEP 4: Calculate ──────────────────────────────────────

    # Sum adjustments
    total_static = sum(a["days"] for a in adjustments if a["category"] == "static")
    total_positive = sum(a["days"] for a in adjustments if a["category"] == "positive")
    total_negative = sum(a["days"] for a in adjustments if a["category"] == "negative")
    total_critical = sum(a["days"] for a in adjustments if a["category"] == "critical")

    adjusted_total_days = baseline_days + total_static + total_positive + total_negative + total_critical
    # Floor at 20 working days minimum
    adjusted_total_days = max(adjusted_total_days, 20)

    expected_completion = _add_working_days(offer_date, adjusted_total_days)

    # If an explicit completion date is set and agreed, use it
    if explicit_completion and explicit_completion > date.today():
        expected_completion = explicit_completion

    # Calculate elapsed and remaining
    today = date.today()
    days_elapsed = _working_days_between(offer_date, today)
    days_remaining = _working_days_between(today, expected_completion)
    if days_remaining < 0:
        days_remaining = 0

    # Progress percentage based on TIME
    if adjusted_total_days > 0:
        progress_pct = min(round((days_elapsed / adjusted_total_days) * 100), 99)
    else:
        progress_pct = 0

    # Don't show negative progress
    if progress_pct < 0:
        progress_pct = 0

    # ── Determine status ───────────────────────────────────────
    if is_fallen_through:
        status = "stalled"
    elif critical_alerts:
        status = "at-risk"
    else:
        # Check staleness — no activity in 14+ days
        days_since_last = _check_last_activity(db, property_id)
        days_since_update_val = prop["days_since_update"] or 0

        # Check milestones for key incomplete ones
        milestones = db.execute(
            "SELECT milestone_name, is_complete FROM milestones WHERE property_id = ?",
            (property_id,),
        ).fetchall()
        key_milestones_incomplete = []
        for m in milestones:
            if m["is_complete"] == 0 and m["milestone_name"] in (
                "Searches Received", "Survey Complete", "Mortgage Offer",
                "Enquiries Answered", "Exchange"
            ):
                key_milestones_incomplete.append(m["milestone_name"])

        if (days_since_last and days_since_last >= 14) or days_since_update_val >= 14:
            status = "stalled"
        elif progress_pct > 80 and len(key_milestones_incomplete) >= 2:
            status = "at-risk"
        elif progress_pct > 90 and len(key_milestones_incomplete) >= 1:
            status = "at-risk"
        elif any(a["category"] == "negative" for a in adjustments):
            # Negative events detected — flag as at-risk
            negative_days = sum(a["days"] for a in adjustments if a["category"] == "negative")
            if negative_days >= 20:
                status = "at-risk"
            else:
                status = "on-track"
        else:
            status = "on-track"

    # Adjusted total in weeks for display
    adjusted_total_weeks = round(adjusted_total_days / WORKING_DAYS_PER_WEEK, 1)

    db.close()

    return {
        "property_id": property_id,
        "property_slug": property_slug,
        "address": prop["address"],
        "offer_date": offer_date.isoformat() if offer_date else None,
        "baseline_weeks": BASELINE_WEEKS,
        "baseline_days": baseline_days,
        "adjusted_total_days": adjusted_total_days,
        "adjusted_total_weeks": adjusted_total_weeks,
        "expected_completion_date": expected_completion.isoformat(),
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "progress_percentage": progress_pct,
        "status": status,
        "is_fallen_through": is_fallen_through,
        "critical_alerts": critical_alerts,
        "adjustments_applied": adjustments,
        "adjustment_summary": {
            "static": total_static,
            "positive": total_positive,
            "negative": total_negative,
            "critical": total_critical,
            "net": total_static + total_positive + total_negative + total_critical,
        },
    }


# ─────────────────────────────────────────────────────────────
#  RECALCULATE + PERSIST TO DB
# ─────────────────────────────────────────────────────────────

def recalculate_property(property_db_id):
    """Recalculate completion engine for a property and persist results.

    Called automatically after notes are added or emails are parsed.

    Args:
        property_db_id: The database integer ID of the property

    Returns:
        The full calculation dict, or None if the property wasn't found.
    """
    db = get_db()
    row = db.execute("SELECT slug FROM properties WHERE id = ?", (property_db_id,)).fetchone()
    db.close()

    if not row:
        return None

    result = calculate_completion(row["slug"])

    if "error" in result:
        return result

    # Persist key fields back to the properties table
    db = get_db()
    db.execute(
        """UPDATE properties SET
               progress_percentage = ?,
               status = ?,
               target_days = ?,
               updated_at = datetime('now')
           WHERE id = ?""",
        (
            result["progress_percentage"],
            result["status"],
            result["days_remaining"],
            property_db_id,
        ),
    )
    db.commit()
    db.close()

    return result


def recalculate_all():
    """Recalculate completion engine for ALL properties.

    Returns:
        list of result dicts
    """
    db = get_db()
    rows = db.execute("SELECT slug FROM properties").fetchall()
    db.close()

    results = []
    for row in rows:
        result = calculate_completion(row["slug"])
        if "error" not in result:
            # Persist
            db = get_db()
            db.execute(
                """UPDATE properties SET
                       progress_percentage = ?,
                       status = ?,
                       target_days = ?,
                       updated_at = datetime('now')
                   WHERE slug = ?""",
                (
                    result["progress_percentage"],
                    result["status"],
                    result["days_remaining"],
                    row["slug"],
                ),
            )
            db.commit()
            db.close()
        results.append(result)

    return results


# ─────────────────────────────────────────────────────────────
#  CLI — run directly to test
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import json as _json

    if len(sys.argv) > 1:
        slug = sys.argv[1]
        result = calculate_completion(slug)
        print(_json.dumps(result, indent=2, default=str))
    else:
        print("Recalculating all properties...")
        results = recalculate_all()
        for r in results:
            if "error" in r:
                print(f"  [SKIP] {r.get('property_slug', '?')}: {r['error']}")
            else:
                status_icon = {"on-track": "\u2705", "at-risk": "\u26A0\uFE0F", "stalled": "\U0001F6A8"}.get(r["status"], "?")
                print(f"  {status_icon} {r['property_slug']:25s}  {r['progress_percentage']:3d}%  "
                      f"{r['days_remaining']:3d}d remaining  "
                      f"({len(r['adjustments_applied'])} adjustments)  "
                      f"→ {r['expected_completion_date']}")
        print(f"\nDone — {len(results)} properties recalculated.")
