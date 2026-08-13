#!/usr/bin/env python3
"""Zet een geschreven reeks activiteiten om in een schemageldig bestand.

De specialisten schrijven de didactische inhoud: leerdoel, instructie,
stimulus, vragen, hints en feedback. Alles wat administratie is — ID's,
boek- en themaverwijzingen, rechtenvelden, hashes — hoort niet in hun handen:
dat is werk dat exact moet kloppen en nooit mag afwijken. Dit script vult dat
in en controleert daarna meteen of de reeks door de poort komt.

    python scripts/assemble_activities.py \\
        --input reports/drafts/present-simple.json \\
        --target ace3-u1-gr-present-simple-and-continuous \\
        --kind grammar_topic

Idempotent: dezelfde invoer levert hetzelfde bestand met dezelfde hashes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.project import (  # noqa: E402
    CONTENT_DIR,
    Config,
    ProjectError,
    content_hash,
    ensure_dirs,
    relative,
    write_json_atomic,
)
from lib.validation import validate_activity_set, validate_schema  # noqa: E402

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _theme_of(target_id: str) -> str:
    """`ace3-u1-gr-present-simple` → `ace3-u1`."""
    parts = target_id.split("-")
    if len(parts) < 3:
        raise ProjectError(f"Kan geen thema afleiden uit {target_id!r}.")
    return "-".join(parts[:2])


def _prompt_id(index: int) -> str:
    """Prompt-ID's zijn positioneel.

    Wat een schrijver aanlevert draagt vaak een half onthouden doelnaam mee;
    die zou hier gaan afwijken van het echte ID zonder dat iets dat merkt.
    """
    return f"p{index}"


def assemble(
    written: list[dict[str, Any]],
    target_id: str,
    target_kind: str,
    config: Config,
    topic: dict[str, Any],
) -> list[dict[str, Any]]:
    theme_id = _theme_of(target_id)
    book_id = theme_id.split("-")[0]

    # Niveau en bronverwijzingen komen van het onderwerp zelf. Het boek noemt
    # een bereik ("A2+/B1"); een activiteit oefent één onderwerp op één niveau.
    cefr = topic["cefr"]
    source_page_refs = topic.get("source_page_refs", [])

    expected = config.exercises["per_scope_unit"]
    if len(written) != expected:
        raise ProjectError(f"Verwacht {expected} activiteiten, kreeg er {len(written)}.")

    activities: list[dict[str, Any]] = []
    for position, item in enumerate(sorted(written, key=lambda a: a["sequence"]), start=1):
        sequence = int(item["sequence"])
        if sequence != position:
            raise ProjectError(
                f"Volgnummers zijn niet aaneengesloten: verwacht {position}, kreeg {sequence}."
            )

        prompts = []
        for index, prompt in enumerate(item["prompts"], start=1):
            entry = {k: v for k, v in prompt.items() if v not in (None, [], {})}
            entry["id"] = _prompt_id(index)
            prompts.append(entry)

        activity = {
            "id": f"{target_id}-act-{sequence:02d}",
            "book_id": book_id,
            "theme_id": theme_id,
            "kind": "exercise_activity",
            "title": item["title"],
            "cefr": cefr,
            "learning_objectives": [item["learning_objective"]],
            "source_page_refs": source_page_refs,
            "provenance": "original_companion",
            "rights_status": "original_only",
            "review_status": "draft",
            "target_id": target_id,
            "target_kind": target_kind,
            "sequence": sequence,
            "stage": int(item["stage"]),
            "difficulty": item["difficulty"],
            "interaction_type": item["interaction_type"],
            "instructions": item["instructions"],
            "stimulus": item["stimulus"],
            "prompts": prompts,
        }
        activity["content_hash"] = content_hash(activity)
        activities.append(activity)

    return activities


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="JSON met {'activities': [...]} of een lijst.")
    parser.add_argument("--target", required=True, help="ID van de scope-eenheid.")
    parser.add_argument("--kind", default="grammar_topic", choices=["grammar_topic", "vocabulary_set"])
    parser.add_argument("--dry-run", action="store_true", help="Alleen valideren, niets wegschrijven.")
    args = parser.parse_args()

    config = Config.load()
    payload = _load(Path(args.input))
    written = payload["activities"] if isinstance(payload, dict) else payload

    target_id = args.target
    theme_id = _theme_of(target_id)

    subdir = "grammar" if args.kind == "grammar_topic" else "vocabulary"
    topic_path = CONTENT_DIR / theme_id / subdir / f"{target_id}.json"
    if not topic_path.exists():
        raise ProjectError(f"Onderwerp ontbreekt: {relative(topic_path)}.")

    activities = assemble(written, target_id, args.kind, config, _load(topic_path))

    failures = 0
    for activity in activities:
        report = validate_schema(activity, "exercise_activity.json", activity["id"])
        for finding in report.errors:
            print(f"FOUT  {finding}")
            failures += 1

    report = validate_activity_set(activities, target_id, args.kind, config)
    for finding in report.errors:
        print(f"FOUT  {finding}")
        failures += 1
    for finding in report.warnings:
        print(f"LET OP {finding}")

    if failures:
        print(f"\n{failures} fouten — niets weggeschreven.")
        return 1

    if args.dry_run:
        print(f"{len(activities)} activiteiten in orde (dry run).")
        return 0

    out_dir = CONTENT_DIR / theme_id / "activities"
    ensure_dirs(out_dir)
    out_path = out_dir / f"{target_id}.json"
    write_json_atomic(
        out_path,
        {"target_id": target_id, "target_kind": args.kind, "activities": activities},
    )
    print(f"{len(activities)} activiteiten geschreven naar {relative(out_path)}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProjectError as error:
        print(f"FOUT  {error}", file=sys.stderr)
        raise SystemExit(1) from error
