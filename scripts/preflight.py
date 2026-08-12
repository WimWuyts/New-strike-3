#!/usr/bin/env python3
"""Read-only inventarisatie van sources/.

Raakt niets aan in sources/. Schrijft reports/intake.md en
reports/source-inventory.md, en zet de technische staat van elke pdf vast:
hash, paginatal, tekstlaag, watermerk en OCR-behoefte.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.project import (  # noqa: E402
    REPORTS_DIR,
    SOURCES_DIR,
    Config,
    ProjectError,
    State,
    ensure_dirs,
    file_sha256,
    relative,
    write_json_atomic,
    DATA_DIR,
)

REQUIRED_BINARIES = {
    "pdftoppm": "poppler-utils — pagina's renderen",
    "tesseract": "tesseract-ocr — OCR",
    "soffice": "LibreOffice — PPTX renderen voor visuele QA",
}
OPTIONAL_BINARIES = {
    "ffmpeg": "ffmpeg — alleen nodig als er echte audio of video gebouwd wordt",
}

# Een pdf met minder dan dit aantal betekenisvolle tekens per pagina heeft
# in de praktijk geen bruikbare tekstlaag.
TEXT_LAYER_CHARS_PER_PAGE = 40


@dataclass
class PdfReport:
    book_id: str
    path: str
    sha256: str
    size_bytes: int
    pages: int | None
    text_chars: int
    chars_per_page: float
    has_text_layer: bool
    watermark_detected: bool
    watermark_text: str | None
    ocr_required: bool
    read_error: str | None


def inspect_pdf(path: Path, book_id: str, watermark_text: str) -> PdfReport:
    import fitz  # PyMuPDF

    base = PdfReport(
        book_id=book_id,
        path=relative(path),
        sha256=file_sha256(path),
        size_bytes=path.stat().st_size,
        pages=None,
        text_chars=0,
        chars_per_page=0.0,
        has_text_layer=False,
        watermark_detected=False,
        watermark_text=None,
        ocr_required=True,
        read_error=None,
    )

    try:
        with fitz.open(path) as doc:
            base.pages = doc.page_count
            total_chars = 0
            watermark_hits = 0
            needle = watermark_text.replace(" ", "").lower()

            for page in doc:
                text = page.get_text("text") or ""
                compact = text.replace(" ", "").replace("\n", "").lower()
                if needle and needle in compact:
                    watermark_hits += 1
                    # Watermerktekst telt niet mee als bruikbare tekstlaag.
                    compact = compact.replace(needle, "")
                total_chars += len(compact)

            base.text_chars = total_chars
            base.chars_per_page = total_chars / doc.page_count if doc.page_count else 0.0
            base.has_text_layer = base.chars_per_page >= TEXT_LAYER_CHARS_PER_PAGE
            base.watermark_detected = watermark_hits > 0
            base.watermark_text = watermark_text if watermark_hits else None
            base.ocr_required = not base.has_text_layer
    except Exception as exc:  # pragma: no cover - afhankelijk van bronbestand
        base.read_error = f"{type(exc).__name__}: {exc}"

    return base


def check_binaries() -> tuple[dict[str, str], dict[str, str]]:
    missing_required = {
        name: why for name, why in REQUIRED_BINARIES.items() if shutil.which(name) is None
    }
    missing_optional = {
        name: why for name, why in OPTIONAL_BINARIES.items() if shutil.which(name) is None
    }
    return missing_required, missing_optional


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only inventarisatie van sources/")
    parser.add_argument("--json", action="store_true", help="Print het rapport ook als JSON.")
    args = parser.parse_args()

    config = Config.load()
    ensure_dirs(REPORTS_DIR, DATA_DIR)

    watermark_text = config.extraction.get("watermark", {}).get("text", "")
    missing_required, missing_optional = check_binaries()

    reports: list[PdfReport] = []
    missing_files: list[str] = []

    for book in config.books:
        for theme in book.themes:
            path = book.source_dir / theme["source_file"]
            if not path.exists():
                missing_files.append(f"{book.id}: {relative(path)}")
                continue
            reports.append(inspect_pdf(path, book.id, watermark_text))

    stray = []
    if SOURCES_DIR.exists():
        expected = {
            (book.source_dir / theme["source_file"]).resolve()
            for book in config.books
            for theme in book.themes
        }
        for candidate in (SOURCES_DIR / "books").rglob("*.pdf"):
            if candidate.resolve() not in expected:
                stray.append(relative(candidate))

    _write_reports(config, reports, missing_files, stray, missing_required, missing_optional)
    write_json_atomic(
        DATA_DIR / "source-inventory.json",
        {"pdfs": [asdict(r) for r in reports], "missing": missing_files},
    )

    state = State()
    state.set_stage(
        "preflight",
        status="blocked" if missing_files or missing_required else "done",
        pdfs_found=len(reports),
        pdfs_missing=len(missing_files),
    )
    state.save()

    # -- samenvatting op stdout -------------------------------------------
    print(f"Bronbestanden gevonden : {len(reports)}")
    print(f"Bronbestanden ontbrekend: {len(missing_files)}")
    if reports:
        needs_ocr = sum(1 for r in reports if r.ocr_required)
        watermarked = sum(1 for r in reports if r.watermark_detected)
        total_pages = sum(r.pages or 0 for r in reports)
        print(f"Pagina's totaal         : {total_pages}")
        print(f"OCR nodig               : {needs_ocr}/{len(reports)} bestanden")
        print(f"Watermerk gedetecteerd  : {watermarked}/{len(reports)} bestanden")
    if missing_required:
        print("\nOntbrekende systeemtools (blokkerend):")
        for name, why in missing_required.items():
            print(f"  - {name}: {why}")
    print(f"\nRapport: {relative(REPORTS_DIR / 'intake.md')}")

    if missing_files:
        print(
            "\nGeblokkeerd: zet de ontbrekende pdf's klaar in sources/books/<boek>/ "
            "voordat je `make extract` draait.",
            file=sys.stderr,
        )
        return 1
    if missing_required:
        print("\nGeblokkeerd: installeer de ontbrekende systeemtools.", file=sys.stderr)
        return 1
    return 0


def _write_reports(
    config: Config,
    reports: list[PdfReport],
    missing_files: list[str],
    stray: list[str],
    missing_required: dict[str, str],
    missing_optional: dict[str, str],
) -> None:
    lines: list[str] = ["# Intake — technische staat van de bronnen", ""]

    if missing_files:
        lines += [
            "## ⛔ Ontbrekende bronbestanden",
            "",
            "De pipeline kan niet starten zolang deze bestanden er niet staan.",
            "",
        ]
        lines += [f"- `{item}`" for item in missing_files]
        lines.append("")

    if missing_required:
        lines += ["## ⛔ Ontbrekende systeemtools", ""]
        lines += [f"- `{name}` — {why}" for name, why in missing_required.items()]
        lines.append("")

    if missing_optional:
        lines += ["## Optionele tools niet gevonden", ""]
        lines += [f"- `{name}` — {why}" for name, why in missing_optional.items()]
        lines.append("")

    if stray:
        lines += [
            "## Niet-herkende pdf's in sources/",
            "",
            "Deze bestanden staan niet in `config/project.yaml` en worden genegeerd.",
            "",
        ]
        lines += [f"- `{item}`" for item in stray]
        lines.append("")

    for book in config.books:
        rows = [r for r in reports if r.book_id == book.id]
        if not rows:
            continue
        lines += [
            f"## {book.title}",
            "",
            f"Doelgroep: {book.audience} — richtniveau {book.cefr_target}",
            "",
            "| Bestand | Pagina's | Tekstlaag | Tekens/pagina | Watermerk | OCR | SHA-256 |",
            "|---|---:|:-:|---:|:-:|:-:|---|",
        ]
        for row in rows:
            pages = row.pages if row.pages is not None else "?"
            lines.append(
                f"| `{Path(row.path).name}` | {pages} "
                f"| {'ja' if row.has_text_layer else 'nee'} "
                f"| {row.chars_per_page:.0f} "
                f"| {'ja' if row.watermark_detected else 'nee'} "
                f"| {'verplicht' if row.ocr_required else 'niet nodig'} "
                f"| `{row.sha256[:16]}…` |"
            )
        lines.append("")

        errors = [r for r in rows if r.read_error]
        if errors:
            lines += ["### Leesfouten", ""]
            lines += [f"- `{Path(r.path).name}`: {r.read_error}" for r in errors]
            lines.append("")

    if reports:
        needs_ocr = sum(1 for r in reports if r.ocr_required)
        lines += [
            "## Gevolgen voor de pipeline",
            "",
            f"- OCR is vereist voor **{needs_ocr} van de {len(reports)}** bestanden.",
        ]
        if any(r.watermark_detected for r in reports):
            lines.append(
                "- Er is een watermerk gedetecteerd. De OCR-pijplijn filtert dat weg; "
                "rasterreproductie van bronpagina's blijft afgeraden."
            )
        if needs_ocr:
            lines.append(
                "- Zonder tekstlaag zijn er geen font- of kleurmetadata. Designtokens "
                "worden afgeleid uit beeldanalyse en zijn dus een benadering."
            )
        lines.append("")

    (REPORTS_DIR / "intake.md").write_text("\n".join(lines), encoding="utf-8")

    inventory = ["# Bronoverzicht", "", "| Boek | Bestand | Bytes | SHA-256 |", "|---|---|---:|---|"]
    for row in sorted(reports, key=lambda r: (r.book_id, r.path)):
        inventory.append(
            f"| {row.book_id} | `{Path(row.path).name}` | {row.size_bytes:,} | `{row.sha256}` |"
        )
    inventory.append("")
    (REPORTS_DIR / "source-inventory.md").write_text("\n".join(inventory), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProjectError as exc:
        print(f"Fout: {exc}", file=sys.stderr)
        raise SystemExit(2)
