"""Agent state schema for the LangGraph pipeline."""

from typing import TypedDict, Optional, Annotated, List
import operator
from models.user_profile import UserProfile
from models.meal_plan import NutritionTargets, MealPlan, EvaluationResult
from models.meal import Meal

class AgentState(TypedDict):
    """The state dictionary passed between nodes in the graph."""
    
    # Context
    profile: UserProfile
    persona_config: dict               # resolved persona rules
    targets: Optional[NutritionTargets]
    timing_windows: dict               # e.g. {"pre_workout": "17:00"}
    
    # State
    candidate_meals: list[Meal]
    plan: Optional[MealPlan]
    evaluation: Optional[EvaluationResult]
    
    # Loop control
    iteration: int
    used_meal_ids: dict[str, list[str]]
    all_issues: Annotated[list[str], operator.add]
    
    # Memory (persisted via SqliteSaver)
    user_history: list[dict]
    preference_memo: dict
    
    # Terminal
    status: str
    final_output: Optional[dict]
    llm_reasoning: Annotated[List[str], operator.add]  # all LLM replan traces


def initial_state(profile: UserProfile) -> dict:
    """
    Input for a new agent run. Memory keys (user_history, preference_memo) are
    deliberately omitted so a resumed thread keeps its checkpointed values.
    """
    return {
        "profile": profile,
        "iteration": 0,
        "used_meal_ids": {},
    }
