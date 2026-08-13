/**
 * Leeromgeving: navigatie, oefeningen, feedback en voortgang.
 *
 * Alle tekst uit de content wordt via textContent gezet, nooit via innerHTML.
 * Zo kan inhoud met tekens als < of & de pagina niet breken.
 */

import { checkAnswer } from '../shared/answers.js';
import type { Activity, ActivitySet, Prompt } from '../shared/types.js';
import { loadBooks, type LoadedBook, type LoadedTheme } from './content.js';
import { Progress } from './progress.js';

const MAX_ATTEMPTS = 3;

type Mode = 'student' | 'teacher';

interface Selection {
  themeId: string;
  targetId: string;
}

const books: LoadedBook[] = loadBooks();
const progress = new Progress();

let mode: Mode = 'student';
let selection: Selection | null = null;
let filterKind = 'all';
let filterStatus = 'all';

// ---------------------------------------------------------------------------
// Hulpfuncties
// ---------------------------------------------------------------------------

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className?: string,
  text?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function announce(message: string): void {
  const region = document.getElementById('live-region');
  if (region) region.textContent = message;
}

function promptIdsFor(set: ActivitySet): Map<string, string[]> {
  const map = new Map<string, string[]>();
  for (const activity of set.activities) {
    map.set(
      activity.id,
      activity.prompts.map((prompt) => prompt.id),
    );
  }
  return map;
}

function setStatus(set: ActivitySet): 'todo' | 'started' | 'done' {
  return progress.status(
    set.activities.map((activity) => activity.id),
    promptIdsFor(set),
  );
}

/** De leesbare titel van een scope-eenheid; de ID is voor de machine. */
function titleFor(theme: LoadedTheme, set: ActivitySet): string {
  const topic = theme.grammar.find((entry) => entry.id === set.target_id);
  if (topic) return topic.title;
  const vocabulary = theme.vocabulary.find((entry) => entry.id === set.target_id);
  if (vocabulary) return vocabulary.title;
  return set.target_id;
}

const STATUS_LABEL: Record<string, string> = {
  todo: 'Nog te doen',
  started: 'Bezig',
  done: 'Afgewerkt',
};

// ---------------------------------------------------------------------------
// Navigatie
// ---------------------------------------------------------------------------

function renderNav(): void {
  const tree = document.getElementById('nav-tree');
  if (!tree) return;
  tree.replaceChildren();

  let visibleSets = 0;
  // Zonder selectie staat het eerste thema met inhoud open, zodat er bij het
  // laden meteen iets zichtbaars staat in plaats van alleen dichte kopjes.
  let openedFirst = false;

  for (const book of books) {
    const bookSection = el('section', 'nav-book');
    bookSection.appendChild(el('h2', 'nav-book__title', book.label));

    let bookHasContent = false;

    for (const theme of book.themes) {
      const sets = theme.activitySets.filter((set) => {
        if (filterKind !== 'all' && set.target_kind !== filterKind) return false;
        if (filterStatus !== 'all' && setStatus(set) !== filterStatus) return false;
        return true;
      });
      if (sets.length === 0) continue;

      bookHasContent = true;
      const details = el('details', 'nav-theme');
      details.open = selection ? selection.themeId === theme.id : !openedFirst;
      if (details.open) openedFirst = true;

      const summary = el('summary', 'nav-theme__summary');
      summary.appendChild(el('span', 'nav-theme__label', `Unit ${theme.unit} — ${theme.title}`));
      const ratio = progress.completion(
        sets.flatMap((set) => set.activities.map((activity) => activity.id)),
        new Map(sets.flatMap((set) => [...promptIdsFor(set)])),
      );
      summary.appendChild(
        el('span', 'nav-theme__progress', `${Math.round(ratio * 100)}%`),
      );
      details.appendChild(summary);

      const list = el('ul', 'nav-list');
      for (const set of sets) {
        visibleSets += 1;
        const item = el('li');
        const button = el('button', 'nav-item');
        button.type = 'button';

        const kindLabel = set.target_kind === 'grammar_topic' ? 'Grammatica' : 'Woordenschat';
        button.appendChild(el('span', 'nav-item__kind', kindLabel));
        button.appendChild(el('span', 'nav-item__name', titleFor(theme, set)));

        const status = setStatus(set);
        const badge = el('span', `nav-item__status is-${status}`, STATUS_LABEL[status]);
        button.appendChild(badge);

        if (selection?.targetId === set.target_id && selection.themeId === theme.id) {
          button.classList.add('is-current');
          button.setAttribute('aria-current', 'true');
        }

        button.addEventListener('click', () => {
          selection = { themeId: theme.id, targetId: set.target_id };
          render();
          document.getElementById('main')?.focus();
        });

        item.appendChild(button);
        list.appendChild(item);
      }
      details.appendChild(list);
      bookSection.appendChild(details);
    }

    if (bookHasContent) tree.appendChild(bookSection);
  }

  if (visibleSets === 0) {
    tree.appendChild(
      el(
        'p',
        'empty-note',
        books.length === 0
          ? 'Er is nog geen content gebouwd. Draai eerst de pipeline.'
          : 'Geen onderdelen die aan deze filters voldoen.',
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Oefeningweergave
// ---------------------------------------------------------------------------

function findSelection(): { theme: LoadedTheme; set: ActivitySet } | null {
  if (!selection) return null;
  for (const book of books) {
    for (const theme of book.themes) {
      if (theme.id !== selection.themeId) continue;
      const set = theme.activitySets.find((entry) => entry.target_id === selection?.targetId);
      if (set) return { theme, set };
    }
  }
  return null;
}

function renderView(): void {
  const view = document.getElementById('view');
  if (!view) return;
  view.replaceChildren();

  const found = findSelection();
  if (!found) {
    const intro = el('div', 'intro');
    intro.appendChild(el('h2', undefined, 'Kies een onderdeel'));
    intro.appendChild(
      el(
        'p',
        undefined,
        'Selecteer links een grammaticaonderwerp of woordenschatset om te beginnen.',
      ),
    );
    view.appendChild(intro);
    return;
  }

  const { theme, set } = found;

  const header = el('header', 'view-header');
  header.appendChild(el('p', 'view-header__eyebrow', `Unit ${theme.unit} — ${theme.title}`));
  header.appendChild(el('h2', undefined, titleFor(theme, set)));
  header.appendChild(
    el(
      'p',
      'view-header__meta',
      `${set.activities.length} activiteiten — ${
        set.target_kind === 'grammar_topic' ? 'grammatica' : 'woordenschat'
      }`,
    ),
  );
  view.appendChild(header);

  const sorted = [...set.activities].sort(
    (a, b) => (a.sequence ?? 0) - (b.sequence ?? 0),
  );
  for (const activity of sorted) {
    view.appendChild(renderActivity(activity));
  }
}

function renderActivity(activity: Activity): HTMLElement {
  const article = el('article', 'activity');
  article.id = `activity-${activity.id}`;

  const head = el('header', 'activity__head');
  head.appendChild(
    el('span', 'activity__stage', `Stage ${activity.stage} · ${activity.difficulty}`),
  );
  head.appendChild(el('h3', 'activity__title', activity.title));
  article.appendChild(head);

  article.appendChild(el('p', 'activity__instructions', activity.instructions_nl));

  const stimulus = el('div', 'activity__stimulus');
  stimulus.appendChild(el('p', undefined, activity.stimulus.content));
  if (activity.stimulus.context_note_nl) {
    stimulus.appendChild(el('p', 'activity__context', activity.stimulus.context_note_nl));
  }
  article.appendChild(stimulus);

  const list = el('ol', 'prompt-list');
  activity.prompts.forEach((prompt, index) => {
    list.appendChild(renderPrompt(activity, prompt, index));
  });
  article.appendChild(list);

  return article;
}

function renderPrompt(activity: Activity, prompt: Prompt, index: number): HTMLElement {
  const item = el('li', 'prompt');
  const inputId = `input-${activity.id}-${prompt.id}`;
  const feedbackId = `feedback-${activity.id}-${prompt.id}`;

  const label = el('label', 'prompt__question', prompt.prompt);
  label.htmlFor = inputId;
  item.appendChild(label);

  const stored = progress.get(activity.id, prompt.id);
  const feedback = el('p', 'prompt__feedback');
  feedback.id = feedbackId;

  let readValue: () => string;

  if (prompt.response_mode === 'multiple_choice' || prompt.response_mode === 'select_multiple') {
    const group = el('div', 'prompt__options');
    group.setAttribute('role', 'group');
    group.setAttribute('aria-labelledby', `${inputId}-label`);
    label.id = `${inputId}-label`;

    const multiple = prompt.response_mode === 'select_multiple';
    (prompt.options ?? []).forEach((option, optionIndex) => {
      const optionId = `${inputId}-${optionIndex}`;
      const wrapper = el('label', 'option');
      const input = el('input');
      input.type = multiple ? 'checkbox' : 'radio';
      input.name = inputId;
      input.value = option;
      input.id = optionId;
      wrapper.appendChild(input);
      wrapper.appendChild(el('span', undefined, option));
      group.appendChild(wrapper);
    });
    item.appendChild(group);

    readValue = () =>
      [...group.querySelectorAll<HTMLInputElement>('input:checked')]
        .map((input) => input.value)
        .join(', ');
  } else if (prompt.response_mode === 'typed_paragraph') {
    const textarea = el('textarea', 'prompt__input');
    textarea.id = inputId;
    textarea.rows = 5;
    textarea.setAttribute('aria-describedby', feedbackId);
    textarea.value = stored.lastResponse ?? '';
    item.appendChild(textarea);
    readValue = () => textarea.value;
  } else {
    const input = el('input', 'prompt__input');
    input.type = 'text';
    input.id = inputId;
    input.autocomplete = 'off';
    input.spellcheck = false;
    input.setAttribute('aria-describedby', feedbackId);
    input.value = stored.lastResponse ?? '';
    item.appendChild(input);
    readValue = () => input.value;
  }

  const actions = el('div', 'prompt__actions');

  const checkButton = el('button', 'btn btn--primary', 'Nakijken');
  checkButton.type = 'button';
  actions.appendChild(checkButton);

  const hints = prompt.hints ?? [];
  const hintButton = el('button', 'btn btn--ghost', 'Hint');
  hintButton.type = 'button';
  if (hints.length === 0) hintButton.disabled = true;
  actions.appendChild(hintButton);

  item.appendChild(actions);

  const hintBox = el('p', 'prompt__hint');
  hintBox.hidden = true;
  item.appendChild(hintBox);
  item.appendChild(feedback);

  // Leerkrachtmodus toont het modelantwoord meteen.
  const answerBox = el('div', 'prompt__answer');
  answerBox.hidden = mode !== 'teacher';
  if (prompt.manual_review_rubric) {
    answerBox.appendChild(el('strong', undefined, 'Beoordelingscriteria'));
    const criteria = el('ul');
    for (const criterion of prompt.manual_review_rubric.criteria) {
      criteria.appendChild(
        el('li', undefined, `${criterion.label_nl}: ${criterion.descriptor_nl}`),
      );
    }
    answerBox.appendChild(criteria);
  } else {
    answerBox.appendChild(
      el('span', undefined, `Antwoord: ${(prompt.canonical_answers ?? []).join(' / ')}`),
    );
  }
  item.appendChild(answerBox);

  if (stored.solved) {
    feedback.textContent = 'Correct.';
    feedback.className = 'prompt__feedback is-correct';
  }

  let hintIndex = stored.hintsUsed;

  hintButton.addEventListener('click', () => {
    if (hintIndex >= hints.length) {
      hintBox.textContent = 'Er zijn geen extra hints meer.';
      hintBox.hidden = false;
      return;
    }
    hintBox.textContent = hints[hintIndex];
    hintBox.hidden = false;
    hintIndex += 1;
    progress.update(activity.id, prompt.id, { hintsUsed: hintIndex });
    announce('Hint getoond.');
  });

  checkButton.addEventListener('click', () => {
    const response = readValue();
    const current = progress.get(activity.id, prompt.id);
    const attempt = current.attempts + 1;

    const result = checkAnswer(prompt, response, { attempt, maxAttempts: MAX_ATTEMPTS });
    progress.update(activity.id, prompt.id, {
      attempts: attempt,
      solved: result.verdict === 'correct',
      lastResponse: response,
    });

    if (result.verdict === 'correct') {
      feedback.textContent = 'Correct.';
      feedback.className = 'prompt__feedback is-correct';
    } else if (result.verdict === 'needs_review') {
      feedback.textContent = result.feedback ?? '';
      feedback.className = 'prompt__feedback is-review';
    } else {
      const suffix =
        result.revealAnswer && !prompt.manual_review_rubric
          ? ` Modelantwoord: ${(prompt.canonical_answers ?? []).join(' / ')}`
          : ` Poging ${attempt} van ${MAX_ATTEMPTS}.`;
      feedback.textContent = `${result.feedback ?? 'Dat klopt nog niet.'}${suffix}`;
      feedback.className = 'prompt__feedback is-incorrect';
    }

    announce(feedback.textContent ?? '');
    renderNav();
  });

  item.dataset.index = String(index + 1);
  return item;
}

// ---------------------------------------------------------------------------
// Bediening
// ---------------------------------------------------------------------------

function render(): void {
  renderNav();
  renderView();
}

function bindControls(): void {
  // Bewust binnen .mode-switch gezocht: op <body> staat ook een data-mode, en
  // een losse [data-mode]-selector zou daar een klikafhandelaar op hangen.
  const modeButtons = document.querySelectorAll<HTMLButtonElement>('.mode-switch [data-mode]');

  modeButtons.forEach((button) => {
    button.addEventListener('click', () => {
      mode = button.dataset.mode === 'teacher' ? 'teacher' : 'student';
      modeButtons.forEach((other) => {
        const active = other === button;
        other.classList.toggle('is-active', active);
        other.setAttribute('aria-pressed', String(active));
      });
      document.body.dataset.mode = mode;
      render();
      announce(mode === 'teacher' ? 'Leerkrachtmodus aan.' : 'Leerlingmodus aan.');
    });
  });

  document.getElementById('filter-kind')?.addEventListener('change', (event) => {
    filterKind = (event.target as HTMLSelectElement).value;
    renderNav();
  });
  document.getElementById('filter-status')?.addEventListener('change', (event) => {
    filterStatus = (event.target as HTMLSelectElement).value;
    renderNav();
  });

  document.getElementById('export-progress')?.addEventListener('click', () => {
    const blob = new Blob([progress.export()], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'voortgang.json';
    link.click();
    URL.revokeObjectURL(url);
    announce('Voortgang geëxporteerd.');
  });

  document.getElementById('import-progress')?.addEventListener('change', (event) => {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    void file.text().then((text) => {
      const ok = progress.import(text);
      announce(ok ? 'Voortgang geïmporteerd.' : 'Dit bestand kon niet gelezen worden.');
      if (ok) render();
    });
  });

  document.getElementById('reset-progress')?.addEventListener('click', () => {
    if (!window.confirm('Alle voortgang wissen? Dit kan niet ongedaan gemaakt worden.')) return;
    progress.reset();
    render();
    announce('Voortgang gewist.');
  });
}

document.body.dataset.mode = mode;
bindControls();
render();
