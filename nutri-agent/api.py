"""FastAPI endpoints."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
import structlog
from graph.builder import build_graph
from models.user_profile import UserProfile

log = structlog.get_logger()
app = FastAPI(title="NutriGraph Advanced AI Agent API")

agent = build_graph()

class PlanRequest(BaseModel):
    profile: UserProfile

@app.post("/api/v1/generate-plan")
async def generate_plan(request: PlanRequest):
    """Generate a meal plan for a specific persona profile."""
    log.info("API request received", persona=request.profile.persona)
    
    initial_state = {
        "profile": request.profile,
        "iteration": 0,
        "used_meal_ids": {},
        "all_issues": [],
        "user_history": [],
        "preference_memo": {},
        "llm_reasoning": [],
    }
    
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        final_state = agent.invoke(initial_state, config=config)
        
        if "final_output" in final_state:
            return final_state["final_output"]
        else:
            raise HTTPException(status_code=500, detail="Agent failed to generate a plan.")
            
    except Exception as e:
        log.exception("Plan generation failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy"}
