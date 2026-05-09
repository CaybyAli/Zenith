"""
Finaler Profile Architecture Audit - 2B-01-F

Dieser Test schliesst 2B-01 technisch ab.
"""

from pathlib import Path
from types import SimpleNamespace

from core.editing_profile_registry import resolve
from core.gaming_pipeline import _load_json_profile_for_job
from core.profile_manager import ProfileManager


PROFILES_DIR = Path(__file__).parent.parent / "profiles"

EXPECTED_PROFILES = {
    "gaming_main",
    "vlog_main",
    "gaming_uncut",
    "reaction_uncut",
    "vlog_uncut",
}

REQUIRED_SNAPSHOT_FIELDS = {
    "profile_id",
    "channel_type",
    "quality_mode",
    "cut_aggressiveness",
    "source_aspect_ratio",
    "target_format",
    "reframing_mode",
    "version",
}


def _fake_job(job_id="job_profile_architecture_final_audit", channel_type="gaming_main"):
    return SimpleNamespace(
        job_id=job_id,
        channel_type=SimpleNamespace(value=channel_type),
    )


def test_list_profiles_returns_only_channel_profiles():
    manager = ProfileManager(profiles_dir=PROFILES_DIR)

    profiles = set(manager.list_profiles())

    assert profiles == EXPECTED_PROFILES
    assert "default" not in profiles


def test_default_profile_loads_correctly():
    manager = ProfileManager(profiles_dir=PROFILES_DIR)

    profile = manager.load_default_profile()

    assert profile["profile_id"] == "default"
    assert profile["quality_mode"] == "balanced"
    assert profile["target_format"] == "16:9"


def test_all_channel_profiles_load_and_contain_required_fields():
    manager = ProfileManager(profiles_dir=PROFILES_DIR)

    for profile_id in EXPECTED_PROFILES:
        profile = manager.load_profile(profile_id)

        assert profile["profile_id"] == profile_id
        assert REQUIRED_SNAPSHOT_FIELDS <= profile.keys()


def test_gaming_main_profile_has_expected_core_values():
    profile = ProfileManager(profiles_dir=PROFILES_DIR).load_profile("gaming_main")

    assert profile["quality_mode"] == "pro"
    assert profile["source_aspect_ratio"] == "32:9"
    assert profile["target_format"] == "16:9"
    assert profile["reframing_mode"] == "intelligent_crop"
    assert profile["cut_aggressiveness"] == 0.85


def test_unknown_profile_uses_default_fallback():
    profile = ProfileManager(profiles_dir=PROFILES_DIR).load_profile("unknown_profile_xyz")

    assert profile["profile_id"] == "unknown_profile_xyz"
    assert profile["_is_fallback"] is True
    assert profile["quality_mode"] == "balanced"


def test_legacy_registry_aligns_with_json_gaming_main():
    json_profile = ProfileManager(profiles_dir=PROFILES_DIR).load_profile("gaming_main")
    legacy_profile, mode_config = resolve(
        channel_str="gaming_main",
        quality_mode_str="pro",
    )

    assert legacy_profile.channel.value == json_profile["profile_id"]
    assert mode_config.mode.value == json_profile["quality_mode"]
    assert legacy_profile.cut_aggressiveness == json_profile["cut_aggressiveness"]


def test_pipeline_helper_loads_gaming_main_json_profile():
    profile = _load_json_profile_for_job(_fake_job(channel_type="gaming_main"))

    assert profile["profile_id"] == "gaming_main"
    assert profile["quality_mode"] == "pro"
    assert profile["cut_aggressiveness"] == 0.85


def test_key_profile_files_have_no_bom_and_end_with_newline():
    files = [
        PROFILES_DIR / "default.json",
        Path(__file__).parent / "test_profile_registry_alignment_smoke.py",
        Path(__file__),
    ]

    for path in files:
        raw = path.read_bytes()

        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"Missing newline at end of {path}"
