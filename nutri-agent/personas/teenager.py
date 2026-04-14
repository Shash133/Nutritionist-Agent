"""Teenager persona — growth-adjusted targets, peak bone density window."""

from personas.base import PersonaBase
from models.user_profile import UserProfile
from models.meal_plan import (
    NutritionTargets, MacroTargets, MicroTargets, TimingTargets,
)


class TeenPersona(PersonaBase):
    """
    Calories higher for growth. Calcium critical (peak bone density window).
    Iron critical for girls post-puberty.
    Restrict: energy drinks, excess caffeine.
    """

    def compute_targets(
        self, profile: UserProfile, bmr: float, tdee: float
    ) -> NutritionTargets:
        calories = round(tdee * 1.05)  # +5% for growth
        protein_per_kg = 1.6           # g/kg — higher for growth
        protein_g = round(protein_per_kg * profile.weight)

        carb_pct = 0.50   # higher carbs for growing bodies
        fat_pct = 0.28
        carbs_g = round(calories * carb_pct / 4)
        fats_g = round(calories * fat_pct / 9)

        macros = MacroTargets(
            calories=calories,
            protein=protein_g,
            protein_per_kg_lbm=protein_per_kg,
            leucine_per_meal=2.0,
            carbs=carbs_g,
            net_carbs=round(carbs_g * 0.85),
            fiber=max(20, round(carbs_g * 0.08)),
            fats=fats_g,
            saturated_fat_max=round(fats_g * 0.3),
            omega3_min=1.6,
            sugar_max=50,
            glycemic_load_max=22,
        )

        micros = MicroTargets(
            sodium_max=2300,
            potassium_min=4500,
            calcium_min=1300,   # PEAK BONE DENSITY WINDOW — highest of any age
            magnesium_min=360 if profile.gender == "female" else 410,
            iron_min=15 if profile.gender == "female" else 11,  # menstrual losses
            zinc_min=9 if profile.gender == "female" else 11,
            phosphorus_max=None,
            vitamin_d_min=600,
            vitamin_b12_min=2.4,
            folate_min=400,
            vitamin_c_min=65,
        )

        timing = TimingTargets(
            pre_workout_carbs=30 if profile.workout_time != "none" else 0,
            pre_workout_protein=15 if profile.workout_time != "none" else 0,
            post_workout_protein=25 if profile.workout_time != "none" else 0,
            post_workout_carbs=40 if profile.workout_time != "none" else 0,
            before_bed_protein=20,
            meal_frequency=max(profile.meals_per_day, 4),  # regular meals important
            protein_per_meal_min=round(
                protein_g / max(profile.meals_per_day, 4)
            ),
        )

        supplements = self.get_supplement_stack(profile)
        notes = self.get_medical_notes(profile)

        return NutritionTargets(
            macros=macros,
            micros=micros,
            timing=timing,
            supplement_stack=supplements,
            persona="teenager",
            notes=notes,
        )

    def get_supplement_stack(self, profile: UserProfile) -> list[str]:
        stack = [
            "vitamin D3 600IU/day (bone development)",
        ]
        if profile.gender == "female":
            stack.append("iron supplement 15mg/day (if dietary intake insufficient)")
        if profile.supplement_openness != "none":
            stack.append("omega-3 fish oil 1g/day (brain development)")
        if profile.supplement_openness == "advanced":
            stack.append("creatine 3g/day (shown safe for adolescent athletes)")
        return stack

    def get_medical_notes(self, profile: UserProfile) -> list[str]:
        notes = [
            "Avoid energy drinks and excess caffeine (limit <100mg/day).",
            "This is the PEAK BONE DENSITY window — calcium + vitamin D "
            "intake now determines lifelong bone health.",
            "Do NOT restrict calories severely — growth requires adequate energy.",
        ]
        if profile.goal == "fat_loss":
            notes.append(
                "WARNING: Aggressive caloric restriction in teenagers can impair "
                "growth and development. Max deficit should be 200–300 kcal."
            )
        if profile.gender == "female":
            notes.append(
                "Iron needs increase post-puberty due to menstrual losses. "
                "Include heme iron sources (meat) or iron-fortified foods."
            )
        return notes
