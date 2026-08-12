/**
 * Voortgang in localStorage. Geen server, geen analytics, geen tracking.
 */

const STORAGE_KEY = 'nans3-progress-v1';

export interface PromptProgress {
  attempts: number;
  solved: boolean;
  hintsUsed: number;
  lastResponse?: string;
}

export interface ProgressData {
  version: 1;
  prompts: Record<string, PromptProgress>;
}

function empty(): ProgressData {
  return { version: 1, prompts: {} };
}

function read(): ProgressData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return empty();
    const parsed = JSON.parse(raw) as ProgressData;
    if (parsed?.version !== 1 || typeof parsed.prompts !== 'object') return empty();
    return parsed;
  } catch {
    // Een onleesbare of geblokkeerde opslag mag de app niet stukmaken.
    return empty();
  }
}

function write(data: ProgressData): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // Quota vol of opslag geweigerd: de oefening blijft werken, alleen zonder
    // bewaarde voortgang.
  }
}

export class Progress {
  private data: ProgressData = read();

  key(activityId: string, promptId: string): string {
    return `${activityId}::${promptId}`;
  }

  get(activityId: string, promptId: string): PromptProgress {
    return (
      this.data.prompts[this.key(activityId, promptId)] ?? {
        attempts: 0,
        solved: false,
        hintsUsed: 0,
      }
    );
  }

  update(activityId: string, promptId: string, patch: Partial<PromptProgress>): PromptProgress {
    const key = this.key(activityId, promptId);
    const next = { ...this.get(activityId, promptId), ...patch };
    this.data.prompts[key] = next;
    write(this.data);
    return next;
  }

  /** Aandeel opgeloste prompts binnen een set activiteit-ID's. */
  completion(activityIds: string[], promptIdsByActivity: Map<string, string[]>): number {
    let total = 0;
    let solved = 0;
    for (const activityId of activityIds) {
      for (const promptId of promptIdsByActivity.get(activityId) ?? []) {
        total += 1;
        if (this.get(activityId, promptId).solved) solved += 1;
      }
    }
    return total === 0 ? 0 : solved / total;
  }

  status(activityIds: string[], promptIdsByActivity: Map<string, string[]>): 'todo' | 'started' | 'done' {
    const ratio = this.completion(activityIds, promptIdsByActivity);
    if (ratio >= 1) return 'done';
    if (ratio > 0) return 'started';
    return 'todo';
  }

  export(): string {
    return JSON.stringify(this.data, null, 2);
  }

  import(json: string): boolean {
    try {
      const parsed = JSON.parse(json) as ProgressData;
      if (parsed?.version !== 1 || typeof parsed.prompts !== 'object') return false;
      this.data = parsed;
      write(this.data);
      return true;
    } catch {
      return false;
    }
  }

  reset(): void {
    this.data = empty();
    write(this.data);
  }
}
