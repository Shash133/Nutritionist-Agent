"""FastAPI endpoints."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
import structlog
from graph.builder import build_graph
from graph.state import initial_state
from models.user_profile import UserProfile

log = structlog.get_logger()
app = FastAPI(title="NutriGraph Advanced AI Agent API")

agent = build_graph()

class PlanRequest(BaseModel):
    profile: UserProfile

@app.post("/api/v1/generate-plan")
def generate_plan(request: PlanRequest):
    """
    Generate a meal plan for a specific persona profile.
    Sync `def` on purpose: agent.invoke blocks (Neo4j + Gemini), so FastAPI
    runs it in a threadpool instead of stalling the event loop.
    """
    log.info("API request received", persona=request.profile.persona)

    state_input = initial_state(request.profile)

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    try:
        final_state = agent.invoke(state_input, config=config)
    except Exception:
        log.exception("Plan generation failed", thread_id=thread_id)
        raise HTTPException(
            status_code=500,
            detail=f"Plan generation failed (thread_id={thread_id}). See server logs.",
        )

    if "final_output" not in final_state:
        raise HTTPException(status_code=500, detail="Agent failed to generate a plan.")
    return final_state["final_output"]

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy"}
