"""Master nutrition engine — BMR, TDEE, persona dispatch."""

from models.user_profile import UserProfile
from models.meal_plan import NutritionTargets
from personas.gym_bro import GymBroPersona
from personas.athlete import AthletePersona
from personas.patient import PatientPersona
from personas.elderly import ElderlyPersona
from personas.pregnant import PregnantPersona
from personas.teenager import TeenPersona
from personas.office_worker import OfficeWorkerPersona


# ── Activity multipliers (Harris-Benedict / Mifflin-St Jeor) ─────────────────
ACTIVITY_MULTIPLIERS = {
    "sedentary":      1.2,
    "lightly_active": 1.375,
    "moderate":       1.55,
    "very_active":    1.725,
    "athlete":        1.9,
}

# ── Persona registry ─────────────────────────────────────────────────────────
PERSONA_MAP = {
    "gym_bro":       GymBroPersona(),
    "athlete":       AthletePersona(),
    "patient":       PatientPersona(),
    "elderly":       ElderlyPersona(),
    "pregnant":      PregnantPersona(),
    "teenager":      TeenPersona(),
    "office_worker": OfficeWorkerPersona(),
}


def calculate_bmr(profile: UserProfile) -> float:
    """
    Mifflin-St Jeor equation.
    Males:   10 × weight(kg) + 6.25 × height(cm) − 5 × age + 5
    Females: 10 × weight(kg) + 6.25 × height(cm) − 5 × age − 161
    Other:   midpoint of the two constants (−78); the equation has no neutral form.
    """
    base = 10 * profile.weight + 6.25 * profile.height - 5 * profile.age
    if profile.gender == "male":
        return base + 5
    if profile.gender == "female":
        return base - 161
    return base - 78


def calculate_tdee(bmr: float, profile: UserProfile) -> float:
    """TDEE = BMR × activity multiplier."""
    multiplier = ACTIVITY_MULTIPLIERS.get(profile.activity_level, 1.2)
    return bmr * multiplier


def get_nutrition_targets(profile: UserProfile) -> NutritionTargets:
    """
    Master function: resolves persona, computes BMR/TDEE, calls persona-specific
    target computation. This is the single entry point for all target calculations.
    """
    bmr = calculate_bmr(profile)
    tdee = calculate_tdee(bmr, profile)
    persona = PERSONA_MAP[profile.persona]
    return persona.compute_targets(profile, bmr, tdee)
