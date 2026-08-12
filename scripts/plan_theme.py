#!/usr/bin/env python3
"""Bereidt één thema voor op contentproductie.

Maakt de contentmappen aan en schrijft een werkorder: welke scope-eenheden er
zijn, en voor elke eenheid een blueprint van 25 activiteiten dat per
constructie aan alle quota voldoet.

Dit script schrijft géén leerinhoud. Het legt de structuur vast waarbinnen de
inhoud geschreven wordt, zodat quotafouten niet pas bij validatie opduiken.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import blueprint as blueprint_lib  # noqa: E402
from lib.project import (  # noqa: E402
    CATALOG_DIR,
    CONTENT_DIR,
    Config,
    ProjectError,
    State,
    ensure_dirs,
    read_json,
    relative,
    write_json_atomic,
)

SUBDIRS = ("vocabulary", "grammar", "readings", "listenings", "visuals", "activities")


def scaffold(theme_id: str) -> Path:
    theme_dir = CONTENT_DIR / theme_id
    ensure_dirs(*(theme_dir / name for name in SUBDIRS))
    return theme_dir


def collect_targets(theme_dir: Path, theme: dict[str, Any] | None) -> list[tuple[str, str]]:
    """Vindt de scope-eenheden: bestaande contentbestanden, anders de kaart."""
    targets: list[tuple[str, str]] = []

    for path in sorted((theme_dir / "grammar").glob("*.json")):
        targets.append((path.stem, "grammar_topic"))
    for path in sorted((theme_dir / "vocabulary").glob("*.json")):
        targets.append((path.stem, "vocabulary_set"))

    if targets or theme is None:
        return targets

    for topic_id in theme.get("grammar_topic_ids", []):
        targets.append((topic_id, "grammar_topic"))
    for set_id in theme.get("vocabulary_set_ids", []):
        targets.append((set_id, "vocabulary_set"))
    return targets


def write_work_order(
    theme_id: str,
    theme: dict[str, Any] | None,
    targets: list[tuple[str, str]],
    config: Config,
    theme_dir: Path,
) -> Path:
    per_unit = config.exercises["per_scope_unit"]
    modules = config.modules
    book = config.book_for_theme(theme_id)

    lines = [
        f"# Werkorder — {theme_id}",
        "",
        f"Boek: **{book.title}** — doelgroep {book.audience}, richtniveau {book.cefr_target}",
        "",
    ]

    if theme:
        lines += [
            f"Thema uit de kaart: **{theme['title']}** "
            f"(pagina's {theme['page_range']['first']}–{theme['page_range']['last']})",
            "",
        ]
        if theme.get("open_questions"):
            lines += [
                "> ⚠️ Dit thema heeft nog open vragen in de curriculumkaart. "
                "Los die eerst op.",
                "",
            ]

    lines += [
        "## Te schrijven",
        "",
        f"- {modules['readings_per_theme']} readings "
        f"({' + '.join(modules['variants'])}), volledig origineel",
        f"- {modules['listenings_per_theme']} listenings "
        f"({' + '.join(modules['variants'])}), met transcript en SSML",
        f"- {len(targets)} scope-eenheden × {per_unit} activiteiten "
        f"= **{len(targets) * per_unit} activiteiten**",
        "",
    ]

    if not targets:
        lines += [
            "## ⛔ Geen scope-eenheden bekend",
            "",
            "Er zijn nog geen grammaticaonderwerpen of woordenschatsets voor dit",
            "thema. Werk eerst de rubrieken `grammar` en `vocabulary` uit de",
            "curriculumkaart inhoudelijk uit, en draai dit script opnieuw.",
            "",
        ]
        path = theme_dir / "WORK-ORDER.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    lines += ["## Blueprints", ""]

    for target_id, target_kind in targets:
        quotas = config.exercises["quotas"][target_kind]
        slots = blueprint_lib.build(target_kind, quotas, total=per_unit)

        payload = {
            "target_id": target_id,
            "target_kind": target_kind,
            "generated_by": "scripts/plan_theme.py",
            "note_nl": (
                "Blueprint, geen leerinhoud. Vul per slot instructies, stimulus, "
                "prompts, antwoorden en feedback in. Wijzig interaction_type alleen "
                "als het blueprint daarna opnieuw gecontroleerd wordt."
            ),
            "slots": [slot.to_json(target_id, target_kind) for slot in slots],
        }
        blueprint_path = theme_dir / "activities" / f"{target_id}.blueprint.json"
        write_json_atomic(blueprint_path, payload)

        lines += [
            f"### `{target_id}` — {target_kind}",
            "",
            f"Blueprint: `{relative(blueprint_path)}`",
            "",
            "| # | Stage | Moeilijkheid | Interactiepatroon | Verwachte antwoordvorm |",
            "|---:|---:|---|---|---|",
        ]
        for slot in slots:
            pattern = blueprint_lib.interactions.get(slot.interaction_type)
            lines.append(
                f"| {slot.sequence} | {slot.stage} | {slot.difficulty} "
                f"| {pattern.label_nl} (`{slot.interaction_type}`) "
                f"| `{pattern.primary_response_mode}` |"
            )
        lines.append("")

    path = theme_dir / "WORK-ORDER.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Bereid een thema voor op contentproductie.")
    parser.add_argument("--theme", required=True)
    args = parser.parse_args()

    config = Config.load()
    config.book_for_theme(args.theme)  # valideert het thema
    state = State()

    theme = read_json(CATALOG_DIR / f"{args.theme}.json")
    if theme is None:
        print(
            f"Waarschuwing: geen curriculumkaart voor {args.theme}. "
            f"Draai eerst `make catalog`.",
            file=sys.stderr,
        )

    theme_dir = scaffold(args.theme)
    targets = collect_targets(theme_dir, theme)
    path = write_work_order(args.theme, theme, targets, config, theme_dir)

    per_unit = config.exercises["per_scope_unit"]
    state.set_theme(
        args.theme,
        scope_units=len(targets),
        planned_activities=len(targets) * per_unit,
        work_order=relative(path),
    )
    state.save()

    print(f"Thema voorbereid : {args.theme}")
    print(f"Scope-eenheden   : {len(targets)}")
    print(f"Geplande activiteiten: {len(targets) * per_unit}")
    print(f"\nWerkorder: {relative(path)}")
    if not targets:
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ProjectError, blueprint_lib.BlueprintError) as exc:
        print(f"Fout: {exc}", file=sys.stderr)
        raise SystemExit(2)
