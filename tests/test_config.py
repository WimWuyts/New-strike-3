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


def test_rights_gate_blocks_page_faithful_reproduction(config):
    """Zolang de rechten niet bevestigd zijn, moet de poort dicht blijven."""
    assert config.rights["status"] == "original_only"
    assert config.rights["confirmed"] is False
    with pytest.raises(ProjectError):
        config.assert_may_reproduce_pages()


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
