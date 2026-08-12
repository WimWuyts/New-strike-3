"""Bouwt een quotaconform blueprint voor een reeks van 25 activiteiten.

Het probleem dat dit oplost: de quota uit sectie 11 zijn met de hand lastig te
halen, en fouten komen pas bij validatie boven water. Deze module kiest vooraf
een verdeling die per constructie aan alle eisen voldoet. De inhoudsauteur
vult daarna alleen nog de echte leerinhoud in.

Volledig deterministisch: dezelfde invoer geeft altijd hetzelfde blueprint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import interactions
from .interactions import InteractionPattern

# Moeilijkheid per stage. Loopt op, zodat de gemiddelde moeilijkheid nooit daalt.
STAGE_DIFFICULTY: dict[int, list[str]] = {
    1: ["support", "support", "core", "core", "core"],
    2: ["support", "core", "core", "core", "core"],
    3: ["core", "core", "core", "core", "challenge"],
    4: ["core", "core", "core", "challenge", "challenge"],
    5: ["core", "core", "challenge", "challenge", "challenge"],
}

# Welke configuratiesleutel bij welke categorie hoort.
CATEGORY_QUOTA_KEYS: dict[str, str] = {
    "min_error_repair_activities": interactions.CAT_ERROR_REPAIR,
    "min_transformation_activities": interactions.CAT_TRANSFORMATION,
    "min_mini_writing_activities": interactions.CAT_MINI_WRITING,
    "min_collocation_activities": interactions.CAT_COLLOCATION,
    "min_word_family_activities": interactions.CAT_WORD_FAMILY,
    "min_register_context_activities": interactions.CAT_REGISTER,
}


class BlueprintError(RuntimeError):
    """De quota zijn met de huidige catalogus niet haalbaar."""


@dataclass
class Slot:
    sequence: int
    stage: int
    difficulty: str
    interaction_type: str

    def to_json(self, target_id: str, target_kind: str) -> dict[str, Any]:
        pattern = interactions.get(self.interaction_type)
        return {
            "id": f"{target_id}-act-{self.sequence:02d}",
            "target_id": target_id,
            "target_kind": target_kind,
            "sequence": self.sequence,
            "stage": self.stage,
            "difficulty": self.difficulty,
            "interaction_type": self.interaction_type,
            "_pattern_label_nl": pattern.label_nl,
            "_pattern_description_nl": pattern.description_nl,
            "_expected_response_mode": pattern.primary_response_mode,
        }


def build(target_kind: str, quotas: dict[str, Any], total: int = 25) -> list[Slot]:
    """Kiest voor elk van de 25 slots een passend interactiepatroon."""
    if total % 5 != 0:
        raise BlueprintError(f"Aantal activiteiten moet deelbaar door 5 zijn, kreeg {total}.")
    per_stage = total // 5

    ceiling = quotas["max_uses_per_interaction_type"]
    min_typed = quotas["min_typed_answer_activities"]
    max_mc = quotas["max_multiple_choice_activities"]
    min_distinct = quotas["min_distinct_interaction_types"]

    slots: list[Slot | None] = [None] * total
    usage: dict[str, int] = {}

    def stage_of(index: int) -> int:
        return index // per_stage + 1

    def candidates(index: int) -> list[InteractionPattern]:
        return sorted(
            interactions.for_stage(stage_of(index), target_kind),
            key=lambda p: p.key,
        )

    def place(index: int, pattern: InteractionPattern) -> None:
        stage = stage_of(index)
        position = index % per_stage
        slots[index] = Slot(
            sequence=index + 1,
            stage=stage,
            difficulty=STAGE_DIFFICULTY[stage][position],
            interaction_type=pattern.key,
        )
        usage[pattern.key] = usage.get(pattern.key, 0) + 1

    def free_indices() -> list[int]:
        return [i for i, slot in enumerate(slots) if slot is None]

    def neighbour_keys(index: int) -> set[str]:
        """Patronen die vlak voor of na dit slot al staan.

        Twee keer hetzelfde patroon binnen drie activiteiten voelt voor de
        leerling als herhaling, ook al blijft het binnen het plafond.
        """
        keys = set()
        for offset in (-2, -1, 1, 2):
            neighbour = index + offset
            if 0 <= neighbour < total and slots[neighbour] is not None:
                keys.add(slots[neighbour].interaction_type)
        return keys

    # -- 1. verplichte categorieen eerst ----------------------------------
    # Deze zijn het schaarst, dus ze krijgen voorrang bij de slotkeuze.
    for quota_key, category in CATEGORY_QUOTA_KEYS.items():
        needed = quotas.get(quota_key, 0)
        if not needed:
            continue
        placed = 0
        # Eerst een ronde waarin alleen nog ongebruikte patronen tellen. Dat
        # spreidt een categorie over de stages waar ze past, in plaats van ze
        # allemaal in de vroegste stage te proppen.
        for require_unused in (True, False):
            for index in free_indices():
                if placed >= needed:
                    break
                options = [
                    p
                    for p in candidates(index)
                    if category in p.categories and usage.get(p.key, 0) < ceiling
                ]
                if require_unused:
                    options = [p for p in options if usage.get(p.key, 0) == 0]
                if not options:
                    continue
                # Vermijd hetzelfde patroon vlak naast een eerder slot.
                nearby = neighbour_keys(index)
                options.sort(key=lambda p: (p.key in nearby, usage.get(p.key, 0), p.key))
                place(index, options[0])
                placed += 1
            if placed >= needed:
                break
        if placed < needed:
            raise BlueprintError(
                f"Categorie {category!r} vraagt {needed} activiteiten, "
                f"maar er passen er maar {placed} in de beschikbare stages."
            )

    # -- 2. resterende slots: eerst diversiteit, dan getypte antwoorden ----
    for index in free_indices():
        options = [p for p in candidates(index) if usage.get(p.key, 0) < ceiling]
        if not options:
            raise BlueprintError(
                f"Geen bruikbaar patroon meer voor stage {stage_of(index)} "
                f"binnen het plafond van {ceiling} gebruiken per patroon."
            )

        mc_so_far = sum(
            1
            for slot in slots
            if slot is not None and interactions.get(slot.interaction_type).is_multiple_choice
        )

        nearby = neighbour_keys(index)

        def rank(pattern: InteractionPattern) -> tuple[int, int, int, int, str]:
            # Meerkeuze alleen als we onder het plafond blijven.
            mc_penalty = 1 if (pattern.is_multiple_choice and mc_so_far >= max_mc) else 0
            adjacency_penalty = 1 if pattern.key in nearby else 0
            unused = 0 if usage.get(pattern.key, 0) == 0 else 1
            typed_bonus = 0 if pattern.is_typed else 1
            return (mc_penalty, adjacency_penalty, unused, typed_bonus, pattern.key)

        options.sort(key=rank)
        place(index, options[0])

    result = [slot for slot in slots if slot is not None]
    _verify(result, quotas, min_typed, max_mc, min_distinct, ceiling)
    return result


def _verify(
    slots: list[Slot],
    quotas: dict[str, Any],
    min_typed: int,
    max_mc: int,
    min_distinct: int,
    ceiling: int,
) -> None:
    patterns = [interactions.get(s.interaction_type) for s in slots]

    typed = sum(1 for p in patterns if p.is_typed)
    if typed < min_typed:
        raise BlueprintError(f"Blueprint haalt {typed} getypte activiteiten, minimaal {min_typed}.")

    mc = sum(1 for p in patterns if p.is_multiple_choice)
    if mc > max_mc:
        raise BlueprintError(f"Blueprint heeft {mc} meerkeuze-activiteiten, maximaal {max_mc}.")

    distinct = len({p.key for p in patterns})
    if distinct < min_distinct:
        raise BlueprintError(
            f"Blueprint gebruikt {distinct} verschillende patronen, minimaal {min_distinct}."
        )

    counts: dict[str, int] = {}
    for pattern in patterns:
        counts[pattern.key] = counts.get(pattern.key, 0) + 1
    for key, count in counts.items():
        if count > ceiling:
            raise BlueprintError(f"Patroon {key!r} komt {count}x voor, maximaal {ceiling}.")

    for quota_key, category in CATEGORY_QUOTA_KEYS.items():
        needed = quotas.get(quota_key, 0)
        if not needed:
            continue
        actual = sum(1 for p in patterns if category in p.categories)
        if actual < needed:
            raise BlueprintError(
                f"Blueprint haalt {actual} activiteiten in categorie {category!r}, "
                f"minimaal {needed}."
            )
