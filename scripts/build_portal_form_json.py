#!/usr/bin/env python3
"""Write data/forms/ta6.json and data/forms/ta10.json from seed modules."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ta10_seed_data import TA10_SECTIONS, TA10_SELECT_OPTIONS
from scripts.ta6_seed_data import TA6_NUMERIC, TA6_PREAMBLE


def _ai_prompt_for_ta6(ref: str, text: str) -> str:
    return (
        f"You are helping a property seller with Law Society TA6 question {ref}. "
        "Explain the question in plain English. If they are unsure, suggest checking title deeds, "
        "lease, EPC, or asking their solicitor. When they have enough detail, summarise and ask to confirm saving."
    )


def _ai_prompt_for_ta10(item: str) -> str:
    return (
        f"Help the seller decide the status of “{item}” for the TA10 fittings form: "
        "included, excluded, none, or not applicable — and whether a price applies. "
        "Keep language simple. Summarise and ask to confirm before saving."
    )


def build_ta6():
    sections = []

    pre_questions = []
    for key, text in TA6_PREAMBLE:
        pre_questions.append(
            {
                "key": key,
                "text": text,
                "type": "textarea",
                "required": True,
                "help": "Answer as on the paper TA6. Your solicitor can help with wording.",
                "ai_prompt": _ai_prompt_for_ta6("intro", text),
            }
        )
    sections.append(
        {
            "key": "seller_and_parties",
            "title": "Seller, property and solicitor",
            "description": "Details at the start of the TA6 (Edition 5) form.",
            "questions": pre_questions,
        }
    )

    part1a = []
    part1b = []
    part1c = []
    part2 = []

    def bucket(ref: str):
        head = ref.split(".")[0]
        n = int(head) if head.isdigit() else 0
        if n in (1, 2, 3):
            return part1a
        if 4 <= n <= 6:
            return part1b
        if 7 <= n <= 14:
            return part1c
        return part2

    for ref, key, text in TA6_NUMERIC:
        q = {
            "key": key,
            "text": f"({ref}) {text}",
            "type": "textarea",
            "required": False,
            "help": "Refer to your TA6 paper form for tick-boxes and sub-parts; describe your position in full.",
            "ai_prompt": _ai_prompt_for_ta6(ref, text),
        }
        bucket(ref).append(q)

    sections.append(
        {
            "key": "part1a_material_information",
            "title": "Part 1 — Section A: Material information (Council tax, price, tenure)",
            "description": "TA6 Part 1, Part A — material information for marketing and conveyancing.",
            "questions": part1a,
        }
    )
    sections.append(
        {
            "key": "part1b_material_information",
            "title": "Part 1 — Section B: Physical characteristics, utilities, parking",
            "description": "TA6 Part 1, Part B.",
            "questions": part1b,
        }
    )
    sections.append(
        {
            "key": "part1c_material_information",
            "title": "Part 1 — Section C: Safety, restrictions, rights, flooding, notices, accessibility, mining",
            "description": "TA6 Part 1, Part C.",
            "questions": part1c,
        }
    )
    sections.append(
        {
            "key": "part2_supplementary",
            "title": "Part 2 — Supplementary information for conveyancing",
            "description": "TA6 Part 2 (boundaries through additional information).",
            "questions": part2,
        }
    )

    return {
        "form_type": "ta6",
        "title": "Property Information Form (TA6)",
        "version": "Edition 5 (2024)",
        "sections": sections,
    }


def build_ta10():
    sections = []
    for sec in TA10_SECTIONS:
        questions = []
        for item in sec["items"]:
            slug = item.lower().replace("/", " ").replace(" ", "_")
            slug = "".join(c for c in slug if c.isalnum() or c == "_").strip("_")
            key = f"{sec['key']}__{slug}"[:120]
            questions.append(
                {
                    "key": key,
                    "text": f"{item} — what is the position for this sale?",
                    "type": "select",
                    "required": False,
                    "options": TA10_SELECT_OPTIONS,
                    "help": "Match the TA10 columns: included, excluded, none, or not applicable. Add price in your reply if selling separately.",
                    "ai_prompt": _ai_prompt_for_ta10(item),
                }
            )
        sections.append(
            {
                "key": sec["key"],
                "title": sec["title"],
                "description": sec["description"],
                "questions": questions,
            }
        )
    return {
        "form_type": "ta10",
        "title": "Fittings and Contents Form (TA10)",
        "version": "Edition 2",
        "sections": sections,
    }


def main():
    out_dir = ROOT / "data" / "forms"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in (("ta6.json", build_ta6()), ("ta10.json", build_ta10())):
        path = out_dir / name
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Wrote", path, "questions", sum(len(s["questions"]) for s in data["sections"]))


if __name__ == "__main__":
    main()
