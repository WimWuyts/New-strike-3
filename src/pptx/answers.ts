/**
 * Correctiedeck bij de oefeningen van het handboek.
 *
 * Dit deck bevat uitgeversinhoud en bestaat alleen onder een vastgelegde
 * rechtenbevestiging. Het is leerkrachtmateriaal: er is geen leerlingvariant,
 * en de webbuild leest `data/answers/` niet.
 *
 * Didactisch punt van dit deck: antwoorden verschijnen één voor één. Een
 * volledige sleutel op één slide leest niemand mee; item per item onthullen
 * houdt de klas bij de les.
 */

import { existsSync, mkdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { parseArgs } from 'node:util';

import PptxGenJS from 'pptxgenjs';

import { BOOK_THEMES, SLIDE, TYPOGRAPHY, assertContrast } from '../design/tokens.js';
import {
  assertMayUseSourceAnswerKeys,
  loadConfig,
  type AnswerDeckConfig,
  type UseScope,
} from './rights.js';

const ANSWERS_DIR = 'data/answers';
const OUTPUT_ROOT = 'dist/pptx';

interface AnswerItem {
  number: string;
  answer: string;
  alternatives?: string[];
  note_nl?: string;
  uncertain?: boolean;
}

interface Exercise {
  id: string;
  number: string;
  label_nl?: string;
  page: number;
  section?: string;
  instruction_nl?: string;
  note_nl?: string;
  open_ended?: boolean;
  items: AnswerItem[];
}

interface AnswerKey {
  id: string;
  book_id: string;
  theme_id: string;
  title: string;
  provenance: 'source_core';
  rights_status: 'licensed_confirmed';
  use_scope: UseScope;
  teacher_only: true;
  derivation: string;
  derivation_note_nl?: string;
  source_page_offset?: number;
  exercises: Exercise[];
}

const SECTION_LABELS: Record<string, string> = {
  theme_opener: 'Opener',
  vocabulary: 'Woordenschat',
  grammar: 'Grammatica',
  reading: 'Reading',
  listening: 'Listening',
  speaking: 'Speaking',
  writing: 'Writing',
  exercises: 'Oefeningen',
  review: 'Test yourself',
  reference: 'Naslag',
  unknown: 'Overig',
};

// ---------------------------------------------------------------------------
// Laden en controleren
// ---------------------------------------------------------------------------

function loadAnswerKey(themeId: string): AnswerKey {
  const path = join(ANSWERS_DIR, `${themeId}.json`);
  if (!existsSync(path)) {
    throw new Error(
      `Geen antwoordsleutel voor ${themeId} in ${path}.\n` +
        'Lever eerst de oplossingen per oefening aan.',
    );
  }
  const key = JSON.parse(readFileSync(path, 'utf-8')) as AnswerKey;

  // Het schema dekt dit ook, maar deze twee horen nooit stilzwijgend te falen.
  if (key.teacher_only !== true) {
    throw new Error(`${path}: teacher_only moet true zijn.`);
  }
  if (key.provenance !== 'source_core') {
    throw new Error(`${path}: een antwoordsleutel is altijd source_core.`);
  }
  return key;
}

// ---------------------------------------------------------------------------
// Slides
// ---------------------------------------------------------------------------

function chunk<T>(items: T[], size: number): T[][] {
  const pages: T[][] = [];
  for (let index = 0; index < items.length; index += size) {
    pages.push(items.slice(index, index + size));
  }
  return pages;
}

function exerciseHeading(exercise: Exercise): string {
  const label = exercise.label_nl ? ` — ${exercise.label_nl}` : '';
  return `Opdracht ${exercise.number}${label}`;
}

function addAnswerSlide(
  pptx: PptxGenJS,
  bookId: string,
  exercise: Exercise,
  visible: AnswerItem[],
  pageItems: AnswerItem[],
  deckConfig: AnswerDeckConfig,
): void {
  const book = BOOK_THEMES[bookId];
  const slide = pptx.addSlide({ masterName: 'ANSWERS' });
  const width = SLIDE.widthInch - SLIDE.marginInch * 2;

  slide.addText(exerciseHeading(exercise), {
    x: SLIDE.marginInch,
    y: 0.35,
    w: width - 1.6,
    h: 0.7,
    fontSize: TYPOGRAPHY.slide.title,
    bold: true,
    color: book.accent,
    fontFace: TYPOGRAPHY.fontFamily,
  });

  slide.addText(`blz. ${exercise.page}`, {
    x: SLIDE.widthInch - SLIDE.marginInch - 1.5,
    y: 0.42,
    w: 1.5,
    h: 0.5,
    align: 'right',
    fontSize: TYPOGRAPHY.slide.caption,
    color: book.muted,
    fontFace: TYPOGRAPHY.fontFamily,
  });

  if (exercise.instruction_nl) {
    slide.addText(exercise.instruction_nl, {
      x: SLIDE.marginInch,
      y: 1.05,
      w: width,
      h: 0.5,
      fontSize: TYPOGRAPHY.slide.caption,
      italic: true,
      color: book.muted,
      fontFace: TYPOGRAPHY.fontFamily,
    });
  }

  // Alle items van deze pagina staan er; wat nog niet onthuld is, blijft leeg.
  // Zo springt de lay-out niet bij elke klik.
  const rows = pageItems.map((item) => {
    const revealed = visible.includes(item);
    if (!revealed) {
      return [
        { text: `${item.number}.`, options: { color: book.muted, bold: true } },
        { text: '', options: {} },
      ];
    }
    const alternatives = item.alternatives?.length
      ? `  /  ${item.alternatives.join('  /  ')}`
      : '';
    const flag = item.uncertain ? '  ⚠' : '';
    return [
      { text: `${item.number}.`, options: { color: book.muted, bold: true } },
      {
        text: `${item.answer}${alternatives}${flag}`,
        options: { bold: true, color: book.surfaceText },
      },
    ];
  });

  slide.addTable(rows, {
    x: SLIDE.marginInch,
    y: exercise.instruction_nl ? 1.7 : 1.35,
    w: width,
    colW: [0.8, width - 0.8],
    fontSize: TYPOGRAPHY.slide.body,
    fontFace: TYPOGRAPHY.fontFamily,
    border: { type: 'none' },
    rowH: 0.42,
  });

  const notes: string[] = [];
  if (exercise.note_nl) notes.push(exercise.note_nl);
  for (const item of visible) {
    if (item.note_nl) notes.push(`${item.number}. ${item.note_nl}`);
    if (item.uncertain) {
      notes.push(`${item.number}. Onzeker gelezen uit de scan — controleer in het boek.`);
    }
  }
  if (notes.length > 0) slide.addNotes(notes.join('\n'));

  slide.addText(deckConfig.footer_nl, {
    x: SLIDE.marginInch,
    y: SLIDE.heightInch - 0.55,
    w: width,
    h: 0.35,
    fontSize: 12,
    color: book.muted,
    fontFace: TYPOGRAPHY.fontFamily,
  });
}

function addOpenEndedSlide(pptx: PptxGenJS, bookId: string, exercise: Exercise, deckConfig: AnswerDeckConfig): void {
  const book = BOOK_THEMES[bookId];
  const slide = pptx.addSlide({ masterName: 'ANSWERS' });
  const width = SLIDE.widthInch - SLIDE.marginInch * 2;

  slide.addText(exerciseHeading(exercise), {
    x: SLIDE.marginInch,
    y: 0.35,
    w: width,
    h: 0.7,
    fontSize: TYPOGRAPHY.slide.title,
    bold: true,
    color: book.accent,
    fontFace: TYPOGRAPHY.fontFamily,
  });
  slide.addText('Open opdracht — geen vast antwoord', {
    x: SLIDE.marginInch,
    y: 1.15,
    w: width,
    h: 0.5,
    fontSize: TYPOGRAPHY.slide.subtitle,
    italic: true,
    color: book.muted,
    fontFace: TYPOGRAPHY.fontFamily,
  });
  slide.addText(exercise.note_nl ?? '', {
    x: SLIDE.marginInch,
    y: 1.9,
    w: width,
    h: 3.0,
    fontSize: TYPOGRAPHY.slide.body,
    color: book.surfaceText,
    fontFace: TYPOGRAPHY.fontFamily,
  });
  slide.addText(deckConfig.footer_nl, {
    x: SLIDE.marginInch,
    y: SLIDE.heightInch - 0.55,
    w: width,
    h: 0.35,
    fontSize: 12,
    color: book.muted,
    fontFace: TYPOGRAPHY.fontFamily,
  });
}

function addSectionSlide(pptx: PptxGenJS, bookId: string, title: string): void {
  const book = BOOK_THEMES[bookId];
  const slide = pptx.addSlide({ masterName: 'ANSWERS_SECTION' });
  slide.addText(title, {
    x: SLIDE.marginInch,
    y: 3.0,
    w: SLIDE.widthInch - SLIDE.marginInch * 2,
    h: 1.2,
    fontSize: TYPOGRAPHY.slide.title,
    bold: true,
    color: book.accentText,
    fontFace: TYPOGRAPHY.fontFamily,
  });
}

function defineMasters(pptx: PptxGenJS, bookId: string): void {
  const book = BOOK_THEMES[bookId];
  pptx.defineSlideMaster({
    title: 'ANSWERS',
    background: { color: book.surface },
    objects: [{ rect: { x: 0, y: 0, w: SLIDE.widthInch, h: 0.14, fill: { color: book.accent } } }],
  });
  pptx.defineSlideMaster({
    title: 'ANSWERS_SECTION',
    background: { color: book.accent },
    objects: [],
  });
}

// ---------------------------------------------------------------------------
// Deck
// ---------------------------------------------------------------------------

async function buildAnswerDeck(key: AnswerKey, deckConfig: AnswerDeckConfig): Promise<string> {
  const pptx = new PptxGenJS();
  const book = BOOK_THEMES[key.book_id];
  if (!book) throw new Error(`Geen designtokens voor boek ${key.book_id}.`);

  pptx.defineLayout({ name: 'HYBRID_16x9', width: SLIDE.widthInch, height: SLIDE.heightInch });
  pptx.layout = 'HYBRID_16x9';
  pptx.title = `${key.title} — correctie`;
  pptx.author = 'Leerkrachtmateriaal';

  defineMasters(pptx, key.book_id);
  addSectionSlide(pptx, key.book_id, key.title);

  let currentSection: string | undefined;

  for (const exercise of key.exercises) {
    if (exercise.section && exercise.section !== currentSection) {
      currentSection = exercise.section;
      addSectionSlide(pptx, key.book_id, SECTION_LABELS[currentSection] ?? currentSection);
    }

    if (exercise.open_ended) {
      addOpenEndedSlide(pptx, key.book_id, exercise, deckConfig);
      continue;
    }

    for (const page of chunk(exercise.items, deckConfig.max_items_per_slide)) {
      if (deckConfig.reveal === 'per_exercise') {
        addAnswerSlide(pptx, key.book_id, exercise, page, page, deckConfig);
        continue;
      }
      // Progressief: per klik komt er één antwoord bij.
      for (let count = 1; count <= page.length; count += 1) {
        addAnswerSlide(pptx, key.book_id, exercise, page.slice(0, count), page, deckConfig);
      }
    }
  }

  const outDir = join(OUTPUT_ROOT, key.book_id);
  mkdirSync(outDir, { recursive: true });
  const outPath = join(outDir, `${key.theme_id}-answers.pptx`);
  await pptx.writeFile({ fileName: outPath });
  return outPath;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const { values } = parseArgs({ options: { theme: { type: 'string' } } });

  if (!values.theme) {
    console.error('Gebruik: npm run build:answers -- --theme ace3-u1');
    process.exitCode = 2;
    return;
  }

  const config = loadConfig();
  const deckConfig = config.pptx.answer_deck;
  if (!deckConfig?.enabled) {
    console.error('pptx.answer_deck.enabled staat uit.');
    process.exitCode = 2;
    return;
  }

  const scope = assertMayUseSourceAnswerKeys(config.rights);
  assertContrast();

  const key = loadAnswerKey(values.theme);
  if (key.use_scope !== scope) {
    throw new Error(
      `De sleutel is vastgelegd voor "${key.use_scope}", de configuratie bevestigt "${scope}".`,
    );
  }

  const path = await buildAnswerDeck(key, deckConfig);
  const slides = key.exercises.reduce((total, exercise) => {
    if (exercise.open_ended) return total + 1;
    const pages = chunk(exercise.items, deckConfig.max_items_per_slide);
    return (
      total +
      pages.reduce((sum, page) => sum + (deckConfig.reveal === 'progressive' ? page.length : 1), 0)
    );
  }, 0);

  console.log(`Gebouwd: ${path}`);
  console.log(`Oefeningen: ${key.exercises.length} — antwoordslides: ${slides}`);
  console.log(`Gebruiksbereik: ${scope}`);
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
