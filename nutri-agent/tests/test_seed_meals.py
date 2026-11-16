"""Seed catalogue checks. Runs generate_seed_meals() only; no Neo4j needed."""

from collections import defaultdict
from typing import get_args

import pytest

from db.seed_meals import generate_seed_meals
from models.meal import Meal
from models.user_profile import MedicalCondition, UserProfile
from tools.graphrag_tool import compatible_diet_types

MEALS = generate_seed_meals()
DIET_TYPES = get_args(UserProfile.model_fields["diet_type"].annotation)
CONDITIONS = set(get_args(MedicalCondition)) - {"none"}
SNACK_SLOTS = {"snack", "mid_morning", "afternoon_snack"}


def _ids(meals):
    return [m["id"] for m in meals]


def test_ids_are_unique():
    ids = _ids(MEALS)
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("meal", MEALS, ids=_ids(MEALS))
def test_meal_parses_into_model(meal):
    Meal(**meal)


@pytest.mark.parametrize("meal", MEALS, ids=_ids(MEALS))
def test_nutrient_panel_is_consistent(meal):
    m = meal
    atwater = 4 * m["protein"] + 4 * m["carbs"] + 9 * m["fats"]
    assert abs(m["calories"] - atwater) <= 0.12 * atwater, "calories vs 4P+4C+9F"

    assert m["net_carbs"] >= 0
    assert m["net_carbs"] == pytest.approx(m["carbs"] - m["fiber"], abs=0.05), "net_carbs = carbs - fiber"

    expected_gl = m["glycemic_index"] * m["net_carbs"] / 100
    assert m["glycemic_load"] == pytest.approx(expected_gl, abs=max(0.5, 0.05 * expected_gl)), "GL = GI * net / 100"

    assert m["saturated_fat"] <= m["fats"]
    assert m["unsaturated_fat"] == pytest.approx(m["fats"] - m["saturated_fat"], abs=1.0)

    assert 0.06 <= m["leucine"] / m["protein"] <= 0.09 + 1e-3, "leucine 6-9% of protein"


@pytest.mark.parametrize("meal", MEALS, ids=_ids(MEALS))
def test_diet_type_and_avoid_for_values_are_valid(meal):
    assert meal["diet_type"] in DIET_TYPES
    assert set(meal["avoid_for"]) <= CONDITIONS, set(meal["avoid_for"]) - CONDITIONS


@pytest.mark.parametrize("diet", DIET_TYPES)
def test_every_diet_type_has_meals_for_each_main_slot_and_a_snack(diet):
    """Counted the way the planner sees meals: compatible diet types, distinct dishes."""
    allowed = set(compatible_diet_types(diet))
    dishes = defaultdict(set)
    for m in MEALS:
        if m["diet_type"] in allowed:
            slot = "snack" if m["meal_slot"] in SNACK_SLOTS else m["meal_slot"]
            dishes[slot].add(Meal(**m).family)

    for slot in ("breakfast", "lunch", "dinner"):
        assert len(dishes[slot]) >= 2, f"{diet}: only {sorted(dishes[slot])} for {slot}"
    assert dishes["snack"], f"{diet}: no snack dish"


def test_variant_ingredients_are_listed_for_allergen_filtering():
    peanut_variants = [m for m in MEALS if "peanut" in m["name"].lower()]
    assert peanut_variants
    for m in peanut_variants:
        assert any("peanut" in ing for ing in m["ingredients"]), m["id"]
