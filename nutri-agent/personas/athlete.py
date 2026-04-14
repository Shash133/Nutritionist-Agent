"""Athlete persona — sport-specific carb periodization, intra-workout fuel."""

from personas.base import PersonaBase
from models.user_profile import UserProfile
from models.meal_plan import (
    NutritionTargets, MacroTargets, MicroTargets, TimingTargets,
)

# Sport-specific carb targets (g/kg body weight/day)
SPORT_CARB_TARGETS = {
    "endurance":    8.0,   # marathon, cycling
    "team_sport":   6.0,   # football, basketball
    "powerlifting": 4.0,   # lower carb, strength focus
    "bodybuilding": 4.5,
    "crossfit":     6.0,
    "combat":       5.0,
    "swimming":     7.0,
    "cycling":      8.0,
    "none":         4.0,
}


class AthletePersona(PersonaBase):
    """
    Carb targets based on sport and training phase.
    Protein: 1.6–2.2 g/kg lean body mass.
    Carb periodization: high on training days, moderate on rest.
    Intra-workout: fast carbs if session > 60 min.
    """

    PHASE_CALORIE_MODIFIER = {
        "bulk":        +200,
        "cut":         -300,
        "recomp":         0,
        "peak":        -150,
        "maintenance":    0,
    }

    def compute_targets(
        self, profile: UserProfile, bmr: float, tdee: float
    ) -> NutritionTargets:
        phase = profile.training_phase
        cal_modifier = self.PHASE_CALORIE_MODIFIER.get(phase, 0)

        sport_carb_g_per_kg = SPORT_CARB_TARGETS.get(profile.sport, 4.0)
        carbs_g = round(sport_carb_g_per_kg * profile.weight)

        protein_per_kg = 2.0
        protein_g = round(protein_per_kg * profile.lean_body_mass)

        calories = round(tdee + cal_modifier)
        fats_g = round((calories - protein_g * 4 - carbs_g * 4) / 9)
        fats_g = max(fats_g, round(profile.weight * 1.0))  # floor: 1 g/kg

        # Recalculate calories to account for fat floor
        calories = max(calories, protein_g * 4 + carbs_g * 4 + fats_g * 9)

        # Intra-workout carbs needed for long sessions
        intra_workout = profile.training_session_duration_min > 60

        macros = MacroTargets(
            calories=calories,
            protein=protein_g,
            protein_per_kg_lbm=protein_per_kg,
            leucine_per_meal=2.5,
            carbs=carbs_g,
            net_carbs=round(carbs_g * 0.85),
            fiber=max(25, round(carbs_g * 0.08)),
            fats=fats_g,
            saturated_fat_max=round(fats_g * 0.3),
            omega3_min=3.0,
            sugar_max=60,  # higher tolerance for athletes (intra-workout)
            glycemic_load_max=25,
        )

        micros = MicroTargets(
            sodium_max=3000,  # higher for athletes (sweat losses)
            potassium_min=4700,
            calcium_min=1000,
            magnesium_min=420 if profile.gender == "male" else 320,
            iron_min=11 if profile.gender == "male" else 18,
            zinc_min=11 if profile.gender == "male" else 8,
            phosphorus_max=None,
            vitamin_d_min=2000,
            vitamin_b12_min=2.4,
            folate_min=400,
            vitamin_c_min=90,
        )

        timing = TimingTargets(
            pre_workout_carbs=60 if intra_workout else 40,
            pre_workout_protein=25,
            post_workout_protein=40,
            post_workout_carbs=80 if profile.sport in ["endurance", "cycling", "swimming"] else 60,
            before_bed_protein=25,
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
            persona="athlete",
            notes=notes,
        )

    def get_supplement_stack(self, profile: UserProfile) -> list[str]:
        stack = [
            "creatine monohydrate 5g/day",
            "omega-3 fish oil 2g EPA+DHA/day",
            "vitamin D3 2000IU/day",
            "electrolyte mix during training (sodium + potassium + magnesium)",
        ]
        if profile.supplement_openness == "advanced":
            stack += [
                "caffeine 3–6 mg/kg 30 min pre-competition",
                "beta-alanine 3.2g/day",
                "citrulline malate 6–8g pre-workout",
                "tart cherry extract (recovery)",
                "HMB 3g/day (if cutting)",
            ]
        if profile.sport in ["endurance", "cycling", "swimming"]:
            stack.append("intra-workout carb drink (30–60g/hr for sessions >60 min)")
        return stack

    def get_medical_notes(self, profile: UserProfile) -> list[str]:
        notes = []
        if profile.sport in ["endurance", "cycling"]:
            notes.append(
                "High carb requirement for endurance sport — "
                "prioritise complex carbs pre-workout, fast carbs intra/post."
            )
        if profile.training_session_duration_min > 90:
            notes.append(
                "Sessions >90 min: intra-workout fueling critical — "
                "30–60g fast carbs per hour."
            )
        return notes
