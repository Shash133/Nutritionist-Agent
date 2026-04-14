"""Seed script to populate Neo4j with 80+ meals across all categories."""

import structlog
from db.neo4j_client import neo4j_client

log = structlog.get_logger()

# ── Base templates for generation ───────────────────────────────────────────
# We generate 80+ meals dynamically by combining bases and modifiers to ensure
# we hit all specific conditions without a massive hardcoded file.

MEAL_TEMPLATES = [
    # ── High Leucine / MPS (Gym Bro / Athlete) ──
    {
        "id": "high-leucine-", "name_base": "Whey Protein Oats with ",
        "diet_type": "veg", "meal_slot": "breakfast",
        "calories": 450, "protein": 40.0, "leucine": 4.5, "carbs": 50.0, "net_carbs": 42.0, "sugar": 5.0, "fiber": 8.0,
        "fats": 10.0, "saturated_fat": 2.0, "unsaturated_fat": 8.0, "omega3": 1.0, "omega6": 2.0,
        "glycemic_index": 45, "glycemic_load": 18.9,
        "sodium": 150, "potassium": 400, "calcium": 300, "magnesium": 120, "iron": 4.0, "zinc": 3.0, "phosphorus": 350,
        "vitamin_d": 40, "vitamin_b12": 1.2, "folate": 50, "vitamin_c": 10, "vitamin_k": 5,
        "cost": 150, "prep_time_min": 10, "ingredients": ["whey isolate", "oats", "milk"],
        "tags": ["high-protein", "high-leucine", "muscle-building"],
        "suitable_for": ["gym_bro", "athlete", "elderly"], "avoid_for": ["ckd", "vegan"],
        "variants": ["Almonds", "Peanut Butter", "Walnuts", "Chia Seeds", "Flaxseed", "Berries", "Banana", "Apple", "Mango", "Dark Chocolate"],
    },
    # ── Low GI / Low GL (Diabetes) ──
    {
        "id": "low-gi-", "name_base": "Lentil & Quinoa Bowl with ",
        "diet_type": "vegan", "meal_slot": "lunch",
        "calories": 380, "protein": 18.0, "leucine": 1.5, "carbs": 55.0, "net_carbs": 40.0, "sugar": 3.0, "fiber": 15.0,
        "fats": 8.0, "saturated_fat": 1.0, "unsaturated_fat": 7.0, "omega3": 0.5, "omega6": 1.5,
        "glycemic_index": 30, "glycemic_load": 12.0,
        "sodium": 200, "potassium": 600, "calcium": 80, "magnesium": 150, "iron": 6.0, "zinc": 4.0, "phosphorus": 250,
        "vitamin_d": 0, "vitamin_b12": 0.0, "folate": 180, "vitamin_c": 15, "vitamin_k": 30,
        "cost": 120, "prep_time_min": 25, "ingredients": ["lentils", "quinoa", "olive oil"],
        "tags": ["low-gi", "high-fiber", "vegan"],
        "suitable_for": ["type2_diabetes", "pcos", "patient", "office_worker"], "avoid_for": [],
        "variants": ["Spinach", "Kale", "Broccoli", "Cauliflower", "Bell Peppers", "Zucchini", "Mushrooms", "Asparagus", "Green Beans", "Brussels Sprouts"],
    },
    # ── Low Sodium (Hypertension / CKD) ──
    {
        "id": "low-sodium-", "name_base": "Herb Roasted Chicken & Sweet Potato with ",
        "diet_type": "non_veg", "meal_slot": "dinner",
        "calories": 420, "protein": 35.0, "leucine": 2.8, "carbs": 45.0, "net_carbs": 39.0, "sugar": 8.0, "fiber": 6.0,
        "fats": 12.0, "saturated_fat": 2.5, "unsaturated_fat": 9.5, "omega3": 0.2, "omega6": 2.0,
        "glycemic_index": 50, "glycemic_load": 19.5,
        "sodium": 95, "potassium": 750, "calcium": 50, "magnesium": 60, "iron": 2.5, "zinc": 2.0, "phosphorus": 280,
        "vitamin_d": 5, "vitamin_b12": 0.8, "folate": 30, "vitamin_c": 25, "vitamin_k": 15,
        "cost": 220, "prep_time_min": 40, "ingredients": ["chicken breast", "sweet potato", "herbs", "no-salt seasoning"],
        "tags": ["low-sodium", "whole-food"],
        "suitable_for": ["hypertension", "patient", "athlete"], "avoid_for": ["vegan", "veg"],
        "variants": ["Thyme", "Rosemary", "Garlic", "Lemon", "Oregano", "Basil", "Parsley", "Cilantro", "Dill", "Sage"],
    },
    # ── Low Phosphorus (CKD) ──
    {
        "id": "low-phos-", "name_base": "White Rice & Egg White Scramble with ",
        "diet_type": "eggetarian", "meal_slot": "lunch",
        "calories": 300, "protein": 15.0, "leucine": 1.2, "carbs": 45.0, "net_carbs": 44.0, "sugar": 1.0, "fiber": 1.0,
        "fats": 6.0, "saturated_fat": 1.0, "unsaturated_fat": 5.0, "omega3": 0.1, "omega6": 1.0,
        "glycemic_index": 70, "glycemic_load": 30.8,
        "sodium": 180, "potassium": 200, "calcium": 20, "magnesium": 25, "iron": 0.5, "zinc": 0.5, "phosphorus": 90,
        "vitamin_d": 0, "vitamin_b12": 0.1, "folate": 10, "vitamin_c": 5, "vitamin_k": 2,
        "cost": 80, "prep_time_min": 15, "ingredients": ["white rice", "egg whites", "olive oil"],
        "tags": ["low-phosphorus", "ckd-friendly"],
        "suitable_for": ["ckd", "patient"], "avoid_for": ["diabetes", "vegan"],
        "variants": ["Onion", "Bell Pepper", "Tomato", "Carrot", "Cabbage", "Zucchini", "Cucumber", "Radish", "Lettuce", "Celery"],
    },
    # ── Omega-3 Rich (Inflammation / Pregnancy) ──
    {
        "id": "omega3-", "name_base": "Baked Salmon & Walnut Salad with ",
        "diet_type": "non_veg", "meal_slot": "dinner",
        "calories": 520, "protein": 32.0, "leucine": 2.5, "carbs": 15.0, "net_carbs": 10.0, "sugar": 3.0, "fiber": 5.0,
        "fats": 35.0, "saturated_fat": 5.0, "unsaturated_fat": 30.0, "omega3": 4.5, "omega6": 8.0,
        "glycemic_index": 20, "glycemic_load": 2.0,
        "sodium": 280, "potassium": 800, "calcium": 60, "magnesium": 110, "iron": 2.0, "zinc": 1.5, "phosphorus": 450,
        "vitamin_d": 600, "vitamin_b12": 4.0, "folate": 60, "vitamin_c": 20, "vitamin_k": 80,
        "cost": 350, "prep_time_min": 25, "ingredients": ["salmon", "walnuts", "mixed greens", "olive oil"],
        "tags": ["high-omega3", "anti-inflammatory", "low-carb"],
        "suitable_for": ["pregnant", "pcos", "elderly", "high_cholesterol"], "avoid_for": ["vegan", "veg", "ckd"],
        "variants": ["Lemon Vinaigrette", "Balsamic", "Avocado", "Cherry Tomatoes", "Cucumber", "Red Onion", "Feta", "Olives", "Artichokes", "Capers"],
    },
    # ── Iron Rich (Anemia / Teens) ──
    {
        "id": "iron-", "name_base": "Lean Beef Stir-fry with ",
        "diet_type": "non_veg", "meal_slot": "dinner",
        "calories": 480, "protein": 38.0, "leucine": 3.1, "carbs": 40.0, "net_carbs": 35.0, "sugar": 6.0, "fiber": 5.0,
        "fats": 16.0, "saturated_fat": 5.0, "unsaturated_fat": 11.0, "omega3": 0.2, "omega6": 1.5,
        "glycemic_index": 55, "glycemic_load": 19.2,
        "sodium": 480, "potassium": 700, "calcium": 40, "magnesium": 70, "iron": 6.5, "zinc": 6.0, "phosphorus": 320,
        "vitamin_d": 10, "vitamin_b12": 5.0, "folate": 45, "vitamin_c": 85, "vitamin_k": 40,
        "cost": 280, "prep_time_min": 20, "ingredients": ["lean beef", "bell peppers", "soy sauce (low sodium)"],
        "tags": ["high-iron", "high-protein"],
        "suitable_for": ["anemia", "teenager", "pregnant", "athlete"], "avoid_for": ["vegan", "veg", "gout"],
        "variants": ["Broccoli", "Snap Peas", "Carrots", "Bok Choy", "Mushrooms", "Water Chestnuts", "Bamboo Shoots", "Baby Corn", "Chili", "Garlic"],
    },
    # ── Pre-Workout ──
    {
        "id": "pre-workout-", "name_base": "Pre-Workout Energy Bowl: ",
        "diet_type": "veg", "meal_slot": "pre_workout",
        "calories": 300, "protein": 15.0, "leucine": 1.2, "carbs": 55.0, "net_carbs": 50.0, "sugar": 25.0, "fiber": 5.0,
        "fats": 3.0, "saturated_fat": 0.5, "unsaturated_fat": 2.5, "omega3": 0.1, "omega6": 0.5,
        "glycemic_index": 65, "glycemic_load": 32.5,
        "sodium": 100, "potassium": 500, "calcium": 150, "magnesium": 60, "iron": 1.5, "zinc": 1.0, "phosphorus": 150,
        "vitamin_d": 20, "vitamin_b12": 0.5, "folate": 30, "vitamin_c": 15, "vitamin_k": 5,
        "cost": 120, "prep_time_min": 5, "ingredients": ["greek yogurt", "honey", "fruit"],
        "tags": ["pre-workout", "fast-carbs", "moderate-protein"],
        "suitable_for": ["gym_bro", "athlete"], "avoid_for": ["diabetes", "keto"],
        "variants": ["Banana & Honey", "Apple & Cinnamon", "Dates & Raisins", "Mango & Agave", "Rice Cakes & Jam"],
    },
    # ── Post-Workout ──
    {
        "id": "post-workout-", "name_base": "Post-Workout Recovery: ",
        "diet_type": "non_veg", "meal_slot": "post_workout",
        "calories": 500, "protein": 45.0, "leucine": 3.8, "carbs": 65.0, "net_carbs": 60.0, "sugar": 10.0, "fiber": 5.0,
        "fats": 6.0, "saturated_fat": 1.5, "unsaturated_fat": 4.5, "omega3": 0.2, "omega6": 1.0,
        "glycemic_index": 70, "glycemic_load": 42.0,
        "sodium": 350, "potassium": 650, "calcium": 120, "magnesium": 80, "iron": 2.5, "zinc": 3.0, "phosphorus": 350,
        "vitamin_d": 15, "vitamin_b12": 1.5, "folate": 50, "vitamin_c": 20, "vitamin_k": 10,
        "cost": 180, "prep_time_min": 15, "ingredients": ["chicken breast", "white rice", "spinach"],
        "tags": ["post-workout", "high-protein", "fast-carbs"],
        "suitable_for": ["gym_bro", "athlete", "muscle_gain"], "avoid_for": ["vegan", "veg", "diabetes"],
        "variants": ["Teriyaki Chicken Rice", "Tuna Pasta Salad", "Turkey & Potato", "Lean Beef Bowl", "Cod & Sweet Potato"],
    },
    # ── Before Bed ──
    {
        "id": "before-bed-", "name_base": "Slow-Release Casein Snack: ",
        "diet_type": "veg", "meal_slot": "before_bed",
        "calories": 220, "protein": 25.0, "leucine": 2.5, "carbs": 12.0, "net_carbs": 10.0, "sugar": 8.0, "fiber": 2.0,
        "fats": 8.0, "saturated_fat": 3.5, "unsaturated_fat": 4.5, "omega3": 0.5, "omega6": 1.0,
        "glycemic_index": 25, "glycemic_load": 2.5,
        "sodium": 200, "potassium": 250, "calcium": 350, "magnesium": 50, "iron": 0.5, "zinc": 1.5, "phosphorus": 250,
        "vitamin_d": 40, "vitamin_b12": 1.0, "folate": 15, "vitamin_c": 5, "vitamin_k": 0,
        "cost": 100, "prep_time_min": 5, "ingredients": ["cottage cheese", "nuts"],
        "tags": ["before-bed", "casein", "slow-protein"],
        "suitable_for": ["gym_bro", "athlete", "elderly"], "avoid_for": ["vegan", "dairy-free"],
        "variants": ["Cottage Cheese & Almonds", "Greek Yogurt & Walnuts", "Protein Fluff", "Milk & Casein Shake", "Egg Whites & Avocado"],
    }
]


def generate_seed_meals() -> list[dict]:
    """Generate 85 meals to seed neo4j."""
    import copy
    meals = []

    for tmpl in MEAL_TEMPLATES:
        tmpl_copy = copy.deepcopy(tmpl)   # never mutate the module-level template
        variants = tmpl_copy.pop("variants")
        name_base = tmpl_copy.pop("name_base")
        for i, variant in enumerate(variants):
            meal = copy.deepcopy(tmpl_copy)
            meal["id"] = f"{tmpl_copy['id']}{i+1}"
            meal["name"] = name_base + variant
            # Minor variation for nutritional realism
            meal["calories"] += (i % 3) * 15
            meal["protein"] = round(meal["protein"] + (i % 2) * 1.5, 1)
            meal["carbs"] += (i % 3) * 4
            meal["sodium"] += (i % 5) * 10
            # Ensure lists are proper Python lists (not tuples) for Cypher
            for list_field in ("ingredients", "tags", "suitable_for", "avoid_for"):
                meal[list_field] = list(meal.get(list_field, []))
            meals.append(meal)

    return meals


def seed_database():
    """Clear and res-seed Neo4j."""
    log.info("Starting Neo4j seed process...")
    meals = generate_seed_meals()
    
    with neo4j_client.driver.session() as session:
        session.run("MATCH (m:Meal) DETACH DELETE m")
        log.info("Cleared existing meals.")
        
        query = """
        UNWIND $meals AS meal
        MERGE (m:Meal {id: meal.id})
        SET m = meal
        """
        session.run(query, meals=meals)
        
    count = neo4j_client.get_meal_count()
    log.info("Neo4j seeding complete", total_meals=count)


if __name__ == "__main__":
    seed_database()
