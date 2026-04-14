"""Office Worker persona — sedentary baseline, stress management nutrition."""

from personas.base import PersonaBase
from models.user_profile import UserProfile
from models.meal_plan import (
    NutritionTargets, MacroTargets, MicroTargets, TimingTargets,
)


class OfficeWorkerPersona(PersonaBase):
    """
    Standard maintenance persona for sedentary / lightly active workers.
    Focus: balanced nutrition, stress management, longevity markers.
    Moderate protein (1.2–1.6 g/kg), balanced carbs.
    """

    GOAL_CALORIE_MODIFIER = {
        "fat_loss":     -400,
        "muscle_gain":  +200,
        "maintenance":     0,
        "performance":     0,
        "clinical":        0,
        "longevity":    -100,   # slight deficit for longevity
    }

    def compute_targets(
        self, profile: UserProfile, bmr: float, tdee: float
    ) -> NutritionTargets:
        cal_modifier = self.GOAL_CALORIE_MODIFIER.get(profile.goal, 0)
        calories = round(tdee + cal_modifier)

        protein_per_kg = 1.4 if profile.goal == "muscle_gain" else 1.2
        protein_g = round(protein_per_kg * profile.lean_body_mass)

        carb_pct = 0.45
        fat_pct = 0.30
        carbs_g = round(calories * carb_pct / 4)
        fats_g = round(calories * fat_pct / 9)

        macros = MacroTargets(
            calories=calories,
            protein=protein_g,
            protein_per_kg_lbm=protein_per_kg,
            leucine_per_meal=2.0,
            carbs=carbs_g,
            net_carbs=round(carbs_g * 0.85),
            fiber=max(25, round(carbs_g * 0.1)),
            fats=fats_g,
            saturated_fat_max=round(fats_g * 0.3),
            omega3_min=2.0,
            sugar_max=40,
            glycemic_load_max=20,
        )

        micros = MicroTargets(
            sodium_max=2300,
            potassium_min=3500,
            calcium_min=1000,
            magnesium_min=420 if profile.gender == "male" else 320,
            iron_min=8 if profile.gender == "male" else 18,
            zinc_min=11 if profile.gender == "male" else 8,
            phosphorus_max=None,
            vitamin_d_min=1000,
            vitamin_b12_min=2.4,
            folate_min=400,
            vitamin_c_min=90,
        )

        timing = TimingTargets(
            pre_workout_carbs=0,
            pre_workout_protein=0,
            post_workout_protein=0,
            post_workout_carbs=0,
            before_bed_protein=15,
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
            persona="office_worker",
            notes=notes,
        )

    def get_supplement_stack(self, profile: UserProfile) -> list[str]:
        stack = [
            "vitamin D3 1000IU/day (especially if indoor worker)",
            "omega-3 fish oil 1–2g EPA+DHA/day",
            "magnesium glycinate 200mg before bed (stress + sleep)",
        ]
        if profile.supplement_openness == "advanced":
            stack += [
                "ashwagandha 300mg/day (cortisol management)",
                "B-complex vitamin (energy metabolism)",
                "probiotics (gut health for sedentary lifestyle)",
            ]
        return stack

    def get_medical_notes(self, profile: UserProfile) -> list[str]:
        notes = [
            "Sedentary lifestyle increases metabolic disease risk — "
            "prioritise whole foods, fibre, and omega-3."
        ]
        if profile.goal == "fat_loss":
            notes.append(
                "Moderate caloric deficit. Increase non-exercise activity "
                "(walking, standing desk) for better TDEE."
            )
        return notes
