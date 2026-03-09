"""
NUVU AI Note Parser
====================
Analyzes free-text agent notes and returns structured updates:
milestones to complete, dates found, issues flagged, suggested actions.

Uses keyword/phrase matching for now — designed for easy upgrade to
full NLP/LLM later.

Usage:
    from ai_parser import parse_note, apply_ai_results
    result = parse_note("Searches came back clear, survey booked for 14th March")
    apply_ai_results(db, property_id, result)
"""

import re
from datetime import datetime, date


# ─────────────────────────────────────────────────────────────
#  FUZZY ENQUIRY PATTERN
# ─────────────────────────────────────────────────────────────
# Catches: enquiries, enquirys, enquires, enquirees, enqiries, queries, querys
# One reusable fragment used in all enquiry-related patterns.
_ENQ = r"(?:enqu?ir(?:y|ies|ys|es|ees|i?es)|quer(?:y|ies|ys))"

# Verbs that indicate enquiries are done
_ENQ_DONE = r"(?:answered|resolved|dealt\s+with|done|complete[d]?|received|back|sorted|satisfied|responded\s+to|cleared)"


# ─────────────────────────────────────────────────────────────
#  MILESTONE PATTERNS
# ─────────────────────────────────────────────────────────────
# Each entry: milestone_name → list of regex patterns that trigger it.
# All patterns are matched case-insensitive against the full note text.

MILESTONE_PATTERNS = {
    "Offer Accepted": [
        r"offer\s+accepted",
        r"accepted\s+the\s+offer",
        r"offer\s+agreed",
    ],
    "Memorandum Sent": [
        r"memo(?:randum)?\s+sent",
        r"sent\s+(?:the\s+)?memo(?:randum)?",
        r"memo(?:randum)?\s+(?:of\s+sale\s+)?issued",
        r"protocol\s+forms?\s+sent",
        r"draft\s+contracts?\s+issued",
        r"draft\s+contracts?\s+sent",
    ],
    "Searches Ordered": [
        r"searches?\s+ordered",
        r"ordered\s+(?:the\s+)?searches",
        r"submitted\s+(?:the\s+)?search(?:es)?",
        r"instructed\s+searches",
    ],
    "Searches Received": [
        r"searches?\s+received",
        r"searches?\s+(?:came|come)\s+back",
        r"searches?\s+returned",
        r"searches?\s+(?:are\s+)?clear",
        r"(?:got|received)\s+(?:the\s+)?search(?:es)?\s+(?:results?|back)",
        r"search\s+results?\s+(?:received|back|in)",
    ],
    "Survey Complete": [
        r"survey\s+complete[d]?",
        r"survey\s+(?:came|come)\s+back",
        r"survey\s+report\s+received",
        r"survey\s+done",
        r"survey\s+results?\s+(?:received|back|in)",
        r"surveyor['\u2019]?s?\s+report\s+(?:received|back|in)",
    ],
    "Enquiries Raised": [
        _ENQ + r"\s+raised",
        r"raised\s+(?:the\s+)?" + _ENQ,
        r"additional\s+" + _ENQ + r"\s+(?:sent|raised)",
        r"pre[-\s]?contract\s+" + _ENQ + r"\s+(?:sent|raised)",
        r"solicitor\s+(?:has\s+)?raised\s+" + _ENQ,
    ],
    "Enquiries Answered": [
        _ENQ + r"\s+(?:(?:have|has|been|are|all|now)\s+)*" + _ENQ_DONE,
        _ENQ_DONE + r"\s+(?:the\s+|all\s+)?" + _ENQ,
        r"all\s+" + _ENQ + r"\s+(?:(?:have|has|been|are|now)\s+)*" + _ENQ_DONE,
        r"repl(?:y|ies|ied)\s+to\s+(?:(?:the|all)\s+)*" + _ENQ,
    ],
    "Mortgage Offer": [
        r"mortgage\s+offer\s+(?:received|issued|confirmed|in)",
        r"(?:got|received)\s+(?:the\s+)?mortgage\s+offer",
        r"mortgage\s+(?:is\s+)?(?:approved|confirmed)",
        r"lender\s+(?:has\s+)?(?:issued|confirmed)\s+(?:the\s+)?offer",
        r"formal\s+mortgage\s+offer",
    ],
    "Exchange": [
        r"contracts?\s+exchanged",
        r"exchange[d]?\s+contracts?",
        r"we['\u2019]?ve\s+exchanged",
        r"exchange\s+(?:has\s+)?(?:taken\s+place|happened|complete[d]?)",
    ],
    "Completion": [
        r"completion\s+(?:has\s+)?(?:taken\s+place|happened|complete[d]?|done)",
        r"completed\s+today",
        r"keys?\s+(?:handed|released|collected)",
        r"sale\s+complete[d]?",
    ],
}

# Also detect "survey booked" separately (not the same as survey complete)
SURVEY_BOOKED_PATTERNS = [
    r"survey\s+booked",
    r"booked\s+(?:a\s+|the\s+)?survey",
    r"surveyor\s+(?:booked|instructed|appointed)",
    r"instructed\s+(?:a\s+|the\s+)?surveyor",
    r"survey\s+(?:arranged|scheduled|set\s+up)",
]


# ─────────────────────────────────────────────────────────────
#  DATE EXTRACTION
# ─────────────────────────────────────────────────────────────
# Recognises: "15th March", "15 March 2026", "15/03/2026", "2026-03-15", etc.

MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "sept": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

DATE_PATTERNS = [
    # "15th March 2026" or "15 March" or "15th Mar"
    r"(\d{1,2})(?:st|nd|rd|th)?\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s*(\d{4})?",
    # "March 15th 2026" or "March 15"
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})?",
    # "15/03/2026" or "15-03-2026"
    r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})",
]


def extract_dates(text):
    """Return list of (date_str, date_obj) tuples found in text."""
    results = []
    now = datetime.now()
    text_lower = text.lower()

    # Pattern 1: "15th March 2026"
    for m in re.finditer(DATE_PATTERNS[0], text_lower):
        day = int(m.group(1))
        month = MONTH_MAP.get(m.group(2).rstrip("."))
        year = int(m.group(3)) if m.group(3) else now.year
        if month and 1 <= day <= 31:
            try:
                d = date(year, month, day)
                results.append((d.strftime("%d/%m/%Y"), d))
            except ValueError:
                pass

    # Pattern 2: "March 15th 2026"
    for m in re.finditer(DATE_PATTERNS[1], text_lower):
        month = MONTH_MAP.get(m.group(1).rstrip("."))
        day = int(m.group(2))
        year = int(m.group(3)) if m.group(3) else now.year
        if month and 1 <= day <= 31:
            try:
                d = date(year, month, day)
                results.append((d.strftime("%d/%m/%Y"), d))
            except ValueError:
                pass

    # Pattern 3: "15/03/2026"
    for m in re.finditer(DATE_PATTERNS[2], text_lower):
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            try:
                d = date(year, month, day)
                results.append((d.strftime("%d/%m/%Y"), d))
            except ValueError:
                pass

    return results


# ─────────────────────────────────────────────────────────────
#  DATE-TO-FIELD CONTEXT PATTERNS
# ─────────────────────────────────────────────────────────────
# When a date is found near these keywords, update the corresponding
# property column.

DATE_CONTEXT = [
    (r"exchange\w*\s+(?:agreed|set|date|on|for|target)", "exchange_date"),
    (r"(?:agreed|set|date|on|for|target)\s+\w*\s*exchange", "exchange_date"),
    (r"complet(?:ion|e|ing)\s+(?:set|date|on|for|target|agreed)", "completion_date"),
    (r"(?:set|date|on|for|target|agreed)\s+\w*\s*complet(?:ion|e)", "completion_date"),
    (r"survey\s+(?:booked|arranged|scheduled)\s+(?:for|on)", "survey_booked"),
]


# ─────────────────────────────────────────────────────────────
#  ISSUE / RISK PATTERNS
# ─────────────────────────────────────────────────────────────

ISSUE_PATTERNS = [
    # Solicitor issues
    (r"(?:buyer['\u2019]?s?\s+)?solicitor\s+(?:not\s+)?respond(?:ing)?",
     "Buyer's solicitor not responding",
     "Chase buyer's solicitor for update"),
    (r"(?:seller['\u2019]?s?\s+)?solicitor\s+(?:not\s+)?respond(?:ing)?",
     "Seller's solicitor not responding",
     "Chase seller's solicitor for update"),
    (r"chasing\s+(?:buyer['\u2019]?s?\s+)?solicitor",
     "Buyer's solicitor being chased",
     "Follow up with buyer's solicitor"),
    (r"chasing\s+(?:seller['\u2019]?s?\s+)?solicitor",
     "Seller's solicitor being chased",
     "Follow up with seller's solicitor"),
    (r"solicitor\s+(?:is\s+)?(?:slow|delayed|unresponsive|dragging)",
     "Solicitor delay",
     "Escalate with solicitor — request timeline"),

    # Survey issues
    (r"survey\s+(?:found|flagged|revealed|showed|identified)\s+(?:damp|issues?|problems?|defects?)",
     "Adverse survey findings",
     "Discuss survey findings with buyer and negotiate"),
    (r"adverse\s+survey",
     "Adverse survey findings",
     "Review survey report and discuss with buyer"),
    (r"survey\s+(?:is\s+)?overdue",
     "Survey overdue",
     "Chase surveyor for completion date"),

    # Buyer/seller issues
    (r"buyer\s+(?:requesting|wants?|asking)\s+(?:a\s+)?(?:price\s+)?reduction",
     "Buyer requesting price reduction",
     "Negotiate price reduction between parties"),
    (r"buyer\s+(?:is\s+)?(?:pulling\s+out|withdrawing|having\s+doubts?|cold\s+feet)",
     "Buyer may withdraw",
     "Urgent: contact buyer to discuss concerns"),
    (r"seller\s+(?:is\s+)?(?:pulling\s+out|withdrawing|changing\s+mind|having\s+doubts?)",
     "Seller may withdraw",
     "Urgent: contact seller to discuss concerns"),
    (r"chain\s+(?:(?:has\s+)?(?:broken|collapsed)|issue|problem)",
     "Chain issue",
     "Assess chain break impact and contact all parties"),

    # Search issues
    (r"search(?:es)?\s+(?:delayed|overdue|slow|backlog)",
     "Searches delayed",
     "Contact local authority for search timeline"),

    # Mortgage issues
    (r"mortgage\s+(?:declined|refused|rejected|issue|problem|delayed)",
     "Mortgage issue",
     "Contact mortgage broker urgently"),
    (r"(?:down\s+)?valuation\s+(?:came\s+in\s+)?(?:low|short|under)",
     "Down valuation",
     "Discuss down-valuation options with buyer and lender"),
]

# Patterns that should push status to "at-risk"
AT_RISK_TRIGGERS = [
    r"adverse\s+survey",
    r"survey\s+(?:found|flagged|revealed)\s+(?:damp|issues?|problems?|defects?)",
    r"buyer\s+(?:requesting|wants?)\s+(?:a\s+)?(?:price\s+)?reduction",
    r"buyer\s+(?:is\s+)?(?:pulling\s+out|withdrawing|cold\s+feet)",
    r"seller\s+(?:is\s+)?(?:pulling\s+out|withdrawing)",
    r"chain\s+(?:(?:has\s+)?(?:broken|collapsed))",
    r"mortgage\s+(?:declined|refused|rejected)",
    r"(?:down\s+)?valuation\s+(?:came\s+in\s+)?(?:low|short|under)",
]


# ─────────────────────────────────────────────────────────────
#  MAIN PARSER
# ─────────────────────────────────────────────────────────────

def parse_note(note_text):
    """
    Analyze free-text note and return structured results.

    Returns dict:
        milestones_completed : list of str   — milestone names to mark done
        dates_found          : list of str   — "dd/mm/yyyy" dates found
        date_updates         : dict          — {db_column: "dd/mm/yyyy"}
        issues               : list of dict  — [{description, suggested_action}]
        suggested_action     : str or None   — override next_action on property
        set_at_risk          : bool          — should property status become at-risk?
        survey_booked        : bool          — "Survey booked" detected (not a milestone)
        summary              : list of str   — human-readable summary lines
    """
    text = note_text.strip()
    text_lower = text.lower()

    result = {
        "milestones_completed": [],
        "dates_found": [],
        "date_updates": {},
        "issues": [],
        "suggested_action": None,
        "set_at_risk": False,
        "survey_booked": False,
        "summary": [],
    }

    # ── Milestone detection ──────────────────────────────────
    for milestone_name, patterns in MILESTONE_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text_lower):
                if milestone_name not in result["milestones_completed"]:
                    result["milestones_completed"].append(milestone_name)
                break

    # ── Survey booked (property column, not a milestone table entry) ─
    for pat in SURVEY_BOOKED_PATTERNS:
        if re.search(pat, text_lower):
            result["survey_booked"] = True
            break

    # ── Date extraction ──────────────────────────────────────
    dates = extract_dates(text)
    result["dates_found"] = [d[0] for d in dates]

    # Try to assign dates to property fields based on context
    if dates:
        for ctx_pat, db_col in DATE_CONTEXT:
            if re.search(ctx_pat, text_lower):
                result["date_updates"][db_col] = dates[0][0]
                break

        # If survey booked and a date found, it's likely the survey date
        if result["survey_booked"] and "survey_booked" not in result["date_updates"]:
            result["date_updates"]["survey_booked"] = dates[0][0]

    # ── Issue detection ──────────────────────────────────────
    for pat, desc, action in ISSUE_PATTERNS:
        if re.search(pat, text_lower):
            result["issues"].append({
                "description": desc,
                "suggested_action": action,
            })
            if not result["suggested_action"]:
                result["suggested_action"] = action

    # ── At-risk trigger ──────────────────────────────────────
    for pat in AT_RISK_TRIGGERS:
        if re.search(pat, text_lower):
            result["set_at_risk"] = True
            break

    # ── Build human-readable summary ─────────────────────────
    for ms in result["milestones_completed"]:
        result["summary"].append(f"{ms} \u2713")

    if result["survey_booked"]:
        date_part = ""
        if "survey_booked" in result["date_updates"]:
            date_part = f" for {result['date_updates']['survey_booked']}"
        result["summary"].append(f"Survey booked{date_part}")

    for col, val in result["date_updates"].items():
        if col == "exchange_date":
            result["summary"].append(f"Exchange date: {val}")
        elif col == "completion_date":
            result["summary"].append(f"Completion date: {val}")

    for issue in result["issues"]:
        result["summary"].append(f"\u26A0 {issue['description']}")

    if result["set_at_risk"]:
        result["summary"].append("\u26A0 Status \u2192 At Risk")

    return result


# ─────────────────────────────────────────────────────────────
#  APPLY RESULTS TO DATABASE
# ─────────────────────────────────────────────────────────────

def apply_ai_results(db, property_id, result):
    """
    Write parsed AI results to the database. Returns a summary dict
    of what was changed.

    Args:
        db          : sqlite3 connection (with row_factory = sqlite3.Row)
        property_id : integer PK from properties table
        result      : dict from parse_note()

    Returns dict:
        milestones_updated : int — count of milestones marked complete
        dates_updated      : int — count of date fields set
        status_changed     : bool
        next_action_set    : bool
        audit_note         : str — text for the audit trail note
    """
    changes = {
        "milestones_updated": 0,
        "dates_updated": 0,
        "status_changed": False,
        "next_action_set": False,
        "audit_note": "",
    }

    audit_lines = []
    today = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── Mark milestones complete ─────────────────────────────
    for ms_name in result["milestones_completed"]:
        row = db.execute(
            """SELECT id, is_complete FROM milestones
               WHERE property_id = ? AND milestone_name = ?""",
            (property_id, ms_name),
        ).fetchone()
        if row and row["is_complete"] != 1:
            db.execute(
                """UPDATE milestones SET is_complete = 1, completed_date = ?
                   WHERE id = ?""",
                (today, row["id"]),
            )
            changes["milestones_updated"] += 1
            audit_lines.append(f"Milestone '{ms_name}' marked complete")

    # ── Update date fields on property ───────────────────────
    valid_date_cols = {
        "exchange_date", "completion_date", "survey_booked",
        "survey_complete", "searches_ordered", "searches_received",
        "enquiries_raised", "enquiries_answered", "mortgage_offered",
        "memo_sent_date", "offer_accepted_date",
    }
    for col, val in result["date_updates"].items():
        if col in valid_date_cols:
            db.execute(
                f"UPDATE properties SET {col} = ? WHERE id = ?",
                (val, property_id),
            )
            changes["dates_updated"] += 1
            audit_lines.append(f"Date set: {col} = {val}")

    # ── Survey booked (set property column) ──────────────────
    if result["survey_booked"]:
        date_val = result["date_updates"].get("survey_booked", today[:10])
        db.execute(
            "UPDATE properties SET survey_booked = ? WHERE id = ?",
            (date_val, property_id),
        )
        if "survey_booked" not in result["date_updates"]:
            audit_lines.append("Survey booked date set to today")

    # ── Status change → at-risk ──────────────────────────────
    if result["set_at_risk"]:
        current = db.execute(
            "SELECT status FROM properties WHERE id = ?", (property_id,)
        ).fetchone()
        if current and current["status"] == "on-track":
            db.execute(
                "UPDATE properties SET status = 'at-risk' WHERE id = ?",
                (property_id,),
            )
            changes["status_changed"] = True
            audit_lines.append("Status changed: on-track \u2192 at-risk")

    # ── Update next_action ───────────────────────────────────
    if result["suggested_action"]:
        db.execute(
            "UPDATE properties SET next_action = ? WHERE id = ?",
            (result["suggested_action"], property_id),
        )
        changes["next_action_set"] = True
        audit_lines.append(f"Next action: {result['suggested_action']}")

    # ── Recalculate progress percentage ──────────────────────
    ms_rows = db.execute(
        """SELECT is_complete FROM milestones WHERE property_id = ?""",
        (property_id,),
    ).fetchall()
    total = sum(1 for r in ms_rows if r["is_complete"] is not None)
    done = sum(1 for r in ms_rows if r["is_complete"] == 1)
    new_pct = int((done / total * 100)) if total > 0 else 0
    db.execute(
        "UPDATE properties SET progress_percentage = ?, days_since_update = 0 WHERE id = ?",
        (new_pct, property_id),
    )

    # ── Write audit trail note ───────────────────────────────
    if audit_lines:
        audit_text = "AI parsed: " + "; ".join(audit_lines)
        db.execute(
            """INSERT INTO notes (property_id, note_text, author, source)
               VALUES (?, ?, 'AI Parser', 'api')""",
            (property_id, audit_text),
        )
        changes["audit_note"] = audit_text

    db.commit()
    return changes
