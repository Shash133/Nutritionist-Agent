"""Supplement stack recommender — merges persona + medical supplement lists."""

from models.user_profile import UserProfile
from models.meal_plan import NutritionTargets


def merge_supplement_stacks(
    persona_stack: list[str],
    medical_stack: list[str],
    profile: UserProfile,
) -> list[str]:
    """
    Merge persona and medical supplement stacks, deduplicating
    and adding universal recommendations.
    """
    combined = list(persona_stack)

    for item in medical_stack:
        # Simple dedup by checking if the supplement name (first word) exists
        item_base = item.split()[0].lower()
        if not any(item_base in s.lower() for s in combined):
            combined.append(item)

    return combined


def flag_supplement_for_deficiency(
    nutrient: str, actual: float, target: float
) -> str | None:
    """
    If a nutrient target can't be met through food alone,
    flag a supplement recommendation.
    """
    deficit_pct = (target - actual) / target * 100 if target > 0 else 0

    SUPPLEMENT_MAP = {
        "vitamin_d":  "Vitamin D3 supplement recommended (dietary sources limited)",
        "vitamin_b12": "Vitamin B12 supplement recommended (especially for plant-based diets)",
        "iron":       "Iron bisglycinate supplement recommended (take with vitamin C)",
        "calcium":    "Calcium citrate supplement recommended (split doses with meals)",
        "omega3":     "Omega-3 fish oil supplement recommended (EPA+DHA)",
        "folate":     "Folic acid supplement recommended (especially for pregnancy planning)",
        "zinc":       "Zinc supplement recommended (avoid taking with iron)",
        "magnesium":  "Magnesium glycinate supplement recommended (before bed)",
    }

    if deficit_pct > 20 and nutrient in SUPPLEMENT_MAP:
        return SUPPLEMENT_MAP[nutrient]
    return None
