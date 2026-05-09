"""Portal seller forms — Supabase portal_sessions / form_responses (Window 1 schema)."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from db_supabase import supabase_for_backend

DEMO_SESSION_ID = "00000000-0000-4000-8000-000000000001"

_TA6_TA10_TOTAL_QUESTIONS: int | None = None


def ta6_ta10_total_questions() -> int:
    """Combined TA6 + TA10 question count for combined portal sessions."""
    global _TA6_TA10_TOTAL_QUESTIONS
    if _TA6_TA10_TOTAL_QUESTIONS is not None:
        return _TA6_TA10_TOTAL_QUESTIONS
    import json

    root = Path(__file__).resolve().parent
    try:
        d6 = json.loads((root / "data" / "forms" / "ta6.json").read_text(encoding="utf-8"))
        d10 = json.loads((root / "data" / "forms" / "ta10.json").read_text(encoding="utf-8"))

        def cnt(d: dict) -> int:
            return sum(len(s.get("questions") or []) for s in d.get("sections") or [])

        _TA6_TA10_TOTAL_QUESTIONS = cnt(d6) + cnt(d10)
    except Exception:
        _TA6_TA10_TOTAL_QUESTIONS = 1
    return _TA6_TA10_TOTAL_QUESTIONS


def count_completed_form_responses(session_id: str) -> int:
    """How many questions are answered or skipped for this session."""
    rows = fetch_form_responses(session_id)
    return sum(1 for r in rows if r.get("status") in ("answered", "skipped"))


def demo_enabled() -> bool:
    """Railway / shell often add trailing spaces or a BOM; normalise before parsing."""
    raw = os.environ.get("PORTAL_FORM_DEMO", "") or ""
    v = raw.strip().strip("\ufeff").lower()
    return v in ("1", "true", "yes", "on")


def is_demo_session_id(session_id: str | None) -> bool:
    """Match the demo UUID regardless of surrounding whitespace or hex case."""
    a = (session_id or "").strip().lower()
    b = DEMO_SESSION_ID.strip().lower()
    return bool(a) and a == b


def _demo_session(form_type: str = "ta6") -> dict[str, Any]:
    return {
        "id": DEMO_SESSION_ID,
        "property_address": os.environ.get(
            "PORTAL_DEMO_ADDRESS", "12 Example Road, Coventry CV1 2AB"
        ),
        "seller_name": os.environ.get("PORTAL_DEMO_SELLER", "Alex Seller"),
        "form_type": (form_type or "ta6").lower(),
    }


def fetch_portal_session(
    session_id: str, form_type: str | None = None
) -> dict[str, Any] | None:
    if not session_id:
        return None
    if demo_enabled() and is_demo_session_id(session_id):
        d = _demo_session(form_type or "ta6")
        d.setdefault("status", "sent")
        d.setdefault("token", None)
        d.setdefault("submitted_at", None)
        d.setdefault("property_id", None)
        d.setdefault("seller_email", None)
        return d
    client = supabase_for_backend()
    try:
        res = (
            client.table("portal_sessions")
            .select("*")
            .eq("id", session_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def fetch_portal_session_by_token(token: str) -> dict[str, Any] | None:
    t = (token or "").strip()
    if not t:
        return None
    client = supabase_for_backend()
    try:
        res = (
            client.table("portal_sessions")
            .select("*")
            .eq("token", t)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def fetch_ta6_ta10_sessions_for_pipeline_ids(
    property_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """Latest ta6_ta10 portal_sessions row per sales_pipeline.id."""
    ids = [str(i).strip() for i in property_ids if str(i).strip()]
    if not ids:
        return {}
    client = supabase_for_backend()
    out: dict[str, dict[str, Any]] = {}
    for chunk in _chunked(list({i for i in ids}), 40):
        try:
            res = (
                client.table("portal_sessions")
                .select("*")
                .eq("form_type", "ta6_ta10")
                .in_("property_id", chunk)
                .execute()
            )
            for row in res.data or []:
                pid = str(row.get("property_id") or "")
                if not pid:
                    continue
                prev = out.get(pid)
                if not prev or str(row.get("id") or "") > str(prev.get("id") or ""):
                    out[pid] = row
        except Exception:
            continue
    return out


def fetch_ta6_ta10_session_for_pipeline(property_id: str) -> dict[str, Any] | None:
    pid = (property_id or "").strip()
    if not pid:
        return None
    client = supabase_for_backend()
    try:
        res = (
            client.table("portal_sessions")
            .select("*")
            .eq("property_id", pid)
            .eq("form_type", "ta6_ta10")
            .order("id", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def insert_portal_session_after_send(
    *,
    session_id: str,
    token: str,
    property_id: str,
    property_address: str,
    seller_name: str,
    seller_email: str,
    form_type: str = "ta6_ta10",
) -> bool:
    client = supabase_for_backend()
    row = {
        "id": session_id,
        "token": token,
        "property_id": property_id,
        "property_address": property_address,
        "seller_name": seller_name or "",
        "seller_email": seller_email,
        "form_type": form_type,
        "status": "sent",
    }
    try:
        client.table("portal_sessions").insert(row).execute()
        return True
    except Exception:
        return False


def update_portal_session_link_sent(session_id: str) -> None:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    client = supabase_for_backend()
    try:
        client.table("portal_sessions").update(
            {"status": "sent", "link_sent_at": now}
        ).eq("id", session_id).execute()
    except Exception:
        pass


def append_sales_progression_nuvu_note(progression_id: str, line: str) -> bool:
    from datetime import datetime, timezone

    pid = (progression_id or "").strip()
    if not pid or not (line or "").strip():
        return False
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = f"[{stamp}] {(line or '').strip()}"
    client = supabase_for_backend()
    try:
        res = (
            client.table("sales_progression")
            .select("nuvu_notes")
            .eq("id", pid)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return False
        prev = (rows[0].get("nuvu_notes") or "").strip()
        merged = f"{prev}\n{entry}".strip() if prev else entry
        client.table("sales_progression").update({"nuvu_notes": merged}).eq(
            "id", pid
        ).execute()
        return True
    except Exception:
        return False


def fetch_form_responses(session_id: str) -> list[dict[str, Any]]:
    if demo_enabled() and is_demo_session_id(session_id):
        from flask import session

        raw = session.get("portal_demo_responses") or []
        return list(raw)
    client = supabase_for_backend()
    try:
        res = (
            client.table("form_responses")
            .select(
                "id, session_id, section_key, question_key, answer, status, ai_conversation, updated_at"
            )
            .eq("session_id", session_id)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def _demo_store_response(session_id: str, row: dict[str, Any]) -> None:
    from flask import session

    store: list[dict[str, Any]] = list(session.get("portal_demo_responses") or [])
    key = (row.get("section_key"), row.get("question_key"))
    for i, existing in enumerate(store):
        if (existing.get("section_key"), existing.get("question_key")) == key:
            store[i] = {**existing, **row}
            break
    else:
        store.append(
            {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                **row,
            }
        )
    session["portal_demo_responses"] = store
    session.modified = True


def upsert_form_response(
    session_id: str,
    section_key: str,
    question_key: str,
    *,
    answer: dict[str, Any] | None,
    status: str,
    ai_conversation: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    payload: dict[str, Any] = {
        "session_id": session_id,
        "section_key": section_key,
        "question_key": question_key,
        "status": status,
        "answer": answer,
    }
    if ai_conversation is not None:
        payload["ai_conversation"] = ai_conversation

    if demo_enabled() and is_demo_session_id(session_id):
        _demo_store_response(session_id, payload)
        return payload

    client = supabase_for_backend()
    try:
        existing = (
            client.table("form_responses")
            .select("id")
            .eq("session_id", session_id)
            .eq("question_key", question_key)
            .limit(1)
            .execute()
        )
        rows = existing.data or []
        if rows:
            rid = rows[0]["id"]
            upd = {k: v for k, v in payload.items() if k != "session_id"}
            client.table("form_responses").update(upd).eq("id", rid).execute()
        else:
            ins = {**payload, "id": str(uuid.uuid4())}
            client.table("form_responses").insert(ins).execute()
        return payload
    except Exception:
        return None


def update_ai_conversation_only(
    session_id: str,
    section_key: str,
    question_key: str,
    messages: list[dict[str, str]],
) -> None:
    if demo_enabled() and is_demo_session_id(session_id):
        existing = None
        from flask import session as fsession

        for row in fsession.get("portal_demo_responses") or []:
            if row.get("question_key") == question_key and row.get("section_key") == section_key:
                existing = row
                break
        merged = {**(existing or {}), "ai_conversation": messages, "section_key": section_key, "question_key": question_key}
        if existing is None:
            merged.setdefault("status", "in_progress")
            merged.setdefault("answer", None)
        _demo_store_response(session_id, merged)
        return

    client = supabase_for_backend()
    try:
        existing = (
            client.table("form_responses")
            .select("id, answer, status")
            .eq("session_id", session_id)
            .eq("question_key", question_key)
            .limit(1)
            .execute()
        )
        rows = existing.data or []
        if rows:
            client.table("form_responses").update({"ai_conversation": messages}).eq(
                "id", rows[0]["id"]
            ).execute()
        else:
            client.table("form_responses").insert(
                {
                    "id": str(uuid.uuid4()),
                    "session_id": session_id,
                    "section_key": section_key,
                    "question_key": question_key,
                    "answer": None,
                    "status": "in_progress",
                    "ai_conversation": messages,
                }
            ).execute()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
#  form_completions (Window 3) — optional table; demo uses Flask session
# ─────────────────────────────────────────────────────────────


def _demo_completions() -> dict[str, dict[str, Any]]:
    from flask import session

    return session.setdefault("portal_demo_form_completions", {})


def fetch_form_completion_by_session(session_id: str) -> dict[str, Any] | None:
    if not session_id:
        return None
    if demo_enabled() and is_demo_session_id(session_id):
        return _demo_completions().get(session_id)
    client = supabase_for_backend()
    try:
        res = (
            client.table("form_completions")
            .select(
                "id, session_id, property_address, form_type, status, "
                "questions_answered, questions_total, pdf_path, "
                "reviewed_by, reviewed_at, dispatched_at, dispatched_to"
            )
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def upsert_form_completion_progress(
    session_id: str,
    property_address: str,
    form_type: str,
    *,
    answered: int,
    total: int,
    status: str,
) -> None:
    ft = (form_type or "ta6").lower()
    payload: dict[str, Any] = {
        "session_id": session_id,
        "property_address": property_address,
        "form_type": ft,
        "questions_answered": answered,
        "questions_total": total,
        "status": status,
    }
    if demo_enabled() and is_demo_session_id(session_id):
        prev = _demo_completions().get(session_id) or {}
        merged = {
            **prev,
            **payload,
            "id": prev.get("id") or "demo-completion",
        }
        _demo_completions()[session_id] = merged
        from flask import session as fs

        fs.modified = True
        return
    client = supabase_for_backend()
    try:
        client.table("form_completions").upsert(payload, on_conflict="session_id").execute()
    except Exception:
        pass


def update_form_completion_pdf_path(session_id: str, pdf_path: str) -> None:
    if demo_enabled() and is_demo_session_id(session_id):
        prev = _demo_completions().get(session_id) or {"session_id": session_id}
        _demo_completions()[session_id] = {**prev, "pdf_path": pdf_path}
        from flask import session as fs

        fs.modified = True
        return
    client = supabase_for_backend()
    try:
        client.table("form_completions").update({"pdf_path": pdf_path}).eq(
            "session_id", session_id
        ).execute()
    except Exception:
        pass


def record_form_completion_dispatch(
    session_id: str,
    *,
    reviewed_by: str,
    dispatched_to: str,
) -> None:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "reviewed_by": reviewed_by,
        "reviewed_at": now,
        "dispatched_at": now,
        "dispatched_to": dispatched_to,
        "status": "dispatched",
    }
    if demo_enabled() and is_demo_session_id(session_id):
        prev = _demo_completions().get(session_id) or {"session_id": session_id}
        _demo_completions()[session_id] = {**prev, **payload}
        from flask import session as fs

        fs.modified = True
        return
    client = supabase_for_backend()
    try:
        client.table("form_completions").update(payload).eq(
            "session_id", session_id
        ).execute()
    except Exception:
        pass


def _chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def fetch_portal_sessions_latest(limit: int = 400) -> list[dict[str, Any]]:
    client = supabase_for_backend()
    selects = (
        "id, property_address, seller_name, form_type, status, "
        "token, property_id, submitted_at, link_sent_at, seller_email",
        "id, property_address, seller_name, form_type",
    )
    for sel in selects:
        try:
            res = (
                client.table("portal_sessions")
                .select(sel)
                .order("id", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception:
            continue
    return []


def fetch_form_completions_for_sessions(
    session_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not session_ids:
        return {}
    client = supabase_for_backend()
    out: dict[str, dict[str, Any]] = {}
    for chunk in _chunked(list({str(s) for s in session_ids if s}), 80):
        try:
            res = (
                client.table("form_completions")
                .select(
                    "session_id, status, questions_answered, questions_total, "
                    "pdf_path, dispatched_at, dispatched_to, reviewed_at"
                )
                .in_("session_id", chunk)
                .execute()
            )
            for row in res.data or []:
                sid = str(row.get("session_id") or "")
                if sid:
                    out[sid] = row
        except Exception:
            continue
    return out


def enrich_properties_with_portal_forms(properties: list[dict]) -> None:
    """Mutate each property dict with portal_ta6 / portal_ta10 summary for the dashboard."""
    from utils.address import normalise_address

    sessions = fetch_portal_sessions_latest()
    by_norm_form: dict[tuple[str, str], dict[str, Any]] = {}
    for row in sessions:
        pa = row.get("property_address") or ""
        nk = normalise_address(pa)
        if not nk:
            continue
        ft = (row.get("form_type") or "ta6").lower()
        key = (nk, ft)
        if key not in by_norm_form:
            by_norm_form[key] = row

    if demo_enabled():
        d = _demo_session("ta6")
        nk0 = normalise_address(d["property_address"] or "")
        if nk0:
            by_norm_form[(nk0, "ta6")] = d

    sids = [str(r["id"]) for r in by_norm_form.values() if r.get("id")]
    completions = fetch_form_completions_for_sessions(sids)
    if demo_enabled():
        dc = _demo_completions().get(DEMO_SESSION_ID)
        if dc and DEMO_SESSION_ID in sids:
            completions[str(DEMO_SESSION_ID)] = dc

    def line_for(ft: str, nk: str) -> dict[str, Any]:
        sess = by_norm_form.get((nk, ft))
        if not sess:
            return {
                "status_line": "Not Started",
                "session_id": None,
                "progress_pct": None,
                "dispatched_at": None,
                "phase": "not_started",
            }
        sid = str(sess["id"])
        comp = completions.get(sid) or {}
        st = (comp.get("status") or "in_progress").lower()
        ans = int(comp.get("questions_answered") or 0)
        tot = int(comp.get("questions_total") or 0)
        pct = int(round(100 * ans / tot)) if tot else None
        disp = comp.get("dispatched_at")
        if st == "dispatched" and disp:
            ds = str(disp)[:10]
            return {
                "status_line": f"Dispatched {ds}",
                "session_id": sid,
                "progress_pct": 100,
                "dispatched_at": disp,
                "phase": "dispatched",
            }
        if st == "completed":
            return {
                "status_line": "Completed — Awaiting Review",
                "session_id": sid,
                "progress_pct": pct if pct is not None else 100,
                "dispatched_at": None,
                "phase": "completed",
            }
        if pct is not None and tot:
            return {
                "status_line": f"{pct}% Complete",
                "session_id": sid,
                "progress_pct": pct,
                "dispatched_at": None,
                "phase": "in_progress",
            }
        return {
            "status_line": "In progress",
            "session_id": sid,
            "progress_pct": pct,
            "dispatched_at": None,
            "phase": "in_progress",
        }

    pipe_ids = [str(p.get("_sales_pipeline_id") or "") for p in properties]
    ta6_ta10_by_pipe = fetch_ta6_ta10_sessions_for_pipeline_ids(pipe_ids)
    total_combo = ta6_ta10_total_questions()

    def ta6_ta10_line(pipe_id: str | None) -> dict[str, Any]:
        if not pipe_id:
            return {
                "status_line": "Not Started",
                "session_id": None,
                "progress_pct": None,
                "phase": "not_started",
                "link_sent": False,
            }
        row = ta6_ta10_by_pipe.get(str(pipe_id))
        if not row:
            return {
                "status_line": "Not Started",
                "session_id": None,
                "progress_pct": None,
                "phase": "not_started",
                "link_sent": False,
            }
        sid = str(row.get("id") or "")
        st = (row.get("status") or "draft").lower()
        if st == "submitted":
            return {
                "status_line": "Submitted",
                "session_id": sid,
                "progress_pct": 100,
                "phase": "submitted",
                "link_sent": bool(row.get("link_sent_at")),
            }
        done = count_completed_form_responses(sid)
        tot = max(1, total_combo)
        pct = int(round(100 * done / tot)) if tot else None
        link_sent = bool(row.get("link_sent_at")) or st == "sent"
        if done >= tot:
            return {
                "status_line": "Ready to submit",
                "session_id": sid,
                "progress_pct": 100,
                "phase": "ready_to_submit",
                "link_sent": link_sent,
            }
        if pct is not None:
            return {
                "status_line": f"{pct}% Complete (TA6 & TA10)",
                "session_id": sid,
                "progress_pct": pct,
                "phase": "in_progress",
                "link_sent": link_sent,
            }
        return {
            "status_line": "In progress",
            "session_id": sid,
            "progress_pct": pct,
            "phase": "in_progress",
            "link_sent": link_sent,
        }

    for p in properties:
        nk = normalise_address(p.get("address") or "")
        p["portal_ta6"] = line_for("ta6", nk)
        p["portal_ta10"] = line_for("ta10", nk)
        p["portal_ta6_ta10"] = ta6_ta10_line(p.get("_sales_pipeline_id"))
