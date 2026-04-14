"""Elderly persona — sarcopenia prevention, bone health, B12 absorption."""

from personas.base import PersonaBase
from models.user_profile import UserProfile
from models.meal_plan import (
    NutritionTargets, MacroTargets, MicroTargets, TimingTargets,
)


class ElderlyPersona(PersonaBase):
    """
    Higher protein to combat sarcopenia (muscle loss with age).
    Calcium + Vitamin D for osteoporosis prevention.
    B12 absorption decreases with age.
    Leucine threshold same as gym_bro — critical for MPS in elderly.
    Sodium restriction if hypertension present.
    """

    GOAL_CALORIE_MODIFIER = {
        "fat_loss":     -300,
        "muscle_gain":  +150,
        "maintenance":     0,
        "longevity":    -100,
        "performance":     0,
        "clinical":        0,
    }

    def compute_targets(
        self, profile: UserProfile, bmr: float, tdee: float
    ) -> NutritionTargets:
        cal_modifier = self.GOAL_CALORIE_MODIFIER.get(profile.goal, 0)
        calories = round(tdee + cal_modifier)

        # Higher protein than RDA (0.8) to combat sarcopenia
        protein_per_kg = 1.6
        protein_g = round(protein_per_kg * profile.lean_body_mass)

        carb_pct = 0.45
        fat_pct = 0.30
        carbs_g = round(calories * carb_pct / 4)
        fats_g = round(calories * fat_pct / 9)

        macros = MacroTargets(
            calories=calories,
            protein=protein_g,
            protein_per_kg_lbm=protein_per_kg,
            leucine_per_meal=2.5,   # same as gym_bro — critical for MPS in elderly
            carbs=carbs_g,
            net_carbs=round(carbs_g * 0.85),
            fiber=max(25, round(carbs_g * 0.1)),
            fats=fats_g,
            saturated_fat_max=round(fats_g * 0.3),
            omega3_min=2.0,
            sugar_max=35,
            glycemic_load_max=18,
        )

        micros = MicroTargets(
            sodium_max=1500,            # lower for cardiovascular health
            potassium_min=4700,
            calcium_min=1200,           # osteoporosis prevention
            magnesium_min=420,
            iron_min=8,                 # post-menopausal: lower
            zinc_min=11,
            phosphorus_max=None,
            vitamin_d_min=2000,         # deficiency rampant in elderly
            vitamin_b12_min=2.4,        # crystalline B12 better absorbed
            folate_min=400,
            vitamin_c_min=90,
        )

        timing = TimingTargets(
            pre_workout_carbs=20 if profile.workout_time != "none" else 0,
            pre_workout_protein=15 if profile.workout_time != "none" else 0,
            post_workout_protein=25 if profile.workout_time != "none" else 0,
            post_workout_carbs=30 if profile.workout_time != "none" else 0,
            before_bed_protein=25,  # casein for overnight MPS
            meal_frequency=profile.meals_per_day,
            protein_per_meal_min=round(protein_g / profile.meals_per_day),
        )

        supplements = self.get_supplement_stack(profile)
        notes = self.get_medical_notes(profile)

        return NutritionTargets(
            macros=macros,
            micros=micros,
            timing=timing,
            supplement_stack=supplements,
            persona="elderly",
            notes=notes,
        )

    def get_supplement_stack(self, profile: UserProfile) -> list[str]:
        stack = [
            "vitamin D3 2000IU/day",
            "calcium citrate 500mg 2x/day (if dietary intake < 1200mg)",
            "vitamin B12 1000mcg/day (sublingual — bypasses absorption issues)",
            "omega-3 fish oil 2g EPA+DHA/day",
        ]
        if profile.supplement_openness != "none":
            stack += [
                "creatine monohydrate 3–5g/day (sarcopenia prevention)",
                "HMB 3g/day (muscle preservation)",
            ]
        if profile.supplement_openness == "advanced":
            stack += [
                "CoQ10 100mg/day (mitochondrial health)",
                "collagen peptides 10g/day (joint + bone support)",
            ]
        return stack

    def get_medical_notes(self, profile: UserProfile) -> list[str]:
        notes = [
            "Protein distribution: spread evenly across meals for optimal MPS — "
            "≥25g per meal with ≥2.5g leucine.",
            "Hydration often reduced with age — aim for 1.5–2L water daily.",
        ]
        if profile.age >= 75:
            notes.append(
                "Age 75+: consider soft-textured foods if chewing is difficult. "
                "Protein shakes can supplement meals."
            )
        return notes
