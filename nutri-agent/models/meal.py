"""Meal schema with full 25+ nutrient panel."""

from pydantic import BaseModel, Field


class Meal(BaseModel):
    """A single meal with complete nutrient data. Unit of nutrition in the system."""

    id: str
    name: str
    diet_type: str
    meal_slot: str  # breakfast | lunch | dinner | snack |
    #                 pre_workout | post_workout | before_bed

    # ── Macros ──────────────────────────────────────────────────────────────
    calories: float
    protein: float          # g total
    leucine: float          # g — branched-chain, critical for MPS trigger (≥2.5g)
    carbs: float            # g total
    net_carbs: float        # g (carbs - fiber)
    sugar: float            # g
    fiber: float            # g
    fats: float             # g total
    saturated_fat: float    # g
    unsaturated_fat: float  # g
    omega3: float           # g
    omega6: float           # g
    glycemic_index: int     # 0–100
    glycemic_load: float    # GL = (GI × net_carbs) / 100

    # ── Micros ──────────────────────────────────────────────────────────────
    sodium: float           # mg
    potassium: float        # mg
    calcium: float          # mg
    magnesium: float        # mg
    iron: float             # mg
    zinc: float             # mg
    phosphorus: float       # mg
    vitamin_d: float        # IU
    vitamin_b12: float      # mcg
    folate: float           # mcg DFE
    vitamin_c: float        # mg
    vitamin_k: float        # mcg

    # ── Meta ─────────────────────────────────────────────────────────────────
    cost: float
    prep_time_min: int
    ingredients: list[str] = []
    tags: list[str] = []          # e.g. ["high-protein", "low-gi", "post-workout"]
    suitable_for: list[str] = []  # e.g. ["diabetes", "ckd", "bulking"]
    avoid_for: list[str] = []     # e.g. ["gout", "hypertension"]

    @classmethod
    def from_neo4j(cls, record: dict) -> "Meal":
        """Create a Meal from a Neo4j node record (handles list serialisation)."""
        data = dict(record)
        # Neo4j may store lists as strings — ensure they're lists
        for list_field in ("ingredients", "tags", "suitable_for", "avoid_for"):
            val = data.get(list_field, [])
            if isinstance(val, str):
                data[list_field] = [v.strip() for v in val.split(",") if v.strip()]
        return cls(**data)
