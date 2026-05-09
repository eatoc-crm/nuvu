"""Chase message copy — aligned with docs/progression-engine-spec.md (Stages 2a, 2b, 3)."""

from __future__ import annotations

import html
from typing import Any

CHASE_SEND_FROM = (
    "David Britton Estates, powered by NUVU <salesprog@brittonestates.co.uk>"
)


def _esc(s: Any) -> str:
    return html.escape(str(s or "").strip(), quote=True)


def _p_wrap(inner: str) -> str:
    return f"<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">{inner}</p>"


def _sign_off(negotiator_name: str) -> str:
    nm = (negotiator_name or "").strip() or "The Sales Progression Team"
    return (
        "<p style=\"margin:24px 0 0 0;line-height:1.5;font-size:15px;color:#1a1a1a;\">"
        f"Kind regards,<br>{_esc(nm)}<br>David Britton Estates</p>"
    )


def render_buyer_protocol_chase(day: int, ctx: dict[str, Any]) -> tuple[str, str]:
    """Stage 2a — buyer protocol forms (spec §2a)."""
    addr = _esc(ctx.get("property_address"))
    buyer = _esc(ctx.get("buyer_name") or "there")
    neg = ctx.get("negotiator_name") or ""

    short_addr = (ctx.get("property_address") or "your purchase").strip()
    if day == 1:
        subject = f"Your purchase — protocol forms ({short_addr})"
        body_txt = (
            "Congratulations again — have you received your solicitor’s instruction letter and protocol forms?"
        )
    elif day == 2:
        subject = f"Quick check-in — {short_addr}"
        body_txt = "Just checking in — have those forms arrived yet?"
    elif day == 3:
        subject = f"We’re here to help — {short_addr}"
        body_txt = (
            "We know forms can feel overwhelming — let us know if you need any help."
        )
    else:
        subject = f"Protocol forms — {short_addr}"
        body_txt = "Just checking in — have those forms arrived yet?"

    inner = (
        f"<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear {buyer},</p>"
        + _p_wrap(body_txt)
        + _p_wrap(f"This relates to <strong>{addr}</strong>.")
        + _sign_off(neg)
    )
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject.strip(), html_body


def render_seller_forms_chase(day: int, ctx: dict[str, Any]) -> tuple[str, str]:
    """Stage 2b — seller Property Information / Fittings & Contents forms (spec §2b). Layman wording only."""
    addr = _esc(ctx.get("property_address"))
    seller = _esc(ctx.get("seller_name") or "there")
    neg = ctx.get("negotiator_name") or ""
    portal = (ctx.get("portal_link") or "").strip()
    portal_para = ""
    if portal and day in (1, 3):
        safe = html.escape(portal, quote=True)
        portal_para = _p_wrap(
            f"You can complete the forms in our secure portal here: "
            f"<a href=\"{safe}\" style=\"color:#1B3A5C;\">open your portal link</a>."
        )

    short_addr = (ctx.get("property_address") or "your sale").strip()
    if day == 1:
        subject = "Your sale — Property Information and Fittings & Contents forms"
        core = (
            "Have you sent back your Property Information Form and Fittings & Contents Form "
            "to your solicitor? If not, log into the portal and we’ll help you complete them."
        )
    elif day == 2:
        subject = f"Important — forms needed for {short_addr}"
        core = "These forms are the single biggest thing holding up your sale right now."
    elif day == 3:
        subject = f"Guided help with your property forms — {short_addr}"
        core = (
            "Most sellers find these forms confusing — our portal walks you through every question step by step."
        )
    else:
        subject = f"Property forms — {short_addr}"
        core = "These forms are the single biggest thing holding up your sale right now."

    inner = (
        f"<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear {seller},</p>"
        + _p_wrap(core)
        + portal_para
        + _p_wrap(f"This relates to <strong>{addr}</strong>.")
        + _sign_off(neg)
    )
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject.strip(), html_body


def render_survey_chase(day: int, buyer_type: str, ctx: dict[str, Any]) -> tuple[str, str]:
    """Stage 3 — survey instruction (spec §3). buyer_type: 'cash' | 'mortgage'."""
    addr = _esc(ctx.get("property_address"))
    buyer = _esc(ctx.get("buyer_name") or "there")
    neg = ctx.get("negotiator_name") or ""
    panel_lines = ctx.get("surveyor_panel_html") or ""
    short_addr = (ctx.get("property_address") or "your purchase").strip()

    if day == 1:
        if buyer_type == "cash":
            body_txt = (
                "Have you booked your survey yet? Surveyors are in high demand so best to get this booked "
                "as soon as possible."
            )
        else:
            body_txt = (
                "Has your mortgage broker booked your survey yet? Surveyors are in high demand so essential "
                "to get this booked as soon as possible."
            )
        subject = f"Survey booking — {short_addr}"
    elif day == 2:
        subject = f"Survey progress — {short_addr}"
        body_txt = "Any progress on the survey booking?"
    elif day == 3:
        subject = f"Survey booking — recommendations — {short_addr}"
        body_txt = (
            "We wanted to follow up on your survey. If you have not yet appointed a surveyor, "
            "we recommend choosing a RICS-accredited firm with strong reviews."
        )
        if panel_lines:
            body_txt += " Here are a few firms we are happy to recommend:"
    else:
        subject = f"Survey — {short_addr}"
        body_txt = "Any progress on the survey booking?"

    inner = (
        f"<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear {buyer},</p>"
        + _p_wrap(body_txt)
    )
    if panel_lines and day == 3:
        inner += f"<div style=\"margin:0 0 14px 0;line-height:1.45;font-size:14px;color:#333;\">{panel_lines}</div>"
        inner += _p_wrap(
            "If none of these suit your location, searching for RICS-accredited surveyors locally is a good next step."
        )
    inner += _p_wrap(f"This relates to <strong>{addr}</strong>.") + _sign_off(neg)
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject.strip(), html_body


def render_post_survey_followup(ctx: dict[str, Any]) -> tuple[str, str]:
    """Spec §3 post-survey: 3 days after survey instructed — one-off."""
    addr = _esc(ctx.get("property_address"))
    buyer = _esc(ctx.get("buyer_name") or "there")
    neg = ctx.get("negotiator_name") or ""
    short_addr = (ctx.get("property_address") or "your purchase").strip()
    subject = f"Following up after your survey — {short_addr}"
    body_txt = "Has the survey taken place? Any issues?"
    inner = (
        f"<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear {buyer},</p>"
        + _p_wrap(body_txt)
        + _p_wrap(f"This relates to <strong>{addr}</strong>.")
        + _sign_off(neg)
    )
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject, html_body


def render_day4_flag(
    chase_stage: str,
    ctx: dict[str, Any],
) -> tuple[str, str, str]:
    """Internal negotiator flag (spec Day 4). Returns (subject, html_body, plain summary)."""
    addr = ctx.get("property_address") or ""
    if chase_stage == "buyer_protocol_forms":
        summary = (
            "No response after 3 days on buyer protocol forms. Negotiator to follow up personally."
        )
    elif chase_stage == "seller_ta6_ta10":
        summary = "No response on seller property forms. Negotiator to call seller directly."
    elif chase_stage == "survey_instruction":
        summary = "Survey still not booked after Day 3 chases. Negotiator to follow up."
    else:
        summary = f"Chase escalation for {chase_stage}."

    subject = f"[NUVU Chase] Action needed — {addr}"
    body = (
        "<div style=\"font-family:Segoe UI,system-ui,sans-serif;max-width:560px;\">"
        f"<p style=\"margin:0 0 12px 0;\"><strong>{_esc(summary)}</strong></p>"
        f"<p style=\"margin:0 0 8px 0;\">Property: <strong>{_esc(addr)}</strong></p>"
        "<p style=\"margin:0;color:#555;font-size:14px;\">This was generated by the NUVU chase engine (Day 4 flag).</p>"
        "</div>"
    )
    return subject, body, summary


def format_surveyor_panel_ul(rows: list[dict[str, Any]]) -> str:
    """Build HTML list from preferred_surveyors rows."""
    if not rows:
        return ""
    parts = ["<ul style=\"margin:8px 0 0 18px;padding:0;\">"]
    for r in rows[:5]:
        nm = _esc(r.get("surveyor_name") or "")
        fm = _esc(r.get("surveyor_firm") or "")
        phone = _esc(r.get("contact_phone") or "")
        em = _esc(r.get("contact_email") or "")
        gr = r.get("google_rating")
        bits = [x for x in (nm, fm) if x]
        line = " — ".join(bits) if bits else "Surveyor"
        if gr is not None:
            line += f" (Google rating: {html.escape(str(gr))})"
        if phone:
            line += f" — {phone}"
        if em:
            line += f" — <a href=\"mailto:{em}\">{em}</a>"
        parts.append(f"<li style=\"margin-bottom:6px;\">{line}</li>")
    parts.append("</ul>")
    return "".join(parts)
