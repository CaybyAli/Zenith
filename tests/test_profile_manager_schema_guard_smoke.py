"""
Smoke-Tests für Profile Validation Hardening / Schema Guard — 2B-01-D
"""

import json
from pathlib import Path

import pytest

from core.profile_manager import ProfileManager, ProfileValidationError


PROFILES_DIR = Path(__file__).parent.parent / "profiles"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_default(tmp_path: Path) -> None:
    default_profile = ProfileManager(profiles_dir=PROFILES_DIR).load_default_profile()
    _write_json(tmp_path / "default.json", default_profile)


def _write_bad_profile(tmp_path: Path, overrides: dict) -> None:
    profile = {
        "profile_id": "bad_profile",
        "channel_type": "bad_profile",
    }
    profile.update(overrides)
    _write_json(tmp_path / "bad_profile.json", profile)


def _load_bad_profile(tmp_path: Path) -> None:
    manager = ProfileManager(profiles_dir=tmp_path)
    manager.load_profile("bad_profile")


def test_valid_gaming_main_profile_loads():
    manager = ProfileManager(profiles_dir=PROFILES_DIR)

    profile = manager.load_profile("gaming_main")

    assert profile["profile_id"] == "gaming_main"
    assert profile["quality_mode"] == "pro"
    assert profile["cut_aggressiveness"] == 0.85


def test_invalid_quality_mode_raises_profile_validation_error(tmp_path):
    _write_default(tmp_path)
    _write_bad_profile(tmp_path, {"quality_mode": "super_pro"})

    with pytest.raises(ProfileValidationError, match="quality_mode"):
        _load_bad_profile(tmp_path)


def test_cut_aggressiveness_above_one_raises_profile_validation_error(tmp_path):
    _write_default(tmp_path)
    _write_bad_profile(tmp_path, {"cut_aggressiveness": 5.0})

    with pytest.raises(ProfileValidationError, match="cut_aggressiveness"):
        _load_bad_profile(tmp_path)


def test_music_enabled_string_raises_profile_validation_error(tmp_path):
    _write_default(tmp_path)
    _write_bad_profile(tmp_path, {"music_enabled": "yes"})

    with pytest.raises(ProfileValidationError, match="music_enabled"):
        _load_bad_profile(tmp_path)


def test_camera_zoom_trigger_string_raises_profile_validation_error(tmp_path):
    _write_default(tmp_path)
    _write_bad_profile(tmp_path, {"camera_zoom_trigger": "reaction"})

    with pytest.raises(ProfileValidationError, match="camera_zoom_trigger"):
        _load_bad_profile(tmp_path)


def test_min_clip_duration_greater_than_max_raises_profile_validation_error(tmp_path):
    _write_default(tmp_path)
    _write_bad_profile(
        tmp_path,
        {
            "min_clip_duration": 50.0,
            "max_clip_duration": 10.0,
        },
    )

    with pytest.raises(ProfileValidationError, match="min_clip_duration"):
        _load_bad_profile(tmp_path)


def test_invalid_source_aspect_ratio_raises_profile_validation_error(tmp_path):
    _write_default(tmp_path)
    _write_bad_profile(tmp_path, {"source_aspect_ratio": "banana"})

    with pytest.raises(ProfileValidationError, match="source_aspect_ratio"):
        _load_bad_profile(tmp_path)


def test_empty_version_raises_profile_validation_error(tmp_path):
    _write_default(tmp_path)
    _write_bad_profile(tmp_path, {"version": ""})

    with pytest.raises(ProfileValidationError, match="version"):
        _load_bad_profile(tmp_path)


def test_unknown_profile_default_fallback_still_works(tmp_path):
    _write_default(tmp_path)

    manager = ProfileManager(profiles_dir=tmp_path)
    profile = manager.load_profile("unknown_profile_xyz")

    assert profile["profile_id"] == "unknown_profile_xyz"
    assert profile["quality_mode"] == "balanced"
    assert profile["_is_fallback"] is True
