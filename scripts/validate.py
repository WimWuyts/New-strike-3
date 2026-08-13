#!/usr/bin/env python3
"""Valideert de content van een thema of van het hele project.

Controleert schema's, de quota uit sectie 11, antwoordbaarheid, bewijs bij
reading- en listeningvragen, en de scheiding tussen leerling- en
leerkrachtoutput. Exitcode 1 zodra er één fout is: dat blokkeert publicatie
naar dist/.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.project import (  # noqa: E402
    CONTENT_DIR,
    REPORTS_DIR,
    Config,
    ProjectError,
    State,
    content_hash,
    ensure_dirs,
    relative,
)
from lib.validation import (  # noqa: E402
    Report,
    validate_activity_set,
    validate_module_evidence,
    validate_schema,
)

SCHEMA_FOR_DIR = {
    "vocabulary": "vocabulary_set.json",
    "grammar": "grammar_topic.json",
    "readings": "reading_module.json",
    "listenings": "listening_module.json",
    "visuals": "visual_grammar_model.json",
}
MODULE_KIND_FOR_DIR = {"readings": "reading", "listenings": "listening"}


def _load(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def validate_theme(theme_id: str, config: Config) -> Report:
    report = Report()
    theme_dir = CONTENT_DIR / theme_id

    if not theme_dir.exists():
        report.error(
            "missing-content",
            f"Geen content gevonden in {relative(theme_dir)}.",
            theme_id,
        )
        return report

    # -- entiteiten met een eigen schema ----------------------------------
    for subdir, schema_name in SCHEMA_FOR_DIR.items():
        for path in sorted((theme_dir / subdir).glob("*.json")):
            payload = _load(path)
            loc = relative(path)
            report.extend(validate_schema(payload, schema_name, loc))
            _check_hash(payload, report, loc)

            kind = MODULE_KIND_FOR_DIR.get(subdir)
            if kind:
                report.extend(validate_module_evidence(payload, kind))

    # -- readings en listenings: aantal én niveaukoppels --------------------
    for subdir, key in (("readings", "readings_per_theme"), ("listenings", "listenings_per_theme")):
        expected = config.modules[key]
        paths = sorted((theme_dir / subdir).glob("*.json"))
        if len(paths) != expected:
            report.error(
                "module-count",
                f"{len(paths)} bestanden in {subdir}/, verwacht {expected}.",
                theme_id,
            )
        _check_variant_pairs(paths, subdir, config, report, theme_id)

    # -- oefenreeksen ------------------------------------------------------
    activity_dir = theme_dir / "activities"
    targets_seen: set[str] = set()
    for path in sorted(activity_dir.glob("*.json")):
        payload = _load(path)
        loc = relative(path)

        if not isinstance(payload, dict) or "activities" not in payload:
            report.error("activity-format", "Bestand bevat geen 'activities'.", loc)
            continue

        target_id = payload.get("target_id", path.stem)
        target_kind = payload.get("target_kind")
        if target_kind not in {"grammar_topic", "vocabulary_set"}:
            report.error("activity-target-kind", f"Ongeldig target_kind: {target_kind!r}.", loc)
            continue

        targets_seen.add(target_id)
        for activity in payload["activities"]:
            report.extend(
                validate_schema(activity, "exercise_activity.json", f"{loc}:{activity.get('id', '?')}")
            )
        report.extend(
            validate_activity_set(payload["activities"], target_id, target_kind, config)
        )

    # -- elke scope-eenheid moet een reeks hebben --------------------------
    expected_targets = {p.stem for p in (theme_dir / "grammar").glob("*.json")}
    expected_targets |= {p.stem for p in (theme_dir / "vocabulary").glob("*.json")}
    for missing in sorted(expected_targets - targets_seen):
        report.error(
            "missing-activity-set",
            f"Scope-eenheid {missing!r} heeft geen reeks van "
            f"{config.exercises['per_scope_unit']} activiteiten.",
            theme_id,
        )

    return report


def _check_variant_pairs(
    paths: list[Path], subdir: str, config: Config, report: Report, theme_id: str
) -> None:
    """Elk onderwerp moet op beide niveaus bestaan.

    Differentiatie werkt alleen als de leerkracht dezelfde inhoud in twee
    moeilijkheidsgraden naast elkaar kan leggen. Eén losse `challenge` zonder
    `core` is dus geen differentiatie maar een gat.
    """
    if not paths:
        return

    by_topic: dict[str, set[str]] = {}
    for path in paths:
        payload = _load(path)
        topic = payload.get("topic_id")
        if not topic:
            report.error("module-topic", "Module zonder topic_id.", relative(path))
            continue
        by_topic.setdefault(topic, set()).add(payload.get("variant", "?"))

    expected_topics = config.modules.get("topics_per_theme")
    if expected_topics and len(by_topic) != expected_topics:
        report.error(
            "module-topics",
            f"{len(by_topic)} onderwerpen in {subdir}/, verwacht {expected_topics}.",
            theme_id,
        )

    for topic, variants in sorted(by_topic.items()):
        missing = set(config.modules["variants"]) - variants
        if missing:
            report.error(
                "module-variant-missing",
                f"Onderwerp {topic!r} in {subdir}/ mist de variant(en): {', '.join(sorted(missing))}.",
                theme_id,
            )


def _check_hash(payload: Any, report: Report, loc: str) -> None:
    if not isinstance(payload, dict):
        return
    stored = payload.get("content_hash")
    if not stored:
        return
    actual = content_hash(payload)
    if stored != actual:
        report.error(
            "stale-hash",
            f"content_hash klopt niet meer (opgeslagen {stored[:12]}…, berekend {actual[:12]}…).",
            loc,
        )


def write_report(theme_ids: list[str], report: Report) -> Path:
    ensure_dirs(REPORTS_DIR)
    path = REPORTS_DIR / "validation.md"
    lines = ["# Validatierapport", "", f"Gecontroleerde thema's: {', '.join(theme_ids) or '(geen)'}", ""]

    if report.ok and not report.warnings:
        lines += ["Alles groen. Geen fouten, geen waarschuwingen.", ""]
    else:
        lines += [
            f"- Fouten: **{len(report.errors)}**",
            f"- Waarschuwingen: **{len(report.warnings)}**",
            "",
        ]

    for level, items in (("Fouten", report.errors), ("Waarschuwingen", report.warnings)):
        if not items:
            continue
        lines += [f"## {level}", "", "| Code | Locatie | Melding |", "|---|---|---|"]
        for finding in items:
            message = finding.message.replace("|", "/")
            lines.append(f"| `{finding.code}` | `{finding.location or '-'}` | {message} |")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Valideer content tegen schema's en quota.")
    parser.add_argument("--theme", help="Alleen dit thema; standaard alle thema's met content")
    parser.add_argument("--quiet", action="store_true", help="Toon alleen de samenvatting")
    args = parser.parse_args()

    config = Config.load()
    state = State()

    if args.theme:
        config.book_for_theme(args.theme)  # valideert dat het thema bestaat
        theme_ids = [args.theme]
    else:
        theme_ids = sorted(p.name for p in CONTENT_DIR.glob("*") if p.is_dir())

    if not theme_ids:
        print(f"Geen content gevonden in {relative(CONTENT_DIR)}.", file=sys.stderr)
        return 1

    combined = Report()
    for theme_id in theme_ids:
        result = validate_theme(theme_id, config)
        combined.extend(result)
        status = "OK" if result.ok else f"{len(result.errors)} fouten"
        print(f"{theme_id}: {status}")
        state.set_theme(
            theme_id,
            validation="passed" if result.ok else "failed",
            validation_errors=len(result.errors),
        )

    if not args.quiet:
        for finding in combined.findings[:60]:
            print(f"  {finding}")
        if len(combined.findings) > 60:
            print(f"  … en nog {len(combined.findings) - 60} bevindingen")

    path = write_report(theme_ids, combined)
    state.set_stage(
        "validate",
        status="passed" if combined.ok else "failed",
        errors=len(combined.errors),
        warnings=len(combined.warnings),
    )
    state.save()

    print(
        f"\nFouten: {len(combined.errors)} | Waarschuwingen: {len(combined.warnings)}"
        f"\nRapport: {relative(path)}"
    )
    return 0 if combined.ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProjectError as exc:
        print(f"Fout: {exc}", file=sys.stderr)
        raise SystemExit(2)
