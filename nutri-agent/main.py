"""CLI entry point for testing the NutriGraph Agent."""

import json
import uuid
import structlog
from langgraph.checkpoint.sqlite import SqliteSaver
from graph.builder import build_graph
from graph.state import initial_state
from models.user_profile import UserProfile

log = structlog.get_logger()

SQLITE_DB_PATH = "nutrigraph_sessions.db"

# Sample Gym Bro profile for testing
sample_profile_dict = {
    "age": 22,
    "gender": "male",
    "weight": 90.0,
    "height": 178.0,
    "body_fat_pct": 28.0,
    "activity_level": "lightly_active",
    "persona": "office_worker",
    "goal": "fat_loss",
    "training_phase": "maintenance",
    "sport": "none",
    "training_days_per_week": 4,
    "training_session_duration_min": 45,
    "workout_time": "evening",
    "diet_type": "non_veg",
    "budget_per_day": 40.0,
    "meals_per_day": 3,
    "allergies": [],
    "intolerances": [],
    "likes": [],
    "dislikes": [],
    "medical_conditions": ["none"],
    "medications": [],
    "pregnancy_trimester": "none",
    "supplement_openness": "advanced"
}


def main(thread_id: str | None = None):
    """
    Run the NutriGraph agent.
    Pass an existing thread_id to resume a previous session (SqliteSaver checkpointing).
    """
    log.info("Starting NutriGraph CLI...")

    profile = UserProfile(**sample_profile_dict)
    log.info("Loaded profile", persona=profile.persona, goal=profile.goal,
             lbm=profile.lean_body_mass, ffmi=profile.ffmi)

    # ── SqliteSaver checkpointer (spec requirement #14) ──────────────────────
    # Each unique thread_id = one conversation/session. Pass the same thread_id
    # to resume from where the agent left off.
    with SqliteSaver.from_conn_string(SQLITE_DB_PATH) as checkpointer:
        agent = build_graph(checkpointer=checkpointer)

        thread_id = thread_id or str(uuid.uuid4())
        log.info("Session thread_id", thread_id=thread_id)

        state_input = initial_state(profile)

        config = {"configurable": {"thread_id": thread_id}}

        log.info("Running agent workflow...")
        final_state = agent.invoke(state_input, config=config)
        log.info("Workflow completed", status=final_state.get("status"))

        if "final_output" in final_state:
            output_json = json.dumps(final_state["final_output"], indent=2)
            print("\n=== FINAL OUTPUT ===\n")
            print(output_json)

            with open("sample_output.json", "w") as f:
                f.write(output_json)
            print(f"\nSaved output to sample_output.json  (thread_id={thread_id})")
        else:
            log.error("No final output generated", status=final_state.get("status"))

    return thread_id


if __name__ == "__main__":
    import sys
    # Optionally pass a previous thread_id as CLI arg to resume session
    prev_thread = sys.argv[1] if len(sys.argv) > 1 else None
    main(thread_id=prev_thread)
