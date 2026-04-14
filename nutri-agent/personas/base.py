"""Base class for all persona nutrition profiles."""

from abc import ABC, abstractmethod
from models.user_profile import UserProfile
from models.meal_plan import NutritionTargets


class PersonaBase(ABC):
    """
    Each persona subclass encodes domain-specific nutrition science:
    - Target macros/micros/timing based on persona rules
    - Supplement stack recommendations
    - Medical notes and warnings
    """

    @abstractmethod
    def compute_targets(
        self, profile: UserProfile, bmr: float, tdee: float
    ) -> NutritionTargets:
        """Each persona overrides this with its specific nutrition science."""

    def get_supplement_stack(self, profile: UserProfile) -> list[str]:
        """Return persona-specific supplement recommendations."""
        return []

    def get_medical_notes(self, profile: UserProfile) -> list[str]:
        """Return persona-specific medical notes and warnings."""
        return []
