from models.meal_plan import MealPlan
from nutrition.engine import get_nutrition_targets
from tools.validator import evaluate


def _issue_keys(result):
    return {i.split(":")[0] for i in result.issues}


def test_high_potassium_flagged_for_ckd(make_profile, make_meal):
    profile = make_profile(persona="patient", goal="clinical", medical_conditions=["ckd"])
    targets = get_nutrition_targets(profile)
    plan = MealPlan(slots={"lunch": [make_meal(potassium=2500)]})

    result = evaluate(plan, targets, profile.budget_per_day, profile, 0)

    assert "high_potassium" in _issue_keys(result)


def test_potassium_not_capped_without_ckd(make_profile, make_meal):
    profile = make_profile()
    targets = get_nutrition_targets(profile)
    plan = MealPlan(slots={"lunch": [make_meal(potassium=5000)]})

    result = evaluate(plan, targets, profile.budget_per_day, profile, 0)

    assert "high_potassium" not in _issue_keys(result)


def test_high_sodium_and_over_budget(make_profile, make_meal):
    profile = make_profile(budget_per_day=100.0)
    targets = get_nutrition_targets(profile)
    plan = MealPlan(slots={"lunch": [make_meal(sodium=5000, cost=150)]})

    keys = _issue_keys(evaluate(plan, targets, profile.budget_per_day, profile, 0))

    assert {"high_sodium", "over_budget"} <= keys


def test_empty_plan_is_low_calories(make_profile):
    profile = make_profile()
    targets = get_nutrition_targets(profile)

    result = evaluate(MealPlan(slots={}), targets, profile.budget_per_day, profile, 0)

    assert not result.valid
    assert "low_calories" in _issue_keys(result)
