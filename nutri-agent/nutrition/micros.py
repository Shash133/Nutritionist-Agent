"""Micronutrient target computation based on demographics."""

from models.user_profile import UserProfile
from models.meal_plan import MicroTargets


def get_baseline_micros(profile: UserProfile) -> MicroTargets:
    """
    Returns baseline RDA/AI micronutrient targets based on age, gender.
    Does NOT apply persona-specific overrides — those come from the persona engine.
    """
    is_male = profile.gender == "male"
    age = profile.age

    # Iron: higher for premenopausal females
    if is_male or age >= 51:
        iron = 8.0
    else:
        iron = 18.0

    # Calcium: higher for teens (1300), elderly (1200), otherwise 1000
    if age <= 18:
        calcium = 1300
    elif age >= 51:
        calcium = 1200
    else:
        calcium = 1000

    # Magnesium: varies by age and gender
    if age <= 18:
        magnesium = 360 if not is_male else 410
    else:
        magnesium = 320 if not is_male else 420

    # Vitamin D: 600 IU for most, 800 IU for 70+
    vitamin_d = 800 if age >= 70 else 600

    return MicroTargets(
        sodium_max=2300,
        potassium_min=3400 if is_male else 2600,
        calcium_min=calcium,
        magnesium_min=magnesium,
        iron_min=iron,
        zinc_min=11 if is_male else 8,
        phosphorus_max=None,
        vitamin_d_min=vitamin_d,
        vitamin_b12_min=2.4,
        folate_min=400,
        vitamin_c_min=90 if is_male else 75,
    )
