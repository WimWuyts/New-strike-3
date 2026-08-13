"""Vastgelegde curriculumkaarten moeten geldig blijven.

De kaarten in data/catalog/ zijn brongegeven zodra ze uit een handmatige
inventaris komen: ze zijn dan niet opnieuw te genereren. Deze tests bewaken dat
ze schemageldig blijven en intern consistent zijn met config/project.yaml.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from lib.project import CATALOG_DIR, ROOT
from lib.validation import validate_schema

def _is_tracked(path: Path) -> bool:
    """Alleen vastgelegde kaarten toetsen, niet wat een fixture genereert."""
    result = subprocess.run(
        ["git", "check-ignore", "-q", str(path)],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    return result.returncode != 0


CATALOG_FILES = sorted(
    path
    for path in CATALOG_DIR.glob("*.json")
    if path.name != "curriculum-map.json" and _is_tracked(path)
)


def _ids(path: Path) -> str:
    return path.stem


if not CATALOG_FILES:
    pytest.skip("Nog geen curriculumkaarten vastgelegd.", allow_module_level=True)


@pytest.mark.parametrize("path", CATALOG_FILES, ids=_ids)
def test_catalog_entry_matches_the_schema(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    report = validate_schema(payload, "theme.json", path.name)
    assert report.ok, [str(f) for f in report.errors]


@pytest.mark.parametrize("path", CATALOG_FILES, ids=_ids)
def test_catalog_entry_is_known_in_the_config(path: Path, config):
    payload = json.loads(path.read_text(encoding="utf-8"))
    book = config.book_for_theme(payload["id"])

    assert payload["book_id"] == book.id
    assert payload["id"] == path.stem

    theme = book.theme(payload["id"])
    assert payload["unit"] == theme["unit"]
    assert payload["source_file"] == theme["source_file"]


@pytest.mark.parametrize("path", CATALOG_FILES, ids=_ids)
def test_sections_are_ordered_and_do_not_overlap(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    sections = payload["sections"]

    for section in sections:
        assert section["first_page"] <= section["last_page"], (
            f"Sectie {section.get('label')} loopt achterstevoren."
        )

    for earlier, later in zip(sections, sections[1:]):
        assert earlier["last_page"] < later["first_page"], (
            f"Secties overlappen: {earlier.get('label')} en {later.get('label')}"
        )


@pytest.mark.parametrize("path", CATALOG_FILES, ids=_ids)
def test_sections_stay_within_the_page_range(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    first, last = payload["page_range"]["first"], payload["page_range"]["last"]

    for section in payload["sections"]:
        assert first <= section["first_page"] <= last
        assert first <= section["last_page"] <= last


@pytest.mark.parametrize("path", CATALOG_FILES, ids=_ids)
def test_scope_unit_ids_follow_the_naming_convention(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    theme_id = payload["id"]

    for topic_id in payload["grammar_topic_ids"]:
        assert topic_id.startswith(f"{theme_id}-gr-"), topic_id
    for set_id in payload["vocabulary_set_ids"]:
        assert set_id.startswith(f"{theme_id}-vocab-"), set_id

    all_ids = payload["grammar_topic_ids"] + payload["vocabulary_set_ids"]
    assert len(all_ids) == len(set(all_ids)), "Dubbele scope-eenheid-ID's."


@pytest.mark.parametrize("path", CATALOG_FILES, ids=_ids)
def test_a_hand_made_map_declares_its_origin(path: Path):
    """Een kaart die niet uit de OCR komt, moet dat zeggen."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    derivation = payload.get("derivation")
    assert derivation in {"ocr_pipeline", "manual_inventory"}, (
        "Elke kaart moet vermelden hoe ze tot stand kwam."
    )
    if derivation == "manual_inventory":
        assert payload.get("derivation_note_nl"), (
            "Een handmatige kaart moet toelichten waar de gegevens vandaan komen."
        )


@pytest.mark.parametrize("path", CATALOG_FILES, ids=_ids)
def test_open_questions_point_at_pages_in_the_unit(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    first, last = payload["page_range"]["first"], payload["page_range"]["last"]

    for question in payload.get("open_questions", []):
        assert first <= question["page"] <= last, (
            f"Open vraag verwijst naar blz. {question['page']}, buiten {first}-{last}."
        )


def test_review_queue_mentions_every_open_question():
    """Elke open vraag uit een kaart moet in de reviewwachtrij terugkomen."""
    queue_path = ROOT / "reports" / "manual-review-queue.md"
    if not queue_path.exists():
        pytest.skip("Nog geen reviewwachtrij.")

    queue = queue_path.read_text(encoding="utf-8")
    for path in CATALOG_FILES:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("open_questions"):
            assert payload["id"] in queue or payload["title"] in queue, (
                f"{payload['id']} heeft open vragen maar staat niet in de wachtrij."
            )
