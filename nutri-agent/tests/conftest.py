"""Shared fixtures. Tests never touch Neo4j or Gemini — those are monkeypatched."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.meal import Meal  # noqa: E402
from models.user_profile import UserProfile  # noqa: E402


@pytest.fixture
def make_meal():
    """Build a Meal with all-zero nutrients unless overridden."""
    def _make(id="m1", **overrides) -> Meal:
        data = dict(
            id=id, name=f"Meal {id}", diet_type="non_veg", meal_slot="any",
            calories=0, protein=0, leucine=0, carbs=0, net_carbs=0, sugar=0,
            fiber=0, fats=0, saturated_fat=0, unsaturated_fat=0, omega3=0,
            omega6=0, glycemic_index=0, glycemic_load=0, sodium=0, potassium=0,
            calcium=0, magnesium=0, iron=0, zinc=0, phosphorus=0, vitamin_d=0,
            vitamin_b12=0, folate=0, vitamin_c=0, vitamin_k=0, cost=0,
            prep_time_min=0,
        )
        data.update(overrides)
        return Meal(**data)
    return _make


@pytest.fixture
def make_profile():
    def _make(**overrides) -> UserProfile:
        data = dict(
            age=30, gender="male", weight=80.0, height=180.0,
            activity_level="moderate", persona="office_worker",
            goal="maintenance", diet_type="non_veg", budget_per_day=1000.0,
            meals_per_day=3,
        )
        data.update(overrides)
        return UserProfile(**data)
    return _make
