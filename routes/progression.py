import os
from datetime import datetime

from flask import Blueprint, jsonify, request

import shared  # loads shared config (e.g. resend.api_key) and exports `sb`
import resend
from shared import sb

progression_bp = Blueprint("progression", __name__)

# ─────────────────────────────────────────────────────────────
#  PATCH API — update milestone dates and notes on progression
# ─────────────────────────────────────────────────────────────

ALLOWED_PATCH_FIELDS = {
    "offer_accepted",
    "memo_sent",
    "searches_ordered",
    "mortgage_offered",
    "enquiries_raised",
    "enquiries_answered",
    "exchange_date",
    "completion_date",
    "notes",
    "nuvu_notes",
    "buyer_solicitor_notes",
    "seller_solicitor_notes",
}


@progression_bp.route("/api/progression/<prog_id>", methods=["PATCH"])
def patch_progression(prog_id):
    """Update one or more fields on a sales_progression row."""
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No data provided"}), 400

    updates = {}
    for key, val in data.items():
        if key in ALLOWED_PATCH_FIELDS:
            updates[key] = val if val else None

    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    try:
        sb.table("sales_progression").update(updates).eq("id", prog_id).execute()
        return jsonify({"ok": True, "updated": list(updates.keys())})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
#  WELCOME ENGINE — 5 outbound emails on intake
# ─────────────────────────────────────────────────────────────

WELCOME_FROM = "David Britton Estates, powered by NUVU <salesprog@brittonestates.co.uk>"


def _completion_phrase(data):
    """Return formatted completion date or fallback phrase."""
    est = (data.get("est_completion") or "").strip()
    if est:
        try:
            dt = datetime.strptime(est, "%Y-%m-%d")
            return dt.strftime("%-d %B %Y")
        except Exception:
            pass
    return "a target of 10\u201312 weeks from today"


def _send_welcome_emails(data):
    """Fire tracks 1-5 of the Welcome Engine. Never raises."""
    if not os.environ.get("WELCOME_ENGINE_ENABLED", "false").lower() == "true":
        print(
            "Welcome Engine: disabled — set WELCOME_ENGINE_ENABLED=true to activate"
        )
        return

    addr = data.get("property_address", "")
    comp = _completion_phrase(data)

    # ── Track 1: Buyer ──────────────────────────────────────
    buyer_email = (data.get("buyer_email") or "").strip()
    buyer_name = data.get("buyer_name") or "there"
    if buyer_email:
        try:
            resend.Emails.send(
                {
                    "from": WELCOME_FROM,
                    "to": [buyer_email],
                    "subject": "Your move is underway \u2014 here\u2019s what happens next",
                    "html": (
                        f"<p>Dear {buyer_name},</p>"
                        f"<p>Congratulations on having your offer accepted on <strong>{addr}</strong>! "
                        "We are delighted to be looking after the sale for you and wanted to introduce ourselves.</p>"
                        "<p>We are David Britton Estates and we will be progressing this transaction through to completion. "
                        "Our job is to keep every party informed, chase outstanding actions, and make sure nothing falls through the cracks.</p>"
                        "<p><strong>What happens now?</strong></p>"
                        "<ul>"
                        "<li>A sales memorandum has been sent to both solicitors so they can begin the legal work.</li>"
                        "<li>We will be in regular contact with your solicitor to track progress on searches, enquiries, and contracts.</li>"
                        "<li>If you need a mortgage, please ensure your broker has submitted the full application as soon as possible.</li>"
                        "<li>If you need a survey, we recommend booking it within the first two weeks.</li>"
                        "</ul>"
                        f"<p>The current estimated completion date is <strong>{comp}</strong>. "
                        "We will update you if this changes.</p>"
                        "<p>If you have any questions at all, please do not hesitate to get in touch.</p>"
                        "<p>Kind regards,<br>The Sales Progression Team<br>David Britton Estates</p>"
                    ),
                }
            )
            print(f"Welcome Engine: Track 1 sent to {buyer_email}")
        except Exception as e:
            print(f"Welcome Engine: Track 1 FAILED for {buyer_email}: {e}")

    # ── Track 2: Seller ─────────────────────────────────────
    vendor_email = (data.get("vendor_email") or "").strip()
    vendor_name = data.get("vendor_name") or "there"
    if vendor_email:
        try:
            resend.Emails.send(
                {
                    "from": WELCOME_FROM,
                    "to": [vendor_email],
                    "subject": "Your sale is progressing \u2014 here\u2019s the plan",
                    "html": (
                        f"<p>Dear {vendor_name},</p>"
                        f"<p>Great news \u2014 we have accepted an offer on <strong>{addr}</strong> and the transaction is now officially Under Offer.</p>"
                        "<p>We are David Britton Estates and we will be progressing this sale through to completion on your behalf. "
                        "Our role is to coordinate between all parties, chase solicitors, and keep you informed at every stage.</p>"
                        "<p><strong>What happens now?</strong></p>"
                        "<ul>"
                        "<li>A sales memorandum has been sent to both your solicitor and the buyer\u2019s solicitor.</li>"
                        "<li>Your solicitor will prepare the contract pack and respond to any enquiries raised by the buyer\u2019s side.</li>"
                        "<li>We will chase weekly and escalate anything that stalls.</li>"
                        "</ul>"
                        f"<p>The current estimated completion date is <strong>{comp}</strong>. "
                        "We will keep you updated on any changes to this timeline.</p>"
                        "<p>If you have any questions, please get in touch at any time.</p>"
                        "<p>Kind regards,<br>The Sales Progression Team<br>David Britton Estates</p>"
                    ),
                }
            )
            print(f"Welcome Engine: Track 2 sent to {vendor_email}")
        except Exception as e:
            print(f"Welcome Engine: Track 2 FAILED for {vendor_email}: {e}")

    # ── Track 3: Buyer's Solicitor ──────────────────────────
    bs_email = (data.get("buyers_solicitor_email") or "").strip()
    bs_name = data.get("buyers_solicitor") or "Sirs/Madams"
    if bs_email:
        try:
            resend.Emails.send(
                {
                    "from": WELCOME_FROM,
                    "to": [bs_email],
                    "subject": f"{addr} \u2014 sales memorandum provided, transaction now Under Offer",
                    "html": (
                        f"<p>Dear {bs_name},</p>"
                        f"<p>We write to confirm that <strong>{addr}</strong> is now Under Offer and a sales memorandum has been issued to all parties.</p>"
                        "<p>We are David Britton Estates and we handle sales progression on behalf of the vendor. "
                        "We will be your main point of contact for chasing and coordinating this transaction.</p>"
                        "<p><strong>We kindly request:</strong></p>"
                        "<ul>"
                        "<li>Confirmation that you are instructed and have received the memorandum.</li>"
                        "<li>Please order searches at the earliest opportunity.</li>"
                        "<li>Any enquiries or issues \u2014 please raise them with us directly so we can resolve quickly.</li>"
                        "</ul>"
                        f"<p>The current estimated completion date is <strong>{comp}</strong>.</p>"
                        "<p>We look forward to working with you to bring this transaction to a successful conclusion.</p>"
                        "<p>Kind regards,<br>The Sales Progression Team<br>David Britton Estates</p>"
                    ),
                }
            )
            print(f"Welcome Engine: Track 3 sent to {bs_email}")
        except Exception as e:
            print(f"Welcome Engine: Track 3 FAILED for {bs_email}: {e}")

    # ── Track 4: Seller's Solicitor ─────────────────────────
    vs_email = (data.get("vendors_solicitor_email") or "").strip()
    vs_name = data.get("vendors_solicitor") or "Sirs/Madams"
    if vs_email:
        try:
            resend.Emails.send(
                {
                    "from": WELCOME_FROM,
                    "to": [vs_email],
                    "subject": f"{addr} \u2014 sales memorandum provided, transaction now Under Offer",
                    "html": (
                        f"<p>Dear {vs_name},</p>"
                        f"<p>We write to confirm that <strong>{addr}</strong> is now Under Offer and a sales memorandum has been issued to all parties.</p>"
                        "<p>We are David Britton Estates and we handle sales progression on behalf of the vendor. "
                        "We will be your main point of contact for chasing and coordinating this transaction.</p>"
                        "<p><strong>We kindly request:</strong></p>"
                        "<ul>"
                        "<li>Confirmation that you are instructed and have received the memorandum.</li>"
                        "<li>Please prepare the contract pack and title documents at the earliest opportunity.</li>"
                        "<li>Any enquiries or issues \u2014 please raise them with us directly so we can resolve quickly.</li>"
                        "</ul>"
                        f"<p>The current estimated completion date is <strong>{comp}</strong>.</p>"
                        "<p>We look forward to working with you to bring this transaction to a successful conclusion.</p>"
                        "<p>Kind regards,<br>The Sales Progression Team<br>David Britton Estates</p>"
                    ),
                }
            )
            print(f"Welcome Engine: Track 4 sent to {vs_email}")
        except Exception as e:
            print(f"Welcome Engine: Track 4 FAILED for {vs_email}: {e}")

    # ── Track 5: Chain Estate Agent ─────────────────────────
    ca_email = (data.get("chain_agent_email") or "").strip()
    if ca_email:
        try:
            resend.Emails.send(
                {
                    "from": WELCOME_FROM,
                    "to": [ca_email],
                    "subject": f"{addr} \u2014 chain coordination, David Britton Estates",
                    "html": (
                        "<p>Dear colleague,</p>"
                        f"<p>We are writing to introduce ourselves as the progressing agent for <strong>{addr}</strong>, which is now Under Offer.</p>"
                        "<p>We understand your property forms part of the chain linked to this transaction. "
                        "We would like to coordinate with you to ensure the chain progresses smoothly and any blockers are identified early.</p>"
                        "<p><strong>Could you please confirm:</strong></p>"
                        "<ul>"
                        "<li>The current status of your transaction.</li>"
                        "<li>Your estimated completion date.</li>"
                        "<li>Any known issues or dependencies we should be aware of.</li>"
                        "</ul>"
                        f"<p>Our current estimated completion date is <strong>{comp}</strong>. "
                        "We aim to keep all chain agents informed of progress on our side.</p>"
                        "<p>Please feel free to contact us at any time.</p>"
                        "<p>Kind regards,<br>The Sales Progression Team<br>David Britton Estates</p>"
                    ),
                }
            )
            print(f"Welcome Engine: Track 5 sent to {ca_email}")
        except Exception as e:
            print(f"Welcome Engine: Track 5 FAILED for {ca_email}: {e}")

