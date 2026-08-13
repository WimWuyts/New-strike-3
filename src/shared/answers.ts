/**
 * Antwoordcontrole.
 *
 * Normaliseert alleen wat aantoonbaar irrelevant is voor het leerdoel.
 * Foutieve spelling, een verkeerde werkwoordsvorm of een verkeerde flexie
 * worden nooit goedgekeurd: die vormen zijn juist het leerdoel.
 */

import type { NormalizationRule, Prompt } from './types.js';

const DEFAULT_RULES: NormalizationRule[] = [
  'typographic_apostrophes',
  'collapse_whitespace',
  'trim',
];

export function normalise(value: string, rules: NormalizationRule[] = DEFAULT_RULES): string {
  let text = value ?? '';
  const active = new Set<NormalizationRule>([...DEFAULT_RULES, ...rules]);

  if (active.has('typographic_apostrophes')) {
    text = text
      .replace(/[‘’ʼ]/g, "'")
      .replace(/[“”]/g, '"')
      .replace(/[‐-―]/g, '-');
  }
  if (active.has('collapse_whitespace')) {
    text = text.replace(/\s+/g, ' ');
  }
  if (active.has('trim')) {
    text = text.trim();
  }
  if (active.has('ignore_terminal_punctuation')) {
    text = text.replace(/[.!?,;:]+$/u, '').trim();
  }
  if (active.has('ignore_case')) {
    text = text.toLocaleLowerCase('en');
  }
  return text;
}

export type Verdict = 'correct' | 'incorrect' | 'needs_review';

export interface CheckResult {
  verdict: Verdict;
  /** Nederlandstalige feedback: de leerling moet de uitleg kunnen begrijpen. */
  feedback?: string;
  /** True zodra de leerling het modelantwoord mag zien. */
  revealAnswer: boolean;
}

export interface CheckOptions {
  attempt: number;
  maxAttempts: number;
}

export function checkAnswer(
  prompt: Prompt,
  response: string,
  options: CheckOptions,
): CheckResult {
  const rules = prompt.normalization_rules ?? [];
  const reveal = options.attempt >= options.maxAttempts;

  // Open productie wordt niet automatisch beoordeeld. Dat zou de leerling een
  // schijnzekerheid geven die de rubric juist moet vervangen.
  if (prompt.response_mode === 'typed_paragraph') {
    return {
      verdict: 'needs_review',
      feedback:
        'Deze opdracht wordt niet automatisch nagekeken. Vergelijk je antwoord met de criteria.',
      revealAnswer: true,
    };
  }

  const given = normalise(response, rules);
  if (given.length === 0) {
    return {
      verdict: 'incorrect',
      feedback: 'Er staat nog niets ingevuld.',
      revealAnswer: reveal,
    };
  }

  const accepted = [
    ...(prompt.canonical_answers ?? []),
    ...(prompt.accepted_variants ?? []),
  ].map((answer) => normalise(answer, rules));

  if (accepted.includes(given)) {
    return { verdict: 'correct', revealAnswer: false };
  }

  const targeted = matchErrorFeedback(prompt, response, given, rules);
  if (targeted) {
    return { verdict: 'incorrect', feedback: targeted, revealAnswer: reveal };
  }

  return {
    verdict: 'incorrect',
    feedback: nearMissFeedback(given, accepted),
    revealAnswer: reveal,
  };
}

function matchErrorFeedback(
  prompt: Prompt,
  raw: string,
  normalised: string,
  rules: NormalizationRule[],
): string | undefined {
  for (const entry of prompt.error_feedback ?? []) {
    const kind = entry.match_kind ?? 'exact';
    if (kind === 'exact' && normalise(entry.matches, rules) === normalised) {
      return entry.feedback;
    }
    if (kind === 'contains' && normalised.includes(normalise(entry.matches, rules))) {
      return entry.feedback;
    }
    if (kind === 'regex') {
      try {
        if (new RegExp(entry.matches, 'u').test(raw)) return entry.feedback;
      } catch {
        // Een onbruikbare regex mag de oefening niet laten crashen.
        continue;
      }
    }
  }
  return undefined;
}

/**
 * Feedback die richting geeft zonder het antwoord te verklappen.
 */
function nearMissFeedback(given: string, accepted: string[]): string {
  if (accepted.length === 0) return 'Dat klopt nog niet.';

  const closest = accepted.reduce((best, candidate) =>
    editDistance(given, candidate) < editDistance(given, best) ? candidate : best,
  );
  const distance = editDistance(given, closest);

  if (distance === 0) return 'Dat klopt nog niet.';
  if (distance <= 2 && given.length > 3) {
    return 'Je zit er dicht bij. Kijk nog eens naar de spelling.';
  }
  if (closest.split(' ').length !== given.split(' ').length) {
    return 'Je antwoord heeft niet het juiste aantal woorden. Lees de opdracht opnieuw.';
  }
  return 'Dat klopt nog niet. Gebruik een hint als je vastzit.';
}

function editDistance(a: string, b: string): number {
  if (a === b) return 0;
  const previous = Array.from({ length: b.length + 1 }, (_, i) => i);
  const current = new Array<number>(b.length + 1).fill(0);

  for (let i = 1; i <= a.length; i += 1) {
    current[0] = i;
    for (let j = 1; j <= b.length; j += 1) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      current[j] = Math.min(current[j - 1] + 1, previous[j] + 1, previous[j - 1] + cost);
    }
    previous.splice(0, previous.length, ...current);
  }
  return previous[b.length];
}
