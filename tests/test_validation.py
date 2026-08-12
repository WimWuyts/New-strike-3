"""De validator moet geldige content doorlaten en fouten hard tegenhouden."""

from __future__ import annotations

import copy

import pytest

from conftest import build_activity_set
from lib.validation import (
    validate_activity_set,
    validate_module_evidence,
    validate_schema,
    validate_student_leak,
)

TARGET_KINDS = ["grammar_topic", "vocabulary_set"]


# ---------------------------------------------------------------------------
# Positief: een correcte reeks komt er zonder fouten door
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("target_kind", TARGET_KINDS)
def test_generated_set_passes_schema(config, target_kind):
    activities = build_activity_set(target_kind, config)
    for activity in activities:
        report = validate_schema(activity, "exercise_activity.json", activity["id"])
        assert report.ok, [str(f) for f in report.errors]


@pytest.mark.parametrize("target_kind", TARGET_KINDS)
def test_generated_set_passes_all_quotas(config, target_kind):
    activities = build_activity_set(target_kind, config)
    report = validate_activity_set(
        activities, "ace3-u1-gr-test", target_kind, config
    )
    assert report.ok, [str(f) for f in report.errors]


# ---------------------------------------------------------------------------
# Negatief: elke regel moet ook echt afgedwongen worden
# ---------------------------------------------------------------------------


def _codes(report) -> set[str]:
    return {f.code for f in report.errors}


def test_rejects_wrong_activity_count(config):
    activities = build_activity_set("grammar_topic", config)[:24]
    report = validate_activity_set(activities, "ace3-u1-gr-test", "grammar_topic", config)
    assert "count" in _codes(report)


def test_rejects_duplicate_ids(config):
    activities = build_activity_set("grammar_topic", config)
    activities[3]["id"] = activities[2]["id"]
    report = validate_activity_set(activities, "ace3-u1-gr-test", "grammar_topic", config)
    assert "duplicate-id" in _codes(report)


def test_rejects_overused_interaction_type(config):
    activities = build_activity_set("grammar_topic", config)
    ceiling = config.exercises["quotas"]["grammar_topic"]["max_uses_per_interaction_type"]
    for activity in activities[: ceiling + 2]:
        activity["interaction_type"] = "error-detective"
    report = validate_activity_set(activities, "ace3-u1-gr-test", "grammar_topic", config)
    assert "interaction-overuse" in _codes(report)


def test_rejects_unknown_interaction_type(config):
    activities = build_activity_set("grammar_topic", config)
    activities[0]["interaction_type"] = "niet-bestaand-patroon"
    report = validate_activity_set(activities, "ace3-u1-gr-test", "grammar_topic", config)
    assert "unknown-interaction" in _codes(report)


def test_rejects_empty_canonical_answer(config):
    activities = build_activity_set("grammar_topic", config)
    for activity in activities:
        for prompt in activity["prompts"]:
            if prompt["response_mode"] != "typed_paragraph":
                prompt["canonical_answers"] = ["   "]
                break
        else:
            continue
        break
    report = validate_activity_set(activities, "ace3-u1-gr-test", "grammar_topic", config)
    assert "empty-answer" in _codes(report)


def test_rejects_answer_missing_from_options(config):
    activities = build_activity_set("grammar_topic", config)
    for activity in activities:
        for prompt in activity["prompts"]:
            if prompt.get("options"):
                prompt["canonical_answers"] = ["staat-er-niet-tussen"]
                report = validate_activity_set(
                    activities, "ace3-u1-gr-test", "grammar_topic", config
                )
                assert "answer-not-in-options" in _codes(report)
                return
    pytest.skip("Deze reeks bevat geen keuzegebaseerde vragen.")


def test_rejects_hint_that_reveals_answer(config):
    activities = build_activity_set("grammar_topic", config)
    for activity in activities:
        for prompt in activity["prompts"]:
            if prompt.get("canonical_answers"):
                prompt["hints"] = [f"Het antwoord is {prompt['canonical_answers'][0]}."]
                report = validate_activity_set(
                    activities, "ace3-u1-gr-test", "grammar_topic", config
                )
                assert "hint-reveals-answer" in _codes(report)
                return
    pytest.fail("Geen enkele prompt had een canonical answer.")


def test_rejects_duplicate_prompts(config):
    activities = build_activity_set("grammar_topic", config)
    activities[5]["prompts"][0]["prompt"] = activities[4]["prompts"][0]["prompt"]
    report = validate_activity_set(activities, "ace3-u1-gr-test", "grammar_topic", config)
    assert "duplicate-prompt" in _codes(report)


def test_rejects_broken_stage_distribution(config):
    activities = build_activity_set("grammar_topic", config)
    activities[0]["stage"] = 5
    report = validate_activity_set(activities, "ace3-u1-gr-test", "grammar_topic", config)
    assert "stage-distribution" in _codes(report)


def test_rejects_target_mismatch(config):
    activities = build_activity_set("grammar_topic", config)
    activities[7]["target_id"] = "een-ander-doel"
    report = validate_activity_set(activities, "ace3-u1-gr-test", "grammar_topic", config)
    assert "target-mismatch" in _codes(report)


def test_open_production_without_rubric_is_rejected(config):
    activities = build_activity_set("grammar_topic", config)
    for activity in activities:
        for prompt in activity["prompts"]:
            if prompt["response_mode"] == "typed_paragraph":
                prompt.pop("manual_review_rubric")
                report = validate_activity_set(
                    activities, "ace3-u1-gr-test", "grammar_topic", config
                )
                assert "open-without-rubric" in _codes(report)
                return
    pytest.fail("Geen enkele activiteit gebruikte open productie.")


# ---------------------------------------------------------------------------
# Reading en listening: bewijs bij elk antwoord
# ---------------------------------------------------------------------------


READING = {
    "id": "ace3-u1-read-1",
    "text": {
        "title_en": "A day at the market",
        "paragraphs": [
            {
                "id": "p1",
                "sentences": [
                    {"id": "p1s1", "text_en": "The market opens at eight."},
                    {"id": "p1s2", "text_en": "Most stalls sell fruit."},
                ],
            }
        ],
    },
    "tasks": {
        "gist": {
            "questions": [
                {
                    "id": "q1",
                    "question": "What time does the market open?",
                    "response_mode": "typed_short",
                    "canonical_answers": ["at eight"],
                    "evidence_ref": "p1s1",
                }
            ]
        }
    },
}


def test_reading_with_valid_evidence_passes():
    report = validate_module_evidence(READING, "reading")
    assert report.ok, [str(f) for f in report.errors]


def test_reading_with_dangling_evidence_is_rejected():
    broken = copy.deepcopy(READING)
    broken["tasks"]["gist"]["questions"][0]["evidence_ref"] = "p9s9"
    report = validate_module_evidence(broken, "reading")
    assert "dangling-evidence" in _codes(report)


def test_reading_without_evidence_is_rejected():
    broken = copy.deepcopy(READING)
    broken["tasks"]["gist"]["questions"][0]["evidence_ref"] = ""
    report = validate_module_evidence(broken, "reading")
    assert "no-evidence" in _codes(report)


def test_listening_marked_built_without_path_is_rejected():
    module = {
        "id": "ace3-u1-listen-1",
        "transcript": [{"id": "s1", "speaker_id": "a", "text_en": "Hi there."}],
        "audio": {"status": "built", "path": None},
        "tasks": {
            "gist": {
                "questions": [
                    {
                        "id": "q1",
                        "question": "Who speaks first?",
                        "response_mode": "typed_short",
                        "canonical_answers": ["speaker a"],
                        "evidence_ref": "s1",
                    }
                ]
            }
        },
    }
    report = validate_module_evidence(module, "listening")
    assert "audio-inconsistent" in _codes(report)


def test_listening_accepts_timestamp_evidence():
    module = {
        "id": "ace3-u1-listen-2",
        "transcript": [{"id": "s1", "speaker_id": "a", "text_en": "Hi there."}],
        "audio": {"status": "not_built", "path": None},
        "tasks": {
            "detail": {
                "questions": [
                    {
                        "id": "q1",
                        "question": "When is the meeting?",
                        "response_mode": "typed_short",
                        "canonical_answers": ["at noon"],
                        "evidence_ref": "0:12",
                    }
                ]
            }
        },
    }
    report = validate_module_evidence(module, "listening")
    assert report.ok, [str(f) for f in report.errors]


# ---------------------------------------------------------------------------
# Scheiding leerling en leerkracht
# ---------------------------------------------------------------------------


def test_answer_leak_in_student_output_is_detected():
    student = {"slides": [{"notes": "De oplossing is have been working."}]}
    report = validate_student_leak(student, ["have been working"])
    assert "answer-leak" in _codes(report)


def test_clean_student_output_passes():
    student = {"slides": [{"body": "Vul de juiste vorm in."}]}
    report = validate_student_leak(student, ["have been working"])
    assert report.ok
