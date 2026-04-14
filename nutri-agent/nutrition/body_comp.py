"""Body composition calculations — LBM, body fat estimation, FFMI."""

from models.user_profile import UserProfile


def estimate_body_fat_pct(profile: UserProfile) -> float:
    """
    Estimate body fat % using BMI-based formula (Deurenberg et al.).
    Only used when body_fat_pct is not provided.
    """
    bmi = profile.weight / (profile.height / 100) ** 2
    sex_factor = 1 if profile.gender == "male" else 0
    # Deurenberg formula
    bf_pct = 1.20 * bmi + 0.23 * profile.age - 10.8 * sex_factor - 5.4
    return max(5.0, min(55.0, bf_pct))


def calculate_lbm(profile: UserProfile) -> float:
    """Lean body mass in kg."""
    return profile.lean_body_mass


def calculate_ffmi(profile: UserProfile) -> float | None:
    """Fat-Free Mass Index. Returns None if body_fat_pct not provided."""
    return profile.ffmi


def calculate_bmi(profile: UserProfile) -> float:
    """Body Mass Index."""
    height_m = profile.height / 100
    return round(profile.weight / (height_m ** 2), 1)
