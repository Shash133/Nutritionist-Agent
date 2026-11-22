# NutriGraph — Nutrition Planning Agent

A LangGraph agent that builds a one-day meal plan for a user profile (persona, goal,
diet type, medical conditions, allergies). Meals are stored in Neo4j.

## How it plans

By default the run is **agentic**: Gemini drives the whole plan through tool calls,
choosing what to look up, which meals to place, when to re-check and when to stop.

| Tool | What it does |
| --- | --- |
| `get_nutrition_targets` | Macro, micro and timing targets, supplements, medical notes, budget |
| `get_meal_slots` | The day's slots with times and the current plan |
| `search_meals` | Safe meals for a slot, with nutrient filters, keyword and sort |
| `get_meal_details` | Full nutrient profile and ingredients of one meal |
| `set_meal` / `clear_slot` | Edit the plan; returns updated day totals |
| `evaluate_plan` | All target and safety checks, with per-slot numbers |
| `finalize_plan` | Submit the plan with a short summary for the user |

Safety is enforced in the tools, not the prompt: the agent can only place meals from
the user's safe pool (diet, medical conditions, allergies, intolerances, dislikes) and
cannot serve the same dish twice. The graph caps the run at `MAX_AGENT_STEPS` LLM turns
(default 25) and re-checks the submitted plan before output.

If the LLM is unreachable, the agent produces no plan, or `AGENTIC=false` / no
`GOOGLE_API_KEY`, the run falls back to the fixed pipeline: generate → evaluate →
replan (LLM-picked swaps, or heuristic swaps if the LLM is down) → finalize. The
output's `planner` field says which path built the plan.

An agentic run makes roughly 8–20 Gemini calls, so at the default `GEMINI_RPM=10` it
takes 1–2 minutes. Raise `GEMINI_RPM` to your tier's limit to speed it up.

## Quick start

```bash
cd nutri-agent
pip install -r requirements.txt
# fill in .env: NEO4J_URI, NEO4J_USER/NEO4J_USERNAME, NEO4J_PASSWORD, GOOGLE_API_KEY
python -m db.seed_meals        # load the meal catalogue into Neo4j
streamlit run app.py           # UI   (or: python main.py for the CLI)
python -m pytest -q tests      # offline tests, no Neo4j or Gemini needed
```

## Data note

The meal catalogue in `nutri-agent/db/seed_meals.py` (~195 meals across all 8 diet
types, including common Indian dishes) uses **approximate per-serving nutrient
estimates** for a prototype. Values are kept internally consistent (calories match
macros, net carbs = carbs − fiber, glycemic load = GI × net carbs / 100) and sit in
realistic ranges from USDA FoodData Central and IFCT 2017, but they are not verified
measurements and should not be used for clinical decisions.

## Roadmap

- Load verified nutrient data from [USDA FoodData Central](https://fdc.nal.usda.gov/)
  (and IFCT 2017 for Indian foods) instead of hand-estimated values.
