/** Laadt themacontent van schijf. Alleen voor Node-scripts, niet voor de browser. */

import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';

import type {
  ActivitySet,
  GrammarTopic,
  ThemeContent,
  VisualGrammarModel,
  VocabularySet,
} from './types.js';

export const CONTENT_ROOT = 'data/content';
export const CATALOG_ROOT = 'data/catalog';

function readJson<T>(path: string): T {
  return JSON.parse(readFileSync(path, 'utf-8')) as T;
}

function readDir<T>(dir: string, filter: (name: string) => boolean = () => true): T[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((name) => name.endsWith('.json') && filter(name))
    .sort()
    .map((name) => readJson<T>(join(dir, name)));
}

export function loadTheme(themeId: string, root = CONTENT_ROOT): ThemeContent {
  const dir = join(root, themeId);
  if (!existsSync(dir)) {
    throw new Error(
      `Geen content voor ${themeId} in ${dir}. Draai eerst: make plan THEME=${themeId}`,
    );
  }

  const grammar = readDir<GrammarTopic>(join(dir, 'grammar'));
  const vocabulary = readDir<VocabularySet>(join(dir, 'vocabulary'));
  const visuals = readDir<VisualGrammarModel>(join(dir, 'visuals'));
  const activitySets = readDir<ActivitySet>(
    join(dir, 'activities'),
    (name) => !name.endsWith('.blueprint.json'),
  );

  const catalogPath = join(CATALOG_ROOT, `${themeId}.json`);
  const catalog = existsSync(catalogPath)
    ? readJson<{ title: string; book_id: string }>(catalogPath)
    : undefined;

  const bookId = catalog?.book_id ?? grammar[0]?.book_id ?? vocabulary[0]?.book_id ?? '';
  if (!bookId) {
    throw new Error(`Kan het boek van ${themeId} niet bepalen. Ontbreekt de curriculumkaart?`);
  }

  return {
    themeId,
    bookId,
    title: catalog?.title ?? themeId,
    grammar,
    vocabulary,
    visuals,
    activitySets,
  };
}

export function listThemes(root = CONTENT_ROOT): string[] {
  if (!existsSync(root)) return [];
  return readdirSync(root, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();
}
