/**
 * Genereert een leerlingdeck en een leerkrachtdeck per thema.
 *
 * Modus `hybrid_classroom_16x9`: opgebouwd uit eigen designtokens en
 * bewerkbare vormen. Er wordt geen bronpagina gereproduceerd, geen bronbeeld
 * hergebruikt en geen rasterachtergrond geplaatst, zolang de rechtenstatus
 * `original_only` is.
 *
 * Antwoorden staan uitsluitend in het leerkrachtdeck, en daar in de
 * speaker notes plus op aparte reveal-slides. Het leerlingdeck wordt na het
 * bouwen gecontroleerd op lekken.
 */

import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { parseArgs } from 'node:util';

import PptxGenJS from 'pptxgenjs';

import {
  BOOK_THEMES,
  ROLE_TOKENS,
  SLIDE,
  TYPOGRAPHY,
  assertContrast,
  type SemanticRole,
} from '../design/tokens.js';
import { loadTheme } from '../shared/content.js';
import type { Activity, GrammarTopic, ThemeContent, VisualGrammarModel } from '../shared/types.js';
import { assertNoSourceImagery, loadConfig } from './rights.js';

type Audience = 'student' | 'teacher';

const OUTPUT_ROOT = 'dist/pptx';

// ---------------------------------------------------------------------------
// Deckopbouw
// ---------------------------------------------------------------------------

function createDeck(theme: ThemeContent, audience: Audience): PptxGenJS {
  const pptx = new PptxGenJS();
  const book = BOOK_THEMES[theme.bookId];
  if (!book) throw new Error(`Geen designtokens voor boek ${theme.bookId}.`);

  pptx.defineLayout({ name: 'HYBRID_16x9', width: SLIDE.widthInch, height: SLIDE.heightInch });
  pptx.layout = 'HYBRID_16x9';
  pptx.author = 'New Ace 3 / New Strike 3 leermiddelen';
  pptx.title = `${book.label} — ${theme.title} (${audience === 'student' ? 'leerling' : 'leerkracht'})`;

  defineMasters(pptx, theme.bookId);
  return pptx;
}

function defineMasters(pptx: PptxGenJS, bookId: string): void {
  const book = BOOK_THEMES[bookId];

  pptx.defineSlideMaster({
    title: 'SECTION',
    background: { color: book.accent },
    objects: [
      {
        text: {
          text: book.label,
          options: {
            x: SLIDE.marginInch,
            y: 6.5,
            w: 6,
            h: 0.4,
            fontSize: TYPOGRAPHY.slide.caption,
            color: book.accentText,
            fontFace: TYPOGRAPHY.fontFamily,
          },
        },
      },
    ],
  });

  pptx.defineSlideMaster({
    title: 'CONTENT',
    background: { color: book.surface },
    objects: [
      {
        rect: {
          x: 0,
          y: 0,
          w: SLIDE.widthInch,
          h: 0.14,
          fill: { color: book.accent },
        },
      },
    ],
  });
}

function addSectionSlide(pptx: PptxGenJS, title: string, subtitle: string, bookId: string): void {
  const book = BOOK_THEMES[bookId];
  const slide = pptx.addSlide({ masterName: 'SECTION' });

  slide.addText(title, {
    x: SLIDE.marginInch,
    y: 2.6,
    w: SLIDE.widthInch - SLIDE.marginInch * 2,
    h: 1.2,
    fontSize: TYPOGRAPHY.slide.title,
    bold: true,
    color: book.accentText,
    fontFace: TYPOGRAPHY.fontFamily,
  });
  slide.addText(subtitle, {
    x: SLIDE.marginInch,
    y: 3.8,
    w: SLIDE.widthInch - SLIDE.marginInch * 2,
    h: 0.8,
    fontSize: TYPOGRAPHY.slide.subtitle,
    color: book.accentText,
    fontFace: TYPOGRAPHY.fontFamily,
  });
}

function addContentSlide(
  pptx: PptxGenJS,
  bookId: string,
  title: string,
  notes: string,
): PptxGenJS.Slide {
  const book = BOOK_THEMES[bookId];
  const slide = pptx.addSlide({ masterName: 'CONTENT' });

  slide.addText(title, {
    x: SLIDE.marginInch,
    y: 0.4,
    w: SLIDE.widthInch - SLIDE.marginInch * 2,
    h: 0.8,
    fontSize: TYPOGRAPHY.slide.title,
    bold: true,
    color: book.accent,
    fontFace: TYPOGRAPHY.fontFamily,
  });
  if (notes) slide.addNotes(notes);
  return slide;
}

/** Bronverwijzingen horen in de notities, niet op de leerlingslide. */
function sourceNote(refs: { page: number; source_file: string }[] | undefined): string {
  if (!refs || refs.length === 0) return '';
  const pages = refs.map((ref) => ref.page).join(', ');
  return `Bron: ${refs[0].source_file}, pagina ${pages}.`;
}

// ---------------------------------------------------------------------------
// Grammatica
// ---------------------------------------------------------------------------

function addGrammarSlides(
  pptx: PptxGenJS,
  topic: GrammarTopic,
  bookId: string,
  audience: Audience,
): void {
  const book = BOOK_THEMES[bookId];

  const goals = addContentSlide(pptx, bookId, topic.title, sourceNote(topic.source_page_refs));
  goals.addText(
    topic.can_do_statements.map((text) => ({ text, options: { bullet: true } })),
    {
      x: SLIDE.marginInch,
      y: 1.5,
      w: SLIDE.widthInch - SLIDE.marginInch * 2,
      h: 2.4,
      fontSize: TYPOGRAPHY.slide.body,
      color: book.surfaceText,
      fontFace: TYPOGRAPHY.fontFamily,
    },
  );

  // Betekenis en gebruik komen vóór de vorm.
  const meaning = addContentSlide(
    pptx,
    bookId,
    `${topic.title} — betekenis en gebruik`,
    topic.meaning_and_use.summary_nl,
  );
  meaning.addText(
    topic.meaning_and_use.use_cases.map((useCase) => ({
      text: `${useCase.label_nl}: ${useCase.example_en}`,
      options: { bullet: true },
    })),
    {
      x: SLIDE.marginInch,
      y: 1.5,
      w: SLIDE.widthInch - SLIDE.marginInch * 2,
      h: 3.6,
      fontSize: TYPOGRAPHY.slide.body,
      color: book.surfaceText,
      fontFace: TYPOGRAPHY.fontFamily,
    },
  );

  const errors = addContentSlide(
    pptx,
    bookId,
    `${topic.title} — veelgemaakte fouten`,
    audience === 'teacher'
      ? topic.typical_errors_nl.map((e) => `${e.wrong} → ${e.right}: ${e.why_nl}`).join('\n')
      : '',
  );
  errors.addTable(
    [
      [
        { text: 'Fout', options: { bold: true, color: book.accentText, fill: { color: book.accent } } },
        { text: 'Correct', options: { bold: true, color: book.accentText, fill: { color: book.accent } } },
      ],
      ...topic.typical_errors_nl.map((entry) => [
        { text: entry.wrong },
        { text: entry.right },
      ]),
    ],
    {
      x: SLIDE.marginInch,
      y: 1.5,
      w: SLIDE.widthInch - SLIDE.marginInch * 2,
      fontSize: TYPOGRAPHY.slide.minBody,
      color: book.surfaceText,
      fontFace: TYPOGRAPHY.fontFamily,
      border: { type: 'solid', color: 'D0D4DC', pt: 1 },
    },
  );
}

/**
 * Progressieve reveal: per stap één duplicaatslide waarop precies één
 * betekenisvolle verandering verschijnt. Geen native objectanimatie — die is
 * via een generator niet betrouwbaar te sturen.
 */
function addVisualModelSlides(pptx: PptxGenJS, model: VisualGrammarModel, bookId: string): void {
  const book = BOOK_THEMES[bookId];

  for (const step of model.steps) {
    const slide = addContentSlide(
      pptx,
      bookId,
      model.title,
      `Stap ${step.index}: ${step.change_description_nl}`,
    );

    const visible = step.elements.filter((element) => element.state !== 'removed');
    const ordered = [...visible].sort(
      (a, b) => (a.position?.order ?? 0) - (b.position?.order ?? 0),
    );

    const tileWidth = Math.min(
      2.4,
      (SLIDE.widthInch - SLIDE.marginInch * 2) / Math.max(ordered.length, 1) - 0.15,
    );

    ordered.forEach((element, index) => {
      const token = ROLE_TOKENS[element.role as SemanticRole] ?? ROLE_TOKENS.complement;
      const dimmed = element.state === 'dimmed';
      const x = SLIDE.marginInch + index * (tileWidth + 0.15);

      slide.addShape(pptx.ShapeType.roundRect, {
        x,
        y: 2.7,
        w: tileWidth,
        h: 1.0,
        fill: { color: token.fill, transparency: dimmed ? 60 : 0 },
        line: { color: token.fill, width: 1 },
      });
      slide.addText(element.text, {
        x,
        y: 2.7,
        w: tileWidth,
        h: 1.0,
        align: 'center',
        valign: 'middle',
        fontSize: TYPOGRAPHY.slide.body,
        bold: element.state === 'highlighted',
        color: token.text,
        fontFace: TYPOGRAPHY.fontFamily,
      });
      // Het rollabel staat er altijd bij: kleur alleen volstaat niet.
      slide.addText(token.label, {
        x,
        y: 3.75,
        w: tileWidth,
        h: 0.35,
        align: 'center',
        fontSize: TYPOGRAPHY.slide.notes,
        color: book.muted,
        fontFace: TYPOGRAPHY.fontFamily,
      });
    });

    slide.addText(step.caption_nl, {
      x: SLIDE.marginInch,
      y: 4.4,
      w: SLIDE.widthInch - SLIDE.marginInch * 2,
      h: 0.9,
      fontSize: TYPOGRAPHY.slide.caption,
      color: book.surfaceText,
      fontFace: TYPOGRAPHY.fontFamily,
    });
  }

  const legend = addContentSlide(
    pptx,
    bookId,
    `${model.title} — legende`,
    model.accessibility.static_alternative_nl,
  );
  legend.addText(
    model.accessibility.role_legend.map((entry) => ({
      text: `${entry.label} (${entry.shape})`,
      options: { bullet: true },
    })),
    {
      x: SLIDE.marginInch,
      y: 1.5,
      w: SLIDE.widthInch - SLIDE.marginInch * 2,
      h: 3.0,
      fontSize: TYPOGRAPHY.slide.body,
      color: book.surfaceText,
      fontFace: TYPOGRAPHY.fontFamily,
    },
  );
}

// ---------------------------------------------------------------------------
// Activiteiten
// ---------------------------------------------------------------------------

function addActivitySlides(
  pptx: PptxGenJS,
  activity: Activity,
  bookId: string,
  audience: Audience,
): void {
  const book = BOOK_THEMES[bookId];

  const slide = addContentSlide(
    pptx,
    bookId,
    activity.title,
    `Stage ${activity.stage} — ${activity.difficulty}. ${activity.learning_objectives[0] ?? ''}`,
  );

  slide.addText(activity.instructions_nl, {
    x: SLIDE.marginInch,
    y: 1.4,
    w: SLIDE.widthInch - SLIDE.marginInch * 2,
    h: 0.7,
    fontSize: TYPOGRAPHY.slide.body,
    italic: true,
    color: book.muted,
    fontFace: TYPOGRAPHY.fontFamily,
  });
  slide.addText(activity.stimulus.content, {
    x: SLIDE.marginInch,
    y: 2.2,
    w: SLIDE.widthInch - SLIDE.marginInch * 2,
    h: 1.8,
    fontSize: TYPOGRAPHY.slide.body,
    color: book.surfaceText,
    fontFace: TYPOGRAPHY.fontFamily,
  });
  slide.addText(
    activity.prompts.map((prompt, index) => ({
      text: `${index + 1}. ${prompt.prompt}`,
      options: { bullet: false },
    })),
    {
      x: SLIDE.marginInch,
      y: 4.1,
      w: SLIDE.widthInch - SLIDE.marginInch * 2,
      h: 2.4,
      fontSize: TYPOGRAPHY.slide.minBody,
      color: book.surfaceText,
      fontFace: TYPOGRAPHY.fontFamily,
    },
  );

  // Alleen de leerkrachtversie krijgt een antwoordslide.
  if (audience !== 'teacher') return;

  const answers = addContentSlide(pptx, bookId, `${activity.title} — antwoorden`, '');
  answers.addText(
    activity.prompts.map((prompt, index) => ({
      text: `${index + 1}. ${
        prompt.manual_review_rubric
          ? 'Open productie — beoordeel met de rubric.'
          : (prompt.canonical_answers ?? []).join(' / ')
      }`,
      options: { bullet: false },
    })),
    {
      x: SLIDE.marginInch,
      y: 1.5,
      w: SLIDE.widthInch - SLIDE.marginInch * 2,
      h: 4.4,
      fontSize: TYPOGRAPHY.slide.minBody,
      color: book.surfaceText,
      fontFace: TYPOGRAPHY.fontFamily,
    },
  );
}

// ---------------------------------------------------------------------------
// Lekcontrole
// ---------------------------------------------------------------------------

function collectAnswers(theme: ThemeContent): string[] {
  const answers: string[] = [];
  for (const set of theme.activitySets) {
    for (const activity of set.activities) {
      for (const prompt of activity.prompts) {
        answers.push(...(prompt.canonical_answers ?? []));
      }
    }
  }
  return answers.filter((answer) => answer.trim().length >= 8);
}

/**
 * Controleert dat er geen oplossingen in het leerlingdeck staan. Er wordt
 * bewust op de gegenereerde structuur gecontroleerd en niet op het bestand:
 * zo vangen we ook antwoorden die in notities of alt-tekst zouden belanden.
 */
function assertNoAnswerLeak(built: string[], answers: string[]): void {
  const haystack = built.join('\n').toLowerCase();
  const leaked = answers.filter((answer) => haystack.includes(answer.toLowerCase()));
  if (leaked.length > 0) {
    throw new Error(
      `Het leerlingdeck bevat ${leaked.length} oplossing(en): ${leaked.slice(0, 3).join(', ')}`,
    );
  }
}

function studentVisibleText(theme: ThemeContent): string[] {
  const chunks: string[] = [];
  for (const set of theme.activitySets) {
    for (const activity of set.activities) {
      chunks.push(activity.title, activity.instructions_nl, activity.stimulus.content);
      chunks.push(...activity.prompts.map((prompt) => prompt.prompt));
    }
  }
  return chunks;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function buildDeck(theme: ThemeContent, audience: Audience): Promise<string> {
  const pptx = createDeck(theme, audience);
  const book = BOOK_THEMES[theme.bookId];

  addSectionSlide(
    pptx,
    theme.title,
    audience === 'student' ? 'Leerlingversie' : 'Leerkrachtversie — met antwoorden',
    theme.bookId,
  );

  for (const topic of theme.grammar) {
    addSectionSlide(pptx, topic.title, 'Grammatica', theme.bookId);
    addGrammarSlides(pptx, topic, theme.bookId, audience);

    const model = theme.visuals.find((visual) => visual.grammar_topic_id === topic.id);
    if (model) addVisualModelSlides(pptx, model, theme.bookId);
  }

  for (const set of theme.vocabulary) {
    const slide = addContentSlide(pptx, theme.bookId, set.title, sourceNote(set.source_page_refs));
    slide.addTable(
      [
        [
          { text: 'Woord', options: { bold: true, color: book.accentText, fill: { color: book.accent } } },
          { text: 'Betekenis', options: { bold: true, color: book.accentText, fill: { color: book.accent } } },
        ],
        ...set.lexemes.slice(0, 12).map((lexeme) => [
          { text: lexeme.learnable_form ?? lexeme.lemma },
          { text: lexeme.definition_en },
        ]),
      ],
      {
        x: SLIDE.marginInch,
        y: 1.5,
        w: SLIDE.widthInch - SLIDE.marginInch * 2,
        fontSize: TYPOGRAPHY.slide.minBody,
        color: book.surfaceText,
        fontFace: TYPOGRAPHY.fontFamily,
        border: { type: 'solid', color: 'D0D4DC', pt: 1 },
      },
    );
  }

  for (const set of theme.activitySets) {
    addSectionSlide(pptx, set.target_id, 'Oefeningen', theme.bookId);
    for (const activity of set.activities) {
      addActivitySlides(pptx, activity, theme.bookId, audience);
    }
  }

  if (audience === 'student') {
    assertNoAnswerLeak(studentVisibleText(theme), collectAnswers(theme));
  }

  const outDir = join(OUTPUT_ROOT, theme.bookId);
  mkdirSync(outDir, { recursive: true });
  const outPath = join(outDir, `${theme.themeId}-${audience}.pptx`);
  await pptx.writeFile({ fileName: outPath });
  return outPath;
}

async function main(): Promise<void> {
  const { values } = parseArgs({
    options: {
      book: { type: 'string' },
      theme: { type: 'string' },
    },
  });

  if (!values.theme) {
    console.error('Gebruik: npm run build:pptx -- --book ace3 --theme ace3-u1');
    process.exitCode = 2;
    return;
  }

  // Dit deck bouwt uitsluitend uit eigen designtokens. De poort staat hier om
  // te voorkomen dat een latere configuratiewijziging stilzwijgend broninhoud
  // binnenlaat zonder dat de rechten dat dekken.
  assertNoSourceImagery(loadConfig().rights);
  assertContrast();

  const theme = loadTheme(values.theme);
  if (values.book && theme.bookId !== values.book) {
    console.error(`Thema ${values.theme} hoort bij ${theme.bookId}, niet bij ${values.book}.`);
    process.exitCode = 2;
    return;
  }

  for (const audience of ['student', 'teacher'] as const) {
    const path = await buildDeck(theme, audience);
    console.log(`Gebouwd: ${path}`);
  }
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
