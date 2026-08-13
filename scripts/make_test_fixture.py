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

THEME_ID = "ace3-u2"
BOOK_ID = "ace3"
TARGET_ID = f"{THEME_ID}-gr-test"

CONTENT_DIR = ROOT / "data" / "content" / THEME_ID
CATALOG_DIR = ROOT / "data" / "catalog"

# Alle fixtures staan op ace3-u2: dat thema draagt geen echte inhoud, dus
# testmateriaal kan er nooit botsen met het pilootthema.
ANSWERS_DIR = ROOT / "data" / "answers"
ANSWERS_THEME_ID = "ace3-u2"


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


def answer_key() -> dict:
    """Een kleine, schemageldige sleutel om de correctiedeck-generator te testen."""
    return {
        "id": f"{ANSWERS_THEME_ID}-answers",
        "book_id": BOOK_ID,
        "theme_id": ANSWERS_THEME_ID,
        "title": "Testsleutel (fixture)",
        "provenance": "source_core",
        "rights_status": "licensed_confirmed",
        "use_scope": "own_lesson_groups",
        "teacher_only": True,
        "derivation": "manual_inventory",
        "derivation_note_nl": "Testmateriaal. Geen echte oplossingen uit het handboek.",
        "source_page_offset": 8,
        "exercises": [
            {
                "id": f"{ANSWERS_THEME_ID}-ex-01",
                "number": "1",
                "label_nl": "Testoefening met korte antwoorden",
                "page": 12,
                "section": "grammar",
                "instruction_nl": "Vul de juiste vorm in.",
                "items": [
                    {"number": str(index), "answer": f"testantwoord {index}"}
                    for index in range(1, 6)
                ],
            },
            {
                "id": f"{ANSWERS_THEME_ID}-ex-02",
                "number": "2",
                "label_nl": "Testoefening met varianten en een onzeker item",
                "page": 13,
                "section": "vocabulary",
                "items": [
                    {
                        "number": "1",
                        "answer": "doesn't have",
                        "alternatives": ["hasn't got"],
                        "note_nl": "Beide vormen zijn correct.",
                    },
                    {"number": "2", "answer": "onzeker gelezen", "uncertain": True},
                    {"number": "3", "answer": "derde antwoord"},
                ],
            },
            {
                "id": f"{ANSWERS_THEME_ID}-ex-03",
                "number": "3",
                "label_nl": "Open schrijfopdracht",
                "page": 14,
                "section": "writing",
                "open_ended": True,
                "note_nl": "Geen vast antwoord. Beoordeel op structuur, aanspreking en afsluiting.",
                "items": [{"number": "1", "answer": "Zie de beoordelingscriteria."}],
            },
        ],
    }


def main() -> int:
    config = Config.load()

    ensure_dirs(
        CATALOG_DIR,
        *(CONTENT_DIR / name for name in ("grammar", "vocabulary", "visuals", "activities")),
    )

    # De curriculumkaart kan brongegeven zijn: waar ze uit een handmatige
    # inventaris komt, is ze niet opnieuw te genereren. Nooit overschrijven.
    catalog_path = CATALOG_DIR / f"{THEME_ID}.json"
    if catalog_path.exists():
        print(f"Curriculumkaart {THEME_ID} bestaat al — ongemoeid gelaten.")
    else:
        write_json_atomic(
            catalog_path,
            {
                "id": THEME_ID,
                "book_id": BOOK_ID,
                "unit": 2,
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

    ensure_dirs(ANSWERS_DIR)
    key = answer_key()
    key["content_hash"] = content_hash(key)
    write_json_atomic(ANSWERS_DIR / f"{ANSWERS_THEME_ID}.json", key)

    print(f"Testfixture klaar: {THEME_ID} met {len(activities)} activiteiten")
    print(f"Testsleutel klaar: {ANSWERS_THEME_ID} met {len(key['exercises'])} oefeningen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
