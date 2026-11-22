"""StateGraph builder for the agent."""

from langgraph.graph import StateGraph, END
from graph.state import AgentState
from graph.nodes import (
    detect_persona, compute_targets, build_timing_windows,
    fetch_meals, generate_plan, evaluate_plan, replan,
    force_finalize, finalize
)
from graph.edges import route_after_evaluation
from graph import agent as agentic

def build_graph(checkpointer=None):
    """
    Assembles the LangGraph workflow.

    Agentic path (default): agent <-> tools loop, where Gemini plans by calling
    tools, then agent_wrap_up re-checks the plan before finalize.
    Pipeline path (agentic off, no API key, or the agent's LLM fails / produces
    no plan): detect_persona -> ... -> generate -> evaluate <-> replan -> finalize.
    """
    g = StateGraph(AgentState)

    g.add_node("agent",                agentic.agent)
    g.add_node("tools",                agentic.tools)
    g.add_node("agent_wrap_up",        agentic.agent_wrap_up)

    g.add_node("detect_persona",       detect_persona)
    g.add_node("compute_targets",      compute_targets)
    g.add_node("build_timing_windows", build_timing_windows)
    g.add_node("fetch_meals",          fetch_meals)
    g.add_node("generate_plan",        generate_plan)
    g.add_node("evaluate_plan",        evaluate_plan)
    g.add_node("replan",               replan)
    g.add_node("force_finalize",       force_finalize)
    g.add_node("finalize",             finalize)

    g.set_conditional_entry_point(
        agentic.route_entry,
        {"agent": "agent", "detect_persona": "detect_persona"},
    )
    g.add_conditional_edges(
        "agent", agentic.route_after_agent,
        {"tools": "tools", "agent_wrap_up": "agent_wrap_up",
         "detect_persona": "detect_persona", "evaluate_plan": "evaluate_plan"},
    )
    g.add_conditional_edges(
        "tools", agentic.route_after_tools,
        {"agent": "agent", "agent_wrap_up": "agent_wrap_up"},
    )
    g.add_conditional_edges(
        "agent_wrap_up", agentic.route_after_wrap_up,
        {"finalize": "finalize", "detect_persona": "detect_persona"},
    )

    g.add_edge("detect_persona",       "compute_targets")
    g.add_edge("compute_targets",      "build_timing_windows")
    g.add_edge("build_timing_windows", "fetch_meals")
    g.add_edge("fetch_meals",          "generate_plan")
    g.add_edge("generate_plan",        "evaluate_plan")
    g.add_edge("force_finalize",       "finalize")
    g.add_edge("finalize",             END)

    g.add_conditional_edges(
        "evaluate_plan",
        route_after_evaluation,
        {
            "finalize": "finalize", 
            "replan": "replan", 
            "force_finalize": "force_finalize"
        },
    )
    
    # Re-evaluate the replanned plan directly; going back through generate_plan
    # would rebuild from scratch and discard the swap.
    g.add_edge("replan",               "evaluate_plan")

    return g.compile(checkpointer=checkpointer)
