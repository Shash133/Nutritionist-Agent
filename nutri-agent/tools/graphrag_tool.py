"""Meal fetcher / Neo4j semantic search proxy tool."""

from db.neo4j_client import neo4j_client
from models.user_profile import UserProfile
from models.meal import Meal

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
        diet_type=profile.diet_type,
        avoid_conditions=profile.medical_conditions,
        avoid_ids=avoid_ids,
        limit=50
    )
    
    # Filter by slot appropriateness (in real life, we might do semantic search here)
    slot_friendly = []
    
    for meal in meals:
        # A meal is slot-friendly if it explicitly targets that slot
        if meal.meal_slot == slot or meal.meal_slot == 'any':
            slot_friendly.append(meal)
            continue
            
        # fallback rules
        if slot in ["pre_workout", "mid_morning", "afternoon_snack"] and "snack" in meal.meal_slot:
            slot_friendly.append(meal)
        elif slot in ["breakfast", "lunch", "dinner"] and meal.meal_slot in ["breakfast", "lunch", "dinner"]:
            slot_friendly.append(meal)

    # If we didn't get enough slot matches, just use whatever is left for the persona
    if len(slot_friendly) < 5:
        return meals[:20]
        
    return slot_friendly[:20]
