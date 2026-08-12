#!/usr/bin/env python3
"""Verwerkt alle thema's van een boek in hervatbare batches.

Eén thema is de transactiegrootte. Een gefaald thema stopt de batch niet: de
rest wordt afgewerkt en aan het eind volgt een overzicht, zodat één kapot
thema geen dag werk blokkeert.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.project import (  # noqa: E402
    CONTENT_DIR,
    Config,
    ProjectError,
    State,
    relative,
)
from validate import validate_theme  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Valideer alle thema's van een boek.")
    parser.add_argument("--book", required=True)
    parser.add_argument(
        "--skip-missing",
        action="store_true",
        help="Thema's zonder content overslaan in plaats van als fout te tellen.",
    )
    args = parser.parse_args()

    config = Config.load()
    book = config.book(args.book)
    state = State()

    passed: list[str] = []
    failed: list[tuple[str, int]] = []
    missing: list[str] = []

    unavailable: list[str] = []

    for theme in book.themes:
        theme_id = theme["id"]

        # Een thema zonder aangeleverde bron telt niet als fout: het bestaat in
        # het boek, maar er valt niets te bouwen.
        if not theme.get("source_available", True):
            unavailable.append(theme_id)
            print(f"{theme_id}: geen bron aangeleverd, overgeslagen")
            continue

        if not (CONTENT_DIR / theme_id).exists():
            missing.append(theme_id)
            marker = "overgeslagen" if args.skip_missing else "GEEN CONTENT"
            print(f"{theme_id}: {marker}")
            continue

        report = validate_theme(theme_id, config)
        if report.ok:
            passed.append(theme_id)
            print(f"{theme_id}: OK")
        else:
            failed.append((theme_id, len(report.errors)))
            print(f"{theme_id}: {len(report.errors)} fouten")

        state.set_theme(
            theme_id,
            validation="passed" if report.ok else "failed",
            validation_errors=len(report.errors),
        )

    state.set_stage(
        f"batch:{book.id}",
        status="done" if not failed else "failed",
        passed=len(passed),
        failed=len(failed),
        missing=len(missing),
    )
    state.save()

    total = len(book.themes) - len(unavailable)
    print(f"\n{book.title}: {len(passed)}/{total} bouwbare thema's geldig")
    if failed:
        print("Gefaald: " + ", ".join(f"{theme} ({count})" for theme, count in failed))
    if missing:
        print("Zonder content: " + ", ".join(missing))
    if unavailable:
        print("Zonder bron: " + ", ".join(unavailable))
    print(f"Details: {relative(Path('reports') / 'validation.md')}")

    if failed:
        return 1
    if missing and not args.skip_missing:
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProjectError as exc:
        print(f"Fout: {exc}", file=sys.stderr)
        raise SystemExit(2)
