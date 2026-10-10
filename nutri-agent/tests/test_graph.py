"""End-to-end graph routing with Neo4j and the LLM replanner stubbed out."""

from config import settings
from graph import nodes
from graph.builder import build_graph
from graph.state import initial_state
from models.meal_plan import MealPlan
from tools import graphrag_tool


def test_replan_result_reaches_finalize(monkeypatch, make_profile, make_meal):
    """The replanner's swap must survive to the final output (not be regenerated away)."""
    initial_meal = make_meal("initial")
    replanned_meal = make_meal("replanned")
    replan_calls = []

    monkeypatch.setattr(nodes, "fetch_suitable_meals_for_slot",
                        lambda slot, profile, avoid_ids=None: [initial_meal])

    def fake_replan(issues, plan, targets, budget, profile, used_meal_ids):
        replan_calls.append(1)
        new_plan = MealPlan(slots={k: [replanned_meal] for k in plan.slots})
        return new_plan, used_meal_ids, "swapped"

    monkeypatch.setattr(nodes, "replan_from_issues", fake_replan)

    final = build_graph().invoke(initial_state(make_profile()))
    output = final["final_output"]

    # An all-zero meal never passes evaluation, so every allowed replan is used.
    assert len(replan_calls) == settings.max_replan_iterations
    assert output["iterations_used"] == settings.max_replan_iterations
    assert all(meals[0]["id"] == "replanned" for meals in output["meal_plan"].values())
    assert output["llm_replan_traces"] == ["swapped"] * settings.max_replan_iterations


def test_allergies_intolerances_dislikes_are_excluded(monkeypatch, make_profile):
    captured = {}

    def fake_get_meals(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(graphrag_tool.neo4j_client, "get_meals_for_persona", fake_get_meals)
    profile = make_profile(allergies=["peanut"], intolerances=["lactose"], dislikes=["tofu"])

    graphrag_tool.fetch_suitable_meals_for_slot("lunch", profile)

    assert captured["exclude_terms"] == ["peanut", "lactose", "tofu"]
