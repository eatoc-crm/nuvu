"""Seller TA6 / TA10 portal — conversational flow, JSON forms, Supabase persistence."""

from __future__ import annotations

import json
import os
import secrets
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request, session as flask_session, url_for

from db_portal import (
    DEMO_SESSION_ID,
    append_sales_progression_nuvu_note,
    count_completed_form_responses,
    demo_enabled,
    fetch_form_completion_by_session,
    fetch_form_responses,
    fetch_portal_session,
    fetch_portal_session_by_token,
    fetch_ta6_ta10_session_for_pipeline,
    insert_portal_session_after_send,
    ta6_ta10_total_questions,
    update_ai_conversation_only,
    update_portal_session_link_sent,
    upsert_form_completion_progress,
    upsert_form_response,
)
from db_supabase import fetch_sales_progression_by_property_address, supabase_for_backend
from routes.portal_notify import (
    notify_negotiator_ta6_ta10_submitted,
    notify_team_form_completed,
    send_ta6_ta10_seller_portal_link_email,
)
from utils.portal_config import portal_dispatch_enabled, portal_forms_enabled

portal_forms_bp = Blueprint("portal_forms", __name__, url_prefix="/portal")
portal_staff_api_bp = Blueprint("portal_staff_api", __name__)

ROOT = Path(__file__).resolve().parents[1]
FORMS_DIR = ROOT / "data" / "forms"


def _env_bool(name: str, default: str = "true") -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes")


def _portal_ai_enabled() -> bool:
    return _env_bool("PORTAL_AI_ENABLED", "true")


@lru_cache(maxsize=2)
def _load_form_json_cached(name: str) -> dict:
    path = FORMS_DIR / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def load_form(form_type: str) -> dict:
    ft = (form_type or "ta6").lower()
    fname = "ta6.json" if ft == "ta6" else "ta10.json"
    return _load_form_json_cached(fname)


def _flatten_questions(form: dict) -> list[dict]:
    out = []
    for sec in form.get("sections") or []:
        for q in sec.get("questions") or []:
            out.append(
                {
                    "section_key": sec["key"],
                    "section_title": sec.get("title", ""),
                    "question": q,
                }
            )
    return out


def _strip_ai_prompt(obj: dict) -> dict:
    """Public form JSON — ai_prompt stays server-side for /api/chat."""
    o = {k: v for k, v in obj.items() if k != "ai_prompt"}
    return o


def _public_form(form: dict) -> dict:
    return {
        **{k: v for k, v in form.items() if k != "sections"},
        "sections": [
            {
                **{k: v for k, v in sec.items() if k != "questions"},
                "questions": [_strip_ai_prompt(q) for q in sec.get("questions") or []],
            }
            for sec in form.get("sections") or []
        ],
    }


def _responses_index(rows: list[dict]) -> dict[tuple[str, str], dict]:
    return {(r.get("section_key"), r.get("question_key")): r for r in rows}


def _flatten_form_meta(form_type: str, form: dict) -> list[dict]:
    out = []
    qi = 0
    for sec in form.get("sections") or []:
        sk = sec.get("key") or ""
        for q in sec.get("questions") or []:
            out.append(
                {
                    "form_type": form_type,
                    "section_key": sk,
                    "section_title": sec.get("title", ""),
                    "question": q,
                    "question_index": qi,
                }
            )
            qi += 1
    return out


def _build_ta6_ta10_review_sections(session_id: str) -> tuple[list[dict], str]:
    rows = fetch_form_responses(session_id)
    by_q = _responses_index(rows)
    bundles = [
        ("ta6", "TA6", load_form("ta6")),
        ("ta10", "TA10", load_form("ta10")),
    ]
    sections_out: list[dict] = []
    for ft, label, form in bundles:
        meta = _flatten_form_meta(ft, form)
        idx_map = {
            (m["section_key"], m["question"]["key"]): m["question_index"] for m in meta
        }
        for sec in form.get("sections") or []:
            section_key = sec.get("key") or ""
            items = []
            for question in sec.get("questions") or []:
                qk = question.get("key") or ""
                row = by_q.get((section_key, qk)) or {}
                status = row.get("status") or "pending"
                q_idx = idx_map.get((section_key, qk), 0)
                items.append(
                    {
                        "question_index": q_idx,
                        "edit_form": ft,
                        "question_text": question.get("text") or qk,
                        "status": status,
                        "display_answer": _display_review_answer(question, row.get("answer")),
                    }
                )
            sections_out.append(
                {
                    "key": f"{ft}__{section_key}",
                    "title": f"{label} — {sec.get('title') or section_key}",
                    "items": items,
                }
            )
    return sections_out, "TA6 & TA10"


def _negotiator_inbox_email(pipe_row: dict | None) -> str:
    if not pipe_row:
        return "salesprog@brittonestates.co.uk"
    for key in ("negotiator_email", "negotiatorEmail"):
        v = (pipe_row.get(key) or "").strip()
        if v and "@" in v:
            return v
    neg = (pipe_row.get("negotiator") or "").strip()
    if neg and "@" in neg:
        return neg
    return "salesprog@brittonestates.co.uk"


def _display_review_answer(question: dict, answer) -> str:
    if answer is None:
        return ""
    if isinstance(answer, dict):
        if isinstance(answer.get("values"), list):
            return ", ".join(str(v) for v in answer["values"] if v is not None)
        if "value" in answer:
            value = answer.get("value")
            q_type = (question.get("answer_type") or question.get("type") or "").lower()
            if isinstance(value, bool):
                return "Yes" if value else "No"
            if value is None and q_type in ("boolean", "yes_no_not_known"):
                return "Not known"
            return "" if value is None else str(value)
        parts = []
        for key, value in answer.items():
            if value is None:
                continue
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            parts.append(f"{key}: {value}")
        return "\n".join(parts)
    if isinstance(answer, list):
        return ", ".join(str(v) for v in answer if v is not None)
    if isinstance(answer, bool):
        return "Yes" if answer else "No"
    return str(answer)


def _prior_answers_text(form: dict, rows: list[dict], until_section: str, until_key: str) -> str:
    idx = _flatten_questions(form)
    stop_at = None
    for i, item in enumerate(idx):
        if item["section_key"] == until_section and item["question"]["key"] == until_key:
            stop_at = i
            break
    if stop_at is None:
        stop_at = len(idx)
    by = _responses_index(rows)
    lines = []
    for i in range(0, stop_at):
        sk = idx[i]["section_key"]
        qk = idx[i]["question"]["key"]
        row = by.get((sk, qk))
        if not row or row.get("status") != "answered":
            continue
        ans = row.get("answer") or {}
        label = idx[i]["question"].get("text", qk)
        lines.append(f"- {label}: {json.dumps(ans, ensure_ascii=False)}")
    return "\n".join(lines) if lines else "(No earlier answers yet.)"


def _system_prompt(
    session: dict,
    form: dict,
    section_title: str,
    question: dict,
    prior_block: str,
) -> str:
    ai = question.get("ai_prompt") or "Help the seller answer accurately and calmly."
    addr = session.get("property_address") or "the property"
    seller = session.get("seller_name") or "the seller"
    parts = [
        "You are a friendly UK property sale assistant helping a seller complete their Law Society form.",
        f"Property: {addr}. Seller name on file: {seller}.",
        f"Form: {form.get('title')} ({form.get('version', '')}).",
        f"Current section: {section_title}.",
        f"Official question text:\n{question.get('text', '')}",
        f"Guidance for you:\n{ai}",
        "Earlier answers from this seller (for context only):\n" + prior_block,
        "Tone: warm, patient, jargon-free. Sellers may be older or less tech-confident. "
        "Explain legal terms simply. Never rush or pressure. Professional guidance with dignity.",
        "When the seller has given enough information, summarise their answer clearly in plain English, "
        'then ask exactly: "Shall I save this as your answer?" and wait for them to confirm before '
        "they use the save control (you cannot save yourself).",
    ]
    return "\n\n".join(parts)


def _claude_messages(system: str, messages: list[dict]) -> str:
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return "Anthropic is not configured (missing ANTHROPIC_API_KEY). Type your answer below and use Save answer."
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        temperature=0.7,
        system=system,
        messages=[{"role": m["role"], "content": m["content"]} for m in messages],
    )
    for block in msg.content:
        if hasattr(block, "text"):
            return block.text
    return ""


@portal_forms_bp.route("/form")
def portal_form_page():
    if not portal_forms_enabled():
        return render_template("portal/coming_soon.html"), 503
    session_id = (request.args.get("session_id") or "").strip()
    if not session_id and demo_enabled():
        session_id = DEMO_SESSION_ID
    form_type = (request.args.get("form") or "ta6").lower()
    if not session_id:
        return (
            render_template(
                "portal/portal_error.html",
                message="This page needs a valid session link. Please use the link from your email or ask your estate agent to resend it.",
            ),
            400,
        )
    session = fetch_portal_session(session_id, form_type=form_type)
    if not session:
        return (
            render_template(
                "portal/portal_error.html",
                message="This link is not valid or has expired. Please request a new link from your estate agent.",
            ),
            404,
        )
    staff_view = bool(flask_session.get("nuvu_email"))
    form = load_form(form_type)
    session_form_type = (session.get("form_type") or form_type or "ta6").lower()
    return render_template(
        "portal/portal_form.html",
        session_id=session_id,
        form_type=form_type,
        session_form_type=session_form_type,
        property_address=session.get("property_address", ""),
        seller_name=session.get("seller_name", ""),
        portal_ai_enabled=_portal_ai_enabled(),
        staff_view=staff_view,
        initial_form=_public_form(form),
    )


def _first_open_wizard_url(session_id: str, db_form_type: str) -> str:
    rows = fetch_form_responses(session_id)
    by_q = _responses_index(rows)
    order = ("ta6", "ta10") if (db_form_type or "").lower() == "ta6_ta10" else ((db_form_type or "ta6").lower(),)
    for ft in order:
        form = load_form(ft)
        flat = _flatten_questions(form)
        for i, item in enumerate(flat):
            r = by_q.get((item["section_key"], item["question"]["key"])) or {}
            if r.get("status") not in ("answered", "skipped"):
                return url_for(
                    "portal_forms.portal_form_page",
                    session_id=session_id,
                    form=ft,
                    q=i,
                )
        last_ft, last_i = ft, max(len(flat) - 1, 0)
    return url_for(
        "portal_forms.portal_form_page",
        session_id=session_id,
        form=last_ft,
        q=last_i,
    )


@portal_forms_bp.route("/form/review")
def portal_form_review_page():
    if not portal_forms_enabled():
        return render_template("portal/coming_soon.html"), 503
    session_id = (request.args.get("session_id") or "").strip()
    if not session_id and demo_enabled():
        session_id = DEMO_SESSION_ID
    form_type = (request.args.get("form") or "ta6").lower()
    if not session_id:
        return (
            render_template(
                "portal/portal_error.html",
                message="This page needs a valid session link. Please use the link from your email or ask your estate agent to resend it.",
            ),
            400,
        )
    session = fetch_portal_session(session_id, form_type=form_type)
    if not session:
        return (
            render_template(
                "portal/portal_error.html",
                message="This link is not valid or has expired. Please request a new link from your estate agent.",
            ),
            404,
        )

    staff_view = bool(flask_session.get("nuvu_email"))
    db_form = (session.get("form_type") or form_type or "ta6").lower()
    merged = db_form == "ta6_ta10"
    submitted = (session.get("status") or "").lower() == "submitted"
    read_only = staff_view or submitted
    portal_token = (session.get("token") or "").strip() if not staff_view else ""
    submitted_at = session.get("submitted_at") or ""

    if merged:
        sections, form_title = _build_ta6_ta10_review_sections(session_id)
        review_form_type = "ta6_ta10"
        back_url = _first_open_wizard_url(session_id, db_form)
        submission_ready = count_completed_form_responses(session_id) >= ta6_ta10_total_questions()
    else:
        form = load_form(form_type)
        rows = fetch_form_responses(session_id)
        by_q = _responses_index(rows)
        flat = _flatten_questions(form)
        first_open = next(
            (
                i
                for i, item in enumerate(flat)
                if (by_q.get((item["section_key"], item["question"]["key"])) or {}).get("status")
                not in ("answered", "skipped")
            ),
            None,
        )
        back_index = first_open if first_open is not None else max(len(flat) - 1, 0)
        sections = []
        question_index = 0
        for sec in form.get("sections") or []:
            section_key = sec.get("key") or ""
            items = []
            for question in sec.get("questions") or []:
                question_key = question.get("key") or ""
                row = by_q.get((section_key, question_key)) or {}
                status = row.get("status") or "pending"
                items.append(
                    {
                        "question_index": question_index,
                        "edit_form": form_type,
                        "question_text": question.get("text") or question_key,
                        "status": status,
                        "display_answer": _display_review_answer(question, row.get("answer")),
                    }
                )
                question_index += 1
            sections.append(
                {
                    "key": section_key,
                    "title": sec.get("title") or section_key,
                    "items": items,
                }
            )
        form_title = form.get("title") or form_type.upper()
        review_form_type = form_type
        back_url = url_for(
            "portal_forms.portal_form_page",
            session_id=session_id,
            form=form_type,
            q=back_index,
        )
        submission_ready = bool(flat) and all(
            (by_q.get((item["section_key"], item["question"]["key"])) or {}).get("status")
            in ("answered", "skipped")
            for item in flat
        )

    return render_template(
        "portal/portal_seller_review.html",
        session_id=session_id,
        form_type=review_form_type,
        property_address=session.get("property_address", ""),
        seller_name=session.get("seller_name", ""),
        form_title=form_title,
        sections=sections,
        staff_view=staff_view,
        read_only=read_only,
        submitted=submitted,
        submitted_at=submitted_at,
        submission_ready=submission_ready,
        portal_dispatch_enabled=portal_dispatch_enabled(),
        portal_token=portal_token,
        back_url=back_url,
    )


@portal_forms_bp.route("/api/form-state", methods=["GET"])
def api_form_state():
    if not portal_forms_enabled():
        return jsonify({"error": "Portal disabled"}), 503
    session_id = (request.args.get("session_id") or "").strip()
    form_type = (request.args.get("form") or "ta6").lower()
    if not session_id:
        return jsonify({"error": "session_id required"}), 400
    session = fetch_portal_session(session_id, form_type=form_type)
    if not session:
        return jsonify({"error": "Unknown session"}), 404
    form = load_form(form_type)
    rows = fetch_form_responses(session_id)
    flat = _flatten_questions(form)
    by = _responses_index(rows)
    answered = 0
    for item in flat:
        r = by.get((item["section_key"], item["question"]["key"]))
        if r and r.get("status") in ("answered", "skipped"):
            answered += 1
    total = len(flat)
    if (session.get("form_type") or "").lower() == "ta6_ta10":
        answered = count_completed_form_responses(session_id)
        total = ta6_ta10_total_questions()
    return jsonify(
        {
            "form": _public_form(form),
            "responses": rows,
            "progress": {"answered": answered, "total": total},
            "portal_ai_enabled": _portal_ai_enabled(),
            "demo_session_id": DEMO_SESSION_ID,
        }
    )


@portal_forms_bp.route("/api/chat", methods=["POST"])
def api_chat():
    if not portal_forms_enabled():
        return jsonify({"error": "Portal disabled"}), 503
    body = request.get_json(silent=True) or {}
    session_id = (body.get("session_id") or "").strip()
    section_key = (body.get("section_key") or "").strip()
    question_key = (body.get("question_key") or "").strip()
    messages = body.get("messages") or []
    if not session_id or not section_key or not question_key:
        return jsonify({"error": "session_id, section_key and question_key required"}), 400
    form_type_hint = (body.get("form_type") or "ta6").lower()
    session = fetch_portal_session(session_id, form_type=form_type_hint)
    if not session:
        return jsonify({"error": "Unknown session"}), 404
    form_type = (body.get("form_type") or "ta6").lower()
    form = load_form(form_type)
    question = None
    section_title = ""
    for sec in form.get("sections") or []:
        if sec.get("key") != section_key:
            continue
        section_title = sec.get("title", "")
        for q in sec.get("questions") or []:
            if q.get("key") == question_key:
                question = q
                break
    if not question:
        return jsonify({"error": "Question not found"}), 404
    rows = fetch_form_responses(session_id)
    prior = _prior_answers_text(form, rows, section_key, question_key)
    if not _portal_ai_enabled():
        return jsonify(
            {
                "reply": "",
                "messages": messages,
                "portal_ai_enabled": False,
            }
        )
    system = _system_prompt(session, form, section_title, question, prior)
    try:
        reply = _claude_messages(system, messages)
    except Exception as exc:
        return jsonify({"error": str(exc), "reply": None}), 502
    merged = list(messages)
    if reply:
        merged.append({"role": "assistant", "content": reply})
    update_ai_conversation_only(session_id, section_key, question_key, merged)
    return jsonify({"reply": reply, "messages": merged, "portal_ai_enabled": True})


@portal_forms_bp.route("/api/save-answer", methods=["POST"])
def api_save_answer():
    if not portal_forms_enabled():
        return jsonify({"error": "Portal disabled"}), 503
    body = request.get_json(silent=True) or {}
    session_id = (body.get("session_id") or "").strip()
    section_key = (body.get("section_key") or "").strip()
    question_key = (body.get("question_key") or "").strip()
    status = (body.get("status") or "answered").strip()
    answer = body.get("answer")
    messages = body.get("messages")
    if not session_id or not section_key or not question_key:
        return jsonify({"error": "session_id, section_key and question_key required"}), 400
    if status not in ("answered", "skipped"):
        return jsonify({"error": "status must be answered or skipped"}), 400
    form_type_hint = (body.get("form_type") or "ta6").lower()
    session = fetch_portal_session(session_id, form_type=form_type_hint)
    if not session:
        return jsonify({"error": "Unknown session"}), 404
    if status == "skipped":
        answer = None
    row = upsert_form_response(
        session_id,
        section_key,
        question_key,
        answer=answer,
        status=status,
        ai_conversation=messages if isinstance(messages, list) else None,
    )
    if row is None:
        return jsonify({"error": "Could not save — database unavailable."}), 503
    form_type = (body.get("form_type") or "ta6").lower()
    db_form = (session.get("form_type") or form_type or "ta6").lower()
    combo = db_form == "ta6_ta10"
    form = load_form(form_type)
    rows = fetch_form_responses(session_id)
    flat = _flatten_questions(form)
    by = _responses_index(rows)
    answered = sum(
        1
        for item in flat
        if by.get((item["section_key"], item["question"]["key"]), {}).get("status")
        in ("answered", "skipped")
    )
    skipped_n = sum(1 for r in rows if r.get("status") == "skipped")
    if combo:
        total_all = ta6_ta10_total_questions()
        answered_all = count_completed_form_responses(session_id)
        answered_only = max(0, answered_all - skipped_n)
        is_complete = answered_all >= total_all
        comp_ft = "ta6_ta10"
        comp_answered = answered_all
        comp_total = total_all
    else:
        skipped_n = sum(
            1
            for item in flat
            if by.get((item["section_key"], item["question"]["key"]), {}).get("status")
            == "skipped"
        )
        answered_only = answered - skipped_n
        is_complete = answered >= len(flat)
        comp_ft = form_type
        comp_answered = answered
        comp_total = len(flat)
    if is_complete:
        prev = fetch_form_completion_by_session(session_id)
        prev_status = ((prev or {}).get("status") or "").lower()
        upsert_form_completion_progress(
            session_id,
            session.get("property_address") or "",
            comp_ft,
            answered=comp_answered,
            total=comp_total,
            status="completed",
        )
        if prev_status != "completed":
            form_label = (
                "TA6/TA10"
                if combo
                else ("TA6" if form_type == "ta6" else "TA10")
            )
            notify_team_form_completed(
                form_label=form_label,
                property_address=session.get("property_address") or "",
                seller_name=session.get("seller_name") or "Seller",
                answered=answered_only,
                total=comp_total,
                skipped=skipped_n,
            )
    else:
        upsert_form_completion_progress(
            session_id,
            session.get("property_address") or "",
            comp_ft,
            answered=comp_answered,
            total=comp_total,
            status="in_progress",
        )
    return jsonify(
        {
            "ok": True,
            "progress": {
                "answered": comp_answered if combo else answered,
                "total": comp_total if combo else len(flat),
            },
            "complete": is_complete,
        }
    )


@portal_forms_bp.route("/form/ta6_ta10")
def portal_ta6_ta10_magic_entry():
    """Resolve ?token= from seller email and start the combined wizard on TA6."""
    if not portal_forms_enabled():
        return render_template("portal/coming_soon.html"), 503
    token = (request.args.get("token") or "").strip()
    if not token:
        return (
            render_template(
                "portal/portal_error.html",
                message="This page needs a valid link from your email.",
            ),
            400,
        )
    row = fetch_portal_session_by_token(token)
    if not row:
        return (
            render_template(
                "portal/portal_error.html",
                message="This link is not valid or has expired. Please request a new link from your estate agent.",
            ),
            404,
        )
    sid = str(row.get("id") or "")
    return redirect(
        url_for(
            "portal_forms.portal_form_page",
            session_id=sid,
            form="ta6",
        )
    )


@portal_forms_bp.route("/form/submitted")
def portal_form_submitted_page():
    if not portal_forms_enabled():
        return render_template("portal/coming_soon.html"), 503
    session_id = (request.args.get("session_id") or "").strip()
    if not session_id and demo_enabled():
        session_id = DEMO_SESSION_ID
    if not session_id:
        return (
            render_template(
                "portal/portal_error.html",
                message="Missing session.",
            ),
            400,
        )
    session = fetch_portal_session(session_id, form_type="ta6_ta10")
    if not session:
        return (
            render_template(
                "portal/portal_error.html",
                message="This link is not valid or has expired.",
            ),
            404,
        )
    if (session.get("status") or "").lower() != "submitted":
        return redirect(
            url_for(
                "portal_forms.portal_form_review_page",
                session_id=session_id,
                form="ta6_ta10",
            )
        )
    return render_template(
        "portal/portal_submitted.html",
        session_id=session_id,
        property_address=session.get("property_address", ""),
        seller_name=session.get("seller_name", ""),
    )


@portal_forms_bp.route("/api/submit", methods=["POST"])
def api_portal_submit():
    if not portal_forms_enabled():
        return jsonify({"error": "Portal disabled"}), 503
    if not portal_dispatch_enabled():
        return jsonify(
            {
                "ok": False,
                "error": "Form submission is currently disabled. Please contact your estate agent.",
                "disabled": True,
            }
        ), 200
    body = request.get_json(silent=True) or {}
    token = (body.get("token") or "").strip()
    if not token:
        return jsonify({"ok": False, "error": "token required"}), 400
    row = fetch_portal_session_by_token(token)
    if not row:
        return jsonify({"ok": False, "error": "Invalid or expired token"}), 404
    sid = str(row.get("id") or "")
    if (row.get("status") or "").lower() == "submitted":
        return jsonify(
            {
                "ok": True,
                "redirect": url_for(
                    "portal_forms.portal_form_submitted_page", session_id=sid
                ),
            }
        )
    if (row.get("form_type") or "").lower() != "ta6_ta10":
        return jsonify({"ok": False, "error": "Submit is only available for combined forms."}), 400
    if count_completed_form_responses(sid) < ta6_ta10_total_questions():
        return jsonify({"ok": False, "error": "Please complete all questions first."}), 400

    addr = (row.get("property_address") or "").strip()
    prog = fetch_sales_progression_by_property_address(addr) if addr else None
    prog_id = str((prog or {}).get("id") or "")
    pipe_id = str(row.get("property_id") or "")
    client = supabase_for_backend()
    prev_submitted = row.get("submitted_at")
    prev_status = (row.get("status") or "").lower()
    prev_proto = (prog or {}).get("protocol_forms_returned") if prog else None
    prev_notes = (prog or {}).get("nuvu_notes") if prog else None
    now = datetime.now(timezone.utc).isoformat()
    try:
        client.table("portal_sessions").update(
            {"status": "submitted", "submitted_at": now}
        ).eq("id", sid).execute()
        if prog_id:
            client.table("sales_progression").update(
                {"protocol_forms_returned": now}
            ).eq("id", prog_id).execute()
            append_sales_progression_nuvu_note(
                prog_id,
                "Seller submitted Property Information Form and Fittings & Contents Form via portal.",
            )
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    pipe_row = None
    if pipe_id:
        try:
            pr = (
                client.table("sales_pipeline")
                .select("*")
                .eq("id", pipe_id)
                .limit(1)
                .execute()
            )
            pipe_row = (pr.data or [None])[0]
        except Exception:
            pipe_row = None
    to_neg = _negotiator_inbox_email(pipe_row)
    base = (os.environ.get("NUVU_BASE_URL") or request.host_url.rstrip("/")).rstrip("/")
    staff_review = f"{base}/portal/review/{sid}"
    try:
        notify_negotiator_ta6_ta10_submitted(
            to_email=to_neg,
            seller_name=(row.get("seller_name") or "Seller"),
            property_address=addr or "the property",
            staff_review_url=staff_review,
        )
    except Exception:
        try:
            client.table("portal_sessions").update(
                {"status": prev_status or "sent", "submitted_at": prev_submitted}
            ).eq("id", sid).execute()
            if prog_id:
                client.table("sales_progression").update(
                    {
                        "protocol_forms_returned": prev_proto,
                        "nuvu_notes": prev_notes,
                    }
                ).eq("id", prog_id).execute()
        except Exception:
            pass
        return jsonify({"ok": False, "error": "Could not send confirmation email — try again."}), 502

    return jsonify(
        {
            "ok": True,
            "redirect": url_for(
                "portal_forms.portal_form_submitted_page", session_id=sid
            ),
        }
    )


@portal_staff_api_bp.route("/api/portal/send-link", methods=["POST"])
def api_portal_send_link():
    from flask import session as fl_session

    if not fl_session.get("nuvu_email"):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    if not portal_dispatch_enabled():
        return jsonify(
            {"success": False, "error": "Portal dispatch is currently disabled.", "disabled": True}
        ), 200
    body = request.get_json(silent=True) or {}
    property_id = (body.get("property_id") or "").strip()
    form_type = (body.get("form_type") or "").strip().lower()
    if not property_id or form_type != "ta6_ta10":
        return jsonify({"success": False, "error": "property_id and form_type ta6_ta10 required"}), 400

    client = supabase_for_backend()
    try:
        pr = (
            client.table("sales_pipeline")
            .select("*")
            .eq("id", property_id)
            .limit(1)
            .execute()
        )
        pipe = (pr.data or [None])[0]
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    if not pipe:
        return jsonify({"success": False, "error": "Property not found"}), 404

    addr = (pipe.get("property_address") or "").strip()
    prog = fetch_sales_progression_by_property_address(addr) if addr else None
    seller_email = ((prog or {}).get("vendor_email") or "").strip()
    seller_name = ((prog or {}).get("vendor_name") or "").strip() or "there"
    negotiator_name = (pipe.get("negotiator") or "").strip()
    if not seller_email or "@" not in seller_email:
        return jsonify(
            {
                "success": False,
                "error": "No seller email on file — add it in the CRM first.",
            }
        ), 400

    existing = fetch_ta6_ta10_session_for_pipeline(property_id)
    base = (os.environ.get("NUVU_BASE_URL") or request.host_url.rstrip("/")).rstrip("/")
    prog_id = str((prog or {}).get("id") or "")

    if existing:
        sid = str(existing.get("id") or "")
        use_token = (existing.get("token") or "").strip() or secrets.token_urlsafe(32)
        if not (existing.get("token") or "").strip():
            try:
                client.table("portal_sessions").update({"token": use_token}).eq(
                    "id", sid
                ).execute()
            except Exception:
                return jsonify({"success": False, "error": "Could not persist session token"}), 500
        magic = f"{base}/portal/form/ta6_ta10?token={use_token}"
        try:
            send_ta6_ta10_seller_portal_link_email(
                to_email=seller_email,
                seller_name=seller_name,
                property_address=addr or "your property",
                negotiator_name=negotiator_name,
                magic_link_url=magic,
            )
        except Exception as exc:
            return jsonify({"success": False, "error": f"Email failed to send — try again. ({exc})"}), 502
        update_portal_session_link_sent(sid)
        if prog_id:
            append_sales_progression_nuvu_note(
                prog_id, f"TA6/TA10 portal link resent to {seller_email}"
            )
        return jsonify(
            {"success": True, "token": use_token, "status": "sent", "resent": True}
        )

    token = secrets.token_urlsafe(32)
    magic = f"{base}/portal/form/ta6_ta10?token={token}"
    try:
        send_ta6_ta10_seller_portal_link_email(
            to_email=seller_email,
            seller_name=seller_name,
            property_address=addr or "your property",
            negotiator_name=negotiator_name,
            magic_link_url=magic,
        )
    except Exception as exc:
        return jsonify({"success": False, "error": f"Email failed to send — try again. ({exc})"}), 502

    sid = str(uuid.uuid4())
    if not insert_portal_session_after_send(
        session_id=sid,
        token=token,
        property_id=property_id,
        property_address=addr,
        seller_name=seller_name,
        seller_email=seller_email,
        form_type="ta6_ta10",
    ):
        return jsonify({"success": False, "error": "Could not create portal session"}), 500
    update_portal_session_link_sent(sid)
    if prog_id:
        append_sales_progression_nuvu_note(
            prog_id, f"TA6/TA10 portal link sent to {seller_email}"
        )
    return jsonify({"success": True, "token": token, "status": "sent"})
