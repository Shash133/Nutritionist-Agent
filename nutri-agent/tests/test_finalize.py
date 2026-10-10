import pytest

from graph.nodes import finalize
from models.meal_plan import MealPlan, EvaluationResult
from nutrition.engine import get_nutrition_targets


@pytest.fixture
def run_finalize(make_profile, make_meal):
    def _run(**meal_nutrients):
        profile = make_profile()
        targets = get_nutrition_targets(profile)
        state = {
            "profile": profile,
            "targets": targets,
            "plan": MealPlan(slots={"lunch": [make_meal(**meal_nutrients)]}),
            "evaluation": EvaluationResult(valid=False, issues=[], iteration=0),
            "iteration": 0,
            "all_issues": [],
        }
        return finalize(state)["final_output"]["nutrition_actuals"], targets
    return _run


def test_low_sodium_is_ok(run_finalize):
    actuals, _ = run_finalize(sodium=500)
    assert actuals["sodium"]["status"] == "ok"


def test_high_sodium_is_over_target(run_finalize):
    actuals, _ = run_finalize(sodium=5000)
    assert actuals["sodium"]["status"] == "over_target"


def test_net_carbs_cap(run_finalize):
    low, _ = run_finalize(net_carbs=10)
    high, targets = run_finalize(net_carbs=2000)
    assert low["net_carbs"]["status"] == "ok"
    assert high["net_carbs"]["status"] == "over_target"


def test_calorie_status_bands(run_finalize, make_profile):
    target = get_nutrition_targets(make_profile()).macros.calories
    assert run_finalize(calories=target)[0]["calories"]["status"] == "ok"
    assert run_finalize(calories=target * 0.5)[0]["calories"]["status"] == "under_target"
    assert run_finalize(calories=target * 1.5)[0]["calories"]["status"] == "over_target"
