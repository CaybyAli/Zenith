"""
Smoke-Tests fÃ¼r Profile Inheritance / Default Fallback â€” 2B-01-C
"""

import json
from pathlib import Path

import pytest

from core.profile_manager import ProfileLoadError, ProfileManager


PROFILES_DIR = Path(__file__).parent.parent / "profiles"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def test_default_json_exists():
    assert (PROFILES_DIR / "default.json").exists()


def test_default_profile_loads_and_validates():
    manager = ProfileManager(profiles_dir=PROFILES_DIR)

    profile = manager.load_default_profile()

    assert profile["profile_id"] == "default"
    assert profile["quality_mode"] == "balanced"
    assert profile["target_format"] == "16:9"
    assert profile["camera_zoom_enabled"] is False
    assert profile["grading_strength"] == 0.2
    assert profile["max_clip_duration"] == 45.0


def test_gaming_main_overrides_default_values():
    manager = ProfileManager(profiles_dir=PROFILES_DIR)

    profile = manager.load_profile("gaming_main")

    assert profile["profile_id"] == "gaming_main"
    assert profile["channel_type"] == "gaming_main"
    assert profile["quality_mode"] == "pro"
    assert profile["cut_aggressiveness"] == 0.85
    assert profile["source_aspect_ratio"] == "32:9"
    assert profile["reframing_mode"] == "intelligent_crop"
    assert profile["camera_zoom_enabled"] is True
    assert profile["gameplay_zoom_enabled"] is True


def test_missing_specific_fields_are_inherited_from_default(tmp_path):
    default_profile = ProfileManager(profiles_dir=PROFILES_DIR).load_default_profile()

    specific_profile = {
        "profile_id": "mini_profile",
        "channel_type": "mini_profile",
        "quality_mode": "pro",
        "cut_aggressiveness": 0.85,
    }

    _write_json(tmp_path / "default.json", default_profile)
    _write_json(tmp_path / "mini_profile.json", specific_profile)

    manager = ProfileManager(profiles_dir=tmp_path)
    profile = manager.load_profile("mini_profile")

    assert profile["profile_id"] == "mini_profile"
    assert profile["quality_mode"] == "pro"
    assert profile["cut_aggressiveness"] == 0.85

    assert profile["target_format"] == "16:9"
    assert profile["camera_zoom_enabled"] is False
    assert profile["grading_strength"] == 0.2
    assert profile["max_clip_duration"] == 45.0


def test_unknown_profile_uses_default_fallback(tmp_path):
    default_profile = ProfileManager(profiles_dir=PROFILES_DIR).load_default_profile()
    _write_json(tmp_path / "default.json", default_profile)

    manager = ProfileManager(profiles_dir=tmp_path)
    profile = manager.load_profile("unknown_channel")

    assert profile["profile_id"] == "unknown_channel"
    assert profile["channel_type"] == "unknown_channel"
    assert profile["quality_mode"] == "balanced"
    assert profile["target_format"] == "16:9"
    assert profile["camera_zoom_enabled"] is False
    assert profile["_is_fallback"] is True


def test_missing_default_json_raises_clear_error(tmp_path):
    manager = ProfileManager(profiles_dir=tmp_path)

    with pytest.raises(ProfileLoadError, match="Default-Profil fehlt"):
        manager.load_profile("gaming_main")
