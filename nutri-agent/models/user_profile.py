"""Expanded user profile with persona, medical conditions, and computed body composition."""

from pydantic import BaseModel, Field, computed_field
from typing import Literal, Optional


# ── Persona types ────────────────────────────────────────────────────────────
PersonaType = Literal[
    "gym_bro", "athlete", "patient", "elderly",
    "pregnant", "teenager", "office_worker"
]

TrainingPhase = Literal["bulk", "cut", "recomp", "maintenance", "peak"]

SportType = Literal[
    "powerlifting", "bodybuilding", "crossfit", "endurance",
    "team_sport", "combat", "swimming", "cycling", "none"
]

MedicalCondition = Literal[
    "type2_diabetes", "type1_diabetes", "hypertension", "ckd",
    "pcos", "hypothyroidism", "celiac", "ibs", "high_cholesterol",
    "anemia", "osteoporosis", "gout", "nafld", "none"
]

PregnancyTrimester = Literal["first", "second", "third", "postpartum", "none"]


class UserProfile(BaseModel):
    """Full user intake form. Drives all downstream persona + nutrition logic."""

    # ── Core biometrics ──────────────────────────────────────────────────────
    age: int = Field(..., ge=10, le=100)
    gender: Literal["male", "female", "other"]
    weight: float = Field(..., gt=0, description="kg")
    height: float = Field(..., gt=0, description="cm")
    body_fat_pct: Optional[float] = Field(
        None, ge=2, le=65, description="% body fat if known"
    )
    activity_level: Literal[
        "sedentary", "lightly_active", "moderate", "very_active", "athlete"
    ]

    # ── Persona & goal ───────────────────────────────────────────────────────
    persona: PersonaType
    goal: Literal[
        "fat_loss", "muscle_gain", "maintenance",
        "performance", "clinical", "longevity"
    ]
    training_phase: TrainingPhase = "maintenance"
    sport: SportType = "none"

    # ── Training schedule (for timing windows) ───────────────────────────────
    training_days_per_week: int = Field(default=3, ge=0, le=7)
    training_session_duration_min: int = Field(default=60, ge=0, le=300)
    workout_time: Literal["morning", "afternoon", "evening", "none"] = "none"

    # ── Diet preferences ─────────────────────────────────────────────────────
    diet_type: Literal[
        "veg", "non_veg", "eggetarian", "vegan", "keto",
        "paleo", "mediterranean", "low_fodmap"
    ]
    budget_per_day: float = Field(..., gt=0)
    meals_per_day: int = Field(default=4, ge=2, le=8)
    allergies: list[str] = []
    intolerances: list[str] = []       # e.g. lactose, gluten (soft avoid)
    likes: list[str] = []
    dislikes: list[str] = []

    # ── Medical / clinical ───────────────────────────────────────────────────
    medical_conditions: list[MedicalCondition] = ["none"]
    medications: list[str] = []        # e.g. ["metformin", "lisinopril"]
    pregnancy_trimester: PregnancyTrimester = "none"

    # ── Advanced fitness ─────────────────────────────────────────────────────
    current_lifts: Optional[dict] = None
    # e.g. {"squat": 100, "bench": 80, "deadlift": 120} kg
    supplement_openness: Literal["none", "basic", "advanced"] = "basic"
    # basic  → protein powder, creatine, omega-3
    # advanced → + pre-workout, BCAAs, beta-alanine, ashwagandha, ZMA, etc.

    # ── Computed fields ──────────────────────────────────────────────────────
    @computed_field
    @property
    def lean_body_mass(self) -> float:
        """LBM in kg. Uses body_fat_pct if provided, else estimates via Boer formula."""
        if self.body_fat_pct:
            return round(self.weight * (1 - self.body_fat_pct / 100), 2)
        # Boer formula estimate
        if self.gender == "male":
            return round(0.407 * self.weight + 0.267 * self.height - 19.2, 2)
        return round(0.252 * self.weight + 0.473 * self.height - 48.3, 2)

    @computed_field
    @property
    def ffmi(self) -> Optional[float]:
        """Fat-Free Mass Index. Only if body_fat_pct provided."""
        if not self.body_fat_pct:
            return None
        height_m = self.height / 100
        return round(self.lean_body_mass / (height_m ** 2), 2)
