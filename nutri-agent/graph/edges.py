"""Edges and routing logic for the LangGraph."""

from graph.state import AgentState
from config import settings

def route_after_evaluation(state: AgentState) -> str:
    """
    Decides where to go after evaluating a generated or replanned plan.
    """
    eval_result = state["evaluation"]
    
    if eval_result.valid:
        return "finalize"
        
    if state["iteration"] >= settings.max_replan_iterations:
        return "force_finalize"
        
    return "replan"
