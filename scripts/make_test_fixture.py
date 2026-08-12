#!/usr/bin/env python3
"""Genereert een synthetisch thema om de web- en PPTX-build te testen.

Dit is testmateriaal, geen leerinhoud. Het staat bewust niet in versiebeheer:
`data/` is genegeerd, en de fixture wordt opnieuw opgebouwd wanneer de
browsertests draaien.

De activiteiten komen uit de echte blueprintgenerator, zodat de tests draaien
op een reeks die aan alle quota voldoet.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from conftest import build_activity_set  # noqa: E402
from lib.project import Config, content_hash, ensure_dirs, write_json_atomic  # noqa: E402

THEME_ID = "ace3-u1"
BOOK_ID = "ace3"
TARGET_ID = f"{THEME_ID}-gr-test"

CONTENT_DIR = ROOT / "data" / "content" / THEME_ID
CATALOG_DIR = ROOT / "data" / "catalog"


def grammar_topic() -> dict:
    topic = {
        "id": TARGET_ID,
        "book_id": BOOK_ID,
        "theme_id": THEME_ID,
        "kind": "grammar_topic",
        "title": "Present perfect",
        "cefr": "A2+",
        "learning_objectives": [
            "Ik kan de present perfect gebruiken om over ervaringen te vertellen."
        ],
        "source_page_refs": [
            {"book_id": BOOK_ID, "source_file": "Digiboek - New Ace 3 UNIT 1.pdf", "page": 12}
        ],
        "provenance": "original_companion",
        "rights_status": "original_only",
        "review_status": "draft",
        "can_do_statements": [
            "Ik kan vertellen wat ik al gedaan heb zonder een tijdstip te noemen."
        ],
        "meaning_and_use": {
            "summary_nl": (
                "De present perfect verbindt het verleden met nu. Je noemt geen "
                "afgesloten tijdstip; het gaat om het resultaat of de ervaring."
            ),
            "use_cases": [
                {
                    "label_nl": "Ervaring",
                    "explanation_nl": "Iets dat ooit gebeurd is; wanneer doet er niet toe.",
                    "example_en": "I have visited Rome twice.",
                }
            ],
        },
        "form": {
            "affirmative": {
                "pattern": "SUBJECT + have/has + past participle",
                "examples": ["She has finished her homework."],
            }
        },
        "typical_errors_nl": [
            {
                "wrong": "I have seen him yesterday.",
                "right": "I saw him yesterday.",
                "why_nl": "Bij een afgesloten tijdstip gebruik je de past simple.",
            }
        ],
        "contrast_with": [
            {
                "other_topic": "past simple",
                "difference_nl": (
                    "De past simple noemt wel een afgesloten tijdstip, de present "
                    "perfect niet."
                ),
                "minimal_pair": ["I have lost my keys.", "I lost my keys on Monday."],
            }
        ],
        "examples": [
            {
                "sentence_en": f"Testvoorbeeld {index} met de doelvorm in context.",
                "context_nl": f"Context bij testvoorbeeld {index}.",
            }
            for index in range(1, 7)
        ],
        "recap": ["Noem twee situaties waarin je de present perfect gebruikt."],
        "exit_ticket": {
            "prompt_nl": "Schrijf één zin over iets dat je ooit gedaan hebt.",
            "expected_evidence_nl": "Correcte vorm van have/has plus voltooid deelwoord.",
        },
    }
    topic["content_hash"] = content_hash(topic)
    return topic


def main() -> int:
    config = Config.load()

    ensure_dirs(
        CATALOG_DIR,
        *(CONTENT_DIR / name for name in ("grammar", "vocabulary", "visuals", "activities")),
    )

    write_json_atomic(
        CATALOG_DIR / f"{THEME_ID}.json",
        {
            "id": THEME_ID,
            "book_id": BOOK_ID,
            "unit": 1,
            "title": "Testthema (fixture)",
            "cefr": "A2+",
        },
    )
    write_json_atomic(CONTENT_DIR / "grammar" / f"{TARGET_ID}.json", grammar_topic())

    activities = build_activity_set("grammar_topic", config)
    write_json_atomic(
        CONTENT_DIR / "activities" / f"{TARGET_ID}.json",
        {
            "target_id": TARGET_ID,
            "target_kind": "grammar_topic",
            "activities": activities,
        },
    )

    print(f"Testfixture klaar: {THEME_ID} met {len(activities)} activiteiten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
