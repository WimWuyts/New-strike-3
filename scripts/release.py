#!/usr/bin/env python3
"""Publiceert alleen gevalideerde artefacten en schrijft het releasemanifest.

De poort is hard: een thema met validatiefouten komt niet in het manifest, en
artefacten van zo'n thema worden uit dist/ geweerd. Liever een kleinere
release dan een release met stille fouten.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.project import (  # noqa: E402
    CONTENT_DIR,
    DIST_DIR,
    REPORTS_DIR,
    Config,
    ProjectError,
    State,
    ensure_dirs,
    file_sha256,
    relative,
    write_json_atomic,
)
from validate import validate_theme  # noqa: E402

ARTEFACT_KINDS = {
    ".pptx": "presentation",
    ".html": "web",
    ".mp3": "audio",
    ".wav": "audio",
    ".pdf": "printable",
    ".js": "web",
    ".css": "web",
}


def theme_of(path: Path) -> str | None:
    """Leidt het thema uit een bestandsnaam af, bijvoorbeeld ace3-u1-student.pptx."""
    stem = path.stem
    for suffix in ("-student", "-teacher"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Bouw een release uit gevalideerde content.")
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Publiceer de geslaagde thema's ook als andere thema's falen.",
    )
    args = parser.parse_args()

    config = Config.load()
    state = State()
    ensure_dirs(DIST_DIR, REPORTS_DIR)

    theme_ids = sorted(p.name for p in CONTENT_DIR.glob("*") if p.is_dir())
    if not theme_ids:
        print(f"Geen content in {relative(CONTENT_DIR)}.", file=sys.stderr)
        return 1

    passed: list[str] = []
    failed: dict[str, int] = {}

    for theme_id in theme_ids:
        report = validate_theme(theme_id, config)
        if report.ok:
            passed.append(theme_id)
        else:
            failed[theme_id] = len(report.errors)
        print(f"{theme_id}: {'OK' if report.ok else f'{len(report.errors)} fouten'}")

    if failed and not args.allow_partial:
        print(
            f"\nGeblokkeerd: {len(failed)} thema('s) falen de validatie. "
            f"Repareer die eerst, of gebruik --allow-partial bewust.",
            file=sys.stderr,
        )
        _write_report(passed, failed, [], blocked=True)
        return 1

    # -- artefacten inventariseren ----------------------------------------
    artefacts: list[dict[str, Any]] = []
    skipped: list[str] = []

    for path in sorted(DIST_DIR.rglob("*")):
        if not path.is_file() or path.name == "release-manifest.json":
            continue

        kind = ARTEFACT_KINDS.get(path.suffix.lower())
        if kind is None:
            continue

        theme_id = theme_of(path)
        if theme_id and theme_id not in passed:
            skipped.append(relative(path))
            continue

        book_id = None
        if theme_id:
            try:
                book_id = config.book_for_theme(theme_id).id
            except ProjectError:
                book_id = None

        artefacts.append(
            {
                "path": relative(path),
                "kind": kind,
                "book_id": book_id,
                "theme_id": theme_id,
                "audience": (
                    "teacher"
                    if path.stem.endswith("-teacher")
                    else "student"
                    if path.stem.endswith("-student")
                    else None
                ),
                "sha256": file_sha256(path),
                "size_bytes": path.stat().st_size,
                "qa_status": "validated",
            }
        )

    manifest = {
        "schema_version": config["project"]["schema_version"],
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rights_status": config.rights["status"],
        "scope_unit": config.exercises["scope_unit"],
        "themes_validated": passed,
        "themes_failed": failed,
        "artefacts": artefacts,
    }
    write_json_atomic(DIST_DIR / "release-manifest.json", manifest)
    _write_report(passed, failed, artefacts, blocked=False)

    state.set_stage(
        "release",
        status="partial" if failed else "done",
        themes=len(passed),
        artefacts=len(artefacts),
    )
    state.save()

    print(f"\nThema's in de release: {len(passed)}")
    print(f"Artefacten           : {len(artefacts)}")
    if skipped:
        print(f"Geweerd uit dist/    : {len(skipped)} (thema faalde de validatie)")
    print(f"\nManifest: {relative(DIST_DIR / 'release-manifest.json')}")
    return 0


def _write_report(
    passed: list[str],
    failed: dict[str, int],
    artefacts: list[dict[str, Any]],
    blocked: bool,
) -> None:
    lines = ["# Finale QA", ""]
    if blocked:
        lines += ["> ⛔ Release geblokkeerd: niet alle thema's zijn geldig.", ""]

    lines += [
        f"- Thema's geldig: **{len(passed)}**",
        f"- Thema's met fouten: **{len(failed)}**",
        f"- Artefacten in de release: **{len(artefacts)}**",
        "",
    ]

    if failed:
        lines += ["## Thema's met fouten", "", "| Thema | Fouten |", "|---|---:|"]
        lines += [f"| `{theme}` | {count} |" for theme, count in sorted(failed.items())]
        lines += ["", "Zie `reports/validation.md` voor de details.", ""]

    if artefacts:
        lines += [
            "## Artefacten",
            "",
            "| Pad | Soort | Boek | Thema | Doelgroep | SHA-256 |",
            "|---|---|---|---|---|---|",
        ]
        for item in artefacts:
            lines.append(
                f"| `{item['path']}` | {item['kind']} | {item['book_id'] or '-'} "
                f"| {item['theme_id'] or '-'} | {item['audience'] or '-'} "
                f"| `{item['sha256'][:16]}…` |"
            )
        lines.append("")

    (REPORTS_DIR / "final-qa.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProjectError as exc:
        print(f"Fout: {exc}", file=sys.stderr)
        raise SystemExit(2)
