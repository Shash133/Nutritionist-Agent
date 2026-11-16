# NutriGraph — Nutrition Planning Agent

A LangGraph agent that builds a one-day meal plan for a user profile (persona, goal,
diet type, medical conditions, allergies), checks it against macro/micro targets, and
replans with Gemini until the plan passes or the iteration limit is reached. Meals are
stored in Neo4j.

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
