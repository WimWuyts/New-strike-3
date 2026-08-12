"""De configuratie moet de boekstructuur correct beschrijven."""

from __future__ import annotations

import pytest

from lib.project import ProjectError


def test_both_books_are_configured(config):
    assert {book.id for book in config.books} == {"ace3", "strike3"}


def test_theme_count_matches_unit_count(config):
    for book in config.books:
        assert len(book.themes) == book.unit_count, (
            f"{book.id} heeft {len(book.themes)} thema's maar unit_count {book.unit_count}"
        )


def test_theme_ids_follow_the_naming_convention(config):
    for book in config.books:
        for theme in book.themes:
            assert theme["id"] == f"{book.id}-u{theme['unit']}"


def test_strike3_has_eight_units(config):
    """Unit 8 bestaat in het boek, ook al is de pdf niet aangeleverd."""
    strike3 = config.book("strike3")
    assert strike3.unit_count == 8
    assert "strike3-u8" in strike3.theme_ids()


def test_unsupplied_theme_is_excluded_from_available(config):
    strike3 = config.book("strike3")
    available = {theme["id"] for theme in strike3.available_themes}
    unavailable = {theme["id"] for theme in strike3.unavailable_themes}

    assert "strike3-u8" in unavailable
    assert "strike3-u8" not in available
    assert available | unavailable == set(strike3.theme_ids())


def test_themes_without_the_flag_count_as_available(config):
    """Alleen een expliciete false sluit een thema uit."""
    ace3 = config.book("ace3")
    assert len(ace3.available_themes) == len(ace3.themes)
    assert ace3.unavailable_themes == []


def test_book_for_theme_resolves_both_books(config):
    assert config.book_for_theme("ace3-u1").id == "ace3"
    assert config.book_for_theme("strike3-u8").id == "strike3"


def test_unknown_theme_raises(config):
    with pytest.raises(ProjectError):
        config.book_for_theme("ace3-u99")


def test_answer_key_gate_is_open_and_scoped(config):
    """De bevestiging voor antwoordsleutels geldt, en draagt een gebruiksbereik."""
    assert config.rights["allow_source_answer_keys"] is True
    assert config.rights["answer_keys_teacher_only"] is True
    assert config.assert_may_use_source_answer_keys() == "own_lesson_groups"


def test_answer_key_confirmation_does_not_unlock_page_reproduction(config):
    """De kern van de poort: twee toestemmingen die niet meebewegen.

    Antwoordsleutels mogen, maar dat mag paginagetrouwe reproductie niet
    stilzwijgend vrijgeven, ook al staat rights.confirmed op true.
    """
    assert config.rights["confirmed"] is True
    assert config.rights["allow_page_faithful_reproduction"] is False

    with pytest.raises(ProjectError, match="Paginagetrouwe reproductie"):
        config.assert_may_reproduce_pages()


def test_source_image_reuse_stays_blocked(config):
    assert config.rights["allow_source_image_reuse"] is False
    assert config.rights["allow_raster_slide_backgrounds"] is False


def test_rights_confirmation_file_exists(config):
    """De poort controleert het bestaan van dit bestand, dus het moet er zijn."""
    from lib.project import ROOT

    assert (ROOT / config.rights["confirmation_file"]).exists()


def test_gate_closes_when_the_flag_is_withdrawn(config):
    """Herroepen moet werken zonder dat er elders iets aangepast wordt."""
    withdrawn = dict(config.rights)
    withdrawn["allow_source_answer_keys"] = False

    class _Stub(type(config)):
        @property
        def rights(self):
            return withdrawn

    stub = _Stub({"rights": withdrawn})
    with pytest.raises(ProjectError, match="antwoordsleutels"):
        stub.assert_may_use_source_answer_keys()


def test_scope_unit_is_topic_scope(config):
    assert config.exercises["scope_unit"] == "topic_scope"
    assert config.exercises["per_scope_unit"] == 25


def test_english_variant_is_confirmed_british(config):
    project = config["project"]
    assert project["english_variant"] == "en-GB"
    assert project["english_variant_confirmed"] is True


def test_pilot_is_confirmed_and_has_no_fallback(config):
    pilot = config["pilot"]
    assert pilot["theme_id"] == "ace3-u1"
    assert pilot["confirmed"] is True
    assert "fallback_theme_id" not in pilot
