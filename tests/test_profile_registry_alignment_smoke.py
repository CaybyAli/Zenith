"""
Smoke-Test fuer Profile Registry Alignment - 2B-01-E

Ziel:
ProfileManager ist die neue editable source of truth.
editing_profile_registry bleibt vorerst Legacy/Compatibility.
Beide duerfen sich bei wichtigen gaming_main Werten nicht widersprechen.
"""

from types import SimpleNamespace

from core.editing_profile_registry import resolve
from core.gaming_pipeline import _load_json_profile_for_job
from core.profile_manager import ProfileManager


PROFILES_DIR = __import__("pathlib").Path(__file__).parent.parent / "profiles"


def _fake_job(job_id="job_profile_alignment_smoke", channel_type="gaming_main"):
    return SimpleNamespace(
        job_id=job_id,
        channel_type=SimpleNamespace(value=channel_type),
    )


def test_profile_manager_loads_gaming_main_source_of_truth():
    profile = ProfileManager(profiles_dir=PROFILES_DIR).load_profile("gaming_main")

    assert profile["profile_id"] == "gaming_main"
    assert profile["quality_mode"] == "pro"
    assert profile["cut_aggressiveness"] == 0.85
    assert profile["source_aspect_ratio"] == "32:9"
    assert profile["target_format"] == "16:9"


def test_legacy_registry_resolve_still_works_for_gaming_main_pro():
    legacy_profile, mode_config = resolve(
        channel_str="gaming_main",
        quality_mode_str="pro",
    )

    assert legacy_profile.channel.value == "gaming_main"
    assert mode_config.mode.value == "pro"
    assert legacy_profile.cut_aggressiveness == 0.85


def test_json_profile_and_legacy_registry_align_on_core_values():
    json_profile = ProfileManager(profiles_dir=PROFILES_DIR).load_profile("gaming_main")
    legacy_profile, mode_config = resolve(
        channel_str="gaming_main",
        quality_mode_str="pro",
    )

    assert json_profile["profile_id"] == legacy_profile.channel.value
    assert json_profile["quality_mode"] == mode_config.mode.value
    assert json_profile["cut_aggressiveness"] == legacy_profile.cut_aggressiveness


def test_pipeline_helper_loads_json_gaming_main_profile():
    job = _fake_job(channel_type="gaming_main")

    profile = _load_json_profile_for_job(job)

    assert profile["profile_id"] == "gaming_main"
    assert profile["quality_mode"] == "pro"
    assert profile["cut_aggressiveness"] == 0.85