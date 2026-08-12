"""Catalogus van herbruikbare interactiepatronen.

Sectie 11 van de projectopdracht eist minstens 35 patronen, per activiteit
inhoudelijk gekozen. Elk patroon legt vast:

- welke response_mode het oplevert (bepaalt of het als "getypt" telt);
- of het hoofdzakelijk meerkeuze is (telt mee voor het meerkeuzeplafond);
- welke didactische categorieen het dekt (foutreparatie, transformatie,
  collocatie, woordfamilie, register, mini-schrijven);
- voor welke stages en welk doeltype het geschikt is.

De validator gebruikt deze tabel om de quota te controleren. Een activiteit
met een interaction_type dat hier niet staat, is ongeldig.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Didactische categorieen waarop quota gelden.
CAT_ERROR_REPAIR = "error_repair"
CAT_TRANSFORMATION = "transformation"
CAT_MINI_WRITING = "mini_writing"
CAT_COLLOCATION = "collocation"
CAT_WORD_FAMILY = "word_family"
CAT_REGISTER = "register"
CAT_NOTICING = "noticing"
CAT_MEANING = "meaning"

TYPED_RESPONSE_MODES = frozenset(
    {"typed_short", "typed_sentence", "typed_paragraph"}
)


@dataclass(frozen=True)
class InteractionPattern:
    key: str
    label_nl: str
    description_nl: str
    primary_response_mode: str
    categories: frozenset[str] = field(default_factory=frozenset)
    stages: frozenset[int] = field(default_factory=lambda: frozenset({1, 2, 3, 4, 5}))
    targets: frozenset[str] = field(
        default_factory=lambda: frozenset({"grammar_topic", "vocabulary_set"})
    )

    @property
    def is_typed(self) -> bool:
        return self.primary_response_mode in TYPED_RESPONSE_MODES

    @property
    def is_multiple_choice(self) -> bool:
        return self.primary_response_mode in {"multiple_choice", "select_multiple"}


def _p(
    key: str,
    label: str,
    description: str,
    mode: str,
    categories: set[str] | None = None,
    stages: set[int] | None = None,
    targets: set[str] | None = None,
) -> InteractionPattern:
    return InteractionPattern(
        key=key,
        label_nl=label,
        description_nl=description,
        primary_response_mode=mode,
        categories=frozenset(categories or set()),
        stages=frozenset(stages or {1, 2, 3, 4, 5}),
        targets=frozenset(targets or {"grammar_topic", "vocabulary_set"}),
    )


CATALOGUE: dict[str, InteractionPattern] = {
    p.key: p
    for p in [
        # -- stage 1: opmerken en receptief onderscheiden ------------------
        _p("timeline-placement", "Tijdlijnplaatsing",
           "Leerling plaatst zinnen op een tijdlijn en ziet zo het tijdsverschil.",
           "drag_to_zone", {CAT_NOTICING}, {1, 2}, {"grammar_topic"}),
        _p("spot-the-form", "Vorm herkennen",
           "Markeer in een tekst elke plaats waar de doelvorm staat.",
           "click_to_mark", {CAT_NOTICING}, {1}),
        _p("sorting-under-pressure", "Sorteren op tijd",
           "Sorteer items in categorieen binnen een zichtbare tijdslimiet.",
           "drag_to_zone", {CAT_NOTICING}, {1, 2}),
        _p("odd-one-out", "Vreemde eend, met verantwoording",
           "Kies het afwijkende item en typ waarom het afwijkt.",
           "typed_short", {CAT_NOTICING, CAT_MEANING}, {1, 2}),
        _p("memory-grid", "Geheugenraster",
           "Draai kaarten om en koppel paren; het raster onthoudt fouten.",
           "matching", {CAT_MEANING}, {1, 2}),
        _p("true-false-evidence", "Waar of niet waar, met bewijs",
           "Beoordeel uitspraken en typ de zin die het bewijst.",
           "typed_short", {CAT_NOTICING}, {1, 2}),
        _p("minimal-pair-choice", "Minimaal paar",
           "Twee bijna identieke zinnen; kies welke bij de context past.",
           "multiple_choice", {CAT_NOTICING, CAT_MEANING}, {1, 2}),
        _p("highlight-the-signal", "Signaal markeren",
           "Markeer signaalwoorden en beoordeel of ze hier echt betrouwbaar zijn.",
           "click_to_mark", {CAT_NOTICING}, {1, 2}, {"grammar_topic"}),

        # -- stage 2: betekenis koppelen -----------------------------------
        _p("collocation-magnets", "Collocatiemagneten",
           "Sleep woorden naar het woord waarmee ze gebruikelijk samengaan.",
           "matching", {CAT_COLLOCATION}, {2, 3}, {"vocabulary_set"}),
        _p("definition-match", "Definitie koppelen",
           "Koppel elk woord aan een korte Engelse definitie.",
           "matching", {CAT_MEANING}, {1, 2}, {"vocabulary_set"}),
        _p("picture-to-word", "Beeld naar woord",
           "Kies of typ het woord dat bij een beschreven situatie past.",
           "typed_short", {CAT_MEANING}, {2}, {"vocabulary_set"}),
        _p("choose-and-justify", "Kies en verantwoord",
           "Kies de juiste vorm en typ in één zin waarom.",
           "typed_short", {CAT_MEANING}, {2, 3}),
        _p("information-gap", "Informatiekloof",
           "Twee halve teksten; leerling vult aan wat de andere helft prijsgeeft.",
           "typed_short", {CAT_MEANING}, {2, 3, 4}),
        _p("context-clue-inference", "Betekenis uit context",
           "Leid de betekenis van een onbekend woord af uit de omringende zin.",
           "typed_short", {CAT_MEANING}, {2, 3}, {"vocabulary_set"}),
        _p("categorise-by-use", "Indelen naar gebruik",
           "Deel voorbeelden in naar gebruiksbetekenis, niet naar vorm.",
           "drag_to_zone", {CAT_MEANING}, {2}, {"grammar_topic"}),

        # -- stage 3: gecontroleerd schrijven ------------------------------
        _p("form-production", "Vorm schrijven",
           "Typ de correcte vorm van het werkwoord of woord tussen haakjes.",
           "typed_short", set(), {3}),
        _p("micro-dictation", "Microdictee",
           "Luister of lees kort en schrijf de zin exact over.",
           "typed_sentence", set(), {3}),
        _p("word-family-machine", "Woordfamiliemachine",
           "Vorm het gevraagde familielid van een woord: zelfstandig, bijvoeglijk, werkwoord.",
           "typed_short", {CAT_WORD_FAMILY}, {3, 4}, {"vocabulary_set"}),
        _p("before-after-transformation", "Omvormen",
           "Zet een zin om naar ontkennend, vragend of een andere tijd.",
           "typed_sentence", {CAT_TRANSFORMATION}, {3, 4}),
        _p("sentence-surgery", "Zinschirurgie",
           "Herschrijf een zin volgens een opgelegde structurele ingreep.",
           "typed_sentence", {CAT_TRANSFORMATION}, {3, 4}),
        _p("error-detective", "Foutendetective",
           "Vind de fout in de zin en typ de verbeterde versie.",
           "typed_sentence", {CAT_ERROR_REPAIR}, {3, 4}),
        _p("chat-repair", "Chatreparatie",
           "Verbeter de foutieve berichten in een chatgesprek.",
           "typed_sentence", {CAT_ERROR_REPAIR}, {3, 4}),
        _p("movable-word-tiles", "Woordtegels schikken",
           "Zet losse woordtegels in de juiste volgorde tot een correcte zin.",
           "ordering", set(), {2, 3}),
        _p("gap-with-constraint", "Invullen met beperking",
           "Vul de opening in, maar het antwoord moet aan een opgelegde eis voldoen.",
           "typed_short", set(), {3, 4}),
        _p("spelling-focus", "Spellingfocus",
           "Schrijf vormen waarvan de spelling verandert bij verbuiging of vervoeging.",
           "typed_short", set(), {3}),

        # -- stage 4: geleid schrijven in context --------------------------
        _p("caption-rewrite", "Onderschrift herschrijven",
           "Herschrijf een onderschrift zodat het de doelvorm correct gebruikt.",
           "typed_sentence", {CAT_TRANSFORMATION}, {4}),
        _p("headline-expansion", "Kop uitbreiden",
           "Werk een telegramkop uit tot een volledige, correcte zin.",
           "typed_sentence", {CAT_TRANSFORMATION}, {4}),
        _p("sentence-combining", "Zinnen samenvoegen",
           "Voeg korte zinnen samen tot één vloeiende zin.",
           "typed_sentence", {CAT_TRANSFORMATION}, {4, 5}),
        _p("branching-dialogue", "Vertakkend gesprek",
           "Elke getypte reactie bepaalt hoe het gesprek verdergaat.",
           "typed_sentence", set(), {4, 5}),
        _p("register-switch", "Registerwissel",
           "Herschrijf een boodschap van informeel naar formeel of omgekeerd.",
           "typed_sentence", {CAT_REGISTER}, {4, 5}, {"vocabulary_set"}),
        _p("guided-note-completion", "Notitie aanvullen",
           "Vul een half ingevulde notitie aan met correcte vormen.",
           "typed_short", set(), {4}),
        _p("mini-mystery", "Minimysterie",
           "Los een klein raadsel op en verantwoord de oplossing schriftelijk.",
           "typed_sentence", set(), {4, 5}),
        _p("reorder-and-rewrite", "Herordenen en herschrijven",
           "Zet een door elkaar gehaalde tekst op volgorde en herschrijf de overgangen.",
           "typed_sentence", {CAT_TRANSFORMATION}, {4, 5}),

        # -- stage 5: productieve transfer ---------------------------------
        _p("constrained-writing", "Schrijven met beperking",
           "Schrijf een kort tekstje dat aan expliciete vorm- en inhoudseisen voldoet.",
           "typed_paragraph", {CAT_MINI_WRITING}, {5}),
        _p("personalised-exit-ticket", "Persoonlijk exit ticket",
           "Pas de doelvorm toe op de eigen situatie van de leerling.",
           "typed_paragraph", {CAT_MINI_WRITING}, {5}),
        _p("revision-pass", "Revisieronde",
           "Herzie een eigen of gegeven tekst aan de hand van een checklist.",
           "typed_paragraph", {CAT_ERROR_REPAIR, CAT_MINI_WRITING}, {5}),
        _p("role-response", "Rolreactie",
           "Reageer schriftelijk vanuit een opgelegde rol en situatie.",
           "typed_paragraph", {CAT_MINI_WRITING}, {5}),
        _p("compare-two-versions", "Twee versies vergelijken",
           "Vergelijk twee versies van een tekst en beargumenteer welke beter is.",
           "typed_paragraph", {CAT_MINI_WRITING}, {5}),
        _p("explain-to-a-peer", "Uitleggen aan een medeleerling",
           "Formuleer de regel in eigen woorden met een zelfbedacht voorbeeld.",
           "typed_paragraph", {CAT_MINI_WRITING}, {5}),
    ]
}

assert len(CATALOGUE) >= 35, (
    f"De catalogus moet minstens 35 patronen bevatten, heeft er {len(CATALOGUE)}."
)


def get(key: str) -> InteractionPattern:
    try:
        return CATALOGUE[key]
    except KeyError:
        raise KeyError(
            f"Onbekend interactiepatroon {key!r}. "
            f"Voeg het toe aan scripts/lib/interactions.py of gebruik een bestaand patroon."
        ) from None


def for_target(target_kind: str) -> list[InteractionPattern]:
    return [p for p in CATALOGUE.values() if target_kind in p.targets]


def for_stage(stage: int, target_kind: str) -> list[InteractionPattern]:
    return [p for p in for_target(target_kind) if stage in p.stages]
