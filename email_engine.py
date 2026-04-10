"""
NUVU Email Engine
==================
Generates professional emails based on property status and milestones.
Suggests relevant emails for each property based on progression state.

Beta mode: agents review and copy-paste into their email client.
Full automation comes later.

Usage:
    from email_engine import suggest_emails, generate_email, TEMPLATES
    suggestions = suggest_emails(prop, tone="professional")
    email = generate_email("chaser_solicitor", prop, tone="firm")
"""

from datetime import datetime, date, timedelta


# ─────────────────────────────────────────────────────────────
#  TONE CONFIGURATION
# ─────────────────────────────────────────────────────────────
# Each tone adjusts greeting, sign-off, urgency language, and politeness.

TONE_CONFIG = {
    "friendly": {
        "greeting": "Hi {name}",
        "greeting_no_name": "Hi there",
        "sign_off": "Thanks so much,\nNUVU Property Team",
        "urgency_prefix": "Just a gentle nudge — ",
        "please": "Would you mind",
        "closing_line": "Thanks for your help with this!",
    },
    "professional": {
        "greeting": "Dear {name}",
        "greeting_no_name": "Dear Sir/Madam",
        "sign_off": "Kind regards,\nNUVU Property Team",
        "urgency_prefix": "We would appreciate an update — ",
        "please": "Could you please",
        "closing_line": "Thank you for your attention to this matter.",
    },
    "firm": {
        "greeting": "Dear {name}",
        "greeting_no_name": "Dear Sir/Madam",
        "sign_off": "Regards,\nNUVU Property Team",
        "urgency_prefix": "This matter is now urgent — ",
        "please": "Please",
        "closing_line": "We expect a response at the earliest opportunity.",
    },
}


# ─────────────────────────────────────────────────────────────
#  EMAIL TEMPLATES
# ─────────────────────────────────────────────────────────────
# Each template uses {placeholders} filled at generation time.
# Tone-dependent placeholders: {greeting}, {sign_off}, {please},
# {urgency_prefix}, {closing_line}

TEMPLATES = {
    "chaser_solicitor": {
        "display_name": "Chaser to Solicitor",
        "recipient_type": "solicitor",
        "subject": "Update requested — {address}",
        "body": (
            "{greeting},\n\n"
            "We are writing regarding the sale/purchase of {address}.\n\n"
            "We are still awaiting {pending_milestone}. It has been "
            "{days_waiting} days since our last update on this matter.\n\n"
            "{please} provide us with a progress update at your earliest "
            "convenience?\n\n"
            "{closing_line}\n\n"
            "{sign_off}"
        ),
        "placeholders": [
            "address", "pending_milestone", "days_waiting",
            "greeting", "sign_off", "please", "closing_line",
        ],
    },
    "update_buyer": {
        "display_name": "Update to Buyer",
        "recipient_type": "buyer",
        "subject": "Progress update — {address}",
        "body": (
            "{greeting},\n\n"
            "Good news — your purchase of {address} is progressing well.\n\n"
            "{completed_milestone} has now been completed. The next step "
            "in the process is {next_milestone}.\n\n"
            "We will keep you updated as things move forward. Please do "
            "not hesitate to get in touch if you have any questions.\n\n"
            "{sign_off}"
        ),
        "placeholders": [
            "address", "buyer_name", "completed_milestone",
            "next_milestone", "greeting", "sign_off",
        ],
    },
    "update_seller": {
        "display_name": "Update to Seller",
        "recipient_type": "seller",
        "subject": "Sale progress — {address}",
        "body": (
            "{greeting},\n\n"
            "Your sale of {address} is progressing well.\n\n"
            "We are currently awaiting {pending_milestone}. We are "
            "actively chasing this on your behalf and will update you "
            "as soon as we have news.\n\n"
            "{closing_line}\n\n"
            "{sign_off}"
        ),
        "placeholders": [
            "address", "pending_milestone", "greeting",
            "sign_off", "closing_line",
        ],
    },
    "nudge_broker": {
        "display_name": "Nudge to Mortgage Broker",
        "recipient_type": "broker",
        "subject": "Mortgage status — {buyer_name}, {address}",
        "body": (
            "{greeting},\n\n"
            "{please} confirm the current status of the mortgage "
            "application for {buyer_name} regarding {address}?\n\n"
            "We are keen to keep this transaction moving and an update "
            "would be much appreciated.\n\n"
            "{closing_line}\n\n"
            "{sign_off}"
        ),
        "placeholders": [
            "address", "buyer_name", "greeting",
            "sign_off", "please", "closing_line",
        ],
    },
    "escalation": {
        "display_name": "Escalation",
        "recipient_type": "solicitor",
        "subject": "URGENT: {address} — {pending_milestone} overdue",
        "body": (
            "{greeting},\n\n"
            "{urgency_prefix}we have been waiting {days_waiting} days "
            "for {pending_milestone} regarding {address}.\n\n"
            "This matter is now at risk of causing delays to the wider "
            "transaction. {please} treat this as a matter of urgency "
            "and provide an update today.\n\n"
            "{closing_line}\n\n"
            "{sign_off}"
        ),
        "placeholders": [
            "address", "pending_milestone", "days_waiting",
            "greeting", "sign_off", "please", "urgency_prefix",
            "closing_line",
        ],
    },
}


# ─────────────────────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────

def _get_first_pending_milestone(prop):
    """Return the label of the first milestone that is pending (done=False)."""
    for m in prop.get("milestones", []):
        if m["done"] is False:
            return m["label"]
    return None


def _get_last_completed_milestone(prop):
    """Return the label of the most recently completed milestone.

    Prefers milestones with a completed_date; falls back to the last
    milestone in order where done=True.
    """
    # Try to find one with a completed_date (most recent)
    dated = []
    for m in prop.get("milestones", []):
        if m["done"] is True and m.get("completed_date"):
            dated.append(m)
    if dated:
        dated.sort(key=lambda x: x["completed_date"], reverse=True)
        return dated[0]["label"]

    # Fallback: last completed by list position
    last = None
    for m in prop.get("milestones", []):
        if m["done"] is True:
            last = m["label"]
    return last


def _get_next_milestone_after(prop, label):
    """Return the label of the next pending milestone after the given one."""
    found = False
    for m in prop.get("milestones", []):
        if found and m["done"] is False:
            return m["label"]
        if m["label"] == label:
            found = True
    # If nothing after, return the first pending overall
    return _get_first_pending_milestone(prop)


def _milestone_is_pending(prop, name):
    """Check if a specific named milestone is pending."""
    for m in prop.get("milestones", []):
        if m["label"] == name and m["done"] is False:
            return True
    return False


def _get_property_stage(prop):
    """Return the current property stage (1, 2, or 3) based on milestones.

    Returns the stage of the first pending milestone, or 3 if all done.
    """
    for m in prop.get("milestones", []):
        if m["done"] is False:
            return m.get("stage", 1)
    return 3


def _get_recipient_name(prop, recipient_type):
    """Get the recipient name from the property dict based on type."""
    if recipient_type == "solicitor":
        # Prefer buyer's solicitor (they're usually the one being chased)
        return prop.get("buyer_solicitor") or prop.get("seller_solicitor") or "Solicitor"
    elif recipient_type == "buyer":
        return prop.get("buyer") or "Buyer"
    elif recipient_type == "seller":
        return "Seller"  # Seller names often not in data
    elif recipient_type == "broker":
        return "Mortgage Broker"
    return "Sir/Madam"


# ─────────────────────────────────────────────────────────────
#  EMAIL GENERATION
# ─────────────────────────────────────────────────────────────

def generate_email(email_type, prop, tone="professional", overrides=None):
    """Generate a full email from a template type and property data.

    Args:
        email_type: One of the TEMPLATES keys (e.g. "chaser_solicitor")
        prop: Property dict from load_properties()
        tone: One of "friendly", "professional", "firm"
        overrides: Optional dict of placeholder overrides

    Returns:
        dict with keys: subject, body, recipient_type, recipient_name,
                        email_type, tone
    """
    template = TEMPLATES.get(email_type)
    if not template:
        return None

    tone_cfg = TONE_CONFIG.get(tone, TONE_CONFIG["professional"])
    recipient_type = template["recipient_type"]
    recipient_name = _get_recipient_name(prop, recipient_type)

    # Build greeting with name
    if recipient_name and recipient_name not in ("Solicitor", "Buyer", "Seller", "Mortgage Broker", "Sir/Madam"):
        greeting = tone_cfg["greeting"].format(name=recipient_name)
    else:
        greeting = tone_cfg["greeting_no_name"]

    # Milestone data
    pending = _get_first_pending_milestone(prop)
    completed = _get_last_completed_milestone(prop)
    next_ms = _get_next_milestone_after(prop, completed) if completed else pending

    # Build placeholder values
    values = {
        "address": prop.get("address", "the property"),
        "buyer_name": prop.get("buyer") or "the buyer",
        "pending_milestone": pending or "the next step",
        "completed_milestone": completed or "a key milestone",
        "next_milestone": next_ms or "the next step",
        "days_waiting": str(prop.get("days_since_update", 0)),
        "greeting": greeting,
        "sign_off": tone_cfg["sign_off"],
        "please": tone_cfg["please"],
        "urgency_prefix": tone_cfg["urgency_prefix"],
        "closing_line": tone_cfg["closing_line"],
    }

    # Apply any overrides
    if overrides:
        values.update(overrides)

    # Fill templates
    try:
        subject = template["subject"].format(**values)
        body = template["body"].format(**values)
    except KeyError:
        # Gracefully handle missing placeholders
        subject = template["subject"]
        body = template["body"]
        for k, v in values.items():
            subject = subject.replace("{" + k + "}", v)
            body = body.replace("{" + k + "}", v)

    return {
        "subject": subject,
        "body": body,
        "recipient_type": recipient_type,
        "recipient_name": recipient_name,
        "email_type": email_type,
        "tone": tone,
    }


# ─────────────────────────────────────────────────────────────
#  EMAIL SUGGESTIONS
# ─────────────────────────────────────────────────────────────

def suggest_emails(prop, tone="professional"):
    """Analyse property state and return a list of suggested emails.

    Each suggestion is a dict with:
        email_type: str — template key
        reason: str — why this email is suggested
        priority: int — 1=high, 2=medium, 3=low
        recipient_type: str
        recipient_name: str
        preview_subject: str
        preview_body: str
        tone: str

    Returns up to 5 suggestions, sorted by priority (highest first).
    """
    suggestions = []
    status = prop.get("status", "on-track")
    days_since = prop.get("days_since_update", 0)
    milestones = prop.get("milestones", [])
    has_pending = any(m["done"] is False for m in milestones)
    has_completed = any(m["done"] is True for m in milestones)
    pending_milestone = _get_first_pending_milestone(prop)

    # ── 1. ESCALATION (highest priority) ──────────────────────
    if status in ("at-risk", "stalled") and has_pending:
        email = generate_email("escalation", prop, tone=tone)
        if email:
            suggestions.append({
                "email_type": "escalation",
                "reason": f"Property is {status} — escalation recommended",
                "priority": 1,
                "recipient_type": email["recipient_type"],
                "recipient_name": email["recipient_name"],
                "preview_subject": email["subject"],
                "preview_body": email["body"],
                "tone": tone,
            })

    # ── 2. CHASER TO SOLICITOR ────────────────────────────────
    if days_since > 3 and has_pending:
        email = generate_email("chaser_solicitor", prop, tone=tone)
        if email:
            suggestions.append({
                "email_type": "chaser_solicitor",
                "reason": f"No update for {days_since} days — chase solicitor for {pending_milestone}",
                "priority": 2,
                "recipient_type": email["recipient_type"],
                "recipient_name": email["recipient_name"],
                "preview_subject": email["subject"],
                "preview_body": email["body"],
                "tone": tone,
            })

    # ── 3. MORTGAGE NUDGE ─────────────────────────────────────
    if _milestone_is_pending(prop, "Mortgage Offer"):
        stage = _get_property_stage(prop)
        if stage >= 2:
            email = generate_email("nudge_broker", prop, tone=tone)
            if email:
                suggestions.append({
                    "email_type": "nudge_broker",
                    "reason": "Mortgage Offer milestone is pending — nudge the broker",
                    "priority": 2,
                    "recipient_type": email["recipient_type"],
                    "recipient_name": email["recipient_name"],
                    "preview_subject": email["subject"],
                    "preview_body": email["body"],
                    "tone": tone,
                })

    # ── 4. BUYER UPDATE ───────────────────────────────────────
    if status == "on-track" and has_completed and has_pending:
        email = generate_email("update_buyer", prop, tone=tone)
        if email:
            suggestions.append({
                "email_type": "update_buyer",
                "reason": "Property is progressing — send buyer an update",
                "priority": 3,
                "recipient_type": email["recipient_type"],
                "recipient_name": email["recipient_name"],
                "preview_subject": email["subject"],
                "preview_body": email["body"],
                "tone": tone,
            })

    # ── 5. SELLER UPDATE ──────────────────────────────────────
    if days_since > 5 and has_pending:
        email = generate_email("update_seller", prop, tone=tone)
        if email:
            suggestions.append({
                "email_type": "update_seller",
                "reason": f"No update to seller for {days_since} days",
                "priority": 3,
                "recipient_type": email["recipient_type"],
                "recipient_name": email["recipient_name"],
                "preview_subject": email["subject"],
                "preview_body": email["body"],
                "tone": tone,
            })

    # Sort by priority, cap at 5
    suggestions.sort(key=lambda s: s["priority"])
    return suggestions[:5]


# ─────────────────────────────────────────────────────────────
#  OUTBOUND SEND (Resend)
# ─────────────────────────────────────────────────────────────

DEFAULT_SEND_FROM = (
    "David Britton Estates, powered by NUVU <salesprog@brittonestates.co.uk>"
)


def send_html_email(to, subject, html_body, from_address=None):
    """Send a single HTML email via Resend.

    ``to`` may be one address (str) or a list of strings.
    Requires ``RESEND_API_KEY`` and ``resend.api_key`` (see ``shared``).
    """
    import os

    import resend

    if not getattr(resend, "api_key", None):
        resend.api_key = os.environ.get("RESEND_API_KEY", "")
    addr = from_address or DEFAULT_SEND_FROM
    recipients = to if isinstance(to, list) else [to]
    return resend.Emails.send(
        {
            "from": addr,
            "to": recipients,
            "subject": subject,
            "html": html_body,
        }
    )
