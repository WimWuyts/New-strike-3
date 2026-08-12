"""OCR-keten getest op synthetische gescande pagina's.

De echte bronnen zijn gerasterde scans met een gepersonaliseerd watermerk over
elke pagina. Deze tests bouwen zo'n pagina na: tekst wordt naar beeld
gerenderd, dus zonder tekstlaag, met een watermerk erover.

Het watermerk wordt op twee plaatsen tegengehouden, en die worden apart
getest:

1. de beeldvoorbewerking trekt lichte grijstinten naar wit, zodat een licht
   watermerk OCR nooit bereikt;
2. de tekstfilter verwijdert regels die op het watermerk lijken, voor het
   geval het donker genoeg is om de voorbewerking te overleven.

Wordt overgeslagen als tesseract of de beeldbibliotheken ontbreken, zodat de
rest van de suite ook zonder OCR-stack draait.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("fitz", reason="PyMuPDF niet geïnstalleerd")
pytest.importorskip("PIL", reason="Pillow niet geïnstalleerd")
pytest.importorskip("pytesseract", reason="pytesseract niet geïnstalleerd")
pytest.importorskip("rapidfuzz", reason="rapidfuzz niet geïnstalleerd")

if shutil.which("tesseract") is None:
    pytest.skip("tesseract niet gevonden", allow_module_level=True)

import fitz  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from extract import (  # noqa: E402
    Block,
    filter_watermark,
    merge_into_lines,
    ocr_page,
    preprocess,
)

WATERMARK = "Wim Wuyts"
THRESHOLD = 0.82

BODY_LINES = [
    "Present perfect",
    "We use this tense to talk about experience.",
    "She has finished her homework already.",
]

# Grijswaarden aan weerszijden van de drempel in preprocess().
LIGHT_WATERMARK = 196
DARK_WATERMARK = 120

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    pytest.skip("Geen bruikbaar TrueType-font gevonden voor de testpagina.")


def _page(watermark_grey: int) -> Image.Image:
    image = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(image)

    body = _font(48)
    for index, line in enumerate(BODY_LINES):
        draw.text((90, 150 + index * 110), line, fill="black", font=body)

    mark = _font(64)
    tone = (watermark_grey,) * 3
    for row in range(3):
        draw.text((180, 700 + row * 320), WATERMARK, fill=tone, font=mark)

    return image


def _lines(image: Image.Image) -> list[Block]:
    return merge_into_lines(ocr_page(preprocess(image), ["eng"]))


@pytest.fixture(scope="module")
def light_page() -> Image.Image:
    return _page(LIGHT_WATERMARK)


@pytest.fixture(scope="module")
def dark_page() -> Image.Image:
    return _page(DARK_WATERMARK)


@pytest.fixture(scope="module")
def light_lines(light_page: Image.Image) -> list[Block]:
    return _lines(light_page)


@pytest.fixture(scope="module")
def dark_lines(dark_page: Image.Image) -> list[Block]:
    return _lines(dark_page)


# ---------------------------------------------------------------------------
# De bron gedraagt zich zoals aangenomen
# ---------------------------------------------------------------------------


def test_synthetic_pdf_has_no_text_layer(tmp_path: Path, light_page: Image.Image):
    """Bevestigt de aanname waarop de hele extractiestrategie rust."""
    png_path = tmp_path / "page.png"
    light_page.save(png_path)

    pdf_path = tmp_path / "unit.pdf"
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_image(fitz.Rect(0, 0, 595, 842), filename=str(png_path))
    document.save(pdf_path)
    document.close()

    with fitz.open(pdf_path) as reopened:
        text = "".join(page.get_text("text") for page in reopened)
    assert text.strip() == "", "De testpagina mag geen tekstlaag hebben."


# ---------------------------------------------------------------------------
# OCR leest de inhoud
# ---------------------------------------------------------------------------


def test_ocr_reads_the_body_text(light_lines: list[Block]):
    text = " ".join(line.text for line in light_lines).lower()
    assert "present perfect" in text
    assert "homework" in text


def test_ocr_reports_usable_confidence(light_lines: list[Block]):
    assert light_lines, "OCR leverde geen enkele regel op."
    mean = sum(line.confidence for line in light_lines) / len(light_lines)
    assert 0.0 <= mean <= 1.0
    assert mean > 0.5, f"Gemiddelde confidence te laag: {mean:.2f}"


def test_lines_carry_bounding_boxes(light_lines: list[Block]):
    for line in light_lines:
        assert line.x1 > line.x0
        assert line.y1 > line.y0


# ---------------------------------------------------------------------------
# Laag 1 — de voorbewerking
# ---------------------------------------------------------------------------


def test_preprocess_whitens_tones_above_the_threshold(light_page: Image.Image):
    """Lichte grijstinten gaan naar wit, zwarte broodtekst blijft staan."""
    import numpy as np

    before = np.asarray(light_page.convert("L"), dtype=np.uint8)
    after = np.asarray(preprocess(light_page), dtype=np.uint8)

    assert after[before < 100].max() < 100, "De broodtekst is lichter geworden."

    above_threshold = before > 176
    assert above_threshold.any()
    assert after[above_threshold].min() == 255


def test_light_watermark_never_reaches_ocr(light_lines: list[Block]):
    """Het lichte watermerk wordt weggepoetst vóór OCR, niet erna."""
    text = " ".join(line.text for line in light_lines).lower()
    assert "wuyts" not in text
    assert "wim" not in text


# ---------------------------------------------------------------------------
# Laag 2 — de tekstfilter
# ---------------------------------------------------------------------------


def test_dark_watermark_survives_preprocessing(dark_lines: list[Block]):
    """Zonder deze aanname test de volgende test niets."""
    text = " ".join(line.text for line in dark_lines).lower()
    assert "wuyts" in text


def test_dark_watermark_is_filtered_from_the_text(dark_lines: list[Block]):
    kept, removed = filter_watermark(dark_lines, WATERMARK, THRESHOLD)
    kept_text = " ".join(line.text for line in kept).lower()

    assert removed >= 1, "Geen enkele watermerkregel herkend."
    assert "wuyts" not in kept_text


def test_filtering_keeps_the_real_content(dark_lines: list[Block]):
    kept, _ = filter_watermark(dark_lines, WATERMARK, THRESHOLD)
    kept_text = " ".join(line.text for line in kept).lower()

    for expected in ("present perfect", "homework", "experience"):
        assert expected in kept_text, f"{expected!r} is ten onrechte weggefilterd."


def _block(text: str) -> Block:
    return Block(
        text=text, confidence=0.9, x0=0, y0=0, x1=100, y1=20, block_num=1, line_num=1
    )


@pytest.mark.parametrize("garbled", ["Wim Wuyts", "Wim Wuyfs", "wim wuyts", "Wlm Wuyts"])
def test_filter_catches_ocr_misreadings_of_the_watermark(garbled: str):
    """OCR leest het watermerk zelden perfect; daarom is de match fuzzy."""
    kept, removed = filter_watermark([_block(garbled)], WATERMARK, THRESHOLD)
    assert removed == 1, f"{garbled!r} werd niet als watermerk herkend."
    assert kept == []


@pytest.mark.parametrize(
    "content",
    [
        "We use this tense to talk about experience.",
        "William went to the shop.",
        "Present perfect",
    ],
)
def test_filter_leaves_ordinary_content_alone(content: str):
    kept, removed = filter_watermark([_block(content)], WATERMARK, THRESHOLD)
    assert removed == 0, f"{content!r} werd ten onrechte als watermerk gezien."
    assert len(kept) == 1


def test_filtering_without_a_watermark_is_a_no_op(dark_lines: list[Block]):
    kept, removed = filter_watermark(dark_lines, "", THRESHOLD)
    assert removed == 0
    assert len(kept) == len(dark_lines)
