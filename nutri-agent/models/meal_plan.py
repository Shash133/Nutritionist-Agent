"""Nutrition targets, meal plan, and evaluation result models."""

from pydantic import BaseModel, Field, computed_field
from typing import Optional
from models.meal import Meal


# ── Target schemas ───────────────────────────────────────────────────────────

class MacroTargets(BaseModel):
    """Daily macronutrient targets."""
    calories: int
    protein: int                  # g/day
    protein_per_kg_lbm: float     # g per kg lean body mass
    leucine_per_meal: float       # g minimum per meal for MPS
    carbs: int                    # g/day
    net_carbs: int                # g/day
    fiber: int                    # g/day (25–38g)
    fats: int                     # g/day
    saturated_fat_max: int        # g/day
    omega3_min: float             # g/day
    sugar_max: int                # g/day
    glycemic_load_max: int        # per meal cap


class MicroTargets(BaseModel):
    """Daily micronutrient targets."""
    sodium_max: int               # mg/day
    potassium_min: int            # mg/day
    calcium_min: int              # mg/day
    magnesium_min: int            # mg/day
    iron_min: float               # mg/day
    zinc_min: float               # mg/day
    phosphorus_max: Optional[int] = None  # mg/day — relevant for CKD
    potassium_max: Optional[int] = None   # mg/day — relevant for CKD
    vitamin_d_min: int            # IU/day
    vitamin_b12_min: float        # mcg/day
    folate_min: int               # mcg DFE/day
    vitamin_c_min: int            # mg/day


class TimingTargets(BaseModel):
    """Pre/post-workout and meal timing targets."""
    pre_workout_carbs: int        # g — 1–2h before training
    pre_workout_protein: int      # g
    post_workout_protein: int     # g — within 45 min after
    post_workout_carbs: int       # g
    before_bed_protein: int       # g — casein/slow protein
    meal_frequency: int
    protein_per_meal_min: int     # g — for leucine threshold coverage


class NutritionTargets(BaseModel):
    """Complete nutrition target profile for a user."""
    macros: MacroTargets
    micros: MicroTargets
    timing: TimingTargets
    supplement_stack: list[str] = []   # e.g. ["creatine 5g", "omega-3 2g"]
    persona: str
    notes: list[str] = []             # e.g. ["Limit sodium due to hypertension"]


# ── Meal plan ────────────────────────────────────────────────────────────────

class MealPlan(BaseModel):
    """A complete day's meal plan with named slots."""
    slots: dict[str, list[Meal]] = {}  # slot_name → list of meals

    @property
    def all_meals(self) -> list[Meal]:
        return [m for meals in self.slots.values() for m in meals]

    @property
    def all_slots_named(self) -> dict[str, list[Meal]]:
        return self.slots

    # ── Macro totals ─────────────────────────────────────────────────────
    @computed_field
    @property
    def total_calories(self) -> float:
        return sum(m.calories for m in self.all_meals)

    @computed_field
    @property
    def total_protein(self) -> float:
        return sum(m.protein for m in self.all_meals)

    @computed_field
    @property
    def total_carbs(self) -> float:
        return sum(m.carbs for m in self.all_meals)

    @computed_field
    @property
    def total_net_carbs(self) -> float:
        return sum(m.net_carbs for m in self.all_meals)

    @computed_field
    @property
    def total_fats(self) -> float:
        return sum(m.fats for m in self.all_meals)

    @computed_field
    @property
    def total_fiber(self) -> float:
        return sum(m.fiber for m in self.all_meals)

    @computed_field
    @property
    def total_sugar(self) -> float:
        return sum(m.sugar for m in self.all_meals)

    @computed_field
    @property
    def total_saturated_fat(self) -> float:
        return sum(m.saturated_fat for m in self.all_meals)

    @computed_field
    @property
    def total_omega3(self) -> float:
        return sum(m.omega3 for m in self.all_meals)

    @computed_field
    @property
    def total_omega6(self) -> float:
        return sum(m.omega6 for m in self.all_meals)

    # ── Micro totals ─────────────────────────────────────────────────────
    @computed_field
    @property
    def total_sodium(self) -> float:
        return sum(m.sodium for m in self.all_meals)

    @computed_field
    @property
    def total_potassium(self) -> float:
        return sum(m.potassium for m in self.all_meals)

    @computed_field
    @property
    def total_calcium(self) -> float:
        return sum(m.calcium for m in self.all_meals)

    @computed_field
    @property
    def total_magnesium(self) -> float:
        return sum(m.magnesium for m in self.all_meals)

    @computed_field
    @property
    def total_iron(self) -> float:
        return sum(m.iron for m in self.all_meals)

    @computed_field
    @property
    def total_zinc(self) -> float:
        return sum(m.zinc for m in self.all_meals)

    @computed_field
    @property
    def total_phosphorus(self) -> float:
        return sum(m.phosphorus for m in self.all_meals)

    @computed_field
    @property
    def total_vitamin_d(self) -> float:
        return sum(m.vitamin_d for m in self.all_meals)

    @computed_field
    @property
    def total_vitamin_b12(self) -> float:
        return sum(m.vitamin_b12 for m in self.all_meals)

    @computed_field
    @property
    def total_folate(self) -> float:
        return sum(m.folate for m in self.all_meals)

    @computed_field
    @property
    def total_vitamin_c(self) -> float:
        return sum(m.vitamin_c for m in self.all_meals)

    @computed_field
    @property
    def total_vitamin_k(self) -> float:
        return sum(m.vitamin_k for m in self.all_meals)

    @computed_field
    @property
    def total_cost(self) -> float:
        return sum(m.cost for m in self.all_meals)


# ── Evaluation result ────────────────────────────────────────────────────────

class EvaluationResult(BaseModel):
    """Result of evaluating a meal plan against nutrition targets."""
    valid: bool
    issues: list[str] = []
    iteration: int = 0
