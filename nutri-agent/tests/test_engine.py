import pytest

from nutrition.engine import calculate_bmr, get_nutrition_targets


@pytest.mark.parametrize("gender,expected", [
    ("male",   10 * 80 + 6.25 * 180 - 5 * 30 + 5),
    ("female", 10 * 80 + 6.25 * 180 - 5 * 30 - 161),
    ("other",  10 * 80 + 6.25 * 180 - 5 * 30 - 78),
])
def test_bmr_mifflin_st_jeor(make_profile, gender, expected):
    assert calculate_bmr(make_profile(gender=gender)) == pytest.approx(expected)


def test_ckd_patient_gets_potassium_and_phosphorus_caps(make_profile):
    profile = make_profile(persona="patient", goal="clinical", medical_conditions=["ckd"])
    targets = get_nutrition_targets(profile)
    assert targets.micros.potassium_max == 2000
    assert targets.micros.phosphorus_max == 800


def test_non_ckd_has_no_potassium_cap(make_profile):
    targets = get_nutrition_targets(make_profile())
    assert targets.micros.potassium_max is None
