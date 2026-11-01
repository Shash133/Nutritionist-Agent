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


def test_non_veg_can_eat_stricter_diets(monkeypatch, make_profile):
    captured = {}
    monkeypatch.setattr(graphrag_tool.neo4j_client, "get_meals_for_persona",
                        lambda **kw: captured.update(kw) or [])

    graphrag_tool.fetch_suitable_meals_for_slot("lunch", make_profile(diet_type="non_veg"))
    assert set(captured["diet_types"]) == {"non_veg", "eggetarian", "veg", "vegan"}

    graphrag_tool.fetch_suitable_meals_for_slot("lunch", make_profile(diet_type="vegan"))
    assert captured["diet_types"] == ["vegan"]

    graphrag_tool.fetch_suitable_meals_for_slot("lunch", make_profile(diet_type="keto"))
    assert captured["diet_types"] == ["keto"]


def test_generate_plan_avoids_repeating_a_dish(monkeypatch, make_profile, make_meal):
    # Variants of one recipe rank first (highest protein), a different dish last.
    pool = [make_meal("iron-1", protein=40), make_meal("iron-2", protein=39),
            make_meal("omega3-1", protein=30)]
    monkeypatch.setattr(nodes, "fetch_suitable_meals_for_slot",
                        lambda slot, profile, avoid_ids=None:
                            [m for m in pool if m.id not in (avoid_ids or [])])

    state = {"profile": make_profile(), "timing_windows": {"lunch": {}, "dinner": {}},
             "used_meal_ids": {}, "iteration": 0}
    plan = nodes.generate_plan(state)["plan"]

    assert {plan.slots["lunch"][0].family, plan.slots["dinner"][0].family} == {"iron-", "omega3-"}


def test_generate_plan_repeats_only_when_nothing_else_fits(monkeypatch, make_profile, make_meal):
    pool = [make_meal("iron-1"), make_meal("iron-2")]
    monkeypatch.setattr(nodes, "fetch_suitable_meals_for_slot",
                        lambda slot, profile, avoid_ids=None:
                            [m for m in pool if m.id not in (avoid_ids or [])])

    state = {"profile": make_profile(), "timing_windows": {"lunch": {}, "dinner": {}},
             "used_meal_ids": {}, "iteration": 0}
    plan = nodes.generate_plan(state)["plan"]

    assert {plan.slots["lunch"][0].id, plan.slots["dinner"][0].id} == {"iron-1", "iron-2"}


def test_generate_plan_varies_between_runs(monkeypatch, make_profile, make_meal):
    """Dinner rotates among the top dishes for the slot instead of always the first."""
    pool = [make_meal("iron-1", meal_slot="dinner"), make_meal("low-sodium-1", meal_slot="dinner"),
            make_meal("omega3-1", meal_slot="dinner"), make_meal("low-phos-1", meal_slot="dinner")]
    monkeypatch.setattr(nodes, "fetch_suitable_meals_for_slot",
                        lambda slot, profile, avoid_ids=None: pool)
    monkeypatch.setattr(nodes, "_rng", __import__("random").Random(0))

    state = {"profile": make_profile(), "timing_windows": {"dinner": {}},
             "used_meal_ids": {}, "iteration": 0}
    dinners = {nodes.generate_plan(state)["plan"].slots["dinner"][0].family for _ in range(40)}

    assert dinners == {"iron-", "low-sodium-", "omega3-"}   # 4th-ranked dish never picked


def test_fetch_ranks_by_slot_and_caps_variants(monkeypatch, make_profile, make_meal):
    pool = ([make_meal(f"iron-{i}", meal_slot="dinner") for i in range(1, 8)]
            + [make_meal("pre-workout-1", meal_slot="pre_workout"),
               make_meal("high-leucine-1", meal_slot="breakfast")])
    monkeypatch.setattr(graphrag_tool.neo4j_client, "get_meals_for_persona", lambda **kw: pool)

    pre = graphrag_tool.fetch_suitable_meals_for_slot("pre_workout", make_profile())
    breakfast = graphrag_tool.fetch_suitable_meals_for_slot("breakfast", make_profile())

    assert pre[0].id == "pre-workout-1"            # exact slot match first
    assert breakfast[0].id == "high-leucine-1"     # exact before compatible
    assert sum(m.family == "iron-" for m in pre) == graphrag_tool.MAX_VARIANTS_PER_DISH
