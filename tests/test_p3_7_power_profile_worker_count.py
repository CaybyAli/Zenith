from core.power_profile import PowerProfile


def test_eco_returns_sequential():
    assert PowerProfile.resolve_worker_count(PowerProfile.ECO) == 1


def test_off_returns_sequential():
    assert PowerProfile.resolve_worker_count(PowerProfile.OFF) == 1


def test_balanced_returns_two():
    assert PowerProfile.resolve_worker_count(PowerProfile.BALANCED) == 2


def test_performance_returns_four():
    assert PowerProfile.resolve_worker_count(PowerProfile.PERFORMANCE) == 4


def test_full_power_returns_eight():
    assert PowerProfile.resolve_worker_count(PowerProfile.FULL_POWER) == 8


def test_unknown_falls_back_to_balanced():
    assert PowerProfile.resolve_worker_count("xyz") == 2


def test_analysis_workers_are_capped_for_resource_safety():
    assert PowerProfile.resolve_analysis_worker_count(PowerProfile.FULL_POWER) == 4
    assert PowerProfile.resolve_analysis_worker_count(PowerProfile.PERFORMANCE) == 4
    assert PowerProfile.resolve_analysis_worker_count(PowerProfile.BALANCED) == 2


def test_normalize_unknown_returns_balanced():
    assert PowerProfile.normalize("xyz") == PowerProfile.BALANCED


def test_normalize_valid_returns_unchanged():
    assert PowerProfile.normalize(PowerProfile.ECO) == PowerProfile.ECO
