"""Testhulpmiddelen: bouwt synthetische maar schemageldige content.

De fixtures hier bevatten bewust geen echte leerinhoud. Ze bestaan om de
validator en de blueprintgenerator te testen, niet om les mee te geven.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib import blueprint as blueprint_lib  # noqa: E402
from lib import interactions  # noqa: E402
from lib.project import Config, content_hash  # noqa: E402

CHOICE_MODES = {
    "multiple_choice",
    "select_multiple",
    "matching",
    "ordering",
    "drag_to_zone",
    "click_to_mark",
}


@pytest.fixture(scope="session")
def config() -> Config:
    return Config.load()


def make_prompt(sequence: int, index: int, mode: str) -> dict[str, Any]:
    """Bouwt één antwoordmoment dat aan het schema voldoet."""
    tag = f"a{sequence:02d}p{index}"
    prompt: dict[str, Any] = {
        "id": f"prompt-{tag}",
        "prompt": f"Vraag {index} van activiteit {sequence} over de doelvorm.",
        "response_mode": mode,
    }

    if mode == "typed_paragraph":
        prompt["manual_review_rubric"] = {
            "criteria": [
                {
                    "label": "Correctheid",
                    "descriptor": "De doelvorm wordt correct gespeld en vervoegd.",
                    "weight": 0.6,
                },
                {
                    "label": "Inhoud",
                    "descriptor": "De inhoud beantwoordt de opdracht volledig.",
                    "weight": 0.4,
                },
            ],
            "model_response": f"Modelantwoord voor activiteit {sequence}, vraag {index}.",
        }
        return prompt

    answer = f"answer-{tag}"
    prompt["canonical_answers"] = [answer]
    prompt["normalization_rules"] = ["trim", "collapse_whitespace"]
    prompt["hints"] = [
        f"Kijk naar het onderwerp van zin {index}.",
        f"Let op de tijd die in activiteit {sequence} centraal staat.",
    ]
    prompt["error_feedback"] = [
        {
            "matches": f"wrong-{tag}",
            "match_kind": "exact",
            "feedback": "Dat is de verkeerde vorm. Kijk opnieuw naar het onderwerp.",
        }
    ]

    if mode == "ordering":
        # Bij ordenen is het antwoord de volgorde van alle tegels samen.
        tiles = [f"tile-a-{tag}", f"tile-b-{tag}", f"tile-c-{tag}"]
        prompt["options"] = tiles
        prompt["canonical_answers"] = [" ".join(tiles)]
    elif mode in CHOICE_MODES:
        prompt["options"] = [answer, f"distractor-a-{tag}", f"distractor-b-{tag}"]

    return prompt


def make_activity(slot: blueprint_lib.Slot, theme_id: str, book_id: str) -> dict[str, Any]:
    pattern = interactions.get(slot.interaction_type)
    mode = pattern.primary_response_mode
    prompts = [make_prompt(slot.sequence, i, mode) for i in range(1, 4)]

    activity: dict[str, Any] = {
        "id": f"{theme_id}-gr-test-act-{slot.sequence:02d}",
        "book_id": book_id,
        "theme_id": theme_id,
        "kind": "exercise_activity",
        "title": f"Activiteit {slot.sequence}: {pattern.label_nl}",
        "cefr": "A2",
        "learning_objectives": [
            f"Ik kan de doelvorm herkennen en toepassen in activiteit {slot.sequence}."
        ],
        "source_page_refs": [],
        "provenance": "original_companion",
        "rights_status": "original_only",
        "review_status": "draft",
        "target_id": f"{theme_id}-gr-test",
        "target_kind": slot.target_kind if hasattr(slot, "target_kind") else "grammar_topic",
        "sequence": slot.sequence,
        "stage": slot.stage,
        "difficulty": slot.difficulty,
        "interaction_type": slot.interaction_type,
        "instructions": (
            f"Lees de zinnen en werk activiteit {slot.sequence} af volgens het voorbeeld."
        ),
        "stimulus": {
            "type": "text",
            "content": (
                f"Stimulus voor activiteit {slot.sequence}. "
                f"Deze tekst bevat de informatie die nodig is om de vragen te beantwoorden."
            ),
        },
        "prompts": prompts,
    }
    activity["content_hash"] = content_hash(activity)
    return activity


def build_activity_set(
    target_kind: str, config: Config, theme_id: str = "ace3-u2", book_id: str = "ace3"
) -> list[dict[str, Any]]:
    """Genereert een volledige, quotaconforme reeks van 25 activiteiten."""
    quotas = config.exercises["quotas"][target_kind]
    slots = blueprint_lib.build(target_kind, quotas, total=config.exercises["per_scope_unit"])

    activities = []
    for slot in slots:
        activity = make_activity(slot, theme_id, book_id)
        activity["target_kind"] = target_kind
        activity["content_hash"] = content_hash(activity)
        activities.append(activity)
    return activities
