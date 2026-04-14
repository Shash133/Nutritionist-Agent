"""Macro calculation utilities."""

from models.user_profile import UserProfile


def protein_from_lbm(lbm: float, g_per_kg: float) -> int:
    """Calculate protein target from lean body mass."""
    return round(lbm * g_per_kg)


def carbs_from_calories(calories: int, pct: float) -> int:
    """Calculate carb grams from calorie target and percentage."""
    return round(calories * pct / 4)


def fats_from_calories(calories: int, pct: float) -> int:
    """Calculate fat grams from calorie target and percentage."""
    return round(calories * pct / 9)


def remaining_fats(calories: int, protein_g: int, carbs_g: int) -> int:
    """Calculate fat grams from remaining calories after protein and carbs."""
    remaining_cal = calories - (protein_g * 4) - (carbs_g * 4)
    return max(round(remaining_cal / 9), 20)  # floor at 20g fats for hormones


def calculate_net_carbs(total_carbs: int, fiber: int) -> int:
    """Net carbs = total carbs - fiber."""
    return max(0, total_carbs - fiber)


def sugar_budget(calories: int, max_pct: float = 0.10) -> int:
    """Maximum sugar in grams — default 10% of calories."""
    return round(calories * max_pct / 4)
