"""Seller TA6 / TA10 portal — conversational flow, JSON forms, Supabase persistence."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request, session as flask_session, url_for

from db_portal import (
    DEMO_SESSION_ID,
    demo_enabled,
    fetch_form_completion_by_session,
    fetch_form_responses,
    fetch_portal_session,
    update_ai_conversation_only,
    upsert_form_completion_progress,
    upsert_form_response,
)
from routes.portal_notify import notify_team_form_completed
from utils.portal_config import portal_forms_enabled

portal_forms_bp = Blueprint("portal_forms", __name__, url_prefix="/portal")

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
    return render_template(
        "portal/portal_form.html",
        session_id=session_id,
        form_type=form_type,
        property_address=session.get("property_address", ""),
        seller_name=session.get("seller_name", ""),
        portal_ai_enabled=_portal_ai_enabled(),
        staff_view=staff_view,
        initial_form=_public_form(form),
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

    return render_template(
        "portal/portal_seller_review.html",
        session_id=session_id,
        form_type=form_type,
        property_address=session.get("property_address", ""),
        seller_name=session.get("seller_name", ""),
        form_title=form.get("title") or form_type.upper(),
        sections=sections,
        staff_view=staff_view,
        back_url=url_for(
            "portal_forms.portal_form_page",
            session_id=session_id,
            form=form_type,
            q=back_index,
        ),
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
    form_type = (body.get("form_type") or session.get("form_type") or "ta6").lower()
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
    form_type = (body.get("form_type") or session.get("form_type") or "ta6").lower()
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
    skipped_n = sum(
        1
        for item in flat
        if by.get((item["section_key"], item["question"]["key"]), {}).get("status")
        == "skipped"
    )
    answered_only = answered - skipped_n
    is_complete = answered >= len(flat)
    if is_complete:
        prev = fetch_form_completion_by_session(session_id)
        prev_status = ((prev or {}).get("status") or "").lower()
        upsert_form_completion_progress(
            session_id,
            session.get("property_address") or "",
            form_type,
            answered=answered,
            total=len(flat),
            status="completed",
        )
        if prev_status != "completed":
            form_label = "TA6" if form_type == "ta6" else "TA10"
            notify_team_form_completed(
                form_label=form_label,
                property_address=session.get("property_address") or "",
                seller_name=session.get("seller_name") or "Seller",
                answered=answered_only,
                total=len(flat),
                skipped=skipped_n,
            )
    else:
        upsert_form_completion_progress(
            session_id,
            session.get("property_address") or "",
            form_type,
            answered=answered,
            total=len(flat),
            status="in_progress",
        )
    return jsonify(
        {
            "ok": True,
            "progress": {"answered": answered, "total": len(flat)},
            "complete": is_complete,
        }
    )
