"""Meal fetcher / Neo4j semantic search proxy tool."""

from db.neo4j_client import neo4j_client
from models.user_profile import UserProfile
from models.meal import Meal

# Meal diet types each user diet can eat: less restrictive diets include the
# stricter ones (a non-veg user can eat veg meals). Pattern diets (keto, paleo,
# mediterranean, low_fodmap) are not supersets of anything, so match exactly.
COMPATIBLE_DIET_TYPES = {
    "vegan":      ["vegan"],
    "veg":        ["veg", "vegan"],
    "eggetarian": ["eggetarian", "veg", "vegan"],
    "non_veg":    ["non_veg", "eggetarian", "veg", "vegan"],
}


MAX_VARIANTS_PER_DISH = 3


def compatible_diet_types(diet_type: str) -> list[str]:
    return COMPATIBLE_DIET_TYPES.get(diet_type, [diet_type])


def fetch_suitable_meals_for_slot(
    slot: str, profile: UserProfile, avoid_ids: list[str] | None = None
) -> list[Meal]:
    """
    Simulates a GraphRAG approach by using Neo4j exact matches + tags
    rather than a full semantic embedding model for simplicity, but easily
    replaceable with sentence-transformers + vector index in a real setup.
    """
    # Fetch generally suitable meals for the persona
    meals = neo4j_client.get_meals_for_persona(
        persona=profile.persona,
        diet_types=compatible_diet_types(profile.diet_type),
        avoid_conditions=profile.medical_conditions,
        avoid_ids=avoid_ids,
        exclude_terms=profile.allergies + profile.intolerances + profile.dislikes,
        limit=200,  # whole catalogue is small; variants are capped below
    )
    
    # Variants of one recipe would otherwise fill the pool and crowd out other dishes.
    meals = _cap_variants(meals, MAX_VARIANTS_PER_DISH)

    # Rank by slot fit (in real life, we might do semantic search here):
    # exact slot first, then compatible slots, then everything else as a last resort.
    exact, compatible, other = [], [], []
    for meal in meals:
        if meal.meal_slot == slot or meal.meal_slot == 'any':
            exact.append(meal)
        elif slot in ["pre_workout", "mid_morning", "afternoon_snack"] and "snack" in meal.meal_slot:
            compatible.append(meal)
        elif slot in ["breakfast", "lunch", "dinner"] and meal.meal_slot in ["breakfast", "lunch", "dinner"]:
            compatible.append(meal)
        else:
            other.append(meal)

    return (exact + compatible + other)[:20]


def _cap_variants(meals: list[Meal], max_per_dish: int) -> list[Meal]:
    """Keep at most `max_per_dish` variants of each recipe, preserving order."""
    counts: dict[str, int] = {}
    kept = []
    for meal in meals:
        counts[meal.family] = counts.get(meal.family, 0) + 1
        if counts[meal.family] <= max_per_dish:
            kept.append(meal)
    return kept
