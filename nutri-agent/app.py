"""NutriGraph Streamlit Frontend — Premium AI Nutrition Planner."""

import sys
import os
import uuid
import json
import streamlit as st

# ── Path setup (so agent modules are importable) ──────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from langgraph.checkpoint.sqlite import SqliteSaver
from graph.builder import build_graph
from models.user_profile import UserProfile

SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "nutrigraph_sessions.db")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nutritionist AI — Clinical Nutrition Planner",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design system (CSS injection) ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Background */
.stApp {
    background: linear-gradient(135deg, #0A0E1A 0%, #0D1321 50%, #0A0E1A 100%);
    color: #E8EDF5;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F1629 0%, #111828 100%);
    border-right: 1px solid rgba(0, 208, 132, 0.15);
}

/* Hero header */
.hero-header {
    background: linear-gradient(135deg, rgba(0,208,132,0.12) 0%, rgba(0,122,255,0.08) 100%);
    border: 1px solid rgba(0,208,132,0.25);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
    backdrop-filter: blur(10px);
}
.hero-header h1 {
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #00D084, #00A8FF);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 0.4rem 0;
}
.hero-header p {
    color: #8B95A8;
    font-size: 1.05rem;
    margin: 0;
}

/* Section headers */
.section-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 1.1rem;
    font-weight: 600;
    color: #00D084;
    margin: 1.5rem 0 0.8rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid rgba(0,208,132,0.2);
}

/* Meal cards */
.meal-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s;
}
.meal-card:hover {
    border-color: rgba(0,208,132,0.35);
}
.meal-card h3 {
    font-size: 1.05rem;
    font-weight: 600;
    color: #E8EDF5;
    margin: 0 0 0.6rem 0;
}
.macro-row {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    margin-top: 0.5rem;
}
.macro-pill {
    background: rgba(0,208,132,0.12);
    border: 1px solid rgba(0,208,132,0.25);
    border-radius: 20px;
    padding: 0.2rem 0.7rem;
    font-size: 0.78rem;
    font-weight: 500;
    color: #00D084;
}
.macro-pill.carbs {
    background: rgba(0,168,255,0.12);
    border-color: rgba(0,168,255,0.25);
    color: #00A8FF;
}
.macro-pill.fats {
    background: rgba(255,179,0,0.12);
    border-color: rgba(255,179,0,0.25);
    color: #FFB300;
}
.macro-pill.cal {
    background: rgba(255,71,87,0.12);
    border-color: rgba(255,71,87,0.25);
    color: #FF4757;
}
.tag-chip {
    display: inline-block;
    background: rgba(255,255,255,0.07);
    border-radius: 6px;
    padding: 0.15rem 0.55rem;
    font-size: 0.72rem;
    color: #8B95A8;
    margin: 0.15rem;
}

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 1.2rem;
    text-align: center;
}
.metric-card .label {
    font-size: 0.78rem;
    color: #8B95A8;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.4rem;
}
.metric-card .value {
    font-size: 2rem;
    font-weight: 700;
    color: #E8EDF5;
}
.metric-card .target {
    font-size: 0.78rem;
    color: #8B95A8;
    margin-top: 0.2rem;
}

/* Status badges */
.status-ok { color: #00D084; font-weight: 600; }
.status-warn { color: #FFB300; font-weight: 600; }
.status-bad { color: #FF4757; font-weight: 600; }

/* Supplement cards */
.supp-card {
    background: linear-gradient(135deg, rgba(0,168,255,0.08), rgba(0,208,132,0.05));
    border: 1px solid rgba(0,168,255,0.2);
    border-radius: 12px;
    padding: 0.8rem 1.2rem;
    margin-bottom: 0.6rem;
    display: flex;
    align-items: center;
    gap: 0.7rem;
    font-size: 0.9rem;
    color: #B8C5D8;
}

/* Note cards */
.note-card {
    background: rgba(255,179,0,0.07);
    border: 1px solid rgba(255,179,0,0.2);
    border-left: 3px solid #FFB300;
    border-radius: 8px;
    padding: 0.8rem 1.2rem;
    margin-bottom: 0.6rem;
    font-size: 0.88rem;
    color: #C8B080;
}

/* Generate button */
div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #00D084, #00A050) !important;
    color: #000 !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 0.7rem 2rem !important;
    width: 100% !important;
    transition: all 0.2s !important;
    box-shadow: 0 4px 20px rgba(0,208,132,0.3) !important;
}
div[data-testid="stButton"] > button:hover {
    box-shadow: 0 6px 30px rgba(0,208,132,0.5) !important;
    transform: translateY(-1px) !important;
}

/* Progress bars */
.progress-row {
    margin: 0.6rem 0;
}
.progress-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.82rem;
    color: #8B95A8;
    margin-bottom: 0.25rem;
}
.progress-bar-wrap {
    background: rgba(255,255,255,0.07);
    border-radius: 6px;
    height: 8px;
    overflow: hidden;
}
.progress-bar-fill {
    height: 100%;
    border-radius: 6px;
    transition: width 0.6s ease;
}

/* Tabs */
[data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 10px !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
}
[data-baseweb="tab"] {
    border-radius: 8px !important;
    color: #8B95A8 !important;
    font-weight: 500 !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    background: rgba(0,208,132,0.15) !important;
    color: #00D084 !important;
}

/* Hide default Streamlit header decorations */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Helper: status colour
# ══════════════════════════════════════════════════════════════════════════════
def status_cls(status: str) -> str:
    if status == "ok":
        return "status-ok"
    if "flagged" in status:
        return "status-warn"
    return "status-bad"


def status_label(status: str) -> str:
    mapping = {
        "ok": "✅ OK",
        "supplement_flagged": "⚠️ Supplement suggested",
        "supplement_required": "🔴 Supplement required",
    }
    return mapping.get(status, status)


def progress_color(pct: float) -> str:
    if pct <= 1.1:
        return "#00D084"
    if pct <= 1.3:
        return "#FFB300"
    return "#FF4757"


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar — Profile form
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:1rem 0 0.5rem 0;">
        <div style="font-size:2rem;">🥗</div>
        <div style="font-size:1.15rem;font-weight:700;color:#00D084;">NutriGraph AI</div>
        <div style="font-size:0.75rem;color:#8B95A8;margin-top:2px;">Clinical Nutrition Planner</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown('<div class="section-header">👤 Persona & Goals</div>', unsafe_allow_html=True)

    persona = st.selectbox(
        "Persona",
        ["gym_bro", "athlete", "patient", "elderly", "pregnant", "teenager", "office_worker"],
        format_func=lambda x: {
            "gym_bro": "🏋️ Gym Bro",
            "athlete": "🏃 Athlete",
            "patient": "🏥 Patient",
            "elderly": "👴 Elderly",
            "pregnant": "🤱 Pregnant",
            "teenager": "🧒 Teenager",
            "office_worker": "💼 Office Worker",
        }[x],
        index=6,
        key="persona",
    )

    goal = st.selectbox(
        "Goal",
        ["fat_loss", "muscle_gain", "maintenance", "performance", "clinical", "longevity"],
        format_func=lambda x: {
            "fat_loss": "🔥 Fat Loss",
            "muscle_gain": "💪 Muscle Gain",
            "maintenance": "⚖️ Maintenance",
            "performance": "⚡ Performance",
            "clinical": "🏥 Clinical",
            "longevity": "🌿 Longevity",
        }[x],
        key="goal",
    )

    training_phase = st.selectbox(
        "Training Phase",
        ["bulk", "cut", "recomp", "maintenance", "peak"],
        index=3,
        key="training_phase",
    )

    activity_level = st.selectbox(
        "Activity Level",
        ["sedentary", "lightly_active", "moderate", "very_active", "athlete"],
        format_func=lambda x: x.replace("_", " ").title(),
        index=1,
        key="activity_level",
    )

    st.markdown('<div class="section-header">🥘 Diet Preferences</div>', unsafe_allow_html=True)

    diet_type = st.selectbox(
        "Diet Type",
        ["veg", "non_veg", "eggetarian", "vegan", "keto", "paleo", "mediterranean", "low_fodmap"],
        format_func=lambda x: x.replace("_", " ").title(),
        index=1,
        key="diet_type",
    )

    supplement_openness = st.selectbox(
        "Supplement Openness",
        ["none", "basic", "advanced"],
        format_func=lambda x: {"none": "❌ None", "basic": "🟡 Basic", "advanced": "🟢 Advanced"}[x],
        index=2,
        key="supplement_openness",
    )

    st.divider()
    st.markdown(
        '<div style="font-size:0.72rem;color:#4A5568;text-align:center;">Powered by LangGraph + Gemini AI</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Main area — Hero + Profile form
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero-header">
    <h1>🥗 NutriGraph AI</h1>
    <p>Clinical-grade, persona-driven nutrition planning powered by LangGraph &amp; Gemini AI.
       Fill in your profile and generate a personalised meal plan with macro targets, micro tracking, and supplement guidance.</p>
</div>
""", unsafe_allow_html=True)


# ── Biometrics ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📊 Biometrics</div>', unsafe_allow_html=True)
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    age = st.number_input("Age", min_value=10, max_value=100, value=25, key="age")
with col2:
    gender = st.selectbox("Gender", ["male", "female", "other"], key="gender")
with col3:
    weight = st.number_input("Weight (kg)", min_value=30.0, max_value=250.0, value=75.0, step=0.5, key="weight")
with col4:
    height = st.number_input("Height (cm)", min_value=100.0, max_value=250.0, value=175.0, step=0.5, key="height")
with col5:
    body_fat = st.number_input("Body Fat %", min_value=2.0, max_value=65.0, value=20.0, step=0.5, key="body_fat")


# ── Training schedule ─────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🏋️ Training Schedule</div>', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
with col1:
    sport = st.selectbox(
        "Sport",
        ["powerlifting", "bodybuilding", "crossfit", "endurance", "team_sport", "combat", "swimming", "cycling", "none"],
        format_func=lambda x: x.replace("_", " ").title(),
        index=8,
        key="sport",
    )
with col2:
    training_days = st.slider("Training Days / Week", 0, 7, 4, key="training_days")
with col3:
    session_dur = st.slider("Session Duration (min)", 0, 180, 60, step=15, key="session_dur")
with col4:
    workout_time = st.selectbox("Workout Time", ["morning", "afternoon", "evening", "none"], index=2, key="workout_time")


# ── Diet & Budget ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">💰 Budget & Meals</div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
with col1:
    budget = st.number_input("Budget per Day (₹)", min_value=50.0, max_value=2000.0, value=500.0, step=10.0, key="budget")
with col2:
    meals_per_day = st.slider("Meals per Day", 2, 8, 3, key="meals_per_day")
with col3:
    allergies_raw = st.text_input("Allergies (comma-separated)", placeholder="e.g. nuts, shellfish", key="allergies")


# ── Medical ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🏥 Medical Conditions</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)
all_conditions = [
    "none", "type2_diabetes", "type1_diabetes", "hypertension", "ckd",
    "pcos", "hypothyroidism", "celiac", "ibs", "high_cholesterol",
    "anemia", "osteoporosis", "gout", "nafld",
]
with col1:
    medical_conditions = st.multiselect(
        "Conditions",
        all_conditions,
        default=["none"],
        format_func=lambda x: x.replace("_", " ").title(),
        key="medical_conditions",
    )
with col2:
    pregnancy_trimester = st.selectbox(
        "Pregnancy Trimester",
        ["none", "first", "second", "third", "postpartum"],
        key="pregnancy_trimester",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Generate button
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
generate = st.button("🚀 Generate My Nutrition Plan", key="generate_btn")

# ══════════════════════════════════════════════════════════════════════════════
# Agent execution
# ══════════════════════════════════════════════════════════════════════════════
if generate:
    # Build profile
    allergies_list = [a.strip() for a in allergies_raw.split(",") if a.strip()] if allergies_raw else []
    conditions = medical_conditions if medical_conditions else ["none"]

    profile_data = {
        "age": int(age),
        "gender": gender,
        "weight": float(weight),
        "height": float(height),
        "body_fat_pct": float(body_fat),
        "activity_level": activity_level,
        "persona": persona,
        "goal": goal,
        "training_phase": training_phase,
        "sport": sport,
        "training_days_per_week": int(training_days),
        "training_session_duration_min": int(session_dur),
        "workout_time": workout_time,
        "diet_type": diet_type,
        "budget_per_day": float(budget),
        "meals_per_day": int(meals_per_day),
        "allergies": allergies_list,
        "intolerances": [],
        "likes": [],
        "dislikes": [],
        "medical_conditions": conditions,
        "medications": [],
        "pregnancy_trimester": pregnancy_trimester,
        "supplement_openness": supplement_openness,
    }

    try:
        profile = UserProfile(**profile_data)
    except Exception as e:
        st.error(f"❌ Profile validation error: {e}")
        st.stop()

    thread_id = str(uuid.uuid4())

    status_msgs = [
        "🧠 Analysing your profile and persona...",
        "📐 Calculating macro & micro targets...",
        "🥘 Selecting optimal meal combinations...",
        "🔄 Running LangGraph replanning loop...",
        "✅ Finalising your personalised plan...",
    ]

    result_placeholder = st.empty()

    with st.spinner(""):
        status_slot = st.empty()
        for msg in status_msgs[:2]:
            status_slot.info(msg)

        initial_state = {
            "profile": profile,
            "iteration": 0,
            "used_meal_ids": {},
            "all_issues": [],
            "user_history": [],
            "preference_memo": {},
            "llm_reasoning": [],
        }
        config = {"configurable": {"thread_id": thread_id}}

        try:
            with SqliteSaver.from_conn_string(SQLITE_DB_PATH) as checkpointer:
                status_slot.info(status_msgs[2])
                agent = build_graph(checkpointer=checkpointer)
                status_slot.info(status_msgs[3])
                final_state = agent.invoke(initial_state, config=config)
                status_slot.info(status_msgs[4])
        except Exception as e:
            st.error(f"❌ Agent error: {e}")
            st.stop()

        status_slot.empty()

    if "final_output" not in final_state:
        st.error("❌ Agent did not produce a final output. Check logs.")
        st.stop()

    output = final_state["final_output"]
    st.session_state["last_output"] = output
    st.session_state["last_thread_id"] = thread_id

# ══════════════════════════════════════════════════════════════════════════════
# Results dashboard (shown if output exists in session_state)
# ══════════════════════════════════════════════════════════════════════════════
if "last_output" in st.session_state:
    output = st.session_state["last_output"]
    thread_id = st.session_state.get("last_thread_id", "—")

    st.divider()
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:1rem;margin-bottom:1.5rem;">
        <div>
            <div style="font-size:1.4rem;font-weight:700;color:#E8EDF5;">Your Personalised Plan</div>
            <div style="font-size:0.78rem;color:#4A5568;">Session: <code style="color:#00D084;">{thread_id[:18]}…</code>
            &nbsp;|&nbsp; Iterations: <b>{output.get("iterations_used", "—")}</b>
            &nbsp;|&nbsp; Status: <span class="{status_cls(output.get('status',''))}">
            {"✅ Valid" if output.get("status") == "valid" else "⚠️ " + str(output.get("status","")).replace("_", " ").title()}</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🍽️ Meal Plan", "📊 Nutrition", "💊 Supplements & Notes", "{}  Raw JSON"])

    # ── Tab 1: Meal Plan ──────────────────────────────────────────────────────
    with tab1:
        meal_plan = output.get("meal_plan", {})
        slot_icons = {
            "breakfast": "🌅", "lunch": "☀️", "dinner": "🌙",
            "pre_workout": "⚡", "post_workout": "💪", "snack": "🍎",
        }
        if not meal_plan:
            st.info("No meal plan data available.")
        else:
            for slot, meals in meal_plan.items():
                icon = slot_icons.get(slot, "🍴")
                st.markdown(
                    f'<div class="section-header">{icon} {slot.replace("_"," ").title()}</div>',
                    unsafe_allow_html=True,
                )
                for meal in meals:
                    ingredients = ", ".join(meal.get("ingredients", []))
                    tags_html = "".join(
                        f'<span class="tag-chip">{t}</span>'
                        for t in meal.get("tags", [])
                    )
                    st.markdown(f"""
                    <div class="meal-card">
                        <h3>{meal.get("name", "Unnamed Meal")}</h3>
                        <div style="font-size:0.8rem;color:#8B95A8;margin-bottom:0.5rem;">
                            🕐 {meal.get("prep_time_min","?")} min &nbsp;|&nbsp;
                            🛒 ₹{meal.get("cost","?")} &nbsp;|&nbsp;
                            🍽️ {meal.get("diet_type","").replace("_"," ").title()}
                        </div>
                        <div class="macro-row">
                            <span class="macro-pill cal">🔥 {meal.get("calories","?")} kcal</span>
                            <span class="macro-pill">🥩 {meal.get("protein","?")}g protein</span>
                            <span class="macro-pill carbs">🌾 {meal.get("carbs","?")}g carbs</span>
                            <span class="macro-pill fats">🧈 {meal.get("fats","?")}g fats</span>
                            <span class="macro-pill">🌿 {meal.get("fiber","?")}g fiber</span>
                        </div>
                        <div style="margin-top:0.7rem;font-size:0.82rem;color:#8B95A8;">
                            <b>Ingredients:</b> {ingredients}
                        </div>
                        <div style="margin-top:0.4rem;">{tags_html}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # ── Tab 2: Nutrition Dashboard ────────────────────────────────────────────
    with tab2:
        actuals = output.get("nutrition_actuals", {})

        # Top macro metrics
        macro_keys = [
            ("calories", "🔥 Calories", "kcal"),
            ("protein", "🥩 Protein", "g"),
            ("net_carbs", "🌾 Net Carbs", "g"),
        ]
        cols = st.columns(len(macro_keys) + 1)
        for i, (key, label, unit) in enumerate(macro_keys):
            d = actuals.get(key, {})
            actual = d.get("actual", "—")
            target = d.get("target", "—")
            with cols[i]:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="label">{label}</div>
                    <div class="value">{actual}</div>
                    <div class="target">Target: {target} {unit}</div>
                </div>
                """, unsafe_allow_html=True)

        # Budget
        with cols[-1]:
            total_cost = output.get("cost", "—")
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">💰 Daily Cost</div>
                <div class="value">₹{total_cost}</div>
                <div class="target">Budget: ₹{budget}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Progress bars for all nutrients
        st.markdown('<div class="section-header">🔬 Nutrient Status</div>', unsafe_allow_html=True)

        skip_keys = set()
        for key, data in actuals.items():
            if key in skip_keys:
                continue

            target = data.get("target") or data.get("max")
            actual = data.get("actual") or data.get("min_actual")
            status = data.get("status", "ok")
            label_text = key.replace("_", " ").title()

            if target is None or actual is None:
                continue

            pct = min(actual / target, 2.0) if target else 1.0
            fill_w = min(pct * 100, 100)
            color = progress_color(pct)
            status_text = status_label(status)
            cls = status_cls(status)

            st.markdown(f"""
            <div class="progress-row">
                <div class="progress-label">
                    <span>{label_text}</span>
                    <span>{actual} / {target} &nbsp; <span class="{cls}">{status_text}</span></span>
                </div>
                <div class="progress-bar-wrap">
                    <div class="progress-bar-fill" style="width:{fill_w}%;background:{color};"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Leucine row (special format)
        leucine = actuals.get("leucine_per_meal", {})
        if leucine:
            min_actual = leucine.get("min_actual", 0)
            target = leucine.get("target", 1)
            pct = min(min_actual / target, 2.0) if target else 1.0
            color = progress_color(pct)
            st.markdown(f"""
            <div class="progress-row">
                <div class="progress-label">
                    <span>Leucine Per Meal</span>
                    <span>{min_actual}g min / {target}g target &nbsp;
                    <span class="{status_cls(leucine.get('status','ok'))}">{status_label(leucine.get('status','ok'))}</span></span>
                </div>
                <div class="progress-bar-wrap">
                    <div class="progress-bar-fill" style="width:{min(pct*100,100):.0f}%;background:{color};"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Tab 3: Supplements & Notes ────────────────────────────────────────────
    with tab3:
        supps = output.get("supplement_stack", [])
        notes = output.get("medical_notes", [])
        traces = output.get("llm_replan_traces", [])

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="section-header">💊 Supplement Stack</div>', unsafe_allow_html=True)
            if supps:
                for s in supps:
                    st.markdown(f'<div class="supp-card">💊 {s}</div>', unsafe_allow_html=True)
            else:
                st.info("No supplements recommended.")

        with col2:
            st.markdown('<div class="section-header">📋 Medical Notes</div>', unsafe_allow_html=True)
            if notes:
                for n in notes:
                    st.markdown(f'<div class="note-card">⚠️ {n}</div>', unsafe_allow_html=True)
            else:
                st.info("No medical notes.")

        if traces:
            st.markdown('<div class="section-header">🤖 AI Replanning Traces</div>', unsafe_allow_html=True)
            for t in traces:
                st.markdown(f"""
                <div style="background:rgba(0,168,255,0.06);border:1px solid rgba(0,168,255,0.15);
                border-left:3px solid #00A8FF;border-radius:8px;padding:0.7rem 1rem;
                margin-bottom:0.5rem;font-size:0.85rem;color:#8BB8D8;">
                🤖 {t}
                </div>""", unsafe_allow_html=True)

        issues = output.get("all_issues_encountered", [])
        if issues:
            with st.expander(f"🔍 All Issues Encountered ({len(issues)})", expanded=False):
                for issue in issues:
                    st.markdown(f"- `{issue}`")

    # ── Tab 4: Raw JSON ───────────────────────────────────────────────────────
    with tab4:
        st.markdown('<div class="section-header">📄 Raw Agent Output</div>', unsafe_allow_html=True)
        st.json(output)
        json_str = json.dumps(output, indent=2)
        st.download_button(
            label="⬇️ Download JSON",
            data=json_str,
            file_name=f"nutrigraph_plan_{thread_id[:8]}.json",
            mime="application/json",
        )
