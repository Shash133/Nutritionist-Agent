"""Advanced Replanner — LLM-powered meal swap decisions using Google Gemini."""

import json
import structlog
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from models.meal_plan import MealPlan, NutritionTargets
from models.user_profile import UserProfile
from models.meal import Meal
from tools.graphrag_tool import fetch_suitable_meals_for_slot
from config import settings

log = structlog.get_logger()

# ── Priority order for safety overrides ──────────────────────────────────────
PRIORITY = [
    "high_phosphorus", "high_potassium", "high_sodium",    # safety first
    "low_leucine_per_meal",                                # MPS
    "low_protein", "high_protein",                         # macros
    "high_net_carbs", "high_glycemic_load",
    "low_fiber", "high_saturated_fat", "low_omega3",
    "low_iron", "low_calcium", "low_vitamin_d", "low_zinc", "low_folate",
    "over_budget",
    "low_calories", "high_calories",
]

# ── LLM structured output schema ─────────────────────────────────────────────
class ReplanDecision(BaseModel):
    """Structured decision from the LLM for which meal to swap and why."""
    reasoning: str = Field(description=(
        "Step-by-step clinical reasoning explaining why this meal was chosen. "
        "Reference specific nutrient values, the issues being addressed, and any "
        "trade-offs accepted."
    ))
    target_slot: str = Field(description=(
        "The meal slot to replace (e.g. 'breakfast', 'pre_workout', 'dinner')."
    ))
    selected_meal_id: str = Field(description=(
        "The exact meal ID string from the candidates list to place in the slot. "
        "MUST be one of the IDs provided in the candidates."
    ))

# ── LLM initialization ────────────────────────────────────────────────────────
def _get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.google_api_key,
        temperature=0.2,
    ).with_structured_output(ReplanDecision)


def _build_plan_summary(plan: MealPlan) -> dict:
    """Concise per-slot nutrient totals for the prompt."""
    summary = {}
    for slot, meals in plan.slots.items():
        if not meals:
            summary[slot] = {"meals": [], "calories": 0, "protein": 0}
            continue
        summary[slot] = {
            "meals": [{"id": m.id, "name": m.name} for m in meals],
            "calories": round(sum(m.calories for m in meals), 1),
            "protein":  round(sum(m.protein for m in meals), 1),
            "leucine":  round(sum(m.leucine for m in meals), 2),
            "fiber":    round(sum(m.fiber for m in meals), 1),
            "sodium":   round(sum(m.sodium for m in meals), 1),
            "omega3":   round(sum(m.omega3 for m in meals), 2),
            "calcium":  round(sum(m.calcium for m in meals), 1),
            "iron":     round(sum(m.iron for m in meals), 2),
        }
    return summary


def _build_candidate_summary(candidates: list[Meal]) -> list[dict]:
    """Compact nutrient card for each candidate (limits token payload)."""
    return [
        {
            "id":        m.id,
            "name":      m.name,
            "calories":  m.calories,
            "protein":   m.protein,
            "leucine":   m.leucine,
            "fiber":     m.fiber,
            "sodium":    m.sodium,
            "omega3":    m.omega3,
            "calcium":   m.calcium,
            "iron":      m.iron,
            "zinc":      m.zinc,
            "folate":    m.folate,
            "vitamin_d": m.vitamin_d,
            "cost":      m.cost,
            "tags":      m.tags,
        }
        for m in candidates
    ]


def _build_prompt(
    issues: list[str],
    plan: MealPlan,
    targets: NutritionTargets,
    budget: float,
    profile: UserProfile,
    candidates_by_slot: dict[str, list[dict]],
    used_meal_ids: dict[str, list[str]],
) -> str:
    plan_summary = _build_plan_summary(plan)

    return f"""You are a clinical-grade AI nutrition agent tasked with improving a failing meal plan.

## PERSONA & GOAL
- Persona: {profile.persona}
- Goal: {profile.goal}
- Training phase: {profile.training_phase}
- Medical conditions: {profile.medical_conditions}
- Diet type: {profile.diet_type}
- Budget per day: {budget}

## DAILY NUTRITION TARGETS
- Calories: {targets.macros.calories} kcal
- Protein: {targets.macros.protein} g
- Leucine per meal (min): {targets.macros.leucine_per_meal} g  ← CRITICAL for muscle protein synthesis
- Net carbs: {targets.macros.net_carbs} g
- Fiber (min): {targets.macros.fiber} g
- Omega-3 (min): {targets.macros.omega3_min} g
- Sodium (max): {targets.micros.sodium_max} mg
- Calcium (min): {targets.micros.calcium_min} mg
- Iron (min): {targets.micros.iron_min} mg
- Vitamin D (min): {targets.micros.vitamin_d_min} IU
- Zinc (min): {targets.micros.zinc_min} mg
- Folate (min): {targets.micros.folate_min} mcg

## CURRENT PLAN STATE (per slot)
{json.dumps(plan_summary, indent=2)}

## ACTIVE ISSUES REQUIRING FIX (ordered by clinical priority)
{json.dumps(issues, indent=2)}

## PREVIOUSLY USED / EXCLUDED MEAL IDs (do NOT choose these — they are not in the candidate lists)
{json.dumps(used_meal_ids, indent=2)}

## AVAILABLE REPLACEMENT MEALS BY SLOT
Only choose a `selected_meal_id` from the IDs listed here. These are the ONLY valid choices.
{json.dumps(candidates_by_slot, indent=2)}

## YOUR TASK
1. Identify which slot most urgently needs fixing given the issues listed.
2. Review ONLY the available replacement meals for that slot in the section above.
3. Choose the SINGLE best meal to place in that slot. Your choice must:
   - Directly address as many listed issues as possible.
   - Respect the persona's medical conditions and diet type.
   - Not introduce new critical issues.
   - Have an ID that appears in the AVAILABLE REPLACEMENT MEALS section.
4. Return a structured ReplanDecision with your reasoning, the target_slot, and the selected_meal_id.

CRITICAL: `selected_meal_id` MUST be one of the `id` values from the AVAILABLE REPLACEMENT MEALS list.
Do NOT use any ID from the PREVIOUSLY USED section. Do NOT invent IDs.
"""


def replan_from_issues(
    issues: list[str],
    plan: MealPlan,
    targets: NutritionTargets,
    budget: float,
    profile: UserProfile,
    used_meal_ids: dict[str, list[str]],
) -> tuple[MealPlan, dict[str, list[str]], str]:
    """
    LLM-powered replanner: Gemini evaluates all active issues and the available
    candidate meals, then returns a structured decision on which swap to make.
    Falls back to heuristic if LLM fails.
    """
    log.info("llm_replan.start", issues=issues)

    # Sort issues by priority for the prompt context
    sorted_issues = sorted(
        issues,
        key=lambda i: PRIORITY.index(i.split(":")[0]) if i.split(":")[0] in PRIORITY else 99,
    )

    # Clone plan and used IDs
    new_plan = MealPlan(slots={k: list(v) for k, v in plan.slots.items()})
    new_used_ids = {k: list(v) for k, v in used_meal_ids.items()}

    # Collect all IDs currently assigned in the plan to avoid returning them as candidates
    current_plan_ids = []
    for meals in new_plan.slots.values():
        for m in meals:
            current_plan_ids.append(m.id)

    # Gather all replacement candidates for every slot (exclude already-used AND currently active)
    candidates_by_slot: dict[str, list[Meal]] = {}
    for slot in new_plan.slots.keys():
        avoid = list(set(new_used_ids.get(slot, []) + current_plan_ids))
        candidates_by_slot[slot] = fetch_suitable_meals_for_slot(
            slot, profile, avoid_ids=avoid
        )

    candidates_summary = {
        slot: _build_candidate_summary(meals)
        for slot, meals in candidates_by_slot.items()
        if meals
    }

    prompt = _build_prompt(sorted_issues, plan, targets, budget, profile, candidates_summary, new_used_ids)

    # ── Call Gemini ───────────────────────────────────────────────────────────
    try:
        llm = _get_llm()
        decision: ReplanDecision = llm.invoke(prompt)

        log.info(
            "llm_replan.decision",
            target_slot=decision.target_slot,
            selected_meal_id=decision.selected_meal_id,
            reasoning=decision.reasoning,
        )

        target_slot = decision.target_slot
        chosen_id = decision.selected_meal_id

        # Validate the slot exists
        if target_slot not in new_plan.slots:
            log.warning("llm_replan.invalid_slot", slot=target_slot)
            return _heuristic_fallback(sorted_issues, new_plan, profile, new_used_ids, candidates_by_slot)

        # Build a flat lookup of ALL candidates across all slots so that
        # the LLM can pick a meal that happens to appear under a different slot key
        # (e.g. meals tagged 'any' appear in multiple slot lists).
        all_candidates_map: dict[str, Meal] = {}
        for meal_list in candidates_by_slot.values():
            for m in meal_list:
                all_candidates_map[m.id] = m

        chosen_meal = all_candidates_map.get(chosen_id)
        if not chosen_meal:
            log.warning("llm_replan.invalid_meal_id", meal_id=chosen_id, slot=target_slot,
                        available_ids=list(all_candidates_map.keys())[:10])
            return _heuristic_fallback(sorted_issues, new_plan, profile, new_used_ids, candidates_by_slot)

        # Apply the swap
        old_meals = new_plan.slots[target_slot]
        if old_meals:
            evicted = old_meals[0]
            new_plan.slots[target_slot] = [m for m in old_meals if m.id != evicted.id]
            if target_slot not in new_used_ids:
                new_used_ids[target_slot] = []
            new_used_ids[target_slot].append(evicted.id)

        new_plan.slots[target_slot] = [chosen_meal]
        new_used_ids.setdefault(target_slot, []).append(chosen_meal.id)

        action = (
            f"[LLM] Swapped {target_slot} → '{chosen_meal.name}' | "
            f"Reasoning: {decision.reasoning[:200]}..."
        )
        return new_plan, new_used_ids, action

    except Exception as exc:
        log.error("llm_replan.error", error=str(exc))
        return _heuristic_fallback(sorted_issues, new_plan, profile, new_used_ids, candidates_by_slot)


# ── Heuristic fallback (used if LLM fails) ───────────────────────────────────
def _heuristic_fallback(
    sorted_issues: list[str],
    plan: MealPlan,
    profile: UserProfile,
    used_ids: dict[str, list[str]],
    candidates_by_slot: dict[str, list[Meal]],
) -> tuple[MealPlan, dict[str, list[str]], str]:
    """Original deterministic fallback when LLM is unavailable."""
    log.warning("llm_replan.fallback_to_heuristic")

    top_issue_str = sorted_issues[0]
    top_issue = top_issue_str.split(":")[0]

    # Determine target slot
    target_slot = None
    if ":slot=" in top_issue_str:
        for p in top_issue_str.split(":"):
            if p.startswith("slot="):
                target_slot = p.split("=")[1]
    else:
        if top_issue == "high_sodium":
            target_slot = _find_slot_with_max_metric(plan, "sodium")
        elif top_issue == "low_protein":
            target_slot = _find_slot_with_min_metric(plan, "protein")
        elif top_issue == "over_budget":
            target_slot = _find_slot_with_max_metric(plan, "cost")
        else:
            for s, meals in plan.slots.items():
                if meals:
                    target_slot = s
                    break

    if not target_slot or not plan.slots.get(target_slot):
        return plan, used_ids, f"[Heuristic] Failed to fix: {top_issue} (no slot)"

    old_meal = plan.slots[target_slot][0]
    plan.slots[target_slot] = [m for m in plan.slots[target_slot] if m.id != old_meal.id]
    used_ids.setdefault(target_slot, []).append(old_meal.id)

    candidates = candidates_by_slot.get(target_slot, [])
    candidates = _sort_candidates_for_issue(candidates, top_issue)

    if candidates:
        plan.slots[target_slot] = [candidates[0]]
        return plan, used_ids, f"[Heuristic] Swapped {target_slot} to fix {top_issue}"
    else:
        plan.slots[target_slot] = [old_meal]
        return plan, used_ids, f"[Heuristic] No alternative found for {target_slot}"


# ── Utility functions ────────────────────────────────────────────────────────
def _find_slot_with_max_metric(plan: MealPlan, metric: str) -> str | None:
    best_slot, max_val = None, -1
    for slot, meals in plan.slots.items():
        val = sum(getattr(m, metric) for m in meals)
        if val > max_val:
            max_val = val
            best_slot = slot
    return best_slot


def _find_slot_with_min_metric(plan: MealPlan, metric: str) -> str | None:
    best_slot, min_val = None, float("inf")
    for slot, meals in plan.slots.items():
        if not meals:
            continue
        val = sum(getattr(m, metric) for m in meals)
        if val < min_val:
            min_val = val
            best_slot = slot
    return best_slot


def _sort_candidates_for_issue(candidates: list[Meal], issue: str) -> list[Meal]:
    if issue == "low_protein":
        return sorted(candidates, key=lambda m: m.protein, reverse=True)
    if issue == "high_sodium":
        return sorted(candidates, key=lambda m: m.sodium)
    if issue == "over_budget":
        return sorted(candidates, key=lambda m: m.cost)
    if issue == "low_leucine_per_meal":
        return sorted(candidates, key=lambda m: m.leucine, reverse=True)
    return sorted(candidates, key=lambda m: m.protein, reverse=True)
