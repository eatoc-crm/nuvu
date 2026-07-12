from __future__ import annotations

import os
from datetime import datetime

from flask import Blueprint, jsonify, request

import shared  # loads shared config and exports `sb`
from email_engine import DEFAULT_SEND_FROM, send_html_email
from db_supabase import supabase_for_backend
from shared import require_nuvu_api_key, sb
from utils.events import emit_event
from utils.send_governor import governed_send

progression_bp = Blueprint("progression", __name__)

# Kill switch: when False, chain outreach is logged only (no Resend send).
CHAIN_OUTREACH_ENABLED = False

# Milestone-type fields on sales_progression that represent tracking dates/events.
# Note fields and email address fields are excluded.
_MILESTONE_FIELDS = {
    "offer_accepted", "memo_sent", "welcome_emails_sent",
    "searches_ordered", "searches_received", "search_fees_confirmed",
    "survey_instructed", "mortgage_offered", "draft_contract_sent",
    "draft_contract_issued", "enquiries_raised", "enquiries_answered",
    "exchange_target_date", "report_on_title", "exchange_date",
    "completion_date", "protocol_forms_returned", "seller_forms_returned",
}

# ─────────────────────────────────────────────────────────────
#  PATCH API — update milestone dates and notes on progression
# ─────────────────────────────────────────────────────────────

ALLOWED_PATCH_FIELDS = {
    "offer_accepted",
    "memo_sent",
    "welcome_emails_sent",
    "searches_ordered",
    "searches_received",
    "search_fees_confirmed",
    "survey_instructed",
    "mortgage_offered",
    "draft_contract_sent",
    "draft_contract_issued",
    "enquiries_raised",
    "enquiries_answered",
    "exchange_target_date",
    "report_on_title",
    "exchange_date",
    "completion_date",
    "protocol_forms_returned",
    "seller_forms_returned",
    "buyer_solicitor_email",
    "seller_solicitor_email",
    "notes",
    "nuvu_notes",
    "buyer_solicitor_notes",
    "seller_solicitor_notes",
}


@progression_bp.route("/api/progression/<prog_id>", methods=["PATCH"])
def patch_progression(prog_id):
    """Update one or more fields on a sales_progression row."""
    prog_id = (prog_id or "").strip()
    if not prog_id:
        return jsonify({"error": "Invalid progression id"}), 400

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
        client = supabase_for_backend()
        res = (
            client.table("sales_progression")
            .update(updates)
            .eq("id", prog_id)
            .select("id,property_address")
            .execute()
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not (res.data or []):
        return (
            jsonify(
                {
                    "error": (
                        "No sales_progression row was updated (check id). "
                        "If RLS blocks updates, set SUPABASE_SERVICE_ROLE_KEY for this server."
                    )
                }
            ),
            409,
        )

    try:
        from routes.chain_chase import (
            chain_inform_milestone_field,
            check_reinstate_keywords_on_note_text,
            notify_confirmed_chain_solicitors_milestone,
        )

        if "nuvu_notes" in updates:
            check_reinstate_keywords_on_note_text(
                prog_id, str(updates.get("nuvu_notes") or "")
            )
        for k, v in updates.items():
            if v and chain_inform_milestone_field(k):
                notify_confirmed_chain_solicitors_milestone(prog_id, k)
    except Exception as ex:
        print(f"[progression] chain chase hooks after PATCH failed: {ex}")

    try:
        from routes.chase_engine import on_sales_progression_patch

        on_sales_progression_patch(prog_id, list(updates.keys()))
    except Exception as ex:
        print(f"[progression] chase engine Phase B hook after PATCH failed: {ex}")

    property_address = (res.data[0].get("property_address") or "").strip() if res.data else ""
    for k, v in updates.items():
        if v and k in _MILESTONE_FIELDS and property_address:
            emit_event(
                event_type="milestone_changed",
                property_address=property_address,
                summary=f"Milestone updated: {k} → {v}",
                actor="staff",
                payload={
                    "milestone": k,
                    "new_value": str(v),
                    "source": "manual",
                },
            )

    return jsonify({"ok": True, "updated": list(updates.keys())})


# ─────────────────────────────────────────────────────────────
#  WELCOME ENGINE — 5 outbound emails on intake
# ─────────────────────────────────────────────────────────────

WELCOME_FROM = "David Britton Estates, powered by NUVU <salesprog@brittonestates.co.uk>"


def _send_welcome_email(
    to_email: str,
    subject: str,
    html: str,
    track: str,
    property_address: str,
    trigger: str | None = None,
) -> None:
    result = governed_send(
        "welcome",
        to_email,
        subject,
        html,
        metadata={
            "source": "welcome_engine",
            "track": track,
            "property_address": property_address,
        },
        from_address=WELCOME_FROM,
        property_address=property_address,
    )
    if trigger:
        emit_event(
            event_type="comms_sent",
            property_address=property_address,
            actor="system",
            summary=f"Welcome Engine {track}: {result}",
            payload={
                "trigger": trigger,
                "track": track,
                "category": "welcome",
                "recipient": to_email,
                "subject": subject,
                "outcome": result,
            },
        )
    if result != "sent":
        raise RuntimeError(result)


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


def _send_welcome_emails(data, trigger: str | None = None):
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
            _send_welcome_email(
                buyer_email,
                "Your move is underway \u2014 here\u2019s what happens next",
                (
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
                "track_1_buyer",
                addr,
                trigger,
            )
            print(f"Welcome Engine: Track 1 sent to {buyer_email}")
        except Exception as e:
            print(f"Welcome Engine: Track 1 FAILED for {buyer_email}: {e}")

    # ── Track 2: Seller ─────────────────────────────────────
    vendor_email = (data.get("vendor_email") or "").strip()
    vendor_name = data.get("vendor_name") or "there"
    if vendor_email:
        try:
            _send_welcome_email(
                vendor_email,
                "Your sale is progressing \u2014 here\u2019s the plan",
                (
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
                "track_2_seller",
                addr,
                trigger,
            )
            print(f"Welcome Engine: Track 2 sent to {vendor_email}")
        except Exception as e:
            print(f"Welcome Engine: Track 2 FAILED for {vendor_email}: {e}")

    # ── Track 3: Buyer's Solicitor ──────────────────────────
    bs_email = (data.get("buyers_solicitor_email") or "").strip()
    bs_name = data.get("buyers_solicitor") or "Sirs/Madams"
    if bs_email:
        try:
            _send_welcome_email(
                bs_email,
                f"{addr} \u2014 sales memorandum provided, transaction now Under Offer",
                (
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
                "track_3_buyer_solicitor",
                addr,
                trigger,
            )
            print(f"Welcome Engine: Track 3 sent to {bs_email}")
        except Exception as e:
            print(f"Welcome Engine: Track 3 FAILED for {bs_email}: {e}")

    # ── Track 4: Seller's Solicitor ─────────────────────────
    vs_email = (data.get("vendors_solicitor_email") or "").strip()
    vs_name = data.get("vendors_solicitor") or "Sirs/Madams"
    if vs_email:
        try:
            _send_welcome_email(
                vs_email,
                f"{addr} \u2014 sales memorandum provided, transaction now Under Offer",
                (
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
                "track_4_seller_solicitor",
                addr,
                trigger,
            )
            print(f"Welcome Engine: Track 4 sent to {vs_email}")
        except Exception as e:
            print(f"Welcome Engine: Track 4 FAILED for {vs_email}: {e}")

    # ── Track 5: Chain Estate Agent ─────────────────────────
    ca_email = (data.get("chain_agent_email") or "").strip()
    if ca_email:
        try:
            _send_welcome_email(
                ca_email,
                f"{addr} \u2014 chain coordination, David Britton Estates",
                (
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
                "track_5_chain_agent",
                addr,
                trigger,
            )
            print(f"Welcome Engine: Track 5 sent to {ca_email}")
        except Exception as e:
            print(f"Welcome Engine: Track 5 FAILED for {ca_email}: {e}")


# ─────────────────────────────────────────────────────────────
#  CHAIN SOLICITOR OUTREACH
# ─────────────────────────────────────────────────────────────


@progression_bp.route("/api/chain/outreach", methods=["POST"])
def api_chain_outreach():
    """Request solicitor details from a chain link's estate agent (email)."""
    auth_err = require_nuvu_api_key()
    if auth_err:
        return auth_err

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    chain_link_id = (data.get("chain_link_id") or "").strip()
    if not chain_link_id:
        return jsonify({"error": "chain_link_id is required"}), 400

    try:
        cl_r = (
            sb.table("chain_links")
            .select(
                "id,property_id,link_address,estate_agent_email,"
                "buyer_solicitor,seller_solicitor,solicitor_details_requested"
            )
            .eq("id", chain_link_id)
            .limit(1)
            .execute()
        )
    except Exception as e:
        return jsonify({"error": f"lookup failed: {e}"}), 500

    if not cl_r.data:
        return jsonify({"error": "Not found"}), 404

    cl = cl_r.data[0]
    if cl.get("solicitor_details_requested") is True:
        return (
            jsonify({"error": "Outreach already sent for this chain link"}),
            400,
        )
    try:
        ccs_r = (
            sb.table("chain_chase_state")
            .select("solicitor_details_requested")
            .eq("chain_link_id", chain_link_id)
            .limit(1)
            .execute()
        )
        if ccs_r.data and ccs_r.data[0].get("solicitor_details_requested") is True:
            return (
                jsonify({"error": "Outreach already sent for this chain link"}),
                400,
            )
    except Exception:
        pass

    agent_email = (cl.get("estate_agent_email") or "").strip()
    if not agent_email:
        return (
            jsonify(
                {"error": "No estate agent email on file for this chain link"}
            ),
            400,
        )

    buyer_sol = (cl.get("buyer_solicitor") or "").strip()
    seller_sol = (cl.get("seller_solicitor") or "").strip()
    if buyer_sol and seller_sol:
        return (
            jsonify({"error": "Solicitor details already on file"}),
            400,
        )

    prop_id = cl.get("property_id")
    if not prop_id:
        return jsonify({"error": "Parent property not found"}), 404

    try:
        pr_r = (
            sb.table("sales_progression")
            .select("id,property_address,staff_initials")
            .eq("id", prop_id)
            .limit(1)
            .execute()
        )
    except Exception as e:
        return jsonify({"error": f"progression lookup failed: {e}"}), 500

    if not pr_r.data:
        return jsonify({"error": "Parent property not found"}), 404

    prog = pr_r.data[0]
    property_address = (prog.get("property_address") or "").strip()
    if not property_address:
        return jsonify({"error": "Parent property not found"}), 404

    sign_name = (prog.get("staff_initials") or "").strip()
    if not sign_name:
        try:
            pipe_r = (
                sb.table("sales_pipeline")
                .select("negotiator")
                .eq("property_address", property_address)
                .limit(1)
                .execute()
            )
            if pipe_r.data:
                sign_name = (pipe_r.data[0].get("negotiator") or "").strip()
        except Exception:
            pass
    sign_off = sign_name if sign_name else "The Sales Progression Team"

    link_address = (cl.get("link_address") or "").strip() or "your linked property"
    subject = f"Sales Progression — {link_address}"

    html = (
        "<p>Dear colleague,</p>"
        f"<p>We are writing from <strong>David Britton Estates</strong>, the agent "
        f"progressing the sale of <strong>{property_address}</strong>.</p>"
        f"<p><strong>{link_address}</strong> forms part of the same chain, and we are "
        "coordinating progression across all parties.</p>"
        "<p>To keep matters moving smoothly, could you please share the buyer and seller "
        "solicitor details for your transaction at your earliest convenience? "
        "Having everyone on record helps us align searches, enquiries, and key dates.</p>"
        "<p>Thank you for your help.</p>"
        f"<p>Kind regards,<br>{sign_off}<br>David Britton Estates</p>"
    )

    live = False
    if CHAIN_OUTREACH_ENABLED:
        try:
            send_result = send_html_email(
                agent_email,
                subject,
                html,
                from_address=DEFAULT_SEND_FROM,
                property_address=property_address,
            )
            if send_result != "sent":
                return jsonify({"error": f"email send blocked: {send_result}"}), 503
            live = True
            print(
                f"Chain outreach: sent to {agent_email} "
                f"(chain_link_id={chain_link_id})"
            )
        except Exception as e:
            return jsonify({"error": f"email send failed: {e}"}), 500
    else:
        print(
            "Chain outreach (dry run — set CHAIN_OUTREACH_ENABLED=True to send): "
            f"to={agent_email!r} subject={subject!r} chain_link_id={chain_link_id}"
        )

    try:
        sb.table("chain_chase_state").upsert(
            {
                "chain_link_id": chain_link_id,
                "property_address": property_address,
                "solicitor_details_requested": True,
                "updated_at": datetime.utcnow().isoformat(),
            },
            on_conflict="chain_link_id",
        ).execute()
    except Exception as e:
        return jsonify({"error": f"update failed: {e}"}), 500

    return (
        jsonify(
            {
                "status": "outreach_sent",
                "chain_link_id": str(chain_link_id),
                "live": live,
            }
        ),
        200,
    )

