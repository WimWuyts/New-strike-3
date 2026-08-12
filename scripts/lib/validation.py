"""Inhoudsvalidatie: schema's, quota, antwoordbaarheid en opbouw.

Dit is de poortwachter voor `dist/`. Een artefact dat hier een `error`
oplevert, mag niet gepubliceerd worden.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from . import interactions
from .project import SCHEMA_DIR, Config

DIFFICULTY_RANK = {"support": 0, "core": 1, "challenge": 2}

CHOICE_MODES = {
    "multiple_choice",
    "select_multiple",
    "matching",
    "ordering",
    "drag_to_zone",
    "click_to_mark",
}


# ---------------------------------------------------------------------------
# Bevindingen
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    level: str  # "error" | "warning"
    code: str
    message: str
    location: str = ""

    def __str__(self) -> str:
        where = f" [{self.location}]" if self.location else ""
        return f"{self.level.upper()} {self.code}{where}: {self.message}"


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    def error(self, code: str, message: str, location: str = "") -> None:
        self.findings.append(Finding("error", code, message, location))

    def warn(self, code: str, message: str, location: str = "") -> None:
        self.findings.append(Finding("warning", code, message, location))

    def extend(self, other: "Report") -> None:
        self.findings.extend(other.findings)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors


# ---------------------------------------------------------------------------
# Schemavalidatie
# ---------------------------------------------------------------------------


def _build_registry() -> Registry:
    registry = Registry()
    for path in SCHEMA_DIR.glob("*.json"):
        with path.open(encoding="utf-8") as fh:
            contents = json.load(fh)
        resource = Resource.from_contents(contents, default_specification=DRAFT202012)
        # Registreer zowel op $id als op bestandsnaam, zodat relatieve
        # verwijzingen als "common.json#/$defs/slug" oplossen.
        registry = registry.with_resource(path.name, resource)
        if "$id" in contents:
            registry = registry.with_resource(contents["$id"], resource)
    return registry


_REGISTRY: Registry | None = None


def _registry() -> Registry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


def validate_schema(payload: Any, schema_name: str, location: str = "") -> Report:
    """Valideert één object tegen een schema uit schemas/."""
    report = Report()
    schema_path = SCHEMA_DIR / schema_name
    if not schema_path.exists():
        report.error("schema-missing", f"Schema {schema_name} bestaat niet.", location)
        return report

    with schema_path.open(encoding="utf-8") as fh:
        schema = json.load(fh)

    validator = Draft202012Validator(schema, registry=_registry())
    for issue in sorted(validator.iter_errors(payload), key=lambda e: list(e.path)):
        pointer = "/".join(str(p) for p in issue.path) or "<root>"
        report.error("schema", issue.message, f"{location}:{pointer}" if location else pointer)
    return report


# ---------------------------------------------------------------------------
# Oefenreeks: exact 25, stages, quota, diversiteit
# ---------------------------------------------------------------------------


def validate_activity_set(
    activities: list[dict[str, Any]],
    target_id: str,
    target_kind: str,
    config: Config,
) -> Report:
    """Controleert een volledige reeks van 25 activiteiten voor één scope-eenheid."""
    report = Report()
    loc = target_id

    expected = config.exercises["per_scope_unit"]
    if len(activities) != expected:
        report.error(
            "count",
            f"Verwacht exact {expected} activiteiten, gevonden {len(activities)}.",
            loc,
        )

    _check_identity(activities, target_id, target_kind, report)
    _check_stage_distribution(activities, config, report, loc)
    _check_interaction_diversity(activities, config, target_kind, report, loc)
    _check_quotas(activities, config, target_kind, report, loc)
    _check_answerability(activities, report)
    _check_duplication(activities, report, loc)
    _check_difficulty_progression(activities, report, loc)
    return report


def _check_identity(
    activities: list[dict[str, Any]],
    target_id: str,
    target_kind: str,
    report: Report,
) -> None:
    ids = [a.get("id", "") for a in activities]
    for dup, count in Counter(ids).items():
        if count > 1:
            report.error("duplicate-id", f"Activiteit-ID {dup!r} komt {count}x voor.", target_id)

    for activity in activities:
        loc = activity.get("id", "<zonder id>")
        if activity.get("target_id") != target_id:
            report.error(
                "target-mismatch",
                f"target_id is {activity.get('target_id')!r}, verwacht {target_id!r}.",
                loc,
            )
        if activity.get("target_kind") != target_kind:
            report.error(
                "target-kind-mismatch",
                f"target_kind is {activity.get('target_kind')!r}, verwacht {target_kind!r}.",
                loc,
            )


def _check_stage_distribution(
    activities: list[dict[str, Any]], config: Config, report: Report, loc: str
) -> None:
    per_stage = Counter(a.get("stage") for a in activities)
    for spec in config.exercises["stages"]:
        stage = spec["stage"]
        low, high = spec["range"]
        expected = high - low + 1
        actual = per_stage.get(stage, 0)
        if actual != expected:
            report.error(
                "stage-distribution",
                f"Stage {stage} ({spec['label']}) heeft {actual} activiteiten, verwacht {expected}.",
                loc,
            )

    sequences = [a.get("sequence") for a in activities if a.get("sequence") is not None]
    if sequences:
        missing = sorted(set(range(1, len(activities) + 1)) - set(sequences))
        if missing:
            report.error(
                "sequence-gap",
                f"Ontbrekende sequence-nummers: {missing}.",
                loc,
            )
        for activity in activities:
            seq, stage = activity.get("sequence"), activity.get("stage")
            if seq is None or stage is None:
                continue
            spec = next((s for s in config.exercises["stages"] if s["stage"] == stage), None)
            if spec and not (spec["range"][0] <= seq <= spec["range"][1]):
                report.error(
                    "sequence-stage-mismatch",
                    f"sequence {seq} hoort niet bij stage {stage} (bereik {spec['range']}).",
                    activity.get("id", loc),
                )


def _check_interaction_diversity(
    activities: list[dict[str, Any]],
    config: Config,
    target_kind: str,
    report: Report,
    loc: str,
) -> None:
    quotas = config.exercises["quotas"][target_kind]
    counts = Counter(a.get("interaction_type") for a in activities)

    for key in counts:
        if key not in interactions.CATALOGUE:
            report.error(
                "unknown-interaction",
                f"Interactiepatroon {key!r} staat niet in de catalogus.",
                loc,
            )
            continue
        pattern = interactions.get(key)
        if target_kind not in pattern.targets:
            report.warn(
                "interaction-target-fit",
                f"Patroon {key!r} is niet bedoeld voor {target_kind}.",
                loc,
            )

    distinct = len(counts)
    minimum = quotas["min_distinct_interaction_types"]
    if distinct < minimum:
        report.error(
            "interaction-diversity",
            f"{distinct} verschillende interactiepatronen, minimaal {minimum} vereist.",
            loc,
        )

    ceiling = quotas["max_uses_per_interaction_type"]
    for key, count in counts.items():
        if count > ceiling:
            report.error(
                "interaction-overuse",
                f"Patroon {key!r} komt {count}x voor, maximaal {ceiling} toegestaan.",
                loc,
            )


def _activity_response_modes(activity: dict[str, Any]) -> list[str]:
    return [p.get("response_mode", "") for p in activity.get("prompts", [])]


def _is_typed_activity(activity: dict[str, Any]) -> bool:
    """Een activiteit telt als 'getypt' zodra er een getypt antwoordmoment in zit."""
    return any(m in interactions.TYPED_RESPONSE_MODES for m in _activity_response_modes(activity))


def _is_mainly_multiple_choice(activity: dict[str, Any]) -> bool:
    modes = _activity_response_modes(activity)
    if not modes:
        return False
    choice = sum(1 for m in modes if m in {"multiple_choice", "select_multiple"})
    return choice > len(modes) / 2


def _categories(activity: dict[str, Any]) -> frozenset[str]:
    key = activity.get("interaction_type")
    if key not in interactions.CATALOGUE:
        return frozenset()
    return interactions.get(key).categories


def _check_quotas(
    activities: list[dict[str, Any]],
    config: Config,
    target_kind: str,
    report: Report,
    loc: str,
) -> None:
    quotas = config.exercises["quotas"][target_kind]

    typed = sum(1 for a in activities if _is_typed_activity(a))
    minimum = quotas["min_typed_answer_activities"]
    if typed < minimum:
        report.error(
            "quota-typed",
            f"{typed} activiteiten met getypte antwoorden, minimaal {minimum} vereist.",
            loc,
        )

    mc = sum(1 for a in activities if _is_mainly_multiple_choice(a))
    ceiling = quotas["max_multiple_choice_activities"]
    if mc > ceiling:
        report.error(
            "quota-multiple-choice",
            f"{mc} hoofdzakelijk meerkeuze-activiteiten, maximaal {ceiling} toegestaan.",
            loc,
        )

    category_quotas = {
        "min_error_repair_activities": interactions.CAT_ERROR_REPAIR,
        "min_transformation_activities": interactions.CAT_TRANSFORMATION,
        "min_mini_writing_activities": interactions.CAT_MINI_WRITING,
        "min_collocation_activities": interactions.CAT_COLLOCATION,
        "min_word_family_activities": interactions.CAT_WORD_FAMILY,
        "min_register_context_activities": interactions.CAT_REGISTER,
    }
    for quota_key, category in category_quotas.items():
        if quota_key not in quotas:
            continue
        needed = quotas[quota_key]
        actual = sum(1 for a in activities if category in _categories(a))
        if actual < needed:
            report.error(
                "quota-category",
                f"{actual} activiteiten in categorie {category!r}, minimaal {needed} vereist.",
                loc,
            )


def _check_answerability(activities: list[dict[str, Any]], report: Report) -> None:
    """Elke vraag moet aantoonbaar te beantwoorden zijn."""
    for activity in activities:
        loc = activity.get("id", "<zonder id>")
        stimulus = (activity.get("stimulus") or {}).get("content", "")

        for prompt in activity.get("prompts", []):
            ploc = f"{loc}/{prompt.get('id', '?')}"
            mode = prompt.get("response_mode")
            answers = prompt.get("canonical_answers") or []
            options = prompt.get("options") or []

            if mode == "typed_paragraph":
                if not prompt.get("manual_review_rubric"):
                    report.error(
                        "open-without-rubric",
                        "Open productie zonder rubric mag niet als automatisch beoordeeld gelden.",
                        ploc,
                    )
                continue

            if not answers:
                report.error("no-answer", "Geen canonical_answers opgegeven.", ploc)
                continue

            if any(not str(a).strip() for a in answers):
                report.error("empty-answer", "Een canonical_answer is leeg.", ploc)

            if mode in CHOICE_MODES:
                if not options:
                    report.error("no-options", f"response_mode {mode} vereist options.", ploc)
                else:
                    normalised = {_norm(o) for o in options}
                    for answer in answers:
                        if _norm(answer) not in normalised:
                            report.error(
                                "answer-not-in-options",
                                f"Antwoord {answer!r} staat niet tussen de opties.",
                                ploc,
                            )
                    if len(normalised) < len(options):
                        report.error(
                            "duplicate-options",
                            "Er staan identieke opties in dezelfde vraag.",
                            ploc,
                        )
                    if len(options) < 2:
                        report.error("too-few-options", "Minstens twee opties vereist.", ploc)

            evidence = prompt.get("evidence_ref")
            if evidence and stimulus and evidence not in stimulus:
                report.warn(
                    "evidence-not-found",
                    f"evidence_ref {evidence!r} is niet letterlijk in de stimulus terug te vinden.",
                    ploc,
                )

            for hint in prompt.get("hints", []):
                for answer in answers:
                    if _norm(answer) and _norm(answer) in _norm(hint):
                        report.error(
                            "hint-reveals-answer",
                            f"Een hint bevat het antwoord {answer!r} letterlijk.",
                            ploc,
                        )

            rules = set(prompt.get("normalization_rules") or [])
            if "ignore_case" in rules and mode in interactions.TYPED_RESPONSE_MODES:
                report.warn(
                    "normalisation-broad",
                    "ignore_case staat aan; controleer dat hoofdletters hier niet het leerdoel zijn.",
                    ploc,
                )


def _check_duplication(activities: list[dict[str, Any]], report: Report, loc: str) -> None:
    """Geen herhaalde prompts en geen identieke distractorensets."""
    prompt_texts: Counter[str] = Counter()
    option_sets: Counter[tuple[str, ...]] = Counter()

    for activity in activities:
        for prompt in activity.get("prompts", []):
            text = _norm(prompt.get("prompt", ""))
            if text:
                prompt_texts[text] += 1
            options = prompt.get("options") or []
            if len(options) >= 2:
                option_sets[tuple(sorted(_norm(o) for o in options))] += 1

    for text, count in prompt_texts.items():
        if count > 1:
            report.error(
                "duplicate-prompt",
                f"Dezelfde prompt komt {count}x voor: {text[:70]!r}",
                loc,
            )

    for options, count in option_sets.items():
        if count > 2:
            report.error(
                "duplicate-distractors",
                f"Identieke optieset komt {count}x voor: {list(options)[:3]}...",
                loc,
            )


def _check_difficulty_progression(
    activities: list[dict[str, Any]], report: Report, loc: str
) -> None:
    """De gemiddelde moeilijkheid mag per stage niet dalen."""
    by_stage: dict[int, list[int]] = {}
    for activity in activities:
        stage = activity.get("stage")
        rank = DIFFICULTY_RANK.get(activity.get("difficulty", ""))
        if stage is None or rank is None:
            continue
        by_stage.setdefault(stage, []).append(rank)

    means = {
        stage: sum(ranks) / len(ranks) for stage, ranks in sorted(by_stage.items()) if ranks
    }
    previous_stage, previous_mean = None, None
    for stage, mean in means.items():
        if previous_mean is not None and mean < previous_mean - 0.5:
            report.warn(
                "difficulty-regression",
                f"Stage {stage} is gemiddeld makkelijker ({mean:.2f}) dan stage "
                f"{previous_stage} ({previous_mean:.2f}).",
                loc,
            )
        previous_stage, previous_mean = stage, mean


# ---------------------------------------------------------------------------
# Reading en listening
# ---------------------------------------------------------------------------


def validate_module_evidence(module: dict[str, Any], kind: str) -> Report:
    """Elke inhoudsvraag moet naar bestaand bewijs verwijzen."""
    report = Report()
    loc = module.get("id", f"<{kind}>")

    if kind == "reading":
        valid_ids = {
            sentence["id"]
            for paragraph in module.get("text", {}).get("paragraphs", [])
            for sentence in paragraph.get("sentences", [])
        }
        valid_ids |= {p["id"] for p in module.get("text", {}).get("paragraphs", [])}
    else:
        valid_ids = {segment["id"] for segment in module.get("transcript", [])}

    for group_name, group in (module.get("tasks") or {}).items():
        if not isinstance(group, dict) or "questions" not in group:
            continue
        for question in group["questions"]:
            ref = question.get("evidence_ref", "")
            qloc = f"{loc}/{group_name}/{question.get('id', '?')}"
            if not ref:
                report.error("no-evidence", "Vraag zonder evidence_ref.", qloc)
            elif ref not in valid_ids and not _is_timestamp(ref):
                report.error(
                    "dangling-evidence",
                    f"evidence_ref {ref!r} verwijst niet naar een bestaand segment.",
                    qloc,
                )

    if kind == "listening":
        audio = module.get("audio", {})
        if audio.get("status") == "built" and not audio.get("path"):
            report.error("audio-inconsistent", "Audio staat op 'built' zonder pad.", loc)

    return report


def _is_timestamp(value: str) -> bool:
    return bool(re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?(?:\s*-\s*\d{1,2}:\d{2}(?::\d{2})?)?", value.strip()))


# ---------------------------------------------------------------------------
# Leerling versus leerkracht
# ---------------------------------------------------------------------------


def validate_student_leak(student_payload: Any, answers: Iterable[str]) -> Report:
    """Controleert dat oplossingen niet in leerlingoutput terechtkomen."""
    report = Report()
    haystack = _norm(json.dumps(student_payload, ensure_ascii=False))
    for answer in answers:
        needle = _norm(answer)
        if len(needle) >= 8 and needle in haystack:
            report.error(
                "answer-leak",
                f"Antwoord {answer[:40]!r} is zichtbaar in de leerlingversie.",
            )
    return report


# ---------------------------------------------------------------------------
# Hulp
# ---------------------------------------------------------------------------


_WS = re.compile(r"\s+")


def _norm(value: Any) -> str:
    text = str(value or "")
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    return _WS.sub(" ", text).strip().lower()


def load_activities(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    if isinstance(payload, dict) and "activities" in payload:
        return payload["activities"]
    if isinstance(payload, list):
        return payload
    raise ValueError(f"{path} bevat geen activiteitenlijst.")
