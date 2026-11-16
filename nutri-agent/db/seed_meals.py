"""Seed script to populate Neo4j with ~195 meals across all diet types and slots."""

import structlog
from db.neo4j_client import neo4j_client

log = structlog.get_logger()

# ── Base templates for generation ───────────────────────────────────────────
# We generate meals dynamically by combining bases and modifiers to ensure
# we hit all specific conditions without a massive hardcoded file.
# Each variant is a name suffix, or (suffix, extra_ingredients[, extra_avoid_for]);
# list every ingredient a variant adds so allergen/dislike filtering can match it.

MEAL_TEMPLATES = [
    # ── High Leucine / MPS (Gym Bro / Athlete) ──
    {
        "id": "high-leucine-", "name_base": "Whey Protein Oats with ",
        "diet_type": "veg", "meal_slot": "breakfast",
        "calories": 450, "protein": 40.0, "leucine": 3.5, "carbs": 50.0, "net_carbs": 42.0, "sugar": 5.0, "fiber": 8.0,
        "fats": 10.0, "saturated_fat": 2.0, "unsaturated_fat": 8.0, "omega3": 1.0, "omega6": 2.0,
        "glycemic_index": 45, "glycemic_load": 18.9,
        "sodium": 150, "potassium": 400, "calcium": 300, "magnesium": 120, "iron": 4.0, "zinc": 3.0, "phosphorus": 350,
        "vitamin_d": 40, "vitamin_b12": 1.2, "folate": 50, "vitamin_c": 10, "vitamin_k": 5,
        "cost": 150, "prep_time_min": 10, "ingredients": ["whey isolate", "oats", "milk"],
        "tags": ["high-protein", "high-leucine", "muscle-building"],
        "suitable_for": ["gym_bro", "athlete", "elderly"], "avoid_for": ["ckd"],
        "variants": [("Almonds", ["almonds", "tree nuts"]), ("Peanut Butter", ["peanuts"]), ("Walnuts", ["walnuts", "tree nuts"]),
                     ("Chia Seeds", ["chia seeds"]), ("Flaxseed", ["flaxseed"]), ("Berries", ["mixed berries"]), ("Banana", ["banana"]),
                     ("Apple", ["apple"]), ("Mango", ["mango"]), ("Dark Chocolate", ["dark chocolate"])],
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
        "suitable_for": ["hypertension", "patient", "athlete"], "avoid_for": [],
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
        "cost": 80, "prep_time_min": 15, "ingredients": ["white rice", "egg whites", "egg", "olive oil"],
        "tags": ["low-phosphorus", "ckd-friendly"],
        "suitable_for": ["ckd", "patient"], "avoid_for": ["type2_diabetes", "type1_diabetes"],
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
        "cost": 350, "prep_time_min": 25, "ingredients": ["salmon", "fish", "walnuts", "tree nuts", "mixed greens", "olive oil"],
        "tags": ["high-omega3", "anti-inflammatory", "low-carb"],
        "suitable_for": ["pregnant", "pcos", "elderly", "high_cholesterol"], "avoid_for": ["ckd"],
        "variants": [("Lemon Vinaigrette", ["lemon"]), ("Balsamic", ["balsamic vinegar"]), ("Avocado", ["avocado"]),
                     ("Cherry Tomatoes", ["tomato"]), ("Cucumber", ["cucumber"]), ("Red Onion", ["red onion"]),
                     ("Feta", ["feta cheese", "milk"]), ("Olives", ["olives"]), ("Artichokes", ["artichokes"]), ("Capers", ["capers"])],
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
        "cost": 280, "prep_time_min": 20, "ingredients": ["lean beef", "bell peppers", "soy sauce (low sodium)", "soy", "wheat"],
        "tags": ["high-iron", "high-protein"],
        "suitable_for": ["anemia", "teenager", "pregnant", "athlete"], "avoid_for": ["gout", "celiac"],
        "variants": [("Broccoli", ["broccoli"]), ("Snap Peas", ["snap peas"]), ("Carrots", ["carrot"]), ("Bok Choy", ["bok choy"]),
                     ("Mushrooms", ["mushrooms"]), ("Water Chestnuts", ["water chestnuts"]), ("Bamboo Shoots", ["bamboo shoots"]),
                     ("Baby Corn", ["baby corn"]), ("Chili", ["chili"]), ("Garlic", ["garlic"])],
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
        "cost": 120, "prep_time_min": 5, "ingredients": ["greek yogurt", "milk", "honey", "fruit"],
        "tags": ["pre-workout", "fast-carbs", "moderate-protein"],
        "suitable_for": ["gym_bro", "athlete"], "avoid_for": ["type2_diabetes", "type1_diabetes"],
        "variants": [("Banana & Honey", ["banana"]), ("Apple & Cinnamon", ["apple", "cinnamon"]), ("Dates & Raisins", ["dates", "raisins"]),
                     ("Mango & Agave", ["mango", "agave syrup"]), ("Rice Cakes & Jam", ["rice cakes", "jam"])],
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
        # Variants swap the protein/carb base, so each lists its own main ingredients.
        "cost": 180, "prep_time_min": 15, "ingredients": ["spinach"],
        "tags": ["post-workout", "high-protein", "fast-carbs"],
        "suitable_for": ["gym_bro", "athlete", "muscle_gain"], "avoid_for": ["type2_diabetes", "type1_diabetes"],
        "variants": [("Teriyaki Chicken Rice", ["chicken breast", "white rice", "teriyaki sauce", "soy", "wheat"], ["celiac"]),
                     ("Tuna Pasta Salad", ["tuna", "fish", "pasta", "wheat", "gluten"], ["celiac", "gout"]),
                     ("Turkey & Potato", ["turkey", "potato"]),
                     ("Lean Beef Bowl", ["lean beef", "white rice"], ["gout"]),
                     ("Cod & Sweet Potato", ["cod", "fish", "sweet potato"])],
    },
    # ── Before Bed ──
    {
        "id": "before-bed-", "name_base": "Slow-Release Casein Snack: ",
        "diet_type": "veg", "meal_slot": "before_bed",
        "calories": 220, "protein": 25.0, "leucine": 2.2, "carbs": 12.0, "net_carbs": 10.0, "sugar": 8.0, "fiber": 2.0,
        "fats": 8.0, "saturated_fat": 3.5, "unsaturated_fat": 4.5, "omega3": 0.5, "omega6": 1.0,
        "glycemic_index": 25, "glycemic_load": 2.5,
        "sodium": 200, "potassium": 250, "calcium": 350, "magnesium": 50, "iron": 0.5, "zinc": 1.5, "phosphorus": 250,
        "vitamin_d": 40, "vitamin_b12": 1.0, "folate": 15, "vitamin_c": 5, "vitamin_k": 0,
        # Variants differ in base, so each lists its own main ingredients.
        "cost": 100, "prep_time_min": 5, "ingredients": [],
        "tags": ["before-bed", "casein", "slow-protein"],
        "suitable_for": ["gym_bro", "athlete", "elderly"], "avoid_for": [],
        "variants": [("Cottage Cheese & Almonds", ["cottage cheese", "milk", "almonds", "tree nuts"]),
                     ("Greek Yogurt & Walnuts", ["greek yogurt", "milk", "walnuts", "tree nuts"]),
                     ("Protein Fluff", ["casein protein", "milk"]),
                     ("Milk & Casein Shake", ["casein protein", "milk"]),
                     ("Egg Whites & Avocado", ["egg whites", "egg", "avocado"])],
    },
    # ═════════════════════════════════════════════════════════════════════
    # Expanded catalogue: Indian dishes, every diet type and clinical needs.
    # Values are approximate per-serving estimates (USDA FDC / IFCT 2017 ranges).
    # ═════════════════════════════════════════════════════════════════════
    # ── Indian: Vegetable Poha (vegan breakfast, CKD-friendly) ──
    # Serving: ~250 g cooked (60 g dry flattened rice), 1 tsp oil
    {
        "id": "poha-", "name_base": "Vegetable Poha with ",
        "diet_type": "vegan", "meal_slot": "breakfast",
        "calories": 280, "protein": 6.0, "leucine": 0.45, "carbs": 48.0, "net_carbs": 45.0, "sugar": 3.0, "fiber": 3.0,
        "fats": 7.0, "saturated_fat": 1.0, "unsaturated_fat": 6.0, "omega3": 0.1, "omega6": 2.0,
        "glycemic_index": 64, "glycemic_load": 28.8,
        "sodium": 300, "potassium": 180, "calcium": 20, "magnesium": 30, "iron": 2.5, "zinc": 0.9, "phosphorus": 90,
        "vitamin_d": 0, "vitamin_b12": 0.0, "folate": 20, "vitamin_c": 10, "vitamin_k": 5,
        "cost": 40, "prep_time_min": 15, "ingredients": ["flattened rice (poha)", "onion", "mustard seeds", "curry leaves", "turmeric", "vegetable oil", "lemon"],
        "tags": ["indian", "light", "low-protein", "low-phosphorus", "low-potassium", "low-purine"],
        "suitable_for": ["office_worker", "teenager", "ckd", "patient", "gout"], "avoid_for": ["type2_diabetes", "type1_diabetes"],
        "variants": [("Peanuts", ["peanuts"]), ("Green Peas", ["green peas"]), ("Pomegranate", ["pomegranate"])],
    },
    # ── Indian: Rava Upma (vegan breakfast, CKD-friendly) ──
    # Serving: ~220 g cooked (60 g semolina), 1 tsp oil
    {
        "id": "upma-", "name_base": "Rava Upma with ",
        "diet_type": "vegan", "meal_slot": "breakfast",
        "calories": 280, "protein": 7.0, "leucine": 0.49, "carbs": 45.0, "net_carbs": 42.0, "sugar": 2.0, "fiber": 3.0,
        "fats": 8.0, "saturated_fat": 1.0, "unsaturated_fat": 7.0, "omega3": 0.1, "omega6": 2.5,
        "glycemic_index": 66, "glycemic_load": 27.7,
        "sodium": 320, "potassium": 150, "calcium": 25, "magnesium": 25, "iron": 1.5, "zinc": 0.7, "phosphorus": 95,
        "vitamin_d": 0, "vitamin_b12": 0.0, "folate": 40, "vitamin_c": 5, "vitamin_k": 5,
        "cost": 35, "prep_time_min": 20, "ingredients": ["semolina (rava)", "wheat", "gluten", "onion", "mustard seeds", "curry leaves", "green chili", "vegetable oil"],
        "tags": ["indian", "low-protein", "low-phosphorus", "low-potassium", "low-purine"],
        "suitable_for": ["office_worker", "elderly", "ckd", "patient", "gout"], "avoid_for": ["celiac", "type2_diabetes", "type1_diabetes"],
        "variants": [("Mixed Vegetables", ["carrot", "green peas", "beans"]), ("Cashews", ["cashews", "tree nuts"]), ("Tomato", ["tomato"])],
    },
    # ── Indian: Idli Sambar (vegan breakfast, gluten-free) ──
    # Serving: 3 idlis (~150 g) + 150 ml sambar
    {
        "id": "idli-", "name_base": "Idli Sambar with ",
        "diet_type": "vegan", "meal_slot": "breakfast",
        "calories": 310, "protein": 11.0, "leucine": 0.82, "carbs": 58.0, "net_carbs": 52.0, "sugar": 4.0, "fiber": 6.0,
        "fats": 4.0, "saturated_fat": 0.6, "unsaturated_fat": 3.4, "omega3": 0.1, "omega6": 1.0,
        "glycemic_index": 62, "glycemic_load": 32.2,
        "sodium": 520, "potassium": 380, "calcium": 60, "magnesium": 60, "iron": 2.8, "zinc": 1.5, "phosphorus": 200,
        "vitamin_d": 0, "vitamin_b12": 0.0, "folate": 70, "vitamin_c": 12, "vitamin_k": 10,
        "cost": 60, "prep_time_min": 20, "ingredients": ["rice", "urad dal (black gram)", "toor dal (pigeon pea)", "tamarind", "mixed vegetables", "mustard seeds", "vegetable oil"],
        "tags": ["indian", "fermented", "gluten-free", "low-fat", "low-purine"],
        "suitable_for": ["office_worker", "elderly", "teenager", "celiac", "gout"], "avoid_for": ["type2_diabetes", "type1_diabetes"],
        "variants": [("Coconut Chutney", ["coconut"]), ("Tomato Chutney", ["tomato"]), ("Mint Chutney", ["mint", "coriander"])],
    },
    # ── Indian: Moong Dal Chilla (vegan breakfast, low-GI) ──
    # Serving: 2 chillas (60 g dry moong dal), 1 tsp oil
    {
        "id": "moong-chilla-", "name_base": "Moong Dal Chilla with ",
        "diet_type": "vegan", "meal_slot": "breakfast",
        "calories": 265, "protein": 14.0, "leucine": 1.12, "carbs": 36.0, "net_carbs": 28.0, "sugar": 2.0, "fiber": 8.0,
        "fats": 7.0, "saturated_fat": 1.0, "unsaturated_fat": 6.0, "omega3": 0.1, "omega6": 2.5,
        "glycemic_index": 38, "glycemic_load": 10.6,
        "sodium": 280, "potassium": 520, "calcium": 60, "magnesium": 80, "iron": 3.2, "zinc": 1.6, "phosphorus": 220,
        "vitamin_d": 0, "vitamin_b12": 0.0, "folate": 250, "vitamin_c": 8, "vitamin_k": 10,
        "cost": 45, "prep_time_min": 20, "ingredients": ["moong dal (green gram)", "onion", "green chili", "coriander", "ginger", "vegetable oil"],
        "tags": ["indian", "low-gi", "high-protein", "high-folate", "gluten-free"],
        "suitable_for": ["type2_diabetes", "pcos", "office_worker", "pregnant", "celiac"], "avoid_for": ["ckd"],
        "variants": [("Mint Chutney", ["mint"]), ("Spinach", ["spinach"]), ("Tomato Onion Topping", ["tomato"])],
    },
    # ── Indian: Dal Tadka & Roti (vegan dinner, high-fibre) ──
    # Serving: 1 cup (200 g) dal + 2 whole wheat rotis (60 g atta), oil tadka
    {
        "id": "dal-roti-", "name_base": "Dal Tadka & Whole Wheat Roti with ",
        "diet_type": "vegan", "meal_slot": "dinner",
        "calories": 395, "protein": 16.0, "leucine": 1.2, "carbs": 62.0, "net_carbs": 51.0, "sugar": 3.0, "fiber": 11.0,
        "fats": 9.0, "saturated_fat": 1.2, "unsaturated_fat": 7.8, "omega3": 0.2, "omega6": 3.5,
        "glycemic_index": 48, "glycemic_load": 24.5,
        "sodium": 450, "potassium": 550, "calcium": 70, "magnesium": 110, "iron": 4.0, "zinc": 2.4, "phosphorus": 280,
        "vitamin_d": 0, "vitamin_b12": 0.0, "folate": 180, "vitamin_c": 10, "vitamin_k": 12,
        "cost": 50, "prep_time_min": 30, "ingredients": ["toor dal (pigeon pea)", "whole wheat flour (atta)", "wheat", "gluten", "onion", "tomato", "cumin", "garlic", "vegetable oil"],
        "tags": ["indian", "high-fiber", "plant-protein"],
        "suitable_for": ["office_worker", "teenager", "pregnant"], "avoid_for": ["celiac", "ckd"],
        "variants": [("Cucumber Salad", ["cucumber"]), ("Onion Salad", ["onion"]), ("Spinach (Dal Palak)", ["spinach"])],
    },
    # ── Indian: Rajma Chawal (vegan lunch, iron-rich) ──
    # Serving: 1 cup (200 g) rajma curry + 1 cup (150 g) cooked rice
    {
        "id": "rajma-chawal-", "name_base": "Rajma Chawal with ",
        "diet_type": "vegan", "meal_slot": "lunch",
        "calories": 430, "protein": 15.0, "leucine": 1.2, "carbs": 75.0, "net_carbs": 63.0, "sugar": 4.0, "fiber": 12.0,
        "fats": 8.0, "saturated_fat": 1.0, "unsaturated_fat": 7.0, "omega3": 0.3, "omega6": 3.0,
        "glycemic_index": 52, "glycemic_load": 32.8,
        "sodium": 480, "potassium": 700, "calcium": 80, "magnesium": 100, "iron": 4.5, "zinc": 2.0, "phosphorus": 290,
        "vitamin_d": 0, "vitamin_b12": 0.0, "folate": 200, "vitamin_c": 8, "vitamin_k": 10,
        "cost": 60, "prep_time_min": 40, "ingredients": ["kidney beans (rajma)", "white rice", "onion", "tomato", "ginger", "garlic", "vegetable oil"],
        "tags": ["indian", "high-fiber", "iron-rich", "gluten-free"],
        "suitable_for": ["office_worker", "teenager", "anemia", "celiac"], "avoid_for": ["ckd", "type2_diabetes", "type1_diabetes"],
        "variants": [("Jeera Rice", ["cumin"]), ("Onion Salad", ["onion"]), ("Cucumber Raita (Dairy-free)", ["cucumber", "coconut yogurt", "coconut"])],
    },
    # ── Indian: Sprouts Chaat (vegan snack, low-GI) ──
    # Serving: 1 cup (~150 g) mixed moong sprouts
    {
        "id": "sprouts-chaat-", "name_base": "Sprouts Chaat with ",
        "diet_type": "vegan", "meal_slot": "snack",
        "calories": 150, "protein": 9.0, "leucine": 0.72, "carbs": 24.0, "net_carbs": 17.0, "sugar": 4.0, "fiber": 7.0,
        "fats": 2.0, "saturated_fat": 0.3, "unsaturated_fat": 1.7, "omega3": 0.1, "omega6": 0.6,
        "glycemic_index": 30, "glycemic_load": 5.1,
        "sodium": 220, "potassium": 420, "calcium": 40, "magnesium": 60, "iron": 2.6, "zinc": 1.2, "phosphorus": 160,
        "vitamin_d": 0, "vitamin_b12": 0.0, "folate": 160, "vitamin_c": 25, "vitamin_k": 25,
        "cost": 40, "prep_time_min": 10, "ingredients": ["moong sprouts (green gram)", "onion", "tomato", "lemon", "chaat masala", "coriander"],
        "tags": ["indian", "low-gi", "low-fat", "high-fiber", "gluten-free", "iron-rich"],
        "suitable_for": ["type2_diabetes", "pcos", "office_worker", "anemia", "celiac"], "avoid_for": [],
        "variants": [("Pomegranate", ["pomegranate"]), ("Cucumber", ["cucumber"]), ("Roasted Peanuts", ["peanuts"])],
    },
    # ── Indian: Paneer Bhurji (veg breakfast, calcium-rich) ──
    # Serving: 100 g paneer scramble + 2 slices multigrain toast
    {
        "id": "paneer-bhurji-", "name_base": "Paneer Bhurji & Multigrain Toast with ",
        "diet_type": "veg", "meal_slot": "breakfast",
        "calories": 405, "protein": 24.0, "leucine": 2.16, "carbs": 28.0, "net_carbs": 24.0, "sugar": 4.0, "fiber": 4.0,
        "fats": 22.0, "saturated_fat": 12.0, "unsaturated_fat": 10.0, "omega3": 0.2, "omega6": 1.5,
        "glycemic_index": 45, "glycemic_load": 10.8,
        "sodium": 420, "potassium": 300, "calcium": 450, "magnesium": 50, "iron": 1.5, "zinc": 2.8, "phosphorus": 380,
        "vitamin_d": 10, "vitamin_b12": 0.6, "folate": 50, "vitamin_c": 15, "vitamin_k": 8,
        "cost": 110, "prep_time_min": 15, "ingredients": ["paneer (cottage cheese)", "milk", "onion", "tomato", "multigrain bread", "wheat", "gluten", "ghee"],
        "tags": ["indian", "calcium-rich", "high-protein", "low-purine"],
        "suitable_for": ["osteoporosis", "gym_bro", "teenager", "elderly", "gout"], "avoid_for": ["ckd", "high_cholesterol", "celiac"],
        "variants": [("Capsicum", ["bell peppers"]), ("Green Peas", ["green peas"]), ("Spinach", ["spinach"])],
    },
    # ── Indian: Curd Rice (veg lunch, gluten-free, low-purine) ──
    # Serving: 1 bowl (~250 g): 150 g cooked rice + 100 g curd
    {
        "id": "curd-rice-", "name_base": "Curd Rice with ",
        "diet_type": "veg", "meal_slot": "lunch",
        "calories": 315, "protein": 9.0, "leucine": 0.77, "carbs": 52.0, "net_carbs": 50.5, "sugar": 6.0, "fiber": 1.5,
        "fats": 8.0, "saturated_fat": 4.5, "unsaturated_fat": 3.5, "omega3": 0.1, "omega6": 0.5,
        "glycemic_index": 55, "glycemic_load": 27.8,
        "sodium": 380, "potassium": 300, "calcium": 220, "magnesium": 30, "iron": 0.6, "zinc": 1.2, "phosphorus": 210,
        "vitamin_d": 2, "vitamin_b12": 0.5, "folate": 15, "vitamin_c": 3, "vitamin_k": 2,
        "cost": 45, "prep_time_min": 10, "ingredients": ["white rice", "curd (yogurt)", "milk", "mustard seeds", "curry leaves", "ginger"],
        "tags": ["indian", "probiotic", "gluten-free", "low-purine"],
        "suitable_for": ["elderly", "office_worker", "celiac", "gout"], "avoid_for": ["type2_diabetes", "type1_diabetes"],
        "variants": [("Pomegranate", ["pomegranate"]), ("Cucumber", ["cucumber"]), ("Grated Carrot", ["carrot"])],
    },
    # ── Indian: Egg Bhurji (eggetarian breakfast) ──
    # Serving: 3 eggs scrambled + 1 whole wheat roti (30 g atta)
    {
        "id": "egg-bhurji-", "name_base": "Egg Bhurji with ",
        "diet_type": "eggetarian", "meal_slot": "breakfast",
        "calories": 340, "protein": 22.0, "leucine": 1.87, "carbs": 22.0, "net_carbs": 19.0, "sugar": 3.0, "fiber": 3.0,
        "fats": 18.0, "saturated_fat": 5.0, "unsaturated_fat": 13.0, "omega3": 0.2, "omega6": 2.5,
        "glycemic_index": 45, "glycemic_load": 8.6,
        "sodium": 480, "potassium": 320, "calcium": 90, "magnesium": 40, "iron": 2.8, "zinc": 2.2, "phosphorus": 320,
        "vitamin_d": 120, "vitamin_b12": 1.5, "folate": 90, "vitamin_c": 12, "vitamin_k": 10,
        "cost": 60, "prep_time_min": 15, "ingredients": ["egg", "onion", "tomato", "green chili", "whole wheat flour (atta)", "wheat", "gluten", "vegetable oil"],
        "tags": ["indian", "high-protein", "low-purine"],
        "suitable_for": ["gym_bro", "teenager", "office_worker", "gout"], "avoid_for": ["celiac", "high_cholesterol"],
        "variants": [("Whole Wheat Roti", []), ("Multigrain Toast", ["multigrain bread"]), ("Spinach", ["spinach"])],
    },
    # ── Indian: Chicken Curry with Rice (non-veg lunch) ──
    # Serving: 150 g chicken curry + 1 cup (150 g) cooked rice
    {
        "id": "chicken-curry-", "name_base": "Chicken Curry with Rice & ",
        "diet_type": "non_veg", "meal_slot": "lunch",
        "calories": 490, "protein": 32.0, "leucine": 2.56, "carbs": 55.0, "net_carbs": 52.0, "sugar": 4.0, "fiber": 3.0,
        "fats": 16.0, "saturated_fat": 4.0, "unsaturated_fat": 12.0, "omega3": 0.1, "omega6": 3.0,
        "glycemic_index": 60, "glycemic_load": 31.2,
        "sodium": 620, "potassium": 520, "calcium": 50, "magnesium": 55, "iron": 2.2, "zinc": 2.5, "phosphorus": 320,
        "vitamin_d": 5, "vitamin_b12": 0.6, "folate": 30, "vitamin_c": 8, "vitamin_k": 8,
        "cost": 150, "prep_time_min": 40, "ingredients": ["chicken", "white rice", "onion", "tomato", "ginger", "garlic", "yogurt", "milk", "vegetable oil"],
        "tags": ["indian", "high-protein", "gluten-free"],
        "suitable_for": ["gym_bro", "teenager", "office_worker", "celiac"], "avoid_for": ["type2_diabetes", "type1_diabetes", "hypertension"],
        "variants": [("Jeera Rice", ["cumin"]), ("Onion Salad", ["onion"]), ("Cucumber Raita", ["cucumber"])],
    },
    # ── Vegan: Tofu Stir-fry with Brown Rice (calcium-rich) ──
    # Serving: 150 g calcium-set tofu + 1 cup (150 g) cooked brown rice + vegetables
    {
        "id": "tofu-stirfry-", "name_base": "Tofu Vegetable Stir-fry with Brown Rice & ",
        "diet_type": "vegan", "meal_slot": "dinner",
        "calories": 440, "protein": 24.0, "leucine": 1.92, "carbs": 55.0, "net_carbs": 49.0, "sugar": 5.0, "fiber": 6.0,
        "fats": 14.0, "saturated_fat": 2.0, "unsaturated_fat": 12.0, "omega3": 0.6, "omega6": 6.0,
        "glycemic_index": 50, "glycemic_load": 24.5,
        "sodium": 480, "potassium": 450, "calcium": 350, "magnesium": 120, "iron": 4.5, "zinc": 2.5, "phosphorus": 330,
        "vitamin_d": 0, "vitamin_b12": 0.0, "folate": 60, "vitamin_c": 40, "vitamin_k": 30,
        "cost": 120, "prep_time_min": 25, "ingredients": ["tofu", "soy", "brown rice", "broccoli", "bell peppers", "soy sauce", "wheat", "garlic", "sesame oil", "sesame"],
        "tags": ["high-protein", "calcium-rich", "plant-protein"],
        "suitable_for": ["osteoporosis", "office_worker", "athlete"], "avoid_for": ["ckd", "celiac"],
        "variants": [("Cashews", ["cashews", "tree nuts"]), ("Mushrooms", ["mushrooms"]), ("Snap Peas", ["snap peas"])],
    },
    # ── Keto: Cheese & Spinach Omelette ──
    # Serving: 3-egg omelette with 30 g cheddar and 1 cup spinach
    {
        "id": "keto-omelette-", "name_base": "Cheese & Spinach Omelette with ",
        "diet_type": "keto", "meal_slot": "breakfast",
        "calories": 370, "protein": 25.0, "leucine": 2.12, "carbs": 4.0, "net_carbs": 3.0, "sugar": 2.0, "fiber": 1.0,
        "fats": 28.0, "saturated_fat": 11.0, "unsaturated_fat": 17.0, "omega3": 0.3, "omega6": 3.0,
        "glycemic_index": 15, "glycemic_load": 0.5,
        "sodium": 520, "potassium": 330, "calcium": 300, "magnesium": 35, "iron": 2.8, "zinc": 2.8, "phosphorus": 400,
        "vitamin_d": 120, "vitamin_b12": 1.6, "folate": 120, "vitamin_c": 6, "vitamin_k": 150,
        "cost": 90, "prep_time_min": 10, "ingredients": ["egg", "cheddar cheese", "milk", "spinach", "butter"],
        "tags": ["keto", "low-carb", "high-protein", "gluten-free"],
        "suitable_for": ["gym_bro", "type2_diabetes", "pcos", "celiac"], "avoid_for": ["high_cholesterol", "ckd"],
        "variants": [("Mushrooms", ["mushrooms"]), ("Bell Peppers", ["bell peppers"]), ("Avocado", ["avocado"])],
    },
    # ── Keto: Coconut Chia Pudding ──
    # Serving: 30 g chia seeds soaked in 150 ml coconut milk
    {
        "id": "keto-chia-", "name_base": "Coconut Chia Pudding with ",
        "diet_type": "keto", "meal_slot": "breakfast",
        "calories": 330, "protein": 6.0, "leucine": 0.42, "carbs": 14.0, "net_carbs": 4.0, "sugar": 2.0, "fiber": 10.0,
        "fats": 28.0, "saturated_fat": 18.0, "unsaturated_fat": 10.0, "omega3": 5.0, "omega6": 1.6,
        "glycemic_index": 15, "glycemic_load": 0.6,
        "sodium": 30, "potassium": 330, "calcium": 200, "magnesium": 110, "iron": 2.5, "zinc": 1.4, "phosphorus": 280,
        "vitamin_d": 0, "vitamin_b12": 0.0, "folate": 20, "vitamin_c": 2, "vitamin_k": 1,
        "cost": 90, "prep_time_min": 5, "ingredients": ["chia seeds", "coconut milk", "coconut"],
        "tags": ["keto", "high-fiber", "high-omega3", "low-sodium", "gluten-free"],
        "suitable_for": ["pcos", "type2_diabetes", "hypertension", "celiac"], "avoid_for": ["high_cholesterol"],
        "variants": [("Almonds", ["almonds", "tree nuts"]), ("Raspberries", ["raspberries"]), ("Cocoa Nibs", ["cocoa"])],
    },
    # ── Keto: Grilled Chicken Caesar-style Salad ──
    # Serving: 150 g grilled chicken, romaine, 15 g parmesan, 2 tbsp Caesar dressing
    {
        "id": "keto-caesar-", "name_base": "Grilled Chicken Caesar-style Salad with ",
        "diet_type": "keto", "meal_slot": "lunch",
        "calories": 415, "protein": 35.0, "leucine": 2.8, "carbs": 6.0, "net_carbs": 4.0, "sugar": 2.0, "fiber": 2.0,
        "fats": 28.0, "saturated_fat": 6.0, "unsaturated_fat": 22.0, "omega3": 0.3, "omega6": 6.0,
        "glycemic_index": 15, "glycemic_load": 0.6,
        "sodium": 650, "potassium": 450, "calcium": 180, "magnesium": 45, "iron": 1.5, "zinc": 1.8, "phosphorus": 330,
        "vitamin_d": 8, "vitamin_b12": 0.5, "folate": 80, "vitamin_c": 15, "vitamin_k": 100,
        "cost": 180, "prep_time_min": 15, "ingredients": ["chicken breast", "romaine lettuce", "parmesan cheese", "milk", "olive oil", "egg", "anchovy", "fish", "lemon"],
        "tags": ["keto", "low-carb", "high-protein", "gluten-free"],
        "suitable_for": ["gym_bro", "type2_diabetes", "pcos", "celiac"], "avoid_for": ["hypertension"],
        "variants": [("Avocado", ["avocado"]), ("Boiled Egg", ["egg"]), ("Cherry Tomatoes", ["tomato"])],
    },
    # ── Keto: Tuna-stuffed Avocado ──
    # Serving: 120 g canned tuna in a whole avocado, 1 tbsp mayonnaise
    {
        "id": "keto-tuna-avocado-", "name_base": "Tuna-stuffed Avocado with ",
        "diet_type": "keto", "meal_slot": "lunch",
        "calories": 390, "protein": 30.0, "leucine": 2.4, "carbs": 13.0, "net_carbs": 3.0, "sugar": 1.0, "fiber": 10.0,
        "fats": 24.0, "saturated_fat": 3.5, "unsaturated_fat": 20.5, "omega3": 0.8, "omega6": 3.0,
        "glycemic_index": 15, "glycemic_load": 0.5,
        "sodium": 420, "potassium": 900, "calcium": 40, "magnesium": 70, "iron": 2.0, "zinc": 1.5, "phosphorus": 350,
        "vitamin_d": 60, "vitamin_b12": 3.0, "folate": 120, "vitamin_c": 15, "vitamin_k": 30,
        "cost": 220, "prep_time_min": 10, "ingredients": ["tuna", "fish", "avocado", "mayonnaise", "egg", "celery", "lemon"],
        "tags": ["keto", "low-carb", "high-protein", "gluten-free"],
        "suitable_for": ["pcos", "type2_diabetes", "celiac"], "avoid_for": ["ckd", "gout"],
        "variants": [("Red Onion", ["red onion"]), ("Jalapeno", ["jalapeno"]), ("Cucumber", ["cucumber"])],
    },
    # ── Keto: Pan-seared Salmon with Butter Broccoli ──
    # Serving: 150 g salmon fillet + 1 cup broccoli in 10 g butter
    {
        "id": "keto-salmon-", "name_base": "Pan-seared Salmon with Butter Broccoli & ",
        "diet_type": "keto", "meal_slot": "dinner",
        "calories": 440, "protein": 34.0, "leucine": 2.72, "carbs": 9.0, "net_carbs": 5.0, "sugar": 2.0, "fiber": 4.0,
        "fats": 30.0, "saturated_fat": 9.0, "unsaturated_fat": 21.0, "omega3": 2.5, "omega6": 1.5,
        "glycemic_index": 15, "glycemic_load": 0.8,
        "sodium": 380, "potassium": 900, "calcium": 80, "magnesium": 70, "iron": 1.5, "zinc": 1.0, "phosphorus": 450,
        "vitamin_d": 600, "vitamin_b12": 4.0, "folate": 90, "vitamin_c": 90, "vitamin_k": 120,
        "cost": 350, "prep_time_min": 20, "ingredients": ["salmon", "fish", "broccoli", "butter", "milk", "garlic"],
        "tags": ["keto", "high-omega3", "low-carb", "gluten-free"],
        "suitable_for": ["pcos", "type2_diabetes", "pregnant", "celiac"], "avoid_for": ["ckd"],
        "variants": [("Lemon", ["lemon"]), ("Garlic", []), ("Dill", ["dill"])],
    },
    # ── Keto: Paneer Tikka with Sauteed Vegetables (vegetarian keto) ──
    # Serving: 120 g paneer tikka + 1 cup sauteed peppers and onion
    {
        "id": "keto-paneer-tikka-", "name_base": "Paneer Tikka with Sauteed Vegetables & ",
        "diet_type": "keto", "meal_slot": "dinner",
        "calories": 420, "protein": 26.0, "leucine": 2.34, "carbs": 12.0, "net_carbs": 9.0, "sugar": 5.0, "fiber": 3.0,
        "fats": 30.0, "saturated_fat": 16.0, "unsaturated_fat": 14.0, "omega3": 0.3, "omega6": 1.0,
        "glycemic_index": 15, "glycemic_load": 1.4,
        "sodium": 520, "potassium": 350, "calcium": 550, "magnesium": 45, "iron": 1.2, "zinc": 3.0, "phosphorus": 420,
        "vitamin_d": 10, "vitamin_b12": 0.8, "folate": 40, "vitamin_c": 50, "vitamin_k": 20,
        "cost": 160, "prep_time_min": 25, "ingredients": ["paneer (cottage cheese)", "milk", "yogurt", "bell peppers", "onion", "butter", "spices"],
        "tags": ["keto", "indian", "calcium-rich", "low-carb", "gluten-free", "low-purine"],
        "suitable_for": ["osteoporosis", "pcos", "type2_diabetes", "celiac", "gout"], "avoid_for": ["ckd", "high_cholesterol"],
        "variants": [("Mint Chutney", ["mint"]), ("Cucumber Salad", ["cucumber"]), ("Green Salad", ["lettuce"])],
    },
    # ── Keto: Nut & Cheese Snack Box ──
    # Serving: 25 g nuts + 30 g cheese
    {
        "id": "keto-snack-", "name_base": "Keto Snack Box: ",
        "diet_type": "keto", "meal_slot": "snack",
        "calories": 275, "protein": 12.0, "leucine": 1.02, "carbs": 7.0, "net_carbs": 4.0, "sugar": 1.0, "fiber": 3.0,
        "fats": 22.0, "saturated_fat": 7.0, "unsaturated_fat": 15.0, "omega3": 0.0, "omega6": 3.5,
        "glycemic_index": 15, "glycemic_load": 0.6,
        "sodium": 200, "potassium": 200, "calcium": 250, "magnesium": 80, "iron": 1.0, "zinc": 1.5, "phosphorus": 250,
        "vitamin_d": 5, "vitamin_b12": 0.3, "folate": 15, "vitamin_c": 0, "vitamin_k": 1,
        "cost": 90, "prep_time_min": 2, "ingredients": ["tree nuts", "cheese", "milk"],
        "tags": ["keto", "low-carb", "gluten-free"],
        "suitable_for": ["type2_diabetes", "pcos", "celiac"], "avoid_for": ["high_cholesterol"],
        "variants": [("Almonds & Cheddar", ["almonds", "cheddar cheese"]), ("Walnuts & Mozzarella", ["walnuts", "mozzarella cheese"]), ("Macadamia & Gouda", ["macadamia", "gouda cheese"])],
    },
    # ── Paleo: Sweet Potato & Egg Hash ──
    # Serving: 2 eggs + 150 g sweet potato, 1 tsp olive oil
    {
        "id": "paleo-hash-", "name_base": "Sweet Potato & Egg Hash with ",
        "diet_type": "paleo", "meal_slot": "breakfast",
        "calories": 335, "protein": 18.0, "leucine": 1.53, "carbs": 30.0, "net_carbs": 25.0, "sugar": 7.0, "fiber": 5.0,
        "fats": 16.0, "saturated_fat": 4.0, "unsaturated_fat": 12.0, "omega3": 0.2, "omega6": 2.5,
        "glycemic_index": 55, "glycemic_load": 13.8,
        "sodium": 320, "potassium": 620, "calcium": 70, "magnesium": 45, "iron": 2.2, "zinc": 1.6, "phosphorus": 260,
        "vitamin_d": 80, "vitamin_b12": 1.0, "folate": 70, "vitamin_c": 20, "vitamin_k": 40,
        "cost": 80, "prep_time_min": 20, "ingredients": ["egg", "sweet potato", "onion", "olive oil"],
        "tags": ["paleo", "gluten-free", "whole-food"],
        "suitable_for": ["gym_bro", "celiac", "office_worker"], "avoid_for": [],
        "variants": [("Spinach", ["spinach"]), ("Bell Peppers", ["bell peppers"]), ("Avocado", ["avocado"])],
    },
    # ── Paleo: Banana Almond Butter Smoothie Bowl ──
    # Serving: 1 banana, 20 g almond butter, 200 ml fortified almond milk
    {
        "id": "paleo-smoothie-", "name_base": "Banana Almond Butter Smoothie Bowl with ",
        "diet_type": "paleo", "meal_slot": "breakfast",
        "calories": 370, "protein": 10.0, "leucine": 0.7, "carbs": 42.0, "net_carbs": 35.0, "sugar": 22.0, "fiber": 7.0,
        "fats": 18.0, "saturated_fat": 2.0, "unsaturated_fat": 16.0, "omega3": 0.1, "omega6": 4.0,
        "glycemic_index": 45, "glycemic_load": 15.8,
        "sodium": 150, "potassium": 650, "calcium": 300, "magnesium": 110, "iron": 1.5, "zinc": 1.2, "phosphorus": 200,
        "vitamin_d": 100, "vitamin_b12": 1.0, "folate": 40, "vitamin_c": 15, "vitamin_k": 3,
        "cost": 110, "prep_time_min": 5, "ingredients": ["banana", "almond butter", "almonds", "tree nuts", "almond milk", "coconut flakes", "coconut"],
        "tags": ["paleo", "dairy-free", "gluten-free", "low-sodium"],
        "suitable_for": ["office_worker", "hypertension", "celiac"], "avoid_for": ["ckd"],
        "variants": [("Berries", ["mixed berries"]), ("Pumpkin Seeds", ["pumpkin seeds"]), ("Cacao", ["cacao"])],
    },
    # ── Paleo: Grilled Chicken & Roasted Vegetable Bowl ──
    # Serving: 150 g chicken breast + 200 g roasted squash, zucchini and peppers
    {
        "id": "paleo-chicken-bowl-", "name_base": "Grilled Chicken & Roasted Vegetable Bowl with ",
        "diet_type": "paleo", "meal_slot": "lunch",
        "calories": 390, "protein": 38.0, "leucine": 3.04, "carbs": 28.0, "net_carbs": 21.0, "sugar": 8.0, "fiber": 7.0,
        "fats": 14.0, "saturated_fat": 3.0, "unsaturated_fat": 11.0, "omega3": 0.1, "omega6": 2.5,
        "glycemic_index": 45, "glycemic_load": 9.4,
        "sodium": 300, "potassium": 900, "calcium": 60, "magnesium": 70, "iron": 2.0, "zinc": 2.0, "phosphorus": 380,
        "vitamin_d": 5, "vitamin_b12": 0.6, "folate": 60, "vitamin_c": 60, "vitamin_k": 40,
        "cost": 190, "prep_time_min": 30, "ingredients": ["chicken breast", "butternut squash", "zucchini", "bell peppers", "olive oil", "herbs"],
        "tags": ["paleo", "high-protein", "low-sodium", "gluten-free"],
        "suitable_for": ["gym_bro", "athlete", "hypertension", "celiac"], "avoid_for": ["ckd"],
        "variants": [("Avocado", ["avocado"]), ("Dairy-free Pesto", ["basil", "pine nuts", "tree nuts"]), ("Lemon Herb Dressing", ["lemon"])],
    },
    # ── Paleo: Shrimp & Cauliflower Rice Stir-fry ──
    # Serving: 150 g shrimp + 200 g cauliflower rice, coconut aminos
    {
        "id": "paleo-shrimp-", "name_base": "Shrimp & Cauliflower Rice Stir-fry with ",
        "diet_type": "paleo", "meal_slot": "lunch",
        "calories": 285, "protein": 28.0, "leucine": 2.24, "carbs": 16.0, "net_carbs": 11.0, "sugar": 6.0, "fiber": 5.0,
        "fats": 12.0, "saturated_fat": 2.0, "unsaturated_fat": 10.0, "omega3": 0.4, "omega6": 3.0,
        "glycemic_index": 30, "glycemic_load": 3.3,
        "sodium": 600, "potassium": 600, "calcium": 120, "magnesium": 70, "iron": 1.5, "zinc": 2.0, "phosphorus": 350,
        "vitamin_d": 2, "vitamin_b12": 1.5, "folate": 90, "vitamin_c": 80, "vitamin_k": 25,
        "cost": 260, "prep_time_min": 20, "ingredients": ["shrimp", "shellfish", "cauliflower", "carrot", "coconut aminos", "coconut", "garlic", "avocado oil"],
        "tags": ["paleo", "low-carb", "low-gi", "gluten-free"],
        "suitable_for": ["pcos", "type2_diabetes", "celiac"], "avoid_for": ["gout", "hypertension"],
        "variants": [("Snap Peas", ["snap peas"]), ("Cashews", ["cashews", "tree nuts"]), ("Scallions", ["scallions"])],
    },
    # ── Paleo: Steak with Roasted Sweet Potato (iron-rich) ──
    # Serving: 150 g grass-fed sirloin + 150 g sweet potato
    {
        "id": "paleo-steak-", "name_base": "Grass-fed Steak with Roasted Sweet Potato & ",
        "diet_type": "paleo", "meal_slot": "dinner",
        "calories": 450, "protein": 36.0, "leucine": 2.88, "carbs": 32.0, "net_carbs": 27.0, "sugar": 7.0, "fiber": 5.0,
        "fats": 20.0, "saturated_fat": 7.0, "unsaturated_fat": 13.0, "omega3": 0.2, "omega6": 1.0,
        "glycemic_index": 55, "glycemic_load": 14.8,
        "sodium": 280, "potassium": 900, "calcium": 50, "magnesium": 60, "iron": 4.0, "zinc": 7.0, "phosphorus": 360,
        "vitamin_d": 5, "vitamin_b12": 3.0, "folate": 30, "vitamin_c": 20, "vitamin_k": 20,
        "cost": 380, "prep_time_min": 30, "ingredients": ["beef", "sweet potato", "olive oil", "garlic", "rosemary"],
        "tags": ["paleo", "iron-rich", "high-protein", "low-sodium", "gluten-free"],
        "suitable_for": ["anemia", "athlete", "gym_bro", "celiac"], "avoid_for": ["gout", "ckd", "high_cholesterol"],
        "variants": [("Green Beans", ["green beans"]), ("Asparagus", ["asparagus"]), ("Chimichurri", ["parsley"])],
    },
    # ── Paleo: Baked Cod with Root Vegetables (low-sodium) ──
    # Serving: 170 g cod fillet + 200 g roasted carrot, parsnip and beetroot
    {
        "id": "paleo-cod-", "name_base": "Baked Cod with Root Vegetables & ",
        "diet_type": "paleo", "meal_slot": "dinner",
        "calories": 340, "protein": 32.0, "leucine": 2.56, "carbs": 30.0, "net_carbs": 24.0, "sugar": 7.0, "fiber": 6.0,
        "fats": 10.0, "saturated_fat": 1.5, "unsaturated_fat": 8.5, "omega3": 0.4, "omega6": 1.5,
        "glycemic_index": 50, "glycemic_load": 12.0,
        "sodium": 220, "potassium": 950, "calcium": 60, "magnesium": 70, "iron": 1.2, "zinc": 1.0, "phosphorus": 380,
        "vitamin_d": 40, "vitamin_b12": 1.5, "folate": 50, "vitamin_c": 25, "vitamin_k": 15,
        "cost": 280, "prep_time_min": 35, "ingredients": ["cod", "fish", "carrot", "parsnip", "beetroot", "olive oil", "lemon"],
        "tags": ["paleo", "low-sodium", "lean-protein", "gluten-free"],
        "suitable_for": ["hypertension", "high_cholesterol", "elderly", "celiac"], "avoid_for": ["ckd"],
        "variants": [("Lemon & Dill", ["dill"]), ("Garlic", ["garlic"]), ("Almond Herb Crust", ["almonds", "tree nuts"])],
    },
    # ── Paleo: Apple & Almond Butter Snack ──
    # Serving: 1 medium apple + 20 g almond butter
    {
        "id": "paleo-apple-snack-", "name_base": "Paleo Snack: Apple & Almond Butter with ",
        "diet_type": "paleo", "meal_slot": "snack",
        "calories": 285, "protein": 7.0, "leucine": 0.49, "carbs": 28.0, "net_carbs": 22.0, "sugar": 19.0, "fiber": 6.0,
        "fats": 16.0, "saturated_fat": 1.5, "unsaturated_fat": 14.5, "omega3": 0.0, "omega6": 4.0,
        "glycemic_index": 38, "glycemic_load": 8.4,
        "sodium": 5, "potassium": 350, "calcium": 90, "magnesium": 90, "iron": 1.2, "zinc": 1.0, "phosphorus": 160,
        "vitamin_d": 0, "vitamin_b12": 0.0, "folate": 15, "vitamin_c": 8, "vitamin_k": 4,
        "cost": 70, "prep_time_min": 3, "ingredients": ["apple", "almond butter", "almonds", "tree nuts"],
        "tags": ["paleo", "low-sodium", "gluten-free"],
        "suitable_for": ["office_worker", "hypertension", "celiac"], "avoid_for": [],
        "variants": [("Cinnamon", ["cinnamon"]), ("Coconut Flakes", ["coconut"]), ("Pumpkin Seeds", ["pumpkin seeds"])],
    },
    # ── Mediterranean: Greek Yogurt Parfait with Walnuts ──
    # Serving: 200 g Greek yogurt + 20 g walnuts + 1 tsp honey
    {
        "id": "med-parfait-", "name_base": "Greek Yogurt Parfait with Walnuts & ",
        "diet_type": "mediterranean", "meal_slot": "breakfast",
        "calories": 325, "protein": 20.0, "leucine": 1.8, "carbs": 30.0, "net_carbs": 26.0, "sugar": 20.0, "fiber": 4.0,
        "fats": 14.0, "saturated_fat": 4.0, "unsaturated_fat": 10.0, "omega3": 1.5, "omega6": 6.0,
        "glycemic_index": 35, "glycemic_load": 9.1,
        "sodium": 80, "potassium": 400, "calcium": 250, "magnesium": 60, "iron": 0.8, "zinc": 1.5, "phosphorus": 300,
        "vitamin_d": 2, "vitamin_b12": 1.2, "folate": 30, "vitamin_c": 10, "vitamin_k": 3,
        "cost": 120, "prep_time_min": 5, "ingredients": ["greek yogurt", "milk", "walnuts", "tree nuts", "honey"],
        "tags": ["mediterranean", "calcium-rich", "low-sodium", "low-gi", "low-purine"],
        "suitable_for": ["osteoporosis", "pcos", "hypertension", "gout"], "avoid_for": [],
        "variants": [("Berries", ["mixed berries"]), ("Figs", ["figs"]), ("Pomegranate", ["pomegranate"])],
    },
    # ── Mediterranean: Shakshuka with Whole Grain Pita ──
    # Serving: 2 eggs poached in 200 g tomato-pepper sauce + 1 small whole wheat pita
    {
        "id": "med-shakshuka-", "name_base": "Shakshuka with Whole Grain Pita & ",
        "diet_type": "mediterranean", "meal_slot": "breakfast",
        "calories": 350, "protein": 18.0, "leucine": 1.53, "carbs": 34.0, "net_carbs": 27.0, "sugar": 9.0, "fiber": 7.0,
        "fats": 16.0, "saturated_fat": 4.0, "unsaturated_fat": 12.0, "omega3": 0.2, "omega6": 2.5,
        "glycemic_index": 50, "glycemic_load": 13.5,
        "sodium": 620, "potassium": 650, "calcium": 110, "magnesium": 60, "iron": 3.5, "zinc": 2.0, "phosphorus": 300,
        "vitamin_d": 80, "vitamin_b12": 1.0, "folate": 110, "vitamin_c": 45, "vitamin_k": 20,
        "cost": 100, "prep_time_min": 25, "ingredients": ["egg", "tomato", "bell peppers", "onion", "olive oil", "whole wheat pita", "wheat", "gluten", "cumin"],
        "tags": ["mediterranean", "vegetarian", "high-folate"],
        "suitable_for": ["office_worker", "pregnant", "teenager"], "avoid_for": ["celiac", "hypertension"],
        "variants": [("Feta", ["feta cheese", "milk"]), ("Spinach", ["spinach"]), ("Parsley", ["parsley"])],
    },
    # ── Mediterranean: Chickpea & Quinoa Tabbouleh (low-GI, gluten-free) ──
    # Serving: 1 cup (~220 g): 80 g chickpeas, 90 g cooked quinoa, herbs, 1 tbsp olive oil
    {
        "id": "med-tabbouleh-", "name_base": "Chickpea & Quinoa Tabbouleh with ",
        "diet_type": "mediterranean", "meal_slot": "lunch",
        "calories": 390, "protein": 14.0, "leucine": 1.05, "carbs": 52.0, "net_carbs": 41.0, "sugar": 4.0, "fiber": 11.0,
        "fats": 14.0, "saturated_fat": 2.0, "unsaturated_fat": 12.0, "omega3": 0.2, "omega6": 2.0,
        "glycemic_index": 35, "glycemic_load": 14.3,
        "sodium": 320, "potassium": 520, "calcium": 80, "magnesium": 110, "iron": 4.0, "zinc": 2.2, "phosphorus": 280,
        "vitamin_d": 0, "vitamin_b12": 0.0, "folate": 170, "vitamin_c": 35, "vitamin_k": 120,
        "cost": 110, "prep_time_min": 20, "ingredients": ["chickpeas", "quinoa", "parsley", "tomato", "cucumber", "olive oil", "lemon", "mint"],
        "tags": ["mediterranean", "low-gi", "high-fiber", "gluten-free"],
        "suitable_for": ["type2_diabetes", "pcos", "celiac", "high_cholesterol"], "avoid_for": ["ckd"],
        "variants": [("Hummus", ["tahini", "sesame"]), ("Olives", ["olives"]), ("Feta", ["feta cheese", "milk"])],
    },
    # ── Mediterranean: Chicken Souvlaki with Greek Salad ──
    # Serving: 150 g chicken skewers + Greek salad + 1/2 whole wheat pita + tzatziki
    {
        "id": "med-souvlaki-", "name_base": "Chicken Souvlaki with Greek Salad & ",
        "diet_type": "mediterranean", "meal_slot": "lunch",
        "calories": 420, "protein": 34.0, "leucine": 2.72, "carbs": 30.0, "net_carbs": 25.0, "sugar": 6.0, "fiber": 5.0,
        "fats": 18.0, "saturated_fat": 4.5, "unsaturated_fat": 13.5, "omega3": 0.2, "omega6": 2.0,
        "glycemic_index": 45, "glycemic_load": 11.2,
        "sodium": 680, "potassium": 650, "calcium": 150, "magnesium": 60, "iron": 2.0, "zinc": 2.0, "phosphorus": 340,
        "vitamin_d": 5, "vitamin_b12": 0.6, "folate": 70, "vitamin_c": 35, "vitamin_k": 60,
        "cost": 220, "prep_time_min": 30, "ingredients": ["chicken breast", "cucumber", "tomato", "red onion", "olives", "feta cheese", "milk", "yogurt", "olive oil", "whole wheat pita", "wheat", "gluten"],
        "tags": ["mediterranean", "high-protein"],
        "suitable_for": ["gym_bro", "office_worker", "athlete"], "avoid_for": ["celiac", "hypertension"],
        "variants": [("Tzatziki", ["garlic"]), ("Hummus", ["chickpeas", "tahini", "sesame"]), ("Extra Olives", ["olives"])],
    },
    # ── Mediterranean: Baked Sea Bass with Lentils ──
    # Serving: 150 g sea bass fillet + 3/4 cup (150 g) cooked green lentils
    {
        "id": "med-sea-bass-", "name_base": "Baked Sea Bass with Lentils & ",
        "diet_type": "mediterranean", "meal_slot": "dinner",
        "calories": 400, "protein": 36.0, "leucine": 2.88, "carbs": 32.0, "net_carbs": 23.0, "sugar": 3.0, "fiber": 9.0,
        "fats": 14.0, "saturated_fat": 2.5, "unsaturated_fat": 11.5, "omega3": 1.2, "omega6": 1.5,
        "glycemic_index": 30, "glycemic_load": 6.9,
        "sodium": 300, "potassium": 800, "calcium": 60, "magnesium": 90, "iron": 4.0, "zinc": 2.5, "phosphorus": 450,
        "vitamin_d": 300, "vitamin_b12": 2.5, "folate": 180, "vitamin_c": 15, "vitamin_k": 40,
        "cost": 320, "prep_time_min": 30, "ingredients": ["sea bass", "fish", "green lentils", "olive oil", "lemon", "garlic", "parsley"],
        "tags": ["mediterranean", "low-gi", "low-sodium", "high-omega3", "gluten-free"],
        "suitable_for": ["hypertension", "high_cholesterol", "type2_diabetes", "pregnant", "celiac"], "avoid_for": ["ckd"],
        "variants": [("Roasted Tomatoes", ["tomato"]), ("Spinach", ["spinach"]), ("Salsa Verde", ["capers", "parsley"])],
    },
    # ── Mediterranean: Vegetable & Chickpea Stew with Couscous ──
    # Serving: 1.5 cups stew (aubergine, zucchini, tomato, 80 g chickpeas) + 1/2 cup whole wheat couscous
    {
        "id": "med-chickpea-stew-", "name_base": "Vegetable & Chickpea Stew with Couscous & ",
        "diet_type": "mediterranean", "meal_slot": "dinner",
        "calories": 410, "protein": 15.0, "leucine": 1.12, "carbs": 60.0, "net_carbs": 48.0, "sugar": 10.0, "fiber": 12.0,
        "fats": 12.0, "saturated_fat": 1.8, "unsaturated_fat": 10.2, "omega3": 0.2, "omega6": 1.5,
        "glycemic_index": 45, "glycemic_load": 21.6,
        "sodium": 420, "potassium": 750, "calcium": 110, "magnesium": 90, "iron": 4.0, "zinc": 2.0, "phosphorus": 260,
        "vitamin_d": 0, "vitamin_b12": 0.0, "folate": 150, "vitamin_c": 40, "vitamin_k": 25,
        "cost": 120, "prep_time_min": 40, "ingredients": ["chickpeas", "aubergine", "zucchini", "tomato", "whole wheat couscous", "wheat", "gluten", "olive oil"],
        "tags": ["mediterranean", "high-fiber", "plant-protein", "iron-rich"],
        "suitable_for": ["high_cholesterol", "office_worker", "anemia"], "avoid_for": ["celiac", "ckd"],
        "variants": [("Feta", ["feta cheese", "milk"]), ("Harissa", ["chili"]), ("Toasted Almonds", ["almonds", "tree nuts"])],
    },
    # ── Mediterranean: Hummus & Vegetable Sticks ──
    # Serving: 80 g hummus + 150 g carrot and cucumber sticks
    {
        "id": "med-hummus-", "name_base": "Hummus with Vegetable Sticks & ",
        "diet_type": "mediterranean", "meal_slot": "snack",
        "calories": 215, "protein": 7.0, "leucine": 0.53, "carbs": 20.0, "net_carbs": 14.0, "sugar": 3.0, "fiber": 6.0,
        "fats": 12.0, "saturated_fat": 1.6, "unsaturated_fat": 10.4, "omega3": 0.1, "omega6": 5.0,
        "glycemic_index": 25, "glycemic_load": 3.5,
        "sodium": 330, "potassium": 350, "calcium": 50, "magnesium": 50, "iron": 2.0, "zinc": 1.2, "phosphorus": 150,
        "vitamin_d": 0, "vitamin_b12": 0.0, "folate": 70, "vitamin_c": 20, "vitamin_k": 10,
        "cost": 80, "prep_time_min": 5, "ingredients": ["chickpeas", "tahini", "sesame", "olive oil", "lemon", "carrot", "cucumber"],
        "tags": ["mediterranean", "low-gi", "high-fiber", "gluten-free"],
        "suitable_for": ["type2_diabetes", "pcos", "high_cholesterol", "celiac"], "avoid_for": [],
        "variants": [("Olives", ["olives"]), ("Bell Pepper Sticks", ["bell peppers"]), ("Cherry Tomatoes", ["tomato"])],
    },
    # ── Low-FODMAP: Overnight Oats with Lactose-free Milk ──
    # Serving: 40 g rolled oats + 200 ml lactose-free milk + 1 tbsp chia
    {
        "id": "lfm-oats-", "name_base": "Overnight Oats with Lactose-free Milk & ",
        "diet_type": "low_fodmap", "meal_slot": "breakfast",
        "calories": 335, "protein": 13.0, "leucine": 1.04, "carbs": 50.0, "net_carbs": 44.0, "sugar": 14.0, "fiber": 6.0,
        "fats": 9.0, "saturated_fat": 2.5, "unsaturated_fat": 6.5, "omega3": 0.8, "omega6": 2.0,
        "glycemic_index": 50, "glycemic_load": 22.0,
        "sodium": 120, "potassium": 420, "calcium": 300, "magnesium": 90, "iron": 2.2, "zinc": 2.0, "phosphorus": 330,
        "vitamin_d": 100, "vitamin_b12": 1.0, "folate": 30, "vitamin_c": 20, "vitamin_k": 5,
        "cost": 70, "prep_time_min": 5, "ingredients": ["rolled oats", "lactose-free milk", "milk", "chia seeds", "maple syrup"],
        "tags": ["low-fodmap", "low-sodium", "calcium-rich"],
        "suitable_for": ["ibs", "office_worker", "hypertension"], "avoid_for": [],
        "variants": [("Blueberries", ["blueberries"]), ("Strawberries", ["strawberries"]), ("Kiwi", ["kiwi"])],
    },
    # ── Low-FODMAP: Scrambled Eggs with Spinach & Potato Hash ──
    # Serving: 2 eggs + 1 cup spinach + 150 g potato
    {
        "id": "lfm-eggs-", "name_base": "Scrambled Eggs with Spinach & Potato Hash with ",
        "diet_type": "low_fodmap", "meal_slot": "breakfast",
        "calories": 330, "protein": 18.0, "leucine": 1.53, "carbs": 28.0, "net_carbs": 24.0, "sugar": 2.0, "fiber": 4.0,
        "fats": 16.0, "saturated_fat": 4.5, "unsaturated_fat": 11.5, "omega3": 0.2, "omega6": 2.5,
        "glycemic_index": 65, "glycemic_load": 15.6,
        "sodium": 380, "potassium": 750, "calcium": 100, "magnesium": 60, "iron": 2.8, "zinc": 1.8, "phosphorus": 300,
        "vitamin_d": 80, "vitamin_b12": 1.0, "folate": 120, "vitamin_c": 20, "vitamin_k": 200,
        "cost": 70, "prep_time_min": 20, "ingredients": ["egg", "spinach", "potato", "olive oil"],
        "tags": ["low-fodmap", "gluten-free", "low-purine"],
        "suitable_for": ["ibs", "celiac", "teenager", "gout"], "avoid_for": ["ckd"],
        "variants": [("Chives", ["chives"]), ("Red Bell Pepper", ["red bell pepper"]), ("Tomato", ["tomato"])],
    },
    # ── Low-FODMAP: Ginger Chicken with Rice ──
    # Serving: 150 g chicken + 1 cup (150 g) cooked rice + carrot and zucchini
    {
        "id": "lfm-ginger-chicken-", "name_base": "Ginger Chicken with Rice & ",
        "diet_type": "low_fodmap", "meal_slot": "lunch",
        "calories": 420, "protein": 32.0, "leucine": 2.56, "carbs": 50.0, "net_carbs": 48.0, "sugar": 3.0, "fiber": 2.0,
        "fats": 10.0, "saturated_fat": 2.5, "unsaturated_fat": 7.5, "omega3": 0.1, "omega6": 2.0,
        "glycemic_index": 60, "glycemic_load": 28.8,
        "sodium": 420, "potassium": 450, "calcium": 30, "magnesium": 50, "iron": 1.5, "zinc": 1.8, "phosphorus": 300,
        "vitamin_d": 5, "vitamin_b12": 0.5, "folate": 25, "vitamin_c": 25, "vitamin_k": 25,
        "cost": 150, "prep_time_min": 25, "ingredients": ["chicken breast", "white rice", "ginger", "carrot", "zucchini", "garlic-infused oil", "tamari", "soy"],
        "tags": ["low-fodmap", "gluten-free", "high-protein"],
        "suitable_for": ["ibs", "celiac", "office_worker"], "avoid_for": ["type2_diabetes", "type1_diabetes"],
        "variants": [("Bok Choy", ["bok choy"]), ("Green Beans", ["green beans"]), ("Spring Onion Greens", ["spring onion greens"])],
    },
    # ── Low-FODMAP: Firm Tofu & Quinoa Bowl (calcium-rich) ──
    # Serving: 150 g firm tofu + 1 cup (180 g) cooked quinoa + vegetables
    {
        "id": "lfm-tofu-quinoa-", "name_base": "Firm Tofu & Quinoa Bowl with ",
        "diet_type": "low_fodmap", "meal_slot": "lunch",
        "calories": 380, "protein": 22.0, "leucine": 1.76, "carbs": 42.0, "net_carbs": 36.0, "sugar": 4.0, "fiber": 6.0,
        "fats": 14.0, "saturated_fat": 2.0, "unsaturated_fat": 12.0, "omega3": 0.6, "omega6": 6.0,
        "glycemic_index": 45, "glycemic_load": 16.2,
        "sodium": 380, "potassium": 500, "calcium": 380, "magnesium": 130, "iron": 4.5, "zinc": 2.8, "phosphorus": 360,
        "vitamin_d": 0, "vitamin_b12": 0.0, "folate": 80, "vitamin_c": 50, "vitamin_k": 40,
        "cost": 120, "prep_time_min": 25, "ingredients": ["firm tofu", "soy", "quinoa", "red bell pepper", "spinach", "tamari", "sesame oil", "sesame"],
        "tags": ["low-fodmap", "calcium-rich", "plant-protein", "gluten-free"],
        "suitable_for": ["ibs", "celiac", "osteoporosis"], "avoid_for": ["ckd"],
        "variants": [("Peanut Sauce", ["peanuts"]), ("Carrot Ribbons", ["carrot"]), ("Cucumber", ["cucumber"])],
    },
    # ── Low-FODMAP: Baked Salmon with Potatoes ──
    # Serving: 150 g salmon fillet + 200 g baby potatoes
    {
        "id": "lfm-salmon-", "name_base": "Baked Salmon with Potatoes & ",
        "diet_type": "low_fodmap", "meal_slot": "dinner",
        "calories": 430, "protein": 32.0, "leucine": 2.56, "carbs": 35.0, "net_carbs": 31.0, "sugar": 2.0, "fiber": 4.0,
        "fats": 18.0, "saturated_fat": 3.5, "unsaturated_fat": 14.5, "omega3": 2.2, "omega6": 1.2,
        "glycemic_index": 60, "glycemic_load": 18.6,
        "sodium": 260, "potassium": 1000, "calcium": 40, "magnesium": 70, "iron": 1.5, "zinc": 1.0, "phosphorus": 450,
        "vitamin_d": 550, "vitamin_b12": 3.5, "folate": 50, "vitamin_c": 25, "vitamin_k": 30,
        "cost": 330, "prep_time_min": 35, "ingredients": ["salmon", "fish", "potato", "olive oil", "lemon", "dill"],
        "tags": ["low-fodmap", "high-omega3", "low-sodium", "gluten-free"],
        "suitable_for": ["ibs", "hypertension", "high_cholesterol", "pregnant", "celiac"], "avoid_for": ["ckd"],
        "variants": [("Green Beans", ["green beans"]), ("Carrots", ["carrot"]), ("Spinach", ["spinach"])],
    },
    # ── Low-FODMAP: Turkey & Vegetable Rice Noodles ──
    # Serving: 120 g lean turkey mince + 80 g dry rice noodles + vegetables
    {
        "id": "lfm-turkey-noodles-", "name_base": "Turkey & Vegetable Rice Noodles with ",
        "diet_type": "low_fodmap", "meal_slot": "dinner",
        "calories": 435, "protein": 30.0, "leucine": 2.4, "carbs": 52.0, "net_carbs": 49.0, "sugar": 4.0, "fiber": 3.0,
        "fats": 12.0, "saturated_fat": 3.0, "unsaturated_fat": 9.0, "omega3": 0.1, "omega6": 2.5,
        "glycemic_index": 55, "glycemic_load": 26.9,
        "sodium": 520, "potassium": 500, "calcium": 40, "magnesium": 50, "iron": 2.2, "zinc": 3.5, "phosphorus": 300,
        "vitamin_d": 5, "vitamin_b12": 1.2, "folate": 30, "vitamin_c": 40, "vitamin_k": 20,
        "cost": 200, "prep_time_min": 25, "ingredients": ["turkey", "rice noodles", "carrot", "red bell pepper", "ginger", "tamari", "soy", "garlic-infused oil"],
        "tags": ["low-fodmap", "gluten-free", "high-protein"],
        "suitable_for": ["ibs", "celiac", "teenager"], "avoid_for": ["type2_diabetes", "type1_diabetes"],
        "variants": [("Bok Choy", ["bok choy"]), ("Peanuts", ["peanuts"]), ("Lime & Coriander", ["lime", "coriander"])],
    },
    # ── Low-FODMAP: Rice Cakes with Peanut Butter ──
    # Serving: 2 rice cakes + 20 g peanut butter
    {
        "id": "lfm-rice-cake-", "name_base": "Rice Cakes with Peanut Butter & ",
        "diet_type": "low_fodmap", "meal_slot": "snack",
        "calories": 245, "protein": 8.0, "leucine": 0.6, "carbs": 26.0, "net_carbs": 24.0, "sugar": 6.0, "fiber": 2.0,
        "fats": 12.0, "saturated_fat": 2.5, "unsaturated_fat": 9.5, "omega3": 0.0, "omega6": 3.5,
        "glycemic_index": 65, "glycemic_load": 15.6,
        "sodium": 150, "potassium": 220, "calcium": 15, "magnesium": 50, "iron": 0.8, "zinc": 1.0, "phosphorus": 130,
        "vitamin_d": 0, "vitamin_b12": 0.0, "folate": 20, "vitamin_c": 3, "vitamin_k": 0.5,
        "cost": 50, "prep_time_min": 3, "ingredients": ["rice cakes", "peanut butter", "peanuts"],
        "tags": ["low-fodmap", "gluten-free", "quick"],
        "suitable_for": ["ibs", "celiac", "office_worker"], "avoid_for": [],
        "variants": [("Banana Slices", ["banana"]), ("Strawberries", ["strawberries"]), ("Cinnamon", ["cinnamon"])],
    },
]


def _variant_parts(variant) -> tuple[str, list[str], list[str]]:
    """A variant is a name suffix, or (suffix, extra_ingredients[, extra_avoid_for])."""
    if isinstance(variant, str):
        return variant, [], []
    label, extra_ingredients, *rest = variant
    return label, list(extra_ingredients), list(rest[0]) if rest else []


def generate_seed_meals() -> list[dict]:
    """Generate 195 meals (49 templates) to seed neo4j."""
    import copy
    meals = []

    for tmpl in MEAL_TEMPLATES:
        tmpl_copy = copy.deepcopy(tmpl)   # never mutate the module-level template
        variants = tmpl_copy.pop("variants")
        name_base = tmpl_copy.pop("name_base")
        for i, variant in enumerate(variants):
            label, extra_ingredients, extra_avoid_for = _variant_parts(variant)
            meal = copy.deepcopy(tmpl_copy)
            meal["id"] = f"{tmpl_copy['id']}{i+1}"
            meal["name"] = name_base + label
            # Minor variation for nutritional realism (no carb bump for keto dishes)
            carb_bump = 0 if meal["diet_type"] == "keto" else (i % 3) * 4
            if carb_bump:
                meal["calories"] += (i % 3) * 15
            base_protein = meal["protein"]
            meal["protein"] = round(base_protein + (i % 2) * 1.5, 1)
            meal["carbs"] += carb_bump
            meal["sodium"] += (i % 5) * 10
            # Keep derived fields consistent with the varied values
            meal["leucine"] = round(meal["leucine"] * meal["protein"] / base_protein, 2)
            meal["net_carbs"] = round(meal["carbs"] - meal["fiber"], 1)
            meal["glycemic_load"] = round(meal["glycemic_index"] * meal["net_carbs"] / 100, 1)
            # Variant toppings/sides go into ingredients so allergen filtering sees them
            meal["ingredients"] = list(dict.fromkeys(meal["ingredients"] + extra_ingredients))
            meal["avoid_for"] = list(dict.fromkeys(meal["avoid_for"] + extra_avoid_for))
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
