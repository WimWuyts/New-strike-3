/**
 * Designtokens voor web en PowerPoint.
 *
 * Volledig eigen systeem. De bronboeken worden niet gereproduceerd zolang
 * `rights.status` op `original_only` staat, dus deze tokens zijn ontworpen
 * voor leesbaarheid bij klasprojectie, niet als nabootsing van de bron.
 *
 * Alle combinaties van tekst op achtergrond halen minstens WCAG AA.
 */

export type SemanticRole =
  | 'subject'
  | 'aux'
  | 'verb'
  | 'time'
  | 'negation'
  | 'object'
  | 'complement';

export interface RoleToken {
  /** Achtergrondkleur van de woordtegel. */
  readonly fill: string;
  /** Tekstkleur, met minstens 4.5:1 contrast op `fill`. */
  readonly text: string;
  /** Zichtbaar label. Kleur is nooit de enige informatiedrager. */
  readonly label: string;
  /** Vorm, zodat de rol ook zonder kleur herkenbaar blijft. */
  readonly shape:
    | 'rounded_rect'
    | 'rect'
    | 'pill'
    | 'clock'
    | 'hexagon'
    | 'diamond'
    | 'strikethrough_badge';
  /** Patroon voor wie kleuren niet onderscheidt. */
  readonly pattern: 'solid' | 'diagonal' | 'dotted' | 'grid' | 'crosshatch';
}

/**
 * Eén betekenislaag voor grammatica, gedeeld door beide boeken. Zo betekent
 * een kleur altijd hetzelfde, over de hele leerlijn heen.
 */
export const ROLE_TOKENS: Readonly<Record<SemanticRole, RoleToken>> = {
  subject: {
    fill: '#1B4F9C',
    text: '#FFFFFF',
    label: 'SUBJECT',
    shape: 'rounded_rect',
    pattern: 'solid',
  },
  aux: {
    fill: '#B75B00',
    text: '#FFFFFF',
    label: 'AUX',
    shape: 'pill',
    pattern: 'diagonal',
  },
  verb: {
    fill: '#6A2C91',
    text: '#FFFFFF',
    label: 'VERB',
    shape: 'rect',
    pattern: 'solid',
  },
  time: {
    fill: '#1E6B42',
    text: '#FFFFFF',
    label: 'TIME',
    shape: 'clock',
    pattern: 'dotted',
  },
  negation: {
    fill: '#A31220',
    text: '#FFFFFF',
    label: 'NOT',
    shape: 'strikethrough_badge',
    pattern: 'crosshatch',
  },
  object: {
    fill: '#2F5D62',
    text: '#FFFFFF',
    label: 'OBJECT',
    shape: 'hexagon',
    pattern: 'solid',
  },
  complement: {
    fill: '#5A5A66',
    text: '#FFFFFF',
    label: 'COMPL',
    shape: 'diamond',
    pattern: 'grid',
  },
} as const;

export interface BookTheme {
  readonly id: string;
  readonly label: string;
  readonly accent: string;
  readonly accentText: string;
  readonly surface: string;
  readonly surfaceText: string;
  readonly muted: string;
}

/** Per boek een eigen accent, zodat materiaal nooit visueel vermengt. */
export const BOOK_THEMES: Readonly<Record<string, BookTheme>> = {
  ace3: {
    id: 'ace3',
    label: 'New Ace 3',
    accent: '#0F4C81',
    accentText: '#FFFFFF',
    surface: '#FFFFFF',
    surfaceText: '#1A1A20',
    muted: '#5C6270',
  },
  strike3: {
    id: 'strike3',
    label: 'New Strike 3',
    accent: '#8A3A12',
    accentText: '#FFFFFF',
    surface: '#FFFFFF',
    surfaceText: '#1A1A20',
    muted: '#5C6270',
  },
} as const;

/** Typografie. De ondergrens van 18 pt geldt voor alles wat de klas moet lezen. */
export const TYPOGRAPHY = {
  fontFamily: 'Verdana',
  fallbackFamily: 'Arial',
  slide: {
    title: 32,
    subtitle: 24,
    body: 20,
    minBody: 18,
    caption: 18,
    notes: 12,
  },
  web: {
    title: '1.75rem',
    body: '1rem',
    small: '0.875rem',
  },
} as const;

export const FEEDBACK_TOKENS = {
  correct: { fill: '#1E6B42', text: '#FFFFFF', icon: '✓' },
  incorrect: { fill: '#A31220', text: '#FFFFFF', icon: '✕' },
  hint: { fill: '#7A5C00', text: '#FFFFFF', icon: '?' },
  neutral: { fill: '#3A3F4B', text: '#FFFFFF', icon: '•' },
} as const;

export const SLIDE = {
  widthInch: 13.333,
  heightInch: 7.5,
  marginInch: 0.6,
} as const;

/** Relatieve luminantie volgens WCAG 2.1. */
function luminance(hex: string): number {
  const value = hex.replace('#', '');
  const channels = [0, 2, 4].map((offset) => {
    const raw = parseInt(value.slice(offset, offset + 2), 16) / 255;
    return raw <= 0.03928 ? raw / 12.92 : ((raw + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

export function contrastRatio(foreground: string, background: string): number {
  const a = luminance(foreground);
  const b = luminance(background);
  const [light, dark] = a > b ? [a, b] : [b, a];
  return (light + 0.05) / (dark + 0.05);
}

/** Faalt bij het bouwen als een token onder AA zakt. */
export function assertContrast(minimum = 4.5): void {
  const failures: string[] = [];

  for (const [role, token] of Object.entries(ROLE_TOKENS)) {
    const ratio = contrastRatio(token.text, token.fill);
    if (ratio < minimum) {
      failures.push(`rol ${role}: ${ratio.toFixed(2)}:1`);
    }
  }
  for (const [book, theme] of Object.entries(BOOK_THEMES)) {
    const accent = contrastRatio(theme.accentText, theme.accent);
    const surface = contrastRatio(theme.surfaceText, theme.surface);
    if (accent < minimum) failures.push(`boek ${book} accent: ${accent.toFixed(2)}:1`);
    if (surface < minimum) failures.push(`boek ${book} oppervlak: ${surface.toFixed(2)}:1`);
  }
  for (const [name, token] of Object.entries(FEEDBACK_TOKENS)) {
    const ratio = contrastRatio(token.text, token.fill);
    if (ratio < minimum) failures.push(`feedback ${name}: ${ratio.toFixed(2)}:1`);
  }

  if (failures.length > 0) {
    throw new Error(
      `Designtokens halen WCAG AA (${minimum}:1) niet:\n  ${failures.join('\n  ')}`,
    );
  }
}
