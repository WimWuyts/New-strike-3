/**
 * Bundelt de content tijdens de build.
 *
 * Bewust geen fetch: zo werkt de app ook zonder webserver en zonder netwerk,
 * en is een single-file export per thema mogelijk.
 */

import type { ActivitySet, GrammarTopic, VisualGrammarModel, VocabularySet } from '../shared/types.js';

interface CatalogTheme {
  id: string;
  book_id: string;
  unit: number;
  title: string;
  cefr: string;
}

export interface LoadedTheme {
  id: string;
  bookId: string;
  unit: number;
  title: string;
  cefr: string;
  grammar: GrammarTopic[];
  vocabulary: VocabularySet[];
  visuals: VisualGrammarModel[];
  activitySets: ActivitySet[];
}

export interface LoadedBook {
  id: string;
  label: string;
  themes: LoadedTheme[];
}

const BOOK_LABELS: Record<string, string> = {
  ace3: 'New Ace 3',
  strike3: 'New Strike 3',
};

const catalogModules = import.meta.glob<CatalogTheme>('../../data/catalog/*.json', {
  eager: true,
  import: 'default',
});
const grammarModules = import.meta.glob<GrammarTopic>('../../data/content/*/grammar/*.json', {
  eager: true,
  import: 'default',
});
const vocabularyModules = import.meta.glob<VocabularySet>('../../data/content/*/vocabulary/*.json', {
  eager: true,
  import: 'default',
});
const visualModules = import.meta.glob<VisualGrammarModel>('../../data/content/*/visuals/*.json', {
  eager: true,
  import: 'default',
});
const activityModules = import.meta.glob<ActivitySet>('../../data/content/*/activities/*.json', {
  eager: true,
  import: 'default',
});

function themeIdFromPath(path: string): string {
  return path.split('/data/content/')[1]?.split('/')[0] ?? '';
}

function collect<T>(modules: Record<string, T>): Map<string, T[]> {
  const byTheme = new Map<string, T[]>();
  for (const [path, value] of Object.entries(modules)) {
    // Blueprints zijn planningsbestanden, geen leerinhoud.
    if (path.endsWith('.blueprint.json')) continue;
    const themeId = themeIdFromPath(path);
    if (!themeId) continue;
    const bucket = byTheme.get(themeId) ?? [];
    bucket.push(value);
    byTheme.set(themeId, bucket);
  }
  return byTheme;
}

export function loadBooks(): LoadedBook[] {
  const grammar = collect(grammarModules);
  const vocabulary = collect(vocabularyModules);
  const visuals = collect(visualModules);
  const activities = collect(activityModules);

  const themes: LoadedTheme[] = [];
  for (const [path, catalog] of Object.entries(catalogModules)) {
    if (path.endsWith('curriculum-map.json')) continue;
    if (!catalog?.id) continue;
    themes.push({
      id: catalog.id,
      bookId: catalog.book_id,
      unit: catalog.unit,
      title: catalog.title,
      cefr: catalog.cefr,
      grammar: grammar.get(catalog.id) ?? [],
      vocabulary: vocabulary.get(catalog.id) ?? [],
      visuals: visuals.get(catalog.id) ?? [],
      activitySets: activities.get(catalog.id) ?? [],
    });
  }

  const books = new Map<string, LoadedBook>();
  for (const theme of themes.sort((a, b) => a.unit - b.unit)) {
    const book = books.get(theme.bookId) ?? {
      id: theme.bookId,
      label: BOOK_LABELS[theme.bookId] ?? theme.bookId,
      themes: [],
    };
    book.themes.push(theme);
    books.set(theme.bookId, book);
  }

  return [...books.values()].sort((a, b) => a.id.localeCompare(b.id));
}
