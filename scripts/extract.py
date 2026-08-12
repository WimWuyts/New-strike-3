#!/usr/bin/env python3
"""Fase A — pagina's renderen en OCR draaien.

De bronboeken zijn gerasterde scans met een gepersonaliseerd watermerk en
zonder tekstlaag. Dit script:

1. rendert elke pagina naar PNG voor visuele inspectie;
2. draait OCR op een voorbewerkte versie van elke pagina;
3. filtert watermerkblokken weg;
4. schrijft page-map.jsonl met blokken, bounding boxes en confidence;
5. zet alles onder de confidencedrempel in de manual review queue.

Idempotent: een pagina wordt overgeslagen als bron, dpi en OCR-instellingen
ongewijzigd zijn. Forceer opnieuw met FORCE=1.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.project import (  # noqa: E402
    ASSETS_DIR,
    EXTRACTED_DIR,
    REPORTS_DIR,
    Config,
    ProjectError,
    State,
    content_hash,
    ensure_dirs,
    file_sha256,
    relative,
)


@dataclass
class Block:
    text: str
    confidence: float
    x0: float
    y0: float
    x1: float
    y1: float
    block_num: int
    line_num: int

    def to_json(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "confidence": round(self.confidence, 4),
            "bbox": {
                "x0": round(self.x0, 2),
                "y0": round(self.y0, 2),
                "x1": round(self.x1, 2),
                "y1": round(self.y1, 2),
            },
            "block_num": self.block_num,
            "line_num": self.line_num,
        }


# ---------------------------------------------------------------------------
# Beeldvoorbewerking
# ---------------------------------------------------------------------------


def preprocess(image: "Image.Image") -> "Image.Image":  # noqa: F821
    """Maakt de pagina leesbaarder voor OCR.

    Grijswaarden plus een lichte drempel. Dat haalt een groot deel van een
    lichtgrijs watermerk weg zonder de eigenlijke tekst aan te tasten. Wat
    overblijft wordt later op tekstniveau gefilterd.
    """
    import numpy as np
    from PIL import Image

    grey = image.convert("L")
    array = np.asarray(grey, dtype=np.uint8)

    # Alles lichter dan de drempel wordt wit. Zwarte broodtekst blijft staan.
    threshold = 176
    cleaned = np.where(array > threshold, 255, array).astype(np.uint8)
    return Image.fromarray(cleaned, mode="L")


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------


def ocr_page(image: "Image.Image", languages: list[str]) -> list[Block]:  # noqa: F821
    import pytesseract

    data = pytesseract.image_to_data(
        image,
        lang="+".join(languages),
        output_type=pytesseract.Output.DICT,
    )

    blocks: list[Block] = []
    count = len(data["text"])
    for index in range(count):
        text = (data["text"][index] or "").strip()
        if not text:
            continue
        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            confidence = -1.0
        if confidence < 0:
            continue
        blocks.append(
            Block(
                text=text,
                confidence=confidence / 100.0,
                x0=float(data["left"][index]),
                y0=float(data["top"][index]),
                x1=float(data["left"][index]) + float(data["width"][index]),
                y1=float(data["top"][index]) + float(data["height"][index]),
                block_num=int(data["block_num"][index]),
                line_num=int(data["line_num"][index]),
            )
        )
    return blocks


def merge_into_lines(blocks: list[Block]) -> list[Block]:
    """Voegt losse woorden samen tot regels, met gemiddelde confidence."""
    grouped: dict[tuple[int, int], list[Block]] = {}
    for block in blocks:
        grouped.setdefault((block.block_num, block.line_num), []).append(block)

    lines: list[Block] = []
    for (block_num, line_num), words in sorted(grouped.items()):
        words.sort(key=lambda w: w.x0)
        text = " ".join(w.text for w in words)
        lines.append(
            Block(
                text=text,
                confidence=sum(w.confidence for w in words) / len(words),
                x0=min(w.x0 for w in words),
                y0=min(w.y0 for w in words),
                x1=max(w.x1 for w in words),
                y1=max(w.y1 for w in words),
                block_num=block_num,
                line_num=line_num,
            )
        )
    return lines


def filter_watermark(lines: list[Block], watermark: str, threshold: float) -> tuple[list[Block], int]:
    """Verwijdert regels die (fuzzy) overeenkomen met de watermerktekst."""
    if not watermark:
        return lines, 0

    from rapidfuzz import fuzz

    needle = watermark.lower().strip()
    kept: list[Block] = []
    removed = 0
    for line in lines:
        candidate = line.text.lower().strip()
        ratio = fuzz.ratio(candidate, needle) / 100.0
        partial = fuzz.partial_ratio(candidate, needle) / 100.0
        # Korte regels die sterk op het watermerk lijken, gaan eruit.
        if ratio >= threshold or (len(candidate) <= len(needle) + 4 and partial >= threshold):
            removed += 1
            continue
        kept.append(line)
    return kept, removed


# ---------------------------------------------------------------------------
# Verwerking per boek
# ---------------------------------------------------------------------------


def process_theme(
    config: Config,
    book_id: str,
    theme: dict[str, Any],
    source_path: Path,
    state: State,
) -> dict[str, Any]:
    import fitz
    from PIL import Image

    extraction = config.extraction
    render_dpi = extraction["render_dpi"]
    ocr_dpi = extraction["ocr_dpi"]
    languages = extraction["ocr_languages"]
    min_conf = extraction["ocr_min_confidence"] / 100.0
    watermark_cfg = extraction.get("watermark", {})
    watermark_text = watermark_cfg.get("text", "")
    watermark_threshold = watermark_cfg.get("filter_similarity_threshold", 0.82)

    theme_id = theme["id"]
    render_dir = ASSETS_DIR / "extracted" / book_id / theme_id
    out_dir = EXTRACTED_DIR / book_id
    ensure_dirs(render_dir, out_dir)
    page_map_path = out_dir / f"{theme_id}.page-map.jsonl"

    signature = content_hash(
        {
            "source_sha256": file_sha256(source_path),
            "render_dpi": render_dpi,
            "ocr_dpi": ocr_dpi,
            "languages": languages,
            "watermark": watermark_text,
            "threshold": watermark_threshold,
        }
    )
    state_key = f"extract:{theme_id}"
    if state.is_current(state_key, signature) and page_map_path.exists():
        print(f"  {theme_id}: ongewijzigd, overgeslagen")
        with page_map_path.open(encoding="utf-8") as fh:
            pages = sum(1 for _ in fh)
        return {"theme_id": theme_id, "pages": pages, "skipped": True, "low_confidence": []}

    low_confidence: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []

    with fitz.open(source_path) as doc:
        for index, page in enumerate(doc, start=1):
            render_scale = render_dpi / 72.0
            pixmap = page.get_pixmap(matrix=fitz.Matrix(render_scale, render_scale))
            render_path = render_dir / f"page-{index:03d}.png"
            pixmap.save(render_path)

            ocr_scale = ocr_dpi / 72.0
            ocr_pixmap = page.get_pixmap(matrix=fitz.Matrix(ocr_scale, ocr_scale))
            image = Image.frombytes(
                "RGB", (ocr_pixmap.width, ocr_pixmap.height), ocr_pixmap.samples
            )

            prepared = preprocess(image)
            words = ocr_page(prepared, languages)
            lines = merge_into_lines(words)
            lines, removed = filter_watermark(lines, watermark_text, watermark_threshold)

            confident = [line for line in lines if line.confidence >= min_conf]
            uncertain = [line for line in lines if line.confidence < min_conf]

            for line in uncertain:
                low_confidence.append(
                    {
                        "theme_id": theme_id,
                        "page": index,
                        "text": line.text,
                        "confidence": round(line.confidence, 3),
                        "render": relative(render_path),
                    }
                )

            records.append(
                {
                    "book_id": book_id,
                    "theme_id": theme_id,
                    "page": index,
                    "render": relative(render_path),
                    "render_dpi": render_dpi,
                    "ocr_dpi": ocr_dpi,
                    "width": ocr_pixmap.width,
                    "height": ocr_pixmap.height,
                    "watermark_lines_removed": removed,
                    "blocks": [line.to_json() for line in confident],
                    "uncertain_blocks": [line.to_json() for line in uncertain],
                    "mean_confidence": (
                        round(sum(l.confidence for l in lines) / len(lines), 4) if lines else 0.0
                    ),
                }
            )
            print(
                f"  {theme_id} p{index:>3}: {len(confident)} blokken, "
                f"{len(uncertain)} onzeker, {removed} watermerkregels weg"
            )

    with page_map_path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    state.mark(state_key, signature)
    state.set_theme(theme_id, extracted_pages=len(records))
    return {
        "theme_id": theme_id,
        "pages": len(records),
        "skipped": False,
        "low_confidence": low_confidence,
    }


def append_review_queue(entries: list[dict[str, Any]]) -> None:
    if not entries:
        return
    path = REPORTS_DIR / "manual-review-queue.md"
    ensure_dirs(REPORTS_DIR)
    header = (
        "# Manual review queue\n\n"
        "OCR-blokken onder de confidencedrempel. Deze tekst komt **niet** in de\n"
        "content terecht tot iemand ze bevestigt of corrigeert.\n\n"
        "| Thema | Pagina | Confidence | Gelezen tekst | Pagina-render |\n"
        "|---|---:|---:|---|---|\n"
    )
    existing = path.read_text(encoding="utf-8") if path.exists() else header
    if not existing.startswith("# Manual review queue"):
        existing = header

    rows = [
        f"| {e['theme_id']} | {e['page']} | {e['confidence']:.2f} "
        f"| `{e['text'][:60].replace('|', '/')}` | `{e['render']}` |"
        for e in entries
    ]
    path.write_text(existing.rstrip("\n") + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render en OCR de bronpagina's.")
    parser.add_argument("--book", required=True, help="Boek-ID, bijvoorbeeld ace3")
    parser.add_argument("--theme", help="Alleen dit thema verwerken")
    args = parser.parse_args()

    config = Config.load()
    book = config.book(args.book)
    state = State()

    themes = book.themes
    if args.theme:
        themes = [book.theme(args.theme)]

    print(f"Extractie voor {book.title} ({len(themes)} thema's)")

    all_low: list[dict[str, Any]] = []
    processed = 0
    for theme in themes:
        source_path = book.source_dir / theme["source_file"]
        if not source_path.exists():
            print(f"  {theme['id']}: ONTBREEKT — {relative(source_path)}", file=sys.stderr)
            continue
        result = process_theme(config, book.id, theme, source_path, state)
        all_low.extend(result["low_confidence"])
        processed += 1

    append_review_queue(all_low)
    state.set_stage(f"extract:{book.id}", status="done", themes=processed)
    state.save()

    print(f"\nVerwerkt: {processed}/{len(themes)} thema's")
    if all_low:
        print(
            f"{len(all_low)} onzekere OCR-blokken naar "
            f"{relative(REPORTS_DIR / 'manual-review-queue.md')}"
        )
    return 0 if processed == len(themes) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProjectError as exc:
        print(f"Fout: {exc}", file=sys.stderr)
        raise SystemExit(2)
