"""De testfixture mag nooit brongegevens overschrijven.

Deze test bestaat omdat het één keer misging: de fixture schreef een stub over
de handmatig samengestelde curriculumkaart van ace3-u1 heen. Die kaart is niet
opnieuw te genereren — ze komt uit een inventaris, niet uit de OCR — dus dat
was echt gegevensverlies.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from lib.project import ROOT

FIXTURE_SCRIPT = ROOT / "scripts" / "make_test_fixture.py"
CATALOG_PATH = ROOT / "data" / "catalog" / "ace3-u1.json"


def _run_fixture() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(FIXTURE_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.skipif(not CATALOG_PATH.exists(), reason="Nog geen curriculumkaart vastgelegd.")
def test_fixture_leaves_an_existing_catalog_entry_untouched():
    before = CATALOG_PATH.read_text(encoding="utf-8")

    result = _run_fixture()
    assert result.returncode == 0, result.stderr

    after = CATALOG_PATH.read_text(encoding="utf-8")
    assert after == before, (
        "De fixture heeft de curriculumkaart gewijzigd. Die is brongegeven en "
        "mag niet overschreven worden."
    )


@pytest.mark.skipif(not CATALOG_PATH.exists(), reason="Nog geen curriculumkaart vastgelegd.")
def test_the_real_map_still_carries_its_content_after_a_fixture_run():
    _run_fixture()
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    assert payload["derivation"] == "manual_inventory"
    assert payload["sections"], "De rubrieken zijn verdwenen."
    assert payload["grammar_topic_ids"], "De grammaticaonderwerpen zijn verdwenen."
    assert payload["vocabulary_set_ids"], "De woordenschatsets zijn verdwenen."


def test_fixture_writes_its_answer_key_to_a_separate_theme():
    """De sleutel-fixture mag niet op het pilootthema landen."""
    source = FIXTURE_SCRIPT.read_text(encoding="utf-8")
    assert 'THEME_ID = "ace3-u2"' in source
    assert 'ANSWERS_THEME_ID = "ace3-u2"' in source


def test_fixture_artifacts_are_gitignored():
    """Testmateriaal mag niet per ongeluk als echte inhoud gecommit worden."""
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for path in (
        "data/content/ace3-u2/",
        "data/catalog/ace3-u2.json",
        "data/answers/ace3-u2.json",
    ):
        assert path in ignored, f"{path} staat niet in .gitignore"
