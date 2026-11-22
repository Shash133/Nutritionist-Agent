"""
Tools the planning agent calls to build a meal plan.

Each tool is a plain function `fn(ctx, **args) -> dict`. `ctx` is a mutable
working copy of the agent state (profile, targets, timing_windows, plan,
candidate_meals, evaluation, iteration); the tools node writes the changed keys
back into the graph state. Results are JSON-serialisable dicts that go back to
the LLM as tool messages.

Safety lives here, not in the prompt: meals can only come from the profile's
safe pool (diet, medical conditions, allergies, intolerances, dislikes), so the
model cannot place an unsafe meal even if it invents or misremembers an ID.
"""

from typing import Literal, Optional

import structlog

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from models.meal import Meal
from models.meal_plan import MealPlan
from nutrition.engine import get_nutrition_targets
from nutrition.timing import build_timing_windows
from tools.graphrag_tool import fetch_safe_meal_pool, slot_fit
from tools.validator import evaluate

log = structlog.get_logger()

MAX_SEARCH_RESULTS = 15

SortField = Literal[
    "protein", "leucine", "calories", "cost", "fiber", "sodium", "omega3",
    "calcium", "iron", "zinc", "folate", "vitamin_d", "potassium",
    "phosphorus", "net_carbs", "glycemic_load", "saturated_fat",
]


# ── Context helpers ───────────────────────────────────────────────────────────

def _targets(ctx: dict):
    if ctx.get("targets") is None:
        ctx["targets"] = get_nutrition_targets(ctx["profile"])
    return ctx["targets"]


def _windows(ctx: dict) -> dict:
    if not ctx.get("timing_windows"):
        ctx["timing_windows"] = build_timing_windows(ctx["profile"], _targets(ctx))
    return ctx["timing_windows"]


def _plan(ctx: dict) -> MealPlan:
    if ctx.get("plan") is None:
        ctx["plan"] = MealPlan(slots={slot: [] for slot in _windows(ctx)})
    return ctx["plan"]


def _pool(ctx: dict) -> list[Meal]:
    if not ctx.get("candidate_meals"):
        ctx["candidate_meals"] = fetch_safe_meal_pool(ctx["profile"])
    return ctx["candidate_meals"]


def _meal_card(m: Meal) -> dict:
    return {
        "id": m.id, "name": m.name, "slot": m.meal_slot,
        "calories": m.calories, "protein": m.protein, "leucine": m.leucine,
        "net_carbs": m.net_carbs, "fiber": m.fiber, "saturated_fat": m.saturated_fat,
        "omega3": m.omega3, "glycemic_load": m.glycemic_load, "sodium": m.sodium,
        "potassium": m.potassium, "phosphorus": m.phosphorus, "calcium": m.calcium,
        "iron": m.iron, "zinc": m.zinc, "folate": m.folate, "vitamin_d": m.vitamin_d,
        "cost": m.cost, "tags": m.tags,
    }


def _day_totals(plan: MealPlan) -> dict:
    return {
        "calories": round(plan.total_calories, 1),
        "protein": round(plan.total_protein, 1),
        "net_carbs": round(plan.total_net_carbs, 1),
        "fiber": round(plan.total_fiber, 1),
        "omega3": round(plan.total_omega3, 2),
        "sodium": round(plan.total_sodium, 1),
        "calcium": round(plan.total_calcium, 1),
        "iron": round(plan.total_iron, 2),
        "cost": round(plan.total_cost, 2),
    }


def _plan_view(plan: MealPlan) -> dict:
    return {
        slot: ({"id": meals[0].id, "name": meals[0].name} if meals else None)
        for slot, meals in plan.slots.items()
    }


# ── Tools ─────────────────────────────────────────────────────────────────────

class NoArgs(BaseModel):
    pass


def get_nutrition_targets_tool(ctx: dict) -> dict:
    t = _targets(ctx)
    return {
        "macros": t.macros.model_dump(),
        "micros": t.micros.model_dump(exclude_none=True),
        "timing": t.timing.model_dump(),
        "supplement_stack": t.supplement_stack,
        "medical_notes": t.notes,
        "budget_per_day": ctx["profile"].budget_per_day,
    }


def get_meal_slots_tool(ctx: dict) -> dict:
    return {"slots": _windows(ctx), "current_plan": _plan_view(_plan(ctx))}


class SearchMealsArgs(BaseModel):
    slot: str = Field(description="Meal slot to search for, e.g. 'breakfast' or 'post_workout'.")
    query: Optional[str] = Field(
        default=None,
        description="Optional keyword matched against meal name, tags and ingredients "
                    "(e.g. 'salmon', 'high-protein', 'low-gi').")
    sort_by: SortField = Field(default="protein", description="Nutrient to rank by.")
    descending: bool = Field(default=True, description="True = highest first.")
    min_protein: Optional[float] = Field(default=None, description="Minimum protein (g).")
    min_leucine: Optional[float] = Field(default=None, description="Minimum leucine (g).")
    min_calories: Optional[float] = Field(default=None, description="Minimum calories (kcal).")
    max_calories: Optional[float] = Field(default=None, description="Maximum calories (kcal).")
    max_sodium: Optional[float] = Field(default=None, description="Maximum sodium (mg).")
    max_net_carbs: Optional[float] = Field(default=None, description="Maximum net carbs (g).")
    max_glycemic_load: Optional[float] = Field(default=None, description="Maximum glycemic load.")
    max_cost: Optional[float] = Field(default=None, description="Maximum cost.")
    limit: int = Field(default=8, ge=1, le=MAX_SEARCH_RESULTS,
                       description=f"Number of meals to return (max {MAX_SEARCH_RESULTS}).")


def search_meals_tool(ctx: dict, slot: str, query: Optional[str] = None,
                      sort_by: str = "protein", descending: bool = True,
                      min_protein=None, min_leucine=None, min_calories=None,
                      max_calories=None, max_sodium=None, max_net_carbs=None,
                      max_glycemic_load=None, max_cost=None, limit: int = 8) -> dict:
    windows = _windows(ctx)
    if slot not in windows:
        return {"error": f"Unknown slot '{slot}'. Valid slots: {list(windows)}"}

    plan = _plan(ctx)
    in_plan = {m.id for m in plan.all_meals}
    families_elsewhere = {m.family for s, ms in plan.slots.items() if s != slot for m in ms}

    bounds = [
        ("protein", min_protein, None), ("leucine", min_leucine, None),
        ("calories", min_calories, max_calories), ("sodium", None, max_sodium),
        ("net_carbs", None, max_net_carbs), ("glycemic_load", None, max_glycemic_load),
        ("cost", None, max_cost),
    ]
    q = query.strip().lower() if query else ""

    def keep(m: Meal) -> bool:
        if m.id in in_plan or m.family in families_elsewhere:
            return False
        for field, lo, hi in bounds:
            v = getattr(m, field)
            if (lo is not None and v < lo) or (hi is not None and v > hi):
                return False
        if q:
            text = " ".join([m.name, *m.tags, *m.ingredients]).lower()
            if q not in text:
                return False
        return True

    matches = [m for m in _pool(ctx) if keep(m)]
    sign = -1 if descending else 1
    # Meals made for this slot first, then by the requested nutrient.
    matches.sort(key=lambda m: (slot_fit(m, slot), sign * getattr(m, sort_by)))

    # At most two variants of one dish, so a page of results shows real choice.
    shown, per_family = [], {}
    for m in matches:
        per_family[m.family] = per_family.get(m.family, 0) + 1
        if per_family[m.family] <= 2:
            shown.append(m)
        if len(shown) >= limit:
            break

    return {
        "slot": slot,
        "total_matches": len(matches),
        "meals": [_meal_card(m) for m in shown],
        "note": "Only meals safe for this user are listed. Dishes already used in "
                "other slots are excluded.",
    }


class MealIdArgs(BaseModel):
    meal_id: str = Field(description="Meal ID from search_meals results.")


def get_meal_details_tool(ctx: dict, meal_id: str) -> dict:
    meal = next((m for m in _pool(ctx) if m.id == meal_id), None)
    if meal is None:
        return {"error": f"No safe meal with id '{meal_id}' for this user."}
    return meal.model_dump()


class SetMealArgs(BaseModel):
    slot: str = Field(description="Slot to fill. Replaces any meal already there.")
    meal_id: str = Field(description="Meal ID from search_meals results.")


def set_meal_tool(ctx: dict, slot: str, meal_id: str) -> dict:
    windows = _windows(ctx)
    if slot not in windows:
        return {"error": f"Unknown slot '{slot}'. Valid slots: {list(windows)}"}
    meal = next((m for m in _pool(ctx) if m.id == meal_id), None)
    if meal is None:
        return {"error": f"'{meal_id}' is not a safe meal for this user. "
                         "Use an ID returned by search_meals."}

    plan = _plan(ctx)
    clash = next((s for s, ms in plan.slots.items()
                  if s != slot and any(m.family == meal.family for m in ms)), None)
    if clash:
        return {"error": f"'{meal.name}' is the same dish as the meal in '{clash}'. "
                         "Pick a different dish to keep the day varied."}

    replaced = plan.slots.get(slot) or []
    new_plan = MealPlan(slots={k: list(v) for k, v in plan.slots.items()})
    new_plan.slots[slot] = [meal]
    ctx["plan"] = new_plan
    return {
        "ok": True,
        "slot": slot,
        "placed": meal.name,
        "replaced": replaced[0].name if replaced else None,
        "plan": _plan_view(new_plan),
        "day_totals": _day_totals(new_plan),
    }


class SlotArgs(BaseModel):
    slot: str = Field(description="Slot to empty.")


def clear_slot_tool(ctx: dict, slot: str) -> dict:
    plan = _plan(ctx)
    if slot not in plan.slots:
        return {"error": f"Unknown slot '{slot}'. Valid slots: {list(plan.slots)}"}
    new_plan = MealPlan(slots={k: list(v) for k, v in plan.slots.items()})
    new_plan.slots[slot] = []
    ctx["plan"] = new_plan
    return {"ok": True, "plan": _plan_view(new_plan)}


def evaluate_plan_tool(ctx: dict) -> dict:
    plan, targets, profile = _plan(ctx), _targets(ctx), ctx["profile"]
    ctx["iteration"] = ctx.get("iteration", 0) + 1
    result = evaluate(plan, targets, profile.budget_per_day, profile, ctx["iteration"])
    ctx["evaluation"] = result
    empty = [s for s, ms in plan.slots.items() if not ms]

    per_slot = {
        s: {"meal": ms[0].name if ms else None,
            "calories": round(sum(m.calories for m in ms), 1),
            "protein": round(sum(m.protein for m in ms), 1),
            "leucine": round(sum(m.leucine for m in ms), 2),
            "glycemic_load": round(sum(m.glycemic_load for m in ms), 1),
            "sodium": round(sum(m.sodium for m in ms), 1),
            "cost": round(sum(m.cost for m in ms), 2)}
        for s, ms in plan.slots.items()
    }
    return {
        "valid": result.valid and not empty,
        "issues": result.issues,
        "empty_slots": empty,
        "day_totals": _day_totals(plan),
        "per_slot": per_slot,
        "hint": "Issue format is 'type:slot=...:delta=...'. Safety issues (sodium, "
                "potassium, phosphorus, high_protein for CKD) matter most.",
    }


class FinalizeArgs(BaseModel):
    summary: str = Field(description=(
        "2-4 sentences for the user: why these meals suit them, and any issue "
        "left unresolved and why (e.g. covered by the supplement stack)."))


def finalize_plan_tool(ctx: dict, summary: str) -> dict:
    plan = _plan(ctx)
    empty = [s for s, ms in plan.slots.items() if not ms]
    if empty and _pool(ctx):
        return {"error": f"Slots still empty: {empty}. Fill them before finalizing."}
    if ctx.get("evaluation") is None:
        return {"error": "Call evaluate_plan before finalize_plan."}
    ctx["agent_done"] = True
    ctx["agent_summary"] = summary
    return {"ok": True}


# ── Registry ──────────────────────────────────────────────────────────────────

_SPECS = [
    ("get_nutrition_targets", get_nutrition_targets_tool, NoArgs,
     "Daily macro, micro and timing targets for this user, their supplement stack, "
     "medical notes and daily budget."),
    ("get_meal_slots", get_meal_slots_tool, NoArgs,
     "The day's meal slots with times and per-slot targets, plus what is in the plan now."),
    ("search_meals", search_meals_tool, SearchMealsArgs,
     "Search the meals this user can safely eat for one slot, with nutrient filters "
     "and sorting. Returns nutrient cards with IDs to use in set_meal."),
    ("get_meal_details", get_meal_details_tool, MealIdArgs,
     "Full nutrient profile and ingredients of one meal."),
    ("set_meal", set_meal_tool, SetMealArgs,
     "Place a meal in a slot (replacing what is there). Returns updated day totals."),
    ("clear_slot", clear_slot_tool, SlotArgs, "Remove the meal from a slot."),
    ("evaluate_plan", evaluate_plan_tool, NoArgs,
     "Check the current plan against every target and safety constraint. "
     "Returns the list of issues, empty slots, day totals and per-slot numbers."),
    ("finalize_plan", finalize_plan_tool, FinalizeArgs,
     "Finish: submit the current plan with a short summary for the user. "
     "Only after evaluate_plan."),
]

TOOL_FUNCS = {name: fn for name, fn, _, _ in _SPECS}
TOOL_ARGS = {name: args for name, _, args, _ in _SPECS}

# Schemas handed to the LLM; execution goes through run_tool with the state context.
TOOL_SCHEMAS = [
    StructuredTool.from_function(func=lambda **_: None, name=name,
                                 description=desc, args_schema=args)
    for name, _, args, desc in _SPECS
]


def run_tool(ctx: dict, name: str, args: dict) -> dict:
    """Validate arguments and run one tool. Errors come back as data for the model."""
    if name not in TOOL_FUNCS:
        return {"error": f"Unknown tool '{name}'. Available: {list(TOOL_FUNCS)}"}
    try:
        parsed = TOOL_ARGS[name](**(args or {}))
    except Exception as exc:
        return {"error": f"Invalid arguments for {name}: {exc}"}
    try:
        return TOOL_FUNCS[name](ctx, **parsed.model_dump())
    except Exception as exc:
        # e.g. Neo4j unreachable: tell the model instead of crashing the run.
        log.error("agent.tool_failed", tool=name, error=str(exc)[:300])
        return {"error": f"{name} failed: {type(exc).__name__}: {str(exc)[:200]}"}
