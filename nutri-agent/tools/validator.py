"""Advanced Multi-Constraint Evaluator."""

from models.meal_plan import MealPlan, NutritionTargets, EvaluationResult
from models.user_profile import UserProfile

# Tolerances
CALORIE_TOL        = 0.08   # ±8%
PROTEIN_TOL        = 0.05   # allow 5% under
MICRO_TOL          = 0.10   # micronutrients ±10%

ISSUE_TYPES = [
    # Macro issues
    "low_calories", "high_calories",
    "low_protein", "high_protein",
    "low_leucine_per_meal",
    "high_net_carbs",
    "high_glycemic_load",
    "low_fiber",
    "high_sugar",
    "high_saturated_fat",
    "low_omega3",
    # Micro issues
    "low_iron", "low_calcium", "low_vitamin_d", "low_zinc",
    "low_folate",
    "high_sodium",
    "high_phosphorus",
    "high_potassium",
    # Budget
    "over_budget",
    # Timing
    "missing_pre_workout_slot",
    "missing_post_workout_slot",
    "post_workout_protein_low",
]


def evaluate(plan: MealPlan, targets: NutritionTargets,
             budget: float, profile: UserProfile,
             iteration: int) -> EvaluationResult:
    issues = []

    # ── Macro checks ────────────────────────────────────────────────────────
    cal_low  = targets.macros.calories * (1 - CALORIE_TOL)
    cal_high = targets.macros.calories * (1 + CALORIE_TOL)
    if plan.total_calories < cal_low:
        issues.append(f"low_calories:delta={cal_low - plan.total_calories:.0f}kcal")
    elif plan.total_calories > cal_high:
        issues.append(f"high_calories:delta={plan.total_calories - cal_high:.0f}kcal")

    if plan.total_protein < targets.macros.protein * (1 - PROTEIN_TOL):
        issues.append(f"low_protein:delta={targets.macros.protein - plan.total_protein:.1f}g")

    # CKD: too much protein is bad
    if "ckd" in profile.medical_conditions:
        protein_ceiling = 0.8 * profile.weight * 1.15
        if plan.total_protein > protein_ceiling:
            issues.append(f"high_protein:delta={plan.total_protein - protein_ceiling:.1f}g")

    # Leucine threshold per meal
    if profile.persona in ["gym_bro", "athlete", "elderly"]:
        leucine_threshold = targets.macros.leucine_per_meal
        for slot_name, slot_meals in plan.all_slots_named.items():
            slot_leucine = sum(m.leucine for m in slot_meals)
            if slot_leucine < leucine_threshold and slot_meals:
                issues.append(f"low_leucine_per_meal:slot={slot_name}:delta={leucine_threshold - slot_leucine:.1f}g")

    # Net carb cap 
    if plan.total_net_carbs > targets.macros.net_carbs * 1.05:
        issues.append(f"high_net_carbs:delta={plan.total_net_carbs - targets.macros.net_carbs:.0f}g")

    # Glycemic load per meal
    for slot_name, slot_meals in plan.all_slots_named.items():
        slot_gl = sum(m.glycemic_load for m in slot_meals)
        if slot_gl > targets.macros.glycemic_load_max:
            issues.append(f"high_glycemic_load:slot={slot_name}:gl={slot_gl:.1f}")

    # Fiber
    if plan.total_fiber < targets.macros.fiber * (1 - MICRO_TOL):
        issues.append(f"low_fiber:delta={targets.macros.fiber - plan.total_fiber:.0f}g")

    # Saturated fat
    if plan.total_saturated_fat > targets.macros.saturated_fat_max:
        issues.append(f"high_saturated_fat:delta={plan.total_saturated_fat - targets.macros.saturated_fat_max:.1f}g")

    # Omega-3
    if plan.total_omega3 < targets.macros.omega3_min * (1 - MICRO_TOL):
        issues.append(f"low_omega3:delta={targets.macros.omega3_min - plan.total_omega3:.1f}g")

    # Sugar
    if plan.total_sugar > targets.macros.sugar_max * (1 + MICRO_TOL):
        issues.append(f"high_sugar:delta={plan.total_sugar - targets.macros.sugar_max:.0f}g")

    # ── Micronutrient checks ────────────────────────────────────────────────
    micro_checks = [
        (plan.total_iron,      targets.micros.iron_min,       "low_iron",       MICRO_TOL, "mg"),
        (plan.total_calcium,   targets.micros.calcium_min,    "low_calcium",    MICRO_TOL, "mg"),
        (plan.total_vitamin_d, targets.micros.vitamin_d_min,  "low_vitamin_d",  MICRO_TOL, "IU"),
        (plan.total_zinc,      targets.micros.zinc_min,       "low_zinc",       MICRO_TOL, "mg"),
        (plan.total_folate,    targets.micros.folate_min,     "low_folate",     MICRO_TOL, "mcg"),
        (plan.total_sodium,    targets.micros.sodium_max,     "high_sodium",    MICRO_TOL, "mg"),
    ]
    for actual, target_val, issue_key, tol, unit in micro_checks:
        if "high" in issue_key and actual > target_val * (1 + tol):
            issues.append(f"{issue_key}:delta={actual - target_val:.0f}{unit}")
        elif "low" in issue_key and actual < target_val * (1 - tol):
            issues.append(f"{issue_key}:delta={target_val - actual:.0f}{unit}")

    # CKD phosphorus and potassium caps
    if targets.micros.phosphorus_max and plan.total_phosphorus > targets.micros.phosphorus_max:
        issues.append(f"high_phosphorus:delta={plan.total_phosphorus - targets.micros.phosphorus_max:.0f}mg")

    # Budget
    if plan.total_cost > budget:
        issues.append(f"over_budget:delta={plan.total_cost - budget:.2f}")
        
    # Timing
    if profile.workout_time != "none":
        if "pre_workout" not in plan.all_slots_named or not plan.all_slots_named["pre_workout"]:
            issues.append("missing_pre_workout_slot")
        if "post_workout" not in plan.all_slots_named or not plan.all_slots_named["post_workout"]:
            issues.append("missing_post_workout_slot")
        else:
            p_pw = sum(m.protein for m in plan.all_slots_named["post_workout"])
            if p_pw < targets.timing.post_workout_protein * (1 - PROTEIN_TOL):
                issues.append(f"post_workout_protein_low:delta={targets.timing.post_workout_protein - p_pw:.1f}g")

    return EvaluationResult(valid=len(issues) == 0, issues=issues, iteration=iteration)
