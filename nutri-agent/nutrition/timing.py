"""Pre/post-workout timing windows and meal slot scheduling."""

from models.user_profile import UserProfile
from models.meal_plan import NutritionTargets


# Base time map for workout times → actual hours
WORKOUT_TIME_MAP = {
    "morning":   "07:00",
    "afternoon": "14:00",
    "evening":   "18:00",
    "none":      None,
}


def build_timing_windows(profile: UserProfile, targets: NutritionTargets) -> dict:
    """
    Maps abstract meal slots to actual time windows based on
    workout_time, meals_per_day, and persona.

    Output schema example for a gym_bro training at 18:00:
    {
      "breakfast":    {"time": "08:00", "type": "regular"},
      "mid_morning":  {"time": "11:00", "type": "regular"},
      "lunch":        {"time": "13:00", "type": "regular"},
      "pre_workout":  {"time": "17:00", "type": "pre_workout",
                       "protein_g": 20, "carbs_g": 40, "note": "fast carbs + protein"},
      "post_workout": {"time": "19:30", "type": "post_workout",
                       "protein_g": 40, "carbs_g": 60, "note": "anabolic window"},
      "before_bed":   {"time": "22:00", "type": "before_bed",
                       "protein_g": 30, "note": "casein for overnight MPS"},
    }

    Rules:
    - pre_workout slot: 60–90 min before workout_time
    - post_workout slot: 30–60 min after estimated session end
    - before_bed: always last slot for gym_bro, athlete, elderly
    - For patients: distribute carbs evenly, no large carb boluses
    - For pregnant: add "nausea-friendly" tag to morning slots in first trimester
    """
    workout_time_str = WORKOUT_TIME_MAP.get(profile.workout_time)
    has_workout = workout_time_str is not None
    windows: dict = {}

    if has_workout:
        workout_hour = int(workout_time_str.split(":")[0])
        session_hours = profile.training_session_duration_min / 60

        # Pre-workout: 60–90 min before
        pre_hour = workout_hour - 1
        # Post-workout: 30–60 min after session end
        post_hour_raw = workout_hour + session_hours + 0.5
        post_hour = int(post_hour_raw)
        post_min = int((post_hour_raw - post_hour) * 60)
    else:
        pre_hour = None
        post_hour = None
        post_min = 0

    # Build regular meal slots
    meals_per_day = profile.meals_per_day
    wake_hour = 7
    sleep_hour = 22

    # Distribute regular meals across the day
    available_hours = sleep_hour - wake_hour
    slot_names = _get_slot_names(meals_per_day, has_workout)

    hour_cursor = wake_hour
    meal_interval = available_hours / max(len(slot_names), 1)

    for i, slot_name in enumerate(slot_names):
        slot_hour = round(wake_hour + i * meal_interval)
        slot_hour = min(slot_hour, sleep_hour - 1)

        # Check if this slot should be a workout slot
        if has_workout and slot_name == "pre_workout":
            windows[slot_name] = {
                "time": f"{pre_hour:02d}:00",
                "type": "pre_workout",
                "protein_g": targets.timing.pre_workout_protein,
                "carbs_g": targets.timing.pre_workout_carbs,
                "note": "fast carbs + moderate protein, 60–90 min before training",
            }
        elif has_workout and slot_name == "post_workout":
            windows[slot_name] = {
                "time": f"{post_hour:02d}:{post_min:02d}",
                "type": "post_workout",
                "protein_g": targets.timing.post_workout_protein,
                "carbs_g": targets.timing.post_workout_carbs,
                "note": "leucine-rich protein + fast carbs within 45 min",
            }
        elif slot_name == "before_bed":
            windows[slot_name] = {
                "time": f"{sleep_hour:02d}:00",
                "type": "before_bed",
                "protein_g": targets.timing.before_bed_protein,
                "note": "casein/slow protein for overnight MPS",
            }
        else:
            window = {
                "time": f"{slot_hour:02d}:00",
                "type": "regular",
            }
            # Pregnancy first trimester: nausea-friendly morning
            if (
                profile.persona == "pregnant"
                and profile.pregnancy_trimester == "first"
                and slot_name == "breakfast"
            ):
                window["note"] = "nausea-friendly: bland, small portion; crackers ok"

            # Patient: even carb distribution
            if profile.persona == "patient":
                window["note"] = "distribute carbs evenly — no large boluses"

            windows[slot_name] = window

    return windows


def _get_slot_names(meals_per_day: int, has_workout: bool) -> list[str]:
    """Generate slot names based on meals per day and workout presence."""
    base_slots = ["breakfast"]

    if meals_per_day >= 3:
        base_slots.append("lunch")
    if meals_per_day >= 2:
        base_slots.append("dinner")
    if meals_per_day >= 4:
        base_slots.insert(1, "mid_morning")
    if meals_per_day >= 5:
        base_slots.insert(3, "afternoon_snack")

    if has_workout:
        # Insert pre/post workout in appropriate positions
        if "pre_workout" not in base_slots:
            base_slots.append("pre_workout")
        if "post_workout" not in base_slots:
            base_slots.append("post_workout")

    # Before bed is always last for personas that need it
    base_slots.append("before_bed")

    # Trim to meals_per_day + workout slots
    max_slots = meals_per_day + (2 if has_workout else 0)
    return base_slots[:max_slots]
