from core.power_profile import PowerProfile


def test_eco_has_low_thread_count():
    cfg = PowerProfile.resolve_render_config(PowerProfile.ECO)
    assert cfg["threads"] == 2


def test_full_power_has_best_nvenc_preset():
    cfg = PowerProfile.resolve_render_config(PowerProfile.FULL_POWER)
    assert cfg["nvenc_preset"] == "p7"


def test_balanced_has_auto_threads():
    cfg = PowerProfile.resolve_render_config(PowerProfile.BALANCED)
    assert cfg["threads"] == 0


def test_off_has_fastest_preset():
    cfg = PowerProfile.resolve_render_config(PowerProfile.OFF)
    assert cfg["nvenc_preset"] == "p1"


def test_render_config_always_has_required_keys():
    for profile in PowerProfile.ALL:
        cfg = PowerProfile.resolve_render_config(profile)
        assert "threads" in cfg
        assert "nvenc_preset" in cfg


def test_unknown_falls_back_to_balanced_config():
    cfg = PowerProfile.resolve_render_config("xyz")
    assert cfg["threads"] == 0
    assert cfg["nvenc_preset"] == "p4"
