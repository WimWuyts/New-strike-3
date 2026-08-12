"""De blueprintgenerator moet per constructie aan alle quota voldoen."""

from __future__ import annotations

import pytest

from lib import blueprint as blueprint_lib
from lib import interactions


TARGET_KINDS = ["grammar_topic", "vocabulary_set"]


def test_catalogue_has_at_least_35_patterns():
    assert len(interactions.CATALOGUE) >= 35


def test_catalogue_keys_are_consistent():
    for key, pattern in interactions.CATALOGUE.items():
        assert pattern.key == key
        assert pattern.stages, f"{key} heeft geen stages"
        assert pattern.targets, f"{key} heeft geen doeltypes"


@pytest.mark.parametrize("target_kind", TARGET_KINDS)
def test_blueprint_has_exactly_25_slots(config, target_kind):
    quotas = config.exercises["quotas"][target_kind]
    slots = blueprint_lib.build(target_kind, quotas, total=25)
    assert len(slots) == 25
    assert [s.sequence for s in slots] == list(range(1, 26))


@pytest.mark.parametrize("target_kind", TARGET_KINDS)
def test_blueprint_spreads_stages_evenly(config, target_kind):
    quotas = config.exercises["quotas"][target_kind]
    slots = blueprint_lib.build(target_kind, quotas, total=25)
    for stage in range(1, 6):
        assert sum(1 for s in slots if s.stage == stage) == 5


@pytest.mark.parametrize("target_kind", TARGET_KINDS)
def test_blueprint_respects_typed_and_choice_quotas(config, target_kind):
    quotas = config.exercises["quotas"][target_kind]
    slots = blueprint_lib.build(target_kind, quotas, total=25)
    patterns = [interactions.get(s.interaction_type) for s in slots]

    typed = sum(1 for p in patterns if p.is_typed)
    assert typed >= quotas["min_typed_answer_activities"]

    choice = sum(1 for p in patterns if p.is_multiple_choice)
    assert choice <= quotas["max_multiple_choice_activities"]


@pytest.mark.parametrize("target_kind", TARGET_KINDS)
def test_blueprint_respects_diversity(config, target_kind):
    quotas = config.exercises["quotas"][target_kind]
    slots = blueprint_lib.build(target_kind, quotas, total=25)

    used = [s.interaction_type for s in slots]
    assert len(set(used)) >= quotas["min_distinct_interaction_types"]
    for key in set(used):
        assert used.count(key) <= quotas["max_uses_per_interaction_type"]


@pytest.mark.parametrize("target_kind", TARGET_KINDS)
def test_blueprint_uses_patterns_valid_for_their_stage(config, target_kind):
    quotas = config.exercises["quotas"][target_kind]
    slots = blueprint_lib.build(target_kind, quotas, total=25)
    for slot in slots:
        pattern = interactions.get(slot.interaction_type)
        assert slot.stage in pattern.stages
        assert target_kind in pattern.targets


@pytest.mark.parametrize("target_kind", TARGET_KINDS)
def test_blueprint_is_deterministic(config, target_kind):
    quotas = config.exercises["quotas"][target_kind]
    first = blueprint_lib.build(target_kind, quotas, total=25)
    second = blueprint_lib.build(target_kind, quotas, total=25)
    assert [s.interaction_type for s in first] == [s.interaction_type for s in second]


@pytest.mark.parametrize("target_kind", TARGET_KINDS)
def test_difficulty_never_regresses_between_stages(config, target_kind):
    quotas = config.exercises["quotas"][target_kind]
    slots = blueprint_lib.build(target_kind, quotas, total=25)
    ranks = {"support": 0, "core": 1, "challenge": 2}

    means = []
    for stage in range(1, 6):
        stage_slots = [s for s in slots if s.stage == stage]
        means.append(sum(ranks[s.difficulty] for s in stage_slots) / len(stage_slots))

    assert means == sorted(means), f"Moeilijkheid daalt: {means}"


def test_blueprint_rejects_impossible_quota(config):
    quotas = dict(config.exercises["quotas"]["grammar_topic"])
    quotas["min_distinct_interaction_types"] = 99
    with pytest.raises(blueprint_lib.BlueprintError):
        blueprint_lib.build("grammar_topic", quotas, total=25)
