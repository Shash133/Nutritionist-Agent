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
    
    # Agent loop (agentic mode)
    messages: list                     # LLM conversation; replaced, not appended, per update
    agent_steps: int                   # LLM turns taken this run
    agent_done: bool                   # agent called finalize_plan
    agent_summary: str                 # agent's closing explanation for the user
    planner: str                       # "agent" or "pipeline": which path built the final plan
    llm_failed: bool                   # LLM unreachable: fall back to the pipeline, no LLM replans

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
        "plan": None,
        "evaluation": None,
        "targets": None,
        "timing_windows": {},
        "candidate_meals": [],
        "messages": [],
        "agent_steps": 0,
        "agent_done": False,
        "agent_summary": "",
        "llm_failed": False,
    }
