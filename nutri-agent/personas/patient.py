"""Patient persona — medical condition overrides that stack without conflict."""

from personas.base import PersonaBase
from personas.office_worker import OfficeWorkerPersona
from models.user_profile import UserProfile
from models.meal_plan import NutritionTargets


class PatientPersona(PersonaBase):
    """
    Medical condition overrides. Multiple conditions stack their constraints.
    Always adds medical_notes to output. Medications may alter nutrient needs.
    Starts from OfficeWorkerPersona base targets, then applies condition-specific
    overrides to create a clinically safe nutrition profile.
    """

    CONDITION_OVERRIDES = {
        "type2_diabetes": {
            "net_carbs_max": 130,             # g/day
            "sugar_max": 25,
            "glycemic_load_max": 10,          # strict per meal
            "fiber_min": 35,                  # improves insulin sensitivity
            "notes": [
                "Low-GI carbs only",
                "No refined sugars",
                "Monitor post-meal glucose",
            ],
        },
        "type1_diabetes": {
            "net_carbs_max": 150,
            "glycemic_load_max": 12,
            "notes": ["Carb counting critical for insulin dosing"],
        },
        "hypertension": {
            "sodium_max": 1500,               # mg/day — strict
            "potassium_min": 4700,            # high K offsets sodium
            "notes": [
                "DASH diet principles",
                "No added salt",
                "High potassium foods prioritised",
            ],
        },
        "ckd": {
            "protein_g_per_kg": 0.8,          # restrict protein to reduce urea load
            "phosphorus_max": 800,            # mg/day — kidneys cannot excrete excess
            "potassium_max": 2000,            # mg/day — dangerous if elevated
            "sodium_max": 1500,
            "notes": [
                "Low phosphorus foods",
                "Avoid potassium-rich foods",
                "Protein restriction — consult nephrologist",
            ],
        },
        "pcos": {
            "net_carbs_max": 100,
            "sugar_max": 20,
            "omega3_min": 3.0,                # anti-inflammatory
            "notes": [
                "Anti-inflammatory focus",
                "Low-GI",
                "High omega-3",
            ],
        },
        "hypothyroidism": {
            "notes": [
                "Avoid raw goitrogens (kale, soy) in excess",
                "Selenium-rich foods: Brazil nuts, tuna",
                "Ensure adequate iodine intake (150 mcg/day)",
            ],
        },
        "celiac": {
            "gluten_free": True,
            "notes": ["Strictly gluten-free", "Watch cross-contamination"],
        },
        "ibs": {
            "low_fodmap": True,
            "notes": [
                "Low-FODMAP protocol",
                "Avoid onion, garlic, lactose, fructose",
            ],
        },
        "high_cholesterol": {
            "saturated_fat_max": 14,          # g/day
            "omega3_min": 4.0,
            "fiber_min": 30,
            "notes": [
                "Limit saturated fat",
                "High soluble fiber",
                "High omega-3",
            ],
        },
        "anemia": {
            "iron_min": 27,                   # mg/day — heme + non-heme
            "vitamin_c_min": 150,             # enhances iron absorption
            "notes": [
                "Combine iron foods with vitamin C",
                "Avoid tea/coffee with meals",
            ],
        },
        "gout": {
            "notes": [
                "Avoid red meat, organ meats, shellfish, beer",
                "Cherries and dairy shown to reduce uric acid",
            ],
        },
        "osteoporosis": {
            "calcium_min": 1200,              # mg/day
            "vitamin_d_min": 2000,            # IU/day
            "notes": [
                "Weight-bearing exercise + nutrition synergy",
                "Avoid excess sodium and caffeine (increase calcium excretion)",
            ],
        },
        "nafld": {
            "sugar_max": 15,
            "saturated_fat_max": 10,
            "notes": [
                "Avoid fructose, refined carbs, saturated fat",
                "Coffee protective",
            ],
        },
    }

    def compute_targets(
        self, profile: UserProfile, bmr: float, tdee: float
    ) -> NutritionTargets:
        # Start with a base maintenance target from OfficeWorkerPersona
        base = OfficeWorkerPersona().compute_targets(profile, bmr, tdee)

        overrides: dict = {}
        notes: list[str] = []
        for condition in profile.medical_conditions:
            if condition == "none":
                continue
            c = self.CONDITION_OVERRIDES.get(condition, {})
            # For numeric overrides, take the most restrictive value
            for key, value in c.items():
                if key == "notes":
                    notes += value
                elif key in overrides:
                    # Take the more restrictive (lower max, higher min)
                    if "max" in key:
                        overrides[key] = min(overrides[key], value)
                    elif "min" in key:
                        overrides[key] = max(overrides[key], value)
                    else:
                        overrides[key] = value
                else:
                    overrides[key] = value

        # ── Apply overrides to base targets ──────────────────────────────
        # Override protein for CKD
        if "protein_g_per_kg" in overrides:
            protein_g = round(overrides["protein_g_per_kg"] * profile.weight)
            base.macros.protein = protein_g
            base.macros.protein_per_kg_lbm = overrides["protein_g_per_kg"]

        # Macro overrides
        if "net_carbs_max" in overrides:
            base.macros.net_carbs = min(
                base.macros.net_carbs, overrides["net_carbs_max"]
            )
        if "sugar_max" in overrides:
            base.macros.sugar_max = min(
                base.macros.sugar_max, overrides["sugar_max"]
            )
        if "glycemic_load_max" in overrides:
            base.macros.glycemic_load_max = min(
                base.macros.glycemic_load_max, overrides["glycemic_load_max"]
            )
        if "fiber_min" in overrides:
            base.macros.fiber = max(
                base.macros.fiber, overrides["fiber_min"]
            )
        if "saturated_fat_max" in overrides:
            base.macros.saturated_fat_max = min(
                base.macros.saturated_fat_max, overrides["saturated_fat_max"]
            )
        if "omega3_min" in overrides:
            base.macros.omega3_min = max(
                base.macros.omega3_min, overrides["omega3_min"]
            )

        # Micro overrides
        if "sodium_max" in overrides:
            base.micros.sodium_max = min(
                base.micros.sodium_max, overrides["sodium_max"]
            )
        if "phosphorus_max" in overrides:
            base.micros.phosphorus_max = overrides["phosphorus_max"]
        if "potassium_min" in overrides:
            base.micros.potassium_min = max(
                base.micros.potassium_min, overrides["potassium_min"]
            )
        if "calcium_min" in overrides:
            base.micros.calcium_min = max(
                base.micros.calcium_min, overrides["calcium_min"]
            )
        if "vitamin_d_min" in overrides:
            base.micros.vitamin_d_min = max(
                base.micros.vitamin_d_min, overrides["vitamin_d_min"]
            )
        if "iron_min" in overrides:
            base.micros.iron_min = max(
                base.micros.iron_min, overrides["iron_min"]
            )
        if "vitamin_c_min" in overrides:
            base.micros.vitamin_c_min = max(
                base.micros.vitamin_c_min, overrides["vitamin_c_min"]
            )

        # CKD: potassium cap (this is a MAX, not a min)
        if "potassium_max" in overrides:
            base.micros.potassium_min = min(
                base.micros.potassium_min, overrides["potassium_max"]
            )

        base.notes = notes
        base.persona = "patient"
        return base

    def get_supplement_stack(self, profile: UserProfile) -> list[str]:
        stack = []
        for condition in profile.medical_conditions:
            if condition == "anemia":
                stack.append("iron bisglycinate 25mg/day (with vitamin C)")
            if condition == "osteoporosis":
                stack.append("calcium citrate 500mg 2x/day + vitamin D3 2000IU")
                stack.append("vitamin K2 (MK-7) 100mcg/day")
            if condition in ["type2_diabetes", "pcos"]:
                stack.append("chromium picolinate 200mcg/day (insulin sensitivity)")
            if condition == "high_cholesterol":
                stack.append("plant sterols 2g/day")
                stack.append("psyllium husk 5g/day (soluble fiber)")
        return stack

    def get_medical_notes(self, profile: UserProfile) -> list[str]:
        notes = []
        if profile.medications:
            notes.append(
                f"Current medications: {', '.join(profile.medications)}. "
                "Verify nutrient-drug interactions with pharmacist."
            )
        return notes
