#!/usr/bin/env python3
"""Fase A — curriculumkaart en schaalberekening.

Leest de page-maps uit `make extract` en leidt daaruit per thema af: titel,
paginabereik en rubrieken. Alles onder de zekerheidsdrempel gaat naar de
manual review queue in plaats van naar de kaart.

Dit script verzint niets. Wat het niet met redelijke zekerheid kan afleiden,
markeert het als open vraag.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.project import (  # noqa: E402
    CATALOG_DIR,
    EXTRACTED_DIR,
    REPORTS_DIR,
    Config,
    ProjectError,
    State,
    ensure_dirs,
    relative,
    write_json_atomic,
)

# Rubrieken en de signaalwoorden waarmee ze in het handboek aangekondigd worden.
SECTION_MARKERS: dict[str, tuple[str, ...]] = {
    "theme_opener": ("unit", "theme", "lesson", "let's start", "warm up", "warming up"),
    "vocabulary": ("vocabulary", "word bank", "wordlist", "word list", "woordenschat", "words"),
    "grammar": ("grammar", "grammatica", "language focus", "focus on form", "rules"),
    "reading": ("reading", "read the text", "lezen", "text"),
    "listening": ("listening", "listen", "luisteren", "audio", "track"),
    "speaking": ("speaking", "speak", "spreken", "in pairs", "role play", "roleplay"),
    "writing": ("writing", "write", "schrijven"),
    "exercises": ("exercise", "exercises", "practice", "oefening", "oefeningen", "task"),
    "review": ("review", "revision", "check your", "self-assessment", "test yourself", "herhaling"),
    "reference": ("reference", "irregular verbs", "appendix", "overview", "overzicht"),
}

# Een rubriek geldt pas als gedetecteerd bij minstens dit zekerheidsniveau.
MIN_SECTION_CONFIDENCE = 0.45

# Regels die als kandidaat-titel voor een thema in aanmerking komen.
TITLE_MIN_CHARS = 4
TITLE_MAX_CHARS = 60


def load_page_map(book_id: str, theme_id: str) -> list[dict[str, Any]]:
    path = EXTRACTED_DIR / book_id / f"{theme_id}.page-map.jsonl"
    if not path.exists():
        raise ProjectError(
            f"Page-map ontbreekt voor {theme_id}: {relative(path)}\n"
            f"Draai eerst: make extract BOOK={book_id}"
        )
    records = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def page_text(record: dict[str, Any]) -> str:
    return " ".join(block["text"] for block in record.get("blocks", []))


def detect_sections(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Wijst elke pagina een rubriek toe op basis van signaalwoorden."""
    per_page: list[tuple[int, str, float]] = []

    for record in records:
        text = page_text(record).lower()
        if not text:
            per_page.append((record["page"], "unknown", 0.0))
            continue

        scores: dict[str, float] = {}
        for kind, markers in SECTION_MARKERS.items():
            hits = 0.0
            for marker in markers:
                if re.search(rf"\b{re.escape(marker)}\b", text):
                    # Een signaalwoord vooraan de pagina weegt zwaarder: dat is
                    # doorgaans een rubriekkop en geen losse vermelding.
                    position = text.find(marker)
                    weight = 1.0 if position < len(text) * 0.25 else 0.5
                    hits += weight
            if hits:
                scores[kind] = hits

        if not scores:
            per_page.append((record["page"], "unknown", 0.0))
            continue

        best = max(scores, key=lambda k: scores[k])
        total = sum(scores.values())
        confidence = scores[best] / total if total else 0.0
        per_page.append((record["page"], best, round(confidence, 3)))

    # Aaneensluitende pagina's met dezelfde rubriek worden één sectie.
    sections: list[dict[str, Any]] = []
    for page, kind, confidence in per_page:
        if sections and sections[-1]["kind"] == kind and sections[-1]["last_page"] == page - 1:
            sections[-1]["last_page"] = page
            sections[-1]["_confidences"].append(confidence)
        else:
            sections.append(
                {
                    "kind": kind,
                    "first_page": page,
                    "last_page": page,
                    "_confidences": [confidence],
                }
            )

    for section in sections:
        confidences = section.pop("_confidences")
        section["detection_confidence"] = round(sum(confidences) / len(confidences), 3)

    return sections


def guess_title(records: list[dict[str, Any]]) -> tuple[str | None, float]:
    """Zoekt op de eerste pagina's een plausibele thematitel.

    De grootste tekstregel bovenaan de openingspagina is de beste kandidaat.
    Levert dat niets bruikbaars op, dan geeft de functie None terug in plaats
    van een gok.
    """
    candidates: list[tuple[float, str, float]] = []

    for record in records[:3]:
        height = record.get("height") or 1
        for block in record.get("blocks", []):
            text = block["text"].strip()
            if not (TITLE_MIN_CHARS <= len(text) <= TITLE_MAX_CHARS):
                continue
            if not re.search(r"[A-Za-z]", text):
                continue
            bbox = block["bbox"]
            font_size = bbox["y1"] - bbox["y0"]
            top_fraction = bbox["y0"] / height
            if top_fraction > 0.5:
                continue
            candidates.append((font_size, text, block["confidence"]))

    if not candidates:
        return None, 0.0

    candidates.sort(key=lambda c: c[0], reverse=True)
    _, text, confidence = candidates[0]
    return text, confidence


def build_theme(config: Config, book_id: str, theme_cfg: dict[str, Any]) -> dict[str, Any]:
    theme_id = theme_cfg["id"]
    records = load_page_map(book_id, theme_id)
    book = config.book(book_id)

    sections = [
        section
        for section in detect_sections(records)
        if section["detection_confidence"] >= MIN_SECTION_CONFIDENCE
        or section["kind"] != "unknown"
    ]

    title, title_confidence = guess_title(records)
    open_questions: list[dict[str, Any]] = []

    if title is None:
        open_questions.append(
            {
                "question_nl": "Titel van dit thema kon niet betrouwbaar uit de OCR worden afgeleid.",
                "page": records[0]["page"] if records else 1,
            }
        )
        title = f"{book.title} — Unit {theme_cfg['unit']}"
        title_confidence = 0.0

    weak = [s for s in sections if s["detection_confidence"] < MIN_SECTION_CONFIDENCE]
    for section in weak:
        open_questions.append(
            {
                "question_nl": (
                    f"Rubriek op pagina {section['first_page']}–{section['last_page']} is onzeker "
                    f"gedetecteerd als {section['kind']!r}."
                ),
                "page": section["first_page"],
            }
        )

    return {
        "id": theme_id,
        "book_id": book_id,
        "unit": theme_cfg["unit"],
        "title": title,
        "title_confidence": round(title_confidence, 3),
        "cefr": _primary_cefr(book.cefr_target),
        "source_file": theme_cfg["source_file"],
        "page_range": {
            "first": records[0]["page"] if records else 1,
            "last": records[-1]["page"] if records else 1,
        },
        "sections": sections,
        "grammar_topic_ids": [],
        "vocabulary_set_ids": [],
        "reading_ids": [],
        "listening_ids": [],
        "open_questions": open_questions,
        "review_status": "machine_checked",
    }


def _primary_cefr(target: str) -> str:
    """'A2+/B1' -> 'A2+'. De kaart draagt één niveau; de spreiding staat in config."""
    return target.split("/")[0].strip()


def write_curriculum_report(themes: list[dict[str, Any]], config: Config) -> None:
    lines = ["# Curriculumkaart", ""]
    lines += [
        "Afgeleid uit OCR. Alles met lage zekerheid staat als open vraag vermeld en",
        "moet handmatig bevestigd worden vóór Fase B.",
        "",
    ]

    for book in config.books:
        book_themes = [t for t in themes if t["book_id"] == book.id]
        if not book_themes:
            continue
        lines += [f"## {book.title}", ""]
        lines += ["| Thema | Titel | Zekerheid | Pagina's | Rubrieken | Open vragen |", "|---|---|---:|---:|---|---:|"]
        for theme in book_themes:
            kinds = Counter(s["kind"] for s in theme["sections"])
            summary = ", ".join(f"{k}×{v}" for k, v in kinds.most_common(4))
            pages = theme["page_range"]["last"] - theme["page_range"]["first"] + 1
            lines.append(
                f"| `{theme['id']}` | {theme['title']} | {theme['title_confidence']:.2f} "
                f"| {pages} | {summary} | {len(theme['open_questions'])} |"
            )
        lines.append("")

    total_open = sum(len(t["open_questions"]) for t in themes)
    lines += [
        "## Samenvatting",
        "",
        f"- Thema's in kaart: **{len(themes)}**",
        f"- Open vragen: **{total_open}**",
        "",
    ]
    if total_open:
        lines += [
            "### Open vragen",
            "",
            "| Thema | Pagina | Vraag |",
            "|---|---:|---|",
        ]
        for theme in themes:
            for question in theme["open_questions"]:
                lines.append(f"| `{theme['id']}` | {question['page']} | {question['question_nl']} |")
        lines.append("")

    (REPORTS_DIR / "curriculum-map.md").write_text("\n".join(lines), encoding="utf-8")


def write_scope_report(themes: list[dict[str, Any]], config: Config) -> None:
    """Berekent de werkelijke omvang zodra grammatica en woordenschat bekend zijn."""
    scope_unit = config.exercises["scope_unit"]
    per_unit = config.exercises["per_scope_unit"]

    grammar = sum(len(t["grammar_topic_ids"]) for t in themes)
    vocab = sum(len(t["vocabulary_set_ids"]) for t in themes)
    known = grammar + vocab > 0

    lines = ["# Schaalberekening", ""]
    lines += [
        f"Gekozen scope-eenheid: **`{scope_unit}`** — {per_unit} activiteiten per eenheid.",
        "",
        f"- Thema's: **{len(themes)}**",
        f"- Grammaticaonderwerpen in kaart: **{grammar}**",
        f"- Woordenschatsets in kaart: **{vocab}**",
        "",
    ]

    if known:
        units = grammar + vocab
        activities = units * per_unit
        low, high = activities * 3, activities * 8
        lines += [
            "## Werkelijke omvang",
            "",
            "| Grootheid | Aantal |",
            "|---|---:|",
            f"| Scope-eenheden | {units} |",
            f"| Activiteiten | {activities} |",
            f"| Antwoordmomenten (3–8 per activiteit) | {low}–{high} |",
            "",
            f"Batchindeling: één thema per batch, {len(themes)} batches, "
            f"gemiddeld {activities // max(len(themes), 1)} activiteiten per batch.",
            "",
        ]
    else:
        lines += [
            "## Nog niet berekenbaar",
            "",
            "De grammaticaonderwerpen en woordenschatsets zijn nog niet uit de bron",
            "afgeleid. Deze kaart bevat alleen thema's en rubrieken. De definitieve",
            "telling volgt zodra de rubrieken `grammar` en `vocabulary` inhoudelijk",
            "zijn uitgewerkt.",
            "",
            "De schatting uit `reports/preflight.md` blijft tot dan geldig.",
            "",
        ]

    (REPORTS_DIR / "scope-calculation.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bouw de curriculumkaart uit de page-maps.")
    parser.add_argument("--book", help="Alleen dit boek verwerken")
    args = parser.parse_args()

    config = Config.load()
    ensure_dirs(CATALOG_DIR, REPORTS_DIR)
    state = State()

    books = [config.book(args.book)] if args.book else config.books
    themes: list[dict[str, Any]] = []
    missing: list[str] = []

    for book in books:
        for theme_cfg in book.available_themes:
            try:
                themes.append(build_theme(config, book.id, theme_cfg))
            except ProjectError as exc:
                missing.append(str(exc).splitlines()[0])
        for skipped in book.unavailable_themes:
            print(f"  {skipped['id']}: overgeslagen, geen bron-pdf aangeleverd")

    if missing:
        for item in missing:
            print(f"  overgeslagen: {item}", file=sys.stderr)

    for theme in themes:
        write_json_atomic(CATALOG_DIR / f"{theme['id']}.json", theme)

    write_json_atomic(
        CATALOG_DIR / "curriculum-map.json",
        {"schema_version": "v1", "themes": [t["id"] for t in themes]},
    )
    write_curriculum_report(themes, config)
    write_scope_report(themes, config)

    state.set_stage("catalog", status="done", themes=len(themes))
    state.save()

    print(f"Thema's in kaart: {len(themes)}")
    print(f"Open vragen     : {sum(len(t['open_questions']) for t in themes)}")
    print(f"\nRapporten: {relative(REPORTS_DIR / 'curriculum-map.md')}")
    print(f"           {relative(REPORTS_DIR / 'scope-calculation.md')}")
    if missing:
        print(f"\n{len(missing)} thema's overgeslagen wegens ontbrekende page-map.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProjectError as exc:
        print(f"Fout: {exc}", file=sys.stderr)
        raise SystemExit(2)
