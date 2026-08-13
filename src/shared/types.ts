/** Types die overeenkomen met de JSON Schemas in schemas/. */

export type Provenance =
  | 'source_core'
  | 'corrected_source'
  | 'original_extension'
  | 'original_companion';

export type ResponseMode =
  | 'typed_short'
  | 'typed_sentence'
  | 'typed_paragraph'
  | 'multiple_choice'
  | 'select_multiple'
  | 'ordering'
  | 'matching'
  | 'drag_to_zone'
  | 'click_to_mark';

export type NormalizationRule =
  | 'typographic_apostrophes'
  | 'collapse_whitespace'
  | 'trim'
  | 'ignore_case'
  | 'ignore_terminal_punctuation';

export interface RubricCriterion {
  label: string;
  descriptor: string;
  weight?: number;
}

export interface ManualReviewRubric {
  criteria: RubricCriterion[];
  model_response?: string;
}

export interface ErrorFeedback {
  matches: string;
  match_kind?: 'exact' | 'regex' | 'contains';
  feedback: string;
}

export interface Prompt {
  id: string;
  prompt: string;
  response_mode: ResponseMode;
  options?: string[];
  canonical_answers?: string[];
  accepted_variants?: string[];
  normalization_rules?: NormalizationRule[];
  evidence_ref?: string;
  error_feedback?: ErrorFeedback[];
  hints?: string[];
  manual_review_rubric?: ManualReviewRubric | null;
}

export interface Stimulus {
  type: 'text' | 'dialogue' | 'list' | 'image_description' | 'table' | 'audio_script';
  content: string;
  context_note?: string;
}

export interface Activity {
  id: string;
  book_id: string;
  theme_id: string;
  kind: 'exercise_activity';
  title: string;
  cefr: string;
  learning_objectives: string[];
  target_id: string;
  target_kind: 'grammar_topic' | 'vocabulary_set';
  sequence?: number;
  stage: 1 | 2 | 3 | 4 | 5;
  difficulty: 'support' | 'core' | 'challenge';
  interaction_type: string;
  instructions: string;
  stimulus: Stimulus;
  prompts: Prompt[];
  provenance: Provenance;
  review_status: string;
  content_hash: string;
}

export interface ActivitySet {
  target_id: string;
  target_kind: 'grammar_topic' | 'vocabulary_set';
  activities: Activity[];
}

export interface GrammarTopic {
  id: string;
  book_id: string;
  theme_id: string;
  title: string;
  cefr: string;
  can_do_statements: string[];
  meaning_and_use: {
    summary: string;
    use_cases: { label: string; explanation: string; example_en: string }[];
  };
  form: Record<string, { pattern: string; examples: string[] } | unknown>;
  signal_words?: string[];
  signal_words_caveat?: string;
  typical_errors: { wrong: string; right: string; why: string }[];
  contrast_with: { other_topic: string; difference: string; minimal_pair: string[] }[];
  examples: {
    sentence_en: string;
    context: string;
    highlights?: { text: string; role: string }[];
  }[];
  visual_model_id?: string;
  recap: string[];
  exit_ticket: { prompt: string; expected_evidence: string };
  source_page_refs: { page: number; source_file: string }[];
}

export interface Lexeme {
  id: string;
  lemma: string;
  learnable_form?: string;
  part_of_speech: string;
  ipa?: string;
  definition_en: string;
  translation_nl: string;
  collocations?: string[];
  example_sentences: string[];
  register?: string;
  provenance: Provenance;
  source_page_refs?: { page: number; source_file: string }[];
}

export interface VocabularySet {
  id: string;
  book_id: string;
  theme_id: string;
  title: string;
  cefr: string;
  lexemes: Lexeme[];
  source_page_refs: { page: number; source_file: string }[];
}

export interface VisualGrammarModel {
  id: string;
  grammar_topic_id: string;
  title: string;
  model_type: string;
  steps: {
    index: number;
    caption: string;
    change_description: string;
    elements: {
      id: string;
      text: string;
      role: string;
      state: string;
      position?: { order: number; row?: number };
    }[];
  }[];
  accessibility: {
    static_alternative: string;
    role_legend: { role: string; label: string; shape: string }[];
  };
  pptx_progressive_slides?: number;
}

export interface ThemeContent {
  themeId: string;
  bookId: string;
  title: string;
  grammar: GrammarTopic[];
  vocabulary: VocabularySet[];
  visuals: VisualGrammarModel[];
  activitySets: ActivitySet[];
}
