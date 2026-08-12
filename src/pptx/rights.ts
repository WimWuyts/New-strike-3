/**
 * Rechtenpoort voor de bouwstappen.
 *
 * Spiegelt `Config.assert_may_*` uit scripts/lib/project.py. De twee
 * toestemmingen staan bewust los: een bevestiging voor antwoordsleutels geeft
 * paginagetrouwe reproductie niet vrij.
 */

import { existsSync, readFileSync } from 'node:fs';

import { parse } from 'yaml';

export type UseScope = 'own_lesson_groups' | 'department' | 'school';

export interface Rights {
  status: string;
  confirmation_file: string;
  confirmed: boolean;
  use_scope?: UseScope;
  allow_inventory: boolean;
  allow_original_companion: boolean;
  allow_source_answer_keys: boolean;
  answer_keys_teacher_only: boolean;
  allow_page_faithful_reproduction: boolean;
  allow_source_image_reuse: boolean;
  allow_raster_slide_backgrounds: boolean;
}

export interface AnswerDeckConfig {
  enabled: boolean;
  reveal: 'progressive' | 'per_exercise';
  max_items_per_slide: number;
  footer_nl: string;
}

export interface ProjectConfig {
  rights: Rights;
  pptx: {
    mode: string;
    min_body_font_pt: number;
    answer_deck: AnswerDeckConfig;
  };
}

export function loadConfig(path = 'config/project.yaml'): ProjectConfig {
  if (!existsSync(path)) {
    throw new Error(`Configuratie ontbreekt: ${path}`);
  }
  return parse(readFileSync(path, 'utf-8')) as ProjectConfig;
}

function assertConfirmationOnFile(rights: Rights): void {
  if (!rights.confirmed || !existsSync(rights.confirmation_file)) {
    throw new Error(
      'Er is geen geldige rechtenbevestiging.\n' +
        `  rights.confirmed = ${rights.confirmed}\n` +
        `  bevestigingsbestand = ${rights.confirmation_file} ` +
        `(aanwezig: ${existsSync(rights.confirmation_file)})`,
    );
  }
}

export function assertMayReproducePages(rights: Rights): void {
  assertConfirmationOnFile(rights);
  if (!rights.allow_page_faithful_reproduction) {
    throw new Error(
      'Paginagetrouwe reproductie is geblokkeerd.\n' +
        '  rights.allow_page_faithful_reproduction = false\n' +
        'Een bevestiging voor antwoordsleutels dekt dit niet.',
    );
  }
}

export function assertMayUseSourceAnswerKeys(rights: Rights): UseScope {
  assertConfirmationOnFile(rights);
  if (!rights.allow_source_answer_keys) {
    throw new Error(
      'Verwerken van antwoordsleutels uit de bron is geblokkeerd.\n' +
        '  rights.allow_source_answer_keys = false',
    );
  }
  if (!rights.use_scope) {
    throw new Error(
      'rights.use_scope ontbreekt. Leg vast hoe ver het materiaal mag reizen.',
    );
  }
  return rights.use_scope;
}

/** Faalt als een bouwstap raster- of beeldreproductie zou meenemen. */
export function assertNoSourceImagery(rights: Rights): void {
  if (rights.allow_source_image_reuse || rights.allow_raster_slide_backgrounds) {
    assertConfirmationOnFile(rights);
  }
}
