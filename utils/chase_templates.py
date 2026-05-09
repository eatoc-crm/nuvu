"""Chase message copy — aligned with docs/progression-engine-spec.md + Phase C brief (Stages 7–8)."""

from __future__ import annotations

import html
from datetime import date
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


def _fmt_uk_date(d: date) -> str:
    return f"{d.day} {d.strftime('%B %Y')}"


def render_enquiries_raise_buyer_chase(day: int, ctx: dict[str, Any]) -> tuple[str, str]:
    """Stage 7a — raise enquiries (buyer's solicitor). day: 0, 3, 7."""
    addr = _esc(ctx.get("property_address"))
    neg = ctx.get("negotiator_name") or ""
    short = (ctx.get("property_address") or "the property").strip()
    if day == 0:
        subject = f"Enquiries on draft contract — {short}"
        body = (
            "Search results and survey are now complete for this matter. "
            "Are you in a position to raise enquiries on the draft contract?"
        )
    elif day == 3:
        subject = f"Following up — enquiries — {short}"
        body = "Following up — any update on when enquiries will be raised on the draft contract?"
    else:
        subject = f"Awaiting enquiries raised — {short}"
        body = (
            "We are still awaiting confirmation that enquiries have been raised on the draft contract. "
            "Could you advise on expected timescale?"
        )
    inner = (
        "<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear Sirs,</p>"
        + _p_wrap(body)
        + _p_wrap(f"This relates to <strong>{addr}</strong>.")
        + _sign_off(neg)
    )
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject.strip(), html_body


def render_enquiries_answer_seller_chase(day: int, ctx: dict[str, Any]) -> tuple[str, str]:
    """Stage 7b — answer enquiries (seller's solicitor). day: 0, 7, 14."""
    addr = _esc(ctx.get("property_address"))
    neg = ctx.get("negotiator_name") or ""
    short = (ctx.get("property_address") or "the property").strip()
    if day == 0:
        subject = f"Outstanding enquiries — {short}"
        body = (
            "Enquiries have been raised on the draft contract for this matter. "
            "Are you able to respond at this stage?"
        )
    elif day == 7:
        subject = f"Following up on enquiries — {short}"
        body = "Following up on the outstanding enquiries. Any update on responses?"
    else:
        subject = f"Awaiting responses to enquiries — {short}"
        body = (
            "We are still awaiting responses to enquiries. "
            "Could you advise on expected timescale?"
        )
    inner = (
        "<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear Sirs,</p>"
        + _p_wrap(body)
        + _p_wrap(f"This relates to <strong>{addr}</strong>.")
        + _sign_off(neg)
    )
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject.strip(), html_body


def render_report_on_title_chase(day: int, ctx: dict[str, Any]) -> tuple[str, str]:
    """Post-enquiries report on title (buyer's solicitor). day: 0, 5."""
    addr = _esc(ctx.get("property_address"))
    neg = ctx.get("negotiator_name") or ""
    short = (ctx.get("property_address") or "the property").strip()
    if day == 0:
        subject = f"Report on title — {short}"
        body = (
            "All enquiries on this matter have now been resolved. "
            "Are you in a position to send the report on title to your client?"
        )
    else:
        subject = f"Following up — report on title — {short}"
        body = "Following up — has the report on title been sent to the buyer?"
    inner = (
        "<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear Sirs,</p>"
        + _p_wrap(body)
        + _p_wrap(f"This relates to <strong>{addr}</strong>.")
        + _sign_off(neg)
    )
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject.strip(), html_body


def render_exchange_target_chase(
    variant: str,
    ctx: dict[str, Any],
) -> tuple[str, str]:
    """Stage 8 — both solicitors. variant: d0 | d14 | d21 | t7 | due."""
    addr = _esc(ctx.get("property_address"))
    neg = ctx.get("negotiator_name") or ""
    short = (ctx.get("property_address") or "the property").strip()
    td: date = ctx["exchange_target_date"]
    ds = _fmt_uk_date(td)
    n_days = int(ctx.get("days_until_exchange") or 0)

    if variant == "d0":
        subject = f"Target exchange date — {short}"
        body = (
            f"We are writing to confirm that enquiries have now been raised on <strong>{addr}</strong>. "
            f"Our <strong>target exchange date</strong> for this transaction is <strong>{ds}</strong>. "
            "We would be grateful if both parties could work towards this date. "
            "Please let us know if there are any circumstances that may prevent exchange by this date."
        )
    elif variant == "d14":
        subject = f"Reminder — target exchange — {short}"
        body = (
            f"A reminder that the target exchange date for <strong>{addr}</strong> is <strong>{ds}</strong>. "
            f"We are <strong>{n_days}</strong> calendar days from that date. "
            "Please confirm there are no outstanding matters that would prevent exchange."
        )
    elif variant == "d21":
        subject = f"Target exchange — update — {short}"
        body = (
            f"Exchange for <strong>{addr}</strong> is targeted for <strong>{ds}</strong>, "
            f"now <strong>{n_days}</strong> calendar days away. "
            "If there are any issues that may delay exchange, please advise immediately so we can address them."
        )
    elif variant == "t7":
        subject = f"One week to target exchange — {short}"
        body = (
            f"Exchange for <strong>{addr}</strong> is scheduled for <strong>{ds}</strong>, "
            "which is one week from today. "
            "Please confirm both parties are ready to proceed."
        )
    else:
        subject = f"Target exchange date — today — {short}"
        body = (
            f"Today is the target exchange date for <strong>{addr}</strong>. "
            "Are we exchanging today?"
        )

    inner = (
        "<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear Sirs,</p>"
        + _p_wrap(body)
        + _sign_off(neg)
    )
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject.strip(), html_body


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
    elif chase_stage == "enquiries_raise_buyer":
        summary = (
            "Enquiries not raised after 10 days (searches and survey complete). Negotiator to escalate."
        )
    elif chase_stage == "enquiries_answer_seller":
        summary = "Enquiry responses overdue after 17 days. Negotiator to escalate."
    elif chase_stage == "report_on_title":
        summary = "Report on title not confirmed. Negotiator to follow up."
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


# --- Track 6 — chain solicitor (Session 19 brief) ---


def render_chain_solicitor_lead_in(ctx: dict[str, Any]) -> tuple[str, str]:
    """Phase 1 — initial outreach to chain-side solicitor."""
    addr = _esc(ctx.get("property_address"))
    short_addr = (ctx.get("property_address") or "the property").strip()
    subject = f"{short_addr} — chain notification, David Britton Estates"
    inner = (
        "<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear Sir/Madam,</p>"
        + _p_wrap(
            "We understand you are acting in a transaction that forms part of a chain connected to our sale of "
            f"<strong>{addr}</strong>, managed by David Britton Estates."
        )
        + _p_wrap(
            "We use NUVU, our sales progression platform, to actively coordinate all links in the chains we manage. "
            "Our aim is simple — to keep communication flowing so that no transaction stalls unnecessarily, including yours."
        )
        + _p_wrap(
            "We have no wish to add to your workload. We simply wanted to make ourselves known as the coordinating agent "
            "above you in this chain, and to let you know that if there is anything we can do to assist progress from our end, "
            "we are happy to do so."
        )
        + _p_wrap(
            "If you are able to confirm you are acting in this matter, that is all we need for now."
        )
        + _p_wrap("We look forward to a smooth completion for all parties.")
        + "<p style=\"margin:24px 0 0 0;line-height:1.5;font-size:15px;color:#1a1a1a;\">"
        "David Britton Estates, powered by NUVU</p>"
    )
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject.strip(), html_body


def render_chain_solicitor_nudge_1(ctx: dict[str, Any]) -> tuple[str, str]:
    addr = _esc(ctx.get("property_address"))
    short_addr = (ctx.get("property_address") or "the property").strip()
    subject = f"Quick follow-up — chain, {short_addr}"
    inner = (
        "<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear Sir/Madam,</p>"
        + _p_wrap(
            "We appreciate how busy conveyancing caseloads are at the moment. "
            "This is a brief courtesy follow-up regarding our earlier email about the chain involving "
            f"<strong>{addr}</strong>."
        )
        + _p_wrap(
            "If you could spare a moment, a one-line confirmation that you are acting in this matter is all we need."
        )
        + "<p style=\"margin:24px 0 0 0;line-height:1.5;font-size:15px;color:#1a1a1a;\">"
        "David Britton Estates, powered by NUVU</p>"
    )
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject, html_body


def render_chain_solicitor_nudge_2(ctx: dict[str, Any]) -> tuple[str, str]:
    addr = _esc(ctx.get("property_address"))
    short_addr = (ctx.get("property_address") or "the property").strip()
    subject = f"Final written follow-up — chain, {short_addr}"
    inner = (
        "<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear Sir/Madam,</p>"
        + _p_wrap(
            "This is our third and final written attempt regarding the chain connected to "
            f"<strong>{addr}</strong>."
        )
        + _p_wrap(
            "If we do not hear from you, we will ask our negotiator to follow up with you directly by telephone. "
            "You are very welcome to reply before that step if easier."
        )
        + "<p style=\"margin:24px 0 0 0;line-height:1.5;font-size:15px;color:#1a1a1a;\">"
        "David Britton Estates, powered by NUVU</p>"
    )
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject, html_body


def chain_solicitor_flag_note_text(firm: str, email: str) -> str:
    return (
        "⚠️ Chain solicitor unresponsive — "
        f"{firm} / {email} has not replied to 3 contact attempts (Days 0, 3, 6). "
        "Negotiator action required: please call and log outcome in notes to reinstate NUVU emails."
    )


def chain_solicitor_reinstate_prompt_text(firm: str) -> str:
    return (
        f"📞 Reminder: Have you called {firm}? Please log the outcome in notes — "
        'type "reinstate" to restart NUVU emails, or "no contact" to record the attempt.'
    )


def render_chain_solicitor_milestone_update(ctx: dict[str, Any]) -> tuple[str, str]:
    firm = _esc(ctx.get("firm_salutation") or "Sir/Madam")
    addr = _esc(ctx.get("property_address"))
    milestone = _esc(ctx.get("milestone_label") or "A progression step")
    done_date = _esc(ctx.get("milestone_date_display") or "")
    target = _esc(ctx.get("target_completion_phrase") or "10–12 weeks from agreement")
    short_addr = (ctx.get("property_address") or "the property").strip()
    subject = f"Chain update — {short_addr}"
    inner = (
        f"<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear {firm},</p>"
        + _p_wrap(
            f"A quick update on <strong>{addr}</strong>: <strong>{milestone}</strong> has been completed"
            f"{(' as of ' + done_date) if done_date else ''}. "
            f"Target completion remains <strong>{target}</strong>. We will keep you informed at each stage."
        )
        + "<p style=\"margin:24px 0 0 0;line-height:1.5;font-size:15px;color:#1a1a1a;\">"
        "David Britton Estates, powered by NUVU</p>"
    )
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject, html_body


def render_chain_solicitor_progress_request(ctx: dict[str, Any]) -> tuple[str, str]:
    firm = _esc(ctx.get("firm_salutation") or "Sir/Madam")
    addr = _esc(ctx.get("property_address"))
    weeks = int(ctx.get("weeks_in") or 4)
    short_addr = (ctx.get("property_address") or "the property").strip()
    subject = f"Progress request — week {weeks} — {short_addr}"
    inner = (
        f"<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear {firm},</p>"
        + _p_wrap(
            f"We are now <strong>{weeks} weeks</strong> into the transaction for <strong>{addr}</strong>. "
            "Could you provide a brief update on progress at your end? A one-line reply keeps everything moving smoothly."
        )
        + "<p style=\"margin:24px 0 0 0;line-height:1.5;font-size:15px;color:#1a1a1a;\">"
        "David Britton Estates, powered by NUVU</p>"
    )
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject, html_body


def render_stage4_search_fee_chase(day: int, ctx: dict[str, Any]) -> tuple[str, str]:
    """Phase B Stage 4 — buyer: search fees awareness (Days 0–1)."""
    addr = _esc(ctx.get("property_address"))
    buyer = _esc(ctx.get("buyer_name") or "there")
    neg = ctx.get("negotiator_name") or ""
    short_addr = (ctx.get("property_address") or "your purchase").strip()
    if day == 0:
        subject = f"Your purchase — a quick check-in ({short_addr})"
        body = (
            "Congratulations — your solicitor now has everything they need to get started. "
            "One thing worth checking: have they asked you to pay the search fees? "
            "Searches can’t be ordered until those are paid, and they’re one of the biggest variables "
            "in how long your move takes."
        )
    else:
        subject = f"Quick follow-up — {short_addr}"
        body = (
            "Quick follow-up: worth checking with your solicitor if search fees have been requested. "
            "Getting these paid early keeps everything moving."
        )
    inner = (
        f"<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear {buyer},</p>"
        + _p_wrap(body)
        + _p_wrap(f"This relates to <strong>{addr}</strong>.")
        + _sign_off(neg)
    )
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject.strip(), html_body


def render_stage4_search_fee_flag(ctx: dict[str, Any]) -> tuple[str, str, str]:
    """Stage 4 Day 3 — negotiator flag (no confirmation of search fees)."""
    addr = ctx.get("property_address") or ""
    summary = (
        "No confirmation of search fees paid after Stage 4 chases. "
        "Negotiator to follow up with buyer."
    )
    subject = f"[NUVU Chase] Search fees — action needed — {addr}"
    body = (
        "<div style=\"font-family:Segoe UI,system-ui,sans-serif;max-width:560px;\">"
        f"<p style=\"margin:0 0 12px 0;\"><strong>{_esc(summary)}</strong></p>"
        f"<p style=\"margin:0 0 8px 0;\">Property: <strong>{_esc(addr)}</strong></p>"
        "<p style=\"margin:0;color:#555;font-size:14px;\">NUVU chase engine — Stage 4 Day 3.</p>"
        "</div>"
    )
    return subject, body, summary


def render_stage5_draft_contract_chase(day: int, ctx: dict[str, Any]) -> tuple[str, str]:
    """Phase B Stage 5 — seller’s solicitor (Days 0–3)."""
    addr = _esc(ctx.get("property_address"))
    neg = ctx.get("negotiator_name") or ""
    short_addr = (ctx.get("property_address") or "the property").strip()
    firm = _esc(ctx.get("solicitor_firm") or "Colleagues")
    if day == 0:
        subject = f"Draft contract — forms received — {short_addr}"
        body = (
            f"We can confirm that the completed property information forms for <strong>{addr}</strong> "
            "have been received. Are you in a position to issue the draft contract?"
        )
    elif day == 1:
        subject = f"Following up — draft contract — {short_addr}"
        body = (
            f"Following up on the draft contract for <strong>{addr}</strong>. "
            "Any update on when this can be issued?"
        )
    elif day == 2:
        subject = f"Checking in — draft contract — {short_addr}"
        body = f"Checking in again on the draft contract for <strong>{addr}</strong>."
    else:
        subject = f"Draft contract — timescale — {short_addr}"
        body = (
            f"We are still awaiting the draft contract for <strong>{addr}</strong>. "
            "Could you advise on expected timescale?"
        )
    inner = (
        f"<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear {firm},</p>"
        + _p_wrap(body)
        + _p_wrap("If completion may be delayed, a short plan from you helps the buyer’s solicitor expedite searches where possible.")
        + _sign_off(neg)
    )
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject.strip(), html_body


def render_stage5_draft_contract_flag(ctx: dict[str, Any]) -> tuple[str, str, str]:
    addr = ctx.get("property_address") or ""
    summary = (
        "No draft contract after 4 days of chases. Negotiator to escalate with seller’s solicitor."
    )
    subject = f"[NUVU Chase] Draft contract overdue — {addr}"
    body = (
        "<div style=\"font-family:Segoe UI,system-ui,sans-serif;max-width:560px;\">"
        f"<p style=\"margin:0 0 12px 0;\"><strong>{_esc(summary)}</strong></p>"
        f"<p style=\"margin:0 0 8px 0;\">Property: <strong>{_esc(addr)}</strong></p>"
        "<p style=\"margin:0;color:#555;font-size:14px;\">NUVU chase engine — Stage 5 Day 4.</p>"
        "</div>"
    )
    return subject, body, summary


def render_stage6_searches_ordered_chase(day: int, ctx: dict[str, Any]) -> tuple[str, str]:
    """Phase B Stage 6 — buyer’s solicitor before searches_ordered confirmed (Days 0–1)."""
    addr = _esc(ctx.get("property_address"))
    neg = ctx.get("negotiator_name") or ""
    firm = _esc(ctx.get("solicitor_firm") or "Colleagues")
    short_addr = (ctx.get("property_address") or "the property").strip()
    if day == 0:
        subject = f"Searches — fees received — {short_addr}"
        body = (
            f"We understand search fees have been paid for <strong>{addr}</strong>. "
            "Have searches been ordered?"
        )
    else:
        subject = f"Following up — searches ordered — {short_addr}"
        body = (
            f"Following up — can you confirm searches have been ordered for <strong>{addr}</strong>?"
        )
    inner = (
        f"<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear {firm},</p>"
        + _p_wrap(body)
        + _sign_off(neg)
    )
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject.strip(), html_body


def render_stage6_search_results_chase(
    follow_up: bool, ctx: dict[str, Any], expected_working_days: int
) -> tuple[str, str]:
    """Stage 6 — buyer’s solicitor: search results (first ping or +3d chase)."""
    addr = _esc(ctx.get("property_address"))
    neg = ctx.get("negotiator_name") or ""
    firm = _esc(ctx.get("solicitor_firm") or "Colleagues")
    n = int(max(1, expected_working_days))
    short_addr = (ctx.get("property_address") or "the property").strip()
    if not follow_up:
        subject = f"Search results — {short_addr}"
        body = (
            f"Checking in on search results for <strong>{addr}</strong>. "
            f"Local authority turnaround is typically around <strong>{n}</strong> working days — "
            "have they come back yet?"
        )
    else:
        subject = f"Search results — update — {short_addr}"
        body = (
            f"Still awaiting search results for <strong>{addr}</strong>. Any update?"
        )
    inner = (
        f"<p style=\"margin:0 0 14px 0;line-height:1.55;font-size:15px;color:#1a1a1a;\">Dear {firm},</p>"
        + _p_wrap(body)
        + _sign_off(neg)
    )
    html_body = f"<div style=\"max-width:560px;font-family:Segoe UI,system-ui,sans-serif;\">{inner}</div>"
    return subject.strip(), html_body


def render_stage6_search_results_flag(ctx: dict[str, Any]) -> tuple[str, str, str]:
    addr = ctx.get("property_address") or ""
    summary = "Searches overdue for search results. Negotiator to follow up with buyer’s solicitor."
    subject = f"[NUVU Chase] Searches overdue — {addr}"
    body = (
        "<div style=\"font-family:Segoe UI,system-ui,sans-serif;max-width:560px;\">"
        f"<p style=\"margin:0 0 12px 0;\"><strong>{_esc(summary)}</strong></p>"
        f"<p style=\"margin:0 0 8px 0;\">Property: <strong>{_esc(addr)}</strong></p>"
        "<p style=\"margin:0;color:#555;font-size:14px;\">NUVU chase engine — Stage 6 +6d flag.</p>"
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
