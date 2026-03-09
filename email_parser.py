"""
NUVU Email Parser
==================
Analyzes incoming emails from solicitors, brokers, and other parties
and returns structured property updates: matched property, milestones,
dates, issues, and a human-readable summary.

This is the foundation for automated email inbox processing. Currently
used via the /admin/email-inbox test interface. Will connect to a real
IMAP/Gmail inbox later.

Usage:
    from email_parser import parse_email, process_email

    # Parse only (no DB changes)
    result = parse_email(subject, body, sender)

    # Parse + apply to database + outbound sync
    result = process_email(subject, body, sender)
"""

import re
from datetime import datetime, date

from database import get_db
from ai_parser import (
    MILESTONE_PATTERNS, SURVEY_BOOKED_PATTERNS,
    ISSUE_PATTERNS, AT_RISK_TRIGGERS, DATE_CONTEXT,
    extract_dates, apply_ai_results,
)
from connectors.sync_outbound import push_note_to_crm, push_milestone_to_crm, push_status_to_crm


# ─────────────────────────────────────────────────────────────
#  EMAIL-SPECIFIC MILESTONE PATTERNS
# ─────────────────────────────────────────────────────────────
# These extend the base ai_parser patterns with phrasings more
# common in solicitor/broker emails vs agent notes.

EMAIL_MILESTONE_PATTERNS = {
    "Searches Received": [
        r"searches?\s+have\s+been\s+received",
        r"(?:please\s+find\s+|we\s+enclose\s+)(?:the\s+)?search\s+results?",
        r"search\s+results?\s+(?:are\s+)?(?:now\s+)?available",
        r"(?:local|environmental|drainage)\s+search(?:es)?\s+(?:received|returned|back)",
    ],
    "Memorandum Sent": [
        r"(?:please\s+find\s+attached?\s+)?draft\s+contracts?",
        r"draft\s+contracts?\s+(?:are\s+)?enclosed",
        r"we\s+(?:have\s+)?(?:issued|prepared|sent)\s+(?:the\s+)?draft\s+contracts?",
        r"memorandum\s+of\s+sale",
        r"title\s+deeds?\s+(?:sent|enclosed|attached)",
        r"protocol\s+documents?\s+(?:enclosed|attached|sent)",
    ],
    "Survey Complete": [
        r"survey\s+report\s+(?:is\s+)?(?:attached|enclosed|available)",
        r"surveyor['\u2019]?s?\s+report",
        r"survey\s+(?:has\s+been\s+)?completed",
        r"building\s+survey\s+(?:report|completed|enclosed)",
        r"homebuyer['\u2019]?s?\s+report",
        r"valuation\s+report\s+(?:attached|enclosed|available)",
    ],
    "Mortgage Offer": [
        r"mortgage\s+offer\s+(?:has\s+been\s+)?issued",
        r"formal\s+(?:mortgage\s+)?offer\s+(?:issued|enclosed|attached)",
        r"lender\s+(?:has\s+)?(?:issued|confirmed)\s+(?:the\s+)?(?:formal\s+)?offer",
        r"(?:please\s+find\s+)?(?:attached?\s+)?(?:the\s+)?mortgage\s+offer",
        r"offer\s+of\s+(?:mortgage|advance)\s+(?:issued|enclosed)",
    ],
    "Enquiries Raised": [
        r"we\s+have\s+raised\s+(?:the\s+)?(?:following\s+)?enquir",
        r"enclosed?\s+(?:are\s+)?our\s+enquir",
        r"(?:please\s+find\s+|attached?\s+)(?:our\s+)?(?:additional\s+)?enquir(?:ies|ys|es)",
        r"(?:pre[-\s]?contract\s+)?enquir(?:ies|ys|es)\s+(?:enclosed|attached|herewith)",
        r"raising\s+(?:the\s+following\s+)?enquir",
        r"we\s+(?:require|need)\s+(?:the\s+following\s+)?(?:replies?|answers?|responses?)",
    ],
    "Enquiries Answered": [
        r"replies?\s+to\s+(?:your\s+)?enquir",
        r"(?:answers?|responses?)\s+to\s+(?:your\s+)?enquir",
        r"enquir(?:ies|ys|es)\s+have\s+been\s+(?:answered|dealt\s+with|responded\s+to|resolved)",
        r"all\s+(?:outstanding\s+)?enquir(?:ies|ys|es)\s+(?:have\s+been\s+)?(?:answered|resolved|satisfied)",
        r"(?:please\s+find\s+)?(?:attached?\s+)?(?:our\s+)?replies?\s+to\s+enquir",
        r"we\s+(?:have\s+)?(?:now\s+)?(?:dealt\s+with|answered|responded\s+to)\s+(?:all\s+)?(?:your\s+)?enquir",
    ],
    "Exchange": [
        r"(?:ready|agree[d]?|confirmed?)\s+to\s+exchange",
        r"exchange\s+(?:has\s+been\s+)?(?:agreed|confirmed|set)\s+(?:for|on)",
        r"we\s+(?:are|were)\s+(?:now\s+)?in\s+a\s+position\s+to\s+exchange",
        r"contracts?\s+(?:can\s+be\s+|have\s+been\s+)?exchanged",
        r"exchange\s+(?:to\s+)?take\s+place",
        r"(?:simultaneous\s+)?exchange\s+and\s+completion",
    ],
    "Completion": [
        r"completion\s+(?:has\s+been\s+)?confirmed?\s+(?:for|on)",
        r"completion\s+(?:will\s+)?take\s+place\s+on",
        r"keys?\s+(?:will\s+be\s+|have\s+been\s+)?(?:released|handed\s+over|available)",
        r"(?:simultaneous\s+)?exchange\s+and\s+completion\s+(?:confirmed?|agreed|set)\s+(?:for|on)",
        r"completion\s+date\s+(?:is\s+|has\s+been\s+)?(?:set|agreed|confirmed)\s+(?:as|for|on)",
    ],
}

# ─────────────────────────────────────────────────────────────
#  EMAIL-SPECIFIC ISSUE PATTERNS
# ─────────────────────────────────────────────────────────────
# Critical alerts from solicitor/broker emails

EMAIL_ISSUE_PATTERNS = [
    # Critical alerts
    (r"(?:chain\s+break|chain\s+has\s+(?:broken|collapsed))",
     "CRITICAL: Chain break detected",
     "Urgent: Assess chain break impact — contact all parties immediately"),
    (r"buyer\s+has\s+withdrawn",
     "CRITICAL: Buyer withdrawn",
     "Urgent: Property needs re-listing — contact seller immediately"),
    (r"sale\s+has\s+fallen\s+through",
     "CRITICAL: Sale fallen through",
     "Urgent: Contact all parties — assess whether sale can be salvaged"),
    (r"(?:our\s+)?client\s+(?:wishes?\s+to|has\s+decided\s+to)\s+withdraw",
     "CRITICAL: Client withdrawing",
     "Urgent: Contact all parties — attempt to resolve"),
    (r"no\s+longer\s+(?:wish(?:es)?|intend(?:s)?)\s+to\s+proceed",
     "CRITICAL: Party no longer proceeding",
     "Urgent: Confirm withdrawal and notify all parties"),

    # Issues and delays
    (r"there\s+is\s+(?:an?\s+)?(?:issue|problem|concern)\s+with",
     "Issue flagged by solicitor",
     "Review issue details and respond to solicitor"),
    (r"(?:significant\s+)?delay\s+(?:in|with|to)",
     "Delay reported",
     "Investigate delay cause and update timeline"),
    (r"unable\s+to\s+(?:proceed|complete|exchange)",
     "Unable to proceed — issue raised",
     "Identify blocker and work to resolve"),
    (r"(?:title\s+)?defect(?:s)?\s+(?:found|discovered|identified)",
     "Title defect found",
     "Discuss title defect with solicitor — assess impact"),
    (r"indemnity\s+(?:insurance|policy)\s+(?:required|needed|necessary)",
     "Indemnity insurance required",
     "Instruct solicitor to obtain indemnity quote"),
    (r"retent(?:ion|ion)\s+(?:sum|amount|requested)",
     "Retention requested",
     "Negotiate retention terms between parties"),

    # Mortgage/valuation issues
    (r"(?:down[-\s]?valuation|(?:valuation|survey)\s+(?:(?:has\s+)?(?:come|came)\s+in\s+)?(?:below|under|short|lower))",
     "Down-valuation by lender",
     "Discuss options: renegotiate price, buyer funds shortfall, or new lender"),
    (r"shortfall\s+of\s+\xa3?\d",
     "Down-valuation — financial shortfall",
     "Discuss options: renegotiate price, buyer funds shortfall, or new lender"),
    (r"mortgage\s+(?:application|offer)\s+(?:has\s+been\s+)?(?:declined|refused|rejected|withdrawn)",
     "Mortgage application declined",
     "Urgent: Contact mortgage broker for alternative lender options"),
    (r"lender\s+(?:requires?|needs?)\s+additional\s+(?:information|documentation)",
     "Lender requesting additional information",
     "Contact buyer to supply required documentation promptly"),
]

# Email-specific at-risk patterns (extends ai_parser.AT_RISK_TRIGGERS)
EMAIL_AT_RISK_PATTERNS = [
    r"(?:down[-\s]?valuation|valuation\s+(?:(?:has\s+)?(?:come|came)\s+in\s+)?(?:below|under|short|lower))",
    r"shortfall\s+of",
    r"mortgage\s+(?:application|offer)\s+(?:has\s+been\s+)?(?:declined|refused|rejected|withdrawn)",
    r"there\s+is\s+(?:an?\s+)?(?:issue|problem|concern)\s+with",
    r"(?:significant\s+)?delay\s+(?:in|with|to)",
    r"unable\s+to\s+(?:proceed|complete|exchange)",
    r"(?:title\s+)?defect(?:s)?\s+(?:found|discovered|identified)",
    r"lender\s+(?:requires?|needs?)\s+additional",
]

# Patterns that definitely mean critical / stalled status
EMAIL_CRITICAL_PATTERNS = [
    r"chain\s+(?:has\s+)?(?:broken|collapsed)",
    r"buyer\s+has\s+withdrawn",
    r"sale\s+has\s+fallen\s+through",
    r"no\s+longer\s+(?:wish|intend)(?:es|s)?\s+to\s+proceed",
    r"client\s+(?:wishes?\s+to|has\s+decided\s+to)\s+withdraw",
]


# ─────────────────────────────────────────────────────────────
#  PROPERTY MATCHING
# ─────────────────────────────────────────────────────────────

def _normalise(text):
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _build_search_tokens(prop):
    """Build a list of searchable strings from a property dict."""
    tokens = []

    # Address and location (most common match)
    if prop.get("address"):
        tokens.append(_normalise(prop["address"]))
    if prop.get("location"):
        tokens.append(_normalise(prop["location"]))

    # Full address (address + location combined)
    if prop.get("address") and prop.get("location"):
        tokens.append(_normalise(f"{prop['address']} {prop['location']}"))

    # Buyer name
    if prop.get("buyer"):
        tokens.append(_normalise(prop["buyer"]))
        # Also extract surnames (e.g. "Mr & Mrs Hartley" → "hartley")
        parts = re.findall(r"[A-Z][a-z]+", prop.get("buyer", ""))
        for p in parts:
            if p.lower() not in ("mr", "mrs", "ms", "miss", "dr", "prof"):
                tokens.append(p.lower())

    # Slug (e.g. "ambleside-cottage" → "ambleside cottage")
    if prop.get("id"):
        tokens.append(prop["id"].replace("-", " "))

    return tokens


def match_property(subject, body, sender, properties):
    """Find which property an email relates to.

    Searches subject line first (highest priority), then body.
    Matches against: property address, location, buyer name, slug.

    Args:
        subject:     Email subject line
        body:        Email body text
        sender:      Sender email/name
        properties:  List of property dicts from load_properties()

    Returns:
        tuple: (matched_prop_dict, confidence, match_reason) or (None, 0, None)
               confidence is 0-100
    """
    combined = f"{subject}\n{body}"
    search_text = _normalise(combined)
    subject_norm = _normalise(subject)

    best_match = None
    best_score = 0
    best_reason = None

    for prop in properties:
        tokens = _build_search_tokens(prop)
        score = 0
        reason = None

        for token in tokens:
            if not token or len(token) < 3:
                continue

            # Subject match (high confidence)
            if token in subject_norm:
                candidate_score = 90
                if candidate_score > score:
                    score = candidate_score
                    reason = f"Subject contains '{token}'"

            # Body match
            elif token in search_text:
                # Longer matches get higher confidence
                if len(token) > 15:
                    candidate_score = 80
                elif len(token) > 8:
                    candidate_score = 65
                else:
                    candidate_score = 45
                if candidate_score > score:
                    score = candidate_score
                    reason = f"Body contains '{token}'"

        # Boost if solicitor name appears (strong indicator)
        if prop.get("buyer_solicitor"):
            sol_norm = _normalise(prop["buyer_solicitor"])
            firm = sol_norm.split(",")[0].strip() if "," in sol_norm else sol_norm
            if len(firm) > 4 and firm in search_text:
                score = min(score + 20, 95)
                reason = (reason or "") + f" + solicitor '{firm}' mentioned"

        if prop.get("seller_solicitor"):
            sol_norm = _normalise(prop["seller_solicitor"])
            firm = sol_norm.split(",")[0].strip() if "," in sol_norm else sol_norm
            if len(firm) > 4 and firm in search_text:
                score = min(score + 20, 95)
                reason = (reason or "") + f" + solicitor '{firm}' mentioned"

        # Boost if sender contains solicitor firm name
        if sender:
            sender_norm = _normalise(sender)
            if prop.get("buyer_solicitor"):
                firm = _normalise(prop["buyer_solicitor"]).split(",")[0].strip()
                if len(firm) > 4 and firm in sender_norm:
                    score = min(score + 15, 95)
                    reason = (reason or "") + " + sender is buyer's solicitor"
            if prop.get("seller_solicitor"):
                firm = _normalise(prop["seller_solicitor"]).split(",")[0].strip()
                if len(firm) > 4 and firm in sender_norm:
                    score = min(score + 15, 95)
                    reason = (reason or "") + " + sender is seller's solicitor"

        if score > best_score:
            best_score = score
            best_match = prop
            best_reason = reason

    if best_score >= 40:
        return best_match, best_score, best_reason

    return None, 0, None


# ─────────────────────────────────────────────────────────────
#  EMAIL CONTENT ANALYSIS
# ─────────────────────────────────────────────────────────────

def _detect_milestones(text):
    """Detect milestones from email content.

    Uses both ai_parser MILESTONE_PATTERNS and EMAIL_MILESTONE_PATTERNS.

    Returns:
        list of str: milestone names triggered
    """
    text_lower = text.lower()
    found = []

    # Check email-specific patterns first (higher priority)
    for ms_name, patterns in EMAIL_MILESTONE_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text_lower):
                if ms_name not in found:
                    found.append(ms_name)
                break

    # Also check base ai_parser patterns (for coverage)
    for ms_name, patterns in MILESTONE_PATTERNS.items():
        if ms_name not in found:
            for pat in patterns:
                if re.search(pat, text_lower):
                    found.append(ms_name)
                    break

    return found


def _detect_issues(text):
    """Detect issues from email content.

    Returns:
        list of dict: [{"description": str, "suggested_action": str, "critical": bool}]
    """
    text_lower = text.lower()
    issues = []

    # Check email-specific issue patterns
    for pat, desc, action in EMAIL_ISSUE_PATTERNS:
        if re.search(pat, text_lower):
            is_critical = desc.startswith("CRITICAL:")
            issues.append({
                "description": desc,
                "suggested_action": action,
                "critical": is_critical,
            })

    # Also check base ai_parser issue patterns
    for pat, desc, action in ISSUE_PATTERNS:
        if re.search(pat, text_lower):
            already = any(i["description"] == desc for i in issues)
            if not already:
                issues.append({
                    "description": desc,
                    "suggested_action": action,
                    "critical": False,
                })

    return issues


def _detect_critical(text):
    """Check if this email contains a critical alert that should stall the property."""
    text_lower = text.lower()
    for pat in EMAIL_CRITICAL_PATTERNS:
        if re.search(pat, text_lower):
            return True
    return False


def _detect_at_risk(text):
    """Check if this email should flag the property as at-risk."""
    text_lower = text.lower()
    # Check base ai_parser triggers
    for pat in AT_RISK_TRIGGERS:
        if re.search(pat, text_lower):
            return True
    # Check email-specific at-risk patterns
    for pat in EMAIL_AT_RISK_PATTERNS:
        if re.search(pat, text_lower):
            return True
    return False


def _summarise_email(subject, body, milestones, dates, issues, is_critical):
    """Generate a human-readable summary of the email parsing results."""
    lines = []

    if milestones:
        for ms in milestones:
            lines.append(f"\u2705 {ms}")

    if dates:
        for d_str, d_obj in dates:
            lines.append(f"\U0001F4C5 Date found: {d_str}")

    if issues:
        for iss in issues:
            prefix = "\U0001F6A8" if iss.get("critical") else "\u26A0\uFE0F"
            lines.append(f"{prefix} {iss['description']}")

    if is_critical:
        lines.append("\U0001F6A8 CRITICAL ALERT — Immediate action required")

    if not lines:
        lines.append("\U0001F4E8 Email processed — no milestone updates detected")

    return lines


# ─────────────────────────────────────────────────────────────
#  MAIN PARSE FUNCTION
# ─────────────────────────────────────────────────────────────

def parse_email(subject, body, sender):
    """Analyze an email and return structured parsing results.

    Args:
        subject:  Email subject line
        body:     Email body text
        sender:   Sender email address or name string

    Returns dict:
        matched_property:    property dict or None
        match_confidence:    0-100
        match_reason:        str explaining the match
        milestones_to_update: list of milestone name strings
        dates_found:         list of (date_str, date_obj) tuples
        date_updates:        dict of {db_column: date_str}
        issues:              list of issue dicts
        is_critical:         bool — chain break / withdrawal etc.
        set_at_risk:         bool — should property go at-risk?
        set_stalled:         bool — should property go stalled?
        survey_booked:       bool
        suggested_action:    str or None
        summary:             list of human-readable summary lines
        email_note:          str — formatted note text for the property
    """
    combined = f"{subject}\n{body}"
    text_lower = combined.lower()

    # Load all properties for matching
    from app import load_properties
    properties = load_properties()

    # ── Property matching ──────────────────────────────────
    matched, confidence, match_reason = match_property(
        subject, body, sender, properties
    )

    # ── Milestone detection ────────────────────────────────
    milestones = _detect_milestones(combined)

    # ── Date extraction (reuse ai_parser) ──────────────────
    dates = extract_dates(combined)
    date_updates = {}
    if dates:
        for ctx_pat, db_col in DATE_CONTEXT:
            if re.search(ctx_pat, text_lower):
                date_updates[db_col] = dates[0][0]
                break

    # ── Survey booked detection ────────────────────────────
    survey_booked = False
    for pat in SURVEY_BOOKED_PATTERNS:
        if re.search(pat, text_lower):
            survey_booked = True
            break

    # ── Issue / risk detection ─────────────────────────────
    issues = _detect_issues(combined)
    is_critical = _detect_critical(combined)
    at_risk = _detect_at_risk(combined)

    # Critical emails → stalled
    set_stalled = is_critical
    set_at_risk = at_risk and not is_critical

    # ── Suggested action ───────────────────────────────────
    suggested_action = None
    if issues:
        # Use the first (most critical) issue's action
        suggested_action = issues[0]["suggested_action"]

    # ── Summary ────────────────────────────────────────────
    summary = _summarise_email(subject, body, milestones, dates, issues, is_critical)

    # ── Build email note text ──────────────────────────────
    note_parts = [f"[EMAIL] From: {sender}"]
    note_parts.append(f"Subject: {subject}")
    if milestones:
        note_parts.append(f"Milestones: {', '.join(milestones)}")
    if issues:
        for iss in issues:
            note_parts.append(f"Issue: {iss['description']}")
    note_parts.append(f"---")
    # Include first 200 chars of body as context
    body_preview = body.strip()[:200]
    if len(body.strip()) > 200:
        body_preview += "..."
    note_parts.append(body_preview)

    return {
        "matched_property": matched,
        "match_confidence": confidence,
        "match_reason": match_reason,
        "milestones_to_update": milestones,
        "dates_found": [(d[0], d[1]) for d in dates],
        "date_updates": date_updates,
        "issues": issues,
        "is_critical": is_critical,
        "set_at_risk": set_at_risk,
        "set_stalled": set_stalled,
        "survey_booked": survey_booked,
        "suggested_action": suggested_action,
        "summary": summary,
        "email_note": "\n".join(note_parts),
    }


# ─────────────────────────────────────────────────────────────
#  PROCESS EMAIL (parse + apply to DB + outbound sync)
# ─────────────────────────────────────────────────────────────

def process_email(subject, body, sender):
    """Parse an email AND apply the results to the database.

    This is the full pipeline: parse → match property → create note →
    update milestones → trigger outbound sync → flag issues.

    Args:
        subject:  Email subject line
        body:     Email body text
        sender:   Sender email address or name string

    Returns dict:
        All keys from parse_email() plus:
        applied:           bool — whether changes were applied
        note_id:           int or None — ID of the created note
        milestones_updated: int — count of milestones marked complete
        dates_updated:      int — count of date fields set
        status_changed:     bool
    """
    result = parse_email(subject, body, sender)
    result["applied"] = False
    result["note_id"] = None
    result["milestones_updated"] = 0
    result["dates_updated"] = 0
    result["status_changed"] = False

    prop = result["matched_property"]
    if not prop:
        return result

    if result["match_confidence"] < 40:
        return result

    db = get_db()

    try:
        property_id = prop["db_id"]

        # ── 1. Create a note with source='email' ──────────────
        cur = db.execute(
            """INSERT INTO notes (property_id, note_text, author, source, is_urgent)
               VALUES (?, ?, ?, 'email', ?)""",
            (property_id, result["email_note"], f"Email: {sender}",
             1 if result["is_critical"] else 0),
        )
        result["note_id"] = cur.lastrowid
        db.commit()

        # ── 2. Build an ai_parser-compatible result for apply_ai_results
        ai_result = {
            "milestones_completed": result["milestones_to_update"],
            "dates_found": [d[0] for d in result["dates_found"]],
            "date_updates": result["date_updates"],
            "issues": result["issues"],
            "suggested_action": result["suggested_action"],
            "set_at_risk": result["set_at_risk"],
            "survey_booked": result["survey_booked"],
            "summary": result["summary"],
        }

        # ── 3. Apply milestone/date/status changes ────────────
        changes = apply_ai_results(db, property_id, ai_result)
        result["milestones_updated"] = changes["milestones_updated"]
        result["dates_updated"] = changes["dates_updated"]
        result["status_changed"] = changes["status_changed"]

        # ── 4. Handle critical → stalled ──────────────────────
        if result["set_stalled"]:
            current = db.execute(
                "SELECT status FROM properties WHERE id = ?", (property_id,)
            ).fetchone()
            if current and current["status"] != "stalled":
                db.execute(
                    "UPDATE properties SET status = 'stalled' WHERE id = ?",
                    (property_id,),
                )
                result["status_changed"] = True

        # ── 5. Update alert field if critical ─────────────────
        if result["is_critical"] and result["issues"]:
            alert_text = result["issues"][0]["description"]
            db.execute(
                "UPDATE properties SET alert = ? WHERE id = ?",
                (alert_text, property_id),
            )

        db.commit()
        result["applied"] = True

        # ── 6. Outbound sync (NUVU → CRM) ─────────────────────
        try:
            push_note_to_crm(property_id, result["email_note"], f"Email: {sender}")

            if result["milestones_updated"] > 0:
                today = datetime.now().strftime("%Y-%m-%d")
                for ms_name in result["milestones_to_update"]:
                    push_milestone_to_crm(property_id, ms_name, True, today)

            if result["status_changed"]:
                new_status = "stalled" if result["set_stalled"] else "at-risk"
                push_status_to_crm(property_id, new_status,
                                   f"Email from {sender}: {result['issues'][0]['description']}" if result["issues"] else "Status changed by email parser")
        except Exception as outbound_err:
            print(f"  [email_parser] Non-critical outbound error: {outbound_err}")

    except Exception as e:
        print(f"  [email_parser] Error processing email: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

    return result


# ─────────────────────────────────────────────────────────────
#  SAMPLE TEST EMAILS
# ─────────────────────────────────────────────────────────────

SAMPLE_EMAILS = [
    {
        "id": "sample-1",
        "label": "Good News — Searches Received",
        "tag": "milestone",
        "tag_color": "#16a34a",
        "subject": "RE: Rose Cottage, Appleby-in-Westmorland — Search Results",
        "sender": "conveyancing@oglethorpe-sturton.co.uk",
        "body": """Dear NUVU,

Further to our recent correspondence regarding Rose Cottage, Main Street, Appleby-in-Westmorland, we are pleased to confirm that all searches have been received and are satisfactory.

The local authority search, environmental search, and drainage search have all been returned with no adverse entries. We are now in a position to proceed with raising pre-contract enquiries.

We will prepare our enquiries and send them to the seller's solicitor shortly.

Kind regards,
Sarah Mitchell
Oglethorpe Sturton & Gillibrand
Lancaster""",
    },
    {
        "id": "sample-2",
        "label": "Bad News — Down-Valuation",
        "tag": "issue",
        "tag_color": "#f97316",
        "subject": "Fell View, Kirkby Stephen — Mortgage Valuation Issue",
        "sender": "mortgages@example-broker.co.uk",
        "body": """Hi,

I'm writing regarding the mortgage application for Fell View, Station Road, Kirkby Stephen.

Unfortunately the lender's valuation has come in below the agreed purchase price. The property was valued at £440,000 against the agreed price of £475,000, representing a shortfall of £35,000.

We need to discuss options with the buyer Dr S. Kapoor:
1. Buyer funds the shortfall personally
2. Renegotiate the purchase price with the seller
3. Approach an alternative lender

Please can we arrange a call to discuss next steps at your earliest convenience.

Best regards,
James Wilson
Mortgage Broker""",
    },
    {
        "id": "sample-3",
        "label": "Routine — Draft Contracts Issued",
        "tag": "routine",
        "tag_color": "#3b82f6",
        "subject": "Bracken House, Kendal — Draft Contract",
        "sender": "property@harrison-drury.co.uk",
        "body": """Dear Sirs,

Re: Bracken House, Windermere Road, Kendal

We act on behalf of the sellers Mr & Mrs Dalton in connection with the above property.

Please find attached the draft contract together with the following documents:
- Property Information Form
- Fittings and Contents Form
- Title Deeds
- Energy Performance Certificate

We look forward to receiving your enquiries in due course.

Yours faithfully,
Harrison Drury Solicitors
Kendal""",
    },
    {
        "id": "sample-4",
        "label": "Urgent — Exchange Ready",
        "tag": "urgent",
        "tag_color": "#8b5cf6",
        "subject": "RE: Ivy Bank, Keswick — Exchange",
        "sender": "conveyancing@oglethorpe-sturton.co.uk",
        "body": """Dear NUVU,

Re: Ivy Bank, Church Lane, Keswick

I am pleased to confirm that we are now in a position to exchange contracts on the above property.

All enquiries have been answered satisfactorily, the mortgage offer has been issued, and the deposit funds are in place. Both parties have signed contracts.

Exchange has been agreed for 28th February 2026 with completion confirmed for 14th March 2026.

Please confirm the agreed exchange date at your earliest convenience so we can proceed.

Kind regards,
Laura Collins
Oglethorpe Sturton & Gillibrand""",
    },
    {
        "id": "sample-5",
        "label": "Critical — Chain Break",
        "tag": "critical",
        "tag_color": "#e11d48",
        "subject": "URGENT: Lakeside Barn, Pooley Bridge — Chain Break",
        "sender": "conveyancing@bendles-carlisle.co.uk",
        "body": """URGENT

Re: Lakeside Barn, Howtown Road, Pooley Bridge

We regret to inform you that the buyer's sale at their Penrith property has fallen through. The buyer, Mr & Mrs Greenwood, is unable to proceed with the purchase of Lakeside Barn without the proceeds from their onward sale.

This represents a chain break and we need to urgently discuss next steps. The buyer has withdrawn from the transaction pending sale of their existing property.

Our client (the seller) is understandably very disappointed. Please contact us as a matter of urgency to discuss options.

Yours faithfully,
Richard Holmes
Bendles Solicitors
Carlisle""",
    },
]
