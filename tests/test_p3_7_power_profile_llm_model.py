from core.power_profile import PowerProfile


def test_eco_returns_smallest_tier():
    assert PowerProfile.resolve_model_tier(PowerProfile.ECO) == "smallest_available"


def test_off_returns_shadow_only():
    assert PowerProfile.resolve_model_tier(PowerProfile.OFF) == "shadow_only"


def test_balanced_returns_default():
    assert PowerProfile.resolve_model_tier(PowerProfile.BALANCED) == "default"


def test_performance_returns_preferred():
    assert PowerProfile.resolve_model_tier(PowerProfile.PERFORMANCE) == "preferred"


def test_full_power_returns_largest():
    assert PowerProfile.resolve_model_tier(PowerProfile.FULL_POWER) == "largest_available"


def test_unknown_falls_back_to_default():
    assert PowerProfile.resolve_model_tier("xyz") == "default"
