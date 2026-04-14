"""All action nodes for the langgraph standard workflow."""

import structlog
from graph.state import AgentState
from nutrition.engine import get_nutrition_targets
from nutrition.timing import build_timing_windows as calc_windows
from tools.graphrag_tool import fetch_suitable_meals_for_slot
from tools.validator import evaluate
from tools.replanner import replan_from_issues
from models.meal_plan import MealPlan

log = structlog.get_logger()

def detect_persona(state: AgentState) -> dict:
    """Resolves persona and medical conditions, populates persona_config."""
    profile = state["profile"]
    log.info("node.detect_persona", persona=profile.persona,
             conditions=profile.medical_conditions)
    persona_config = {
        "persona": profile.persona,
        "medical_conditions": profile.medical_conditions,
        "workout_time": profile.workout_time,
        "has_workout": profile.workout_time != "none",
    }
    return {"persona_config": persona_config, "status": "detecting_persona"}


def compute_targets(state: AgentState) -> dict:
    """Calculates macros, micros, and timing targets."""
    log.info("node.compute_targets")
    targets = get_nutrition_targets(state["profile"])
    return {"targets": targets, "status": "computed_targets"}


def build_timing_windows(state: AgentState) -> dict:
    """Creates specific meal slots."""
    log.info("node.build_timing_windows")
    windows = calc_windows(state["profile"], state["targets"])
    return {"timing_windows": windows, "status": "windows_built"}


def fetch_meals(state: AgentState) -> dict:
    """Fetches candidate meals context for generation."""
    log.info("node.fetch_meals")
    # For initial generation, just fetch a big pool
    return {"status": "meals_fetched"}


def generate_plan(state: AgentState) -> dict:
    """Assembles a fresh meal plan mapping one meal to each timing window slot."""
    log.info("node.generate_plan", iteration=state.get("iteration", 0))

    plan = MealPlan(slots={})
    used_ids = {k: list(v) for k, v in state.get("used_meal_ids", {}).items()}
    chosen_in_plan = []  # track all meals picked so far to prevent intraday dupes

    for slot_name in state["timing_windows"].keys():
        already_used = used_ids.get(slot_name, [])
        avoid_combo = list(set(already_used + chosen_in_plan))
        candidates = fetch_suitable_meals_for_slot(
            slot_name, state["profile"], avoid_ids=avoid_combo
        )
        if candidates:
            meal = candidates[0]
            plan.slots[slot_name] = [meal]
            chosen_in_plan.append(meal.id)
            # DONT add to already_used yet, already_used is specifically for rejected meals
            # used_ids[slot_name] = already_used  <-- Keep it as is
        else:
            plan.slots[slot_name] = []

    return {
        "plan": plan,
        "used_meal_ids": used_ids,
        "status": "plan_generated",
        "iteration": state.get("iteration", 0) + 1
    }


def evaluate_plan(state: AgentState) -> dict:
    """Evaluates the plan against all constraints."""
    log.info("node.evaluate_plan")
    res = evaluate(
        state["plan"], 
        state["targets"], 
        state["profile"].budget_per_day,
        state["profile"],
        state["iteration"]
    )
    # Log issues to the cumulative array
    return {
        "evaluation": res, 
        "all_issues": list(set(res.issues)), 
        "status": "evaluated"
    }


def replan(state: AgentState) -> dict:
    """Applies a Gemini-powered fix for the highest priority issue(s)."""
    log.info("node.replan", iteration=state["iteration"])
    new_plan, new_used, action = replan_from_issues(
        state["evaluation"].issues,
        state["plan"],
        state["targets"],
        state["profile"].budget_per_day,
        state["profile"],
        state["used_meal_ids"]
    )
    log.info("node.replan.done", action=action)
    return {
        "plan": new_plan,
        "used_meal_ids": new_used,
        "status": f"replanned: {action}",
        "iteration": state["iteration"] + 1,
        "llm_reasoning": [action],   # accumulates via Annotated[list, operator.add]
    }


def force_finalize(state: AgentState) -> dict:
    """Handles edge case where max iterations are reached."""
    log.info("node.force_finalize")
    return {"status": "forced_finalize_with_unresolved_issues"}


def finalize(state: AgentState) -> dict:
    """Prepares the final structured output matching spec §12 format."""
    log.info("node.finalize")

    plan = state["plan"]
    targets = state["targets"]
    profile = state["profile"]

    def _status(actual, target, mode="min"):
        """Return ok / supplement_required / over / under."""
        if mode == "min":
            return "ok" if actual >= target * 0.9 else "supplement_required"
        elif mode == "max":
            return "ok" if actual <= target * 1.1 else "over_target"
        return "ok"

    # Per-slot leucine minimums
    min_leucine_actual = min(
        (sum(m.leucine for m in meals) for meals in plan.slots.values() if meals),
        default=0.0
    )

    nutrition_actuals = {
        "calories": {
            "target": targets.macros.calories,
            "actual": round(plan.total_calories, 1),
            "status": _status(plan.total_calories, targets.macros.calories * 0.92, "min")
                      if plan.total_calories < targets.macros.calories else
                      _status(targets.macros.calories * 1.08, plan.total_calories, "max"),
        },
        "protein": {
            "target": targets.macros.protein,
            "actual": round(plan.total_protein, 1),
            "status": _status(plan.total_protein, targets.macros.protein),
        },
        "leucine_per_meal": {
            "target": targets.macros.leucine_per_meal,
            "min_actual": round(min_leucine_actual, 2),
            "status": "ok" if min_leucine_actual >= targets.macros.leucine_per_meal else "low",
        },
        "net_carbs": {
            "target": targets.macros.net_carbs,
            "actual": round(plan.total_net_carbs, 1),
            "status": _status(targets.macros.net_carbs, plan.total_net_carbs, "max"),
        },
        "fiber": {
            "target": targets.macros.fiber,
            "actual": round(plan.total_fiber, 1),
            "status": _status(plan.total_fiber, targets.macros.fiber),
        },
        "omega3": {
            "target": targets.macros.omega3_min,
            "actual": round(plan.total_omega3, 2),
            "status": _status(plan.total_omega3, targets.macros.omega3_min)
                      if plan.total_omega3 >= targets.macros.omega3_min * 0.9
                      else "supplement_flagged",
        },
        "sodium": {
            "max": targets.micros.sodium_max,
            "actual": round(plan.total_sodium, 1),
            "status": _status(targets.micros.sodium_max, plan.total_sodium, "max"),
        },
        "iron": {
            "target": targets.micros.iron_min,
            "actual": round(plan.total_iron, 2),
            "status": _status(plan.total_iron, targets.micros.iron_min),
        },
        "calcium": {
            "target": targets.micros.calcium_min,
            "actual": round(plan.total_calcium, 1),
            "status": _status(plan.total_calcium, targets.micros.calcium_min),
        },
        "vitamin_d": {
            "target": targets.micros.vitamin_d_min,
            "actual": round(plan.total_vitamin_d, 1),
            "status": _status(plan.total_vitamin_d, targets.micros.vitamin_d_min)
                      if plan.total_vitamin_d >= targets.micros.vitamin_d_min * 0.9
                      else "supplement_required",
        },
        "zinc": {
            "target": targets.micros.zinc_min,
            "actual": round(plan.total_zinc, 2),
            "status": _status(plan.total_zinc, targets.micros.zinc_min),
        },
        "folate": {
            "target": targets.micros.folate_min,
            "actual": round(plan.total_folate, 1),
            "status": _status(plan.total_folate, targets.micros.folate_min),
        },
        "magnesium": {
            "target": targets.micros.magnesium_min,
            "actual": round(plan.total_magnesium, 1),
            "status": _status(plan.total_magnesium, targets.micros.magnesium_min),
        },
        "potassium": {
            "target": targets.micros.potassium_min,
            "actual": round(plan.total_potassium, 1),
            "status": _status(plan.total_potassium, targets.micros.potassium_min),
        },
    }

    output = {
        "persona": profile.persona,
        "training_phase": profile.training_phase,
        "meal_plan": {
            k: [m.model_dump() for m in v] for k, v in plan.slots.items()
        },
        "nutrition_actuals": nutrition_actuals,
        "supplement_stack": targets.supplement_stack,
        "medical_notes": targets.notes,
        "cost": round(plan.total_cost, 2),
        "status": "valid" if state["evaluation"].valid else "partial_issues",
        "iterations_used": state["iteration"],
        "all_issues_encountered": state["all_issues"],
        "llm_replan_traces": state.get("llm_reasoning", []),
    }

    # Append plan summary to user_history for memory-aware replanning
    history_entry = {
        "persona": profile.persona,
        "goal": profile.goal,
        "calories_target": targets.macros.calories,
        "calories_actual": round(plan.total_calories, 1),
        "protein_actual": round(plan.total_protein, 1),
        "status": output["status"],
        "cost": output["cost"],
    }
    updated_history = list(state.get("user_history", [])) + [history_entry]

    return {
        "final_output": output,
        "user_history": updated_history,
        "status": "done"
    }
