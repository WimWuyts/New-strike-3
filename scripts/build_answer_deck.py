#!/usr/bin/env python3
"""Bouwt het klassikale correctiedeck bij de oefeningen van het handboek.

Kern van dit deck is de klik-voor-klik onthulling: bij het openen van een slide
staan alleen de itemnummers en de vraagstelling er; elke klik laat één antwoord
verschijnen. Een volledige sleutel in één keer leest niemand mee.

python-pptx kent geen API voor animaties, dus de `<p:timing>`-boom wordt per
slide in de slide-XML geïnjecteerd. Zie `add_click_reveal`.

Dit deck bevat uitgeversinhoud en bestaat alleen onder de rechtenbevestiging in
docs/rights-confirmation.md. Het is leerkrachtmateriaal.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Emu, Inches, Pt
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.project import (  # noqa: E402
    Config,
    ProjectError,
    ROOT,
    ensure_dirs,
    relative,
)

# ---------------------------------------------------------------------------
# Vormgeving — waarden uit de opdrachtomschrijving
# ---------------------------------------------------------------------------

PETROL = RGBColor(0x0E, 0x7C, 0x8A)
LIME = RGBColor(0xA5, 0xC6, 0x3B)
LIME_FILL = RGBColor(0xED, 0xF2, 0xD6)
ORANGE = RGBColor(0xE8, 0xA3, 0x3D)
DARKRED = RGBColor(0xC0, 0x34, 0x2B)
BEIGE = RGBColor(0xED, 0xE0, 0xD0)
ANSWER_BLUE = RGBColor(0x1F, 0x6F, 0xB2)
BLACK = RGBColor(0x1A, 0x1A, 0x1A)
GREY = RGBColor(0x8C, 0x8C, 0x8C)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

FONT = "Verdana"

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
MARGIN = Inches(0.6)
CONTENT_W = SLIDE_W - MARGIN * 2

# Typografie. Leesbaarheid gaat vóór getrouwheid: alles in de body minstens 24 pt.
PT_NUMBER = 40
PT_TITLE = 30
PT_ITEM = 24
PT_ANSWER = 27
PT_TABLE = 22
PT_FOOTER = 12

LINE_SPACING = 1.2
BODY_TOP = Inches(1.65)
# Onder deze lijn staan de voetnoot en de klik-hint, dus daar stopt de inhoud.
BODY_BOTTOM = Inches(6.60)
ANSWER_INDENT = Inches(0.394)  # 1 cm

# Ruwe schatting van de tekenbreedte van Verdana, om regelterugloop te voorspellen.
CHAR_WIDTH_FACTOR = 0.60


# ---------------------------------------------------------------------------
# Klik-animatie
# ---------------------------------------------------------------------------

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"


def _click_par(shape_ids: Iterable[int], base_id: int) -> tuple[str, int]:
    """Bouwt één klikstap die de gegeven shapes tegelijk laat verschijnen."""
    node_id = base_id
    behaviours = []
    for spid in shape_ids:
        behaviours.append(
            f"""
            <p:par>
              <p:cTn id="{node_id + 1}" presetID="1" presetClass="entr" presetSubtype="0"
                     fill="hold" grpId="0" nodeType="{'clickEffect' if spid == list(shape_ids)[0] else 'withEffect'}">
                <p:stCondLst><p:cond delay="0"/></p:stCondLst>
                <p:childTnLst>
                  <p:set>
                    <p:cBhvr>
                      <p:cTn id="{node_id + 2}" dur="1" fill="hold">
                        <p:stCondLst><p:cond delay="0"/></p:stCondLst>
                      </p:cTn>
                      <p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>
                      <p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>
                    </p:cBhvr>
                    <p:to><p:strVal val="visible"/></p:to>
                  </p:set>
                  <p:animEffect transition="in" filter="fade">
                    <p:cBhvr>
                      <p:cTn id="{node_id + 3}" dur="400"/>
                      <p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>
                    </p:cBhvr>
                  </p:animEffect>
                </p:childTnLst>
              </p:cTn>
            </p:par>"""
        )
        node_id += 3

    inner = "".join(behaviours)
    xml = f"""
        <p:par>
          <p:cTn id="{node_id + 1}" fill="hold">
            <p:stCondLst><p:cond delay="indefinite"/></p:stCondLst>
            <p:childTnLst>
              <p:par>
                <p:cTn id="{node_id + 2}" fill="hold">
                  <p:stCondLst><p:cond delay="0"/></p:stCondLst>
                  <p:childTnLst>{inner}</p:childTnLst>
                </p:cTn>
              </p:par>
            </p:childTnLst>
          </p:cTn>
        </p:par>"""
    return xml, node_id + 2


def add_click_reveal(slide, steps: list[list[int]]) -> None:
    """Injecteert een p:timing-boom: één klik per stap.

    `steps` is een lijst van stappen; elke stap is een lijst shape-id's die
    samen verschijnen. Zo verschijnt een antwoord samen met zijn alternatieven
    en zijn stippellijn, maar los van het volgende antwoord.
    """
    steps = [step for step in steps if step]
    if not steps:
        return

    parts = []
    next_id = 10
    for step in steps:
        xml, next_id = _click_par(step, next_id)
        parts.append(xml)

    timing_xml = f"""<p:timing {nsdecls('p')}>
      <p:tnLst>
        <p:par>
          <p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">
            <p:childTnLst>
              <p:seq concurrent="1" nextAc="seek">
                <p:cTn id="2" dur="indefinite" nodeType="mainSeq">
                  <p:childTnLst>{"".join(parts)}</p:childTnLst>
                </p:cTn>
                <p:prevCondLst>
                  <p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>
                </p:prevCondLst>
                <p:nextCondLst>
                  <p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>
                </p:nextCondLst>
              </p:seq>
            </p:childTnLst>
          </p:cTn>
        </p:par>
      </p:tnLst>
    </p:timing>"""

    timing = etree.fromstring(timing_xml)
    # Volgorde in p:sld is vast: cSld, clrMapOvr, transition, timing.
    slide._element.append(timing)


# ---------------------------------------------------------------------------
# Tekst
# ---------------------------------------------------------------------------


def textbox(
    slide,
    left: Emu,
    top: Emu,
    width: Emu,
    height: Emu,
    text: str,
    *,
    size: int,
    color: RGBColor,
    bold: bool = False,
    italic: bool = False,
    align=PP_ALIGN.LEFT,
    anchor=MSO_ANCHOR.TOP,
    font: str = FONT,
):
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.word_wrap = True
    frame.margin_left = 0
    frame.margin_right = 0
    frame.margin_top = 0
    frame.margin_bottom = 0
    frame.vertical_anchor = anchor

    paragraph = frame.paragraphs[0]
    paragraph.alignment = align
    paragraph.line_spacing = LINE_SPACING
    run = paragraph.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = font
    return box


def answer_box(slide, left: Emu, top: Emu, width: Emu, height: Emu, answer: str, alternatives: list[str]):
    """Antwoord in blauw vet cursief; alternatieven op dezelfde regel, niet vet."""
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.word_wrap = True
    frame.margin_left = 0
    frame.margin_right = 0
    frame.margin_top = 0
    frame.margin_bottom = 0

    paragraph = frame.paragraphs[0]
    paragraph.line_spacing = LINE_SPACING

    main = paragraph.add_run()
    main.text = answer
    main.font.size = Pt(PT_ANSWER)
    main.font.bold = True
    main.font.italic = True
    main.font.color.rgb = ANSWER_BLUE
    main.font.name = FONT

    if alternatives:
        extra = paragraph.add_run()
        extra.text = "  /  " + "  /  ".join(alternatives)
        extra.font.size = Pt(PT_ANSWER)
        extra.font.bold = False
        extra.font.italic = True
        extra.font.color.rgb = ANSWER_BLUE
        extra.font.name = FONT

    return box


def line(slide, left: Emu, top: Emu, width: Emu, color: RGBColor = GREY, thickness: float = 1.0):
    from pptx.enum.shapes import MSO_SHAPE

    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, Pt(thickness))
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def rect(slide, left: Emu, top: Emu, width: Emu, height: Emu, color: RGBColor):
    from pptx.enum.shapes import MSO_SHAPE

    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def estimate_lines(text: str, width_inches: float, size_pt: int) -> int:
    char_width_in = size_pt * CHAR_WIDTH_FACTOR / 72.0
    per_line = max(1, int(width_inches / char_width_in))
    return max(1, math.ceil(len(text) / per_line))


def line_height(size_pt: int) -> float:
    return size_pt * LINE_SPACING / 72.0


# ---------------------------------------------------------------------------
# Slide-onderdelen
# ---------------------------------------------------------------------------


@dataclass
class Deck:
    presentation: Presentation
    unit_label: str
    slide_count: int = 0
    animated_slides: list[str] = None

    def __post_init__(self):
        if self.animated_slides is None:
            self.animated_slides = []

    def blank(self):
        slide = self.presentation.slides.add_slide(self.presentation.slide_layouts[6])
        self.slide_count += 1
        return slide


def add_footer(deck: Deck, slide, page: int | None) -> None:
    textbox(
        slide,
        MARGIN,
        SLIDE_H - Inches(0.55),
        Inches(6.0),
        Inches(0.35),
        deck.unit_label.upper(),
        size=PT_FOOTER,
        color=GREY,
    )
    if page is not None:
        badge_w = Inches(0.85)
        rect(
            slide,
            SLIDE_W - MARGIN - badge_w,
            SLIDE_H - Inches(0.58),
            badge_w,
            Inches(0.4),
            PETROL,
        )
        textbox(
            slide,
            SLIDE_W - MARGIN - badge_w,
            SLIDE_H - Inches(0.50),
            badge_w,
            Inches(0.3),
            str(page),
            size=PT_FOOTER,
            color=WHITE,
            bold=True,
            align=PP_ALIGN.CENTER,
        )


def add_header(slide, number: str, label: str, page: int) -> None:
    number_w = Inches(2.6) if len(number) > 3 else Inches(1.4)
    textbox(
        slide, MARGIN, Inches(0.3), number_w, Inches(0.9), number,
        size=PT_NUMBER, color=PETROL, bold=True,
    )
    textbox(
        slide,
        MARGIN + number_w + Inches(0.15),
        Inches(0.42),
        CONTENT_W - number_w - Inches(1.9),
        Inches(0.85),
        label,
        size=PT_TITLE,
        color=PETROL,
        bold=True,
    )
    textbox(
        slide,
        SLIDE_W - MARGIN - Inches(1.6),
        Inches(0.45),
        Inches(1.6),
        Inches(0.4),
        f"blz. {page}",
        size=18,
        color=GREY,
        align=PP_ALIGN.RIGHT,
    )
    line(slide, MARGIN, Inches(1.38), CONTENT_W)


def add_click_hint(slide) -> None:
    textbox(
        slide,
        SLIDE_W - MARGIN - Inches(2.4),
        Inches(6.72),
        Inches(2.4),
        Inches(0.32),
        "klik ▸",
        size=PT_FOOTER,
        color=GREY,
        align=PP_ALIGN.RIGHT,
    )


# ---------------------------------------------------------------------------
# Slidetypes
# ---------------------------------------------------------------------------


def add_title_slide(deck: Deck, key: dict[str, Any]) -> None:
    slide = deck.blank()
    rect(slide, Emu(0), Emu(0), SLIDE_W, SLIDE_H, PETROL)
    textbox(
        slide, MARGIN, Inches(2.6), CONTENT_W, Inches(1.2),
        key["title"], size=44, color=WHITE, bold=True,
    )
    textbox(
        slide, MARGIN, Inches(3.9), CONTENT_W, Inches(0.7),
        "Oplossingen", size=30, color=WHITE,
    )
    textbox(
        slide, MARGIN, SLIDE_H - Inches(0.75), CONTENT_W, Inches(0.4),
        "Leerkrachtmateriaal — eigen lesgroepen", size=14, color=WHITE,
    )


def add_part_slide(deck: Deck, part: str) -> None:
    slide = deck.blank()
    colour = DARKRED if part.startswith("Check this out") else PETROL
    rect(slide, Emu(0), Emu(0), SLIDE_W, SLIDE_H, colour)
    textbox(
        slide, MARGIN, Inches(3.1), CONTENT_W, Inches(1.3),
        part, size=40, color=WHITE, bold=True,
    )


def add_open_slide(deck: Deck, exercise: dict[str, Any]) -> None:
    """Open opdracht: alles meteen zichtbaar, geen animatie."""
    slide = deck.blank()
    add_header(slide, exercise["number"], exercise.get("label_nl", ""), exercise["page"])

    badge_w = Inches(3.5)
    rect(slide, MARGIN, BODY_TOP, badge_w, Inches(0.6), ORANGE)
    textbox(
        slide, MARGIN + Inches(0.2), BODY_TOP + Inches(0.08), badge_w - Inches(0.4), Inches(0.36),
        "OPEN OPDRACHT", size=24, color=WHITE, bold=True,
    )

    top = BODY_TOP + Inches(0.85)
    if exercise.get("instruction_nl"):
        height = Inches(estimate_lines(exercise["instruction_nl"], 12.1, PT_ITEM) * line_height(PT_ITEM) + 0.1)
        textbox(slide, MARGIN, top, CONTENT_W, height, exercise["instruction_nl"], size=PT_ITEM, color=BLACK)
        top = top + height + Inches(0.25)

    textbox(slide, MARGIN, top, CONTENT_W, Inches(0.45), "Waar op letten:", size=PT_ITEM, color=PETROL, bold=True)
    top = top + Inches(0.55)

    note = exercise.get("note_nl", "")
    height = Inches(estimate_lines(note, 12.1, PT_ITEM) * line_height(PT_ITEM) + 0.2)
    textbox(slide, MARGIN, top, CONTENT_W, height, note, size=PT_ITEM, color=BLACK)

    add_footer(deck, slide, exercise["page"])


# De schatting van de regelterugloop is een benadering, en de kleine afrondingen
# per rij stapelen op bij lange oefeningen. Deze marge vangt die drift op.
PACK_SAFETY_INCHES = 0.65


def pack_items(items: list[dict[str, Any]], available_inches: float) -> list[list[dict[str, Any]]]:
    """Verdeelt items over slides zodat niets buiten de slide loopt."""
    available_inches -= PACK_SAFETY_INCHES
    pages: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    used = 0.0

    for item in items:
        prompt = item.get("note_nl")
        height = 0.0
        if prompt:
            height += estimate_lines(prompt, 10.4, PT_ITEM) * line_height(PT_ITEM)
        answer_text = item["answer"] + ("  /  ".join(item.get("alternatives", [])) or "")
        height += estimate_lines(answer_text, 10.0, PT_ANSWER) * line_height(PT_ANSWER)
        height += 0.22  # tussenruimte en stippellijn

        # Nooit meer dan 8 antwoordregels per slide, ook al past het.
        if current and (used + height > available_inches or len(current) >= 8):
            pages.append(current)
            current, used = [], 0.0
        current.append(item)
        used += height

    if current:
        pages.append(current)
    return balance_last_page(pages)


def balance_last_page(pages: list[list[Any]]) -> list[list[Any]]:
    """Voorkomt een slotslide met één eenzaam item.

    Gulzig vullen levert soms 4-5-1 op. Dat leest slordig; 4-4-2 niet.
    """
    guard = 0
    while len(pages) > 1 and len(pages[-1]) * 2 < len(pages[-2]) and len(pages[-2]) > 2:
        pages[-1].insert(0, pages[-2].pop())
        guard += 1
        if guard > 8:
            break
    return pages


def add_item_slide(
    deck: Deck,
    exercise: dict[str, Any],
    items: list[dict[str, Any]],
    continued: bool,
) -> None:
    slide = deck.blank()
    label = exercise.get("label_nl", "")
    if continued:
        label = f"{label} (vervolg)" if label else "(vervolg)"
    add_header(slide, exercise["number"], label, exercise["page"])

    top = BODY_TOP
    if exercise.get("instruction_nl") and not continued:
        height = Inches(estimate_lines(exercise["instruction_nl"], 12.1, PT_ITEM) * line_height(PT_ITEM) + 0.08)
        textbox(slide, MARGIN, top, CONTENT_W, height, exercise["instruction_nl"], size=22, color=GREY, italic=True)
        top = top + height + Inches(0.15)

    steps: list[list[int]] = []
    has_uncertain = False

    for item in items:
        number_w = Inches(1.5)
        prompt = item.get("note_nl")

        textbox(
            slide, MARGIN, top, number_w, Inches(0.5), item["number"],
            size=PT_ITEM, color=GREY, bold=True,
        )

        answer_left = MARGIN + number_w + ANSWER_INDENT
        answer_w = SLIDE_W - MARGIN - answer_left

        if prompt:
            prompt_h = Inches(estimate_lines(prompt, 10.4, PT_ITEM) * line_height(PT_ITEM) + 0.05)
            textbox(slide, MARGIN + number_w, top, answer_w + ANSWER_INDENT, prompt_h, prompt, size=PT_ITEM, color=BLACK)
            top = top + prompt_h

        answer_text = item["answer"]
        if item.get("uncertain"):
            answer_text = f"{answer_text}  ?"
            has_uncertain = True

        answer_h = Inches(
            estimate_lines(answer_text + "".join(item.get("alternatives", [])), 10.0, PT_ANSWER)
            * line_height(PT_ANSWER)
            + 0.08
        )
        box = answer_box(slide, answer_left, top, answer_w, answer_h, answer_text, item.get("alternatives", []))
        underline = line(slide, answer_left, top + answer_h + Inches(0.02), answer_w - Inches(0.3), GREY, 0.75)

        steps.append([box.shape_id, underline.shape_id])
        top = top + answer_h + Inches(0.22)

    if has_uncertain:
        # Naast de klik-hint, niet eronder: die staat rechts op dezelfde hoogte.
        textbox(
            slide, MARGIN, Inches(6.72), CONTENT_W - Inches(2.8), Inches(0.3),
            "?  Niet met zekerheid leesbaar in het digiboek.", size=14, color=GREY, italic=True,
        )

    add_click_hint(slide)
    add_footer(deck, slide, exercise["page"])
    add_click_reveal(slide, steps)
    deck.animated_slides.append(f"{exercise['number']}{' (vervolg)' if continued else ''}")


def table_row_height(row: list[str], widths: list[Emu]) -> float:
    lines = max(
        estimate_lines(str(cell), widths[index] / Inches(1) - 0.3, PT_TABLE)
        for index, cell in enumerate(row)
    )
    return lines * line_height(PT_TABLE) + 0.18


def table_column_widths(columns: int) -> tuple[list[Emu], list[Emu]]:
    first_w = CONTENT_W * (0.42 if columns > 2 else 0.46)
    other_w = (CONTENT_W - first_w) / (columns - 1)
    lefts = [MARGIN] + [MARGIN + first_w + other_w * index for index in range(columns - 1)]
    widths = [first_w] + [other_w] * (columns - 1)
    return lefts, widths


def pack_rows(rows: list[list[str]], widths: list[Emu], available_inches: float) -> list[list[list[str]]]:
    """Verdeelt tabelrijen over slides. Laat nooit een rij vallen."""
    available_inches -= PACK_SAFETY_INCHES
    pages: list[list[list[str]]] = []
    current: list[list[str]] = []
    used = 0.0

    for row in rows:
        height = table_row_height(row, widths)
        if current and used + height > available_inches:
            pages.append(current)
            current, used = [], 0.0
        current.append(row)
        used += height

    if current:
        pages.append(current)
    return balance_last_page(pages)


def add_table_slide(
    deck: Deck,
    exercise: dict[str, Any],
    rows: list[list[str]],
    continued: bool,
    row_offset: int,
) -> None:
    """Raster met een petrol kopregel; per klik verschijnt één rij.

    Bewust opgebouwd uit losse vormen en niet als OOXML-tabel: een echte tabel
    is in PowerPoint niet per rij te animeren, en het onthullen per rij weegt
    hier zwaarder dan de tabelstructuur.
    """
    slide = deck.blank()
    label = exercise.get("label_nl", "")
    if continued:
        label = f"{label} (vervolg)" if label else "(vervolg)"
    add_header(slide, exercise["number"], label, exercise["page"])

    table = exercise["table"]
    headers = table["headers"]
    columns = len(headers)

    lefts, widths = table_column_widths(columns)

    top = BODY_TOP
    header_h = Inches(0.55)
    rect(slide, MARGIN, top, CONTENT_W, header_h, PETROL)
    for index, header in enumerate(headers):
        textbox(
            slide, lefts[index] + Inches(0.12), top + Inches(0.1), widths[index] - Inches(0.24), Inches(0.4),
            header, size=PT_TABLE, color=WHITE, bold=True,
        )
    top = top + header_h

    steps: list[list[int]] = []

    for offset, row in enumerate(rows):
        row_index = row_offset + offset
        row_h = Inches(table_row_height(row, widths))

        shapes: list[int] = []
        if row_index % 2 == 1:
            band = rect(slide, MARGIN, top, CONTENT_W, row_h, LIME_FILL)
            shapes.append(band.shape_id)

        for index, cell in enumerate(row):
            is_answer = index > 0
            box = textbox(
                slide,
                lefts[index] + Inches(0.12),
                top + Inches(0.08),
                widths[index] - Inches(0.24),
                row_h - Inches(0.12),
                str(cell),
                size=PT_TABLE,
                color=ANSWER_BLUE if is_answer else BLACK,
                bold=is_answer,
                italic=is_answer,
            )
            if is_answer:
                shapes.append(box.shape_id)

        steps.append(shapes)
        top = top + row_h

    add_click_hint(slide)
    add_footer(deck, slide, exercise["page"])
    add_click_reveal(slide, steps)
    deck.animated_slides.append(f"{exercise['number']}{' (vervolg)' if continued else ''}")


# ---------------------------------------------------------------------------
# Bouw
# ---------------------------------------------------------------------------


def build(key: dict[str, Any], out_path: Path) -> Deck:
    presentation = Presentation()
    presentation.slide_width = SLIDE_W
    presentation.slide_height = SLIDE_H

    # "New Ace 3 — Unit 1 First day" -> "UNIT 1 FIRST DAY"
    unit_label = key["title"].split("—")[-1].strip() if "—" in key["title"] else key["title"]
    deck = Deck(presentation=presentation, unit_label=unit_label.replace("Unit 1 ", "Unit 1 • "))

    add_title_slide(deck, key)

    current_part = None
    available = (BODY_BOTTOM - BODY_TOP) / Inches(1)

    for exercise in key["exercises"]:
        part = exercise.get("part")
        if part and part != current_part:
            current_part = part
            add_part_slide(deck, part)

        if exercise.get("open_ended"):
            add_open_slide(deck, exercise)
        elif exercise.get("table"):
            _, widths = table_column_widths(len(exercise["table"]["headers"]))
            # De kopregel staat op elke vervolgslide opnieuw, dus die hoogte
            # gaat er per slide af.
            row_pages = pack_rows(exercise["table"]["rows"], widths, available - 0.55)
            offset = 0
            for index, page in enumerate(row_pages):
                add_table_slide(deck, exercise, page, continued=index > 0, row_offset=offset)
                offset += len(page)
        else:
            # De instructie en de onzekerheidsvoetnoot eten van dezelfde hoogte
            # als de antwoorden, dus die gaan er eerst af.
            reserved = 0.0
            instruction = exercise.get("instruction_nl")
            if instruction:
                reserved += estimate_lines(instruction, 12.1, 22) * line_height(22) + 0.23
            if any(item.get("uncertain") for item in exercise["items"]):
                reserved += 0.35

            pages = pack_items(exercise["items"], available - reserved)
            for index, page in enumerate(pages):
                add_item_slide(deck, exercise, page, continued=index > 0)

    ensure_dirs(out_path.parent)
    presentation.save(out_path)
    return deck


def main() -> int:
    parser = argparse.ArgumentParser(description="Bouw het correctiedeck bij de boekoefeningen.")
    parser.add_argument("--theme", required=True)
    parser.add_argument("--out", help="Uitvoerpad; standaard dist/pptx/<boek>/<thema>-oplossingen.pptx")
    args = parser.parse_args()

    config = Config.load()
    scope = config.assert_may_use_source_answer_keys()

    path = ROOT / "data" / "answers" / f"{args.theme}.json"
    if not path.exists():
        raise ProjectError(f"Geen antwoordsleutel voor {args.theme}: {relative(path)}")

    key = json.loads(path.read_text(encoding="utf-8"))
    if key.get("teacher_only") is not True:
        raise ProjectError("teacher_only moet true zijn.")
    if key.get("use_scope") != scope:
        raise ProjectError(
            f"De sleutel is vastgelegd voor {key.get('use_scope')!r}, "
            f"de configuratie bevestigt {scope!r}."
        )

    out_path = Path(args.out) if args.out else ROOT / "dist" / "pptx" / key["book_id"] / f"{args.theme}-oplossingen.pptx"
    deck = build(key, out_path)

    print(f"Gebouwd: {relative(out_path)}")
    print(f"Slides: {deck.slide_count}")
    print(f"Oefeningen: {len(key['exercises'])}")
    print(f"Slides met klik-animatie: {len(deck.animated_slides)}")
    print(f"Gebruiksbereik: {scope}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProjectError as exc:
        print(f"Fout: {exc}", file=sys.stderr)
        raise SystemExit(2)
