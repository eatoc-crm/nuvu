#!/usr/bin/env python3
"""
Batch import Alto progression PDFs: parse notes, match sales_pipeline, prepend
formatted notes to sales_progression.nuvu_notes only (no milestone writes).

Generates Claude-assisted milestone review at ~/Desktop/alto_milestone_review.txt
and notes-only revert SQL at ~/Desktop/alto_import_revert.sql.

Usage (from repo root, .env with Supabase + ANTHROPIC_API_KEY):
  .venv_import/bin/python scripts/alto_pdf_notes_import.py /path/to/Alto-screens

Optional:
  --skip-claude   Write placeholder review (no ANTHROPIC_API_KEY)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from pypdf import PdfReader

from db_supabase import supabase_for_backend
from utils.address import normalise_address

NOTE_START = re.compile(
    r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})\s+(\d{2}:\d{2})\s*[\u2010\u2011\u2012\u2013\u2014\u2212-]\s*([^\n]*)",
    re.MULTILINE,
)

ADDRESS_BLOCK = re.compile(
    r"Property\s+Address\s*(.+?)\s*Type\s",
    re.IGNORECASE | re.DOTALL,
)

MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

# Milestone columns shown to Claude + listed in CURRENT MILESTONES
MILESTONE_CONTEXT_COLS = [
    "search_fees_confirmed",
    "searches_ordered",
    "searches_received",
    "draft_contract_issued",
    "seller_forms_returned",
    "survey_instructed",
    "enquiries_raised",
    "enquiries_answered",
    "report_on_title",
    "exchange_target_date",
]

UK_POSTCODE_RE = re.compile(
    r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b", re.IGNORECASE
)

# v3: U+2500 light horizontal, ~37 chars, wraps each note (above + below).
NOTE_ENTRY_SEPARATOR = "\u2500" * 37


@dataclass
class AltoNote:
    dt: datetime
    author: str
    body: str
    raw_header: str = ""


@dataclass
class ParsedPdf:
    path: Path
    address_lines: list[str]
    full_address: str
    notes: list[AltoNote] = field(default_factory=list)
    error: str | None = None


def _anthropic_api_key() -> str:
    return (
        os.environ.get("ANTHROPIC_API_KEY", "").strip()
        or os.environ.get("ANTHROPIC_KEY_FOR_RAILWAY", "").strip()
    )


def extract_pdf_text(path: Path) -> str:
    r = PdfReader(str(path))
    parts: list[str] = []
    for p in r.pages:
        parts.append(p.extract_text() or "")
    return "\n".join(parts)


def parse_address(text: str) -> tuple[list[str], str] | None:
    m = ADDRESS_BLOCK.search(text)
    if not m:
        return None
    block = m.group(1).strip()
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    if not lines:
        return None
    full = ", ".join(lines)
    return lines, full


def parse_notes_blob(text: str) -> list[AltoNote]:
    m = re.search(r"\bNotes\s*\n", text, re.IGNORECASE)
    if not m:
        return []
    blob = text[m.end() :]
    matches = list(NOTE_START.finditer(blob))
    out: list[AltoNote] = []
    for i, mo in enumerate(matches):
        start = mo.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(blob)
        chunk = blob[start:end]
        lines = chunk.splitlines()
        if not lines:
            continue
        wk, d, mon, y, hm, author = mo.groups()
        author = (author or "").strip()
        body_lines = lines[1:]
        while body_lines and body_lines[0].strip().lower() in (
            "note",
            "email",
        ):
            body_lines = body_lines[1:]
        body = "\n".join(body_lines).strip()
        try:
            day_i = int(d)
            year_i = int(y)
            hh, mm = map(int, hm.split(":"))
            mon_i = MONTHS[mon.lower()[:3]]
            dt = datetime(year_i, mon_i, day_i, hh, mm)
        except (ValueError, KeyError):
            continue
        out.append(AltoNote(dt=dt, author=author, body=body, raw_header=lines[0]))
    return out


def postcode_from_lines(lines: list[str]) -> str | None:
    for ln in reversed(lines):
        for pc in UK_POSTCODE_RE.findall(ln):
            return pc.upper().replace(" ", "")
    return None


def street_match_key(lines: list[str]) -> str:
    if not lines:
        return ""
    first = lines[0].strip()
    first = re.sub(r",+", ",", first).strip(",").strip()
    return first


def sanitise_ilike_fragment(s: str) -> str:
    return re.sub(r"[%_\\]+", " ", (s or "")).strip()


def trim_trailing_per_line(text: str) -> str:
    return "\n".join(ln.rstrip() for ln in (text or "").splitlines())


def format_single_note(n: AltoNote) -> str:
    """Date/author line ending with colon; body on following lines; internal newlines preserved."""
    header = f'[{n.dt.strftime("%a %d %b %Y %H:%M")}] {n.author}:'
    body = trim_trailing_per_line(n.body or "").strip()
    return f"{header}\n{body}"


def format_note_entry_v3(n: AltoNote) -> str:
    """v3: separator above and below; date/author + body unchanged from v2 (format_single_note)."""
    inner = format_single_note(n)
    return f"{NOTE_ENTRY_SEPARATOR}\n{inner}\n{NOTE_ENTRY_SEPARATOR}"


def build_import_block(notes: list[AltoNote], import_date: str) -> str:
    """
    --- Alto Progression Notes (imported DD MMM YYYY) ---

    ─ (x37)
    [Date] Author:
    body...
    ─ (x37)

    (blank line between notes)

    ─ (x37)
    next note...
    """
    lines_out: list[str] = [
        f"--- Alto Progression Notes (imported {import_date}) ---",
        "",
    ]
    ordered = sorted(notes, key=lambda x: x.dt, reverse=True)
    if not ordered:
        return "\n".join(lines_out)
    entries = [format_note_entry_v3(n) for n in ordered]
    lines_out.append("\n\n".join(entries))
    return "\n".join(lines_out)


def notes_plain_for_claude(notes: list[AltoNote]) -> str:
    parts = []
    for n in sorted(notes, key=lambda x: x.dt, reverse=True):
        parts.append(
            f"[{n.dt.strftime('%a %d %b %Y %H:%M')}] {n.author}:\n{trim_trailing_per_line(n.body)}"
        )
    return "\n\n---\n\n".join(parts)


def score_pipeline_row(
    pipe_addr: str,
    pipe_postcode: str | None,
    pdf_lines: list[str],
    pdf_pc_norm: str | None,
) -> float:
    score = 0.0
    pnorm = normalise_address(pipe_addr)
    pdf_full = normalise_address(", ".join(pdf_lines))
    if pdf_pc_norm and pipe_postcode:
        ppc = normalise_address(pipe_postcode).replace(" ", "")
        if ppc == pdf_pc_norm.replace(" ", ""):
            score += 200.0
    ptoks = set(pnorm.split())
    dtoks = set(pdf_full.split())
    score += 5.0 * len(ptoks & dtoks)
    score += min(len(pnorm), 80) * 0.05
    if pnorm == pdf_full:
        score += 300.0
    return score


def pick_best_pipeline(
    rows: list[dict],
    pdf_lines: list[str],
    pdf_pc_norm: str | None,
) -> dict | None:
    if not rows:
        return None
    best = None
    best_s = -1.0
    for r in rows:
        s = score_pipeline_row(
            (r.get("property_address") or "").strip(),
            (r.get("postcode") or "").strip() or None,
            pdf_lines,
            pdf_pc_norm,
        )
        if s > best_s:
            best_s = s
            best = r
    return best


def sql_escape_str(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def sql_value(val) -> str:
    if val is None or val == "":
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val)
    if re.match(r"^\d{4}-\d{2}-\d{2}([T ].*)?$", s):
        if "T" in s or "+" in s or s.endswith("Z"):
            return sql_escape_str(s) + "::timestamptz"
        return sql_escape_str(s) + "::date"
    return sql_escape_str(s)


def fetch_pipeline_ilike(client, key: str) -> list[dict]:
    if not key or len(key.strip()) < 2:
        return []
    pat = f"%{sanitise_ilike_fragment(key)}%"
    try:
        res = (
            client.table("sales_pipeline")
            .select("id,property_address,postcode")
            .ilike("property_address", pat)
            .limit(80)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def fetch_progression_by_address(client, addr: str) -> dict | None:
    addr = (addr or "").strip()
    if not addr:
        return None
    cols = "id,property_address,nuvu_notes," + ",".join(MILESTONE_CONTEXT_COLS)
    try:
        res = (
            client.table("sales_progression")
            .select(cols)
            .eq("property_address", addr)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def current_milestones_lines(prog: dict) -> list[str]:
    lines = []
    for c in MILESTONE_CONTEXT_COLS:
        v = prog.get(c)
        if v is not None and str(v).strip() != "":
            lines.append(f"  {c} = {v}")
    return lines if lines else ["  (none set)"]


def call_claude_milestone_review(
    ai_client,
    model: str,
    property_label: str,
    pipeline_id: str,
    milestone_lines: list[str],
    notes_plain: str,
) -> str:
    system = (
        "You are analysing UK property sales progression notes from an estate agent's CRM. "
        "For each property, summarise the key progression events, and suggest which NUVU milestones "
        "can be confidently set based on the evidence. Be conservative — only suggest a milestone if "
        "the notes clearly confirm it happened. Flag anything ambiguous.\n\n"
        "Milestones to check for: search_fees_confirmed, searches_ordered, searches_received, "
        "draft_contract_issued, seller_forms_returned, survey_instructed, enquiries_raised, "
        "enquiries_answered, report_on_title, exchange_target_date.\n\n"
        "Also flag: completed properties, exchanged properties, properties with legal holds or complications."
    )
    user = (
        f"Property (NUVU address): {property_label}\n"
        f"sales_pipeline.id: {pipeline_id}\n\n"
        "CURRENT MILESTONES IN DATABASE:\n"
        + "\n".join(milestone_lines)
        + "\n\n--- ALTO NOTES (newest first, --- separates notes) ---\n"
        + notes_plain
        + "\n\n---\n"
        "Respond using EXACTLY this structure (markdown), with the equals line 64 chars:\n"
        "================================================================\n"
        "PROPERTY: <full address line>\n"
        "PIPELINE ID: <uuid>\n"
        "CURRENT MILESTONES: (repeat non-null from input, or say 'none set')\n\n"
        "NOTES SUMMARY:\n"
        "- <bullet points>\n\n"
        "SUGGESTED MILESTONES:\n"
        "  <milestone_name>: LIKELY — <short reason>\n"
        "  <milestone_name>: UNCLEAR — <short reason>\n"
        "  (one line per milestone you considered; use LIKELY / UNCLEAR / NOT SUPPORTED)\n\n"
        "VERDICT: <one short paragraph>\n"
        "================================================================"
    )
    msg = ai_client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    parts: list[str] = []
    for block in msg.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "".join(parts).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "pdf_dir",
        type=Path,
        nargs="?",
        default=Path.home() / "Desktop" / "Alto-screens",
    )
    ap.add_argument(
        "--anthropic-model",
        default=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        help="Anthropic model id",
    )
    ap.add_argument(
        "--skip-claude",
        action="store_true",
        help="Skip API calls; write placeholder review sections",
    )
    args = ap.parse_args()
    pdf_dir = args.pdf_dir.expanduser().resolve()
    today_s = date.today().isoformat()
    import_tag = date.today().strftime("%d %b %Y")

    log_lines: list[str] = []

    def log(msg: str):
        print(msg)
        log_lines.append(msg)

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    log(f"STEP 1: Found {len(pdfs)} PDF file(s) in {pdf_dir}")

    parsed_ok: list[ParsedPdf] = []
    parse_fail: list[tuple[str, str]] = []
    for p in pdfs:
        try:
            text = extract_pdf_text(p)
        except Exception as e:
            parse_fail.append((str(p), str(e)))
            log(f"PARSE FAIL: {p.name} — {e}")
            continue
        addr = parse_address(text)
        if not addr:
            parse_fail.append((str(p), "no Address/Type block"))
            log(f"PARSE FAIL: {p.name} — no Address block")
            continue
        lines, full = addr
        notes = parse_notes_blob(text)
        parsed_ok.append(
            ParsedPdf(path=p, address_lines=lines, full_address=full, notes=notes)
        )

    log(f"Parsed successfully: {len(parsed_ok)}, failed: {len(parse_fail)}")

    client = supabase_for_backend()

    keyed: dict[str, list[ParsedPdf]] = defaultdict(list)
    pipeline_id_by_addr: dict[str, str] = {}
    unmatched: list[str] = []

    for pp in parsed_ok:
        key = street_match_key(pp.address_lines)
        pc = postcode_from_lines(pp.address_lines)
        pc_norm = normalise_address(pc).replace(" ", "") if pc else None
        rows = fetch_pipeline_ilike(client, key)
        if not rows:
            unmatched.append(pp.full_address)
            log(f"UNMATCHED (no pipeline): {pp.full_address} [file: {pp.path.name}]")
            continue
        best = pick_best_pipeline(rows, pp.address_lines, pc_norm)
        if not best:
            unmatched.append(pp.full_address)
            continue
        pipe_addr = (best.get("property_address") or "").strip()
        keyed[pipe_addr].append(pp)
        pipeline_id_by_addr.setdefault(pipe_addr, str(best.get("id") or ""))

    progression_by_pipe: dict[str, dict] = {}
    for pipe_addr in keyed:
        prog = fetch_progression_by_address(client, pipe_addr)
        if not prog:
            unmatched.append(pipe_addr)
            log(f"UNMATCHED (no sales_progression): {pipe_addr}")
            continue
        progression_by_pipe[pipe_addr] = prog

    log(f"Matched pipeline+progression: {len(progression_by_pipe)}")
    log(f"Unmatched count: {len(unmatched)}")

    merged_notes: dict[str, list[AltoNote]] = {}
    merged_pdfs: dict[str, list[Path]] = {}
    prog_id_to_pipe: dict[str, str] = {}

    for pipe_addr, pps in keyed.items():
        if pipe_addr not in progression_by_pipe:
            continue
        all_notes: list[AltoNote] = []
        for pp in pps:
            all_notes.extend(pp.notes)
        seen = set()
        deduped: list[AltoNote] = []
        for n in sorted(all_notes, key=lambda x: x.dt):
            sig = (n.dt.isoformat(), n.author, n.body)
            if sig in seen:
                continue
            seen.add(sig)
            deduped.append(n)
        deduped.sort(key=lambda x: x.dt, reverse=True)
        pid = str(progression_by_pipe[pipe_addr]["id"])
        merged_notes[pid] = deduped
        merged_pdfs[pid] = [pp.path for pp in pps]
        prog_id_to_pipe[pid] = pipe_addr

    anthropic_client = None
    if not args.skip_claude:
        key = _anthropic_api_key()
        if not key:
            log("ERROR: ANTHROPIC_API_KEY (or ANTHROPIC_KEY_FOR_RAILWAY) required unless --skip-claude")
            return 1
        try:
            import anthropic

            anthropic_client = anthropic.Anthropic(api_key=key)
        except ImportError:
            log("ERROR: pip install anthropic")
            return 1

    review_sections: list[str] = []
    review_sections.append(f"ALTO MILESTONE REVIEW — generated {today_s}")
    review_sections.append(f"Model: {args.anthropic_model}")
    review_sections.append("")

    sorted_pipes = sorted(progression_by_pipe.keys())
    for pipe_addr in sorted_pipes:
        prog = progression_by_pipe[pipe_addr]
        pid = str(prog["id"])
        pl_id = pipeline_id_by_addr.get(pipe_addr, "")
        notes = merged_notes.get(pid, [])
        pdf_names = ", ".join(p.name for p in merged_pdfs.get(pid, []))
        prop_label = (prog.get("property_address") or pipe_addr).strip()
        ms_lines = current_milestones_lines(prog)
        plain = notes_plain_for_claude(notes)

        log(f"Claude review: {prop_label} ({len(notes)} notes)")

        if args.skip_claude or anthropic_client is None:
            block = (
                "================================================================\n"
                f"PROPERTY: {prop_label}\n"
                f"PIPELINE ID: {pl_id}\n"
                "CURRENT MILESTONES:\n"
                + "\n".join(ms_lines)
                + "\n\nNOTES SUMMARY:\n"
                "- (Claude skipped — re-run without --skip-claude)\n\n"
                "SUGGESTED MILESTONES:\n"
                "  (not generated)\n\n"
                "VERDICT: Run with ANTHROPIC_API_KEY set.\n"
                "================================================================"
            )
        else:
            try:
                block = call_claude_milestone_review(
                    anthropic_client,
                    args.anthropic_model,
                    prop_label,
                    pl_id,
                    ms_lines,
                    plain,
                )
                time.sleep(0.35)
            except Exception as e:
                block = (
                    "================================================================\n"
                    f"PROPERTY: {prop_label}\n"
                    f"PIPELINE ID: {pl_id}\n"
                    f"ERROR calling Claude: {e}\n"
                    "================================================================"
                )
                log(f"  Claude error: {e}")

        review_sections.append(block)
        review_sections.append("")

    desktop = Path.home() / "Desktop"
    review_path = desktop / "alto_milestone_review.txt"
    try:
        review_path.write_text("\n".join(review_sections).strip() + "\n", encoding="utf-8")
        log(f"\nMilestone review saved to: {review_path}")
    except Exception as e:
        log(f"Could not write review file: {e}")
        return 1

    revert_parts: list[str] = [
        f"-- REVERT ALTO NOTES-ONLY IMPORT {today_s}",
        "-- Restores nuvu_notes only; milestones were not modified by this import.",
    ]

    notes_written = 0
    snap_nuvu: dict[str, str | None] = {}

    for pipe_addr in sorted_pipes:
        prog = progression_by_pipe[pipe_addr]
        pid = str(prog["id"])
        snap_nuvu[pid] = prog.get("nuvu_notes")
        notes = merged_notes.get(pid, [])
        pdf_names = ", ".join(p.name for p in merged_pdfs.get(pid, []))

        block = build_import_block(notes, import_tag)
        prev_notes = prog.get("nuvu_notes")
        prev_s = (prev_notes or "").strip()
        if prev_s:
            new_notes = block + "\n\n" + prev_s
        else:
            new_notes = block

        log(f"\nPROPERTY: {prog.get('property_address')}")
        log(f"  SOURCE PDF(S): {pdf_names}")
        log(f"  PIPELINE ID: {pipeline_id_by_addr.get(pipe_addr, '')}")
        log(f"  nuvu_notes BEFORE (first 100 chars): {(prev_notes or '')[:100]!r}")

        try:
            client.table("sales_progression").update({"nuvu_notes": new_notes}).eq(
                "id", pid
            ).execute()
        except Exception as e:
            log(f"  UPDATE FAILED: {e}")
            continue

        notes_written += 1
        log(f"  nuvu_notes: WRITTEN ({len(notes)} note(s), formatted block)")

        orig = snap_nuvu[pid]
        revert_parts.append(
            f"-- Property: {prog.get('property_address')} (progression {pid})\n"
            f"UPDATE sales_progression SET\n  nuvu_notes = {sql_value(orig)}\n"
            f"WHERE id = '{pid}';\n"
        )

    revert_path = desktop / "alto_import_revert.sql"
    log_path = desktop / f"alto_import_run_log_{today_s}.txt"
    revert_sql = "\n".join(revert_parts)
    try:
        revert_path.write_text(revert_sql, encoding="utf-8")
        log_path.write_text("\n".join(log_lines), encoding="utf-8")
        log(f"\nRevert SQL (notes only) saved to: {revert_path}")
        log(f"Full log saved to: {log_path}")
    except Exception as e:
        log(f"Could not write Desktop SQL/log: {e}")

    log("\n=== SUMMARY ===")
    log(f"Properties updated (nuvu_notes only): {notes_written}")
    log(f"Milestone review properties: {len(sorted_pipes)}")
    log("Milestone columns: not written (David reviews alto_milestone_review.txt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
