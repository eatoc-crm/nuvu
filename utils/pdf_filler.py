"""Fill Law Society TA6/TA10 PDFs from portal form_responses.

Mappings are keyed by portal ``question_key`` values from ``data/forms/ta6.json`` /
``ta10.json`` (merged chat UX), not raw Law Society clause ids. Each mapping value
is the target PDF AcroForm field name, or \"\" until you wire it.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.address import normalise_address

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "data" / "templates"
FORMS_DIR = ROOT / "data" / "forms"
OUTPUT_DIR = ROOT / "generated_pdfs"


def _form_json_path(form_type: str) -> Path:
    ft = (form_type or "ta6").lower()
    return FORMS_DIR / ("ta6.json" if ft == "ta6" else "ta10.json")


def _mapping_path(form_type: str) -> Path:
    ft = (form_type or "ta6").lower()
    return FORMS_DIR / ("ta6_pdf_mapping.json" if ft == "ta6" else "ta10_pdf_mapping.json")


def iter_portal_question_keys(form_type: str) -> list[str]:
    """All ``question.key`` values from the portal form JSON (authoritative)."""
    path = _form_json_path(form_type)
    data = json.loads(path.read_text(encoding="utf-8"))
    keys: list[str] = []
    for sec in data.get("sections") or []:
        for q in sec.get("questions") or []:
            k = (q.get("key") or "").strip()
            if k:
                keys.append(k)
    return keys


def load_pdf_mapping(form_type: str) -> dict[str, str]:
    """question_key -> PDF field name. Ignores JSON keys starting with ``_``."""
    path = _mapping_path(form_type)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("PDF mapping must be a JSON object")
    out: dict[str, str] = {}
    for k, v in raw.items():
        if str(k).startswith("_"):
            continue
        if not isinstance(v, str):
            continue
        out[str(k)] = v
    return out


def mapping_validation_warnings(form_type: str, mapping: dict[str, str]) -> list[str]:
    """Return issues such as mapping keys that are not portal question_keys (typos)."""
    form_keys = set(iter_portal_question_keys(form_type))
    warnings: list[str] = []
    for mk in mapping:
        if mk not in form_keys:
            warnings.append(f"Mapping key not in {form_type}.json: {mk!r}")
    return warnings


def _slug(addr: str) -> str:
    n = normalise_address(addr)
    if not n:
        return "property"
    s = re.sub(r"[^a-z0-9]+", "-", n)[:80].strip("-")
    return s or "property"


def load_pdf_field_names(template_path: Path) -> dict[str, Any]:
    """Return pypdf ``get_fields()`` for discovery against a blank template."""
    from pypdf import PdfReader

    reader = PdfReader(str(template_path))
    return reader.get_fields() or {}


def _template_path(form_type: str) -> Path:
    ft = (form_type or "ta6").lower()
    return TEMPLATES_DIR / ("ta6_blank.pdf" if ft == "ta6" else "ta10_blank.pdf")


def _answer_to_text(answer: Any) -> str:
    if answer is None:
        return ""
    if isinstance(answer, str):
        return answer
    if isinstance(answer, bool):
        return "Yes" if answer else "No"
    if isinstance(answer, (int, float)):
        return str(answer)
    if isinstance(answer, dict):
        return json.dumps(answer, ensure_ascii=False)
    if isinstance(answer, list):
        return ", ".join(_answer_to_text(x) for x in answer)
    return str(answer)


def _flatten_responses(rows: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in rows:
        qk = (row.get("question_key") or "").strip()
        if not qk:
            continue
        if row.get("status") == "skipped":
            out[qk] = ""
            continue
        if row.get("status") != "answered":
            continue
        out[qk] = _answer_to_text(row.get("answer"))
    return out


def fill_ta_form(form_type: str, property_address: str, session_id: str) -> str:
    """Generate a filled PDF; update ``form_completions.pdf_path``; return absolute path.

    Only portal question_keys present in the mapping with a non-empty PDF field
    name are written. Mapping must align with ``data/forms/ta{6,10}.json``.
    """
    from pypdf import PdfReader, PdfWriter

    from db_portal import fetch_form_responses, update_form_completion_pdf_path

    ft = (form_type or "ta6").lower()
    tpl = _template_path(ft)
    if not tpl.is_file():
        raise FileNotFoundError(
            f"Missing blank PDF template: {tpl}. Add the official Law Society file there."
        )
    if not _form_json_path(ft).is_file():
        raise FileNotFoundError(f"Missing portal form JSON: {_form_json_path(ft)}")

    mapping = load_pdf_mapping(ft)
    _warns = mapping_validation_warnings(ft, mapping)
    if _warns:
        for msg in _warns:
            print(f"[pdf_filler] {msg}")

    reader = PdfReader(str(tpl))
    if not reader.get_fields():
        raise ValueError(
            "This PDF has no fillable form fields (flat PDF). "
            "Stop and obtain fillable Law Society templates before continuing."
        )

    answers = _flatten_responses(fetch_form_responses(session_id))
    writer = PdfWriter()
    if hasattr(writer, "append"):
        writer.append(reader)
    else:
        writer.append_pages_from_reader(reader)

    field_updates: dict[str, Any] = {}
    for q_key, pdf_field in mapping.items():
        pdf_field = (pdf_field or "").strip()
        if not pdf_field:
            continue
        if q_key not in answers:
            continue
        field_updates[pdf_field] = answers.get(q_key, "")

    for page in writer.pages:
        if field_updates:
            writer.update_page_form_field_values(
                page, field_updates, auto_regenerate=False
            )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_name = f"{_slug(property_address)}_{ft}_{ts}.pdf"
    out_path = OUTPUT_DIR / out_name
    with open(out_path, "wb") as f:
        writer.write(f)

    rel = str(out_path.relative_to(ROOT))
    update_form_completion_pdf_path(session_id, rel.replace("\\", "/"))
    return str(out_path)
