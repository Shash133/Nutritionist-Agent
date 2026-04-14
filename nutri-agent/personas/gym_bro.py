"""Gym Bro persona — LBM-based protein, leucine per meal, phase-driven calories."""

from personas.base import PersonaBase
from models.user_profile import UserProfile
from models.meal_plan import (
    NutritionTargets, MacroTargets, MicroTargets, TimingTargets,
)


class GymBroPersona(PersonaBase):
    """
    Science: Protein target based on LBM (not total weight).
    MPS (muscle protein synthesis) requires ≥2.5g leucine per meal.
    Carbs periodized: high on training days, lower on rest days.
    """

    PHASE_CALORIE_MODIFIER = {
        "bulk":        +350,   # kcal surplus
        "cut":         -400,   # kcal deficit
        "recomp":         0,
        "peak":        -200,
        "maintenance":    0,
    }

    PROTEIN_PER_KG_LBM = {
        "bulk":        2.2,    # g/kg LBM — max MPS stimulus
        "cut":         2.6,    # higher to preserve muscle on deficit
        "recomp":      2.4,
        "peak":        2.8,
        "maintenance": 1.8,
    }

    def compute_targets(
        self, profile: UserProfile, bmr: float, tdee: float
    ) -> NutritionTargets:
        phase = profile.training_phase
        cal_modifier = self.PHASE_CALORIE_MODIFIER[phase]
        calories = round(tdee + cal_modifier)

        protein_per_kg = self.PROTEIN_PER_KG_LBM[phase]
        protein_g = round(profile.lean_body_mass * protein_per_kg)

        # High-carb for bulking, moderate for cut, protein fills the rest
        carb_pct = 0.45 if phase == "bulk" else 0.35 if phase == "cut" else 0.40
        fat_pct = 0.25
        carbs_g = round(calories * carb_pct / 4)
        fats_g = round(calories * fat_pct / 9)

        macros = MacroTargets(
            calories=calories,
            protein=protein_g,
            protein_per_kg_lbm=protein_per_kg,
            leucine_per_meal=2.5,          # CRITICAL: must hit per meal for MPS
            carbs=carbs_g,
            net_carbs=round(carbs_g * 0.85),
            fiber=max(25, round(carbs_g * 0.1)),
            fats=fats_g,
            saturated_fat_max=round(fats_g * 0.3),
            omega3_min=3.0,                # g/day for recovery + inflammation
            sugar_max=50,
            glycemic_load_max=20,          # per meal — avoid spikes
        )

        micros = MicroTargets(
            sodium_max=2300,
            potassium_min=3500,
            calcium_min=1000,
            magnesium_min=420 if profile.gender == "male" else 320,
            iron_min=8 if profile.gender == "male" else 18,
            zinc_min=11 if profile.gender == "male" else 8,
            phosphorus_max=None,
            vitamin_d_min=2000,            # IU — high D for testosterone + muscle
            vitamin_b12_min=2.4,
            folate_min=400,
            vitamin_c_min=90,
        )

        timing = TimingTargets(
            pre_workout_carbs=40,          # fast carbs 60–90 min before
            pre_workout_protein=20,
            post_workout_protein=40,       # leucine-rich within 45 min
            post_workout_carbs=60,         # replenish glycogen fast
            before_bed_protein=30,         # casein — slow-release overnight MPS
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
            persona="gym_bro",
            notes=notes,
        )

    def get_supplement_stack(self, profile: UserProfile) -> list[str]:
        stack = [
            "creatine monohydrate 5g/day",
            "whey protein (if dietary protein target not met)",
            "omega-3 fish oil 2–3g EPA+DHA/day",
            "vitamin D3 2000IU/day",
        ]
        if profile.supplement_openness == "advanced":
            stack += [
                "caffeine 200mg pre-workout",
                "beta-alanine 3.2g/day (split doses)",
                "ZMA before bed",
                "citrulline malate 6g pre-workout",
                "ashwagandha 600mg/day for cortisol",
            ]
        if profile.training_phase in ["cut", "peak"]:
            stack.append("L-carnitine 2g pre-workout")
        return stack

    def get_medical_notes(self, profile: UserProfile) -> list[str]:
        notes = []
        if profile.training_phase == "cut":
            notes.append(
                "On a cut — prioritise protein to preserve lean mass. "
                "Expect strength to plateau or slightly decline."
            )
        if profile.training_phase == "bulk":
            notes.append(
                "Caloric surplus of ~350 kcal. Track weekly weight gain — "
                "aim for 0.25–0.5 kg/week."
            )
        return notes
