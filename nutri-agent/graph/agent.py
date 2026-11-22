"""
Agentic planner: Gemini drives the whole planning run by calling tools.

    agent ──tool calls──▶ tools ──▶ agent ... ──finalize_plan──▶ agent_wrap_up ──▶ finalize

The model decides which targets to look at, which meals to search for, what to
place in each slot, when to re-check the plan and when it is good enough. The
graph only enforces a step budget and falls back to the deterministic pipeline
if the LLM is unreachable or the agent produces no plan.
"""

import json

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from config import settings
from graph.agent_tools import TOOL_SCHEMAS, run_tool
from graph.state import AgentState
from nutrition.engine import get_nutrition_targets
from tools.llm import get_chat_model, is_rate_limit_error
from tools.validator import evaluate

log = structlog.get_logger()

# State keys the tools may change; written back after each tools step.
CTX_KEYS = ("targets", "timing_windows", "plan", "candidate_meals", "evaluation",
            "iteration", "agent_done", "agent_summary")

SYSTEM_PROMPT = """You are NutriGraph, a clinical-grade nutrition planning agent. \
You build a one-day meal plan for the user below by calling tools. You decide the order \
of work, but a good run usually looks like this:

1. Read the user's targets (get_nutrition_targets) and the day's slots (get_meal_slots).
2. For each slot, search_meals with filters that fit the slot and the user's goal, \
then set_meal. Think about the whole day: calories and protein should add up to the \
targets, not each meal on its own.
3. evaluate_plan. For each issue, find the slot causing it, search for a better meal \
and swap it with set_meal. Then evaluate again.
4. When the plan is valid, or the remaining issues cannot be fixed by swapping meals \
(for example a micronutrient that the supplement stack already covers), call \
finalize_plan with a short summary for the user.

Rules:
- Only use meal IDs returned by search_meals. Every meal search_meals returns is \
already safe for this user's diet, allergies and medical conditions.
- Fix safety issues first: high sodium, potassium or phosphorus, high protein for \
kidney disease, high glycemic load for diabetes. Then protein and leucine, then \
calories, carbs and fiber, then micronutrients, then budget.
- Keep the day varied: never serve the same dish twice.
- Make independent tool calls in the same turn (for example searching several slots \
at once) to save time.
- You have a limited number of turns ({max_steps}). Do not finalize without \
calling evaluate_plan first."""


NUDGE = ("You stopped without calling finalize_plan. Either keep fixing the remaining "
         "issues with tool calls, or call finalize_plan now with a summary for the user.")


def _profile_brief(state: AgentState) -> str:
    p = state["profile"]
    profile = p.model_dump()
    lines = [
        "Plan today's meals for this user.",
        "",
        "## Profile",
        json.dumps(profile, indent=2, default=str),
    ]
    if p.lean_body_mass is not None and p.ffmi is not None:
        lines.append(f"Lean body mass: {p.lean_body_mass:.1f} kg, FFMI: {p.ffmi:.1f}")
    if p.likes:
        lines.append(f"They like: {', '.join(p.likes)} — prefer these when the numbers allow.")
    history = state.get("user_history") or []
    if history:
        lines += ["", "## Previous plans for this user (most recent last)",
                  json.dumps(history[-3:], indent=2),
                  "Learn from these: if earlier plans missed calories or protein, "
                  "correct for it; vary the dishes from day to day."]
    return "\n".join(lines)


def _llm():
    return get_chat_model().bind_tools(TOOL_SCHEMAS)


def agent(state: AgentState) -> dict:
    """One LLM turn: the model reads the conversation and decides what to do next."""
    messages = list(state.get("messages") or [])
    if not messages:
        messages = [
            SystemMessage(SYSTEM_PROMPT.format(max_steps=settings.max_agent_steps)),
            HumanMessage(_profile_brief(state)),
        ]
    steps = state.get("agent_steps", 0) + 1
    if steps == settings.max_agent_steps:
        messages.append(HumanMessage(
            "This is your last turn. Call finalize_plan now with the current plan."))

    log.info("node.agent", step=steps)
    try:
        response = _llm().invoke(messages)
        if not response.tool_calls:
            # The model stopped without finalize_plan (sometimes with an empty
            # reply). Nudge it once so the run ends with a summary for the user.
            if _text_of(response):
                messages.append(response)
            messages.append(HumanMessage(NUDGE))
            response = _llm().invoke(messages)
    except Exception as exc:
        if is_rate_limit_error(exc):
            log.warning("agent.rate_limited", model=settings.gemini_model, error=str(exc)[:300])
        else:
            log.error("agent.llm_error", error=str(exc)[:500])
        update = {
            "llm_failed": True,
            "agent_steps": steps,
            "status": "agent_llm_failed",
            "llm_reasoning": [f"[Agent] LLM unavailable ({type(exc).__name__}); "
                              "falling back to the deterministic planner."],
        }
        if _can_resume_in_pipeline(state):
            # Keep the agent's plan; the pipeline's heuristic replans finish it.
            update.update(iteration=0, planner="agent+heuristic",
                          llm_reasoning=[f"[Agent] LLM unavailable ({type(exc).__name__}); "
                                         "finishing the agent's plan with heuristic swaps."])
        return update

    trace = []
    text = _text_of(response)
    if text:
        trace.append(f"[Agent] {text[:300]}")
    for call in response.tool_calls:
        trace.append(f"[Agent] → {call['name']}({_short_args(call['args'])})")

    return {
        "messages": messages + [response],
        "agent_steps": steps,
        "status": f"agent_step_{steps}",
        "llm_reasoning": trace,
    }


def tools(state: AgentState) -> dict:
    """Run every tool call from the last agent turn against the current state."""
    messages = list(state["messages"])
    last: AIMessage = messages[-1]
    ctx = {k: state.get(k) for k in CTX_KEYS}
    ctx["profile"] = state["profile"]

    for call in last.tool_calls:
        result = run_tool(ctx, call["name"], call.get("args") or {})
        log.info("agent.tool", tool=call["name"], args=call.get("args"),
                 error=result.get("error"))
        messages.append(ToolMessage(
            content=json.dumps(result, default=str),
            tool_call_id=call["id"],
            name=call["name"],
        ))

    # Write back only what changed: the meal pool is large, and every update is checkpointed.
    update = {k: ctx[k] for k in CTX_KEYS if ctx[k] is not state.get(k)}
    update["messages"] = messages
    update["status"] = "agent_tools_run"
    if ctx.get("evaluation") is not None:
        update["all_issues"] = list(ctx["evaluation"].issues)
    return update


def agent_wrap_up(state: AgentState) -> dict:
    """Re-check the agent's final plan so the output reflects exactly what was submitted."""
    plan = state.get("plan")
    if plan is None or not plan.all_meals:
        log.warning("agent.no_plan", steps=state.get("agent_steps"))
        return {"status": "agent_produced_no_plan",
                "llm_reasoning": ["[Agent] No plan produced; falling back to the "
                                  "deterministic planner."]}
    targets = state.get("targets") or get_nutrition_targets(state["profile"])
    profile = state["profile"]
    result = evaluate(plan, targets, profile.budget_per_day, profile, state.get("iteration", 0))
    empty = [s for s, ms in plan.slots.items() if not ms]
    if empty:
        result.issues.extend(f"empty_slot:slot={s}" for s in empty)
        result.valid = False
    log.info("agent.wrap_up", valid=result.valid, issues=result.issues,
             finalized_by_agent=state.get("agent_done", False))
    return {
        "targets": targets,
        "evaluation": result,
        "all_issues": list(result.issues),
        "planner": "agent",
        "status": "agent_finished",
    }


# ── Routing ───────────────────────────────────────────────────────────────────

def route_entry(state: AgentState) -> str:
    if settings.agentic and settings.google_api_key:
        return "agent"
    return "detect_persona"


def _can_resume_in_pipeline(state: AgentState) -> bool:
    """Agent plan has every slot filled and targets are known: the pipeline can take over."""
    plan = state.get("plan")
    return (state.get("targets") is not None and plan is not None and bool(plan.slots)
            and all(plan.slots.values()))


def route_after_agent(state: AgentState) -> str:
    if state.get("llm_failed"):
        return "evaluate_plan" if state.get("planner") == "agent+heuristic" else "detect_persona"
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    # The model stopped calling tools without finalizing: take its plan as is.
    return "agent_wrap_up"


def route_after_tools(state: AgentState) -> str:
    if state.get("agent_done") or state.get("agent_steps", 0) >= settings.max_agent_steps:
        return "agent_wrap_up"
    return "agent"


def route_after_wrap_up(state: AgentState) -> str:
    plan = state.get("plan")
    return "finalize" if plan is not None and plan.all_meals else "detect_persona"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _text_of(msg: AIMessage) -> str:
    content = msg.content
    if isinstance(content, str):
        return content.strip()
    parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
    return " ".join(p.strip() for p in parts if p.strip())


def _short_args(args: dict) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in (args or {}).items()
                     if v is not None and k != "summary")[:160]
