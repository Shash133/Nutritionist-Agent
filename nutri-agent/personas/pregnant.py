"""Pregnant persona — trimester-aware calorie, protein, folate, iron targets."""

from personas.base import PersonaBase
from models.user_profile import UserProfile
from models.meal_plan import (
    NutritionTargets, MacroTargets, MicroTargets, TimingTargets,
)


# Trimester-specific adjustments
TRIMESTER_EXTRA_CALORIES = {
    "first": 0,
    "second": +340,
    "third": +452,
    "postpartum": +500,
}

TRIMESTER_EXTRA_PROTEIN = {
    "first": 0,
    "second": +25,
    "third": +25,
    "postpartum": +25,
}


class PregnantPersona(PersonaBase):
    """
    Folate is CRITICAL in first trimester (neural tube development).
    Iron nearly doubles. Omega-3 DHA critical for brain development.
    Avoid: raw fish, deli meats, high-mercury fish, unpasteurised dairy.
    """

    def compute_targets(
        self, profile: UserProfile, bmr: float, tdee: float
    ) -> NutritionTargets:
        tri = profile.pregnancy_trimester
        if tri == "none":
            tri = "second"  # safe default

        extra_cal = TRIMESTER_EXTRA_CALORIES[tri]
        extra_prot = TRIMESTER_EXTRA_PROTEIN[tri]

        calories = round(tdee + extra_cal)
        protein_g = round(0.88 * profile.weight + extra_prot)

        carb_pct = 0.50  # higher carbs for maternal energy
        fat_pct = 0.30
        carbs_g = round(calories * carb_pct / 4)
        fats_g = round(calories * fat_pct / 9)

        macros = MacroTargets(
            calories=calories,
            protein=protein_g,
            protein_per_kg_lbm=round(protein_g / profile.lean_body_mass, 2),
            leucine_per_meal=2.0,
            carbs=carbs_g,
            net_carbs=round(carbs_g * 0.85),
            fiber=max(28, round(carbs_g * 0.1)),  # constipation common in pregnancy
            fats=fats_g,
            saturated_fat_max=round(fats_g * 0.3),
            omega3_min=2.5,           # DHA critical for fetal brain
            sugar_max=45,
            glycemic_load_max=20,
        )

        micros = MicroTargets(
            sodium_max=2300,
            potassium_min=2900,
            calcium_min=1000,
            magnesium_min=350,
            iron_min=27,              # doubled from baseline — fetal + maternal
            zinc_min=11,
            phosphorus_max=None,
            vitamin_d_min=600,
            vitamin_b12_min=2.6,
            folate_min=600 if tri == "first" else 400,  # neural tube critical
            vitamin_c_min=85,
        )

        timing = TimingTargets(
            pre_workout_carbs=0,
            pre_workout_protein=0,
            post_workout_protein=0,
            post_workout_carbs=0,
            before_bed_protein=20,
            meal_frequency=max(profile.meals_per_day, 5),  # frequent small meals
            protein_per_meal_min=round(
                protein_g / max(profile.meals_per_day, 5)
            ),
        )

        supplements = self.get_supplement_stack(profile)
        notes = self.get_medical_notes(profile)

        return NutritionTargets(
            macros=macros,
            micros=micros,
            timing=timing,
            supplement_stack=supplements,
            persona="pregnant",
            notes=notes,
        )

    def get_supplement_stack(self, profile: UserProfile) -> list[str]:
        tri = profile.pregnancy_trimester
        stack = [
            "prenatal multivitamin (with 600mcg folic acid)",
            "DHA omega-3 200–300mg/day (fetal brain development)",
            "iron bisglycinate 27mg/day (if not in prenatal)",
        ]
        if tri == "first":
            stack.append(
                "ginger supplements or crackers for morning sickness"
            )
        if tri in ["third", "postpartum"]:
            stack.append("calcium citrate 500mg/day (if dairy intake low)")
        if tri == "postpartum":
            stack.append(
                "vitamin D3 2000IU/day (especially if breastfeeding)"
            )
        return stack

    def get_medical_notes(self, profile: UserProfile) -> list[str]:
        tri = profile.pregnancy_trimester
        extra_cal = TRIMESTER_EXTRA_CALORIES.get(tri, 0)

        notes = [
            "Avoid raw fish, deli meats, high-mercury fish "
            "(shark, swordfish, king mackerel)",
            "Avoid unpasteurised cheeses and juices",
            "DHA omega-3 critical for fetal brain development",
            f"Extra {extra_cal} kcal/day for {tri} trimester",
        ]
        if tri == "first":
            notes.append(
                "First trimester: nausea common — small frequent meals, "
                "crackers, ginger tea. Prioritise folate."
            )
        if tri == "postpartum":
            notes.append(
                "Postpartum: +500 kcal/day for breastfeeding. "
                "Continue prenatal vitamins."
            )
        return notes
