"""Resend notifications for portal form lifecycle (Window 3)."""

from __future__ import annotations

import os

import resend

from utils.portal_config import portal_team_notifications_enabled

TEAM_NOTIFY_TO = "salesprog@brittonestates.co.uk"
FROM_LINE = "David Britton Estates, powered by NUVU <salesprog@brittonestates.co.uk>"


def _base_url() -> str:
    return (os.environ.get("NUVU_BASE_URL") or "http://127.0.0.1:5000").rstrip("/")


def send_ta6_ta10_seller_portal_link_email(
    *,
    to_email: str,
    seller_name: str,
    property_address: str,
    negotiator_name: str,
    magic_link_url: str,
) -> None:
    subject = f"Your Property Information Forms — {property_address}"
    who = (negotiator_name or "").strip() or "Your negotiator"
    html = (
        f"<p>Dear {(seller_name or 'there').strip() or 'there'},</p>"
        "<p>Congratulations on your sale of "
        f"<strong>{property_address}</strong>. To keep things moving smoothly, we need you to complete "
        "two important forms — your Property Information Form and your Fittings and Contents Form.</p>"
        "<p>We’ve built a simple online portal that walks you through every question step by step. "
        "It usually takes around 20–30 minutes, and you can save your progress and come back at any time.</p>"
        f'<p><a href="{magic_link_url}" style="display:inline-block;padding:12px 28px;'
        "background:#1B3A5C;color:#ffffff;border-radius:8px;text-decoration:none;"
        'font-weight:700;font-size:1rem;">Click here to get started</a></p>'
        "<p>This link is unique to you — please don’t share it. If you have any questions, just reply to this email.</p>"
        f"<p>Best wishes,<br>{who}<br>David Britton Estates</p>"
    )
    resend.Emails.send(
        {
            "from": FROM_LINE,
            "to": [to_email.strip()],
            "subject": subject,
            "html": html,
        }
    )


def notify_negotiator_ta6_ta10_submitted(
    *,
    to_email: str,
    seller_name: str,
    property_address: str,
    staff_review_url: str,
) -> None:
    subject = f"TA6/TA10 Submitted — {property_address}"
    body = (
        f"{(seller_name or 'The seller').strip()} has submitted their Property Information Form and "
        f"Fittings and Contents Form for {property_address}. "
        f"Review the answers in the NUVU portal: <a href=\"{staff_review_url}\">{staff_review_url}</a>"
    )
    html = f"<p>{body}</p>"
    resend.Emails.send(
        {
            "from": FROM_LINE,
            "to": [to_email.strip()],
            "subject": subject,
            "html": html,
        }
    )


def notify_team_form_completed(
    *,
    form_label: str,
    property_address: str,
    seller_name: str,
    answered: int,
    total: int,
    skipped: int,
) -> None:
    """Email progression when a seller completes every question. Respects PORTAL_ENABLED."""
    subject = f"Form Completed — {form_label} — {property_address}"
    body = (
        f"{seller_name} has completed the {form_label} for {property_address}. "
        f"{answered} of {total} questions answered, {skipped} skipped. "
        "Please review and dispatch."
    )
    dash = _base_url() + "/"
    html = f"<p>{body}</p><p><a href=\"{dash}\">Open NUVU dashboard</a></p>"

    if not portal_team_notifications_enabled():
        print(f"[portal notify suppressed PORTAL_ENABLED=false] {subject}: {body}")
        return

    try:
        resend.Emails.send(
            {
                "from": FROM_LINE,
                "to": [TEAM_NOTIFY_TO],
                "subject": subject,
                "html": html,
            }
        )
        print(f"[portal notify sent] {subject}")
    except Exception as exc:
        print(f"[portal notify failed] {subject}: {exc}")


def _dispatch_recipient_allowed(email: str) -> tuple[bool, str]:
    from utils.portal_config import portal_dispatch_test_mode

    e = (email or "").strip().lower()
    if not e or "@" not in e:
        return False, "Invalid email"
    if portal_dispatch_test_mode():
        allow = (os.environ.get("PORTAL_DISPATCH_TEST_EMAIL") or "").strip().lower()
        if allow and e == allow:
            return True, ""
        if e.endswith("@brittonestates.co.uk"):
            return True, ""
        return (
            False,
            "Test mode: use @brittonestates.co.uk or set PORTAL_DISPATCH_TEST_EMAIL to this recipient.",
        )
    return True, ""


def send_solicitor_dispatch_email(
    *,
    to_email: str,
    form_label: str,
    property_address: str,
    seller_name: str,
    completed_on: str,
    pdf_path: str,
    pdf_bytes: bytes,
    filename: str,
) -> None:
    """Attach filled PDF and send covering note to the solicitor."""
    import base64

    ok, err = _dispatch_recipient_allowed(to_email)
    if not ok:
        raise ValueError(err)

    intro = (
        f"Please find attached the completed {form_label} for {property_address}, "
        f"completed by {seller_name} on {completed_on}."
    )
    html = (
        "<p>Dear Colleague,</p>"
        f"<p>{intro}</p>"
        "<p>If you have any questions, please contact our sales progression team.</p>"
        "<p>Kind regards,<br>David Britton Estates — Sales Progression</p>"
    )
    b64 = base64.b64encode(pdf_bytes).decode("ascii")
    resend.Emails.send(
        {
            "from": FROM_LINE,
            "to": [to_email.strip()],
            "subject": f"{form_label} — {property_address} — Completed by {seller_name}",
            "html": html,
            "attachments": [{"filename": filename, "content": b64}],
        }
    )
