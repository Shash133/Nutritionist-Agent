from config import settings
from models.meal_plan import MealPlan
from nutrition.engine import get_nutrition_targets
from tools import replanner


def test_llm_client_is_shared_and_rate_limited(monkeypatch):
    """One client per process, so the rate limiter budget covers every call."""
    monkeypatch.setattr(settings, "gemini_rpm", 30)
    monkeypatch.setattr(settings, "google_api_key", "test-key")  # no network call is made
    replanner._get_llm.cache_clear()
    try:
        llm = replanner._get_llm()
        assert replanner._get_llm() is llm

        chat_model = llm.first.bound   # with_structured_output -> model | parser
        assert chat_model.rate_limiter.requests_per_second == 30 / 60
        assert chat_model.max_retries == settings.gemini_max_retries
    finally:
        replanner._get_llm.cache_clear()


def test_rate_limited_llm_falls_back_to_heuristic(monkeypatch, make_profile, make_meal):
    class RateLimitedLLM:
        def invoke(self, prompt):
            raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")

    monkeypatch.setattr(replanner, "_get_llm", lambda: RateLimitedLLM())
    monkeypatch.setattr(replanner, "fetch_suitable_meals_for_slot",
                        lambda slot, profile, avoid_ids=None: [make_meal("alt", protein=50)])

    profile = make_profile()
    plan = MealPlan(slots={"lunch": [make_meal("orig")]})

    new_plan, _, action = replanner.replan_from_issues(
        ["low_protein:delta=50g"], plan, get_nutrition_targets(profile),
        profile.budget_per_day, profile, {},
    )

    assert action.startswith("[Heuristic]")
    assert new_plan.slots["lunch"][0].id == "alt"


def test_rate_limit_error_detection():
    assert replanner._is_rate_limit_error(RuntimeError("Error 429 Too Many Requests"))
    assert replanner._is_rate_limit_error(RuntimeError("RESOURCE_EXHAUSTED"))
    assert not replanner._is_rate_limit_error(RuntimeError("404 NOT_FOUND"))
