#!/usr/bin/env python3
"""Berekent en schrijft `content_hash` in alle inhoudsbestanden.

De hash dient om te zien of een artefact nog overeenkomt met wat er gebouwd is.
Met de hand bijhouden is onbegonnen werk, en een verouderde hash blokkeert de
validatie, dus dit script zet ze na elke inhoudswijziging opnieuw.

Idempotent: een bestand waarvan de hash al klopt, wordt niet aangeraakt.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.project import (  # noqa: E402
    CONTENT_DIR,
    ROOT,
    content_hash,
    relative,
    write_json_atomic,
)

# Mappen met losse entiteiten die elk een eigen hash dragen.
ENTITY_DIRS = ("grammar", "vocabulary", "readings", "listenings", "visuals")


def stamp_entity(path: Path) -> bool:
    payload = json.loads(path.read_text(encoding="utf-8"))
    digest = content_hash(payload)
    if payload.get("content_hash") == digest:
        return False
    payload["content_hash"] = digest
    write_json_atomic(path, payload)
    return True


def stamp_activities(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    activities = payload.get("activities")
    if not isinstance(activities, list):
        return 0

    changed = 0
    for activity in activities:
        digest = content_hash(activity)
        if activity.get("content_hash") != digest:
            activity["content_hash"] = digest
            changed += 1

    if changed:
        write_json_atomic(path, payload)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Zet content_hash in alle inhoudsbestanden.")
    parser.add_argument("--theme", help="Alleen dit thema; standaard alle thema's")
    args = parser.parse_args()

    roots = (
        [CONTENT_DIR / args.theme]
        if args.theme
        else sorted(p for p in CONTENT_DIR.glob("*") if p.is_dir())
    )

    entities = 0
    activities = 0

    for theme_dir in roots:
        if not theme_dir.exists():
            print(f"Geen content in {relative(theme_dir)}", file=sys.stderr)
            return 1

        for name in ENTITY_DIRS:
            for path in sorted((theme_dir / name).glob("*.json")):
                if stamp_entity(path):
                    entities += 1
                    print(f"  gestempeld: {relative(path)}")

        for path in sorted((theme_dir / "activities").glob("*.json")):
            if path.name.endswith(".blueprint.json"):
                continue
            count = stamp_activities(path)
            if count:
                activities += count
                print(f"  gestempeld: {relative(path)} ({count} activiteiten)")

    print(f"\nEntiteiten bijgewerkt : {entities}")
    print(f"Activiteiten bijgewerkt: {activities}")
    if entities == 0 and activities == 0:
        print("Alles was al actueel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
