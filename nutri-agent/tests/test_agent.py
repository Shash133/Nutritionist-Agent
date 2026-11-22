"""Agentic planner: a scripted fake LLM drives the real graph and tools."""

import pytest
from langchain_core.messages import AIMessage

from config import settings
from graph import agent as agent_mod
from graph import agent_tools
from graph.builder import build_graph
from graph.state import initial_state


class ScriptedLLM:
    """Returns pre-written AI turns; a callable turn receives the message history."""
    def __init__(self, turns):
        self.turns = list(turns)
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        turn = self.turns.pop(0)
        return turn(messages) if callable(turn) else turn


def call(name, _id=None, **args):
    return {"name": name, "args": args, "id": _id or f"{name}-{len(args)}", "type": "tool_call"}


@pytest.fixture
def agentic(monkeypatch, make_meal):
    monkeypatch.setattr(settings, "agentic", True)
    monkeypatch.setattr(settings, "google_api_key", "test-key")
    pool = [
        make_meal("oats-1", meal_slot="breakfast", calories=500, protein=30),
        make_meal("oats-2", meal_slot="breakfast", calories=520, protein=31),
        make_meal("chicken-1", meal_slot="lunch", calories=700, protein=50),
        make_meal("salmon-1", meal_slot="dinner", calories=650, protein=45),
    ]
    monkeypatch.setattr(agent_tools, "fetch_safe_meal_pool", lambda profile: pool)

    def install(turns):
        llm = ScriptedLLM(turns)
        monkeypatch.setattr(agent_mod, "_llm", lambda: llm)
        return llm
    return install


def test_agent_builds_and_finalizes_plan(agentic, make_profile):
    profile = make_profile(meals_per_day=3, workout_time="none")
    llm = agentic([
        AIMessage("", tool_calls=[call("get_nutrition_targets"), call("get_meal_slots")]),
        AIMessage("", tool_calls=[call("search_meals", slot="breakfast")]),
        AIMessage("", tool_calls=[call("set_meal", "a", slot="breakfast", meal_id="oats-1"),
                                  call("set_meal", "b", slot="lunch", meal_id="chicken-1"),
                                  call("set_meal", "c", slot="dinner", meal_id="salmon-1")]),
        AIMessage("", tool_calls=[call("evaluate_plan")]),
        AIMessage("", tool_calls=[call("finalize_plan", summary="Balanced day.")]),
    ])

    final = build_graph().invoke(initial_state(profile))
    out = final["final_output"]

    assert llm.calls == 5
    assert out["planner"] == "agent"
    assert out["agent_summary"] == "Balanced day."
    assert {s: m[0]["id"] for s, m in out["meal_plan"].items()} == {
        "breakfast": "oats-1", "lunch": "chicken-1", "dinner": "salmon-1"}
    assert any("set_meal" in t for t in out["llm_replan_traces"])


def test_tool_results_reach_the_model(agentic, make_profile):
    seen = {}

    def inspect(messages):
        seen["search"] = messages[-1].content
        return AIMessage("", tool_calls=[call("finalize_plan", summary="x")])

    agentic([
        AIMessage("", tool_calls=[call("search_meals", slot="breakfast", sort_by="calories")]),
        inspect,
        lambda messages: seen.setdefault("finalize", messages[-1].content)
                         and AIMessage("", tool_calls=[call("set_meal", slot="lunch",
                                                            meal_id="chicken-1")]),
        AIMessage("Done."),  # stops without finalize_plan: nudged once...
        AIMessage(""),       # ...still no tool call: plan is taken as is
    ])
    out = build_graph().invoke(initial_state(make_profile(workout_time="none")))["final_output"]

    import json
    ids = [m["id"] for m in json.loads(seen["search"])["meals"]]
    assert ids[:2] == ["oats-2", "oats-1"]     # breakfast meals first, highest calories first
    assert "Slots still empty" in seen["finalize"]
    assert out["planner"] == "agent" and out["meal_plan"]["lunch"][0]["id"] == "chicken-1"


def test_set_meal_rejects_unsafe_or_unknown_ids_and_repeats(agentic, make_profile):
    ctx = {"profile": make_profile(workout_time="none")}
    assert "error" in agent_tools.run_tool(ctx, "set_meal", {"slot": "lunch", "meal_id": "made-up"})
    assert agent_tools.run_tool(ctx, "set_meal", {"slot": "breakfast", "meal_id": "oats-1"})["ok"]
    # oats-2 is the same dish as oats-1
    err = agent_tools.run_tool(ctx, "set_meal", {"slot": "lunch", "meal_id": "oats-2"})
    assert "same dish" in err["error"]
    # ...and search hides it from other slots
    res = agent_tools.run_tool(ctx, "search_meals", {"slot": "lunch"})
    assert {m["id"] for m in res["meals"]} == {"chicken-1", "salmon-1"}


def test_bad_arguments_come_back_as_errors(agentic, make_profile):
    ctx = {"profile": make_profile(workout_time="none")}
    assert "error" in agent_tools.run_tool(ctx, "search_meals", {"slot": "lunch", "limit": 999})
    assert "error" in agent_tools.run_tool(ctx, "search_meals", {"slot": "brunch"})
    assert "error" in agent_tools.run_tool(ctx, "no_such_tool", {})


def test_llm_failure_falls_back_to_pipeline(agentic, monkeypatch, make_profile, make_meal):
    from graph import nodes

    def boom(messages):
        raise RuntimeError("503 unavailable")

    agentic([boom])
    monkeypatch.setattr(nodes, "fetch_suitable_meals_for_slot",
                        lambda slot, profile, avoid_ids=None: [make_meal(f"x{slot}")])
    used_llm = []
    monkeypatch.setattr(nodes, "replan_from_issues",
                        lambda *a, use_llm=True: used_llm.append(use_llm) or (a[1], a[5], "h"))

    out = build_graph().invoke(initial_state(make_profile(workout_time="none")))["final_output"]

    assert out["planner"] == "pipeline"
    assert used_llm and not any(used_llm)        # no LLM replans after the LLM failed


def test_step_limit_finalizes_current_plan(agentic, monkeypatch, make_profile):
    monkeypatch.setattr(settings, "max_agent_steps", 2)
    agentic([
        AIMessage("", tool_calls=[call("set_meal", slot="breakfast", meal_id="oats-1")]),
        AIMessage("", tool_calls=[call("search_meals", slot="lunch")]),
    ])
    out = build_graph().invoke(initial_state(make_profile(workout_time="none")))["final_output"]

    assert out["planner"] == "agent"
    assert out["status"] == "partial_issues"
    assert out["meal_plan"]["breakfast"][0]["id"] == "oats-1"
    assert any(i.startswith("empty_slot") for i in out["all_issues_encountered"])


def test_tool_exception_is_returned_to_the_model(agentic, monkeypatch, make_profile):
    def down(profile):
        raise ConnectionError("neo4j unreachable")
    monkeypatch.setattr(agent_tools, "fetch_safe_meal_pool", down)
    ctx = {"profile": make_profile(workout_time="none")}
    res = agent_tools.run_tool(ctx, "search_meals", {"slot": "lunch"})
    assert "neo4j unreachable" in res["error"]


def test_agent_is_nudged_to_finalize(agentic, make_profile):
    seen = {}

    def after_nudge(messages):
        seen["nudge"] = messages[-1].content
        return AIMessage("", tool_calls=[call("finalize_plan", summary="All set.")])

    agentic([
        AIMessage("", tool_calls=[call("set_meal", "a", slot="breakfast", meal_id="oats-1"),
                                  call("set_meal", "b", slot="lunch", meal_id="chicken-1"),
                                  call("set_meal", "c", slot="dinner", meal_id="salmon-1"),
                                  call("evaluate_plan")]),
        AIMessage(""),          # empty reply, no tool call
        after_nudge,
    ])
    out = build_graph().invoke(initial_state(make_profile(workout_time="none")))["final_output"]

    assert seen["nudge"] == agent_mod.NUDGE
    assert out["agent_summary"] == "All set."


def test_llm_failure_mid_run_keeps_the_agents_plan(agentic, monkeypatch, make_profile):
    from graph import nodes
    used_llm = []
    monkeypatch.setattr(nodes, "replan_from_issues",
                        lambda *a, use_llm=True: used_llm.append(use_llm) or (a[1], a[5], "h"))

    def quota(messages):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    agentic([
        AIMessage("", tool_calls=[call("get_nutrition_targets"),
                                  call("set_meal", "a", slot="breakfast", meal_id="oats-1"),
                                  call("set_meal", "b", slot="lunch", meal_id="chicken-1"),
                                  call("set_meal", "c", slot="dinner", meal_id="salmon-1")]),
        quota,
    ])
    out = build_graph().invoke(initial_state(make_profile(workout_time="none")))["final_output"]

    assert out["planner"] == "agent+heuristic"
    assert {s: m[0]["id"] for s, m in out["meal_plan"].items()} == {
        "breakfast": "oats-1", "lunch": "chicken-1", "dinner": "salmon-1"}
    assert used_llm and not any(used_llm)
